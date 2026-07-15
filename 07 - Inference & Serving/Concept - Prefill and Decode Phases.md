---
tags: [concept, domain/inference-serving, level/surface]
aliases: [prefill/decode, PD]
summary: "Prefill is parallel and compute-bound; decode is sequential and memory-bandwidth-bound — the split that shapes all LLM serving design."
---
> **One-paragraph hook:** Autoregressive inference is really two different workloads wearing the same model's weights. Prefill processes an entire prompt in one shot and behaves like a training step — a big, efficient matmul. Decode produces one token at a time and behaves like nothing else in deep learning: a workload so starved for arithmetic that the GPU spends almost all its time waiting on memory, not computing. Every serving optimization is an attack on one side of this split or the other, and conflating the two is the single most common beginner mistake in capacity planning.

## The mechanism

**Prefill** runs the model once over all `P` prompt tokens simultaneously. Because the same weight matrices are reused across all `P` positions in one matmul, the arithmetic intensity — FLOPs performed per byte of weight read from HBM — scales with `P`. This is the same regime a training forward pass runs in: high intensity, tensor cores stay fed, and achieved model FLOPs utilization (MFU) can reach 40-50%. Cost is roughly linear in `P`, with an additional `O(P^2)` term from the [[Concept - Attention Mechanism]] score matrix that starts to dominate at long context (tens of thousands of tokens).

**Decode** runs the model once *per generated token*, and each of those passes only has one token's worth of new work: one query, attending over the already-cached keys and values. The FLOPs are tiny. But the model still has to load its entire weight tensor from HBM to do that tiny amount of arithmetic — nothing is reused across time steps within a single sequence, because each step is a separate kernel launch waiting on the previous token's output. The workload is therefore **memory-bandwidth-bound**, not compute-bound:

$$t_{\text{decode step, batch 1}} \approx \frac{\text{weight\_bytes}}{\text{HBM\_bandwidth}}$$

For a 70B-parameter model in fp16 (`~140 GB` of weights) on an H100 SXM (`~3.35 TB/s` HBM bandwidth):

$$t \approx \frac{140 \times 10^9}{3.35 \times 10^{12}} \approx 42\text{ ms/token}$$

That's under 25 tokens/second, and single-stream decode MFU is often below 5% — the GPU's compute units sit mostly idle, waiting for bytes.

The reason batch size is the lever that fixes this: if `B` sequences decode together, the *same* weight read off HBM serves all `B` of them in one fused batched matmul, so arithmetic intensity rises roughly in proportion to `B` (one extra MAC per weight per additional sequence, at the cost of essentially no extra bytes moved). This is exactly the mechanism the [[Concept - The Roofline Model]] describes: decode at batch 1 sits far to the left of the ridge point (memory-bound region); raising batch size walks the operating point rightward toward the compute roof.

```
achieved FLOPs/s
      ^                              ___________ compute roof
      |                       ___----
      |                 __---°  <- decode, high batch
      |            __--
      |       __--
      | __--°  <- decode, batch 1 (stuck here)
      +------------------------------------------> arithmetic intensity
                 ridge point
```

Prefill, by contrast, is already near the ridge point or past it at any reasonable prompt length — more batching helps throughput but barely moves its per-token cost, because it was never memory-bound to begin with.

## In practice

The practitioner's rule of thumb: **prefill is priced in FLOPs, decode is priced in memory bandwidth.** A GPU with twice the HBM bandwidth roughly halves decode latency, but barely touches prefill throughput; a GPU with twice the tensor-core FLOPs roughly halves prefill latency but does nothing for single-stream decode. This is why hardware generations are sold on both numbers separately (e.g. H100 → H200 mostly buys HBM bandwidth and capacity, not much more FLOPs) and why [[Reference - Inference Performance Math]] tabulates decode step time per GPU using real HBM bandwidth figures rather than headline TFLOPs.

