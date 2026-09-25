---
tags: [reference, domain/inference-serving, level/core]
aliases: [TTFT, TPOT, ITL, goodput, inference perf formulas]
summary: "Formula and metric sheet for LLM serving: KV cache bytes, decode step time, max batch, TTFT/TPOT/throughput/goodput, and cost per token."
---

# Reference - Inference Performance Math

## KV cache memory

$$\text{KV bytes/token} = 2 \times n_{\text{layers}} \times n_{\text{kv\_heads}} \times d_{\text{head}} \times \text{bytes\_per\_elem}$$

The factor of 2 is for storing both K and V. See [[Concept - KV Cache]] for the derivation.

| Model | Layers | KV heads | Head dim | fp16 KV bytes/token | fp8 KV bytes/token |
|---|---|---|---|---|---|
| Llama-3-8B | 32 | 8 (GQA) | 128 | 131,072 B ≈ 0.125 MB | ≈ 0.0625 MB |
| Mistral-7B | 32 | 8 (GQA) | 128 | 131,072 B ≈ 0.125 MB | ≈ 0.0625 MB |
| Llama-3-70B | 80 | 8 (GQA) | 128 | 327,680 B ≈ 0.31 MB | ≈ 0.156 MB |
| DeepSeek-V2/V3 (MLA)¹ | — | — (compressed latent) | — | ≈ 93% smaller than an equal-quality MHA model² | further reduced |

¹ MLA (DeepSeek-AI 2024) replaces per-head K,V with a shared low-rank latent, so the layers/heads columns don't apply the same way. Read the row as an order-of-magnitude pointer; don't plug it into the formula above.
² DeepSeek-V2 technical report figure, reported relative to a comparable standard-MHA model at similar quality. Company-reported, not independently re-derived here.

**Total live KV** = (bytes/token) × Σ(sequence lengths of all live requests). At long context this, more than the model weights, is usually what caps concurrency. [[Concept - PagedAttention]] explains why it's allocated in blocks instead of reserved contiguously.

## Decode step time (batch = 1)

$$t_{\text{step}} \approx \frac{\text{model\_weight\_bytes}}{\text{HBM\_bandwidth}}$$

Every decode step re-reads the full weight tensor from HBM (see [[Concept - Prefill and Decode Phases]]). At batch 1 that read dominates, because arithmetic intensity is far below the compute roof ([[Concept - The Roofline Model]]).

GPU HBM bandwidth (as of 2026, per vendor datasheets)³:

| GPU | HBM generation | Bandwidth |
|---|---|---|
| A100 40GB SXM | HBM2e | 1.56 TB/s |
| A100 80GB SXM | HBM2e | 2.04 TB/s |
| H100 SXM | HBM3 | 3.35 TB/s |
| H200 SXM | HBM3e | 4.8 TB/s |
| B200 | HBM3e | ≈ 8 TB/s |

³ Datasheet bandwidth is a ceiling. A real decode kernel typically achieves 70-90% of it, so treat the table as an upper bound for the estimates below.

Using $t_{\text{ms}} \approx \text{weight\_GB} / \text{bandwidth\_TBps}$:

| Model + precision | Weight size | H100 (3.35 TB/s) | H200 (4.8 TB/s) | B200 (8 TB/s) |
|---|---|---|---|---|
| Llama-3-8B, fp16 | 16 GB | 4.8 ms/tok | 3.3 ms/tok | 2.0 ms/tok |
| Llama-3-70B, fp16 | 140 GB | 41.8 ms/tok | 29.2 ms/tok | 17.5 ms/tok |
| Llama-3-70B, fp8 | 70 GB | 20.9 ms/tok | 14.6 ms/tok | 8.75 ms/tok |

These are single-stream (batch-1) numbers. Batching spreads the same weight read across many concurrent sequences, and that's the whole mechanical case for [[Concept - Continuous Batching]]: decode step time barely rises with batch size until the GPU crosses from memory-bound to compute-bound.

## Max concurrent tokens (KV budget)

$$N_{\text{tokens}} \approx \frac{\text{VRAM} - \text{weight\_bytes} - \text{activation/framework overhead}}{\text{KV\_bytes\_per\_token}}$$

**Worked example:** Llama-3-70B fp16 (~140 GB weights) on 2×H100 80GB with tensor-parallel=2. After weights and framework/activation overhead, real deployments typically keep something on the order of ~20 GB/GPU of headroom for KV. At 0.3125 MB/token (fp16 KV, from the table above):

$$\frac{20{,}480 \text{ MB}}{0.3125 \text{ MB/token}} \approx 65{,}536 \text{ tokens per GPU}$$

