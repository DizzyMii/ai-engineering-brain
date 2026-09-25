---
tags: [moc, domain/trajectory, level/surface]
aliases: [Trajectory MOC, Navigation MOC, Where AI Is Headed]
summary: "Map of the domain that tracks where AI capability is going, what evidence supports each claim, and how to build for the uncertainty."
---

# MOC - Trajectory & Navigation

What the field actually knows about where AI capability, cost and deployment are headed, as opposed to what any single forecaster, lab or vendor claims. The honest answer to "when AGI?" or "is this a bubble?" is a contested spread with named camps and named incentives, not a date. The practitioner question underneath (what do I build *now*, when I can't wait for the debate to resolve?) has a real, evidence-backed answer. These notes separate measured capability signals (METR horizons, RCTs) from model-based projections (bio-anchors, TAM estimates) and from incentive-laden pronouncements, and apply the Evidence Law tiering (§8) throughout so a number's confidence travels with it. The question this domain answers: given real, well-documented disagreement about the trajectory, what's worth doing today whichever branch turns out true?

**Start here:**
- **Surface:** [[Concept - Benchmark Saturation]]: the evidence problem under everything else here. The field's oldest capability signal, leaderboard scores, stopped discriminating, so every other note reaches for a different kind of evidence.
- **Core:** [[Reference - The 2026 Navigation Cheatsheet]]: the compressed, date-stamped index of every number a practitioner needs, with tiers attached. Read it before the longer core notes.
- **Advanced:** [[Deep Dive - Bubble or Boom]]: the widest-lens advanced note. Its three-question framework (equities / capex / technology) organizes how to read the compute-buildout and labor-market notes beside it.
- **Frontier:** [[Concept - Automated AI Research and Takeoff]]: the mechanism the short-timeline camp rests on, made concrete enough to interrogate instead of just believing or dismissing.
- **Unicorn:** [[Lore - Failed AI Predictions]]: the graveyard that calibrates everything above. Read it after the calibration notes, not instead of them.

## Measuring the trajectory
How the field knows anything about where capability is headed once static scores stop working.

- [[Concept - Benchmark Saturation]]: MMLU's frontier cluster (89-92% by Q1 2026) sits inside its own label-error rate. OpenAI's own Feb 2026 audit found 59.4% of the SWE-bench Verified tasks its o3 failed had flawed tests, not model failures.
- [[Concept - METR Time Horizons]]: the 50%-success time horizon doubled roughly every 7 months from 2019-2025, sped up to a ~3-month doubling time since 2024, and reached 16-20 hours in METR's May 2026 joint-lab pilot. The 80%-reliability horizon in that same pilot was only 3-4 hours.
- [[Reference - The AI Forecasting Track Record]]: the scorecard in short. Capability/scaling has been systematically *under*-forecast and reliable open-ended autonomy systematically *over*-forecast. Averaging pundits blends those opposite errors into noise.

## The AGI timeline and takeoff debate
Whether and when AI automates its own research, and the honest spread of dates that follows.

- [[Concept - The AGI Timeline Debate]]: expert-survey medians jumped 13 years in one year (2060→2047, Grace et al. 2022 vs. 2023), while Metaculus's strict full-AGI question sits at a ~2033 community median. Four methods, four numbers decades apart, and not a range to average.
- [[Concept - Automated AI Research and Takeoff]]: the AI-2027 authors' own December 2025 revision pushed their headline "superhuman coder" milestone from early-2027 to a model median of December 2031, a 3-5 year retreat within eight months of publishing.
- [[Reference - The Open Questions Ledger]]: six coupled, unresolved questions (data wall, reliability wall, bubble-or-boom, takeoff, labor net effect, AGI timing), each stated with the specific observable that would resolve it instead of a debate to be won by rhetoric.

## Structural constraints on the curve
The physical and data-supply limits that could bend every extrapolation above.

- [[Concept - The Data Wall]]: Epoch AI's usable-text stock (~300 trillion tokens) is projected to run dry around 2028. The date has already moved once, from an original ~2024 estimate, after better filtering revised the usable pool 5x upward.
- [[Deep Dive - The AI Compute Buildout]]: Stargate targets $500B and 10GW by end of 2025, and the top-4 US hyperscalers are on track for ~$650-700B combined 2026 capex. The limit turns out to be grid power and HBM/CoWoS packaging, not chip logic or money.

## Is the spend justified?
Whether the capital committed to the buildout can be absorbed.

- [[Deep Dive - Bubble or Boom]]: Sequoia's Cahn put the annual AI revenue needed to justify 2024-era infrastructure spend at ~$600B, an order of magnitude above the actual run-rate then. Nvidia-OpenAI-Oracle circular-financing arrangements totaled $800B+ by 2026.

## Who it actually displaces
The measured, not projected, labor evidence.

- [[Deep Dive - AI and the Labor Market]]: a 5,179-agent RCT found AI raised novice-agent output +34% and expert-agent output ~0%. The same skill compression shows up at population scale as a ~13% relative employment decline for 22-25-year-olds in the most AI-exposed occupations.

## Navigating the uncertainty
What to do, given that none of the above resolves cleanly.

- [[Playbook - Picking Profitable AI Use Cases]]: a six-step filter whose hardest step is pricing verification honestly. MIT NANDA found ~95% of pilots (after an estimated $30-40B in enterprise spend) showed no measured P&L impact, traced to workflow integration, not model capability.
- [[Reference - The 2026 Navigation Cheatsheet]]: puts +26% PRs/week across three coding-assistant RCTs (~4,900 devs) next to METR's RCT finding experienced open-source developers 19% *slower* with AI. Profitable plays and overhyped claims in one table, tier by tier.
- [[Concept - What Stays Valuable Through Any Scenario]]: token prices for a fixed quality bar fell ~10x/year since 2022 (GPT-3-equivalent quality: $60/M tokens to $0.06/M). That's the dominance argument for calling the model layer itself the least defensible position in AI right now.

## History and folklore
The graveyard that calibrates confidence in every forecast above.

- [[Lore - Failed AI Predictions]]: Hinton told a 2016 conference to stop training radiologists. A decade later Mayo Clinic employs ~55% more of them than it did then, and Hinton admitted the miss in a May 2026 New York Times piece.

## Adjacent domains
- [[MOC - AI Economics]]: the unit-economics and pricing detail (token deflation, build-vs-buy, moats) that this domain's trajectory forecasts and buildout numbers are ultimately bets on.
- [[MOC - Adoption & Blockers]]: the enterprise-side failure modes (pilot-to-production gap, evaluation gap) that this domain's navigation notes are built to route around before funding a pilot.
- [[MOC - AI Across Business Functions]]: the per-function deployment detail (support, legal, medical, HR) that the labor-market and use-case-picking notes here abstract into general patterns.
- [[MOC - AI in Software Engineering]]: the developer-productivity RCTs and agentic-coding evidence behind this domain's coding-assistant rows and METR horizon numbers.
- [[Ladder - Navigating the AI Economy]]: a guided walk through this domain in order, surface to unicorn, for building a full mental model instead of looking up one number.
