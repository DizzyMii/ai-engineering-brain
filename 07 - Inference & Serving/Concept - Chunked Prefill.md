---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [SARATHI, stall-free batching, chunked prefill scheduling]
summary: "Slicing long prefills into token-budget chunks interleaved with decode tokens so a new request's prefill can't stall everyone else's inter-token latency."
---

> **One-paragraph hook:** In plain [[Concept - Continuous Batching]], admitting a request with a 4,000-token prompt means running its entire prefill as one giant forward pass in the middle of an otherwise-smooth decode loop — and every other in-flight request's next token waits behind it. Chunked prefill fixes this by capping how many tokens the scheduler is allowed to process per iteration and slicing long prefills into pieces that fit, filling any leftover budget with decode tokens from requests already running. It is the difference between "one big request occasionally freezes everyone" and "the GPU stays smoothly busy on a mix of work every step."

## The mechanism

Continuous batching re-forms the running batch every decode iteration, admitting newly-arrived requests as soon as there is room. The catch: admitting a request means prefilling it first, and prefill is a single forward pass over the *entire* prompt — for a 4K-token prompt, that's a compute-bound pass that dwarfs the cost of a normal decode step (one token per sequence). If the scheduler simply inserts that prefill into the next iteration, the GPU spends that whole iteration on the new request's prefill, and every currently-decoding sequence sees its inter-token latency spike — a stall visible to users as a stutter in an otherwise steady stream.

SARATHI (Agrawal et al. 2023) and its production form SARATHI-Serve (2024) solve this with a single knob: a **token budget** per iteration (`max_num_batched_tokens`). The scheduler:

1. Computes how many tokens it can process this iteration without exceeding the budget.
2. Fills that budget first with decode tokens from all in-flight sequences (one token each — cheap, and these have latency SLOs riding on them).
3. Uses whatever budget remains to process a **chunk** of a pending prefill — if a 4K-token prompt doesn't fit in the remaining budget, only the next `budget - decode_tokens` tokens of it are processed this iteration; the rest waits for subsequent iterations.
4. Repeats until the prefill is fully consumed, at which point that request joins the decode pool.

```
iteration budget = 512 tokens, 3 requests decoding, 1 new 4096-token prefill pending

iter 1: [d1][d2][d3]  + prefill chunk[0:509]     (509 + 3 = 512)
iter 2: [d1][d2][d3]  + prefill chunk[509:1018]
iter 3: [d1][d2][d3]  + prefill chunk[1018:1527]
   ...                                            (8 iterations to consume 4096)
iter 8: [d1][d2][d3]  + prefill chunk[3563:4072]
iter 9: [d1][d2][d3]  + prefill chunk[4072:4096] -> prefill DONE, request joins decode pool
```

This is "stall-free batching": no single iteration is ever dominated by one request's prefill, because prefill work is capped and diluted across many iterations, interleaved with the decode tokens that have a tight latency budget.

## In practice

The token budget is the entire tuning surface, and it is a direct trade: a **larger** budget lets each iteration make more progress on pending prefills, improving prefill throughput and lowering [[Reference - Inference Performance Math|TTFT]] for waiting requests, but it lets more prefill tokens leak into any one iteration, reintroducing decode-latency jitter. A **smaller** budget keeps decode smooth (low, predictable TPOT) but chops prefills into more pieces, adding per-chunk scheduling overhead and slowing how fast new requests get through prefill. There is no universally correct value — it's set against the [[Concept - Latency, Throughput, and Cost in LLM Serving|TTFT/TPOT SLO]] you're targeting, exactly the tuning exercise described in [[Playbook - Tuning an LLM Serving Deployment]].

Chunked prefill is now the default scheduling mode in vLLM V1 and is implemented across the major engines as part of [[Breakdown - vLLM]]'s scheduler and its peers — it stopped being an optional feature and became how continuous batching is done at all, because unchunked prefill's jitter is unacceptable for any latency-sensitive workload.

It composes with two neighboring techniques rather than competing with them. With [[Concept - Automatic Prefix Caching]], a prefill whose prefix already hits the cache skips those chunks outright — the token budget only has to cover the uncached suffix. And it sits as the *interleaving* answer to a problem that [[Concept - Prefill-Decode Disaggregation]] answers by *physical separation*: chunked prefill shares one GPU pool between prefill and decode work by time-slicing it every iteration, while disaggregation puts prefill and decode on entirely different GPUs so neither's scheduling can touch the other's latency at all. Chunked prefill is the cheaper, single-pool fix; disaggregation is the more expensive, cleaner one — teams usually adopt chunked prefill first and disaggregate only once they need to hit TTFT and TPOT targets that chunked prefill's inherent trade-off can't satisfy simultaneously.

The underlying reason chunking works at all traces back to why prefill and decode have opposite bottlenecks in the first place: prefill is compute-bound (it wants to saturate tensor-core FLOPs, see [[Concept - The Roofline Model]]) while decode is memory-bandwidth-bound (it wants to amortize the HBM weight read across a big batch) — see [[Concept - Prefill and Decode Phases]]. Because they stress different hardware resources, mixing a slice of one into a batch dominated by the other doesn't force a hard resource conflict the way naively running two prefills back to back would.

## Failure modes

- **Budget set too low starves prefill.** Every request's prefill takes many more iterations to complete, TTFT for new requests climbs, and under sustained load the queue of not-yet-prefilled requests can grow faster than the scheduler drains it — visible as rising queue depth and TTFT even though decode-side TPOT looks fine.
- **Budget set too high reintroduces the original stall.** If the budget is large enough that a full (or near-full) prefill chunk fits in one iteration alongside the decode tokens, you're back to the pre-SARATHI failure mode: periodic latency spikes on all in-flight decodes exactly when a large prompt is admitted. This is easy to miss in aggregate throughput metrics and only shows up in p99 inter-token latency — [[Concept - Latency, Throughput, and Cost in LLM Serving|watch the tail, not the mean]].
- **Under capacity-planning pressure, teams reach for [[Concept - LLM Load Testing and Capacity Planning|coarse concurrency limits]] instead of tuning the budget**, which trades away throughput unnecessarily; the budget is a finer, more correct lever than blanket admission throttling for this specific interference problem.

## The non-obvious

The token budget is not really a "prefill" setting or a "decode" setting — it's a single shared resource that the scheduler apportions between two workloads with opposite bottlenecks every iteration, and that framing is what tells you how to tune it: watch KV utilization and queue depth (are prefills backing up?) *and* p99 inter-token latency (are decodes stalling?) simultaneously, because moving the budget in either direction always trades one against the other. There is no setting that maximizes both, which is exactly the signal that tells a team it's time to stop tuning this knob and move to prefill-decode disaggregation instead.

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
