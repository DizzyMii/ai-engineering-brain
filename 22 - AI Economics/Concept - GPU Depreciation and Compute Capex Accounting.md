---
tags: [concept, domain/ai-economics, level/advanced]
aliases: [GPU Depreciation, Compute Capex Accounting, useful life GPU, AI depreciation debate]
summary: "How hyperscalers depreciate GPU capex, why useful-life swings reported AI profits, and whether 5-6yr schedules overstate earnings."
---

# Concept - GPU Depreciation and Compute Capex Accounting
> A GPU isn't expensed when it's bought. It's capitalized and written down over an assumed useful life. That one assumption, invisible in the headline, governs the largest cost of the AI buildout and is the lever that swings reported hyperscaler profit the most. Whether Microsoft's or Meta's AI-era earnings are real, or partly an accounting artifact, comes down to a number practitioners rarely think about: how many years a GPU "lasts."

## The mechanism

When a hyperscaler spends $30,000 on an H100, the income statement doesn't take the hit that year. The cost is **capitalized** onto the balance sheet as a fixed asset and released to the P&L as **depreciation expense** over the asset's assumed useful life. Straight-line, the annual expense is:

$$\text{annual depreciation} = \frac{\text{capitalized cost} - \text{salvage value}}{\text{useful life (years)}}$$

The useful-life denominator is a management estimate, and since depreciation is the dominant recurring cost of AI infrastructure, it matters enormously. Lengthen the life and each year's expense shrinks, so reported operating income rises, with no change in cash spent or hardware bought. Take the $1.5-2T of cumulative GPU-related capex placed on balance sheets 2023-2026 (E2, industry estimates):

| Assumed useful life | Annual depreciation on $1T of GPU capex |
|---|---|
| 3 years | ~$333B/yr |
| 5 years | ~$200B/yr |
| 6 years | ~$167B/yr |

The spread between the 3-year and 6-year rows, ~$166B/yr on a single trillion, is reported profit created or destroyed by the estimate. Nothing physical changed.

## In practice

The industry moved its schedules *longer* just as GPU capex exploded (E2, 10-K disclosures):

- **Microsoft** extended server and network-equipment life from ~4 to **6 years** (10-K range 2-6 years).
- **Meta** stepped useful life from 3yr (pre-2021) → 4yr (2021) → 4.5yr (2022) → 5yr → **5.5yr (effective Jan 2025)**. The 2025 change alone cut depreciation expense by ~$2.9B for the year (E2, 10-K).
- **Amazon** went the *other* way for a subset, **shortening** some servers from 6 to 5 years and citing "the increased pace of technology development, particularly in AI" (E2, 10-K). The long-life consensus isn't unanimous.
- Together, extending server life to 6 years saved the hyperscalers ~$18B/yr in reported depreciation (E1/E2).

**The Burry critique (Nov 2025, E2, his own estimate).** Michael Burry argued frontier GPUs become economically obsolete in ~2-3 years. Nvidia ships a new architecture every year (the Hopper → Blackwell → Rubin cadence), and each jump raises memory bandwidth and capacity ([[Concept - GPU Memory Hierarchy]]) and matmul throughput through new [[Concept - Tensor Cores]] (e.g., FP8/FP4 support). That collapses the previous generation's training economics and resale value. By his estimate, 5-6yr schedules understate depreciation by ~**$176B across the industry 2026-2028**, inflating AI-era earnings. He disclosed shorts across Nvidia and the AI hardware complex. Nvidia's memo to analysts rejected the fraud framing.

**The counter (E1): the waterfall.** A chip ages out of frontier *training* in 18-36 months but keeps earning for years on cheaper inference, fine-tuning and older workloads. [[Concept - Token Price Deflation]] drives demand here by pushing ever more inference volume onto older, cheaper silicon, and because of [[Concept - The Capability-Reliability Gap]], many production workloads never needed the frontier chip at all. If the asset really earns across a 5-6 year life, a long book life isn't fraud; it matches expense to the earning period, which is what depreciation is for. A high-end GPU losing ~half its resale value in ~3 years (E2) fits *either* story, so the resale curve alone doesn't settle the debate.

## Failure modes

