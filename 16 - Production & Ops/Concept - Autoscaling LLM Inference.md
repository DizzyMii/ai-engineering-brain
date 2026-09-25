---
tags: [concept, domain/production-ops, level/advanced]
aliases: [KEDA autoscaling, inference autoscaling]
summary: "Why CPU-based HPA fails for LLM serving and how to scale replicas on queue depth, KV-cache occupancy, and a cold-start-aware policy."
---

> **One-paragraph hook:** A standard Horizontal Pod Autoscaler watching CPU utilization is close to useless for LLM inference. The bottleneck is GPU compute and memory bandwidth, not CPU, and by the time a naive signal notices load, a one-to-ten-minute cold start for a large model means the burst is over before new capacity shows up. Autoscaling LLM inference means picking a signal that tracks the real bottleneck, wiring it through something like KEDA, and designing the policy around a cold-start constant no traditional web-service autoscaler was built for. All of it sits on the GPU node pool that [[Concept - GPU Orchestration on Kubernetes]] provisions.

## The mechanism

During decode, a GPU-bound serving process can run at 90%+ GPU utilization while host CPU sits at 10–20%. CPU was never the constrained resource, so CPU-based HPA either never scales or scales on noise that has nothing to do with load. Worse, serving latency is highly non-linear near saturation. Under [[Concept - Continuous Batching]], throughput climbs roughly linearly with concurrency until the KV cache or compute saturates, and then queue wait and time-to-first-token explode: the "latency knee". A signal that can't see the knee coming will always scale too late.

The right signals come from demand and from the engine itself: queue depth / pending-request count, concurrent in-flight requests, or KV-cache occupancy (the memory structure behind [[Concept - KV Cache]]). [[Breakdown - vLLM]] exposes these directly as Prometheus metrics, e.g. `vllm:num_requests_waiting` and `vllm:gpu_cache_usage_perc`. KEDA (Kubernetes Event-Driven Autoscaling) polls an external metrics source like Prometheus through a `ScaledObject` custom resource and turns the query result into an HPA-compatible external metric, which the controller uses to set replica count. The trigger becomes "the engine's own reported waiting count crossed N", not some proxy unrelated to the bottleneck.

Cold start for a large model (pulling weights, filling VRAM, CUDA context init and, for engines that use it, CUDA-graph capture) commonly takes one to ten minutes. Kubernetes HPA's default reactivity assumes second-scale container starts. The inequality that matters: metric lag (time from the load shift to the autoscaler's decision, plus time for the new replica to become ready) has to be shorter than cold-start time, or every scale-up lands after the burst that triggered it. If cold start is three minutes and traffic noise cycles faster than that, autoscaling on that noise only adds cost. The fix is a warm floor sized to absorb the noise band, with autoscaling kept for sustained shifts longer than the cold-start constant.

## In practice

A typical policy is a KEDA `ScaledObject` with a Prometheus trigger on average `num_requests_waiting`. `minReplicaCount` is a warm floor sized from the concurrency ceiling [[Concept - LLM Load Testing and Capacity Planning]] finds at the load-test knee. `maxReplicaCount` is bounded by node-pool size and cost budget. An asymmetric `stabilizationWindowSeconds` (fast scale-up, slow scale-down, e.g. 300s) prevents flapping. Predictive or scheduled scaling (a cron trigger, or a custom controller) handles known diurnal patterns like business-hours chat traffic by pre-warming ahead of the metric-based trigger. GPU class, meaning how much concurrency one replica holds before the knee ([[Decision - Selecting GPUs for Training and Inference]]), sets the denominator in `replicas ≈ ceil(peak_concurrency / safe_concurrency_per_replica)`. Ray Serve's queue-based autoscaler (target ongoing-requests-per-replica) and managed provisioned-throughput offerings are other implementations of the same signal choice.

## Failure modes

**Flapping.** A noisy raw signal with no stabilization window scales replicas up and straight back down, paying the cold-start cost again and again for no lasting benefit.

**Scaling too late.** Metric lag exceeds cold-start time, so users hit the latency cliff well before new capacity is ready. It's the most common autoscaling failure for LLM inference, and why a warm floor is standard practice instead of purely reactive scaling.

**OOM on scale-up.** A new replica's batch-size or max-context-length config doesn't fit the free VRAM on the node it lands on, especially in a heterogeneous pool. It starts, OOMs immediately, and the autoscaler happily launches another replica that does the same.

**Naive threshold, variable request cost.** A queue-depth-of-10 threshold means one thing for a batch of 50-token completions and another for 4,000-token ones. Thresholds tuned on one traffic mix silently misfire on another.

**Scale-to-zero cold-start outage.** Scale a low-traffic deployment to zero and rely on request-triggered scale-up, and whoever sends the first request during a burst gets a multi-minute outage. [[Gotchas - LLM Production Operations]] has the incident shape. Check the [[Reference - LLM Production SLOs and Latency Budgets]] target you're actually trying to hit before choosing scale-to-zero at all.

Reservation-based throttling interacts badly with autoscaling as well. If [[Concept - Rate Limiting and Quota Design]] reserves `max_tokens` per in-flight request instead of a realistic p95 output length, the system looks saturated and scales up long before it actually is.

## The non-obvious

A generation holds a replica's concurrency slot for seconds to minutes, not milliseconds, which makes it closer to a long-poll connection than a normal web request. So a replica's "safe operating concurrency" isn't a percentage of GPU utilization. Utilization can read 95%+ while TTFT is already unacceptable, or read deceptively low while decode is purely memory-bandwidth-bound and compute looks idle. The safe figure is a concrete concurrency number, found empirically just below the latency knee in a realistic load test. Teams that autoscale on GPU-utilization percentage instead of the engine's own queue/cache-occupancy metrics are optimizing a number that doesn't track what they care about, and they typically find out during an incident, not in testing.

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
