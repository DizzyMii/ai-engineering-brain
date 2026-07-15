---
tags: [concept, domain/inference-serving, level/core]
aliases: [serving economics, TTFT, TPOT, goodput]
summary: "How TTFT, TPOT, and throughput trade off, and how to derive dollars-per-million-tokens from GPU price and decode throughput."
---
# Concept - Latency, Throughput, and Cost in LLM Serving
> **One-paragraph hook:** Every serving decision — batch size, quantization, prefix caching, speculative decoding — ultimately resolves to a point on one curve: how many tokens per second a fleet produces versus how long any individual user waits. Understanding that curve, and how to price a point on it in dollars per million tokens, is what separates "we deployed a model" from "we deployed a model we can afford to run at the traffic we actually have."

## The mechanism
Serving cost reduces to a small number of identities once you accept the asymmetry from [[Concept - Prefill and Decode Phases]]: decode is memory-bandwidth-bound and prefill is compute-bound. The cost identity for output tokens:

$$
\text{\$ per 1M output tokens} = \frac{\text{GPU \$/hr} / 3600}{\text{aggregate decode tokens/sec}} \times 10^6
$$

Worked example: an H100 at roughly $2.50/hr, sustaining ~2,500 output tokens/sec across a full continuous-batched workload, gives $(2.50/3600) / 2500 \times 10^6 \approx \$0.28$ per million output tokens at the raw hardware level — before margin, overhead, or redundancy. This number moves almost entirely through the denominator: anything that raises aggregate decode throughput (bigger batch, faster HBM, quantization) divides the cost directly.

**Why input and output tokens are priced so differently:** prefill is a single parallel pass with high arithmetic intensity — it's compute-rich and comparatively cheap per token. Decode is serialized, one token at a time, and bound by re-reading the entire weight matrix from HBM every step regardless of how much useful work that step does. This asymmetry is why hosted API pricing runs **roughly 3-5x higher for output tokens than input tokens** — it's not a business-model choice, it's a direct pass-through of the underlying compute-vs-bandwidth cost structure.

**The core tension** is that raising batch size is the main lever for throughput (it amortizes the fixed HBM weight-read across more concurrent sequences, exactly the mechanism [[Concept - Continuous Batching]] exploits), but every additional sequence in the batch also lengthens that step's wall-clock time, which raises every in-flight user's per-token latency (TPOT). There is no single "best" batch size — there is a latency-throughput Pareto frontier, and an SLO (e.g., "TPOT under 50ms") picks a point on it:

```
throughput
(tok/s)
    ^
    |                         .  saturation: compute-bound, TPOT
    |                    . '     rising fast for little more throughput
    |               . '
    |          . '        <- the "knee": best throughput per unit TPOT
    |     . '
    |. '
    +------------------------------------> TPOT (ms/token)
      small batch                 large batch
      (low throughput,            (high throughput,
       low latency)                 high latency)
```

## In practice
The levers and the direction they push the frontier:

| Lever | Effect |
|---|---|
| Quantization (see [[Concept - Post-Training Quantization Formats]]) | Smaller weights → more batch and/or longer context fits per GPU → throughput up, cost down |
| [[Concept - Automatic Prefix Caching]] | Skips recomputing shared prompt prefix → TTFT down, cost down |
| [[Concept - Speculative Decoding]] | Cuts per-token latency at *low* batch; can actively *reduce* throughput at high batch (verifying rejected draft tokens burns compute that a compute-saturated GPU doesn't have spare) |
| [[Concept - Prefill-Decode Disaggregation]] | Separates the two phases onto dedicated hardware pools, hitting a tight TTFT *and* tight TPOT simultaneously instead of trading one for the other |

Utilization is where money actually leaks in production: a decode-bound service running at batch size 4 can sit under **10% Model FLOPs Utilization**, because decode's arithmetic intensity at small batch is nowhere near the GPU's compute roof — nearly all of that HBM bandwidth and compute capacity is paid for and unused. The entire discipline of serving tuning (see [[Playbook - Tuning an LLM Serving Deployment]]) is pushing effective batch size up toward the knee without blowing through the latency SLO.

## Failure modes
**Optimizing raw throughput instead of goodput:** the metric that actually maps to cost-effectiveness under a real latency contract is **goodput** — requests per second that meet the (TTFT, TPOT) SLO — not raw tokens/sec. A configuration can post impressive raw throughput while a growing fraction of requests blow past their latency budget and get discarded or retried by the client; goodput is the number that would have caught it, and teams that dashboard only throughput find this out from user complaints instead of monitoring.

**Chasing the input-token discount for free:** because input tokens are cheap relative to output, it's tempting to treat prompt length as nearly free — but long prompts still add real prefill compute and queueing delay to TTFT, and at extreme context lengths the $O(N^2)$ attention term in prefill starts to dominate, so "cheap" input tokens are cheap *per token*, not free in aggregate.

**Batch-size decisions made on mean latency, not tail:** batching makes the latency distribution fatter-tailed (a request that lands right as a large prefill is admitted eats that iteration's stall), so tuning against p50 while ignoring p90/p99 systematically underestimates how bad the SLO violation rate actually is.

## The non-obvious
The single most counter-intuitive lesson in this domain is that **speculative decoding, which every practitioner reaches for first as a latency fix, can make throughput worse, not better** — because it only has spare compute to spend at low batch, where the GPU is memory-bound and FLOPs are sitting idle. At high batch the GPU is already compute-saturated, so the extra verification FLOPs speculative decoding spends compete directly with the batch's useful work. This is why labs deploy it selectively for low-QPS, latency-critical paths (e.g., an interactive assistant) rather than as a blanket throughput optimization for bulk serving — the same technique is a win or a regression depending entirely on which regime of the Pareto frontier you're already operating in.

## Connections
- [[Concept - Continuous Batching]] — the scheduling mechanism that actually captures the throughput side of the batch-size lever described here.
- [[Reference - Inference Performance Math]] — the formula sheet (KV bytes, decode step time, max concurrency) this note's cost derivation is built from.
- [[Concept - Cost Engineering for LLM Applications]] — the application-level layer above this: routing, caching, and budget enforcement built on top of the hardware cost floor this note derives.
- [[Concept - Unit Economics of LLM Products]] — how this per-token hardware cost feeds into product-level margin and pricing decisions.
- [[Concept - Token Price Deflation]] — the market-level trend (falling $/token over time) that this note's cost identity explains the mechanism behind.
- [[Concept - Speculative Decoding]] — the lever whose effect on throughput flips sign depending on batch regime, discussed above under the non-obvious section.
- [[Concept - The Roofline Model]] — the general compute-vs-bandwidth framework that explains why decode has this particular latency-throughput shape.
- [[Concept - Prefill-Decode Disaggregation]] — the architectural fix that decouples TTFT and TPOT instead of forcing a single-config tradeoff between them.
- [[Concept - Automatic Prefix Caching]] — a direct lever on TTFT and cost by skipping recomputation of shared prompt prefixes.
- [[Concept - Post-Training Quantization Formats]] — a direct lever on throughput and cost by shrinking the weight bytes decode must read every step.
- [[Playbook - Tuning an LLM Serving Deployment]] — the operational procedure for finding a deployment's actual position on the latency-throughput frontier described here.

## Sources
- Formulas and target figures (H100 pricing, decode throughput, MFU thresholds) reflect commonly cited 2026-era serving benchmarks and vendor pricing; treat exact $/hr and tok/s figures as illustrative and re-benchmark against current spot/on-demand pricing and your own workload before using them for capacity planning.
