---
tags: [breakdown, domain/applied-software, level/advanced]
aliases: [METR RCT, METR developer slowdown, METR productivity study, 2507.09089]
summary: "The 2025 METR RCT where AI made experienced devs 19% slower while they believed it made them 20% faster."
---

# Breakdown - The METR Developer Slowdown RCT

> A randomized controlled trial by METR (Model Evaluation & Threat Research), published July 2025, that measured what early-2025 AI coding tools actually did to the productivity of experienced open-source developers on their own mature repositories. It matters because it is the only sizeable *independent, randomized, real-work* study in a field otherwise dominated by vendor-run experiments on synthetic tasks — and it found a **slowdown**, not a speedup, in exactly the population everyone assumed AI helped. (Study: "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity", arXiv 2507.09089, July 2025.)

## The headline numbers

| Quantity | Value | Tier |
|---|---|---|
| Developers | 16 experienced OSS contributors | E3 (RCT) |
| Tasks | 246 real issues (bugs, features, refactors), randomized AI-allowed vs not | E3 |
| Prior experience on the repos | ~5 years average, large mature codebases | E3 |
| **Measured effect of allowing AI** | **+19% task completion time (i.e. 19% slower)** | E3 |
| Developer forecast *before* | 24% *speedup* expected | E3 |
| Developer estimate *after* finishing | still believed ~20% *speedup* | E3 |
| Toolchain | mainly Cursor Pro + Claude 3.5/3.7 Sonnet | E3 |

The perception-vs-reality gap is the single most important number in the whole applied-software domain: participants were wrong about the *direction* of the effect by roughly 40 percentage points, having lived through it. (All figures: METR 2025, arXiv 2507.09089, E3 — but note small N=16 and a specific population; see caveats.)

## How it actually works

The design is a within-developer randomized trial, which is what makes it credible despite the small headcount.

```
For each of 246 real tasks on the developer's own repo:
  1. Developer forecasts how long it will take (baseline + AI-allowed)
  2. Coin flip -> AI-ALLOWED or AI-FORBIDDEN for this task
  3. Developer does the task, screen recorded, self-reports time
  4. Task is a genuine issue/PR that gets merged (real work, real quality bar)
Compare AI-allowed vs AI-forbidden completion times WITHIN each developer.
```

