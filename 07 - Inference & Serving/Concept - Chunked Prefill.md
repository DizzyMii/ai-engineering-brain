---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [SARATHI, stall-free batching, chunked prefill scheduling]
summary: "Slicing long prefills into token-budget chunks interleaved with decode tokens so a new request's prefill can't stall everyone else's inter-token latency."
---

> **One-paragraph hook:** In plain [[Concept - Continuous Batching]], admitting a request with a 4,000-token prompt means running its whole prefill as one giant forward pass in the middle of an otherwise smooth decode loop, and every other in-flight request's next token waits behind it. Chunked prefill caps how many tokens the scheduler may process per iteration, slices long prefills into pieces that fit, and fills leftover budget with decode tokens from requests already running. Without it, one big request occasionally freezes everyone. With it, the GPU stays busy on a mix of work every step.

## The mechanism

Continuous batching re-forms the running batch every decode iteration and admits new requests as soon as there's room. The catch is that admission means prefill first, and prefill is a single forward pass over the *entire* prompt. For a 4K-token prompt that's a compute-bound pass that dwarfs a normal decode step (one token per sequence). Drop it into the next iteration as-is and the GPU spends that whole iteration on the new request, while every decoding sequence sees its inter-token latency spike. Users see a stutter in an otherwise steady stream.

SARATHI (Agrawal et al. 2023) and its production form SARATHI-Serve (2024) fix this with one knob, a **token budget** per iteration (`max_num_batched_tokens`). Each iteration the scheduler:

1. Works out how many tokens it can process without exceeding the budget.
2. Fills the budget first with decode tokens from all in-flight sequences. That's one token each, cheap, and these carry latency SLOs.
3. Spends the remainder on a **chunk** of a pending prefill. If a 4K-token prompt doesn't fit, only the next `budget - decode_tokens` tokens get processed now; the rest waits for later iterations.
4. Repeats until the prefill is consumed, at which point the request joins the decode pool.

```
iteration budget = 512 tokens, 3 requests decoding, 1 new 4096-token prefill pending

iter 1: [d1][d2][d3]  + prefill chunk[0:509]     (509 + 3 = 512)
iter 2: [d1][d2][d3]  + prefill chunk[509:1018]
iter 3: [d1][d2][d3]  + prefill chunk[1018:1527]
   ...                                            (8 iterations to consume 4096)
iter 8: [d1][d2][d3]  + prefill chunk[3563:4072]
iter 9: [d1][d2][d3]  + prefill chunk[4072:4096] -> prefill DONE, request joins decode pool
```

That's "stall-free batching". Prefill work is capped and spread across many iterations, interleaved with the latency-sensitive decode tokens, so no single iteration is dominated by one request's prefill.

## In practice

The token budget is the whole tuning surface, and it's a direct trade. A **larger** budget makes more progress on pending prefills per iteration, which raises prefill throughput and lowers [[Reference - Inference Performance Math|TTFT]] for waiting requests, but more prefill tokens leak into each iteration and decode latency jitters again. A **smaller** budget keeps decode smooth (low, predictable TPOT) but chops prefills into more pieces, adds per-chunk scheduling overhead, and slows how fast new requests clear prefill. No value is universally right. You set it against the [[Concept - Latency, Throughput, and Cost in LLM Serving|TTFT/TPOT SLO]] you're targeting, which is the tuning exercise in [[Playbook - Tuning an LLM Serving Deployment]].

Chunked prefill is now the default scheduling mode in vLLM V1 and is implemented across the major engines, in [[Breakdown - vLLM]]'s scheduler and its peers. It stopped being optional and became how continuous batching is done, because unchunked prefill's jitter is unacceptable for any latency-sensitive workload.

