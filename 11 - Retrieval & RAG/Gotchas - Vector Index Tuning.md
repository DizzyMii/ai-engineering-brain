---
tags: [gotchas, domain/retrieval-rag, level/unicorn]
aliases: [ANN index tuning, HNSW tuning, filtered vector search, vector index pitfalls]
summary: "Production ANN failures: filtered-search disconnection, recall cliffs, delete rot, metric mismatch, memory blowup, and benchmark lies."
---

# Gotchas - Vector Index Tuning

The vector index is the one component of a RAG stack that looks fine in the demo, passes its unit tests, and then quietly returns the wrong three chunks in production. Approximate nearest-neighbor (ANN) indexes trade exactness for speed, and every knob in that trade has a failure mode that surfaces only under real data, real filters, and real update traffic. These are the ones that cost people a week, ordered by how often they do.

---

## 1. Filtered search silently craters recall as the filter gets selective

**Symptom:** A query with a metadata filter (`tenant_id = X`, `date > 2024`, `lang = "de"`) returns 2 results when it should return 10, or returns semantically worse hits than the same query without the filter. Unfiltered queries look perfect, so nobody suspects the index. Recall looks fine in aggregate but collapses precisely on the tenants or categories that match few documents.

**Cause:** This is the single most underestimated production issue in vector search, and it is a direct consequence of how [[Concept - HNSW]] works. Greedy graph search starts at a fixed entry point in the top layer and walks down toward the query. **Pre-filtering** — only traversing nodes that pass the predicate — disconnects the graph: if the entry point and the bridge nodes on the path to the answer all fail the filter, the walk cannot reach the surviving candidates, even though they exist in the index. The more selective the filter (the fewer nodes survive), the worse the connectivity, so recall degrades *non-linearly* toward zero exactly when the filter keeps only 1–5% of the corpus. **Post-filtering** — fetch the top-k by vector score, then drop non-matching rows — has the opposite failure: if 2% of docs match your filter, a top-100 retrieval yields ~2 survivors, so your effective `k` silently collapses.

**Fix:** In rough order of preference:
- **Filterable / filter-aware HNSW.** [[Reference - Vector Database Landscape|Qdrant]] builds extra payload-conditioned links so the graph stays connected within a filtered subset; this is its strongest differentiator. Weaviate and pgvector have their own filter integration paths.
- **ACORN-style predicate-agnostic traversal** (Patel et al. 2024): expand the neighbor exploration factor in proportion to filter selectivity so the walk visits enough nodes to route around filtered-out bridges.
- **Cardinality-threshold fallback to brute force.** Below some matching-set size, an exact scan of the surviving rows is both faster *and* correct. Qdrant does this automatically; it is the honest answer for highly selective filters.
- **Over-fetch then post-filter** as a crude fallback: raise `ef_search`/`k` by roughly the inverse of the filter selectivity. Wasteful, but it works when you can't change the engine.
- [[Concept - IVF and Product Quantization|IVF]]-with-filter degrades more gracefully than naive pre-filtered HNSW because scanning an inverted list and applying a predicate is a linear operation, not a graph walk that can strand you.

**Detection:** Plot recall@k as a function of filter selectivity on a labeled set. A healthy system is roughly flat; a broken one craters as the filter tightens. If you only ever benchmark unfiltered queries — as nearly everyone does — you will never see it until a customer with a narrow tenant complains.

---

## 2. The `ef_search` recall cliff — "defaults are fine" is a lie

**Symptom:** Recall sits at 0.999 on your test set, then a slightly different query distribution or a larger corpus drops it to 0.85 with no code change. Or: you copied `ef_search=64` from a README and never questioned it.

**Cause:** `ef_search` is the query-time beam width in HNSW — the size of the candidate priority queue during the greedy walk. Recall as a function of `ef_search` is **not linear and not concave everywhere**; it rises steeply then saturates, and *below a corpus-dependent threshold it falls off a cliff* rather than degrading gracefully. The threshold moves with corpus size, intrinsic dimensionality, and `M` (graph degree). A value that gives 0.99 recall at 1M vectors can give 0.9 at 10M because the graph is deeper and the beam is now too narrow to escape local minima.

**Fix:** Sweep `ef_search` against measured recall on a labeled query set and pick the value that hits your target recall (say 0.97) with margin, *at production scale*, not at prototype scale. `ef_search` is the one true runtime knob: it trades recall against latency continuously, and unlike `M` and `ef_construction` you can change it per-query without rebuilding. Set it deliberately; it should be an output of a measurement, never a copied constant.

**Detection:** A recall-vs-`ef_search` curve and a recall-vs-latency curve on your data. If you don't have a labeled recall set for your own corpus, you are flying blind — public numbers do not transfer (see #6).

