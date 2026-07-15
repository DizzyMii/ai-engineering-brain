---
tags: [reference, domain/trajectory, level/core]
aliases: [2026 navigation cheatsheet, where the money is 2026, AI trajectory cheatsheet]
summary: "Date-stamped, tier-marked lookup of profitable AI plays, the cost curve, the reliability frontier, and the forecast spread, as of mid-2026."
---

# Reference - The 2026 Navigation Cheatsheet

All rows date-stamped mid-2026. Tier per row, evidence-law style (E3 independently verified, E2 single credible source, E1 analyst/forecaster estimate, E0 speculation). This note ages fast by design — check dates before quoting.

## Profitable today (evidence survives scrutiny)

| Play | Evidence | Tier | Date | Detail |
|---|---|---|---|---|
| Coding assistants, human-in-the-loop | +26% PRs/week across 3 RCTs, ~4,900 devs (trials at Microsoft, Accenture, and an anonymous Fortune-100 firm) — **but** METR's separate RCT found experienced OSS devs 19% *slower* with AI on mature codebases (16 devs, 246 tasks, July 2025) | E2/E3, contested | 2024-2025 | [[Reference - Developer Productivity Studies]]; net signal: strong for boilerplate/novice-adjacent work, unproven-to-negative for expert work on unfamiliar large codebases |
| Support deflection, AI-in-the-loop | +14% issues/hr average, +34% for novices, ~0 for experts (Brynjolfsson-Li-Raymond RCT, 5,179 agents) | E3 | 2023/2025 | [[Breakdown - Klarna's AI Customer Service Bet]] shows the same pattern at company scale — works, but not as a full headcount replacement (see Overhyped table) |
| Medical scribes | Modest, consistent time savings: 16 min/8hr saved documentation, 13 fewer min in EHR, ~1 extra patient/2 weeks across 1,800 clinicians, 5 academic centers, 2023-2025; a separate UCLA RCT found only ~41 sec/note reduction | E2/E3 | 2025-2026 | [[Breakdown - AI Medical Scribes]]; sold on burnout/well-being gains as much as raw time — do not expect dramatic throughput numbers |
| Content/marketing drafting | High adoption volume, but ROI not independently measured here — no RCT or named dollar figure backs this row | E1 | 2025-2026 | [[Reference - AI Impact by Business Function]]; adoption is not evidence of profitability — treat as unquantified until a named study lands |

## Overhyped / unproven (as of mid-2026)

| Claim | Why it doesn't hold up | Tier |
|---|---|---|
| Fully-autonomous agents in high-stakes unattended work | 80%-reliability time horizon is ~5x shorter than the 50%-horizon — models do far shorter tasks *reliably* than they do *sometimes* | E2, [[Concept - METR Time Horizons]] / [[Concept - The Capability-Reliability Gap]] |
| "AI replaces headcount" wholesale | Klarna's "700 agents" claim (2024) was walked back in 2025 — company rehired humans for disputes, complex refunds, and hardship cases after service quality dropped; current model is hybrid, not full replacement | E2, company-claimed then walked back — [[Breakdown - Klarna's AI Customer Service Bet]] |
| Generic enterprise pilots with no KPI | MIT NANDA: ~95% of pilots (of ~300 analyzed) showed no measured P&L impact after ~$30-40B enterprise spend; failure traced to workflow-integration gap, not model quality | E2, single study — [[Concept - The Pilot-to-Production Gap]] |

## Cost curve

| Metric | Value | Tier | Date |
|---|---|---|---|
| Fixed-capability-bar deflation rate | ~10x/yr headline (a16z); ranges 9x-900x/yr by capability tier (Epoch AI, commodity tasks deflate fastest) | E2 | a16z Nov 2024; Epoch AI 2025 |
| GPT-3-equivalent quality (MMLU 42) | ~$60/M tokens (late 2021) → ~$0.06/M (late 2024), ~1000x in 3 yrs | E2, a16z "LLMflation" analysis of published price lists | dated to Nov 2024 read |
| GPT-4-class output pricing | ~$30/M (early 2023) → ~$0.40-0.80/M (2026), ~40-70x — do not conflate with the 1000x figure above, different capability bars | E1/E2, provider list prices + aggregator trackers, noisy | 2026 |

