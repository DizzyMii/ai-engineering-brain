---
tags: [concept, domain/retrieval-rag, level/unicorn]
aliases: [binary embeddings, int8 embeddings, scalar quantization, embedding compression, quantize-and-rescore]
summary: "Compressing embedding vectors to int8 or binary for 4-32x cheaper storage and faster search, with a rescore pass that recovers 95%+ of recall."
---
> **One-paragraph hook:** A million 1024-dimensional [[Concept - Floating Point for Deep Learning|`float32`]] embeddings take 4 GB, and an [[Concept - HNSW|HNSW]] graph roughly doubles that in RAM, so memory, more than compute, is usually what caps a vector index. Embedding quantization turns those 4 GB into 1 GB (int8) or 128 MB (binary) and keeps almost all of the [[Concept - Semantic Search|retrieval]] quality. What makes it work is the *rescore*: a cheap coarse-precision shortlist, then an exact re-ranking of just that shortlist. Get the rescore right and binary embeddings hold ~95% of full-precision recall at 32× less memory. Skip it and binary tanks on the hard queries you care about most.

## The mechanism

Two compression schemes dominate, plus one recovery step that makes them usable.

**Scalar int8.** Map each `float32` dimension onto an 8-bit integer using a per-dimension (or global) min/max range: `q = round((x - min) / (max - min) × 255)`. That's a **4× storage cut** (4 bytes → 1 byte) with only minor recall loss when the calibration ranges are per dimension. The *asymmetric* variant keeps the query in `float32` and quantizes only the stored documents, so the dot product `q · d̂` picks up quantization error on one operand instead of two. Cheap accuracy insurance.

**Binary.** Threshold each dimension at 0 and keep the sign bit: **1 bit per dimension, 32× compression**. Similarity becomes **Hamming distance**, an XOR plus a `popcount` (one hardware instruction), in place of a floating-point dot product. Brutally lossy per dimension, but 1024 dims fit in 128 bytes.

**Quantize-then-rescore.** This is the key idea, and Cohere and mixedbread both shipped and documented it in 2024. *Stage 1:* search the tiny quantized index (binary Hamming or int8) and **over-fetch** a shortlist, say 10× the final `k`. *Stage 2:* **rescore** only that shortlist against higher-precision vectors (int8 or full `float32`, kept on disk or a cold tier) and take the true top-`k`. A binary shortlist rescored with int8 or fp32 recovers **95%+ of full-precision recall** while the hot tier stays 4–32× smaller.

## Why it works

It sounds impossible until you notice that **retrieval needs the *ranking*, not the distances.** A `d = 1024` dot product sums 1024 terms. Per-dimension quantization noise is roughly zero-mean and *averages out* over the sum, so its share of the total shrinks relative to the signal as `d` grows. Exact pairwise distances move under coarse quantization, but the *order* of the top candidates stays remarkably stable. Binary keeps the **sign structure** of each coordinate, and in high dimensions the sign bits carry most of the angular information. It's the intuition behind random-hyperplane LSH / SimHash (Charikar 2002), where Hamming distance over sign bits approximates angular distance. High-dimensional embeddings are *robust to per-coordinate precision loss*, and that's what makes them compressible.

It's the same move as [[Concept - Post-Training Quantization Formats|post-training weight quantization]] (fp32 → int8 and below), pointed at the embedding tensor instead of the weight matrices. One difference matters: retrieval can fully recover the precision loss with a rescore, while a quantized weight is committed at inference time. (How far you can compress depends on the space being well-behaved. An anisotropic, off-center space quantizes worse; see [[Concept - Embedding Space Geometry]].)

## In practice

For a 1M × 1024-d corpus, the numbers make the argument:

| Representation | Bytes / vector | Total | Ratio |
|---|---|---:|---:|
| fp32 | 4096 | 4 GB | 1× |
| int8 | 1024 | 1 GB | 4× |
| binary | 128 | 128 MB | 32× |

