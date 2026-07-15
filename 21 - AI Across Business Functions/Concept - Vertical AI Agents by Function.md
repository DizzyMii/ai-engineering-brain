---
tags: [concept, domain/applied-business, level/frontier]
aliases: [vertical AI agents, vertical agents, outcome-priced agents, AI concierge, Sierra Decagon Harvey Abridge]
summary: "The shift from horizontal copilots to outcome-priced vertical agents owning a whole function — and the review gate still underneath."
---

# Concept - Vertical AI Agents by Function

> The dominant 2025–2026 app-layer thesis: stop selling a copilot that lives *inside* someone's existing software and instead build an agent that owns the *whole* workflow for one function — support, legal, health documentation, sales — and charge per *outcome* rather than per seat. Investors priced this hard (Harvey $11B, Abridge $5.3B, Decagon $4.5B). The catch the marketing hides: every vertical agent that actually works still runs with a human-review or human-escalation gate underneath, and the outcome-pricing model quietly transfers reliability risk onto the vendor — which is exactly why the measurement games start.

## The mechanism

Three things distinguish a vertical agent from the horizontal copilots (ChatGPT-in-a-sidebar) that preceded it:

1. **Workflow ownership, not suggestion.** The agent doesn't draft a message for a human to paste — it *is* the front door for that function. Decagon and Sierra sit as the support agent; [[Breakdown - Harvey and AI in Legal Work]] owns the research/drafting workflow; Abridge owns the encounter-to-note pipeline. The product surface is the whole task, not an assist inside someone else's task.
2. **Outcome pricing.** Charging per resolved ticket / per task / per note instead of per seat. Intercom Fin bills **$0.99 per resolution** (E2, Intercom 2025–2026); Sierra prices at roughly **$1.50 per resolution** (E1, third-party estimate 2026); Decagon offers per-conversation and per-resolution options, with full enterprise contracts estimated at **~$95k–$590k/yr, median ~$400k** depending on volume and scope (E1, third-party estimates 2026, sales-gated). The pricing model *is* the business model.
3. **Domain depth as the claimed moat.** The defensibility argument is that the moat is proprietary domain data, workflow integration, and the accountable-reviewer relationship — Abridge's Epic-EHR integration and 1.5M+ encounter dataset, Harvey's Am Law anchor firms — *not* the base model. This is the direct response to the wrapper-commoditization lesson (see [[Concept - AI in Marketing and Content]] and [[Concept - Moats in the AI Application Layer]]): when the model is the product and the model is available directly, a thin wrapper dies, so vertical agents claim the value lives in the domain-specific layer the model can't supply.

## In practice

**The valuation signal (all E2, announced rounds).** Investors are pricing vertical agents as the app-layer winners:

| Agent | Function | Valuation | Marker |
|---|---|---|---|
| Harvey | Legal | ~$3B (Feb 2025) → $8B (Dec 2025) → **$11B (Mar 2026)** | ~$100M ARR (Aug 2025) → ~$190M ARR (Jan 2026); 142,000+ lawyers, 1,500+ customers, majority of Am Law 100 |
| Abridge | Health documentation | **$5.3B (Jun 2025)**, doubled from $2.75B (Feb 2025) | $300M Series E (a16z/Khosla); Epic-integrated |
| Decagon | Support | **$4.5B (Jan 2026)**, tripled in ~6 months | $250M Series D (Coatue/Index); 100+ enterprise customers |

Read these as markers of investor conviction, **not realized value** — the funding narrative runs well ahead of demonstrated retention (contrast the [[Concept - AI SDRs and Sales Automation]] churn story, where the same category of hype met an audit).

**Outcome pricing as actually deployed** reveals the seams. Intercom counts a "resolution" when the customer confirms the answer helped (*confirmed*) **or** exits without asking for more help (*assumed resolution*). Sierra's "outcome" is negotiated per contract and can trigger billing even when the agent transfers to a human. Both are legitimate businesses; both also show how much of the "outcome" is a definitional choice rather than a verified problem-solved.

## Failure modes