Full mechanism and margin implications: [[Concept - Token Price Deflation]].

## Reliability frontier

| Metric | Value | Tier | Date |
|---|---|---|---|
| Frontier 50%-success time horizon | Doubling ~every 7 months 2019-2025 → ~4.3 months since 2023 → ~3 months since 2024 (accelerating, not steady); strongest shared model reached ~16-20 hrs | E2, METR Time Horizon 1.1 (doubling rates); METR Frontier Risk Report (16-20hr figure, joint pilot w/ Anthropic, Google, Meta, OpenAI) | Jan 2026; May 2026 |
| Frontier 80%-success time horizon | ~5x shorter than the 50%-horizon; strongest shared model ~3-4 hrs | E2, METR | May 2026 |
| Measurement ceiling | Original suite unreliable above ~16 hrs; TH1.1 added longer tasks, itself a sign of top-end saturation pressure | E2, METR (self-reported limitation) | Jan 2026 |

Design implication: build for supervised, checkable tasks scoped inside the 80%-horizon, not the more-often-quoted 50%-horizon; see [[Concept - METR Time Horizons]] and step 1 of [[Playbook - Picking Profitable AI Use Cases]].

## Forecast spread (never averaged — see [[Concept - The AGI Timeline Debate]])

| Camp | Median estimate | Tier | Source |
|---|---|---|---|
| Short / lab-affiliated | Amodei: "as early as 2026" (Oct 2024), narrowed to "late 2026/early 2027" (Anthropic OSTP, Mar 2025). AI-2027 (Kokotajlo et al., Apr 2025) walked its own headline milestone back to ~2030 in a Dec 2025 revision | E2/E1, company-affiliated or self-revised scenario — name the fundraising/narrative incentive explicitly | Amodei 2024-25; AI Futures Project 2025-26 |
| Aggregator market | Metaculus full-AGI question (#5121) community median ~2033 (~25% by 2029), down from ~2055 (Jan 2022) — a ~22-year compression in ~4 years; the separate lower-bar "weakly general AI" question (#3479) sits ~2028 and remains **open, not resolved** | E2, prediction market, self-selected forecasting community, moving target | Metaculus, 2022-2026 |
| Expert survey median | 2047 (2023 survey), up from 2060 (2022 survey) — a 13-year jump in one year, read as evidence surveys anchor to recent headlines (GPT-4 shipped between rounds) rather than a stable model | E2, single survey series, response/selection bias | Grace et al. / AI Impacts, 2023 |
| Model-based (bio-anchors) | 2050-2052 (2020 original) → 2040 (2022 update, based on faster-than-expected scaling), spans 20+ orders of magnitude of compute, author-flagged as fragile to input choices in both versions | E1, model | Cotra / Open Philanthropy, 2020 & 2022 |

Four methods, four different numbers, decades apart — not a range to average. The systematic pattern per [[Reference - The AI Forecasting Track Record]]: raw capability/scaling has historically been *under*-forecast (surveys revised earlier), while reliable open-ended autonomy and full job displacement have historically been *over*-forecast — the same asymmetry the reliability-frontier row above is evidence for. Full spread and provenance weighting: [[Reference - The AI Forecasting Track Record]].

## No-regret moves (hold in bubble or boom)

- Own proprietary data and workflow lock-in, not a thin prompt wrapper — see [[Concept - What Stays Valuable Through Any Scenario]].
- Stay model-agnostic; churn and ~10x/yr deflation punish deep single-vendor integration — [[Decision - Build vs Buy vs Wrap]].
- Instrument evals with a real baseline before funding a pilot — [[Playbook - Picking Profitable AI Use Cases]] step 6.
- Buy or wrap commodity capability rather than building it in-house — same deflation math as above.
- These four survive both the bear and bull case in [[Deep Dive - Bubble or Boom]] because they don't depend on which case is true.

## Footnotes
- Every $ and % figure above is date-stamped; treat anything undated as stale.
- Vendor-claimed figures (Klarna's original "700 agents," any single-company ROI number) are flagged E2 company-claimed and paired with their correction where one exists, per STANDARDS §8's contested-claims rule.
- This note is expected to be wrong within 6-12 months on the cost-curve and reliability-frontier rows specifically — re-verify before using in a funding decision.

## Connections
- [[Playbook - Picking Profitable AI Use Cases]] — the procedure this cheatsheet is the quick-reference companion to.
- [[Reference - AI Impact by Business Function]] — the per-function depth behind the "profitable today" table.
- [[Concept - Token Price Deflation]] — mechanism behind the cost-curve table.
- [[Concept - METR Time Horizons]] — mechanism behind the reliability-frontier table.
- [[Concept - What Stays Valuable Through Any Scenario]] — the reasoning behind the no-regret-moves row.
- [[Deep Dive - Bubble or Boom]] — why the no-regret moves are scenario-robust.
- [[Concept - The Pilot-to-Production Gap]] — the mechanism behind the MIT NANDA overhyped-table entry.
- [[Breakdown - Klarna's AI Customer Service Bet]] — the full case behind the Klarna row in both tables.
- [[Concept - The Capability-Reliability Gap]] — the mechanism behind the reliability-frontier design implication.
- [[Breakdown - AI Medical Scribes]] — the full evidence behind the medical-scribes row.
- [[Reference - The AI Forecasting Track Record]] — full provenance and weighting behind the forecast-spread table.

## Sources
- METR (Jan 29, 2026) — "Time Horizon 1.1." 50%/80% reliability-horizon doubling-time figures.
- METR (May 2026) — Frontier Risk Report, joint pilot with Anthropic, Google, Meta, OpenAI (Feb-Mar 2026 data). The 16-20hr/3-4hr frontier horizon figures.
- MIT NANDA (2025) — "The GenAI Divide: State of AI in Business 2025." ~95% no-P&L-impact figure.
- Andreessen Horowitz, "Welcome to LLMflation" (Guido Appenzeller, Nov 2024) — the 10x/yr framing and the $60/M→$0.06/M GPT-3-equivalent (MMLU 42) data point.
- Epoch AI (2025) — "LLM inference prices have fallen rapidly but unequally across tasks." The 9x-900x/yr range by capability milestone.
- Grace, K. et al. / AI Impacts (2022, 2023) — expert survey on HLMI timelines; 2060→2047 median jump.
- Cotra, A. / Open Philanthropy (2020, updated 2022) — bio-anchors report; 2050-52→2040 median.
- Amodei, D., "Machines of Loving Grace" (Oct 2024); Anthropic OSTP submission (Mar 2025) — the lab-affiliated "late 2026/early 2027" claim.
- Kokotajlo, D. et al. / AI Futures Project (April 2025; walk-back Dec 2025) — AI-2027 scenario and its revised ~2030 milestone.
- Metaculus — full-AGI question #5121 (community median ~2055 in Jan 2022 → ~2033, ~25% by 2029) and the separate weakly-general-AI question #3479 (~2028 median, still open, not resolved); aggregator medians tracked 2022-2026.
- Brynjolfsson, E., Li, D. & Raymond, L. (2023/2025) — support-agent RCT.
- Cui et al. (2024/2025) — "The Effects of Generative AI on High-Skilled Work: Evidence from Three Field Experiments with Software Developers" (SSRN 2024; Management Science 2025), n=4,867, +26.08%; and METR (2025) — contested developer-productivity RCTs.
