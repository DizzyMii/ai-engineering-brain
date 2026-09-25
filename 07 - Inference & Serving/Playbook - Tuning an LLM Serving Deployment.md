---
tags: [playbook, domain/inference-serving, level/advanced]
aliases: [vLLM tuning, serving config tuning, finding the throughput knee]
summary: "The ordered procedure to take a model, GPU, and SLO and produce a tuned serving config: baseline, find the knee, tune the knobs, diagnose."
---

> **Goal:** turn a model + GPU allocation + latency SLO into a concrete, benchmarked serving configuration that maximizes throughput (or minimizes latency) without violating the SLO.
> **When to run this:** before any production launch, after any model/GPU/engine-version change, and whenever a capacity plan needs a real number instead of a guess.
> **Prerequisites:** a working deployment on your chosen engine (see [[Decision - Choosing an Inference Serving Framework]]), a defined latency SLO (TTFT/TPOT targets), and a realistic traffic sample, not synthetic fixed-length prompts.

Serving tuning usually fails in one of two ways. Teams benchmark the wrong workload (fixed 128/128 tokens instead of the real length distribution), or they chase one number, throughput or latency, as if the two didn't trade against each other. Follow these steps in order and you avoid both.

## Steps

1. **Pin the baseline and get a realistic benchmark trace.** Fix model weights, engine version and quantization recipe as an immutable triple before you touch any knob. [[Gotchas - LLM Serving in Production]] shows what happens when they drift silently. Build the benchmark trace from real production input/output length distributions (a ShareGPT-style trace will do if you have none yet), not fixed-length synthetic prompts. Prefill and decode cost scale very differently with length, and a fixed-length benchmark misrepresents both every time. *Expected:* a request trace whose length distribution you can defend as representative. *Deviation:* if all you have is a fixed-length synthetic benchmark, treat every number from step 2 on as directional only. Flat 128/128 prompts hide the prefill-stall and KV-pressure effects this playbook exists to tune.

