---
tags: [concept, domain/ai-economics, level/core]
aliases: [AI COGS, LLM product margins, gross margin on inference]
summary: "The per-query cost model behind an AI product's gross margin, why it trails SaaS, and the concrete levers that move it."
---
# Concept - Unit Economics of LLM Products

> SaaS pricing assumed the marginal cost of serving one more user action is roughly zero. Put an LLM in the request path and that stops being true. Every LLM call is a real, metered, variable cost, so a product's gross margin now depends on prompt design, model choice and the shape of its heaviest users, as well as its price list. A team that doesn't instrument cost per request finds out its actual COGS the day the inference bill arrives, usually after pricing is already locked into a contract.

## The mechanism

Classic SaaS gross margin (80-90%) rests on near-zero marginal cost: once the software is built, serving the 10,000th customer costs almost nothing more than serving the 100th. An LLM call breaks that, because every request burns metered compute: tokens in, tokens out, at a real $/M-token price. Per Bessemer's *State of AI* work, **LLM-native companies run gross margins around 65%** (E2, Bessemer, 2025). ICONIQ Capital's January 2026 survey of AI-native companies puts the average at **52%**, up from 41% in 2024 and 45% in 2025 (E2, ICONIQ, single survey). Margins improve as models get cheaper ([[Concept - Token Price Deflation]]) but remain well short of legacy SaaS. The same survey found **model inference averages ~23% of total product cost** at scaling-stage AI companies, ahead of infrastructure/cloud (17%) and behind only talent (26%) (E2, ICONIQ, Jan 2026). Inference is one of the largest line items on the income statement, far from a rounding error.

**What drives cost per query:**
- **Token volume, split input vs. output.** Output tokens typically cost 3-5x input tokens across major APIs, because generation is autoregressive and can't be batched as efficiently as prompt processing ([[Concept - KV Cache]] and [[Concept - Continuous Batching]] explain the serving side).
- **Retries and self-consistency sampling.** Any pattern that calls the model N times to improve reliability multiplies COGS by N. [[Concept - Pass@k and Sampling-Based Evaluation]] covers the maj@k/self-consistency family behind this cost.
- **RAG overhead.** Every retrieval-augmented query pays for embedding calls and retrieval infrastructure on top of the generation call (see [[Deep Dive - RAG Architectures]]).
- **Hidden thinking tokens in reasoning models.** Extended-reasoning models generate internal chain-of-thought the user never sees but the API bills for. These can run **5-20x the visible output token count** for one answer, so a short-looking response is a long, expensive one.

## In practice

**Margin levers, each trading something for lower COGS:**
- **Prompt caching.** Reusing KV-cache state for a repeated prefix cuts cached-input pricing by up to ~90% against fresh processing (see [[Concept - Prompt Caching]]). Free if your prompts already have a stable, reusable prefix. If not, you have to redesign them into a fixed-prefix/variable-suffix shape.
- **Semantic caching.** Skip the model call for queries semantically similar to ones already answered (see [[Concept - Semantic Caching]]). You accept a small risk of stale or mismatched answers in exchange for near-zero marginal cost on hits.
- **Model routing / cascades.** Send each query to the cheapest model that can plausibly handle it, and escalate to a frontier model only on failure or low confidence. Costs average-case latency and engineering complexity; saves a lot of COGS on the (usually majority) easy-query tail.
- **Quantized or distilled small models.** Serve a distilled or quantized version of a larger model for most traffic (see [[Concept - Post-Training Quantization Formats]], [[Concept - Knowledge Distillation]]). You give up some quality ceiling for throughput and cost.
- **Batching.** [[Breakdown - vLLM]] and other continuous-batching stacks spread fixed per-request overhead across concurrent requests, raising throughput per GPU-hour.

[[Concept - Cost Engineering for LLM Applications]] covers each of these mechanically. This note is about *why* the margin problem exists; that one is about *how* to fix it.

**The power-user problem.** Flat-rate or per-seat pricing on a token-metered backend breaks the assumption that made flat pricing work in SaaS. A small fraction of heavy users can consume far more compute than their subscription covers, making each of them gross-margin-negative while the blended average looks healthy. AI coding tools, Cursor and Anthropic's own Claude Code among them, repeatedly repriced or added usage caps and overage pricing through 2025 after their first flat-rate plans proved unsustainable against the heaviest cohorts (E2, contemporaneous reporting). Unlimited usage was safe under SaaS because marginal cost was ~0. Under token metering, marginal cost is real and unbounded per user.

**Deflation cuts both ways.** [[Concept - Token Price Deflation]] lowers the cost side of the margin equation over time, but two forces eat the gain before it reaches the bottom line. Competition passes savings through to customers, so in a competitive market a deflating cost structure becomes a deflating price instead of a wider margin. And reasoning and agentic workflows raise token volume per task faster than unit price falls: one agent task can issue dozens of tool calls and thinking passes where a simple query issued one. Net margin is a race between these effects, with no guaranteed improvement ([[Breakdown - Frontier Lab Economics]] shows the same race one layer up the stack). Zoom out and whether the [[Deep Dive - The AI Compute Buildout|physical compute buildout]] gets absorbed is this race at fleet scale. The buildout bets that served tokens keep 10x-ing faster than per-token margin erodes. That only holds if products like the ones this note describes clear a margin at volume.

**Measure per feature and per cohort, never blended.** A blended average cost per query hides the one runaway agent workflow, power-user segment or badly scoped RAG feature that may be erasing what the rest of the product earns. The right unit is outcome-denominated, something like *cost per resolved support ticket* or *cost per generated, merged pull request*, because request counts don't map cleanly to value delivered. [[Playbook - Measuring AI ROI]] covers the instrumentation.

## Failure modes

- **Finding out COGS when the monthly invoice arrives.** Teams that don't log token counts per request, feature and customer at the point of the call learn their real gross margin a month late, after pricing commitments (annual contracts, flat-rate plans) are locked in and can't be changed quickly.
- **Pricing off average cost while power users lose money.** A healthy blended margin can coexist with a subset of actively unprofitable customers. If that subset grows disproportionately, the blended average degrades faster than a naive extrapolation predicts, and usage-based products tend to select for exactly that, since your best, most engaged customers are the heaviest token consumers.
- **Leaving reasoning-model thinking tokens out of cost projections.** A team that budgets on visible output tokens and later adopts an extended-reasoning model for quality can see COGS jump 5-20x on the same feature with no visible change in behavior.

## The non-obvious

Gross margin on an LLM product isn't a fixed property of the business model. It moves, set jointly by your *worst* users (the heavy-usage tail flat pricing doesn't cover) and your *newest* model choice. Every model upgrade resets the cost baseline, often upward, because newer models tend to reason more or generate more tokens per answer even when they're cheaper per token. So unit economics has to be re-measured on a cadence tied to model releases and usage growth. Calculating it once at launch and assuming it holds is how teams get burned: they price a plan against one model's cost profile, upgrade the model for quality, and never re-price the plan.

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
