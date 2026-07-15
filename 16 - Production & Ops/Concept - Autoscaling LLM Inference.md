---
tags: [concept, domain/production-ops, level/advanced]
aliases: [KEDA autoscaling, inference autoscaling]
summary: "Why CPU-based HPA fails for LLM serving and how to scale replicas on queue depth, KV-cache occupancy, and a cold-start-aware policy."
---

> **One-paragraph hook:** A standard Horizontal Pod Autoscaler watching CPU utilization is close to useless for LLM inference: the bottleneck is GPU compute and memory bandwidth, not CPU, and by the time a naive signal notices load, a one-to-ten-minute cold start for a large model means the burst is already over before new capacity arrives. Autoscaling LLM inference means picking a signal that tracks the real bottleneck, wiring it through something like KEDA, and designing the policy around a cold-start constant no traditional web-service autoscaler was built to respect — all layered on top of the GPU node pool [[Concept - GPU Orchestration on Kubernetes]] provisions.

## The mechanism

During decode, a GPU-bound serving process can sit at 90%+ GPU utilization while host CPU sits at 10–20% — CPU was never the constrained resource, so CPU-based HPA either never scales or scales on noise unrelated to actual load. Worse, LLM serving latency is highly non-linear near saturation: under [[Concept - Continuous Batching]], throughput climbs roughly linearly with concurrency until the KV-cache or compute saturates, at which point queue wait and time-to-first-token explode — the "latency knee." A signal that doesn't detect the approach to that knee will always scale too late.

The right signals are demand-side and engine-native: queue depth / pending-request count, concurrent in-flight requests, or KV-cache occupancy (the memory structure behind [[Concept - KV Cache]]). [[Breakdown - vLLM]] exposes these directly as Prometheus metrics, e.g. `vllm:num_requests_waiting` and `vllm:gpu_cache_usage_perc`. KEDA (Kubernetes Event-Driven Autoscaling) polls an external metrics source like Prometheus via a `ScaledObject` custom resource, translates the query result into an HPA-compatible external metric, and the controller adjusts replica count from it — so the trigger is "queue depth over the engine's own reported waiting count crossed N," not a proxy unrelated to the actual bottleneck.

