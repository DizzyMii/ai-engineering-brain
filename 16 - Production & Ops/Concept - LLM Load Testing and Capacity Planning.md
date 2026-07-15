---
tags: [concept, domain/production-ops, level/frontier]
aliases: [LLM load testing, capacity planning, goodput, latency knee, open-loop load test]
summary: "Token-aware load testing and SLO-driven capacity sizing for LLM endpoints: TTFT/TPOT, the latency knee, and Little's Law."
---

# Concept - LLM Load Testing and Capacity Planning

> **One-paragraph hook:** A REST endpoint you can size with "requests per second × latency." An LLM endpoint you cannot, because a single request holds a GPU slot for seconds-to-minutes, latency is a non-linear function of how many *other* requests are in flight, and cost and compute scale with *tokens*, not calls. Load testing an LLM means driving realistic token distributions at a realistic arrival process until you find the concurrency where latency falls off a cliff, then sizing replicas back from that point with headroom. Get the load model wrong and every number you report is a comforting lie.

## The mechanism

**The metrics that matter** (all reported as distributions, at least p50/p95/p99 — never the mean):

- **TTFT** — time to first token. Dominated by prefill (processing the input prompt) plus any queue wait. Prefill is *compute*-bound and scales roughly linearly with input length until the GPU's FLOP ceiling saturates. See [[Concept - Latency, Throughput, and Cost in LLM Serving]] for the full decomposition.
- **TPOT / ITL** — time per output token (inter-token latency). This is the *decode* phase and it is **memory-bandwidth bound**, not compute-bound: each decode step must stream the full model weights plus the [[Concept - KV Cache]] out of HBM to produce one token. By the [[Concept - The Roofline Model]], the single-stream floor is

$$\text{TPOT}_{\min} \approx \frac{\text{model\_bytes} + \text{kv\_bytes per token}}{\text{HBM bandwidth}}$$

  A 70B model in fp16 is ~140 GB; an H100 sustains ~3.35 TB/s, so single-stream TPOT bottoms out near $140\text{e}9 / 3.35\text{e}12 \approx 42\text{ ms}$ (~24 tok/s) before you add any KV traffic. Batching amortizes the weight read across concurrent sequences, which is *why* throughput climbs with concurrency.
- **Throughput** — both req/s and aggregate tokens/s. These peak at different concurrencies.
- **Goodput** — the req/s that *actually meet the SLO* under load. This is the number that matters and the one naive benchmarks never report.

**The saturation curve (the latency knee).** With [[Concept - Continuous Batching]], as you raise concurrency the scheduler packs more sequences per step, so aggregate throughput rises while TTFT stays flat — until the KV cache fills or the batch hits the compute roof. Past that point new arrivals *queue*, TTFT is now dominated by queue wait, and latency explodes while throughput plateaus. That inflection is the **knee**.

```
    aggregate throughput            p99 TTFT
 tok/s ^        ,--•---- (flat)  ms  ^                ,•  (queue wait
       |      ,'                     |              ,'    dominates)
       |    ,'                       |           ,-'
       |  ,'                         |    ___,--'
       |,'                           |__--'  (flat: prefill only)
       +-----------------> conc      +-----------------> conc
            ^ knee                        ^ knee
   safe operating point = just left of the knee (both curves)
```

**Capacity from an SLO — Little's Law.** The number of in-flight requests a system holds is $L = \lambda \times W$ (arrival rate × average time-in-system). So:

