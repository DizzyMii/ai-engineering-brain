---
tags: [concept, domain/inference-serving, level/core]
aliases: [serving economics, TTFT, TPOT, goodput]
summary: "How TTFT, TPOT, and throughput trade off, and how to derive dollars-per-million-tokens from GPU price and decode throughput."
---
# Concept - Latency, Throughput, and Cost in LLM Serving
> **One-paragraph hook:** Batch size, quantization, prefix caching, speculative decoding: every serving decision ends up as a point on one curve, tokens per second across the fleet versus how long a single user waits. If you can read that curve and price a point on it in dollars per million tokens, you can tell "we deployed a model" apart from "we deployed a model we can afford to run at the traffic we actually have."

## The mechanism
Start from the asymmetry in [[Concept - Prefill and Decode Phases]]: decode is memory-bandwidth-bound, prefill is compute-bound. After that, serving cost comes down to a few identities. For output tokens:

$$
\text{\$ per 1M output tokens} = \frac{\text{GPU \$/hr} / 3600}{\text{aggregate decode tokens/sec}} \times 10^6
$$

Worked example: an H100 at roughly $2.50/hr sustaining ~2,500 output tokens/sec across a full continuous-batched workload gives $(2.50/3600) / 2500 \times 10^6 \approx \$0.28$ per million output tokens at the raw hardware level, before margin, overhead, or redundancy. Nearly all the movement in that number comes from the denominator. Anything that raises aggregate decode throughput (bigger batch, faster HBM, quantization) divides the cost directly.

Input and output tokens are priced so differently because of how each phase runs. Prefill is one parallel pass with high arithmetic intensity, so it's compute-rich and comparatively cheap per token. Decode is serialized, one token at a time, and every step re-reads the whole weight matrix from HBM no matter how much useful work that step does. Hosted API pricing runs **roughly 3-5x higher for output tokens than input tokens** as a direct pass-through of that compute-vs-bandwidth cost structure, not as a business-model choice.

The tension: batch size is the main throughput lever, because it amortizes the fixed HBM weight-read across more concurrent sequences (the mechanism [[Concept - Continuous Batching]] exploits). But each extra sequence also lengthens that step's wall-clock time, which raises per-token latency (TPOT) for every in-flight user. So there's no single best batch size. There's a latency-throughput Pareto frontier, and an SLO (e.g., "TPOT under 50ms") picks a point on it:

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
The levers and which way they move the frontier:

| Lever | Effect |
|---|---|
| Quantization (see [[Concept - Post-Training Quantization Formats]]) | Smaller weights → more batch and/or longer context fits per GPU → throughput up, cost down |
| [[Concept - Automatic Prefix Caching]] | Skips recomputing shared prompt prefix → TTFT down, cost down |
| [[Concept - Speculative Decoding]] | Cuts per-token latency at *low* batch; can actively *reduce* throughput at high batch (verifying rejected draft tokens burns compute that a compute-saturated GPU doesn't have spare) |
| [[Concept - Prefill-Decode Disaggregation]] | Separates the two phases onto dedicated hardware pools, hitting a tight TTFT *and* tight TPOT simultaneously instead of trading one for the other |

Production money leaks through utilization. A decode-bound service at batch size 4 can sit under **10% Model FLOPs Utilization**, since decode's arithmetic intensity at small batch is nowhere near the GPU's compute roof. You're paying for nearly all of that HBM bandwidth and compute and not using it. Serving tuning (see [[Playbook - Tuning an LLM Serving Deployment]]) is mostly the work of pushing effective batch size up toward the knee without blowing the latency SLO.

## Failure modes
**Optimizing raw throughput instead of goodput.** Under a real latency contract, cost-effectiveness is measured by **goodput**: requests per second that meet the (TTFT, TPOT) SLO. Raw tokens/sec can look impressive while a growing share of requests blow their latency budget and get discarded or retried by the client. Goodput would have caught it. Teams that dashboard only throughput find out from user complaints instead of monitoring.

**Treating the input-token discount as free.** Input tokens are cheap relative to output, so it's tempting to treat prompt length as nearly free. Long prompts still add real prefill compute and queueing delay to TTFT, and at extreme context lengths the $O(N^2)$ attention term in prefill starts to dominate. Input tokens are cheap *per token*, not free in aggregate.

**Choosing batch size on mean latency instead of tail.** Batching fattens the tail of the latency distribution: a request that lands just as a large prefill is admitted eats that iteration's stall. Tune against p50 and ignore p90/p99, and you'll systematically underestimate the SLO violation rate.

## The non-obvious
Speculative decoding is the first latency fix most practitioners reach for, and it **can make throughput worse**. It only has spare compute to spend at low batch, where the GPU is memory-bound and FLOPs sit idle. At high batch the GPU is already compute-saturated, so the extra verification FLOPs compete directly with the batch's useful work. Labs therefore deploy it selectively on low-QPS, latency-critical paths (e.g., an interactive assistant) and don't use it as a blanket throughput optimization for bulk serving. Whether it's a win or a regression depends entirely on which regime of the Pareto frontier you're already in.

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
