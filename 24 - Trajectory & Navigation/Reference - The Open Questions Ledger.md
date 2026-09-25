---
tags: [reference, domain/trajectory, level/frontier]
aliases: [Open Questions, AI Trajectory Unknowns, The Ledger, What Would Resolve It]
summary: "The genuinely unresolved questions that decide the AI trajectory — each with current state, the camps, and what evidence would settle it."
---

# Reference - The Open Questions Ledger

*Every row is E0/E1 by construction, since these are the open questions. The point is to state each one crisply and name the specific evidence that would move it, so you can update instead of argue. Date-stamped mid-2026 and expected to churn fast. Each gets its deep treatment in the linked owning note.*

## The ledger

| # | Question | Current state (mid-2026) | The camps | What would resolve it | Tier |
|---|---|---|---|---|---|
| 1 | Does the **data wall** bind? | Epoch: ~300T-token effective stock of quality human text; compute-optimal training hits it around **5e28 FLOP ≈ 2028** (80% CI 2026–2032). Frontier gains 2024–26 came mostly from post-training/RL, not more pretraining data. | *Binds:* pretraining is the engine, synthetic data risks collapse. *Routed around:* RL/RLVR + multimodal shift the bottleneck to compute & environments. | Whether frontier capability keeps climbing **without** more human pretraining text over 2026–2028. | E1/E2 |
| 2 | Is there a **reliability wall**? | METR 80%-horizon is ~5x shorter than the 50%-horizon; MIT NANDA: **~95%** of enterprise GenAI pilots show no P&L impact after $30–40B spend (Aug 2025). | *Engineering gap:* scaffolding, verification, RL close it. *Structural:* LLMs are ~good-enough-sometimes and won't hit unattended 99.9%. | Whether the 80%-horizon curve keeps doubling with the 50%-horizon, or decouples and flattens. | E1/E2 |
| 3 | **Bubble or boom**? | Sequoia's ~$600B revenue-gap question (2024); top-4 hyperscaler capex ~$650–700B by 2026; large circular-financing arrangements (Nvidia↔OpenAI↔clouds). Inference cost fell ~1000x 2023→2026. | *Bubble:* capex ≫ revenue, GPU depreciation overstates margins (Burry). *Boom:* deflation drives Jevons demand; revenue growing fast. | The **revenue/capex ratio** trend and whether a circular-financing unwind occurs. | E1 |
| 4 | Does AI **automate AI research** (takeoff)? | METR RE-bench uplift real but **bounded** (~0.5–0.8 of 8h-expert; agents sprint, plateau on long tasks). AI-2027 authors walked their superhuman-coder median from ~2027 to ~2030–2035 in late 2025. | *Fast/discontinuous:* R&D loop compresses to months. *Slow/diffuse:* GDP-visible over years. | Whether RE-bench-style R&D uplift keeps climbing toward full automation or saturates. | E1 |
| 5 | What is the **labor net effect**? | Stanford "Canaries" (ADP payroll): **~13% relative employment decline for 22–25yos** in the most AI-exposed jobs; older cohorts flat; no aggregate unemployment signal yet. Anthropic Economic Index: augmentation ~52% vs automation ~45%. | *Net-destructive:* entry-level hollows out the pipeline. *Net-neutral/creative:* complements + new roles absorb it (historical base rate). | Whether the entry-level signal spreads up the age/skill distribution or stays contained. | E1/E2 |
| 6 | **When — if ever — AGI**, and does the definition cohere? | Expert-survey medians span **~2033 (Metaculus full-AGI question #5121; weak-AGI #3479 is ~2028) to ~2047–2050 (AI Impacts survey, Cotra bio-anchors)**. "AGI/HLMI/transformative AI" name different targets. | *Short camp:* Amodei, Kokotajlo. *Long/skeptic:* LeCun (need new architectures), Marcus (reliability wall). | A shared operational definition + hitting it; until then the question is partly **ill-posed**. | E1/E2 |

## How to read this ledger

- **Nothing here is settled.** An E1 row isn't a soft E3. It's a real unknown, and confident assertion either way is the error. Anyone who calls row 3, 4, or 6 *resolved* is selling something.
- **The rows are coupled.** The data wall (1) feeds takeoff (4), which feeds the timeline (6). The reliability wall (2) gates the labor effect (5) and the bubble (3). A move in one propagates: if reliability (2) is a hard limit, takeoff (4) stalls and "boom" (3) weakens.
- **Watch the resolving evidence, not the debate.** Each row names one concrete thing to monitor. Updating on it beats collecting more opinions.
- **Provenance discount.** Forecasts with a fundraising or product incentive (inside-lab short timelines, vendor deflection numbers) get discounted, and aggregators with track records get weighted up; see [[Reference - The AI Forecasting Track Record]].

## Connections

- [[Concept - The Data Wall]] — owns row 1; the pretraining-exhaustion question and its escape routes.
- [[Concept - The Capability-Reliability Gap]] — owns the mechanism behind row 2; the 50/80 reliability split.
- [[Concept - The Pilot-to-Production Gap]] — the ~95%-pilot-failure evidence that makes row 2 live in the enterprise.
- [[Deep Dive - Bubble or Boom]] — owns row 3; the full capex-vs-revenue scenario analysis.
- [[Concept - Automated AI Research and Takeoff]] — owns row 4; the RSI mechanism and the AI-2027 walk-back.
- [[Deep Dive - AI and the Labor Market]] — owns row 5; the Stanford payroll and Anthropic Index evidence.
- [[Concept - The AGI Timeline Debate]] — owns row 6; the forecast spread and definitional chaos.
- [[Reference - The AI Forecasting Track Record]] — how to weight every number in this table.
- [[Lore - Failed AI Predictions]] — the base rate reminding you these questions have burned confident answerers before.

## Sources

- Villalobos et al. / Epoch AI (2022, updated 2024–26) — data-stock estimate (~300T tokens), 5e28 FLOP ≈ 2028 exhaustion point.
- MIT NANDA (Aug 2025) — *The GenAI Divide*; ~95% of pilots with no measurable P&L impact.
- Kwa et al. / METR (2025) & RE-bench (Wijk et al. 2025) — the horizon and R&D-uplift metrics behind rows 2 and 4.
- AI Futures Project (2025) — *AI 2027* and its late-2025 date walk-back (row 4).
- Brynjolfsson et al. / Stanford Digital Economy Lab (Aug/Nov 2025) — *Canaries in the Coal Mine*; ~13% young-worker decline (row 5).
- Sequoia (Cahn, 2024), Grace et al. / AI Impacts, Cotra / Open Phil, Metaculus — the bubble and timeline spreads (rows 3, 6).
