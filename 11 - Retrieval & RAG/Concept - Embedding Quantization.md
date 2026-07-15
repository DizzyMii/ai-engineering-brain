---
tags: [concept, domain/retrieval-rag, level/unicorn]
aliases: [binary embeddings, int8 embeddings, scalar quantization, embedding compression, quantize-and-rescore]
summary: "Compressing embedding vectors to int8 or binary for 4-32x cheaper storage and faster search, with a rescore pass that recovers 95%+ of recall."
---
> **One-paragraph hook:** A million 1024-dimensional [[Concept - Floating Point for Deep Learning|`float32`]] embeddings is 4 GB, and an [[Concept - HNSW|HNSW]] graph roughly doubles that in RAM — so memory, not compute, is usually what caps a vector index. Embedding quantization is the lever that turns those 4 GB into 1 GB (int8) or 128 MB (binary) while keeping almost all of the [[Concept - Semantic Search|retrieval]] quality. The trick that makes it work is not the compression — it's the *rescore*: a cheap coarse-precision shortlist followed by an exact re-ranking of just that shortlist. Get the rescore right and binary embeddings hold ~95% of full-precision recall at 32× less memory. Forget it and binary tanks on exactly the hard queries you care about.

## The mechanism

Two compression schemes dominate, plus one recovery step that makes them usable.

**Scalar int8.** Map each `float32` dimension onto an 8-bit integer using a per-dimension (or global) min/max range: `q = round((x - min) / (max - min) × 255)`. That is a **4× storage cut** (4 bytes → 1 byte) with only minor recall loss when the calibration ranges are computed per dimension. The *asymmetric* variant keeps the query in `float32` and quantizes only the stored documents, so the dot product `q · d̂` accumulates quantization error on one operand instead of two — cheap accuracy insurance.

**Binary.** Threshold each dimension at 0 and keep the sign bit: **1 bit per dimension, 32× compression**. Similarity becomes **Hamming distance** — an XOR followed by a `popcount`, a single hardware instruction — instead of a floating-point dot product. It is brutally lossy per dimension but stores 1024 dims in 128 bytes.

**The two-stage recovery (quantize-then-rescore).** This is the load-bearing idea (Cohere and mixedbread both shipped and documented it in 2024). *Stage 1:* run the search over the tiny quantized index — binary Hamming or int8 — and **over-fetch** a shortlist (say 10× the final `k`). *Stage 2:* **rescore** just that shortlist against higher-precision vectors (int8 or the full `float32`, kept on disk / a cold tier) and take the true top-`k`. A binary shortlist rescored with int8 or fp32 recovers **95%+ of full-precision recall** while the hot tier stays 4–32× smaller.

## Why it works

The result feels impossible until you see why: **retrieval needs the *ranking*, not the distances.** A `d = 1024` dot product is a sum of 1024 terms; per-dimension quantization noise is roughly zero-mean and *averages out* across the sum, so its effect on the total shrinks relative to the signal as `d` grows. Exact pairwise distances shift under coarse quantization, but the *order* of the top candidates is remarkably stable. Binary specifically preserves the **sign structure** of each coordinate, and for high-dimensional embeddings the sign bits carry most of the angular information — the same intuition as random-hyperplane LSH / SimHash (Charikar 2002), where Hamming distance over sign bits approximates angular distance. High-dimensional embeddings are, in a real sense, *robust to per-coordinate precision loss* — which is exactly what makes them compressible. This is the same move as [[Concept - Post-Training Quantization Formats|post-training weight quantization]] (fp32 → int8 and below) aimed at the embedding tensor rather than the weight matrices, with one crucial difference: retrieval can fully recover the precision loss via rescore, whereas a quantized weight is committed at inference time. (How compressible depends on the space being well-behaved: an anisotropic, off-center space quantizes worse — see [[Concept - Embedding Space Geometry]].)

## In practice

The numbers are the whole argument, for a 1M × 1024-d corpus:

| Representation | Bytes / vector | Total | Ratio |
|---|---|---:|---:|
| fp32 | 4096 | 4 GB | 1× |
| int8 | 1024 | 1 GB | 4× |
| binary | 128 | 128 MB | 32× |

That is the memory lever that matters most for RAM-bound HNSW — the same [[Reference - Memory Math for Transformers|byte-budget arithmetic]] that governs whether a model or an index fits on a given box, applied to the embedding tensor. It **composes with [[Concept - Matryoshka Representation Learning|Matryoshka]] dimension truncation** multiplicatively: truncate 1024 → 512 dims (MRL) *then* int8 gives 8×; 512-d binary gives 64×. Support is broad as of 2026 — Qdrant (scalar / binary / product quantization), [[Reference - Vector Database Landscape|pgvector]] (`halfvec`, `bit`), Milvus, and Weaviate all expose it, and Cohere embed v3, mixedbread, and Jina ship models documented for binary/int8 use. Practical default: **int8 is near-lossless** with per-dimension calibration and needs no rescore for most workloads; **binary needs the rescore step and per-dataset threshold calibration** before you trust it.

Note that binary is often also a *latency* win, not only a memory win: `popcount` over 128 bytes beats a 1024-wide fp32 SIMD dot product, so the hot-tier search gets faster as well as smaller.

## Failure modes

- **Naive binary with no rescore.** Recall collapses on close / hard queries — precisely the ones that matter. *Fix:* always keep higher-precision vectors on a cold tier for stage 2; "binary embeddings" really means "binary hot tier + full-precision cold tier."
- **Threshold miscalibration.** Binary's sign-at-0 assumes centered dimensions; an [[Concept - Embedding Space Geometry|anisotropic]] space with off-center dimensions loses information. *Fix:* center/whiten or calibrate per-dimension thresholds.
- **Quantizing an already-degenerate space.** A crushed similarity range means int8 buckets collapse and the *effective* precision is well under the nominal 8 bits.
- **Query/document range mismatch.** Quantizing the query with a different calibration range than the documents introduces a systematic distance bias — a subtle, silent ranking error.
- **Detection for all of the above:** A/B `recall@k` of quantized-with-rescore versus fp32 on a labeled set, and sweep recall against shortlist size to size the over-fetch.

## The non-obvious

The counterintuitive, hard-won lesson: **the rescore, not the bit-width, is what protects recall.** Teams instinctively over-invest in keeping vectors at `float32` "to be safe" and under-invest in the rescore step — then discover that a 32× binary index *with* a well-sized rescore beats a naive fp32 index on cost at nearly identical quality, while a binary index *without* rescore is worthless. The precision you need for *navigation* (finding the neighborhood) and the precision you need for *final ranking* (ordering within it) are different budgets, and the whole art is spending cheap bits on the first and exact bits on the second. This is the same two-tier-precision principle that [[Breakdown - DiskANN]] uses internally (PQ codes in RAM to navigate, full vectors on disk to rescore) and that separates embedding quantization from its learned cousin [[Concept - IVF and Product Quantization|product quantization]] — scalar/binary are the simple per-dimension methods; PQ is the learned subvector-codebook method, but both live or die by the same rescore.

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
