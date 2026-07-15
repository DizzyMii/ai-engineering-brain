---
tags: [moc, domain/trajectory, level/surface]
aliases: [Trajectory MOC, Navigation MOC, Where AI Is Headed]
summary: "Map of the domain that tracks where AI capability is going, what evidence supports each claim, and how to build for the uncertainty."
---

# MOC - Trajectory & Navigation

This domain records what the field actually knows about where AI capability, cost, and deployment are headed — as opposed to what any single forecaster, lab, or vendor claims. It exists because the honest answer to "when AGI" or "is this a bubble" is a contested spread with named camps and named incentives, not a date, and because the practitioner question underneath all of it — what do I build *now*, given that I can't wait for the debate to resolve — has a real, evidence-backed answer. The notes here separate measured capability signals (METR horizons, RCTs) from model-based projections (bio-anchors, TAM estimates) from pure incentive-laden pronouncement, and apply the Evidence Law tiering (§8) throughout so a number's confidence travels with it. The question this domain answers: given genuine, well-documented disagreement about the trajectory, what is worth doing today regardless of which branch turns out true?

**Start here:**
- **Surface:** [[Concept - Benchmark Saturation]] — the epistemic problem underneath everything else in this domain: the field's oldest capability signal (leaderboard scores) stopped discriminating, which is why every other note here reaches for a different kind of evidence.
- **Core:** [[Reference - The 2026 Navigation Cheatsheet]] — the compressed, date-stamped index of every number a practitioner actually needs, with tiers attached; read this before any of the longer core notes.
- **Advanced:** [[Deep Dive - Bubble or Boom]] — the widest-lens advanced note; its three-question framework (equities / capex / technology) organizes how to read the compute-buildout and labor-market notes that sit beside it.
- **Frontier:** [[Concept - Automated AI Research and Takeoff]] — the mechanism the short-timeline camp actually rests on, made concrete enough to interrogate rather than just believe or dismiss.
- **Unicorn:** [[Lore - Failed AI Predictions]] — the graveyard that calibrates everything above it; read it after, not instead of, the calibration notes.

## Measuring the trajectory
How the field knows anything at all about where capability is headed, once static scores stop working.

- [[Concept - Benchmark Saturation]] — MMLU's frontier cluster (89-92% by Q1 2026) sits inside its own label-error rate, and OpenAI's own Feb 2026 audit found 59.4% of the SWE-bench Verified tasks its o3 failed had flawed tests, not model failures.
- [[Concept - METR Time Horizons]] — the 50%-success time horizon doubled roughly every 7 months from 2019-2025, accelerated to a ~3-month doubling time since 2024, and reached 16-20 hours in METR's May 2026 joint-lab pilot — but the 80%-reliability horizon on that same pilot was only 3-4 hours.
- [[Reference - The AI Forecasting Track Record]] — the scorecard's two-word summary: capability/scaling has been systematically *under*-forecast while reliable open-ended autonomy has been systematically *over*-forecast, opposite errors that averaging pundits blends into noise.

## The AGI timeline and takeoff debate
Whether and when AI automates its own research, and the honest spread of dates that follow from that question.

- [[Concept - The AGI Timeline Debate]] — expert-survey medians jumped 13 years in a single year (2060→2047, Grace et al. 2022 vs. 2023) while Metaculus's strict full-AGI question sits at a ~2033 community median — four methods, four different numbers, decades apart, not a range to average.
- [[Concept - Automated AI Research and Takeoff]] — the AI-2027 authors' own December 2025 revision pushed their headline "superhuman coder" milestone from early-2027 to a model median of December 2031, a 3-5 year retreat inside eight months of publishing the original scenario.
- [[Reference - The Open Questions Ledger]] — six coupled, genuinely unresolved questions (data wall, reliability wall, bubble-or-boom, takeoff, labor net effect, AGI timing), each stated with the specific observable that would resolve it rather than left as a debate to be won by rhetoric.

## Structural constraints on the curve
The physical and data-supply limits that could bend every extrapolation above.

- [[Concept - The Data Wall]] — Epoch AI's usable-text stock (~300 trillion tokens) is projected to run dry around 2028, a date that already moved once, from an original ~2024 estimate, after better filtering revised the usable pool 5x upward.
- [[Deep Dive - The AI Compute Buildout]] — Stargate targets $500B and 10GW by end of 2025; the top-4 US hyperscalers are on track for ~$650-700B combined 2026 capex, and the binding constraint turns out to be grid power and HBM/CoWoS packaging, not chip logic or money.

## Is the spend justified?
The market-scale question of whether the capital committed to the buildout can be absorbed.

- [[Deep Dive - Bubble or Boom]] — Sequoia's Cahn calculated the annual AI revenue needed to justify 2024-era infrastructure spend at ~$600B, an order of magnitude above the actual run-rate at the time, while Nvidia-OpenAI-Oracle circular-financing arrangements totaled $800B+ by 2026.

## Who it actually displaces
The measured, not projected, labor evidence.

- [[Deep Dive - AI and the Labor Market]] — a 5,179-agent RCT found AI raised novice-agent output +34% and expert-agent output ~0%, and that same skill-compression pattern shows up at population scale as a ~13% relative employment decline for 22-25-year-olds in the most AI-exposed occupations.

## Navigating the uncertainty
What to actually do, given that none of the above resolves cleanly.

- [[Playbook - Picking Profitable AI Use Cases]] — the six-step filter whose hardest step is pricing verification honestly, because MIT NANDA found ~95% of pilots (after an estimated $30-40B in enterprise spend) showed no measured P&L impact, traced to workflow integration, not model capability.
- [[Reference - The 2026 Navigation Cheatsheet]] — puts +26% PRs/week across three coding-assistant RCTs (~4,900 devs) next to METR's own RCT finding experienced open-source developers 19% *slower* with AI — profitable plays and overhyped claims in the same table, tier by tier.
- [[Concept - What Stays Valuable Through Any Scenario]] — token prices for a fixed quality bar fell ~10x/year since 2022 (GPT-3-equivalent quality: $60/M tokens to $0.06/M), which is the dominance argument for why the model layer itself is named the least defensible position in AI right now.

## History and folklore
The graveyard that calibrates confidence in every forecast above.

- [[Lore - Failed AI Predictions]] — Hinton told a 2016 conference to stop training radiologists; a decade later Mayo Clinic employs ~55% more of them than it did then, and Hinton said so himself in a May 2026 New York Times mea culpa.

## Adjacent domains
- [[MOC - AI Economics]] — the unit-economics and pricing detail (token deflation, build-vs-buy, moats) that this domain's trajectory forecasts and buildout numbers are ultimately bets on.
- [[MOC - Adoption & Blockers]] — the enterprise-side failure modes (pilot-to-production gap, evaluation gap) that this domain's navigation notes are built to route around before funding a pilot.
- [[MOC - AI Across Business Functions]] — the per-function deployment detail (support, legal, medical, HR) that the labor-market and use-case-picking notes here abstract into general patterns.
- [[MOC - AI in Software Engineering]] — the developer-productivity RCTs and agentic-coding evidence this domain's coding-assistant rows and METR horizon numbers are drawn from.
- [[Ladder - Navigating the AI Economy]] — a guided walk through this domain's notes in order, surface to unicorn, for someone building a full mental model rather than looking up one number.
