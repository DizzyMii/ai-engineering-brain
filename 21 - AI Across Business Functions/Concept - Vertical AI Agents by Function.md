---
tags: [concept, domain/applied-business, level/frontier]
aliases: [vertical AI agents, vertical agents, outcome-priced agents, AI concierge, Sierra Decagon Harvey Abridge]
summary: "The shift from horizontal copilots to outcome-priced vertical agents owning a whole function — and the review gate still underneath."
---

# Concept - Vertical AI Agents by Function

> The dominant 2025–2026 app-layer thesis: stop selling a copilot that lives *inside* someone's existing software. Build an agent that owns the *whole* workflow for one function (support, legal, health documentation, sales) and charge per *outcome* instead of per seat. Investors priced this hard: Harvey $11B, Abridge $5.3B, Decagon $4.5B. The marketing hides two things. Every vertical agent that works still has a human-review or human-escalation gate underneath. And outcome pricing quietly shifts reliability risk onto the vendor, which is how the measurement games start.

## The mechanism

Three things separate a vertical agent from the horizontal copilots (ChatGPT-in-a-sidebar) that came before:

1. **It owns the workflow.** The agent doesn't draft a message for a human to paste. It *is* the front door for that function. Decagon and Sierra sit as the support agent; [[Breakdown - Harvey and AI in Legal Work]] owns the research and drafting workflow; Abridge owns the encounter-to-note pipeline. The product surface is the whole task, not an assist inside someone else's.
2. **Outcome pricing.** Charging per resolved ticket, task or note instead of per seat. Intercom Fin bills **$0.99 per resolution** (E2, Intercom 2025–2026). Sierra prices at roughly **$1.50 per resolution** (E1, third-party estimate 2026). Decagon offers per-conversation and per-resolution options, with full enterprise contracts estimated at **~$95k–$590k/yr, median ~$400k** depending on volume and scope (E1, third-party estimates 2026, sales-gated). The pricing model *is* the business model.
3. **Domain depth as the claimed moat.** The claimed moat is proprietary domain data, workflow integration and the accountable-reviewer relationship (Abridge's Epic-EHR integration and 1.5M+ encounter dataset, Harvey's Am Law anchor firms), not the base model. This answers the wrapper-commoditization lesson (see [[Concept - AI in Marketing and Content]] and [[Concept - Moats in the AI Application Layer]]). When the model is the product and is available directly, a thin wrapper dies, so vertical agents claim the value sits in a domain layer the model can't supply.

## In practice

**The valuation signal (all E2, announced rounds).** Investors are pricing vertical agents as the app-layer winners:

| Agent | Function | Valuation | Marker |
|---|---|---|---|
| Harvey | Legal | ~$3B (Feb 2025) → $8B (Dec 2025) → **$11B (Mar 2026)** | ~$100M ARR (Aug 2025) → ~$190M ARR (Jan 2026); 142,000+ lawyers, 1,500+ customers, majority of Am Law 100 |
| Abridge | Health documentation | **$5.3B (Jun 2025)**, doubled from $2.75B (Feb 2025) | $300M Series E (a16z/Khosla); Epic-integrated |
| Decagon | Support | **$4.5B (Jan 2026)**, tripled in ~6 months | $250M Series D (Coatue/Index); 100+ enterprise customers |

Read these as markers of investor conviction, **not realized value**. The funding story runs well ahead of demonstrated retention. Compare the [[Concept - AI SDRs and Sales Automation]] churn story, where the same kind of hype met an audit.

**Outcome pricing as deployed** shows the seams. Intercom counts a "resolution" when the customer confirms the answer helped (*confirmed*) **or** leaves without asking for more help (*assumed resolution*). Sierra's "outcome" is negotiated per contract and can trigger billing even when the agent hands off to a human. Both are legitimate businesses, and both show how much of an "outcome" is a definitional choice.

## Failure modes

- **The reliability gate is still there; autonomy is partial.** Every vertical agent succeeding today has a human somewhere: scribe sign-off (Abridge), lawyer review (Harvey), escalation to a human in support (Sierra/Decagon/Fin). "Full autonomy" remains marketing, held back by [[Concept - The Capability-Reliability Gap]]. Buyers who provision for zero human oversight find out the escalation path was doing real work.
- **Outcome definitions inflate under pricing pressure.** Revenue is tied to the outcome count, so the definition drifts toward whatever is easy to count ("assumed resolution," "billable transfer") and the headline resolution rate rises above verified problem-solving. Fin resolution rates observed in production have been reported as low as **45–53%** against a 67% marketed average (E2, practitioner critiques 2026), with nearly all of the gap in the "assumed" bucket. See [[Concept - Support Deflection Economics]] and [[Lore - What Vendors Don't Say About Deflection Rates]].
- **Cost scales with success, unpredictably.** Per-resolution billing rises with adoption and gets "expensive fast" at high volume, inverting the intuitive "AI makes support cheaper" story and making budgets hard to forecast.
- **Over-scoping autonomy.** Betting the whole function on the agent, instead of the top slice of repetitive queries, is how [[Breakdown - Klarna's AI Customer Service Bet]] over-rotated and walked back (see [[Lore - The Klarna Reversal and Support Bot Walk-Backs]]).

## The non-obvious

**Outcome pricing moves reliability risk from buyer to vendor, and that move is what breeds the measurement games.** Under per-seat pricing the buyer eats a bad model, since they paid for the seat regardless. Under per-outcome pricing, if the agent under-resolves, the *vendor* eats the miss. That's better for the buyer, until you notice the vendor now has a direct financial reason to define "outcome" generously. "Assumed resolution," billable human transfers and elastic success criteria aren't accidents. They're the predictable response to a pricing model that pays per counted outcome. **The pricing model and the measurement games come as a pair.** You can't adopt outcome pricing and then be surprised the outcome definition is contested. The buyer's only defense is to define the outcome in the contract (CSAT-confirmed, or no re-contact within N days), audit a transcript sample by hand, and price against the audited number instead of the vendor's headline. The vertical-agent thesis is real. The autonomy and the outcome counts are both softer than the pitch deck.

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
