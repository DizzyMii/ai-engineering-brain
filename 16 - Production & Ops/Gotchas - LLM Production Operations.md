---
tags: [gotchas, domain/production-ops, level/unicorn]
aliases: [LLM production pitfalls, LLM ops gotchas, runaway bill]
summary: "Hard-won pitfalls of running LLM apps in production: gateways, caching, cost, versioning, retries, streaming, and provider quirks."
---

# Gotchas - LLM Production Operations

Symptom-first, ordered by how much money or downtime each one costs when it bites. Each links to the note where the mechanism is treated in full.

## 1. A single unbounded agent loop ran up a 10–100× bill overnight

**Symptom:** the monthly spend graph has a vertical wall; one feature or one tenant accounts for nearly all of it.
**Cause:** an agent loop with no depth cap kept calling the model, each turn appending the previous output so context grew monotonically ($O(n^2)$ tokens over $n$ turns), or a [[Concept - Prompt Injection]] payload told the model to emit a huge output / recurse. Cost is token-driven ([[Concept - Cost Engineering for LLM Applications]]), so unbounded tokens = unbounded dollars.
**Fix:** hard per-request and per-tenant token caps, a `max_tokens` on every call, an agent loop-depth/step limit, and a circuit breaker on cumulative spend. Enforce the tenant cap atomically (see the budget snippet), not per-pod.
**Detection:** alert on tokens-per-request and cost-per-request *outliers* (p99, not mean); a runaway shows as a fat right tail hours before the invoice does.

## 2. A retry storm turned a 30-second provider blip into a self-inflicted outage

**Symptom:** upstream returns a burst of 429/503, your system retries, load *increases*, the provider stays saturated, and a transient blip becomes a sustained outage with a 20× bill spike.
**Cause:** synchronized, unbounded retries with no jitter — every client backs off on the same schedule and re-fires in lockstep (thundering herd), amplifying the original perturbation instead of damping it.
**Fix:** exponential backoff with **full jitter**, a hard attempt cap, a circuit breaker that fast-fails to a fallback, and honoring `Retry-After`. See [[Pattern - Resilient LLM Request Handling]].
**Detection:** retry-rate and in-flight-request metrics spiking in step with upstream error rate; the giveaway is that your request volume *rose* while the provider was failing.

## 3. A floating model alias silently changed behavior overnight

**Symptom:** no deploy on your side, yet outputs shifted — a downstream JSON parser started failing, refusal rate jumped, or eval scores moved.
**Cause:** you pinned to a floating alias (`gpt-4o`, `claude-3-5-sonnet-latest`) and the provider repointed it under you. See [[Lore - When the Model Changed Under You]].
**Fix:** pin the exact **dated snapshot** (`gpt-4o-2024-08-06`), treat the model as an unstable third-party dependency, and run a golden-set canary probe on a schedule.
**Detection:** continuous diff of a fixed golden prompt set against a stored baseline (embedding similarity / judge score); a change with no deploy of yours = the model moved.

## 4. The semantic cache served a confidently wrong answer

**Symptom:** a user got a fluent, authoritative answer to the *wrong* question.
**Cause:** a [[Concept - Semantic Caching]] false hit — two prompts embedded just above the similarity threshold but mean different things ("capital of Austria" vs "capital of Australia"), so the cache returned a neighbor's completion. Highest-pain failure because it is *silent* and *confident*.
**Fix:** raise the threshold (typical safe operating point ~0.95–0.97 cosine, validated per domain), include model id + prompt-template version + tenant in the cache key, and log hit-similarity for audit.
**Detection:** sample cached hits into an offline judge; watch the distribution of hit similarities and alert on hits clustering near the threshold floor.

## 5. Scale-to-zero caused a 5-minute cold-start outage under a burst

**Symptom:** the first burst after an idle window hangs or times out for minutes.
**Cause:** scaling to zero means a cold replica must pull 10s–100s of GB of weights, load VRAM, capture CUDA graphs, and warm up — 1–10 minutes for a large model. See [[Concept - Autoscaling LLM Inference]].
**Fix:** keep a warm minimum floor (never true zero for latency-sensitive paths), pre-pull weights to a PVC/cache, and use predictive/scheduled scaling for diurnal patterns. Back it with a queue + backpressure, not the assumption of instant scale.
**Detection:** cold-start duration metric vs. burst inter-arrival time; if scale-up lag > your burst spacing you will always be behind.

## 6. Streaming retries double-charged and duplicated the output

