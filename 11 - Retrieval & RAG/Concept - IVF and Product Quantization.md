---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [IVF, PQ, IVFPQ, inverted file index, product quantization]
summary: "Cluster-and-compress ANN: IVF prunes the search to nearby cells, PQ shrinks each vector to a handful of bytes — FAISS's billion-scale workhorse."
---
> **One-paragraph hook:** Where [[Concept - HNSW]] buys speed with a RAM-hungry graph, IVF and Product Quantization (PQ) buy it by literally throwing away precision: partition the space so you only scan a fraction of it, then compress every stored vector down to a handful of bytes. Combined as IVFPQ, this is the index family that lets FAISS serve billion-vector [[Concept - Semantic Search|semantic search]] out of tens of gigabytes of RAM instead of hundreds — at the cost of a real, measurable recall hit that HNSW mostly avoids.

## The mechanism

**IVF (inverted file index)** partitions the vector space with the same [[Concept - Clustering and Dimensionality Reduction|$k$-means]] used across classical ML into `nlist` centroids (typically thousands to tens of thousands), assigning every vector to its nearest centroid's bucket — a Voronoi cell. At query time you don't scan all $N$ vectors: you compute distance to the `nlist` centroids, pick the `nprobe` nearest cells, and scan only the inverted lists belonging to those cells. `nprobe` is the direct recall/speed knob — probe more cells and you catch vectors that landed in a neighboring cell near the true boundary, at proportionally more scan cost.

**Product Quantization** (Jegou, Douze & Schmid, 2011) compresses each vector independently of IVF. Split a $d$-dimensional vector into $m$ subvectors of $d/m$ dimensions each. Run $k$-means separately within each of the $m$ subspaces with $k^*=256$ centroids, so each subvector can be replaced by a single byte — the ID of its nearest subspace centroid. A 768-dimensional vector with $m=96$ (8 dims per subvector) compresses to 96 bytes, versus $768 \times 4\text{B} = 3072$ bytes raw — a **32x** cut, and the whole reason PQ exists.

Distances against compressed vectors are computed via **Asymmetric Distance Computation (ADC)**: at query time, precompute a table of the query's distance to all 256 centroids in each of the $m$ subspaces ($m \times 256$ table entries, cheap), then approximate the full distance to any stored code by summing the appropriate table entry per subvector — no decompression of the stored codes required, just $m$ table lookups and a sum.

$$\hat{d}(q, x) = \sum_{j=1}^{m} \lVert q_j - c_{j}(x_j) \rVert^2$$

where $c_j(x_j)$ is the centroid assigned to the $j$-th subvector of $x$. This is the query encoded exactly ("asymmetric") against a codebook-quantized document — quantizing only the document side keeps more precision than quantizing both. ADC's table-lookup-and-sum is a compressed stand-in for the [[Concept - Matrix Multiplication as the Atom of Deep Learning|dot products]] that exact search would otherwise compute directly.

**OPQ (optimized PQ)** learns an orthogonal rotation matrix applied to vectors before splitting them into subvectors, so variance is balanced and decorrelated across the $m$ chunks rather than concentrated in a few. Plain PQ implicitly assumes each subspace carries roughly equal, independent variance — real embedding dimensions rarely satisfy that — so OPQ's learned rotation measurably improves the quality of the 256-centroid codebooks per subspace.

**IVFPQ** combines both: `nprobe` cells prune the candidate set, and within those cells PQ compresses the **residual** — the vector minus its assigned IVF centroid — rather than the raw vector. The residual has much smaller dynamic range than the raw vector (the coarse centroid already explains most of the magnitude), so PQ's fixed 256-centroid budget per subspace resolves it far more precisely than it would resolve the raw vector directly. This residual-encoding trick, not the IVF pruning or the PQ compression alone, is what makes IVFPQ recall-competitive at its compression ratio.

```
Index build:
  vectors --k-means(nlist)--> IVF cells (coarse)
  residual = vector - assigned_centroid
  residual --split m subvectors--k-means(256) each--> PQ codes (m bytes)

Query:
  query --distance to nlist centroids--> pick nprobe nearest cells
  query --build ADC table (m x 256)--> scan PQ codes in those cells only
  optional: exact-rescore top candidates with full-precision vectors
```

A common precision-recovery pattern is a **two-stage rerank**: use the cheap ADC pass over PQ codes to produce a shortlist, then rescore that shortlist with exact float distances (from cached or refetched full-precision vectors) to recover the precision PQ's compression lost.

## In practice