For RAM-bound HNSW this is the memory lever that matters most. It's the same [[Reference - Memory Math for Transformers|byte-budget arithmetic]] that decides whether a model or an index fits on a given box, applied to the embedding tensor. It **multiplies with [[Concept - Matryoshka Representation Learning|Matryoshka]] dimension truncation**: truncate 1024 → 512 dims (MRL) *then* int8 and you get 8×; 512-d binary gives 64×. Support is broad as of 2026. Qdrant (scalar / binary / product quantization), [[Reference - Vector Database Landscape|pgvector]] (`halfvec`, `bit`), Milvus and Weaviate all expose it, and Cohere embed v3, mixedbread and Jina ship models documented for binary/int8 use. My default: **int8 is near-lossless** with per-dimension calibration and needs no rescore for most workloads. **Binary needs the rescore step and per-dataset threshold calibration** before you trust it.

Binary is often a *latency* win too. `popcount` over 128 bytes beats a 1024-wide fp32 SIMD dot product, so the hot-tier search gets faster as well as smaller.

## Failure modes

- **Naive binary with no rescore.** Recall collapses on close, hard queries, the ones that matter. *Fix:* always keep higher-precision vectors on a cold tier for stage 2. "Binary embeddings" really means "binary hot tier + full-precision cold tier."
- **Threshold miscalibration.** Binary's sign-at-0 assumes centered dimensions; an [[Concept - Embedding Space Geometry|anisotropic]] space with off-center dimensions loses information. *Fix:* center/whiten, or calibrate per-dimension thresholds.
- **Quantizing an already-degenerate space.** If the similarity range is crushed, int8 buckets collapse and *effective* precision falls well under the nominal 8 bits.
- **Query/document range mismatch.** Quantizing the query with a different calibration range from the documents adds a systematic distance bias, a subtle and silent ranking error.
- **Detection for all of the above:** A/B `recall@k` of quantized-with-rescore against fp32 on a labeled set, and sweep recall against shortlist size to set the over-fetch.

## The non-obvious

**The rescore protects recall more than the bit-width does.** Teams instinctively keep vectors at `float32` "to be safe" and under-invest in the rescore step. Then they find that a 32× binary index *with* a well-sized rescore beats a naive fp32 index on cost at nearly identical quality, while a binary index *without* rescore is worthless. The precision you need for *navigation* (finding the neighborhood) and for *final ranking* (ordering within it) are separate budgets. Spend cheap bits on the first and exact bits on the second. [[Breakdown - DiskANN]] uses the same two-tier principle internally (PQ codes in RAM to navigate, full vectors on disk to rescore). It also links embedding quantization to its learned cousin [[Concept - IVF and Product Quantization|product quantization]]: scalar/binary are the simple per-dimension methods and PQ is the learned subvector-codebook method, but all of them live or die by the rescore.

## Connections

- [[Concept - IVF and Product Quantization]] — the learned subvector-codebook compression family; scalar and binary are the simpler per-dimension cousins, all recovered by rescore.
- [[Concept - Matryoshka Representation Learning]] — dimension truncation that composes multiplicatively with bit quantization for stacked compression.
- [[Concept - HNSW]] — the RAM-bound index whose memory blowup quantization is the standard fix for.
- [[Concept - Floating Point for Deep Learning]] — what fp32 / int8 actually are and why a dimension costs 4 bytes before compression (cross-domain: foundations).
- [[Concept - Semantic Search]] — the dense retrieval this compresses without (much) hurting.
- [[Reference - Vector Database Landscape]] — which stores support scalar / binary / product quantization and how.
- [[Concept - Post-Training Quantization Formats]] — the model-weight analog: same idea (fp32 → int8/lower), different tensor and different rescore story (cross-domain: inference & serving).
- [[Breakdown - DiskANN]] — uses PQ codes in RAM and full vectors on disk, the same navigate-approximate / rescore-exact pattern.
- [[Concept - Embedding Space Geometry]] — how anisotropy and off-center dimensions set the ceiling on how far you can quantize.
- [[Reference - Memory Math for Transformers]] — the byte-budget framework that makes the compression ratios above actionable (cross-domain: hardware).

## Sources

- Cohere (2024) — *Int8 and binary embeddings* (blog / docs). The two-stage binary-shortlist-then-int8/fp32-rescore recipe and its recall retention.
- mixedbread (2024) — binary + int8 rescoring writeups. Independent confirmation of ~32× hot-tier compression at high recall retention.
- Charikar (2002) — *Similarity Estimation Techniques from Rounding Algorithms* (SimHash / random-hyperplane LSH). The intuition that sign bits approximate angular distance.
- Jégou, Douze, Schmid (2011) — *Product Quantization for Nearest Neighbor Search*. The learned-codebook contrast to scalar/binary quantization.
