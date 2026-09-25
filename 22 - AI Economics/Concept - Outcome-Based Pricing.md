---
tags: [concept, domain/ai-economics, level/frontier]
aliases: [Outcome-Based Pricing, Outcome Pricing, Per-Resolution Pricing, Results-Based AI Pricing]
summary: "Charging per delivered result instead of per seat or token — why agents make it newly possible, and why attribution and gaming make it hard."
---

# Concept - Outcome-Based Pricing

> Outcome-based pricing charges for a *verified result* (a resolved support ticket, a booked meeting, a merged PR) instead of a seat or a token. Agents made it possible and deflation made it attractive. Once an agent can finish a whole task on its own, the thing you sell stops being a tool and becomes a labor substitute, so you can price against the human it replaces instead of the compute it burns. It also drags out the hardest commercial problem in AI: *what counts as success, and who caused it?* As soon as revenue depends on a metric, you and your customer both start optimizing that metric against each other.

## The mechanism

The vendor charges $X per verified outcome and **absorbs the token cost of getting there.** That inverts both SaaS seat pricing and usage/token pricing:

- **Seat pricing** (GitHub Copilot ~$19/user/mo) decouples price from cost but caps upside at headcount. Worse for agents, it *shrinks as the product works*. If the agent replaces human labor, the customer needs fewer seats, so a per-seat model shrinks its own market the more it succeeds.
- **Usage/token pricing** ties price to cost but exposes the customer to unpredictable bills and hands all the deflation upside to *them*.
- **Outcome pricing** decouples price from cost the *other* way. Price is pinned to the value of the result (what the human alternative costs), and cost is your falling token bill. The full comparison is in [[Decision - Pricing Models for AI Products]]; the COGS mechanics are in [[Concept - Unit Economics of LLM Products]].

The margin consequence is the point. Price tracks value and cost tracks tokens, so **[[Concept - Token Price Deflation]] lands in the vendor's margin instead of the customer's wallet.** When a fixed-quality token gets ~10x cheaper every year, any model whose price is bolted to today's token cost is a melting ice cube. Outcome pricing turns deflation into expanding gross margin instead of a competitive giveaway. That makes it the theoretically best model in a deflationary regime. It's also why the moat literature ([[Concept - Moats in the AI Application Layer]]) treats the outcome data you accumulate as a compounding asset and more than a billing line.

## In practice

The market is actively experimenting as of 2026. Customer support is the proving ground because its outcome ("did the customer's problem get solved without a human?") is unusually cheap to define and verify:

| Product | Model | Price point | Tier |
|---|---|---|---|
| Intercom **Fin** | Per resolution | **$0.99 / resolution**; no charge if it escalates to a human | E3 (published) |
| **Sierra** (Bret Taylor) | Pure outcome; paid only on successful autonomous resolution | Per-contract, undisclosed | E2 (company-stated) |
| Salesforce **Agentforce** | Launched per-conversation, then diversified | ~**$2 / conversation** at Oct 2024 launch → Flex Credits ($0.10/action = 20 credits; $500/100K credits, May 2025) → per-user (~$125/mo) | E2/E3 (published) |

Intercom reports growing Fin from ~$1M to $100M+ ARR on per-resolution pricing, backed by a performance guarantee (E2, company-stated, 2026). Sierra reports pure outcome pricing where "more resolutions = more revenue" (E2, company-stated). Agentforce is the cautionary counterpoint. It launched on a clean per-conversation unit in October 2024 and hit immediate backlash over *what counts as a conversation* when one enterprise query set off many backend actions. Within ~18 months it had layered on credit-based and per-user models, three pricing schemes running at once (E2, reporting, 2025-26). That's the attribution problem made visible.

**Why now.** This follows from agentic capability; it isn't a billing fad. When AI was a suggestion tool (autocomplete, draft assist), the only honest unit was a seat or a token, because the vendor delivered no end-to-end "outcome." Once agents complete whole tasks (mechanics in [[Deep Dive - Agentic Coding in Production]], deflection math in [[Concept - Support Deflection Economics]]), the vendor is **selling work**, and work has always been priced against the labor it replaces. Outcome pricing is the commercial form of "AI as labor."

## Failure modes

