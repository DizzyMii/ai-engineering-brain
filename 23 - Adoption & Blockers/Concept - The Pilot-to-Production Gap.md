---
tags: [concept, domain/adoption-blockers, level/surface]
aliases: [GenAI Divide, pilot purgatory, POC-to-production gap, the 95% problem]
summary: "Most enterprise GenAI pilots never reach production — not weak models, but production being a reliability cliff, not a slope."
---
# Concept - The Pilot-to-Production Gap

> **One-paragraph hook:** Enterprises run GenAI pilots constantly and ship almost none into systems that move revenue or cost. The distance between "the demo worked" and "the system is in production, trusted and measured" is the headline fact of enterprise AI adoption in 2026. It comes from how these systems fail, and better models won't make it go away.

## The mechanism

A demo is a curated slice of input space: inputs the system handles well, run a few times, stopped at the first success. Production is the full, adversarial, long-tail input distribution, running continuously, forever. A system that looks 90% right in a demo isn't 90% done. It fails on roughly 1 in 10 real invocations, and those failures cluster in the messy, ambiguous, edge-case inputs that make up a disproportionate share of real work.

That last 10% costs far more than its size suggests. It needs eval infrastructure to *find* the failures ([[Concept - The Evaluation Gap]]), data plumbing to *feed* the system correctly ([[Concept - Data and Integration Readiness]]), and human review to *catch* what still slips through ([[Concept - The Verification Tax]]). None of it shows in a demo, so budgets and timelines get set as if it doesn't exist. It's the same curve as [[Concept - The Capability-Reliability Gap]]: capability is roughly continuous, but usability is a step function that only trips once reliability clears the bar the task needs.

The path from pilot to abandonment typically runs: (1) a team stands up a proof of concept against a small, friendly test set; (2) it clears that bar and gets budget and executive attention; (3) it meets real users or real data volume; (4) failure modes the small test set hid show up: stale data, edge-case inputs, permission leaks, silent model drift; (5) with no pre-built eval set or rollback plan, the team can't say whether the system is "close" or "broken," and trust collapses; (6) the project gets shelved without announcement instead of fixed, because fixing it means the unglamorous plumbing nobody budgeted for.

## In practice

The most-cited data point is MIT NANDA's *"The GenAI Divide: State of AI in Business 2025"* (published Aug 2025). Despite an estimated $30–40B in enterprise GenAI spend, roughly 95% of organizations report no measurable P&L impact from their initiatives, while about 5%, mostly narrow and well-scoped deployments, extract concentrated value (E2, single report).

The methodology, since it's widely misquoted: a systematic review of 300+ publicly disclosed AI initiatives, 52 structured interviews, and 153 survey responses from senior leaders, fielded January–June 2025 (E2; not an RCT, not peer-reviewed, and the sample skews toward AI-engaged firms). The report's framing matters as much as the headline: "no measurable P&L impact" doesn't mean "failed". Many of these are pilots that never got attribution instrumentation, not systems that broke. Treat 95% as directionally real and badly overloaded by press coverage that flattens it into "95% of AI fails," a claim the report doesn't make.