1. From load tests, find the **max concurrency per replica** where p99 TTFT and p99 TPOT *still* meet the SLO (that's the knee, minus a safety margin).
2. Compute demand: $\text{concurrency\_demand} = \text{peak\_QPS} \times \text{avg\_hold\_time}$, where hold time is the full request latency (seconds a request occupies a slot — for LLMs this is dominated by `output_tokens × TPOT`).
3. $\text{replicas} = \lceil \text{concurrency\_demand} / \text{safe\_concurrency\_per\_replica} \rceil + \text{headroom}$.

Headroom covers cold-start lag (a new replica takes minutes to warm — see [[Concept - Autoscaling LLM Inference]]) and the burst tail. On Kubernetes each replica is one or more whole GPUs (see [[Concept - GPU Orchestration on Kubernetes]]), so this arithmetic maps straight to card count and $/hr.

## In practice

Drive load with token-realistic tools: vLLM's `benchmark_serving.py` (from [[Breakdown - vLLM]]), Anyscale's **LLMPerf**, NVIDIA's **GenAI-Perf**, or `k6`/Locust with a custom LLM client. Feed them the *actual* input/output length distributions from your production traces — a ShareGPT-style mixture or your own logged token counts — not a fixed 512-in/128-out synthetic, which produces numbers that do not survive contact with real traffic.

Hold the serving-engine knobs constant across a sweep: [[Concept - Chunked Prefill]] and the prefill/decode chunk budget shift the TTFT-vs-TPOT balance, so a benchmark that changes them mid-run is comparing two different systems. Watch the engine's own saturation signals while you push — vLLM exposes `num_requests_waiting` (queue depth) and `gpu_cache_usage_perc` (KV pressure); the knee is where `num_requests_waiting` starts climbing off zero. Sweep concurrency (or arrival rate) in steps, record the full latency CDF at each, and plot goodput vs load to locate the knee empirically. Target the operating point at ~70–80% of knee concurrency so a diurnal spike doesn't push you over.

## Failure modes

- **Unrealistic length distributions.** Fixed-size prompts hide the reality that TTFT scales with input and hold-time scales with output; your knee moves by 2–3× when real long-context requests arrive. *Detection:* compare benchmark token histograms against production traces before trusting any capacity number.
- **Reporting averages.** The mean latency looks fine while p99 is 10× worse; users live on the tail. *Detection:* refuse any capacity report without p95/p99.
- **Ignoring TTFT-under-concurrency.** Measuring TTFT at concurrency=1 and assuming it holds under load — it doesn't, queue wait dominates past the knee.
- **Zero headroom.** Sizing exactly at the knee means the first traffic spike falls off the latency cliff and cascades into a queue-collapse outage.

## The non-obvious

**Closed-loop load testing lies; use open-loop.** The default load-tester design is *closed-loop*: N worker threads each send the next request only after the previous one returns. This self-throttles — the offered load automatically backs off exactly when the system slows down, so a closed-loop test **can never reproduce the queue buildup that causes a real outage.** It draws a smooth, flattering latency curve and hides the knee entirely. Production traffic is *open-loop*: requests arrive on a Poisson-ish process indifferent to whether you're keeping up, so queues grow without bound past the knee. If your load generator can't hold a fixed *arrival rate* (not fixed concurrency), it is measuring a system that doesn't exist. This is the single most common reason a capacity plan that "passed load testing" collapses on launch day.

A corollary: because decode is bandwidth-bound and prefill is compute-bound, the *same* GPU has two different bottlenecks depending on your traffic's input/output ratio. A summarization workload (long input, short output) is prefill-heavy and saturates FLOPs; a chat/agent workload (short input, long output) is decode-heavy and saturates HBM bandwidth. One capacity number cannot cover both — size each workload class separately.

## Connections

- [[Concept - Autoscaling LLM Inference]] — capacity planning sets the floor/ceiling and the scaling signal (queue depth) that autoscaling then actuates on.
- [[Reference - LLM Production SLOs and Latency Budgets]] — the SLO targets you size *against*; capacity planning is the inverse function of that budget.
- [[Concept - Continuous Batching]] — the batching scheduler is what makes the throughput-vs-concurrency curve rise, and what produces the knee when it saturates.
- [[Concept - KV Cache]] — KV memory is the usual capacity limit; the cache fills before compute does on long-context decode workloads.
- [[Concept - The Roofline Model]] — gives the hard TPOT floor (bandwidth-bound decode) that no amount of load tuning can beat.
- [[Concept - GPU Orchestration on Kubernetes]] — replica count from Little's Law becomes GPU node count and pod scheduling.
- [[Breakdown - vLLM]] — the reference serving engine whose `benchmark_serving` tool and `num_requests_waiting`/`gpu_cache_usage_perc` metrics you drive these tests with.
- [[Concept - Chunked Prefill]] — must be held constant across a benchmark because it moves the TTFT/TPOT tradeoff point.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — the underlying latency decomposition these load tests measure.

## Sources
- Kwon et al. (2023) — *Efficient Memory Management for LLM Serving with PagedAttention* (vLLM). Establishes continuous batching and the KV-cache-as-capacity-limit that produces the latency knee.
- Anyscale (2023) — **LLMPerf** benchmark harness. Popularized TTFT/TPOT/token-throughput as the standard LLM-serving metric triad.
- Little, J. D. C. (1961) — *A Proof for the Queuing Formula L = λW*. The queueing identity used to convert an SLO and arrival rate into replica count.