**Symptom:** traces show two completions for one request; the user saw text repeat or garble; billing double-counted.
**Cause:** a retry fired *after* tokens had already streamed, so the model generated (and billed) the response twice, and the client concatenated two partial streams.
**Fix:** never retry once the first token has been emitted unless you carry an idempotency key; classify "timeout before first token" (retriable) separately from "stream stalled mid-generation" (not blindly retriable). See [[Pattern - Resilient LLM Request Handling]].
**Detection:** duplicate-completion detector on traces (same request_id, two GENERATION spans); duplicated-billing anomaly in cost attribution.

## 7. Prompt caching broke because a timestamp was in the system prompt

**Symptom:** your prompt-cache hit rate is ~0% and input cost never dropped despite a long stable system prompt.
**Cause:** [[Concept - Prompt Caching]] keys on a **byte-stable prefix**; appending a timestamp, a UUID, or per-user data at the *top* of the prompt invalidates the cacheable prefix on every call (cache is prefix-based, so one early byte-change busts everything after it).
**Fix:** keep the cacheable prefix byte-identical; move volatile content (timestamps, user IDs) to the *end* of the prompt, after the stable instructions and few-shot block.
**Detection:** provider `cache_read`/`cache_creation` token counts in the usage object; a near-zero cache-read fraction on a repetitive workload is the tell.

## 8. `max_tokens` over-reservation throttled throughput

**Symptom:** the system throttles requests and reports "at capacity" while GPUs sit well below the rate-limit ceiling.
**Cause:** admission/rate-limiting reserved the full `max_tokens` (e.g., 4096) per request even though 95% of generations finish in a few hundred tokens, so the reservation math thinks the system is full when it is mostly idle. See [[Concept - Autoscaling LLM Inference]] and rate-limit design.
**Fix:** reserve near the **p95 output length**, not the max; reconcile to actual usage after completion; let continuous batching preempt rather than reserving worst-case.
**Detection:** effective utilization (actual tokens / reserved tokens) far below 1.0; throttling events with low real GPU utilization.

## 9. Provider rate-limit headers were ignored, so you invited 429 storms

**Symptom:** repeated 429s that you could have seen coming; traffic gets choppy near tier boundaries.
**Cause:** the client ignored `x-ratelimit-remaining-tokens` / `-requests` and `Retry-After`, so it kept firing into a nearly-exhausted budget instead of shaping traffic under it.
**Fix:** read the remaining-budget headers, throttle proactively before hitting zero, and back off by `Retry-After` on a 429. A gateway ([[Concept - Semantic Caching]]-capable proxies included) can centralize this.
**Detection:** correlate 429 rate against the remaining-budget headers; a 429 while remaining-tokens was already near zero means you drove past a signal you had.

## 10. Cost estimates were wrong for non-OpenAI models because you used tiktoken

**Symptom:** your pre-flight cost estimates and dashboards disagree with the invoice, worst on non-English text and code.
**Cause:** you counted tokens with `tiktoken` (OpenAI's tokenizer) for Anthropic/Google/Llama models, which tokenize differently — counts can diverge 20–30%+ on non-Latin scripts and code. Estimation is fine; *billing* off an estimate is not.
**Fix:** bill from the provider-returned `usage` object (authoritative); use a local tokenizer only for a pre-flight reservation, and use the *right* tokenizer per model family.
**Detection:** reconcile estimated vs. billed tokens per model; a systematic per-family offset points straight at a tokenizer mismatch.

## Connections
- [[Concept - Semantic Caching]] — gotchas #4 and #9 live here; false hits and cache keying are its core failure surface.
- [[Pattern - Resilient LLM Request Handling]] — the fix for #2 and #6; retries, jitter, breakers, and idempotency are its whole subject.
- [[Concept - Cost Engineering for LLM Applications]] — #1, #8, and #10 are all cost-attribution and token-accounting failures it governs.
- [[Concept - Prompt Caching]] — #7 is a direct consequence of its byte-stable-prefix keying rule.
- [[Concept - Autoscaling LLM Inference]] — #5 and #8 stem from cold-start lag and reservation policy it manages.
- [[Concept - Prompt Injection]] — the amplification vector behind the worst case of #1 (token-blowup attacks).
- [[Gotchas - Agents in Production]] — agent-loop and tool-call pitfalls that compound #1; the sibling gotchas note one layer up the stack.
- [[Lore - When the Model Changed Under You]] — the war-story backing for #3, silent provider drift.

## Sources
- Amazon Builders' Library — *Timeouts, retries, and backoff with jitter* (Brooker). The full-jitter result behind gotcha #2.
- Anthropic / OpenAI prompt-caching docs (2024–2025) — the prefix-stability keying that gotcha #7 violates.
- Chen, Zaharia & Zou (2023) — *How Is ChatGPT's Behavior Changing over Time?* Documents the silent-drift phenomenon behind #3.
