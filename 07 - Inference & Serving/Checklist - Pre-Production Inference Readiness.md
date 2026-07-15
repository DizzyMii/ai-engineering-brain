---
tags: [checklist, domain/inference-serving, level/core]
aliases: [LLM serving launch checklist, inference go-live checklist]
summary: "Pre-flight verification list before an LLM serving deployment takes real traffic: correctness, capacity, reliability, and observability."
---

# Checklist - Pre-Production Inference Readiness

## Correctness

- [ ] Chat template rendering is diffed against the model card's reference template and matches exactly, token for token
- [ ] BOS is added exactly once — verified it isn't added by both the tokenizer and the chat template
- [ ] EOS token ID(s) are configured and confirmed to actually fire on a live generation, not just present in config
- [ ] Configured stop strings are tested against a generation deliberately constructed so the stop pattern straddles a token boundary
- [ ] Special/added tokens (BOS, EOS, tool-call tags, thinking/reasoning delimiters) are filtered from user-visible output but preserved for any downstream parser
- [ ] Sampling defaults (temperature, top_p, top_k, penalties) are pinned in server config and documented, not left to implicit per-request defaults

## Capacity

- [ ] Max concurrency at the target SLO has been measured under a realistic prompt/output length distribution, not estimated from a spec sheet
- [ ] KV cache headroom leaves margin for the longest context allowed by `max_model_len`, not just the average observed request
- [ ] Behavior is verified when every live request simultaneously hits `max_model_len` at once (worst-case KV pressure)
- [ ] A backpressure/queueing policy and an explicit overload response (e.g. HTTP 429) exist as an alternative to silent out-of-memory failure

## Reliability

- [ ] Liveness and readiness probes are wired to the orchestrator and reflect actual model-serving health, not just process-alive
- [ ] Every request carries a hard per-request timeout and a hard `max_tokens` cap
- [ ] Generation is cancelled server-side when the client disconnects mid-stream
- [ ] The preemption/recompute path has been exercised under real load, not only verified at idle

## Quantization (only if the served model is quantized)

- [ ] Quantized model quality is validated on downstream task metrics — coding, tool-calling, math, or the production eval suite — not on perplexity alone

## Observability

- [ ] TTFT, TPOT, throughput, queue depth, KV cache utilization, and preemption count are all emitted as metrics
- [ ] Per-request tracing captures prompt and output with PII redaction applied before storage
- [ ] Alert thresholds are set on tail latency (p90/p99), not only on the mean

## Versioning and determinism

- [ ] Model weights, engine version, quantization recipe, and chat template are pinned together as one immutable deployment tag
- [ ] The seed and determinism policy is documented so evals and any caching layer key against it correctly

## Why these items

**BOS-doubling** is on this list because it's a silent-degradation bug, not a crash: a tokenizer that auto-prepends BOS plus a chat template that also prepends it shifts every downstream position by one, producing output that's measurably worse but still plausible enough to pass a casual smoke test — the exact bug class that survives code review and shows up as an unexplained quality regression weeks later.

**Stop strings tested against boundary-straddling generations** is here because the failure only appears under the traffic pattern most dev testing skips: a real [[Concept - Streaming Detokenization]] pipeline detokenizes and matches stop patterns on text, not token IDs, so a stop sequence that happens to split across a token boundary in production (and never did in a short manual test) leaks into the visible transcript or truncates output early.

**Generation cancellation on client disconnect** is on this list because without it, every abandoned request — a closed tab, a timed-out client — still runs to completion server-side, burning full decode compute and GPU-hours for tokens nobody will ever read; at scale this is a direct, avoidable cost leak, not a theoretical one.

**Downstream-task validation of quantized models, not just perplexity** is here because perplexity is a documented weak proxy: a 4-bit quantized model can show under 1% WikiText perplexity delta while losing double-digit points on coding or tool-calling benchmarks, and that gap is invisible to anyone checking only the metric that's cheapest to compute.

**Backpressure/429 instead of silent OOM** is on this list because an engine that simply falls over under load takes down every in-flight request, not just the one that tipped it over — an explicit overload response degrades gracefully for the requests already being served while rejecting new ones cleanly.

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
