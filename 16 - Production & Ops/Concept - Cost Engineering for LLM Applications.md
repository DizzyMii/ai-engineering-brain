---
tags: [concept, domain/production-ops, level/core]
aliases: [LLM Cost Optimization, Token Cost Engineering, LLM Unit Economics]
summary: "Modeling and controlling the marginal $/request of an LLM app: pricing asymmetry, cost drivers, caching/routing levers, and attribution."
---

> **One-paragraph hook:** An LLM feature's cost isn't a fixed infrastructure line item like a database server. It scales per request, per token and per user, and it can jump 10-100x overnight from a bug nobody elsewhere in the stack would call a "performance regression". Cost engineering means treating $/request as a primary metric with the same rigor as latency: modeled, monitored, attributed and defended with concrete levers, instead of discovered on the invoice at the end of the month.

## The mechanism

The base cost model is simple and worth memorizing:

$$\text{cost}_{\text{call}} = n_{\text{in}} \cdot p_{\text{in}} + n_{\text{out}} \cdot p_{\text{out}}$$

$n_{\text{in}}$/$n_{\text{out}}$ are input/output token counts and $p_{\text{in}}$/$p_{\text{out}}$ the per-token prices. The asymmetry matters. Output tokens typically cost 3-5x the input rate, because generation is autoregressive and bound by compute per token, while input goes through parallelizable prefill ([[Concept - KV Cache]] has the serving-side reason prefill is cheaper per token than decode). Reasoning models complicate it further: they bill hidden "thinking" tokens that never show up in the visible completion, so a short answer can still carry a large output-token charge.

Real magnitudes as of 2026: frontier models run roughly \$2.5-15 per million input tokens and \$10-75 per million output tokens, and small/cheap models roughly \$0.1-0.6 per million tokens. Two levers lower the effective price without touching the base rate. Batch APIs (offline, non-interactive processing) run at roughly 50% off, and [[Concept - Prompt Caching]] discounts the cached-input part of a call by roughly 90%. Neither is free. Batch APIs give up immediacy, and prompt caching only pays when a prefix is reused verbatim across calls.

## In practice

In most production apps the main cost driver is input volume, not generation length, because RAG context and conversation history get resent on every call. Agent loops make it worse. Each of $N$ steps resends a context that only grows (prior tool results, prior reasoning), so the total cost of one agentic action grows roughly quadratically in the number of steps even when each call looks cheap. Retries and self-consistency sampling multiply the same call by $k$. Verbose, unconstrained outputs inflate $n_{\text{out}}$ directly. And per-user system prompts (a user's name or session data inlined at the top) defeat prefix-based prompt caching, since every user's "identical" prompt is now byte-different from the next.

The levers, roughly in order of impact for the effort: [[Concept - Prompt Caching]] for repeated prefixes; [[Concept - Semantic Caching]] to skip the model call entirely on near-duplicate requests; [[Concept - Model Routing and Cascades]] to send easy queries to a cheap model and escalate only when needed; hard `max_tokens` caps; structured-output schemas that limit verbosity by construction; context pruning against [[Concept - Context Rot]] so stale history isn't resent forever; and the batch API for anything that doesn't need a synchronous answer.

Attribution turns a single "total spend" number into something you can act on. Tag every call with tenant, user, feature and trace ID (the same identifiers [[Concept - LLM Observability and Tracing]] attaches at the span level) so cost dashboards can be sliced by any of them. That makes "fully loaded cost per request", and from it per-customer margin, a unit-economics metric you can compute instead of guess. [[Snippet - Token Cost Attribution and Budget Enforcement]] works through the tagging and atomic per-tenant budget enforcement in code.

Owning inference hardware instead of paying per token is a separate, larger decision, covered in [[Decision - Self-Hosting vs Managed LLM API]], and it only pays off above a sustained utilization floor.

## Failure modes

**Runaway agent loops or retry storms.** An unbounded tool-call loop or naive retry-without-backoff can turn one user action into hundreds of calls, with bill spikes in the 10-100x range within hours. [[Gotchas - LLM Production Operations]] has the detection signature: a spike in tokens-per-request outliers, beyond total spend.

**No per-tenant caps.** Without an enforced budget per tenant, one customer's misbehaving integration or abusive usage eats the margin on every other customer, and the first signal is often the invoice, not an alert.

**Floating-alias cost misattribution.** A cost dashboard keyed on a floating model alias instead of the dated snapshot silently misprices requests as soon as the provider repoints the alias to a model with a different price. [[Concept - Model Lifecycle and Versioning]] explains why the dated snapshot has to be the join key everywhere, cost included.

## The non-obvious

The instinct is to optimize model choice or prompt wording first, because those feel like the "AI" part of the cost problem. In practice the fix that pays most is usually in the plumbing. Cap `max_tokens` close to the actual p95 output length (not a generous ceiling "just in case"), and make the system prompt byte-stable across users so prefix caching actually kicks in. Neither touches the model or the core prompt content, and both are typically a bigger lever than switching to a cheaper model. A cheaper model still pays full price on every wasted token; a cap or a cache hit removes the token.

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
