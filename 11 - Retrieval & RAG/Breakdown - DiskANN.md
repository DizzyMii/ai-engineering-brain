---
tags: [breakdown, domain/retrieval-rag, level/unicorn]
aliases: [Vamana, FreshDiskANN, SSD-based ANN, DiskANN]
summary: "Microsoft's SSD-resident ANN index (the Vamana graph) that serves billion-scale nearest-neighbor search from disk on a single node with tens of GB of RAM."
---

# Breakdown - DiskANN
> DiskANN (Subramanya et al. 2019, NeurIPS; Microsoft Research India) is the index you reach for when your vectors no longer fit in RAM. In-memory graph indexes like HNSW keep every vector *and* the graph resident in memory; for a billion 768-dimensional `float32` vectors that is ~3 TB of raw vectors before the graph overhead, which prices most teams out of billion-scale search. DiskANN puts the full-precision vectors and adjacency lists on an SSD, keeps only compressed codes in RAM, and still answers queries at single-digit-millisecond latency with 95%+ recall — turning "you need a rack of high-memory machines" into "you need one box with an NVMe drive." It is the quiet workhorse behind Azure AI Search's vector tier and is embedded in Milvus and Weaviate (see [[Reference - Vector Database Landscape]]), serving the same dense [[Concept - Semantic Search|nearest-neighbor search]] as an in-memory index but at a scale in-memory indexes can't reach.

## The headline numbers

- **Scale on one node:** the original paper indexed a **billion points on a single machine with 64 GB of RAM**, versus the estimated ~5 TB of DRAM an in-memory graph would need for the same set — roughly a **10× cost reduction** for billion-scale search (Subramanya et al. 2019).
- **Latency / recall:** ~5 ms mean query latency at **~95% [email protected]**, achieved with only about **5 SSD reads per query** thanks to a low-diameter graph (paper-reported).
- **Memory split for a billion 768-d vectors:** raw [[Concept - Floating Point for Deep Learning|fp32]] vectors are ~3 TB (`1e9 × 768 × 4 B`) and live on SSD; PQ codes at ~96 bytes/vector are ~96 GB (or tens of GB with more aggressive PQ) and live in RAM. The graph adjacency also lives on SSD, co-located with the vectors.
- **Per-hop cost:** each graph hop that misses the RAM cache is one random NVMe read, ~**100 µs** — three orders of magnitude slower than a DRAM access, which is the entire reason the algorithm is shaped the way it is.

## How it actually works

DiskANN has three pieces: the **Vamana** graph-construction algorithm, the **RAM/SSD split**, and **beam search** over disk.

**Vamana graph.** Unlike [[Concept - HNSW|HNSW]]'s multi-layer hierarchy, Vamana builds a *single flat* directed graph. Construction visits each point, runs a greedy search from the current graph to find its candidate neighbors, then prunes the candidate set with **RobustPrune** governed by a parameter **α ≥ 1**. The prune rule keeps an edge to a point `p` unless an already-selected, closer neighbor `q` "covers" it, i.e. `α · dist(q, p) ≤ dist(source, p)`. With `α = 1` this is ordinary nearest-neighbor pruning; with `α > 1` (typically **1.2**) the rule is *stricter about discarding long edges*, so it deliberately keeps some long-range "highway" edges. The build runs two passes (α = 1, then α = 1.2). The result is a higher-average-degree graph with **low diameter** — any node reaches any other in few hops.

Why sacrifice memory for graph density? Because on disk the bottleneck is **hops, not edges**. In an in-memory index every extra edge costs RAM and every hop is nearly free, so you minimize degree. On DiskANN every hop is a ~100 µs random read, so you minimize *diameter* even at the cost of a fatter graph — the exact inversion of the in-memory intuition.

**The RAM/SSD split** applies the same latency-tiering logic as the [[Concept - GPU Memory Hierarchy|memory hierarchy]] that governs GPU kernels (fast-small vs slow-large):

```
        RAM (tens of GB, fast)                 SSD / NVMe (TB, slow, cheap)
   ┌───────────────────────────────┐     ┌───────────────────────────────────┐
   │  PQ codes for ALL vectors      │     │  full-precision fp32 vectors       │
   │  (approx distances, ~96 B/vec) │     │  + adjacency list, CO-LOCATED in   │
   │  hot-node graph cache          │◄───►│  one sector-aligned block per node │
   └───────────────────────────────┘     └───────────────────────────────────┘
          navigate approximately              1 random read fetches a node's
          (cheap, in-memory)                  full vector AND its neighbors
```

The layout decision is load-bearing: each node's full vector and its edge list are packed into **one 4 KB block**, so a single random read yields both the data needed to rescore that node *and* the pointers to expand it — one I/O per hop, not two.

**Beam search.** The query walks the graph greedily, but maintains a **beam** of width `W` unexpanded frontier nodes and issues their SSD reads **in parallel** (batched I/O), amortizing the ~100 µs latency across the NVMe device's queue depth. Candidate ranking during the walk uses the **PQ codes in RAM** (see [[Concept - IVF and Product Quantization|product quantization]]) for cheap approximate distances — the per-hop distance is a [[Concept - Matrix Multiplication as the Atom of Deep Learning|dot product]], just over compressed codes instead of full vectors; only the final shortlist is **re-ranked with the full-precision on-disk vectors** to recover exact ordering — the same navigate-approximate / rank-exact pattern as [[Concept - Embedding Quantization|quantize-then-rescore]].

