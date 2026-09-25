---
tags: [concept, domain/production-ops, level/frontier]
aliases: [LLM load testing, capacity planning, goodput, latency knee, open-loop load test]
summary: "Token-aware load testing and SLO-driven capacity sizing for LLM endpoints: TTFT/TPOT, the latency knee, and Little's Law."
---

# Concept - LLM Load Testing and Capacity Planning

> **One-paragraph hook:** You can size a REST endpoint with "requests per second × latency". You can't size an LLM endpoint that way. One request holds a GPU slot for seconds to minutes, latency is a non-linear function of how many *other* requests are in flight, and cost and compute scale with *tokens*, not calls. Load testing an LLM means driving realistic token distributions with a realistic arrival process until you find the concurrency where latency falls off a cliff, then sizing replicas back from there with headroom. Get the load model wrong and every number you report is a comforting lie.

## The mechanism

**The metrics that matter**, always reported as distributions (at least p50/p95/p99, never the mean):

- **TTFT**, time to first token. Dominated by prefill (processing the input prompt) plus any queue wait. Prefill is *compute*-bound and scales roughly linearly with input length until the GPU's FLOP ceiling saturates. [[Concept - Latency, Throughput, and Cost in LLM Serving]] has the full decomposition.
- **TPOT / ITL**, time per output token (inter-token latency). This is the *decode* phase, and it's **memory-bandwidth bound**: each decode step streams the full model weights plus the [[Concept - KV Cache]] out of HBM to produce one token. From [[Concept - The Roofline Model]], the single-stream floor is

$$\text{TPOT}_{\min} \approx \frac{\text{model\_bytes} + \text{kv\_bytes per token}}{\text{HBM bandwidth}}$$

  A 70B model in fp16 is ~140 GB and an H100 sustains ~3.35 TB/s, so single-stream TPOT bottoms out near $140\text{e}9 / 3.35\text{e}12 \approx 42\text{ ms}$ (~24 tok/s) before any KV traffic. Batching spreads the weight read across concurrent sequences, and that's *why* throughput climbs with concurrency.
- **Throughput**, both req/s and aggregate tokens/s. They peak at different concurrencies.
- **Goodput**, the req/s that *actually meet the SLO* under load. It's the number that matters and the one naive benchmarks never report.

**The saturation curve (the latency knee).** With [[Concept - Continuous Batching]], raising concurrency lets the scheduler pack more sequences into each step, so aggregate throughput rises and TTFT stays flat. That holds until the KV cache fills or the batch hits the compute roof. After that, new arrivals *queue*, queue wait takes over TTFT, and latency explodes while throughput plateaus. That inflection is the **knee**.

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

**Capacity from an SLO: Little's Law.** The number of in-flight requests a system holds is $L = \lambda \times W$ (arrival rate × average time in system). So:

1. From load tests, find the **max concurrency per replica** at which p99 TTFT and p99 TPOT *still* meet the SLO (the knee, minus a safety margin).
2. Compute demand: $\text{concurrency\_demand} = \text{peak\_QPS} \times \text{avg\_hold\_time}$, where hold time is the full request latency (the seconds a request occupies a slot; for LLMs mostly `output_tokens × TPOT`).
3. $\text{replicas} = \lceil \text{concurrency\_demand} / \text{safe\_concurrency\_per\_replica} \rceil + \text{headroom}$.

Headroom covers cold-start lag (a new replica takes minutes to warm; see [[Concept - Autoscaling LLM Inference]]) and the burst tail. On Kubernetes each replica is one or more whole GPUs ([[Concept - GPU Orchestration on Kubernetes]]), so the arithmetic maps straight to card count and $/hr.

## In practice

Drive load with token-aware tools: vLLM's `benchmark_serving.py` (from [[Breakdown - vLLM]]), Anyscale's **LLMPerf**, NVIDIA's **GenAI-Perf**, or `k6`/Locust with a custom LLM client. Feed them the *actual* input/output length distributions from production traces (a ShareGPT-style mixture or your own logged token counts). A fixed 512-in/128-out synthetic produces numbers that don't survive real traffic.

Hold the serving-engine knobs constant across a sweep. [[Concept - Chunked Prefill]] and the prefill/decode chunk budget shift the TTFT-vs-TPOT balance, so a benchmark that changes them mid-run is comparing two different systems. Watch the engine's own saturation signals as you push: vLLM exposes `num_requests_waiting` (queue depth) and `gpu_cache_usage_perc` (KV pressure), and the knee is where `num_requests_waiting` starts climbing off zero. Sweep concurrency (or arrival rate) in steps, record the full latency CDF at each step, and plot goodput against load to find the knee empirically. Aim the operating point at ~70–80% of knee concurrency so a diurnal spike doesn't push you over.

## Failure modes

- **Unrealistic length distributions.** Fixed-size prompts hide that TTFT scales with input and hold time scales with output. Your knee moves by 2–3× when real long-context requests show up. *Detection:* compare benchmark token histograms with production traces before trusting any capacity number.
- **Reporting averages.** Mean latency looks fine while p99 is 10× worse, and users live on the tail. *Detection:* reject any capacity report without p95/p99.
- **Ignoring TTFT under concurrency.** Measuring TTFT at concurrency=1 and assuming it holds under load. It doesn't; past the knee, queue wait dominates.
- **Zero headroom.** Size exactly at the knee and the first traffic spike goes off the latency cliff and cascades into a queue-collapse outage.

## The non-obvious

**Closed-loop load tests lie. Use open-loop.** The default load-tester design is *closed-loop*: N worker threads each send their next request only after the previous one returns. That throttles itself. Offered load backs off the moment the system slows down, so a closed-loop test **can never reproduce the queue buildup behind a real outage**. It draws a smooth, flattering latency curve and hides the knee completely. Production traffic is *open-loop*: requests arrive on a roughly Poisson process that doesn't care whether you're keeping up, so past the knee queues grow without bound. If your load generator can't hold a fixed *arrival rate* (as opposed to fixed concurrency), it's measuring a system that doesn't exist. It's the most common reason a capacity plan that "passed load testing" collapses on launch day.

A corollary: decode is bandwidth-bound and prefill is compute-bound, so the *same* GPU has two different bottlenecks depending on your traffic's input/output ratio. Summarization (long input, short output) is prefill-heavy and saturates FLOPs. Chat and agent workloads (short input, long output) are decode-heavy and saturate HBM bandwidth. No single capacity number covers both, so size each workload class separately.

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
