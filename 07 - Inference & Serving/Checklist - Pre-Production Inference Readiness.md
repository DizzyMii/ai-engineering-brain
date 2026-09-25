---
tags: [checklist, domain/inference-serving, level/core]
aliases: [LLM serving launch checklist, inference go-live checklist]
summary: "Pre-flight verification list before an LLM serving deployment takes real traffic: correctness, capacity, reliability, and observability."
---

# Checklist - Pre-Production Inference Readiness

## Correctness

- [ ] Rendered chat template diffed against the model card's reference template; it matches token for token
- [ ] BOS added once, and only once: confirm the tokenizer and the chat template aren't both adding it
- [ ] EOS token ID(s) configured and seen to fire on a live generation (being present in config isn't enough)
- [ ] Stop strings tested against a generation built so the stop pattern straddles a token boundary
- [ ] Special/added tokens (BOS, EOS, tool-call tags, thinking/reasoning delimiters) filtered from user-visible output but kept for any downstream parser
- [ ] Sampling defaults (temperature, top_p, top_k, penalties) pinned in server config and documented, never left to implicit per-request defaults

## Capacity

- [ ] Max concurrency at the target SLO measured under a realistic prompt/output length distribution, not estimated from a spec sheet
- [ ] KV cache headroom covers the longest context `max_model_len` allows, and not only the average observed request
- [ ] Behavior verified when every live request hits `max_model_len` at once (worst-case KV pressure)
- [ ] A backpressure/queueing policy and an explicit overload response (e.g. HTTP 429) exist, so overload doesn't end in a silent out-of-memory failure

## Reliability

- [ ] Liveness and readiness probes wired to the orchestrator and reporting actual model-serving health, beyond process-alive
- [ ] Hard per-request timeout and hard `max_tokens` cap on every request
- [ ] Generation cancelled server-side when the client disconnects mid-stream
- [ ] Preemption/recompute path exercised under real load, not only checked at idle

## Quantization (only if the served model is quantized)

- [ ] Quantized model quality validated on downstream task metrics (coding, tool-calling, math, or the production eval suite), not on perplexity alone

## Observability

- [ ] TTFT, TPOT, throughput, queue depth, KV cache utilization and preemption count all emitted as metrics
- [ ] Per-request tracing captures prompt and output, with PII redacted before storage
- [ ] Alert thresholds set on tail latency (p90/p99), not only on the mean

## Versioning and determinism

- [ ] Model weights, engine version, quantization recipe and chat template pinned together as one immutable deployment tag
- [ ] Seed and determinism policy documented so evals and any caching layer key against it correctly

## Why these items

**BOS-doubling** is a silent-degradation bug. It doesn't crash. A tokenizer that auto-prepends BOS plus a chat template that also prepends it shifts every downstream position by one. Output gets measurably worse but stays plausible enough to pass a casual smoke test, so the bug survives code review and turns up weeks later as an unexplained quality regression.

**Boundary-straddling stop strings** only fail under traffic that most dev testing skips. A real [[Concept - Streaming Detokenization]] pipeline detokenizes and matches stop patterns on text, not token IDs. A stop sequence that splits across a token boundary in production (and never did in a short manual test) either leaks into the visible transcript or truncates output early.

**Cancellation on client disconnect**: without it, every abandoned request (a closed tab, a timed-out client) still runs to completion server-side. That's full decode compute and GPU-hours spent on tokens nobody will read, a direct and avoidable cost leak at scale.

**Downstream-task validation for quantized models**, because perplexity is a documented weak proxy. A 4-bit quantized model can show under 1% WikiText perplexity delta while losing double-digit points on coding or tool-calling benchmarks. Anyone checking only the cheapest metric never sees that gap.

**Backpressure/429 over silent OOM**: an engine that falls over under load takes down every in-flight request, including all the ones that didn't tip it over. An explicit overload response keeps serving the requests already in flight and rejects new ones cleanly.

## Connections

- [[Playbook - Tuning an LLM Serving Deployment]] — the procedure that produces the tuned config this checklist verifies before go-live.
- [[Gotchas - LLM Serving in Production]] — the collected failure modes each checklist item exists specifically to catch ahead of time.
- [[Reference - Inference Performance Math]] — the formulas behind the capacity-section measurements (KV headroom, max concurrency).
- [[Concept - Sampling and Decoding Parameters]] — the mechanism behind the pinned-sampling-defaults correctness item.
- [[Concept - LLM Observability and Tracing]] — the metrics and tracing infrastructure the observability section requires to already exist.
- [[Concept - Nondeterminism in LLM Inference]] — the reason a documented determinism policy is a checklist item rather than an afterthought.
- [[Concept - Automatic Prefix Caching]] — cache correctness and isolation belong in a fuller correctness audit alongside the template and stop-string checks here.
- [[Concept - Streaming Detokenization]] — the mechanism behind the stop-string-straddling and special-token-filtering checks.
- [[Concept - Tool Use and Function Calling]] — tool-call tag filtering is specifically load-bearing for agent-facing deployments hitting this checklist.