**FreshDiskANN** (Singh et al. 2021) removes the static-index limitation: inserts land in a small in-memory delta index, deletes are tracked in a delete-list, and a periodic **StreamingMerge** consolidates the delta into the on-disk long-term index — so the index accepts streaming updates without a full rebuild per write.

## The clever parts

1. **α-pruning (RobustPrune with α > 1).** The crux. It buys a low-diameter graph by keeping long "highway" edges, minimizing the number of disk hops — because when your per-hop cost is a random SSD read, hop count dominates everything else. This is the insight that made SSD-resident graph search viable.
2. **Co-locating vector + adjacency in one block.** A pure systems decision that halves I/O per hop (one read instead of two). The algorithm and the on-disk layout are co-designed.
3. **Two-tier precision: PQ in RAM, full vectors on disk.** Navigate on lossy compressed codes that fit in memory; rescore the shortlist against exact vectors on disk. You pay disk latency only for the handful of nodes that make the final cut.
4. **Beam-width batched I/O.** Turns a latency-bound sequence of dependent random reads into a throughput-bound batch that exploits NVMe parallelism — the difference between a device queue depth of 1 and 32.
5. **FreshDiskANN's delta-merge.** Decouples cheap online inserts from the expensive multi-pass graph build, so the index is mutable without a rebuild on every write.

## What it got wrong / what's dated

- **NVMe or nothing.** The whole design assumes ~100 µs random reads. On a spinning HDD (seek in the ~10 ms range) beam search collapses; DiskANN is an artifact of the NVMe era, not disk in general.
- **Build cost is real.** The multi-pass Vamana construction over the full set is expensive in time and compute; (re)building a billion-scale index is not a cheap operation, which is precisely what FreshDiskANN's streaming updates paper over rather than eliminate.
- **Deletes still accumulate.** FreshDiskANN's delta grows and the delete-list must eventually be merged out; you have deferred the rebuild, not abolished it — the same tombstone-degradation story that dogs [[Concept - HNSW|HNSW]] (see [[Gotchas - Vector Index Tuning]]).
- **PQ sets a recall ceiling during navigation.** If the compressed-code distances are too distorted, the walk can miss the true neighborhood before rescore ever sees it; the shortlist must be wide enough to catch it.
- **The GPU era moved the frontier.** GPU graph indexes (e.g. CAGRA in Milvus) push billion-scale in-memory throughput far past DiskANN's QPS. DiskANN's enduring niche is **cost per vector**, not peak queries per second — it wins when the alternative is buying terabytes of DRAM.

## What to steal

- **Precision-tiering as a design principle.** Keep a cheap, lossy representation hot in fast memory for navigation and the exact representation in slow, cheap storage for final scoring. This generalizes far beyond ANN — it is the same shape as the [[Reference - Memory Math for Transformers|memory-budget math]] behind KV-cache offloading.
- **Optimize for the actual bottleneck's cost model.** When per-hop I/O latency dominates, minimize graph *diameter*, not edge count — even if that means spending memory. The right objective flips with the storage tier.
- **Batch your random reads** to the device's parallelism (beam width ↔ NVMe queue depth) to convert latency-bound access into throughput-bound access.

## Connections

- [[Concept - HNSW]] — the in-memory graph index DiskANN replaces when vectors won't fit in RAM; same greedy-graph-search family, opposite memory strategy.
- [[Concept - IVF and Product Quantization]] — supplies the PQ codes DiskANN keeps in RAM for approximate navigation.
- [[Concept - Embedding Quantization]] — the navigate-approximate / rescore-exact pattern DiskANN uses internally is the same two-stage recovery used for embedding compression.
- [[Reference - Vector Database Landscape]] — where DiskANN actually ships (Azure AI Search, Milvus, Weaviate) and how it compares on scale and cost.
- [[Concept - GPU Memory Hierarchy]] — the RAM-vs-SSD latency tiering is the same fast-small / slow-large hierarchy that shapes GPU kernels (cross-domain: hardware).
- [[Reference - Memory Math for Transformers]] — the byte-budget arithmetic that decides when raw vectors overflow RAM and disk residency becomes mandatory (cross-domain: hardware).
- [[Concept - Semantic Search]] — the dense retrieval workload DiskANN serves at billion scale.
- [[Gotchas - Vector Index Tuning]] — delete accumulation, recall cliffs, and the benchmark-vs-production gap all apply to DiskANN too.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the distance computations at every hop are dot products; their cost model drives the PQ-vs-exact split (cross-domain: foundations).
- [[Concept - Floating Point for Deep Learning]] — why full-precision fp32 vectors are 4 bytes/dim and therefore what pushes them off RAM and onto disk (cross-domain: foundations).

## Sources

- Subramanya, Devvrit, Kadekodi, Krishnaswamy, Simhadri (2019) — *DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node*, NeurIPS. Introduces Vamana and the SSD-resident design; the billion-point / 64 GB / ~95% recall result.
- Singh et al. (2021) — *FreshDiskANN: A Fast and Accurate Graph-Based ANN Index for Streaming Similarity Search*. Adds streaming inserts/deletes via an in-memory delta and periodic merge.
- Jégou, Douze, Schmid (2011) — *Product Quantization for Nearest Neighbor Search*. The PQ compression DiskANN keeps in RAM for navigation.
