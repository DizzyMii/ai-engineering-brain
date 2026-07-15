---
tags: [concept, domain/ai-economics, level/core]
aliases: [AI COGS, LLM product margins, gross margin on inference]
summary: "The per-query cost model behind an AI product's gross margin, why it trails SaaS, and the concrete levers that move it."
---
# Concept - Unit Economics of LLM Products

> **One-paragraph hook:** SaaS pricing was built on an assumption that no longer holds once an LLM sits in the request path: that the marginal cost of serving one more user-action is approximately zero. Every LLM call is a real, metered, variable cost — and a product's gross margin is now a function of prompt design, model choice, and the shape of its heaviest users, not just its price list. A team that doesn't instrument cost per request discovers its actual COGS the day the inference bill arrives, usually after pricing has already been locked into a contract.

## The mechanism

Classic SaaS gross margin (80-90%) rests on software's near-zero marginal cost: once built, serving the 10,000th customer costs almost nothing more than serving the 100th. An LLM call breaks that assumption because every request consumes metered compute — tokens in, tokens out, at a real $/M-token price. The result, per Bessemer's *State of AI* work, is that **LLM-native companies run gross margins around 65%** (E2, Bessemer, 2025), with ICONIQ Capital's January 2026 survey of AI-native companies putting the average at **52%**, up from 41% in 2024 and 45% in 2025 (E2, ICONIQ, single survey) — improving over time as models cheapen ([[Concept - Token Price Deflation]]), but still well short of legacy SaaS. ICONIQ's same survey found **model inference averages ~23% of total product cost** at scaling-stage AI companies, ahead of infrastructure/cloud (17%) and trailing only talent (26%) (E2, ICONIQ, Jan 2026) — inference is not a rounding error on the income statement, it is one of the largest line items.

**What drives cost per query:**
- **Token volume, split input vs. output.** Output tokens are typically priced 3-5x input tokens across major APIs, because generation is autoregressive and can't be batched as efficiently as prompt processing (see [[Concept - KV Cache]] and [[Concept - Continuous Batching]] for the serving-side reason).
- **Retries and self-consistency sampling.** Any pattern that calls the model N times to improve reliability multiplies COGS by N; see [[Concept - Pass@k and Sampling-Based Evaluation]] for the maj@k/self-consistency family this cost pattern is built on.
- **RAG overhead.** Every retrieval-augmented query pays for embedding calls plus retrieval infrastructure on top of the generation call itself — see [[Deep Dive - RAG Architectures]].
- **Reasoning models' hidden thinking tokens.** Extended-reasoning models generate internal chain-of-thought tokens the user never sees but the API bills for; these can run **5-20x the visible output token count** for a single answer, turning what looks like a short response into a long, expensive one.

## In practice

**Margin levers, each trading something for lower COGS:**
- **Prompt caching** — reusing the KV-cache state for a repeated prefix cuts cached-input pricing by up to ~90% versus fresh processing (see [[Concept - Prompt Caching]]). Free lever if your prompt structure has a stable, reusable prefix; requires redesigning prompts around a fixed-prefix/variable-suffix shape if it doesn't.
- **Semantic caching** — skip the model call entirely for queries semantically similar to ones already answered (see [[Concept - Semantic Caching]]). Trades a small risk of stale or mismatched answers for near-zero marginal cost on cache hits.
- **Model routing / cascades** — send the query to the cheapest model that can plausibly handle it, escalate to a frontier model only on failure or low-confidence signals. Trades average-case latency and engineering complexity for large COGS reduction on the (usually majority) easy-query tail.
- **Quantized / distilled small models** — serve a distilled or quantized version of a larger model for the bulk of traffic (see [[Concept - Post-Training Quantization Formats]], [[Concept - Knowledge Distillation]]). Trades some quality ceiling for throughput and cost.
- **Batching** — [[Breakdown - vLLM]] and continuous-batching serving stacks amortize fixed per-request overhead across concurrent requests, raising throughput per GPU-hour.

Each of these is covered mechanically in [[Concept - Cost Engineering for LLM Applications]]; this note is about *why* the margin problem exists, that note is about *how* to fix it.

**The power-user problem.** Flat-rate or per-seat pricing on a token-metered backend inverts the SaaS assumption that let flat pricing work in the first place: a small fraction of heavy users can consume far more compute than their subscription price covers, making them gross-margin-negative individually even while the blended average looks healthy. This is why AI coding tools — Cursor and Anthropic's own Claude Code among them — repeatedly repriced or introduced usage caps and overage pricing through 2025 (E2, contemporaneous reporting) after initial flat-rate plans proved unsustainable against the heaviest usage cohorts. The mechanism: unlimited-usage pricing was safe under SaaS because marginal cost was ~0; it is unsafe under token metering because marginal cost is real and unbounded per user.

