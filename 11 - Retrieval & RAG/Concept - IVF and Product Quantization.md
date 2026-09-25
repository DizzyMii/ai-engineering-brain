---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [IVF, PQ, IVFPQ, inverted file index, product quantization]
summary: "Cluster-and-compress ANN: IVF prunes the search to nearby cells, PQ shrinks each vector to a handful of bytes — FAISS's billion-scale workhorse."
---
> **One-paragraph hook:** [[Concept - HNSW]] buys speed with a RAM-hungry graph. IVF and Product Quantization (PQ) buy it by throwing away precision: partition the space so you scan only a fraction of it, then compress every stored vector to a handful of bytes. Combined as IVFPQ, this is the index family that lets FAISS serve billion-vector [[Concept - Semantic Search|semantic search]] from tens of gigabytes of RAM instead of hundreds, at the cost of a real, measurable recall hit that HNSW mostly avoids.

## The mechanism

**IVF (inverted file index)** partitions the vector space into `nlist` centroids (typically thousands to tens of thousands) using the same [[Concept - Clustering and Dimensionality Reduction|$k$-means]] found all over classical ML. Each vector goes into its nearest centroid's bucket, a Voronoi cell. At query time you skip scanning all $N$ vectors. You compute distance to the `nlist` centroids, pick the `nprobe` nearest cells, and scan only their inverted lists. `nprobe` is the direct recall/speed knob: probe more cells and you catch vectors that landed in a neighboring cell near the true boundary, for proportionally more scan cost.

**Product Quantization** (Jegou, Douze & Schmid, 2011) compresses each vector, independent of IVF. Split a $d$-dimensional vector into $m$ subvectors of $d/m$ dimensions. Run $k$-means separately in each of the $m$ subspaces with $k^*=256$ centroids, so each subvector becomes one byte, the ID of its nearest subspace centroid. A 768-dimensional vector with $m=96$ (8 dims per subvector) compresses to 96 bytes against $768 \times 4\text{B} = 3072$ bytes raw. That **32x** cut is why PQ exists.

Distances to compressed vectors use **Asymmetric Distance Computation (ADC)**. At query time, precompute the query's distance to all 256 centroids in each of the $m$ subspaces (an $m \times 256$ table, cheap). The distance to any stored code is then approximated by summing one table entry per subvector: $m$ lookups and a sum, no decompression.

$$\hat{d}(q, x) = \sum_{j=1}^{m} \lVert q_j - c_{j}(x_j) \rVert^2$$

Here $c_j(x_j)$ is the centroid assigned to the $j$-th subvector of $x$. The query is used exactly ("asymmetric") against a codebook-quantized document, and quantizing only the document side keeps more precision than quantizing both. ADC's lookup-and-sum is a compressed stand-in for the [[Concept - Matrix Multiplication as the Atom of Deep Learning|dot products]] exact search would compute.

**OPQ (optimized PQ)** learns an orthogonal rotation applied before the split, so variance is balanced and decorrelated across the $m$ chunks instead of piled into a few. Plain PQ implicitly assumes each subspace carries roughly equal, independent variance. Real embedding dimensions rarely do, so OPQ's learned rotation measurably improves the 256-centroid codebooks per subspace.

**IVFPQ** combines the two. `nprobe` cells prune the candidates, and inside those cells PQ compresses the **residual** (the vector minus its assigned IVF centroid), not the raw vector. The coarse centroid already explains most of the magnitude, so the residual has a much smaller dynamic range, and PQ's fixed 256-centroid budget per subspace resolves it far more precisely than it could the raw vector. Residual encoding, more than the IVF pruning or the PQ compression alone, is what makes IVFPQ recall-competitive at its compression ratio.

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

A common way to win back precision is a **two-stage rerank**. The cheap ADC pass over PQ codes produces a shortlist, and exact float distances (from cached or refetched full-precision vectors) rescore it to recover what PQ's compression lost.

## In practice

FAISS's `IndexIVFPQ` is the reference implementation and the workhorse behind most billion-scale ANN deployments. A common rule of thumb puts `nlist` around $\sqrt{N}$ to $4\sqrt{N}$, with `nprobe` swept from single digits to a few hundred depending on the recall target. $m$ must divide $d$ evenly; 8, 16, 32, 64 or 96 are common for typical embedding dimensions. Training the 256-centroid codebooks per subspace needs a reasonably large sample. Too few points per centroid gives poor quantization and lower recall that no query-time tuning fixes. Size `nlist`, `m` and the resulting codes with the same shape-times-bytes-per-element budgeting as [[Reference - Memory Math for Transformers]].

HNSW carries roughly 1.5–2x memory overhead over raw vectors. IVFPQ routinely runs at a fraction of raw-vector size, but PQ gives up recall per byte that HNSW's graph keeps. Choosing between them (the rest of the field is cataloged in [[Reference - Vector Database Landscape]]) comes down to recall per RAM dollar; neither index is strictly better. Past a certain scale even IVFPQ's RAM footprint won't fit, and [[Breakdown - DiskANN]]'s disk-resident design or simpler [[Concept - Embedding Quantization|scalar/binary quantization]] become the next lever.

## Failure modes

- **Recall silently below the benchmark.** PQ's per-subspace $k$-means assumes roughly isotropic variance. Skewed or correlated embedding dimensions break that and cost recall until OPQ's rotation corrects it. Detect by comparing IVFPQ recall@k with exact brute-force search on a held-out set, not with a public ANN benchmark's numbers.
- **`nprobe` too low near cell boundaries.** Vectors just across a Voronoi boundary from the query's nearest cell get missed if that neighboring cell isn't probed. There's no obvious error, only a lower hit rate on borderline queries.
- **Bad `nlist`.** Too small and each inverted list is nearly the whole corpus, so pruning buys little. Too large and $k$-means produces uneven, sparse cells, and computing query-to-centroid distances becomes the bottleneck itself.
- **Stale centroids under distribution drift.** IVF's coarse partition and PQ's codebooks are trained once on a snapshot. If the embedding distribution shifts (new content type, new embedding model version), the clusters stop matching the data and recall degrades gradually. Retrain periodically; re-indexing alone won't fix it.
- **Undertrained codebooks.** Training PQ's 256-centroid-per-subspace codebooks on too few vectors gives codebooks that don't span the subspace's real variance. It's a common mistake when prototyping on a small sample before scaling to the full corpus.

## The non-obvious

The residual-encoding step is easy to skip past mentally. "IVF prunes, then PQ compresses" sounds like two independent stages bolted together, but the residual is the biggest single gain over running flat PQ on raw vectors. Subtracting the assigned centroid first hands PQ a residual with far smaller dynamic range, and the fixed 256-centroid-per-subspace budget goes further on a tighter distribution. Skip it (quantize raw vectors, ignoring the IVF assignment) and recall is materially worse at the identical byte budget. The compression ratio is the same; what each byte carries isn't. The same logic explains why OPQ's rotation is *learned* and not random. A random rotation decorrelates axes somewhat, but a learned one equalizes variance across the $m$ chunks, which matters because each chunk gets the same fixed 256-centroid budget however much variance it holds.

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
