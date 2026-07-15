---
tags: [concept, domain/production-ops, level/core]
aliases: [LLM Cost Optimization, Token Cost Engineering, LLM Unit Economics]
summary: "Modeling and controlling the marginal $/request of an LLM app: pricing asymmetry, cost drivers, caching/routing levers, and attribution."
---

> **One-paragraph hook:** An LLM feature's cost isn't a fixed infrastructure line item the way a database server is — it scales per request, per token, and per user in ways that can 10-100x overnight from a bug nobody would call a "performance regression" anywhere else in the stack. Cost engineering is treating $/request as a first-class metric with the same rigor as latency: modeled, monitored, attributed, and defended with concrete levers, not discovered at the end of the month on an invoice.

## The mechanism

The base cost model is simple and worth having memorized:

$$\text{cost}_{\text{call}} = n_{\text{in}} \cdot p_{\text{in}} + n_{\text{out}} \cdot p_{\text{out}}$$

where $n_{\text{in}}$/$n_{\text{out}}$ are input/output token counts and $p_{\text{in}}$/$p_{\text{out}}$ are the per-token prices. The asymmetry matters: output tokens typically price at 3-5x the input rate, because generation is autoregressive and compute-per-token bound while input processing is parallelizable prefill (see [[Concept - KV Cache]] for the serving-side reason prefill is cheaper per token than decode). Reasoning models complicate the formula further — they bill hidden "thinking" tokens that never appear in the visible completion, so a short visible answer can still carry a large output-token charge.

Real magnitudes as of 2026: frontier models run roughly \$2.5-15 per million input tokens and \$10-75 per million output tokens; small/cheap models run roughly \$0.1-0.6 per million tokens. Two levers move the effective price down without touching the base rate: batch APIs (offline, non-interactive processing) run at roughly 50% off, and [[Concept - Prompt Caching]] discounts the cached-input portion of a call by roughly 90%. Both are volume/latency-for-cost trades, not free lunches — batch APIs sacrifice immediacy, and prompt caching only pays off when a prefix is reused verbatim across calls.

## In practice

The real cost driver in most production apps is not generation length — it's input volume, because RAG context and conversation history get resent on every single call. An agent loop compounds this: each of its $N$ steps resends a monotonically growing context (prior tool results, prior reasoning), so total cost for one agentic action grows roughly quadratically in the number of steps even if each individual call looks cheap. Retries and self-consistency sampling multiply the same call by $k$; verbose, unconstrained outputs inflate $n_{\text{out}}$ directly; and per-user system prompts (a user's name or session data inlined at the front of the prompt) defeat prefix-based prompt caching by making every user's "identical" prompt byte-different from the next.

The levers, roughly in order of impact-to-effort: [[Concept - Prompt Caching]] for repeated prefixes, [[Concept - Semantic Caching]] to skip the model call entirely on near-duplicate requests, [[Concept - Model Routing and Cascades]] to send easy queries to a cheap model and escalate only when needed, hard `max_tokens` caps, structured-output schemas that constrain verbosity by construction, context pruning against [[Concept - Context Rot]] so stale history isn't resent forever, and the batch API for anything that doesn't need a synchronous response.

Attribution is what turns a single "total spend" number into an actionable one: tag every call with tenant, user, feature, and trace ID (the same identifiers [[Concept - LLM Observability and Tracing]] attaches at the span level) so cost dashboards can be sliced by any of them. This is what makes "fully-loaded cost per request" — and from it, per-customer margin — a computable unit-economics metric rather than a guess. The mechanics of this tagging plus atomic per-tenant budget enforcement are worked through concretely in [[Snippet - Token Cost Attribution and Budget Enforcement]].

Whether to reduce cost by owning inference hardware directly rather than paying per-token is a separate, larger decision — covered in [[Decision - Self-Hosting vs Managed LLM API]] — that only pays off above a sustained utilization floor.

## Failure modes

**Runaway agent loops or retry storms.** An unbounded tool-call loop or a naive retry-without-backoff can turn a single user action into hundreds of calls, producing bill spikes in the 10-100x range within hours — see [[Gotchas - LLM Production Operations]] for the detection signature (a spike in tokens-per-request outliers, not just total spend). **No per-tenant caps.** Without an enforced budget per tenant, one customer's misbehaving integration or abusive usage pattern eats the margin on every other customer, and the first signal is often the invoice, not an alert. **Floating-alias cost misattribution.** A cost dashboard keyed on a floating model alias rather than the dated snapshot silently mis-prices requests the moment the provider repoints the alias to a model with a different price — see [[Concept - Model Lifecycle and Versioning]] for why the dated snapshot has to be the join key everywhere, cost included.

## The non-obvious

The instinct is to optimize the model choice or the prompt wording first, because those feel like the "AI" parts of the cost problem. In practice the highest-leverage fix is usually structural: capping `max_tokens` to something close to the actual p95 output length (not a generous ceiling "just in case"), and fixing the system prompt to be byte-stable across users so prefix caching actually engages. Neither requires touching the model or the core prompt content, and both are typically a bigger cost lever than switching to a cheaper model — because a cheaper model still pays the full price on every wasted token, while a fixed cap or a cache hit removes the token entirely.

## Connections

- [[Concept - LLMOps]] — cost governance is one of the core stack layers LLMOps names; this note is the mechanism and math behind it.
- [[Concept - Semantic Caching]] — the strongest lever for skipping a model call entirely on repetitive workloads.
- [[Concept - Model Routing and Cascades]] — the lever for paying frontier prices only on the queries that need frontier capability.
- [[Snippet - Token Cost Attribution and Budget Enforcement]] — the runnable implementation of the attribution and per-tenant budget mechanics described above.
- [[Concept - Prompt Caching]] — the ~90% cached-input discount that depends on keeping the prompt prefix byte-stable.
- [[Concept - Context Rot]] — why unbounded context growth is both a quality and a cost problem, not just the latter.
- [[Decision - Self-Hosting vs Managed LLM API]] — the larger structural decision for when owning GPU capacity beats per-token pricing.
- [[Gotchas - LLM Production Operations]] — the catalog of concrete incidents (retry storms, cache false-hits, reservation throttling) that cost engineering exists to prevent.
- [[Concept - KV Cache]] — the serving-side mechanism that makes input tokens cheaper than output tokens in the first place.
- [[Concept - LLM Observability and Tracing]] — the source of the per-call attribution tags (tenant, user, feature, trace ID) cost dashboards are sliced by.
- [[Concept - Model Lifecycle and Versioning]] — why cost has to be keyed on the dated model snapshot rather than a floating alias.

## Sources
- OpenAI, Anthropic, and Google provider pricing pages (as of 2026, volatile — date-stamp any cited figure at time of use) — the source for the input/output price-asymmetry magnitudes cited above.
- Kaplan, J. et al. (2020) — "Scaling Laws for Neural Language Models" — the compute-cost intuition (decode is sequential and FLOPs-per-token bound in a way prefill is not) underlying the input/output price asymmetry.