**Deflation cuts both ways.** [[Concept - Token Price Deflation]] lowers the cost side of the margin equation over time — but two forces erode the gain before it reaches the bottom line: competition passes the savings through to customers as lower prices (a deflating cost structure in a competitive market becomes a deflating price, not a widening margin), and reasoning/agentic workflows raise token volume per task faster than unit price falls (a single agent task can issue dozens of tool calls and thinking passes where a simple query issued one). Net margin trajectory is a race between these two effects, not a guaranteed improvement — see [[Breakdown - Frontier Lab Economics]] for how this plays out one layer up the stack. Zoomed out further, whether the industry's [[Deep Dive - The AI Compute Buildout|physical compute buildout]] gets absorbed is exactly this race run at fleet scale: the buildout is a bet that served tokens keep 10x-ing faster than per-token margin erodes, which only holds if products like the ones this note describes actually clear a margin at volume.

**Measure per-feature, per-cohort — never blended.** A blended average cost-per-query hides the fact that one runaway agent workflow, one power-user segment, or one poorly-scoped RAG feature can be erasing the margin the rest of the product earns. The correct unit is something like *cost per resolved support ticket* or *cost per generated, merged pull request* — an outcome-denominated cost, not a request-denominated one — because request counts don't map cleanly to value delivered. See [[Playbook - Measuring AI ROI]] for the instrumentation this requires.

## Failure modes

- **Discovering COGS only when the monthly invoice arrives.** Teams that don't log token counts per request, per feature, per customer at the point of the call find out their actual gross margin a month late, after pricing commitments (annual contracts, flat-rate plans) are already locked in and can't be repriced quickly.
- **Pricing off average cost while power users are gross-margin-negative.** A healthy blended margin can coexist with a subset of customers who are actively unprofitable; if that subset grows disproportionately (which usage-based products tend to select for — your best, most-engaged customers are exactly the heaviest token consumers), the blended average degrades faster than a naive extrapolation predicts.
- **Ignoring reasoning-model thinking tokens in cost projections.** A team that budgets based on visible output token counts and later adopts an extended-reasoning model for quality reasons can see COGS jump 5-20x on the same feature without any change in visible behavior.

## The non-obvious

Gross margin on an LLM product is not a fixed property of the business model — it's a moving target set jointly by your *worst* users (the heavy-usage tail that flat pricing doesn't cover) and your *newest* model choice (every model upgrade resets the cost baseline, often upward, because newer models tend to reason more or generate more tokens per answer even when priced lower per token). This means unit economics has to be re-measured on a cadence tied to model releases and usage growth, not calculated once at launch and assumed stable. The teams that get burned are the ones that priced a plan against one model's cost profile and then upgraded the underlying model for quality reasons without re-pricing the plan.

## Connections

- [[Concept - Token Price Deflation]] — the downward pressure on the cost side of the unit-economics equation, and why it doesn't automatically translate to wider margins.
- [[Decision - Pricing Models for AI Products]] — the pricing-model choice (seat, usage, hybrid, outcome-based) that determines whether a given COGS structure is survivable.
- [[Breakdown - Frontier Lab Economics]] — the same margin dynamics one layer up the stack, where labs face their own version of this problem against training and compute capex.
- [[Playbook - Measuring AI ROI]] — the instrumentation playbook for the per-feature, per-cohort measurement this note argues is mandatory.
- [[Concept - Value Capture Across the AI Stack]] — situates app-layer margin numbers (52-65%) within the full stack's margin distribution.
- [[Concept - Outcome-Based Pricing]] — one resolution to the power-user problem: price the outcome, not the seat, so COGS and revenue scale together.
- [[Concept - Support Deflection Economics]] — a concrete, function-level worked example of cost-per-resolved-unit measurement in a specific vertical (support).
- [[Breakdown - The Cursor Ramp]] — the coding-tool repricing example cited above, examined in full as a case study.
- [[Concept - Cost Engineering for LLM Applications]] — the practical how-to for the margin levers (caching, routing, quantization) introduced here.
- [[Concept - Prompt Caching]] — mechanism detail behind the ~90% cached-input discount cited as a margin lever.
- [[Concept - Semantic Caching]] — mechanism detail behind the cache-hit-avoids-model-call lever.
- [[Breakdown - vLLM]] — the serving-engine internals (continuous batching, PagedAttention) that determine achievable throughput per GPU-hour and thus cost floor.
- [[Deep Dive - The AI Compute Buildout]] — the fleet-scale version of this note's margin race: whether the physical buildout gets absorbed depends on products clearing a per-token margin at the volume this note describes (cross-domain: trajectory).

## Sources

- Bessemer Venture Partners, State of AI report (2025) — LLM-native gross margins ~65%.
- ICONIQ Capital, State of AI: Bi-Annual Snapshot (Jan 2026) — average AI product gross margin 52% (41% 2024, 45% 2025); inference ~23% of cost structure at scaling stage.
- Contemporaneous reporting on AI coding-tool pricing changes (Cursor, Claude Code usage caps/overage pricing, 2025).
