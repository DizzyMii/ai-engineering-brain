---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [Hierarchical Navigable Small World, HNSW graph]
summary: "The layered proximity-graph ANN index that turns nearest-neighbor search into O(log N) greedy hops — the default in-memory vector index."
---
> **One-paragraph hook:** HNSW (Hierarchical Navigable Small World) is the ANN index almost every vector database uses by default. FAISS, Qdrant, Weaviate, Milvus and Lucene-based [[Concept - Semantic Search|semantic search]] engines all run it under the hood. It swaps brute-force $O(N)$ scanning for a layered graph you walk greedily, so million- and billion-vector search becomes a latency problem measured in single-digit milliseconds. The price: it's entirely RAM-bound, and it has a real, tunable recall ceiling instead of an exact answer.

## The mechanism

HNSW (Malkov & Yashunin, 2016/2018) builds a multi-layer graph over the vectors. Layer 0 holds every node, and each higher layer holds an exponentially shrinking random subset. It's the skip-list trick applied to a proximity graph instead of a sorted list. On insert, a node's maximum layer is drawn as

$$\ell = \lfloor -\ln(U(0,1)) \cdot m_L \rfloor, \quad m_L = \frac{1}{\ln(M)}$$

where $U(0,1)$ is uniform and $M$ is the target node degree. Each layer ends up roughly $1/M$ the size of the one below, so the top layers are sparse "express lanes" and the bottom layer is the dense full graph.

Search starts at a fixed entry point in the top layer and does a **greedy nearest-neighbor walk**. At each step it moves to whichever neighbor of the current node is closer to the query, until no neighbor improves. Then it drops a layer and repeats from that local optimum. Only at layer 0 does the walk widen into a **beam search** with candidate-list size `ef_search`: keep the `ef_search` best candidates seen so far and expand their neighbors until nothing closer turns up. Each layer roughly halves (or `1/M`s) the effective search radius before handing a good starting point down, so empirical hop count grows close to $O(\log N)$ instead of linearly. That's the whole payoff of the hierarchy.

Construction reuses the same greedy search to find a new node's entry candidates at every layer up to its assigned $\ell$, then picks up to $M$ edges from a candidate list of size `ef_construction`. Edge selection is **not** "keep the $M$ closest candidates." Malkov & Yashunin's heuristic prefers a diverse spread of neighbors over the naive closest set. A graph built from pure nearest-neighbor edges clumps into tight local cliques and loses the long-range connectivity that lets greedy descent converge in log-ish hops without getting stuck in a local basin.

```
Layer 2:        A ─────────────── E                (sparse, long-range)
                 │                 │
Layer 1:    A ── C ──── D ──── E ── F               (medium density)
             │    │      │      │    │
Layer 0:  A─B─C─D─E─F─G─H─I─J─K─L─M─N─O─P            (every node, dense)

search: greedy descent from entry point at top layer,
        widen to beam width ef_search only at layer 0
```

Memory per vector is roughly $d \cdot 4$ bytes for the raw float32 vector plus about $M \cdot 2 \cdot 8$ bytes of edges (each node keeps up to $M$ neighbor IDs at layer 0, doubled to cover bidirectional adjacency plus upper-layer edges). In practice the graph overhead runs **1.5–2x** the size of the raw vectors. That makes HNSW memory-hungry more than compute-hungry: the whole index has to stay resident in host RAM for the graph walk to stay fast, unlike a GPU kernel's working set in the [[Concept - GPU Memory Hierarchy]].

The "closer" the greedy walk chases at each hop is whatever [[Concept - Vector Norms and Distances|distance or similarity function]] the index was built with: cosine, dot product or Euclidean. HNSW doesn't care which, as long as build time and query time use the same one.

## In practice

Three knobs set the recall/latency/memory tradeoff. `M` (16–64): more edges, better recall, more RAM. `ef_construction` (100–500): a more thorough build-time search for good edges, costing only build time. `ef_search`: the one knob you tune at query time, trading latency for recall on every query. A typical default is `M=16`, `ef_construction=200`. Production systems tune `ef_search` per workload by sweeping it against a labeled recall@k set. Recall commonly lands in the 0.95–0.99 range at reasonable `ef_search`, but the curve isn't linear. Push `ef_search` too low and recall falls off a cliff (see [[Gotchas - Vector Index Tuning]]).

