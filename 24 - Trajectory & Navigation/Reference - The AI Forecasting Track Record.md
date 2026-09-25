---
tags: [reference, domain/trajectory, level/advanced]
aliases: [AI Forecasting Track Record, AI Prediction Accuracy, Forecasting AGI Calibration]
summary: "Scorecard of how AI forecasting has actually performed, and a rule for weighting any AI forecast."
---

# Reference - The AI Forecasting Track Record

> Nearly every figure below is a moving target, date-stamped mid-2026. Forecasting the forecasters is itself E1.

## Calibration by forecaster type (as of 2026)

| Cohort | Track record | AI-specific reliability | Tier |
|---|---|---|---|
| Aggregator superforecasters (Metaculus pro cohort) | Best-performing on general questions; low Brier on benchmark sets¹ | Noisier on AI than on geopolitics/econ | E2 |
| AI-engaged forecasters (Samotsvety, AI Impacts) | Strong; shorter AI timelines than generic supers² | Better domain models; small n | E1/E2 |
| Generic superforecasters | Excellent general calibration | **Under-forecast compute/scaling** | E1/E2 |
| Expert surveys (published AI researchers) | Volatile; anchors to recent headlines | Point-estimates swing years/yr | E2 |
| Model-based (bio-anchors, scaling extrapolations) | Useful structure, weak point forecast | Fragile to input choices | E1 |
| Inside-lab pronouncements | — | Selection + fundraising incentive bias | E1 |
| LLM forecasters | Improving; below top human cohorts (2026) | Below superforecasters on AI | E1/E2 |

¹ Brier score: mean squared error of probabilistic forecasts, 0 = perfect, 0.25 = chance on 50/50 binaries. Superforecaster cohorts report Brier in the low-0.1s on benchmark question sets; treat specific AI-question figures as E1 given small samples and question heterogeneity.
² "Shorter" is directional, not an endorsement of accuracy. Engagement correlates with shorter timelines, a selection signal, not proof of calibration.

## Systematic direction of error (E1/E2)

| Quantity | Historical bias | Evidence |
|---|---|---|
| Raw scaling / compute growth | **Under-forecast** | Survey medians repeatedly revised *earlier* |
| Benchmark progress | **Under-forecast** | GSM8K/MMLU/coding saturated faster than expected (see [[Concept - Benchmark Saturation]]) |
| Reliable open-ended autonomy | **Over-forecast** | 50%-demo ≠ deployment; the [[Concept - The Capability-Reliability Gap]] |
| Self-driving (L5) | **Over-forecast** | "Next year" repeated ~annually since ~2015 |
| Task-vs-job displacement | **Over-forecast** | Radiologist/labor projections; [[Deep Dive - AI and the Labor Market]] |

**In short: capability gets under-forecast, reliability/adoption over-forecast.** Opposite errors, which averaging pundits blends into noise.

## Expert-survey volatility (E2)

| Survey | Median 50%-HLMI/AGI | Note |
|---|---|---|
| AI Impacts / Grace et al. 2022 | **2060** | 2,700+ published AI researchers |
| AI Impacts / Grace et al. 2023 | **2047** | Same instrument, **13-yr jump in one year** |
| (Prior 2016→2022 drift) | 2061 → 2060 | Only 1 yr of movement in 6 yrs, then the 2023 lurch |

A 13-year swing in one year is direct evidence that survey point estimates anchor to recent headlines (GPT-4, reasoning models), not to stable underlying models. Full spread in [[Concept - The AGI Timeline Debate]].

## Model-based fragility (E1)

| Method | Median | Movement | Author's own caveat |
|---|---|---|---|
| Cotra bio-anchors 2020 | TAI ~**2050** | — | Spans 20+ orders of magnitude of compute |
| Cotra bio-anchors 2022 update | TAI ~**2040** | −10 yr on modest input changes | "Fragile to parameter choices" |

Bio-anchors is useful *structure* (it makes you name your compute/algorithm assumptions) and a weak *point forecast*: its median moved a decade on input tweaks its author flagged.

## Aggregator compression (E2, prediction market)

| Date | Metaculus "first general AI" (full-AGI, #5121) median | ~P(by 2029) |
|---|---|---|
| Jan 2022 | ~2055 | low |
| ~2025-early 2026 | ~**2033** | ~25% |

Community medians compressed ~22 years in ~4 years. A *distribution shift*, not a converged date.

## How to weight any AI forecast

1. **Prefer distributions over dates.** A point estimate hides the fragility every method above shows.
2. **Discount for incentive.** Anything tied to a product launch, fundraise or disclosed market position (long *or* short) carries selection bias. Apply it symmetrically.
3. **Weight aggregators with a track record** above single-expert pronouncements and, *on AI specifically*, above generic superforecasters, who mis-forecast compute.
4. **Treat sub-decade "AGI" points as a tail, not a center.** Survey medians still sit ~2 decades out. Short timelines are a live tail view, not consensus.
5. **Separate the axes.** Capability-timeline forecasts and market/bubble forecasts (see [[Deep Dive - Bubble or Boom]]) are different questions with different error profiles. Never one number.

## Connections
- [[Concept - The AGI Timeline Debate]] — the timeline content this scorecard grades; the spread and named camps.
- [[Concept - METR Time Horizons]] — the metric that *reduced* forecast error by converting capability to human-time; the empirical anchor.
- [[Lore - Failed AI Predictions]] — the war stories (self-driving, radiologists, Watson) behind the systematic-error table.
- [[Concept - Automated AI Research and Takeoff]] — the takeoff timing forecasters are worst at; AI-2027's own dates moved +3-5 yr in a year.
- [[Reference - The Open Questions Ledger]] — the live questions this track record tells you how to weight.
- [[Reference - AI Market Sizing Claims]] — the market-forecast sibling; the same discount-for-incentive rule applies to TAMs.
- [[Reference - The 2026 Navigation Cheatsheet]] — where these weighting rules are applied to operator decisions.
- [[Concept - Benchmark Saturation]] — why benchmark progress was under-forecast, feeding the error-direction table.
- [[Concept - Statistical Rigor in Model Evaluation]] — the measurement discipline that separates real capability gains from noise in the forecasts.

## Sources
- Grace, K. et al. / AI Impacts (2022, 2023) — "Thousands of AI Authors on the Future of AI." HLMI median 2060→2047 (E2, survey).
- Cotra, A. / Open Philanthropy (2020, 2022 update) — "Forecasting TAI with biological anchors." Median ~2050→~2040; author-acknowledged fragility (E1, model).
- Metaculus community "first general AI" question (#5121, 2022-2026) — median ~2055→~2033, ~25% by 2029 (E2, prediction market); the separate "weakly general AI" question (#3479) sits at a ~2028 median.
- Frey, C. & Osborne, M. (2013); self-driving forecast history — canonical over-forecasts of autonomy/displacement (E1/E2).
- Tetlock / Good Judgment + Samotsvety materials — superforecaster calibration and AI-engaged-forecaster comparisons (E1/E2; specific Brier figures E1).