---

## 3. Distance-metric mismatch produces confidently wrong rankings

**Symptom:** Retrieval quality is mediocre and inexplicable. Nearest neighbors are "kind of related" but never the obvious best match. No errors, no warnings — just a persistently bad top-k.

**Cause:** The index was built for one metric while the embedding model expects another. The classic case: an index configured for **L2 (Euclidean)** distance over embeddings that were trained for **cosine** similarity and were never L2-normalized. For normalized vectors, L2 and cosine rank identically ($\lVert q-d\rVert^2 = 2 - 2\,q\!\cdot\!d$ when $\lVert q\rVert=\lVert d\rVert=1$), so normalization masks the bug in tests — until you feed unnormalized vectors and magnitude starts leaking document length into the ranking. The dual mistake is using an **inner-product** index on unnormalized vectors and calling it "cosine," which rewards long documents for being long.

**Fix:** Match the metric to the model card. If the model says cosine, L2-normalize every vector at index and query time and use inner product (which now equals cosine, and is cheaper than an explicit norm in the hot loop). Verify a handful of known query→answer pairs by hand after any embedding-model or index-config change — this bug hides behind plausible-looking results.

**Detection:** Compute exact brute-force top-k for a sample of queries and compare against the index's top-k. If they disagree beyond expected ANN approximation error, you have a metric or normalization mismatch, not a recall problem.

---

## 4. Delete degradation — tombstones rot the graph

**Symptom:** A long-lived, update-heavy index slowly loses recall and gains tail latency over weeks. Nothing changed in the config. Rebuilding from scratch "fixes it," which nobody can explain.

**Cause:** HNSW has no true delete. Removing a vector marks it as a **tombstone**; the node stays in the graph as a routing waypoint but is filtered from results. As tombstones accumulate — think a document store with churn, or reindexing pipelines that delete-then-insert — the effective graph fills with dead nodes that the search still visits and traverses. Connectivity between live nodes degrades, `ef_search` now burns its beam on tombstones, and both recall and latency drift. Updates that change an embedding (re-embed a modified doc) are internally a delete + insert, so "we just update docs" is silently a tombstone factory.

**Fix:** Schedule periodic full rebuilds (or segment compaction/merge in Lucene-based engines like Elasticsearch/OpenSearch, which achieve the same effect by merging away deleted docs). Monitor the deleted-to-live ratio and rebuild before it passes ~20–30%. For genuinely streaming workloads where rebuilds are painful, move to a design built for it: [[Breakdown - DiskANN|FreshDiskANN]] merges an in-memory delta into the on-disk index instead of rotting in place.

**Detection:** Track `deleted_count / total_count` per index (Qdrant exposes vacuuming metrics; Lucene exposes `numDeletedDocs`). A rising ratio with flat or rising p99 latency is the tell.

---

## 5. Memory blowup — and the "2× raw vectors" folklore is wrong at high dimension

**Symptom:** You sized the box for `N × d × 4` bytes of embeddings, the index OOMs at load, and you can't explain the extra gigabytes. Or you over-provisioned 2× on a high-dimensional corpus and wasted money.

**Cause:** HNSW is an in-memory structure that stores the graph *on top of* the raw vectors. Per vector, the graph adds roughly $M_0 \times 4$ bytes at the base layer, where $M_0 = 2M$ is the max degree at layer 0 and each edge is a 4-byte node id, plus a smaller contribution from the exponentially sparser upper layers. The widely repeated "budget ~2× the raw vectors" rule is an **operational safety margin, not the data-structure math** — and it misleads in both directions:

| Case | Raw (fp32) | Graph (M=32, $M_0$=64) | Ratio |
|---|---|---|---|
| d=768 (typical) | 3072 B | ~256 B | **~1.08×** |
| d=384 (MiniLM) | 1536 B | ~256 B | ~1.17× |
| d=128 (low-dim) | 512 B | ~256 B | ~1.5× |