Independent data points the same way. S&P Global Market Intelligence's *Voice of the Enterprise: AI & Machine Learning* survey (n=1,006 IT and line-of-business professionals, North America and Europe, fielded 2025) found the share of firms abandoning *most* of their AI initiatives before production rose from 17% to 42% year over year, with an average of 46% of proofs of concept scrapped before production (E2, single survey). Gartner's July 2024 forecast said at least 30% of GenAI projects would be abandoned after proof of concept by end-2025, citing poor data quality, unclear ROI and escalating cost (E1 forecast; attribute to Gartner, don't launder into fact). By early 2026 Gartner's follow-on reporting put the *realized* abandonment rate closer to 50% for projects completed through end-2025 (E1, Gartner, 2026; a forecast revision, not independent verification, but directionally corroborating).

The clearest asymmetry in the NANDA data is buy vs. build. Tools bought from specialized vendors or built via partnership reached production about 67% of the time, versus roughly a third of that rate for internal builds (E2). That feeds directly into [[Decision - Build vs Buy vs Wrap]], and fits vendor market-sizing narratives that deserve their own skepticism (see [[Reference - AI Market Sizing Claims]]).

## Failure modes

- **Reading "no P&L impact" as "broken."** In survey data, a pilot with no attribution model looks identical to a failed one. The fix is instrumenting ROI from day one, not dropping the use case.
- **Confusing capability with reliability.** Teams approve scope on demo capability, then find the task needed near-100% reliability with no human check. That's a use-case selection failure (see [[Playbook - Picking Profitable AI Use Cases]]).
- **No visible mechanism, so no fix.** Without an eval set ([[Concept - The Evaluation Gap]]) or clean data access ([[Concept - Data and Integration Readiness]]), teams can't tell whether the gap is closing, so they shelve instead of iterating.
- **Survivorship bias in public narratives.** Vendor case studies and conference talks oversample the 5% that worked, which makes the base rate look better than it is (see [[Deep Dive - Bubble or Boom]]).

## The non-obvious

The gap is a cliff, not a slope, because most enterprise workflows have a hard pass/fail threshold (correct enough to trust unsupervised, or not) instead of a graceful-degradation curve. A model 20% more capable doesn't close 20% of the gap. It closes whatever share of the remaining failure modes happens to fall under the new capability line, which is often small. So NANDA puts the root cause in a "learning gap" (systems that don't retain feedback or adapt to a specific workflow), not in raw model quality, infrastructure or regulation. The blocker is organizational and integration work, and frontier-model progress doesn't substitute for building the eval set and the data pipeline. [[Playbook - Crossing the Pilot-to-Production Gap]] has the procedure this implies, and [[Gotchas - Enterprise AI Adoption]] the specific ways teams get it wrong.

## Connections
- [[Concept - The Evaluation Gap]] — the specific missing infrastructure (no eval set) that makes the gap invisible until production.
- [[Concept - Data and Integration Readiness]] — the plumbing work that consumes most of the effort NANDA attributes to the "learning gap."
- [[Concept - Organizational Resistance and Change Management]] — the human side of why systems that clear the reliability bar still fail to spread.
- [[Playbook - Crossing the Pilot-to-Production Gap]] — the operational procedure that addresses this gap step by step.
- [[Gotchas - Enterprise AI Adoption]] — the symptom-level pitfalls (demo-vs-prod, shelfware) this concept explains structurally.
- [[Concept - The Capability-Reliability Gap]] — the underlying mechanism: usability is a step function of reliability, not capability.
- [[Decision - Build vs Buy vs Wrap]] — the buy-vs-build asymmetry NANDA measured is a direct input to this decision.
- [[Reference - AI Market Sizing Claims]] — where to check enterprise AI spend and ROI figures against their evidence tier.
- [[Playbook - Picking Profitable AI Use Cases]] — choosing use cases that don't require clearing an unrealistic reliability bar in the first place.
- [[Deep Dive - Bubble or Boom]] — how survivorship bias in public AI success stories distorts the perceived base rate.

## Sources
- MIT NANDA — *The GenAI Divide: State of AI in Business 2025* (Aug 2025). Headline 95%/5% finding and the "learning gap" causal framing; methodology as stated in the report (300+ initiatives reviewed, 52 interviews, 153 survey responses, Jan–Jun 2025).
- S&P Global Market Intelligence — *Voice of the Enterprise: AI & Machine Learning, Use Cases 2025* (2025, n=1,006). Independent corroboration: 17%→42% YoY rise in firms abandoning most AI initiatives; 46% average POC scrap rate.
- Gartner — press release, 29 Jul 2024, "Gartner Predicts 30% of Generative AI Projects Will Be Abandoned After Proof of Concept By End of 2025"; follow-on 2026 reporting revising the realized rate upward (~50%).
- Fortune, Aug 2025 — reporting on the MIT NANDA report's release and reception, including the widely-repeated (and partially inaccurate) "95% of AI fails" framing.
