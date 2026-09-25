---
tags: [gotchas, domain/retrieval-rag, level/unicorn]
aliases: [ANN index tuning, HNSW tuning, filtered vector search, vector index pitfalls]
summary: "Production ANN failures: filtered-search disconnection, recall cliffs, delete rot, metric mismatch, memory blowup, and benchmark lies."
---

# Gotchas - Vector Index Tuning

The vector index is the part of a RAG stack that looks fine in the demo, passes its unit tests, and then returns the wrong three chunks in production. Approximate nearest-neighbor (ANN) indexes trade exactness for speed, and every knob in that trade has a failure mode that only shows up under real data, real filters and real update traffic. Ordered by how often they cost someone a week.

---

## 1. Filtered search silently craters recall as the filter gets selective

**Symptom:** a query with a metadata filter (`tenant_id = X`, `date > 2024`, `lang = "de"`) returns 2 results when it should return 10, or returns worse hits than the same query unfiltered. Unfiltered queries look perfect, so nobody suspects the index; recall collapses only on the tenants or categories that match few documents.

**Cause:** this is the most underestimated production issue in vector search, and it follows directly from how [[Concept - HNSW]] works. Greedy graph search starts at a fixed entry point in the top layer and walks down toward the query. **Pre-filtering** (only traversing nodes that pass the predicate) disconnects the graph. If the entry point and the bridge nodes on the path to the answer all fail the filter, the walk can't reach the surviving candidates, though they're in the index. The more selective the filter, the worse the connectivity, so recall degrades *non-linearly* toward zero right when the filter keeps only 1–5% of the corpus. **Post-filtering** (fetch top-k by vector score, drop non-matching rows) fails the other way: if 2% of docs match, a top-100 retrieval leaves ~2 survivors, and your effective `k` collapses without warning.

**Fix**, roughly in order of preference:
- **Filterable / filter-aware HNSW.** [[Reference - Vector Database Landscape|Qdrant]] builds extra payload-conditioned links so the graph stays connected within a filtered subset. It's Qdrant's strongest differentiator. Weaviate and pgvector have their own filter integration paths.
- **ACORN-style predicate-agnostic traversal** (Patel et al. 2024): widen neighbor exploration in proportion to filter selectivity, so the walk visits enough nodes to route around filtered-out bridges.
- **Brute-force fallback below a cardinality threshold.** Below some matching-set size, an exact scan of the surviving rows is faster *and* correct. Qdrant does this automatically. For highly selective filters it's the honest answer.
- **Over-fetch, then post-filter**, as a crude fallback: raise `ef_search`/`k` by roughly the inverse of the filter selectivity. Wasteful, but it works when you can't change the engine.
- [[Concept - IVF and Product Quantization|IVF]]-with-filter degrades more gracefully than naive pre-filtered HNSW. Scanning an inverted list and applying a predicate is linear; there's no graph walk to strand you.

**Detection:** plot recall@k against filter selectivity on a labeled set. A healthy system is roughly flat; a broken one craters as the filter tightens. Benchmark only unfiltered queries, as nearly everyone does, and you'll find out when a customer with a narrow tenant complains.

---

## 2. The `ef_search` recall cliff: "defaults are fine" is a lie

**Symptom:** recall sits at 0.999 on your test set, then a slightly different query distribution or a bigger corpus drops it to 0.85 with no code change. Or you copied `ef_search=64` from a README and never questioned it.

**Cause:** `ef_search` is HNSW's query-time beam width, the size of the candidate priority queue during the greedy walk. Recall as a function of `ef_search` is **not linear and not concave everywhere**. It rises steeply, saturates, and *below a corpus-dependent threshold drops off a cliff* instead of degrading gracefully. The threshold moves with corpus size, intrinsic dimensionality and `M` (graph degree). A value that gives 0.99 recall at 1M vectors can give 0.9 at 10M, because the graph is deeper and the beam is now too narrow to escape local minima.