Because the two phases want opposite things — prefill wants big token batches to amortize fixed costs, decode wants big *sequence* batches to raise arithmetic intensity — a server that just interleaves whole prefills and whole decode steps naively creates interference: a newly admitted request's prefill monopolizes an iteration and stalls every decoding request's inter-token latency for that step. Serving systems handle this two ways: [[Concept - Chunked Prefill]] slices long prefills into fixed-size chunks and interleaves them with in-flight decode tokens so no single iteration is prefill-dominated, and [[Concept - Prefill-Decode Disaggregation]] goes further and runs prefill and decode on physically separate GPU pools tuned for their own bottleneck. Both exist purely because of the asymmetry described above — there is no other reason to disaggregate an otherwise identical model.

The full formula and worked numbers per model/GPU pair live in [[Reference - Inference Performance Math]]; the batching mechanism that exploits decode's spare compute lives in [[Concept - Continuous Batching]]; and the cost consequence — why output tokens are priced several times higher than input tokens on every commercial API — is covered in [[Concept - Latency, Throughput, and Cost in LLM Serving]].

## Failure modes

- **Treating decode latency like a FLOPs problem.** Engineers used to training-time intuition reach for lower precision or fewer FLOPs to speed up decode and are confused when nothing changes — the bottleneck is bytes moved, not arithmetic, so only weight-size reduction (quantization) or bandwidth (better hardware, or [[Concept - Speculative Decoding]] amortizing one weight-read across multiple accepted tokens) helps.
- **Sizing capacity off prefill-only benchmarks.** A load test that only measures TTFT on short, isolated requests looks nothing like a production mix of concurrent long-context prefill and steady-state decode; real capacity planning must model both phases interacting in the same batch.
- **Ignoring the O(P²) attention term.** Linear-cost intuition for prefill breaks down at very long prompts, where the attention score matrix's quadratic growth starts to dominate total prefill time — TTFT curves bend upward, not stay linear, past tens of thousands of tokens.

## The non-obvious

The asymmetry means the "obvious" hardware upgrade path is wrong more often than practitioners expect: buying a GPU with more FLOPs to speed up a chat product barely moves the metric users actually feel (inter-token latency), because chat is a decode-dominated, bandwidth-bound workload. The metric that predicts user-perceived speed is HBM bandwidth divided by weight size — which is also why quantization is such an outsized win for serving despite being a comparatively modest change: shrinking `weight_bytes` shrinks the decode-step formula directly, while shrinking FLOPs (the thing quantization is usually marketed on) barely matters for decode at all.

## Connections
- [[Concept - The Roofline Model]] — the general compute-vs-bandwidth framework that explains exactly why decode sits memory-bound and prefill doesn't.
- [[Concept - Continuous Batching]] — the scheduling mechanism that exploits decode's spare arithmetic intensity by raising batch size every iteration.
- [[Concept - Chunked Prefill]] — slices prefill into a token budget so it stops stalling in-flight decode requests.
- [[Concept - Prefill-Decode Disaggregation]] — the more radical fix: separate hardware pools per phase instead of interleaving.
- [[Concept - KV Cache]] — the structure prefill writes and decode reads every step; its growth is what decode's memory traffic is actually spent on beyond the weights.
- [[Concept - GPU Memory Hierarchy]] — the HBM/SRAM distinction underlying why "memory-bandwidth-bound" is a real, measurable regime and not just a metaphor.
- [[Reference - Inference Performance Math]] — the worked formulas and per-GPU numbers for both phases.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — how this asymmetry becomes the reason output tokens cost several times more than input tokens.
- [[Concept - Attention Mechanism]] — the operation whose quadratic score matrix drives prefill's superlinear cost at long context.
- [[Concept - Speculative Decoding]] — amortizes one memory-bound weight read across several accepted tokens, directly attacking decode's bandwidth bottleneck rather than its FLOPs.

## Sources
- Kwon et al. (2023, SOSP) — "Efficient Memory Management for Large Language Model Serving with PagedAttention" (vLLM). Establishes the modern framing of prefill vs. decode as distinct scheduling regimes.
- Agrawal et al. (2023/2024) — "SARATHI" / "Taming Throughput-Latency Tradeoff in LLM Inference with SARATHI-Serve." The chunked-prefill mechanism built directly on this asymmetry.
- Williams, Waterman & Patterson (2009) — "Roofline: An Insightful Visual Performance Model." The compute-vs-bandwidth framework decode's behavior is an instance of.