FAISS's `IndexIVFPQ` is the reference implementation and the workhorse behind most billion-scale ANN deployments; a common sizing rule of thumb is `nlist` on the order of $\sqrt{N}$ to $4\sqrt{N}$, with `nprobe` swept from single digits up to a few hundred depending on the recall target. $m$ must divide $d$ evenly — 8, 16, 32, 64, or 96 are common choices for typical embedding dimensions. Training the 256-centroid codebooks per subspace needs a reasonably large training sample (a codebook trained on too few points per centroid produces poor quantization, degrading recall independent of query-time tuning) — the same shape-times-bytes-per-element budgeting discipline from [[Reference - Memory Math for Transformers]] applies directly to sizing `nlist`, `m`, and the resulting codes. Against HNSW's roughly 1.5–2x memory overhead over raw vectors, IVFPQ routinely runs at a fraction of raw-vector size — the tradeoff is that PQ gives up recall per byte that HNSW's graph structure preserves, so the choice between them (cataloged with the rest of the field in [[Reference - Vector Database Landscape]]) is really a recall-per-RAM-dollar decision, not a strictly-better-index decision. Past a certain scale even IVFPQ's RAM footprint stops fitting the budget, which is the point where [[Breakdown - DiskANN]]'s disk-resident design or simpler [[Concept - Embedding Quantization|scalar/binary quantization]] become the next lever to pull.

## Failure modes

- **Recall silently lower than benchmarked**: PQ's per-subspace $k$-means assumes roughly isotropic variance; skewed or correlated embedding dimensions violate that and cost real recall until OPQ's rotation corrects it. Detect by comparing IVFPQ recall@k against exact brute-force search on a held-out set, not against a public ANN benchmark's numbers.
- **`nprobe` too low near cell boundaries**: vectors that land just across a Voronoi boundary from the query's nearest cell get missed if the boundary-adjacent cell isn't probed — a structural recall loss that doesn't show up as an obvious error, just a lower hit rate on borderline queries.
- **Bad `nlist` choice**: too small and each inverted list is nearly the whole corpus (little pruning benefit); too large and $k$-means quality degrades with uneven, sparse cells and query-time centroid-distance computation itself becomes the bottleneck.
- **Stale centroids under distribution drift**: IVF's coarse partition and PQ's codebooks are trained once on a snapshot of the data; if the embedding distribution shifts (new content type, new embedding model version), the trained clusters stop matching the actual data and recall degrades gradually — fix with periodic retraining, not just re-indexing.
- **Undertrained codebooks**: training PQ's 256-centroid-per-subspace codebooks on too few vectors yields codebooks that don't actually span the subspace's real variance — a common mistake when prototyping on a small sample before scaling to the full corpus.

## The non-obvious

The residual-encoding step inside IVFPQ is easy to skip mentally — "IVF prunes, then PQ compresses" sounds like two independent stages bolted together — but it's the single biggest lever over naively running flat PQ on raw vectors. By subtracting the assigned centroid first, IVFPQ hands PQ a residual with far smaller dynamic range to encode, and PQ's fixed 256-centroid-per-subspace budget goes proportionally further on a tighter distribution. Skip the residual (quantize raw vectors directly, ignoring the IVF assignment) and you get materially worse recall at the identical byte budget — the compression ratio doesn't change, but the information each byte carries does. This is also why OPQ's rotation is *learned* rather than random: a random rotation decorrelates axes somewhat, but a learned one specifically equalizes variance across the $m$ chunks, which matters precisely because each chunk gets an identical, fixed 256-centroid budget regardless of how much real variance it holds.

## Connections

- [[Concept - HNSW]] — the graph-based alternative; higher recall per byte at the cost of RAM-heavy graph overhead and no compression by default.
- [[Breakdown - DiskANN]] — blends graph search with disk residency and PQ-in-RAM shortlisting, taking ideas from both HNSW and this note.
- [[Concept - Embedding Quantization]] — the simpler scalar/binary compression family PQ generalizes beyond; often layered with PQ for extra compression.
- [[Concept - Semantic Search]] — IVFPQ is one concrete implementation of the ANN step that makes dense retrieval fast at scale.
- [[Reference - Vector Database Landscape]] — where IVF/PQ tuning knobs are actually exposed (or hidden) across production vector databases.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — ADC's table-lookup-and-sum distance approximation is a compressed stand-in for the dot products that power exact search.
- [[Reference - Memory Math for Transformers]] — the same byte-accounting discipline (shape times bytes-per-element) applies directly to sizing a PQ codebook and codes.
- [[Concept - Clustering and Dimensionality Reduction]] — the $k$-means machinery both IVF's coarse partition and PQ's per-subspace codebooks are built from.

## Sources

- Jegou, Douze & Schmid (2011) — Product Quantization for Nearest Neighbor Search. The original PQ paper and the source of the asymmetric distance computation.
- Johnson, Douze & Jegou — FAISS, the library that made IVFPQ the de facto billion-scale ANN workhorse in production.
