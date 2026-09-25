---
tags: [concept, domain/trajectory, level/core]
aliases: [Time Horizon, 50% Task-Completion Horizon, METR Horizon, Task-Completion Time Horizon]
summary: "METR converts capability into human-task-time, not percent-correct — the horizon doubles every 4-7 months and is accelerating."
---

# Concept - METR Time Horizons

> **One-paragraph hook:** Static benchmarks ask what fraction of a fixed item set the model gets right. METR's time-horizon metric asks something more operational: how long a task, measured in skilled-human time, can this model complete unattended at a given reliability? That reframing is why the metric survived where [[Concept - Benchmark Saturation|static benchmarks saturated]]. A percentage tops out at 100%. A time axis keeps going, and by early 2026 it had moved from seconds to double-digit hours in six years.

## The mechanism

METR (Model Evaluation & Threat Research) built a suite of ~170 tasks across software engineering, cybersecurity, general reasoning and ML research, and timed skilled humans on each. For a given model they measure success rate against that human task duration, fit a logistic curve, and report the task length where the curve crosses 50% success: the *50% time horizon* (E3, Kwa et al./METR, "Measuring AI Ability to Complete Long Tasks," March 2025; the methodology is a released, reproducible measurement, not an estimate).

Mechanically, the reframe matters. A fixed-item benchmark asks the same difficulty over and over and reports percent-correct, so it saturates once models clear nearly every item. A time horizon asks at what length performance crosses a threshold, and length has no ceiling. A model that clears every task in the suite just gets reported as "longer than we tested," which is informative in itself (and is what happened by early 2026; see below). It also puts capability in a unit non-specialists already think in. Instead of "94.3% on GPQA Diamond," you get "this model reliably does what a skilled engineer does in about a workday."

## In practice

**Headline trend.** The 50% horizon doubled roughly every 7 months from 2019 to 2025, from about 2 seconds (GPT-2) through roughly 50 minutes (Claude 3.7 Sonnet, early 2025) to nearly 2 hours (o3) (E2, METR 2025, 170-task suite). METR cross-checked the trend against ~9 other benchmarks (math, robotics, computer use, self-driving) and found broadly similar doubling rates, which suggests it isn't an artifact of this one suite (E2, METR 2025). The curve sits downstream of [[Concept - Scaling Laws]]. It's what compute-and-data scaling looks like when you measure output as agentic task completion instead of next-token loss.

**Acceleration and the Jan 2026 update.** The doubling time keeps shrinking. METR's *Time Horizon 1.1* release (Jan 29, 2026) puts the all-time doubling at 188 days (~6.3 months), 129 days (~4.3 months) from 2023 onward, and just 89 days (~3 months) from 2024 onward (E2, METR 2026, single-org measurement, methodology revised between releases; treat the exact day counts as fragile and the *direction* of acceleration as the robust finding). Version 1.1 also added longer tasks and removed some flawed ones. That's an admission the original suite was running out of headroom at the top: the same saturation pressure that hits static benchmarks, arriving later because the axis is time instead of percentage.

**Where the frontier sits as of mid-2026.** METR's May 2026 Frontier Risk Report, run jointly with Anthropic, Google, Meta and OpenAI on a Feb-Mar 2026 pilot, put the strongest evaluated agents near or past the reliable measurement range of Time Horizon 1.1: roughly 16-20 hours at the 50% horizon and 3-4 hours at the 80% horizon for the most capable shared model (E2, METR 2026, joint-lab pilot; small sample, fast-moving, date-stamp any horizon number you repeat).

**The 50/80 gap.** METR consistently finds the 80%-reliability horizon is roughly 5x shorter than the 50% horizon. A model that finishes a 16-hour task half the time might reliably (80%+) finish only something like 3-4 hours of equivalent work, which matches the mid-2026 pilot numbers above. It's [[Concept - The Capability-Reliability Gap]] expressed as a measured multiplier instead of an anecdote. The honest deployment-ready number is closer to the 80% horizon than the more-quoted 50% one. Where the horizon meets messy real engineering (merge conflicts, undocumented dependencies, ambiguous tickets), the gap tends to widen further, as documented in [[Deep Dive - Agentic Coding in Production]] and [[Gotchas - Agents in Production]].

## Failure modes

**Extrapolating past the suite's coverage.** Naively extending a ~4-month doubling puts month-long autonomous tasks in the late 2020s. That projection carries a lot of weight and is contested. The curve could bend from [[Concept - The Data Wall|data]] or [[Deep Dive - The AI Compute Buildout|compute]] limits, or because real-world tasks lack the clean, checkable success criterion the suite needs (E1/E0, extrapolation beyond the measured range; flag it whenever you cite a forward date). [[Reference - The AI Forecasting Track Record]] shows the field's record on this kind of extrapolation is poor. Treat forward-projected horizon dates like any other point forecast in [[Concept - The AGI Timeline Debate]]: one input to a spread, not a date.