Cold start for a large model — pulling weights, populating VRAM, CUDA context init, and (for engines that use it) CUDA-graph capture — commonly runs one to ten minutes, against a Kubernetes HPA default reactivity built around second-scale container starts. The controlling inequality: metric-lag (time from the load shift to the autoscaler's decision, plus time for the new replica to become ready) must be shorter than cold-start time, or the scale-up decision always arrives after the burst that triggered it has passed. If cold start is three minutes and traffic noise cycles faster than that, autoscaling on that noise band accomplishes nothing except cost — the fix is a warm floor sized to absorb the noise band, with autoscaling reserved for sustained shifts longer than the cold-start constant.

## In practice

A typical policy: a KEDA `ScaledObject` with a Prometheus trigger on average `num_requests_waiting`, `minReplicaCount` set to a warm floor sized from the concurrency ceiling [[Concept - LLM Load Testing and Capacity Planning]] finds at the load-test knee, `maxReplicaCount` bounded by node-pool size and cost budget, and an asymmetric `stabilizationWindowSeconds` — fast scale-up, slow scale-down (e.g. 300s) — to avoid flapping. Predictive/scheduled scaling (a cron trigger, or a custom controller) covers known diurnal patterns like business-hours chat traffic by pre-warming ahead of the metric-based trigger rather than waiting for it to fire. GPU class choice — how much concurrency a single replica can hold before hitting the knee, per [[Decision - Selecting GPUs for Training and Inference]] — sets the denominator in `replicas ≈ ceil(peak_concurrency / safe_concurrency_per_replica)`. Ray Serve's queue-based autoscaler (target ongoing-requests-per-replica) and managed provisioned-throughput offerings are alternative implementations of the same signal choice.

## Failure modes

**Flapping.** A noisy raw signal without a stabilization window causes replicas to scale up and immediately back down, repeatedly burning cold-start cost for no sustained benefit.

**Scaling too late.** Metric-lag exceeds cold-start time, so users hit the latency cliff well before new capacity is ready — the single most common autoscaling failure for LLM inference, and the reason a warm floor, not pure reactive scaling, is standard practice.

**OOM on scale-up.** A new replica's batch-size or max-context-length configuration doesn't fit the free VRAM on whatever node it lands on, especially in a heterogeneous node pool — it comes up, immediately OOMs, and the autoscaler happily spins up another replica that does the same thing.

**Naive threshold, variable request cost.** A raw queue-depth-of-10 threshold means something different for a batch of 50-token completions than a batch of 4,000-token ones; thresholds tuned on one traffic mix silently misfire on another.

**Scale-to-zero cold-start outage.** Scaling a low-traffic deployment to zero and relying on request-triggered scale-up to serve the first request produces a multi-minute outage for whoever hits that first request under a burst — see [[Gotchas - LLM Production Operations]] for the incident shape this produces, and check the [[Reference - LLM Production SLOs and Latency Budgets]] target you're actually trying to hit before choosing scale-to-zero at all.

Reservation-based throttling interacts badly with autoscaling too: if [[Concept - Rate Limiting and Quota Design]] reserves `max_tokens` per in-flight request rather than a realistic p95 output length, the system looks saturated and triggers scale-up long before it actually is.

## The non-obvious

A generation holds a replica's concurrency slot for seconds to minutes, not milliseconds — closer to a long-poll connection than a typical web request. That means the "safe operating concurrency" for a replica is not some percentage of GPU utilization, which can read 95%+ while TTFT is already unacceptable, or read deceptively low while decode is purely memory-bandwidth-bound and compute looks idle — it's the concrete concurrency figure found empirically just below the latency knee in a realistic load test. Teams that autoscale on GPU-utilization percentage instead of on the engine's own queue/cache-occupancy metrics are optimizing a number that doesn't track the thing they actually care about, and typically discover it during an incident rather than in testing.

## Connections

- [[Concept - GPU Orchestration on Kubernetes]] — the node pool and GPU-sharing layer replicas scale within; cold-start time here comes directly from that note's weight-loading mechanics.
- [[Concept - LLM Load Testing and Capacity Planning]] — the source of the safe-concurrency-per-replica figure that turns a target QPS into a replica count.
- [[Concept - Rate Limiting and Quota Design]] — shares the same `max_tokens`-reservation pitfall, and interacts directly with autoscaling by shaping how "load" is measured.
- [[Concept - Continuous Batching]] — the mechanism that produces the latency knee this note's scaling signal has to detect before it's crossed.
- [[Concept - KV Cache]] — `gpu_cache_usage_perc`, one of the two engine-native metrics this note recommends scaling on.
- [[Breakdown - vLLM]] — the serving engine whose Prometheus metrics are the concrete example of an engine-native scaling signal.
- [[Reference - LLM Production SLOs and Latency Budgets]] — the TTFT/TPOT targets that define what "too late" means for a scale-up decision.
- [[Gotchas - LLM Production Operations]] — the scale-to-zero cold-start outage and related pitfalls collected alongside this note's failure modes.
- [[Decision - Selecting GPUs for Training and Inference]] — the GPU-class choice that sets the per-replica concurrency ceiling used in capacity math.

## Sources

- KEDA project documentation — the event-driven autoscaling controller and `ScaledObject`/external-metrics mechanism described above.
- vLLM project documentation — the `num_requests_waiting` and `gpu_cache_usage_perc` Prometheus metrics used as scaling signals.
- Ray Serve documentation — the queue-based `target_num_ongoing_requests_per_replica` autoscaler as an alternative implementation of the same signal choice.