Randomizing *per task within the same developer* cancels the biggest confounds — individual skill, repo difficulty, tooling familiarity — that wreck cross-sectional "teams with Copilot ship more" studies. Screen recordings let METR audit where the time actually went rather than trusting self-report (which, as it turned out, was catastrophically wrong). This is the methodological gulf between METR and the vendor studies in the [[Breakdown - GitHub Copilot's Measured Productivity Impact]] body of evidence, and it is why this note sits at `advanced` alongside the [[Reference - Developer Productivity Studies]] catalog.

## The clever parts

- **Within-subject randomization over real merged tasks.** Most coding-productivity studies use a synthetic greenfield task (Peng's HTTP server) or an observational adoption metric (PRs/week after rollout). METR randomized the *treatment* on genuine tasks that had to meet the repo's real review bar. That kills the task-selection and population confounds in one move, which is exactly the kind of design [[Concept - Statistical Rigor in Model Evaluation]] demands.
- **It captured belief and reality separately.** Forecast, post-hoc estimate, and stopwatch were three distinct measurements. Almost no other study measures the self-report error, and the self-report error turned out to be the finding.
- **Screen-recording forensics.** METR could attribute the lost time to concrete activities — prompting, waiting on generations, reading and reviewing AI output, and cleaning up AI suggestions that didn't meet the quality bar — rather than inferring it. This is the [[Concept - The Capability-Reliability Gap]] made visible as wall-clock minutes: the model was capable of drafting a plausible patch, but on a codebase the developer knew cold, verifying and repairing that draft cost more than writing it.

Why these developers slowed (METR's stated factors):
1. **Very high prior repo familiarity** — the developers averaged ~5 years on these codebases; there was little the model could tell them they didn't already know faster.
2. **A high quality bar** that rejected a large share of AI output, so review-and-discard was pure overhead.
3. **Large, complex codebases** where the model's context window and retrieval couldn't hold the relevant state — a direct instance of [[Concept - Context Rot]].
4. **Time lost to reviewing and fixing** AI suggestions, the tax that the [[Deep Dive - Agentic Coding in Production]] oversight economics predict.

## What it got wrong / what's dated

Read the scope honestly — this note is a defect if quoted as "AI makes developers slower," full stop.

- **N=16, one population.** These are elite open-source maintainers on repos they've owned for years. That is precisely the population where *every* prior study (Peng 2023, Cui et al. 2024) found the *smallest* benefit, because juniors and newcomers gain the most. The result does **not** generalize to greenfield work, junior developers, or unfamiliar code — see [[Breakdown - GitHub Copilot's Measured Productivity Impact]] for where gains are real.
- **Early-2025 tooling.** The stack was Cursor Pro + Claude 3.5/3.7 Sonnet — strong for its moment, but agentic coding moved fast afterward. The point estimate is a snapshot, not a law of nature.
- **Self-reported task time**, though screen-recording corroboration mitigates this.
- **Not a retraction, a rethink.** METR announced (Feb 2026) it is revising the experiment design to measure uplift more robustly. The finding stimulated a methodological correction across the field, not a walk-back — which is the opposite of the vendor pattern of quietly softening claims.

## What to steal

- **Measure output, never feeling.** The durable transferable lesson: developers cannot introspect their own speedup. Any AI-ROI program built on "our engineers report saving 30% of their time" — which is most vendor ROI surveys and the modeled savings in [[Breakdown - AI-Driven Code Migrations]] — is measuring perception, and this RCT shows perception can invert the true sign. Instrument merged output, lead time, and rework; this is the core argument of [[Concept - The Evaluation Gap]] and the metrics section of [[Concept - Team Workflow Restructuring with AI]].
- **Task structure decides the outcome.** The same tools that slowed these developers 19% saved thousands of developer-years on mechanical migrations. Route autonomy by task class.
- **Randomize within-subject** if you run your own internal study — it is the only cheap way to beat the confounds.
- **AI's value falls as your familiarity rises.** The tool helps most where you know least, which inverts the naive assumption that senior engineers extract the most from it. This connects to why capability curves and reliability curves diverge in [[Concept - METR Time Horizons]] and [[Concept - AI Coding Assistants]], and why revenue for tools like [[Breakdown - Cursor]] proves demand, not measured output gains — Cursor Pro was the exact stack that slowed these developers.

## Connections

- [[Breakdown - GitHub Copilot's Measured Productivity Impact]] — the pro-speedup evidence this result contradicts; the two together define the real range of effect sizes.
- [[Reference - Developer Productivity Studies]] — the full evidence-tiered catalog this study anchors as the strongest independent RCT.
- [[Concept - The Capability-Reliability Gap]] — the slowdown is the gap billed as wall-clock minutes: capable drafts, expensive verification.
- [[Concept - AI Coding Assistants]] — this is the load-bearing counter-datapoint to "AI makes coding faster."
- [[Breakdown - Cursor]] — Cursor Pro was the tested toolchain; demand ≠ measured productivity.
- [[Concept - AI's Effect on Code Quality and Security]] — the high quality bar that rejected AI output is the same maintainability pressure measured downstream.
- [[Deep Dive - Agentic Coding in Production]] — the review-and-fix tax quantified here is the oversight cost that note builds on.
- [[Concept - The Evaluation Gap]] — the self-report gap is why activity metrics and "feels faster" dashboards mislead.
- [[Concept - METR Time Horizons]] — METR's other measurement line; both show capability and reliability diverging.
- [[Concept - Team Workflow Restructuring with AI]] — the org-level version: teams can slow down while every developer feels faster.
- [[Concept - Statistical Rigor in Model Evaluation]] — the within-subject randomized design is the methodological standard other studies miss.
- [[Concept - Context Rot]] — large mature codebases exceeding the model's usable context is a named slowdown factor.

## Sources
- METR (Joel Becker, Nate Rush, Elizabeth Barnes, David Rein), 2025 — "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity", arXiv:2507.09089. The RCT itself; source of the 19% slowdown and the perception gap (E3).
- METR, Feb 2026 — announcement of a revised uplift-measurement design following the study.
- CMU S&DS Data Repository, 2025 — independent write-up of the METR effect used for teaching statistical methods.