- **Debt covenants trip when real life is shorter than booked life.** Neocloud GPU-backed debt (CoreWeave: >$21B total debt, ~$7.5B secured against GPU collateral, E2) assumes multi-year GPU cash flows to service the loans. The same multi-year assumption props up the [[Deep Dive - Circular Financing in the AI Buildout]] loops. Shorten the true useful life and the collateral value and debt-coverage math break; analysts flag covenant risk as early as 2027 (E2). This is the debt half of [[Reference - AI Venture Funding Patterns]].
- **Margins that look good on paper and thin in cash.** If depreciation is understated, hyperscaler AI segment margins and lab economics ([[Breakdown - Frontier Lab Economics]]) look healthier than the cash reality, and so does the capex-justification math behind the whole buildout. The schedule also decides how much buildout cost lands on hyperscaler versus lab books, shifting the profit pool across [[Concept - Value Capture Across the AI Stack]]. The overstatement flows into the numbers that reassure investors ([[Reference - AI Market Sizing Claims]]).
- **Detection signals.** Watch for (1) depreciation-schedule *changes* in 10-Ks timed to capex ramps, since a life extension right as spending explodes is a yellow flag; (2) a widening gap between capex cash outflow and reported operating income; (3) rising retirements or impairments of "still-useful" hardware, which would contradict the long-life story.

## The non-obvious

The same physical GPU is **two different assets depending on the regime**. In a shortage it's scarce, nearly appreciating, and rents at a premium. Once the next generation ships and supply loosens, it depreciates fast. Straight-line accounting has to pick *one* useful-life story, reality depends on the regime, and which regime holds is the bull/bear crux of [[Deep Dive - Bubble or Boom]]. The accounting isn't lying so much as forced to commit to one narrative about an uncertain earning life. That's why the AI-economics debate concentrates on depreciation. It's the one place where an unresolvable question about the future (how long will this compute earn?), a forecast with an unproven track record ([[Reference - The AI Forecasting Track Record]]), gets compressed into a single hard number on today's income statement. Practitioners learn this the hard way when a segment that looked profitable at 6-year lives goes underwater the moment the estimate is revised down.

## Connections
- [[Breakdown - Frontier Lab Economics]] — depreciation sits below the gross-margin line and shapes reported lab/hyperscaler profitability.
- [[Deep Dive - Circular Financing in the AI Buildout]] — the loops assume multi-year GPU cash flows; short lives tighten the financing math.
- [[Reference - AI Market Sizing Claims]] — understated depreciation flatters the ROI and margin claims.
- [[Reference - AI Venture Funding Patterns]] — GPU-backed debt is the funding structure most exposed to useful-life error.
- [[Deep Dive - Bubble or Boom]] — the regime-dependence of GPU value is the accounting core of the bubble debate.
- [[Concept - Value Capture Across the AI Stack]] — depreciation determines how much of the buildout's cost lands on hyperscaler vs. lab books.
- [[Reference - The AI Forecasting Track Record]] — calibration for the "how long will GPUs earn?" forecasts the schedules embed.
- [[Concept - Token Price Deflation]] — deflation is the demand-side reason old GPUs keep earning on cheap inference (the waterfall).
- [[Concept - The Capability-Reliability Gap]] — why older chips still find paying inference workloads even off the frontier.
- [[Concept - GPU Memory Hierarchy]] — the hardware substrate whose generational jumps (HBM capacity/bandwidth) drive obsolescence.
- [[Concept - Tensor Cores]] — the per-generation throughput gains (e.g., FP8/FP4) that make prior GPUs economically stale for training.

## Sources
- CNBC (Nov 14, 2025) — "How long before a GPU depreciates?"; Burry critique, hyperscaler 6-year schedules, CoreWeave/Nvidia context. E2.
- Michael Burry (Nov 2025) — ~$176B understated depreciation 2026-2028; short disclosures. E2 (his own estimate).
- Microsoft, Meta, Amazon 10-Ks (2023-2025) — useful-life disclosures: MSFT 4→6yr; Meta →5.5yr (~$2.9B/yr expense reduction); AMZN some servers 6→5yr. E2.
- Nvidia analyst memo (Nov 2025) — rebuttal rejecting fraud framing, asserting economic soundness. E2 (company response).
- Quartz / Forbes (2026) — CoreWeave GPU-collateralized debt (~$7.5B), covenant-trip risk ~2027. E2.
- Deep Quarry / MBI Deep Dives (2025) — waterfall counter-argument; GPU resale ~half value in ~3 years. E1/E2.
