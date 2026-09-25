---
tags: [concept, domain/inference-serving, level/surface]
aliases: [prefill/decode, PD]
summary: "Prefill is parallel and compute-bound; decode is sequential and memory-bandwidth-bound — the split that shapes all LLM serving design."
---
> **One-paragraph hook:** Autoregressive inference is two different workloads sharing one model's weights. Prefill processes the whole prompt in one shot and behaves like a training step: a big, efficient matmul. Decode produces one token at a time and behaves like nothing else in deep learning. It has so little arithmetic that the GPU spends almost all its time waiting on memory. Every serving optimization attacks one side of this split or the other, and mixing the two up is the most common beginner mistake in capacity planning.

## The mechanism

**Prefill** runs the model once over all `P` prompt tokens at the same time. The same weight matrices are reused across all `P` positions in one matmul, so arithmetic intensity (FLOPs per byte of weight read from HBM) scales with `P`. A training forward pass runs in the same regime: high intensity, fed tensor cores, and achieved model FLOPs utilization (MFU) of up to 40-50%. Cost is roughly linear in `P`, plus an `O(P^2)` term from the [[Concept - Attention Mechanism]] score matrix that starts to dominate at long context (tens of thousands of tokens).

**Decode** runs the model once *per generated token*, and each pass has one token's worth of new work: one query attending over the cached keys and values. The FLOPs are tiny. The model still has to load its entire weight tensor from HBM to do them. Nothing is reused across time steps within a sequence, because each step is a separate kernel launch waiting on the previous token. So decode is **memory-bandwidth-bound**:

$$t_{\text{decode step, batch 1}} \approx \frac{\text{weight\_bytes}}{\text{HBM\_bandwidth}}$$

For a 70B-parameter model in fp16 (`~140 GB` of weights) on an H100 SXM (`~3.35 TB/s` HBM bandwidth):

$$t \approx \frac{140 \times 10^9}{3.35 \times 10^{12}} \approx 42\text{ ms/token}$$

That's under 25 tokens/second. Single-stream decode MFU is often below 5%, with the compute units mostly idle, waiting for bytes.

Batch size fixes it. If `B` sequences decode together, one weight read from HBM serves all `B` in a single fused batched matmul, so arithmetic intensity rises roughly in proportion to `B`: one extra MAC per weight per added sequence, for essentially no extra bytes moved. [[Concept - The Roofline Model]] describes the same thing. Batch-1 decode sits far left of the ridge point, in the memory-bound region, and raising batch size moves the operating point right toward the compute roof.

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

Prefill is already near or past the ridge point at any reasonable prompt length. More batching helps its throughput but barely changes per-token cost, since it was never memory-bound.

## In practice

Rule of thumb: **prefill is priced in FLOPs, decode is priced in memory bandwidth.** Double the HBM bandwidth and decode latency roughly halves while prefill throughput barely moves. Double the tensor-core FLOPs and prefill latency roughly halves while single-stream decode doesn't improve. Hardware generations get sold on both numbers separately for this reason (H100 → H200 mostly buys HBM bandwidth and capacity, not much more FLOPs), and [[Reference - Inference Performance Math]] tabulates decode step time per GPU from real HBM bandwidth figures instead of headline TFLOPs.

The two phases want opposite things. Prefill wants big token batches to amortize fixed costs; decode wants big *sequence* batches to raise arithmetic intensity. A server that naively interleaves whole prefills and whole decode steps gets interference: a newly admitted request's prefill takes over an iteration and stalls every decoding request's inter-token latency for that step. There are two fixes. [[Concept - Chunked Prefill]] slices long prefills into fixed-size chunks and interleaves them with in-flight decode tokens, so no iteration is prefill-dominated. [[Concept - Prefill-Decode Disaggregation]] goes further and runs the phases on physically separate GPU pools, each tuned for its own bottleneck. Both exist only because of this asymmetry. Nobody would otherwise split an identical model across two pools.

Full formulas and worked numbers per model/GPU pair are in [[Reference - Inference Performance Math]]. The batching mechanism that uses decode's spare compute is [[Concept - Continuous Batching]]. The cost consequence, output tokens priced several times higher than input tokens on every commercial API, is in [[Concept - Latency, Throughput, and Cost in LLM Serving]].

## Failure modes

- **Treating decode latency as a FLOPs problem.** Engineers with training-time intuition try lower precision or fewer FLOPs to speed up decode and are confused when nothing changes. The bottleneck is bytes moved. Only smaller weights (quantization) or more bandwidth helps, whether from better hardware or from [[Concept - Speculative Decoding]], which amortizes one weight read across several accepted tokens.
- **Sizing capacity off prefill-only benchmarks.** A load test measuring TTFT on short, isolated requests looks nothing like production, where concurrent long-context prefill and steady-state decode share the same batch. Capacity planning has to model both phases interacting.
- **Ignoring the O(P²) attention term.** Linear-cost intuition for prefill fails at very long prompts, where the quadratic growth of the attention score matrix comes to dominate prefill time. Past tens of thousands of tokens, TTFT curves bend upward.

## The non-obvious

The "obvious" hardware upgrade is wrong more often than practitioners expect. A GPU with more FLOPs barely moves the metric chat users feel (inter-token latency), because chat is decode-dominated and bandwidth-bound. What predicts user-perceived speed is HBM bandwidth divided by weight size. That's also why quantization is such an outsized win for serving despite being a fairly modest change: shrinking `weight_bytes` shrinks the decode-step formula directly, while shrinking FLOPs (what quantization is usually marketed on) barely matters for decode.

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