Switching KV to fp8 (see [[Concept - KV Cache Quantization]]) roughly doubles that ceiling to ~131,000 tokens/GPU. Same GPUs, twice the concurrent-request budget, paid for in KV precision.

## Latency, throughput, and goodput definitions

| Metric | Definition |
|---|---|
| **TTFT** | Time to first token = queue wait + prefill time |
| **TPOT / ITL** | Time per output token / inter-token latency = mean decode step time |
| **End-to-end latency** | TTFT + TPOT × output_length |
| **Throughput** | Aggregate tokens/sec or requests/sec served by the engine |
| **Goodput** | Requests/sec that meet the target (TTFT, TPOT) SLO jointly: completed *on time*, not merely completed |

Always report **p50/p90/p99** alongside the mean. Batching creates fat tails: a request queued behind a large prefill or a chunked-prefill iteration (see [[Concept - Chunked Prefill]]) can see TTFT or TPOT far worse than the median request in the same window.

Typical human-facing latency targets (as of 2026; these are UX thresholds, not hardware limits):

| Use case | TTFT target | TPOT target |
|---|---|---|
| Chat | < 300–500 ms | < 50 ms (~20 tok/s, above average reading speed) |
| Voice / real-time agent | < 200 ms | < 50 ms |

## Cost identity

$$\frac{\$}{\text{1M output tokens}} = \frac{\text{GPU\_\$/hr} / 3600}{\text{decode\_tokens\_per\_sec (aggregate)}} \times 10^{6}$$

Worked example: an H100 at ~$2.50/hr (as of 2026, illustrative; varies by cloud, region, and commitment level) sustaining ~2,500 output tok/s aggregate across a full batch:

$$\frac{2.50/3600}{2500} \times 10^{6} \approx \$0.28 \text{ per 1M output tokens (hardware cost only, before margin/overhead)}$$

Input tokens are cheap next to output tokens (API pricing typically puts input at roughly 1/3 to 1/5 of output price). Prefill is parallel and compute-rich; decode is serialized and memory-bandwidth-bound. See [[Concept - Latency, Throughput, and Cost in LLM Serving]].

## Benchmarking tools

- **`vllm bench serve`** (vLLM's built-in serving benchmark): sweeps request rate/concurrency against a target engine and reports TTFT/TPOT/throughput percentiles.
- **NVIDIA `genai-perf`**: protocol-aware (OpenAI-compatible) load generator with the same percentile reporting, vendor-neutral across engines.
- **`llmperf`**: a similar sweep-and-report tool, common for cross-provider API benchmarking.

Use a realistic input/output length distribution (a ShareGPT-style trace, not a fixed 128/128 tokens). Fixed short lengths understate both TTFT variance and KV pressure compared with production traffic.

## Connections

- [[Reference - Memory Math for Transformers]] — the general transformer memory reference this sheet specializes for the inference/serving case.
- [[Concept - KV Cache]] — the mechanism behind the KV bytes/token formula.
- [[Concept - Prefill and Decode Phases]] — why decode step time reduces to a bandwidth-bound formula while prefill doesn't.
- [[Concept - The Roofline Model]] — the arithmetic-intensity framework that explains why decode is memory-bound at low batch.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — the economic interpretation of these same formulas (cost, pricing, SLO tradeoffs).
- [[Concept - GPU Memory Hierarchy]] — the HBM bandwidth figures used throughout this sheet come from this note's hardware model.
- [[Playbook - Tuning an LLM Serving Deployment]] — the procedure that uses these formulas to find a deployment's actual operating point.
- [[Concept - Continuous Batching]] — why decode step time is nearly flat with batch size until the compute roof is hit.
- [[Reference - LLM Production SLOs and Latency Budgets]] — the production-operations counterpart to the latency targets listed here.
- [[Concept - PagedAttention]] — the block-based allocator that makes the "total live KV" figure achievable in practice instead of wasted to fragmentation.
- [[Concept - KV Cache Quantization]] — the lever behind the fp8-KV row that doubles the max-concurrent-tokens ceiling.
- [[Concept - Chunked Prefill]] — the scheduling mechanism responsible for the fat p99 tails this sheet says to always report.

## Sources

- Kwon et al. (2023) — "Efficient Memory Management for Large Language Model Serving with PagedAttention" (SOSP). Source of the memory-bound framing underlying the KV and concurrency formulas.
- DeepSeek-AI (2024) — DeepSeek-V2 technical report. Source of the MLA KV-reduction figure.
- NVIDIA H100/H200/B200 datasheets — source of the HBM bandwidth figures (as of 2026; verify against the current datasheet before relying on these for capacity planning).