**Treating the metric as covering all work.** The suite is built almost entirely from tasks with an objective pass/fail: code that runs, a CTF flag, a correct numeric answer. Open-ended, context-heavy, judgment-laden work, which is most of what white-collar jobs consist of, has no clean success signal and is under-represented by design. A 16-hour horizon on checkable software tasks doesn't mean a model can take on 16 hours of ambiguous strategic work. The metric overstates readiness for the jobs people worry about most, because those are the jobs it can't measure. This is the most common misreading of it in the wild.

**Reporting the 50% number as the deployment number.** With a roughly 5x 50/80 gap, a headline like "models now do full workdays of autonomous work" that cites the 50% horizon is reporting the length at which the model fails outright half the time. [[Concept - The Evaluation Gap]] covers why teams still need their own reliability threshold instead of borrowing METR's.

## The non-obvious

The metric's biggest limitation is also why it's trustworthy. It only scores tasks with a checkable success criterion, so it can't measure the work (ambiguous scope, competing stakeholder judgment, taste) that decides whether an autonomous agent is safe to run unsupervised. That helps measurement rigor: no fuzzy grading, the discipline [[Concept - Statistical Rigor in Model Evaluation]] asks of any eval. It's a trap for interpretation, because the number looks like "general capability" and isn't. Reading "16-hour horizon" as "hire the agent for a two-day project" is the same category error as reading a saturated MMLU score as "the model understands the subject": a specific, well-defined proxy mistaken for the general thing it correlates with.

[[Breakdown - The METR Developer Slowdown RCT]] catches the inverse error in developers. Engineers *felt* faster with AI tools while measured completion time was slower. Self-reported and measured capability diverge in both directions: to an impressed user, models look more capable than the checkable-task horizon suggests, and developers felt more productive than the RCT's stopwatch showed. The horizon curve is also the concrete capability proxy the fast-timeline case for [[Concept - Automated AI Research and Takeoff]] leans on hardest, which is a reason to hold it carefully and not extrapolate it casually.

## Connections
- [[Concept - Benchmark Saturation]] — the static-benchmark problem this metric was built to route around by measuring length instead of a percentage that tops out.
- [[Concept - The Capability-Reliability Gap]] — the 50/80 horizon gap is this metric's quantitative version of that broader reliability shortfall.
- [[Breakdown - The METR Developer Slowdown RCT]] — same organization, a companion finding that self-reported speedup and measured speedup diverge, a caution that applies to reading horizon numbers too.
- [[Concept - The AGI Timeline Debate]] — horizon extrapolation is one of the inputs short-timeline forecasts lean on; this note supplies the actual curve, that note supplies the honest spread of dates drawn from it.
- [[Concept - Automated AI Research and Takeoff]] — the horizon trend is the capability proxy the takeoff/R&D-automation case is extrapolated from.
- [[Reference - The AI Forecasting Track Record]] — where to weigh how much to trust forward extrapolation of this specific curve.
- [[Deep Dive - Agentic Coding in Production]] — where the horizon numbers meet messy, real (not benchmark) engineering work.
- [[Concept - The Data Wall]] — one of the named candidate mechanisms that could bend the horizon curve if pretraining data is the bottleneck behind it.
- [[Concept - Scaling Laws]] — the underlying compute/data scaling relationship that the horizon curve is a downstream, agentic-task expression of.
- [[Concept - Statistical Rigor in Model Evaluation]] — the same rigor questions (sample size, suite coverage, curve-fitting assumptions) apply to reading METR's logistic fits, not just static-benchmark leaderboards.
- [[Gotchas - Agents in Production]] — the concrete production failure modes that show up well inside the "reliable" side of the 80% horizon.

## Sources
- Kwa, West, et al. / METR (March 19, 2025) — *Measuring AI Ability to Complete Long Tasks*. Original methodology, the 7-month doubling, and the GPT-2-to-o3 curve.
- METR (Jan 29, 2026) — *Time Horizon 1.1*. Revised suite; the 188/129/89-day doubling-time breakdown by period.
- METR (May 2026) — *Frontier Risk Report* (joint pilot with Anthropic, Google, Meta, OpenAI, Feb-Mar 2026). The 16-20hr / 3-4hr frontier numbers.
- METR — cross-domain check across ~9 other benchmarks (math, robotics, computer use, self-driving), cited in the March 2025 release, supporting the trend is not a single-suite artifact.
