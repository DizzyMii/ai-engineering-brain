---
tags: [concept, domain/trajectory, level/core]
aliases: [Time Horizon, 50% Task-Completion Horizon, METR Horizon, Task-Completion Time Horizon]
summary: "METR converts capability into human-task-time, not percent-correct — the horizon doubles every 4-7 months and is accelerating."
---

# Concept - METR Time Horizons

> **One-paragraph hook:** Static benchmarks answer "what fraction of a fixed item set does the model get right." METR's time-horizon metric answers a different, more operational question: "how long a task, measured in the time it takes a skilled human, can this model complete unattended at a given reliability." That reframing is why the metric survived where [[Concept - Benchmark Saturation|static benchmarks saturated]] — a percentage tops out at 100%, but a time axis just keeps going, and by early 2026 the axis had moved from seconds to double-digit hours in six years.

## The mechanism

METR (Model Evaluation & Threat Research) built a suite of ~170 tasks spanning software engineering, cybersecurity, general reasoning, and ML research, each independently timed by measuring how long skilled humans take to complete it. For a given model, they measure success rate as a function of that human-task-duration, fit a logistic curve, and report the task length at which the fitted curve crosses 50% success — the *50% time horizon* (E3, Kwa et al./METR, "Measuring AI Ability to Complete Long Tasks," March 2025 — the methodology itself is a released, reproducible measurement, not an estimate).

The reframe matters mechanically. A fixed-item benchmark asks the same difficulty repeatedly and reports percent-correct; it saturates when models clear nearly every item. A time horizon asks "at what length does performance cross a threshold," and length has no ceiling — a model that clears every task in the suite simply has its horizon reported as "longer than we tested," which is itself informative (and is what happened by early 2026, see below). It also converts capability into a unit non-specialists reason about natively: not "94.3% on GPQA Diamond" but "this model reliably does what a skilled engineer does in about a workday."

## In practice

**Headline trend.** The 50%-horizon doubled roughly every 7 months from 2019 to 2025, rising from about 2 seconds (GPT-2) through roughly 50 minutes (Claude 3.7 Sonnet, early 2025) to nearly 2 hours (o3) (E2, METR 2025, 170-task suite). METR cross-checked the trend against ~9 other benchmarks — math, robotics, computer use, self-driving — and found broadly similar doubling rates, which is evidence the trend isn't an artifact of this one task suite (E2, METR 2025). The curve sits downstream of [[Concept - Scaling Laws]]: it is what compute-and-data scaling looks like once you measure its output in agentic task-completion rather than next-token loss.

**Acceleration and the Jan 2026 update.** The doubling time has been shortening, not holding steady: METR's *Time Horizon 1.1* release (Jan 29, 2026) reports the all-time doubling at 188 days (~6.3 months), but 129 days (~4.3 months) computed from 2023 onward, and just 89 days (~3 months) computed from 2024 onward (E2, METR 2026, single-org measurement, methodology revised between releases — treat the exact day-counts as fragile, the *direction* of acceleration as the robust finding). The 1.1 release also added longer-duration tasks and removed some flawed ones, which is itself an admission that the original suite was starting to run out of headroom at the top end — the same saturation pressure that hits static benchmarks, arriving later because the axis is time rather than percentage.

**Where the frontier sits as of mid-2026.** METR's May 2026 Frontier Risk Report, run jointly with Anthropic, Google, Meta, and OpenAI on a Feb-Mar 2026 pilot, put the strongest evaluated agents near or beyond the reliable measurement range of Time Horizon 1.1: roughly 16-20 hours at the 50% horizon and 3-4 hours at the 80% horizon for the most capable shared model (E2, METR 2026, joint-lab pilot — small sample, fast-moving, date-stamp any horizon number you repeat).

**The 50/80 gap.** METR consistently finds the 80%-reliability horizon is roughly 5x shorter than the 50%-horizon: a model that completes a 16-hour task half the time might only reliably (80%+) complete something closer to 3-4 hours of equivalent work, matching the mid-2026 pilot numbers above. This is the quantitative face of [[Concept - The Capability-Reliability Gap]] — the same underlying phenomenon showing up as a specific, measured multiplier rather than an anecdote. It means the honest deployment-ready number is closer to the 80% horizon than the more-often-quoted 50% one. Where the horizon meets messy, real (not benchmark-suite) engineering — merge conflicts, undocumented dependencies, ambiguous tickets — the gap tends to widen further, which is the pattern documented in [[Deep Dive - Agentic Coding in Production]] and [[Gotchas - Agents in Production]].

## Failure modes

**Extrapolating past the suite's coverage.** Naive extrapolation of a ~4-month doubling puts month-long autonomous tasks in the late 2020s, but this is load-bearing and contested: the curve could bend from [[Concept - The Data Wall|data]] or [[Deep Dive - The AI Compute Buildout|compute]] limits, or simply because real-world tasks lack the clean, checkable success criterion the suite requires (E1/E0, extrapolation beyond measured range — flag it as such whenever you cite a forward date). [[Reference - The AI Forecasting Track Record]] shows this is exactly the kind of extrapolation the field has a poor track record with; treat forward-projected horizon dates the same way you'd treat any other point forecast in [[Concept - The AGI Timeline Debate]] — as one input to a spread, not a date.

**Treating the metric as covering all work.** The suite is built almost entirely from tasks with an objective, checkable pass/fail — code that runs, a CTF flag, a correct numeric answer. Open-ended, context-heavy, judgment-laden work (the kind most white-collar jobs are actually made of) has no clean success signal and is structurally under-represented. A 16-hour horizon on checkable software tasks does not mean a model can be handed 16 hours of ambiguous strategic work — the metric overstates readiness for exactly the jobs people worry about, because those are the jobs it can't measure. This is the single most common misreading of the metric in the wild.

**Reporting the 50% number as the deployment number.** Because the 50/80 gap is roughly 5x, any headline like "models now do full workdays of autonomous work" that cites the 50% horizon is quietly reporting the number at which the model fails outright half the time. See [[Concept - The Evaluation Gap]] for why teams still need their own reliability threshold rather than borrowing METR's.

## The non-obvious

The metric's biggest limitation is also the reason it's trustworthy: it only scores tasks with a checkable success criterion, so it systematically cannot measure the categories of work — ambiguous scope, competing stakeholder judgment, taste — that determine whether an autonomous agent is actually safe to deploy unsupervised. That's a feature for measurement rigor (no fuzzy grading, the same discipline [[Concept - Statistical Rigor in Model Evaluation]] asks of any eval) and a trap for interpretation (the number looks like "general capability" and isn't). Practitioners who read "16-hour horizon" as "hire the agent for a two-day project" are making the same category error as reading a saturated MMLU score as "the model understands the subject" — mistaking a specific, well-defined proxy for the general thing it correlates with. It's also the same error, inverted, as [[Breakdown - The METR Developer Slowdown RCT]] catches in developers themselves: that study found engineers *felt* faster with AI tools while measured completion time was slower, which is a reminder that self-reported capability and measured capability diverge in both directions — models look more capable than the checkable-task horizon suggests to an impressed user, and developers felt more productive than the RCT's stopwatch showed. The horizon curve is also the concrete capability proxy that the fast-timeline case for [[Concept - Automated AI Research and Takeoff]] leans on most heavily — which is a reason to hold it carefully rather than extrapolate it casually.

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
