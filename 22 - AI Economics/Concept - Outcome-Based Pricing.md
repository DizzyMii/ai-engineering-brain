---
tags: [concept, domain/ai-economics, level/frontier]
aliases: [Outcome-Based Pricing, Outcome Pricing, Per-Resolution Pricing, Results-Based AI Pricing]
summary: "Charging per delivered result instead of per seat or token — why agents make it newly possible, and why attribution and gaming make it hard."
---

# Concept - Outcome-Based Pricing

> **One-paragraph hook:** Outcome-based pricing charges for a *verified result* — a resolved support ticket, a booked meeting, a merged PR — rather than for a seat or a token. It is the pricing model that agents made possible and deflation made attractive: when an agent can complete a whole task autonomously, the sellable unit stops being a tool and becomes a labor substitute, so you can price against the human it replaces instead of the compute it consumes. It is also the model that surfaces the hardest commercial problem in AI — *what counts as success, and who caused it* — because the moment your revenue depends on a metric, both you and your customer start optimizing that metric against each other.

## The mechanism

The vendor charges $X per verified outcome and **absorbs the token cost of getting there.** This is the structural inversion of both SaaS seat pricing and usage/token pricing:

- **Seat pricing** (GitHub Copilot ~$19/user/mo) decouples price from cost, but caps upside at headcount and — the fatal flaw for agents — *shrinks as the product works*. If the agent replaces human labor, the customer needs fewer seats, so a per-seat model is a machine that shrinks its own addressable market as it succeeds.
- **Usage/token pricing** aligns price to cost but exposes the customer to unpredictable bills and hands all the deflation upside to *them*, not you.
- **Outcome pricing** decouples price from cost in the *other* direction: price is pinned to the value of the result (what the human alternative costs), while cost is your falling token bill. See the full comparison in [[Decision - Pricing Models for AI Products]] and the COGS mechanics in [[Concept - Unit Economics of LLM Products]].

The margin consequence is the whole point. Because price tracks value and cost tracks tokens, **[[Concept - Token Price Deflation]] accrues to the vendor's margin rather than the customer's wallet.** In a world where a fixed-quality token falls ~10x/year, any model whose price is bolted to today's token cost is a melting ice cube; outcome pricing is the structure that turns deflation into expanding gross margin instead of a competitive giveaway. That is why it is the theoretically best model in a deflationary regime — and why the value/moat literature ([[Concept - Moats in the AI Application Layer]]) treats the outcome-data you accumulate as a compounding asset, not just a billing line.

## In practice

The market is actively experimenting as of 2026, and customer support is the proving ground because the outcome ("did the customer's problem get solved without a human?") is unusually cheap to define and verify:

| Product | Model | Price point | Tier |
|---|---|---|---|
| Intercom **Fin** | Per resolution | **$0.99 / resolution** — no charge if it escalates to a human | E3 (published) |
| **Sierra** (Bret Taylor) | Pure outcome — paid only on successful autonomous resolution | Per-contract, undisclosed | E2 (company-stated) |
| Salesforce **Agentforce** | Launched per-conversation, then diversified | ~**$2 / conversation** at Oct 2024 launch → Flex Credits ($0.10/action = 20 credits; $500/100K credits, May 2025) → per-user (~$125/mo) | E2/E3 (published) |

Intercom reports growing Fin from ~$1M to $100M+ ARR on the per-resolution model and backing it with a performance guarantee (E2, company-stated, 2026). Sierra reports pure outcome pricing where "more resolutions = more revenue" (E2, company-stated). The Agentforce trajectory is the cautionary counterpoint: it launched on a clean per-conversation outcome unit in October 2024, hit immediate backlash over *what counts as a conversation* when one enterprise query triggered many backend actions, and within ~18 months had layered on credit-based and per-user models — three pricing schemes running at once (E2, reporting, 2025-26). That reversal is the attribution problem made visible.

**Why now.** This is downstream of agentic capability, not a billing fad. When AI was a suggestion tool (autocomplete, draft assist), the only honest unit was a seat or a token — there was no "outcome" the vendor delivered end-to-end. Once agents complete whole tasks — the mechanics of which live in [[Deep Dive - Agentic Coding in Production]] and the deflection math in [[Concept - Support Deflection Economics]] — the vendor is effectively **selling work**, and work has always been priced against the labor it replaces. Outcome pricing is the commercial expression of "AI as labor."

## Failure modes

- **Attribution disputes (the central friction).** You must *define* the outcome precisely and *prove the agent caused it* — not a human colleague, not luck, not a customer who would have self-served anyway. When one query spawns many backend actions (the Agentforce problem) or when a "resolution" is later reopened, the definition itself becomes the contract negotiation. This is the [[Concept - The Evaluation Gap]] problem wearing a commercial hat: if you can't measure the outcome reliably, you can't price on it.
- **Gaming and adverse selection, from both sides.** *Customer side:* route only the hard, low-success cases to the per-outcome agent while keeping easy wins on flat-rate channels — adverse selection that craters the vendor's realized success rate. *Vendor side:* tune the agent to over-declare marginal "resolutions" to book more outcomes — Goodhart's law aimed at your own invoice. A per-outcome metric that isn't Goodhart-resistant gets optimized to death by whichever party it hurts.
- **Verification cost exceeds the margin.** Outcome pricing only pencils where confirming the outcome is *cheap*. When verification requires expert human review (did the legal memo actually hold up? was the medical guidance safe?), the review cost eats the deflation advantage, and the [[Lore - AI Wrapper Graveyard]]'s lesson about thin value-add applies — you're now paying humans to check the thing you sold as autonomous.
- **Contested-quality domains reject it outright.** Where the result carries liability and quality is disputable — legal advice, medical guidance, anything under [[Lore - Hallucination Liability Incidents]] — no vendor wants revenue pinned to an outcome they can be sued over, and no buyer trusts the vendor's self-scored success. Seat/usage pricing persists there for a reason.

## The non-obvious

**Outcome pricing works only in the narrow band where the outcome is both cheap to verify *and* clearly cheaper than the human it replaces — and that band is smaller than the hype implies.** The instinct after seeing Intercom Fin is "price everything on outcomes." But Fin works precisely because support resolution is a near-ideal case: binary-ish, high-volume (so noise averages out), self-evident to the end user (they either stopped asking or didn't), and replacing a well-understood human cost ($X per human-handled ticket). Move even one axis — make the outcome ambiguous (a "good" marketing draft), rare (a closed enterprise deal, where attribution is a quarter-long argument), expensive to verify (code that compiles but is subtly wrong — see [[Concept - Cost Engineering for LLM Applications]] on the true cost of a "completed" task), or liability-laden — and the model breaks. The durable rule practitioners converge on: **price on value, meter on cost.** The winning structure decouples what the customer pays for (the resolved ticket) from what you pay for (the tokens), so deflation flows to your margin — but that decoupling is only *defensible* when the outcome is verifiable enough that neither side can profitably cheat it.

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