So at the common d=768–1536, the pure graph overhead is only ~5–15%. The "2×" figure comes from **operational headroom**: transient double-memory during a rebuild, payload/metadata indexes, deletion overhead (#4), and OS page-cache slack. Budget for *those*, not for an imaginary graph that doubles high-dimensional vectors. (See [[Reference - Memory Math for Transformers]] for the same bytes-per-element discipline applied to model serving.)

**Fix:** When the raw vectors themselves are the problem, attack them, not the graph:
- **Compress the vectors.** [[Concept - Embedding Quantization]]: int8 (4× smaller) or binary (32×) with a full-precision rescore of the shortlist recovers most recall. This is the highest-leverage memory lever for RAM-bound HNSW — the same recall-vs-precision trade you make for model weights in [[Concept - Post-Training Quantization Formats]], applied to embeddings.
- **Go to disk.** [[Breakdown - DiskANN]] serves billion-scale from SSD with a few GB of RAM (PQ codes in RAM, full vectors on SSD).
- **Plan `M`.** Higher `M` buys recall at linear memory cost; don't crank it reflexively.

**Detection:** Compute the expected footprint before deploying — `N × (d×4 + 2M×4)` for pure HNSW — and compare to RSS after load. A 2× surprise means payload indexes or a rebuild in flight, and you should find which.

---

## 6. `ann-benchmarks` recall is not your recall

**Symptom:** You picked an index/params off a public leaderboard, they hit 0.99 recall there, and you get 0.9 in production.

**Cause:** Public ANN benchmarks (Aumüller et al.'s `ann-benchmarks`; the SIFT1M/GIST/GloVe/DEEP datasets) use **uniformly distributed, static, unfiltered** query sets — the exact conditions your production workload violates. Real corpora are skewed and clustered (embedding spaces have hubs), real queries carry metadata filters (#1), and real indexes take live updates (#4). Any of those changes the achievable recall-latency frontier. The leaderboard tells you which algorithms are *good*, not what *your* number will be.

**Fix:** Benchmark on **your** vectors, **your** filter distribution, and **your** update pattern. Build a labeled recall set from real queries (even 200 of them) and measure the frontier you actually operate on. The metadata-filtering strategy is the number-one differentiator between vector stores, and it is precisely the thing public benchmarks omit.

**Detection:** If your only recall numbers come from a vendor slide or a public leaderboard, you have not measured recall. Full stop.

---

## 7. Over-indexing a tiny corpus

**Symptom:** A 30k-chunk knowledge base runs an HNSW index, occasionally returns approximate (slightly wrong) results, needs tuning, and is somehow not even faster than the obvious alternative.

**Cause:** ANN is a trade you make only when exact search is too slow. Flat brute-force is $O(N \cdot d)$ and **exact**. For 50k × 768-d vectors, one query is ~38M multiply-adds — sub-millisecond on a modern CPU with a BLAS/SIMD dot-product kernel, and trivially GPU-batched. Under roughly 1M vectors, a flat index (FAISS `IndexFlatIP`, pgvector with no index) is frequently faster *and* has perfect recall and zero tuning. Reaching for HNSW at 50k vectors buys you approximation error and a `ef_search` knob to babysit in exchange for nothing.

**Fix:** Know the crossover. Below ~1M vectors, default to exact flat search and revisit only when latency measurements say to. ANN earns its complexity at scale, not before it.

**Detection:** If your corpus fits in a few hundred MB and your p99 on flat search is already under budget, deleting the ANN index is a valid optimization.

---

## Connections
- [[Concept - HNSW]] — the graph structure whose greedy walk and tombstone model cause gotchas #1, #2, #4, and #5; understand it to debug them.
- [[Concept - IVF and Product Quantization]] — the cluster-and-compress alternative that degrades more gracefully under filters and is cheaper to build.
- [[Breakdown - DiskANN]] — the escape hatch for #5 (RAM) and #4 (streaming updates via FreshDiskANN).
- [[Concept - Embedding Quantization]] — the primary memory lever when raw vectors, not the graph, are what won't fit.
- [[Concept - Post-Training Quantization Formats]] — the model-serving analog of embedding quantization; the same recall/precision recovery pattern, a seam worth linking (domain: inference & serving).
- [[Reference - Vector Database Landscape]] — which engines implement filterable HNSW, quantization, and disk tiers; consult before picking a store (metadata filtering is the #1 differentiator).
- [[Reference - Memory Math for Transformers]] — the bytes-per-element discipline behind the memory table in #5 (domain: hardware & systems).
- [[Gotchas - RAG Pipelines]] — the layer above this one; index bugs here surface as retrieval failures there, so debug them together.

## Sources
- Malkov & Yashunin (2016/2018) — *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs.* The HNSW construction and search that gotchas #1, #2, #4, #5 all trace back to.
- Jégou, Douze & Schmid (2011) — *Product Quantization for Nearest Neighbor Search.* The compression basis for FAISS's memory story and #5's rescore trick.
- Subramanya et al. (2019) — *DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node.* SSD-resident serving; FreshDiskANN adds streaming updates.
- Patel et al. (2024) — *ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data.* Predicate-agnostic filtered traversal addressing gotcha #1.
- Aumüller, Bernhardsson & Faithfull (2020) — *ANN-Benchmarks: A benchmarking tool for approximate nearest neighbor algorithms.* The public benchmarks whose numbers don't transfer (gotcha #6).