2. **Sweep concurrency and find the knee.** With the metric definitions from [[Reference - Inference Performance Math]], sweep request rate or concurrency using a load-testing tool (`vllm bench serve`, NVIDIA's `genai-perf`, or `llmperf`). Record TTFT, TPOT, throughput and goodput at p50/p90/p99. The tail matters more than the mean because batching fattens it. Raise concurrency until TTFT or TPOT crosses your SLO at p90 or p99 (your call, but say which). The throughput just before that crossing is your usable ceiling, "the knee." *Expected:* a clear inflection where the latency curve bends sharply up. *Deviation:* latency that degrades smoothly with no obvious knee suggests you're compute-bound, not KV-bound (check MFU). A step-function degradation means you've hit a preemption cliff (see the [[Concept - KV Cache]] check in step 4).

3. **Diagnose what limits you at the knee.** At the concurrency where TPOT or TTFT crossed the SLO, look at KV cache utilization and the preemption/recompute count. High KV utilization with rising preemption: you're KV-capacity-bound (memory-bound). Low KV utilization, GPU pegged near 100%, TTFT dominating: you're compute-bound on prefill. Smooth but elevated TPOT with little preemption: raw decode bandwidth. This decides which knobs in step 4 will do anything, and tuning the wrong axis wastes benchmark cycles. *Expected:* one of the three signatures, clearly dominant. *Deviation:* if none dominates, suspect a scheduling artifact (see the token-budget interaction in [[Concept - Chunked Prefill]]) before a resource limit.

4. **Turn the knobs that match the diagnosis.** What each one trades, and when to use it:
   - `--gpu-memory-utilization` (raise carefully toward 0.92-0.95): more room for the [[Concept - KV Cache]], which addresses the KV-bound signature from step 3. Too high and you starve activation/workspace memory and risk OOM in a burst.
   - `--max-num-seqs`: the concurrency cap. Lower it to stop the preemption spiral described in the throughput-collapse entry of [[Gotchas - LLM Serving in Production]]. Raise it, if KV headroom allows, to climb toward the compute roof.
   - `--max-num-batched-tokens` (the [[Concept - Chunked Prefill]] budget): raise it for better prefill throughput and lower TTFT under load, lower it to smooth TPOT jitter for in-flight decodes. It's the direct knob for step 3's compute-bound-on-prefill signature.
   - `--kv-cache-dtype fp8`: roughly doubles effective KV capacity at near-lossless quality on Hopper+. For a KV-bound signature it's the fix with the biggest payoff, and it leaves weight precision alone (see [[Concept - KV Cache Quantization]]).
   - `--enable-prefix-caching`: close to free whenever the trace has shared prefixes (system prompts, few-shot blocks, multi-turn chat); see [[Concept - Automatic Prefix Caching]]. Check the hit rate on your real trace instead of assuming it fires.
   - `--tensor-parallel-size` / `--max-model-len`: TP adds compute and bandwidth by adding GPUs (see step 6). `max-model-len` bounds worst-case KV cost per sequence and is the blunt instrument when nothing else fits.
   *Expected:* a change in the metric the diagnosis predicted. *Deviation:* if a knob doesn't move the metric you expected, your step-3 diagnosis was wrong. Re-check KV utilization and preemption count before touching another knob.

5. **Choose throughput mode or latency mode. One config won't win both.** Throughput mode maximizes batch size and memory utilization and tolerates higher TPOT; it fits bulk, offline and batch workloads. Latency mode caps concurrency, uses chunked prefill aggressively, and considers [[Concept - Speculative Decoding]] for low-batch latency-critical paths (chat, agents). Spec decode only helps when the GPU has spare compute, meaning low batch, and can *reduce* throughput at high batch, so keep it out of the throughput-mode config. If one deployment has to serve both regimes well, look at [[Concept - Prefill-Decode Disaggregation]] instead of compromising a single config. *Expected:* two configs for two SLOs, not one "balanced" config. *Deviation:* a single config that claims both a tight TTFT and maximum throughput is almost certainly under-benchmarked at the tail.

6. **Decide sharding, then re-benchmark from step 2.** If the weights don't fit on the target GPU count, prefer [[Concept - Tensor and Pipeline Parallelism|tensor parallelism]] within a node (its per-layer all-reduce needs NVLink-class bandwidth) and pipeline parallelism across nodes where the interconnect is slower. Before adding GPUs to "fix" throughput, check that the all-reduce isn't already the bottleneck. TP scaling that doesn't raise throughput proportionally is a communication-bound symptom, not a compute one. Every change from steps 4-6 invalidates the previous benchmark, so re-run the step 2 sweep after each one and compare the full latency distribution, not only the mean.

## Verification

The config is done when all of these hold. The step 2 concurrency sweep shows the SLO holding at p90/p99, not only p50, up to target load. Preemption count stays near zero at that load, so you aren't silently trading latency for throughput through recompute. KV cache utilization sits in a stable band with headroom for bursts instead of pinned at the ceiling. The config was validated against the *realistic* trace from step 1, not the synthetic one. And if quantization was part of the tuning, downstream task quality (not perplexity; see [[Gotchas - Quantization Quality Loss]]) was actually checked.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| Throughput collapses as concurrency rises past a threshold | KV budget exceeded, preemption spiral | Lower `max-num-seqs`, raise `gpu-memory-utilization`, or enable fp8 KV (step 4) |
| TPOT jitters periodically for streaming users | Long prefills stalling the decode batch | Lower the chunked-prefill token budget (step 4) |
| High TTFT even at low concurrency | Prefill compute-bound, or no TP where weights are memory-bandwidth-starved | Raise prefill token budget, add tensor parallelism (step 6) |
| OOM at long context specifically | `max_model_len` exceeds what KV budget supports at target concurrency | Cut `max_model_len` or switch to fp8/int4 KV cache (step 4) |
| Low throughput even though latency is well under SLO | Concurrency capped too conservatively, leaving throughput on the table | Raise `max-num-seqs` incrementally and re-sweep (step 2) until the knee is found |
| TP scaling adds GPUs but throughput doesn't scale proportionally | All-reduce communication-bound, not compute-bound | Check interconnect (NVLink vs. cross-node), reduce TP degree, prefer PP across nodes (step 6) |
| Spec decode enabled but throughput dropped at high load | Verification overhead exceeds savings once GPU is compute-saturated | Disable speculative decoding above the batch size where it stops paying off (step 5) |

## Connections
- [[Checklist - Pre-Production Inference Readiness]] — the correctness/capacity/reliability/observability checklist to run against the config this playbook produces before it takes real traffic.
- [[Reference - Inference Performance Math]] — the formulas and metric definitions (TTFT, TPOT, goodput) every step of this benchmarking loop is built on.
- [[Concept - Continuous Batching]] — the scheduling substrate whose `max-num-seqs`/token-budget knobs this playbook tunes directly.
- [[Concept - Chunked Prefill]] — the mechanism behind step 4's token-budget knob and the fix for the prefill-stall jitter symptom.
- [[Concept - KV Cache Quantization]] — the single highest-leverage fix for a KV-bound diagnosis at step 3, via `--kv-cache-dtype fp8`.
- [[Concept - Automatic Prefix Caching]] — a near-free throughput/TTFT win this playbook checks is actually firing on the real traffic trace.
- [[Concept - Tensor and Pipeline Parallelism]] — cross-domain (04) grounding for the sharding decision in step 6, including why TP must stay intra-node.
- [[Breakdown - vLLM]] — the reference engine whose flags (`--gpu-memory-utilization`, `--max-num-batched-tokens`, etc.) this playbook names concretely.
- [[Gotchas - LLM Serving in Production]] — the failure-mode catalog this playbook's branch table draws its diagnoses from.
- [[Concept - GPU Memory Hierarchy]] — cross-domain (08) grounding for why the `gpu-memory-utilization` knob and KV headroom are fundamentally an HBM-capacity tradeoff.

## Sources
- Kwon et al. (2023) — *Efficient Memory Management for Large Language Model Serving with PagedAttention* (SOSP 2023). The paged KV allocator and continuous-batching scheduler this playbook's knobs operate on.
- Agrawal et al. (2023) — *SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills*. The stall-free batching mechanism behind step 4's chunked-prefill budget.
- Yu et al. (2022) — *Orca: A Distributed Serving System for Transformer-Based Generative Models* (OSDI 2022). Establishes the iteration-level scheduling this playbook's concurrency sweep is tuning.