- **The reliability gate is still there — the autonomy is partial.** Every currently-successful vertical agent runs with a human somewhere: scribe sign-off (Abridge), lawyer review (Harvey), support escalation-to-human (Sierra/Decagon/Fin). "Full autonomy" remains marketing, gated by the [[Concept - The Capability-Reliability Gap]]. Buyers who provision for zero human oversight discover the escalation path was load-bearing.
- **Outcome definitions inflate under pricing pressure.** Because revenue is tied to the outcome count, the definition of "outcome" drifts toward whatever is easy to count — "assumed resolution," "billable transfer" — inflating the headline resolution rate versus verified problem-solving. Production-observed Fin resolution rates have been reported as low as **45–53%** against a 67% marketed average (E2, practitioner critiques 2026), the gap living almost entirely in the "assumed" bucket. See [[Concept - Support Deflection Economics]] and [[Lore - What Vendors Don't Say About Deflection Rates]].
- **Cost scales with success, unpredictably.** Per-resolution billing means the bill rises as adoption rises — "expensive fast" at high volume — inverting the intuitive "AI makes support cheaper" story and complicating budget forecasting.
- **Over-scoping autonomy.** Betting the whole function on the agent instead of the top slice of repetitive queries is how [[Breakdown - Klarna's AI Customer Service Bet]] over-rotated and walked back (see [[Lore - The Klarna Reversal and Support Bot Walk-Backs]]).

## The non-obvious

**Outcome pricing quietly transfers reliability risk from buyer to vendor — and that transfer is what breeds the measurement games.** Under per-seat pricing, the buyer eats a bad model (they paid for the seat regardless). Under per-outcome pricing, if the agent under-resolves, the *vendor* eats the miss. That's genuinely better for the buyer's incentives — until you notice the vendor now has a direct financial motive to define "outcome" generously. "Assumed resolution," billable human-transfers, and elastic success criteria are not accidents; they are the predictable response to a pricing model that pays the vendor per counted outcome. **The pricing model and the measurement games are two sides of the same coin** — you cannot adopt outcome pricing and then be surprised the outcome definition is contested. The buyer's only defense is to redefine the outcome in the contract (CSAT-confirmed or no-re-contact within N days) and audit a transcript sample by hand, pricing against the audited number rather than the vendor's headline. The vertical-agent thesis is real; the autonomy and the outcome counts are both softer than the pitch deck.

## Connections

- [[Concept - Copilot vs Autopilot Deployment Modes]] — vertical agents are marketed as autopilot but ship as instrumented copilots with an escalation gate; the mode split is the honest description.
- [[Concept - Support Deflection Economics]] — support vertical agents are priced and measured on deflection/resolution; the outcome-definition problem is that note's core.
- [[Concept - AI SDRs and Sales Automation]] — the sales vertical agent and its cautionary churn/ARR story; the most exposed instance of the thesis.
- [[Breakdown - Klarna's AI Customer Service Bet]] — the scaled support-agent bet and its over-scoping lesson.
- [[Breakdown - Harvey and AI in Legal Work]] — the legal vertical agent whose moat is anchor-firm data and mandatory review, not the base model.
- [[Breakdown - AI Medical Scribes]] — Abridge as the health-documentation vertical agent; Epic integration as the concrete moat.
- [[Lore - What Vendors Don't Say About Deflection Rates]] — the measurement games that outcome pricing structurally incentivizes.
- [[Concept - The Capability-Reliability Gap]] — the gate that still bounds every "autonomous" vertical agent.
- [[Concept - Moats in the AI Application Layer]] — the defensibility claim (domain data, integration, reviewer relationship) that justifies the whole thesis.
- [[Decision - Build vs Buy vs Wrap]] — vertical agents are the "buy a full-stack function" end of that decision; the wrapper end is what they claim to have escaped.
- [[Concept - Token Price Deflation]] — falling token costs erode the base-model cost advantage, pushing value toward the domain layer vertical agents claim.

## Sources

- CNBC / Bloomberg / Harvey.ai (Mar 2026) — Harvey $200M round at $11B, up from $8B (Dec 2025); ARR figures via Sacra. Legal vertical-agent scale (E2 rounds; E1 ARR estimate).
- TechCrunch (Jun 24 2025) — "In just 4 months, AI medical scribe Abridge doubles valuation to $5.3B." $300M Series E, a16z/Khosla (E2).
- Bloomberg / Forbes / Decagon (Jan 2026) — Decagon $250M Series D, $4.5B valuation, Coatue/Index (E2).
- Intercom / fin.ai help docs (2025–2026) — $0.99/resolution and the confirmed-vs-assumed resolution definition (E2, company primary source).
- Third-party pricing analyses (Retell AI, Sacra, eesel, 2026) — Sierra ~$1.50/resolution, Decagon contract ranges ~$95k–$590k/yr (E1, estimates; neither vendor publishes full pricing).
