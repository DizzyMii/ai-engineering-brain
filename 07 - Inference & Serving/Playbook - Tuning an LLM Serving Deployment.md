---
tags: [playbook, domain/inference-serving, level/advanced]
aliases: [vLLM tuning, serving config tuning, finding the throughput knee]
summary: "The ordered procedure to take a model, GPU, and SLO and produce a tuned serving config: baseline, find the knee, tune the knobs, diagnose."
---

> **Goal:** turn a model + GPU allocation + latency SLO into a concrete, benchmarked serving configuration that maximizes throughput (or minimizes latency) without violating the SLO.
> **When to run this:** before any production launch, after any model/GPU/engine-version change, and whenever a capacity plan needs a real number instead of a guess.
> **Prerequisites:** a working deployment on your chosen engine (see [[Decision - Choosing an Inference Serving Framework]]), a defined latency SLO (TTFT/TPOT targets), and a realistic traffic sample — not synthetic fixed-length prompts.

Serving tuning fails most often because teams benchmark the wrong workload (fixed 128/128 tokens instead of the real length distribution) or chase a single number (throughput, or latency) without acknowledging they trade against each other. This playbook is the ordered sequence that avoids both traps.

## Steps

1. **Pin the baseline and get a realistic benchmark trace.** Fix the model weights, engine version, and quantization recipe as an immutable triple before touching any knob — see [[Gotchas - LLM Serving in Production]] for what happens when they drift silently. Build a benchmark request trace from real production input/output length distributions (a ShareGPT-style trace is a reasonable substitute if you have none yet) rather than fixed-length synthetic prompts, because prefill and decode cost scale very differently with length and a fixed-length benchmark systematically misrepresents both. *Expected:* a request trace with a length distribution you can defend as representative. *Deviation:* if you only have a fixed-length synthetic benchmark, treat every number from step 2 onward as directional, not load-bearing — flat 128/128 prompts hide the exact prefill-stall and KV-pressure effects this playbook exists to tune around.

2. **Sweep concurrency and find the knee.** Using [[Reference - Inference Performance Math]]'s metric definitions, sweep request rate or concurrency with a load-testing tool (`vllm bench serve`, NVIDIA's `genai-perf`, or `llmperf`) and record TTFT, TPOT, throughput, and goodput at p50/p90/p99 — the tail matters more than the mean because batching makes it fat. Raise concurrency until TTFT or TPOT crosses your SLO at p90 or p99 (your choice, but be explicit about which). The throughput reached just before that crossing is your usable ceiling — this is "the knee." *Expected:* a clear inflection point where the latency curve bends sharply upward. *Deviation:* if latency degrades smoothly with no obvious knee, you're likely compute-bound rather than KV-bound (check MFU); if it degrades in a step function, you've hit a preemption cliff (see step 4's [[Concept - KV Cache]] check).

3. **Diagnose what's binding at the knee.** At the concurrency where TPOT or TTFT crossed the SLO, check KV cache utilization and preemption/recompute count. High KV utilization with rising preemption means you're KV-capacity-bound (memory-bound); low KV utilization with the GPU pegged near 100% and TTFT dominating means you're compute-bound on prefill; smooth-but-elevated TPOT with low preemption points at raw decode bandwidth limits. This diagnosis determines which knobs in step 4 actually move the needle — tuning the wrong axis wastes benchmark cycles. *Expected:* one of the three signatures above, clearly dominant. *Deviation:* if none is dominant, suspect a scheduling artifact (see [[Concept - Chunked Prefill]]'s token-budget interaction) rather than a resource limit.

4. **Apply the knobs matched to the diagnosis.** The knobs, what they trade, and when to reach for each:
   - `--gpu-memory-utilization` (raise carefully toward 0.92-0.95): more headroom for [[Concept - KV Cache]], directly addresses the KV-bound signature from step 3. Push too high and you starve activation/workspace memory and risk OOM under a burst.
   - `--max-num-seqs`: the concurrency cap. Lower it to stop the preemption spiral from [[Gotchas - LLM Serving in Production]]'s throughput-collapse gotcha; raise it (if KV headroom allows) to climb toward the compute roof.
   - `--max-num-batched-tokens` (the [[Concept - Chunked Prefill]] budget): raise for better prefill throughput and lower TTFT under load; lower to smooth TPOT jitter for in-flight decode requests. This is the direct knob for step 3's compute-bound-on-prefill signature.
   - `--kv-cache-dtype fp8`: roughly doubles effective KV capacity at near-lossless quality on Hopper+ — the single highest-leverage fix for a KV-bound signature that doesn't require touching weight precision at all (see [[Concept - KV Cache Quantization]]).
   - `--enable-prefix-caching`: near-free win whenever the traffic trace has shared prefixes (system prompts, few-shot blocks, multi-turn chat) — see [[Concept - Automatic Prefix Caching]]; verify hit rate on your actual trace rather than assuming it fires.
   - `--tensor-parallel-size` / `--max-model-len`: TP adds compute and bandwidth by adding GPUs (see step 6); `max-model-len` directly bounds worst-case KV cost per sequence and is the blunt instrument when nothing else fits.
   *Expected:* a change in exactly the metric the diagnosis predicted. *Deviation:* if a knob change doesn't move the metric you expected, your step-3 diagnosis was wrong — go back and re-check KV utilization and preemption count before changing another knob.

5. **Pick throughput mode or latency mode — never expect one config to win both.** Throughput mode maximizes batch size and memory utilization and tolerates elevated TPOT (right for bulk/offline/batch workloads); latency mode caps concurrency, enables chunked prefill aggressively, and considers [[Concept - Speculative Decoding]] for low-batch latency-critical paths (chat, agents) — recall spec decode only helps when the GPU has spare compute, i.e. at low batch, and can *reduce* throughput at high batch, so don't apply it to the throughput-mode config. If a single deployment must serve both regimes well, consider [[Concept - Prefill-Decode Disaggregation]] rather than compromising one config for both. *Expected:* two different configs for two different SLOs, not a single "balanced" one. *Deviation:* a single config that claims to satisfy both a tight TTFT and maximum throughput is almost certainly under-benchmarked at the tail.

6. **Decide sharding, then re-benchmark from step 2.** If weights don't fit on the target GPU count, prefer [[Concept - Tensor and Pipeline Parallelism|tensor parallelism]] within a node (it needs NVLink-class bandwidth for its per-layer all-reduce) and pipeline parallelism across nodes where interconnect is slower. Before adding more GPUs to "fix" a throughput problem, verify the all-reduce isn't already the bottleneck — TP scaling that doesn't improve throughput proportionally is a communication-bound symptom, not a compute one. Every change from steps 4-6 invalidates the previous benchmark; re-run step 2's sweep after each change and compare the full latency distribution, not just the mean.

## Verification

The tuned config is done when: the concurrency sweep from step 2 shows the SLO holding at p90/p99 (not just p50) up to the target load; preemption count stays near zero at that load (confirming you're not silently trading latency for throughput via recompute); KV cache utilization sits in a stable band with headroom for burst traffic, not pinned at the ceiling; and the config has been validated against the *realistic* traffic trace from step 1, not the synthetic one. If quantization was part of the tuning, downstream task quality (not perplexity — see [[Gotchas - Quantization Quality Loss]]) has been checked, not just assumed unchanged.

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