It composes with two neighboring techniques. With [[Concept - Automatic Prefix Caching]], a prefill whose prefix hits the cache skips those chunks outright, so the budget only covers the uncached suffix. And it's the *interleaving* answer to a problem [[Concept - Prefill-Decode Disaggregation]] answers by *physical separation*. Chunked prefill time-slices one GPU pool between prefill and decode every iteration; disaggregation puts them on different GPUs so neither's scheduling can touch the other's latency. Chunking is the cheaper, single-pool fix and disaggregation the more expensive, cleaner one. Teams usually adopt chunked prefill first and disaggregate only when they need TTFT and TPOT targets that chunking's built-in trade-off can't meet at the same time.

Chunking works because prefill and decode have opposite bottlenecks. Prefill is compute-bound and wants to saturate tensor-core FLOPs (see [[Concept - The Roofline Model]]). Decode is memory-bandwidth-bound and wants to amortize the HBM weight read across a big batch (see [[Concept - Prefill and Decode Phases]]). Since they stress different hardware, mixing a slice of one into a batch dominated by the other avoids the hard resource conflict you'd get running two prefills back to back.

## Failure modes

- **Budget too low starves prefill.** Each prefill takes many more iterations, TTFT for new requests climbs, and under sustained load the queue of not-yet-prefilled requests can grow faster than the scheduler drains it. You see rising queue depth and TTFT while decode-side TPOT looks fine.
- **Budget too high brings the original stall back.** If a full or near-full prefill chunk fits in one iteration alongside the decode tokens, you're back to the pre-SARATHI failure: latency spikes on every in-flight decode whenever a large prompt is admitted. Aggregate throughput metrics hide this. It only shows in p99 inter-token latency, so [[Concept - Latency, Throughput, and Cost in LLM Serving|watch the tail, not the mean]].
- **Under capacity-planning pressure, teams reach for [[Concept - LLM Load Testing and Capacity Planning|coarse concurrency limits]] instead of tuning the budget.** That gives up throughput for no reason. For this specific interference problem the budget is a finer, more correct lever than blanket admission throttling.

## The non-obvious

The token budget belongs to neither prefill nor decode. It's one shared resource the scheduler splits every iteration between two workloads with opposite bottlenecks, and that tells you how to tune it. Watch KV utilization and queue depth (are prefills backing up?) *and* p99 inter-token latency (are decodes stalling?) together, because moving the budget either way trades one against the other. No setting maximizes both. Once you hit that wall, stop tuning this knob and move to prefill-decode disaggregation.

## Connections
- [[Concept - Continuous Batching]] — chunked prefill is a scheduling refinement on top of continuous batching, solving the interference problem plain iteration-level batching introduces.
- [[Concept - Prefill and Decode Phases]] — the compute-bound/memory-bound asymmetry between the two phases is *why* naive co-scheduling stalls and why chunking (mixing small amounts of each) works.
- [[Concept - Prefill-Decode Disaggregation]] — the alternative fix by physical separation rather than interleaving; teams graduate to this when the chunked-prefill budget trade-off stops meeting the SLO.
- [[Concept - Automatic Prefix Caching]] — a cached prefix shrinks the prefill that needs chunking in the first place, reducing pressure on the token budget.
- [[Breakdown - vLLM]] — the system where chunked prefill (via SARATHI-style scheduling) became the default batching mode.
- [[Reference - Inference Performance Math]] — TTFT and TPOT are exactly the two metrics the token budget trades against each other.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — the SLO framing that determines which side of the budget trade-off a deployment should favor.
- [[Playbook - Tuning an LLM Serving Deployment]] — the procedure that sets this budget in practice, alongside the other serving knobs.
- [[Concept - The Roofline Model]] — the compute-vs-bandwidth-bound distinction underlying why prefill and decode tokens can share a budget without fully competing for the same hardware resource.
- [[Concept - LLM Load Testing and Capacity Planning]] — where chunked-prefill tuning fits into the broader capacity-planning exercise for a deployment.

## Sources
- Agrawal et al. (2023) — *SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills*. Introduces chunked prefill and stall-free batching.
- Agrawal et al. (2024) — *Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve*. Production-grade chunked-prefill scheduling, now the default approach in vLLM V1.