**Fix:** sweep `ef_search` against measured recall on a labeled query set and pick the value that hits your target (say 0.97) with margin, *at production scale*, not prototype scale. `ef_search` is the one true runtime knob. It trades recall against latency continuously, and unlike `M` and `ef_construction` you can change it per query without a rebuild. It should come out of a measurement, never a copied constant.

**Detection:** a recall-vs-`ef_search` curve and a recall-vs-latency curve on your data. Without a labeled recall set for your own corpus you're flying blind; public numbers don't transfer (see #6).

---

## 3. Distance-metric mismatch produces confidently wrong rankings

**Symptom:** retrieval is mediocre for no visible reason. Nearest neighbors are "kind of related" but never the obvious best match. No errors, no warnings, just a persistently bad top-k.

**Cause:** the index was built for one metric and the embedding model expects another. The classic case is an index configured for **L2 (Euclidean)** distance over embeddings trained for **cosine** similarity and never L2-normalized. For normalized vectors, L2 and cosine rank identically ($\lVert q-d\rVert^2 = 2 - 2\,q\!\cdot\!d$ when $\lVert q\rVert=\lVert d\rVert=1$), so normalization hides the bug in tests. Feed it unnormalized vectors and magnitude starts leaking document length into the ranking. The mirror-image mistake is an **inner-product** index on unnormalized vectors labeled "cosine," which rewards long documents for being long.

**Fix:** match the metric to the model card. If it says cosine, L2-normalize every vector at index and query time and use inner product, which then equals cosine and is cheaper than an explicit norm in the hot loop. After any embedding-model or index-config change, check a handful of known query→answer pairs by hand; this bug hides behind plausible results.

**Detection:** compute exact brute-force top-k for a sample of queries and compare with the index's top-k. Disagreement beyond expected ANN approximation error means a metric or normalization mismatch, not a recall problem.

---

## 4. Delete degradation: tombstones rot the graph

**Symptom:** a long-lived, update-heavy index loses recall and gains tail latency over weeks with no config change. Rebuilding from scratch "fixes it," and nobody can say why.

**Cause:** HNSW has no true delete. Removing a vector marks it as a **tombstone**: the node stays in the graph as a routing waypoint and is filtered out of results. As tombstones pile up (a document store with churn, or a reindexing pipeline that deletes then inserts), the graph fills with dead nodes that search still visits. Connectivity between live nodes degrades, `ef_search` spends its beam on tombstones, and recall and latency both drift. Re-embedding a modified doc is internally a delete + insert, so "we just update docs" turns out to be a tombstone factory.

**Fix:** schedule periodic full rebuilds (or segment compaction/merge in Lucene-based engines like Elasticsearch/OpenSearch, which gets the same effect by merging away deleted docs). Monitor the deleted-to-live ratio and rebuild before it passes ~20–30%. For streaming workloads where rebuilds hurt, use a design built for it: [[Breakdown - DiskANN|FreshDiskANN]] merges an in-memory delta into the on-disk index instead of rotting in place.

**Detection:** track `deleted_count / total_count` per index (Qdrant exposes vacuuming metrics; Lucene exposes `numDeletedDocs`). A rising ratio with flat or rising p99 latency is the tell.

---

## 5. Memory blowup, and why the "2× raw vectors" folklore is wrong at high dimension

**Symptom:** you sized the box for `N × d × 4` bytes of embeddings and the index OOMs at load. Or you over-provisioned 2× on a high-dimensional corpus and wasted money.

**Cause:** HNSW is an in-memory structure that stores the graph *on top of* the raw vectors. Per vector, the graph adds roughly $M_0 \times 4$ bytes at the base layer, where $M_0 = 2M$ is the max degree at layer 0 and each edge is a 4-byte node id, plus a smaller amount from the exponentially sparser upper layers. The often-repeated "budget ~2× the raw vectors" rule is an **operational safety margin, not the data-structure math**, and it misleads in both directions:

| Case | Raw (fp32) | Graph (M=32, $M_0$=64) | Ratio |
|---|---|---|---|
| d=768 (typical) | 3072 B | ~256 B | **~1.08×** |
| d=384 (MiniLM) | 1536 B | ~256 B | ~1.17× |
| d=128 (low-dim) | 512 B | ~256 B | ~1.5× |

At the common d=768–1536, pure graph overhead is only ~5–15%. The "2×" comes from **operational headroom**: transient double memory during a rebuild, payload/metadata indexes, deletion overhead (#4) and OS page-cache slack. Budget for those, not for a graph that supposedly doubles high-dimensional vectors. ([[Reference - Memory Math for Transformers]] applies the same bytes-per-element discipline to model serving.)

**Fix:** when the raw vectors are the problem, shrink the vectors and leave the graph alone:
- **Compress the vectors.** [[Concept - Embedding Quantization]]: int8 (4× smaller) or binary (32×), with a full-precision rescore of the shortlist, recovers most recall. For RAM-bound HNSW this is the biggest memory lever you have. It's the same recall-vs-precision trade you make for model weights in [[Concept - Post-Training Quantization Formats]], applied to embeddings.
- **Go to disk.** [[Breakdown - DiskANN]] serves billion-scale from SSD with a few GB of RAM (PQ codes in RAM, full vectors on SSD).
- **Plan `M`.** Higher `M` buys recall at linear memory cost. Don't crank it by reflex.

**Detection:** compute the expected footprint before deploying (`N × (d×4 + 2M×4)` for pure HNSW) and compare with RSS after load. A 2× surprise means payload indexes or a rebuild in flight; find out which.

---

## 6. `ann-benchmarks` recall is not your recall

**Symptom:** you picked an index and params off a public leaderboard, they hit 0.99 recall there, and you get 0.9 in production.

**Cause:** public ANN benchmarks (Aumüller et al.'s `ann-benchmarks`; the SIFT1M/GIST/GloVe/DEEP datasets) use **uniformly distributed, static, unfiltered** query sets, which is everything your production workload isn't. Real corpora are skewed and clustered (embedding spaces have hubs), real queries carry metadata filters (#1), and real indexes take live updates (#4). Any one of these shifts the achievable recall-latency frontier. The leaderboard tells you which algorithms are *good*, not what *your* number will be.

**Fix:** benchmark on **your** vectors, **your** filter distribution and **your** update pattern. Build a labeled recall set from real queries (even 200 of them) and measure the frontier you actually run on. Metadata filtering is the number-one differentiator between vector stores, and it's the thing public benchmarks leave out.

**Detection:** if your only recall numbers come from a vendor slide or a public leaderboard, you haven't measured recall. Full stop.

---

## 7. Over-indexing a tiny corpus

**Symptom:** a 30k-chunk knowledge base runs an HNSW index, sometimes returns slightly wrong approximate results, needs tuning, and isn't even faster than the obvious alternative.

**Cause:** ANN is a trade you make only when exact search is too slow. Flat brute force is $O(N \cdot d)$ and **exact**. For 50k × 768-d vectors, one query is ~38M multiply-adds: sub-millisecond on a modern CPU with a BLAS/SIMD dot-product kernel, and trivially GPU-batched. Under roughly 1M vectors, a flat index (FAISS `IndexFlatIP`, pgvector with no index) is frequently faster, with perfect recall and zero tuning. HNSW at 50k vectors gets you approximation error and an `ef_search` knob to babysit, and nothing in return.

**Fix:** know the crossover. Below ~1M vectors, default to exact flat search and revisit only when latency measurements say so. ANN pays for its complexity at scale.

**Detection:** if the corpus fits in a few hundred MB and flat-search p99 is already under budget, deleting the ANN index is a valid optimization.

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