- **Attribution disputes, the central friction.** You have to *define* the outcome precisely and *prove the agent caused it*, not a human colleague, luck, or a customer who would have self-served anyway. When one query spawns many backend actions (the Agentforce problem), or a "resolution" gets reopened later, the definition itself becomes the contract negotiation. It's [[Concept - The Evaluation Gap]] in a commercial hat: if you can't measure the outcome reliably, you can't price on it.
- **Gaming and adverse selection from both sides.** On the *customer side*, route only the hard, low-success cases to the per-outcome agent and keep the easy wins on flat-rate channels. That adverse selection craters the vendor's realized success rate. On the *vendor side*, tune the agent to over-declare marginal "resolutions" to book more outcomes, which is Goodhart's law aimed at your own invoice. A per-outcome metric that isn't Goodhart-resistant gets optimized to death by whichever party it hurts.
- **Verification costs more than the margin.** Outcome pricing only pencils out where confirming the outcome is *cheap*. When verification needs expert human review (did the legal memo hold up? was the medical guidance safe?), review cost eats the deflation advantage. The [[Lore - AI Wrapper Graveyard]] lesson about thin value-add applies: you're paying humans to check the thing you sold as autonomous.
- **Contested-quality domains reject it outright.** Where the result carries liability and its quality is disputable (legal advice, medical guidance, anything in [[Lore - Hallucination Liability Incidents]]), no vendor wants revenue pinned to an outcome it can be sued over, and no buyer trusts the vendor's self-scored success. Seat and usage pricing persist there for good reason.

## The non-obvious

**Outcome pricing works only in the narrow band where the outcome is both cheap to verify *and* clearly cheaper than the human it replaces, and that band is smaller than the hype suggests.** After seeing Intercom Fin, the instinct is to price everything on outcomes. But Fin works because support resolution is close to ideal. It's roughly binary, high-volume (so noise averages out), self-evident to the end user (they stopped asking or didn't), and it replaces a well-understood human cost ($X per human-handled ticket). Change one axis and the model breaks: an ambiguous outcome (a "good" marketing draft), a rare one (a closed enterprise deal, where attribution is a quarter-long argument), an expensive-to-verify one (code that compiles but is subtly wrong; see [[Concept - Cost Engineering for LLM Applications]] on the true cost of a "completed" task), or a liability-laden one. The rule practitioners converge on is **price on value, meter on cost.** The winning structure separates what the customer pays for (the resolved ticket) from what you pay for (the tokens), so deflation flows to your margin. That separation is only *defensible* when the outcome is verifiable enough that neither side can profitably cheat.

## Connections
- [[Decision - Pricing Models for AI Products]] — the parent decision; outcome pricing is one of its four options, with the seat/usage/credit alternatives and when each wins.
- [[Concept - Unit Economics of LLM Products]] — the COGS the vendor absorbs under outcome pricing; why margin depends on getting the outcome in few tokens.
- [[Concept - Support Deflection Economics]] — the unit math (cost per resolved ticket vs human cost) that makes per-resolution pricing possible.
- [[Concept - Token Price Deflation]] — the deflation that outcome pricing routes into vendor margin instead of customer savings.
- [[Concept - Moats in the AI Application Layer]] — why the outcome/feedback data outcome pricing generates is a compounding moat.
- [[Lore - AI Wrapper Graveyard]] — the failure lesson: outcome pricing needs real owned value-add, not a thin wrapper the platform commoditizes.
- [[Deep Dive - Agentic Coding in Production]] — the agent capability (completing whole tasks) that makes an "outcome" a sellable unit at all.
- [[Concept - The Evaluation Gap]] — the measurement problem underneath outcome definition and attribution.
- [[Concept - Cost Engineering for LLM Applications]] — the tooling to keep per-outcome token cost below the price you charge.

## Sources
- Intercom — Fin AI Agent, $0.99/resolution pricing and outcome mechanics (published pricing + company blog, 2024-26). (E3 price / E2 ARR claims)
- Sierra — pure outcome-based pricing model (company statements/reporting, 2025-26). (E2)
- Salesforce — Agentforce pricing evolution: $2/conversation launch (Oct 2024) → Flex Credits (May 2025) → per-user; SaaStr/Concret.io reporting. (E2/E3)
- Bessemer / OpenView — AI pricing analyses on the seat-to-usage-to-outcome shift (2025-26). (E1)
- GitHub Copilot — ~$19/user/mo seat pricing, as the per-seat baseline. (E3, published)