Concretely, 10M vectors at 768 dimensions is $10^7 \times 768 \times 4\text{B} \approx 30.7\text{GB}$ of raw vectors. With 1.5–2x graph overhead the resident index needs on the order of 45–60GB of RAM before it serves a single query. That's the number that becomes a fire drill in [[Reference - Memory Math for Transformers|memory-budgeting exercises]] once someone tries to 10x a corpus. hnswlib is the reference implementation, written by the paper's own author. FAISS, Qdrant, Weaviate, Milvus and Elasticsearch/OpenSearch's Lucene HNSW all ship production variants, cataloged in [[Reference - Vector Database Landscape]].

HNSW supports incremental inserts natively (NSW was designed as an online structure). Deletes are second-class. Removing a node means a tombstone (filtered at query time, edges left dangling) or an expensive local repair, so update-heavy workloads accumulate graph rot and need periodic full rebuilds.

When RAM is the limit and recall isn't, the alternative is the cluster-and-compress family, [[Concept - IVF and Product Quantization]]. It gives up some recall per byte for an order-of-magnitude smaller footprint. Neither index is strictly better; you're buying recall per RAM dollar.

## Failure modes

- **The recall cliff.** Set `ef_search` too low and recall drops sharply below some workload-dependent threshold instead of degrading gracefully. Sweep `ef_search` against a labeled query set before trusting a default. "The library's default is fine" is a common and expensive assumption.
- **Filtered search returns too few or wrong results.** Metadata pre-filtering removes graph nodes before traversal and can cut the connectivity the greedy walk needs, so valid candidates become unreachable even though they pass the filter. Post-filtering (over-fetch, then discard) avoids this at the cost of wasted work. Filterable-HNSW variants and ACORN-style approaches fix it at the graph level. Full pathology in [[Gotchas - Vector Index Tuning]].
- **Memory blowup at scale.** The 1.5–2x graph overhead is easy to forget when budgeting for corpus growth, and it shows up as an OOM at 3am instead of a planning line item. Quantize stored vectors (see [[Concept - Embedding Quantization]]) or move to a disk-resident index (see [[Breakdown - DiskANN]]) once RAM stops being cheap enough.
- **Delete-heavy degradation.** Tombstones from frequent deletes rot graph connectivity over time and drag down recall and latency without any alert. Schedule full rebuilds and monitor the deleted ratio.
- **Distance-metric mismatch.** An index built for cosine similarity but fed unnormalized vectors (or the reverse) yields a graph that's internally consistent and ranks wrong. No error, just bad relevance.

## The non-obvious

The heuristic edge-selection rule, preferring diverse neighbors over the naive $M$ closest, is what makes HNSW work at all. A graph built only from nearest-neighbor edges degenerates into tight cliques: accurate locally, disconnected globally, and greedy search gets trapped in local optima with no way out. Think of a highway system built only from the shortest local roads; you'd never get across the country. Keeping some farther, well-spread neighbors preserves the small-world shortcuts that let a greedy walk converge in a handful of hops from anywhere to anywhere. People who reimplement HNSW from the paper's pseudocode and skip this heuristic (using plain top-$M$ selection) get an index that looks fine but has collapsed recall on any corpus with real geometric structure. It never throws an exception. It just retrieves worse neighbors.

## Connections

- [[Concept - IVF and Product Quantization]] — the cluster-and-compress alternative family; trades HNSW's RAM-heavy high recall for far smaller footprint at lower recall per byte.
- [[Breakdown - DiskANN]] — the answer once the vector set stops fitting in RAM at all; keeps a Vamana graph on SSD instead.
- [[Gotchas - Vector Index Tuning]] — the full catalogue of the filtered-search and recall-cliff failures this note only introduces.
- [[Concept - Semantic Search]] — HNSW is the ANN engine that makes dense semantic search fast past brute-force scale.
- [[Reference - Vector Database Landscape]] — which production vector databases ship HNSW and how they expose its tuning knobs.
- [[Concept - GPU Memory Hierarchy]] — the same "fast-tier capacity is the bottleneck" tradeoff shows up between host RAM and disk here as between SRAM and HBM there.
- [[Reference - Memory Math for Transformers]] — the same discipline of turning a shape into a byte count applies directly to index sizing.
- [[Concept - Embedding Quantization]] — the standard fix for HNSW's RAM hunger: shrink what each node stores.
- [[Concept - Vector Norms and Distances]] — the distance/similarity functions the greedy graph walk is actually comparing.

## Sources

- Malkov & Yashunin (2016; journal version 2018) — Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs. The original HNSW paper and the source of the heuristic edge-selection rule.
