---
tags: [deep-dive, domain/trajectory, level/advanced]
aliases: [AI and Jobs, AI Labor Market, AI Employment Impact, AI Automation Jobs]
summary: "The measured 2026 labor evidence, and why aggregate unemployment is the wrong dashboard to watch."
---

# Deep Dive - AI and the Labor Market

> **One-paragraph hook:** Nearly everything written about AI and jobs is a forecast, and forecasts like these have a documented record of being wrong in both directions. This note skips the projections and collects the *measured* evidence available by mid-2026: one clean randomized trial, one large payroll panel, and the labs' own usage telemetry. It doesn't say "mass unemployment." It says something narrower. AI compresses the skill distribution, and its first labor bite lands at the entry level, the rung that trains the next generation of experts. So watch *who gets hired, at what level, into which tasks*, not the unemployment rate.

## The mechanism: augmentation compresses the skill distribution

The cleanest causal evidence shows the mechanism; the rest of the data confirms it at scale.

**Brynjolfsson, Li & Raymond, "Generative AI at Work" (NBER w31161, 2023)** (E3, RCT-grade; staggered rollout across 5,179 support agents at a Fortune-500 firm). Access to an LLM assistant raised issues resolved per hour by **+14% on average**, which breaks down to **+34% for novice/low-skilled agents and ~0% for experienced agents**. The tool works by *spreading the tacit knowledge of the best agents to everyone else*, moving novices down the experience curve. Here AI is a **skill-leveler**, and its value concentrates where it closes a skill gap. That's the root of the augment-before-automate pattern seen everywhere downstream, and it feeds straight into [[Playbook - Picking Profitable AI Use Cases]] (deploy where AI closes a gap) and [[Concept - Support Deflection Economics]].

If AI lifts the floor toward the ceiling, the *return to junior tacit skill falls* (the model supplies it) and the *return to whatever the model can't do yet rises*. The population data picks up that asymmetry.

## The three tiers of evidence

Rank labor evidence by causal strength and weight it accordingly.

```
 STRONGEST  ┌─────────────────────────────────────────────┐
 (E3 RCT)   │ Brynjolfsson-Li-Raymond call-center RCT 2023 │  MECHANISM:
            │ +14% overall / +34% novice / ~0 expert       │  skill compression
            └──────────────────────┬──────────────────────┘
                                    │
 STRONG     ┌──────────────────────▼──────────────────────┐
 (E2/E3     │ Stanford "Canaries in the Coal Mine" 2025    │  SIGNAL:
 panel)     │ ADP payroll; -13% relative employment for    │  entry-level first
            │ 22-25yos in most AI-exposed jobs             │
            └──────────────────────┬──────────────────────┘
                                    │
 SUGGESTIVE ┌──────────────────────▼──────────────────────┐
 (E2 first- │ Anthropic Economic Index 2025-26 telemetry   │  DIRECTION:
 party)     │ ~52% augment / ~45% automate; automate rising│  augment→automate
            └──────────────────────┬──────────────────────┘
                                    │
 WEAKEST    ┌──────────────────────▼──────────────────────┐
 (E1 model) │ "X% of jobs automatable" projections         │  DISCOUNT HEAVILY:
            │ Frey-Osborne 47%, McKinsey/PwC waves         │  historically wrong
            └─────────────────────────────────────────────┘
```

**Tier 2: the population signal.** Stanford Digital Economy Lab, **"Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of AI"** (Brynjolfsson et al., ADP payroll, Aug 2025, updated Nov 2025) (E2/E3, large panel, single team). Workers aged **22-25 in the most AI-exposed occupations** (entry-level software, customer service, some accounting) saw a **~13% relative employment decline** since late 2022 (some cuts of the data reach ~16%), while older cohorts in the same occupations held flat or grew. The effect is *compositional*. It's concentrated in automating applications, muted where AI augments, and it shows up at the entry level first.

**Tier 3: the labs' own telemetry.** The **Anthropic Economic Index** (2025-26) classifies Claude usage as augmentation vs automation. In the Nov 2025 sample it was **~52% augmentation vs ~45% automation** on Claude.ai. That's volatile: automation *led* 49-47% in the August 2025 sample before product changes (file creation, memory, Skills) pushed usage back toward collaborative patterns. Two facts hold through the noise. **API users automate more than consumers**, so first-party consumer telemetry *understates* where automation is heading. And **the automation share has trended up** across 2025-26 even while augmentation leads. This is company data (E2), informative about usage and not a labor-market census.

## The clever and contested parts

**Automation hits the training ground first.** The entry-level tasks AI automates *are* the apprenticeship, the work through which juniors become seniors. So the near-term threat is less to incumbent employment than to the **talent pipeline** (the "canary" framing). A firm that automates its junior rung today may have no mid-career experts in five years. This second-order effect turns "AI took entry-level jobs" from a wage story into a human-capital-formation story. It connects to [[Concept - What Stays Valuable Through Any Scenario]]: judgment and taste, the senior skills, hold their value because the model supplies the junior ones.

**The augment→automate trajectory (E2, AEI).** Augmentation leads *today*, but the automation share is rising and API traffic automates more than consumer traffic. Augmentation is the current center of gravity, not a permanent equilibrium. [[Concept - The Capability-Reliability Gap]] and the [[Concept - METR Time Horizons]] 50/80 reliability gap explain *why*: models cross into unattended automation only as the reliable-task horizon lengthens, which is happening, within limits.

**Why the projections are E1 and get discounted.** Frey & Osborne (2013) famously put **47% of US jobs at "high risk" of automation**, and later McKinsey/PwC waves gave other headline shares. They missed badly on *timing* and *net effect*. They counted automatable *tasks* and implied lost *jobs*, conflating the two, and didn't anticipate that automating tasks within a job often *raises* demand for the job (the radiologist pattern). Treat any "X% of jobs" headline as low-tier, per [[Reference - The AI Forecasting Track Record]] and the war stories in [[Lore - Failed AI Predictions]]. The developer-specific slice of this evidence is in [[Reference - Developer Productivity Studies]] and [[Breakdown - The METR Developer Slowdown RCT]], where measured productivity effects were smaller than perceived gains, and sometimes negative.

## Failure modes

- **Watching aggregate unemployment.** By the time AI shows up in the headline unemployment rate, the compositional adjustment (who gets hired, at what level) is long underway. The rate lags and aggregates, which hides the signal.
- **Conflating task automation with job elimination.** The most common error (see the radiologist story). A job is a bundle of tasks, and automating some can raise demand for the rest.
- **Over-trusting first-party telemetry.** Anthropic/OpenAI usage data is informative but self-selected and consumer-weighted. It *understates* automation because heavy automation runs on the API.
- **Extrapolating the RCT to all work.** The +34%-novice result is a call-center finding with a checkable success signal. Open-ended judgment work with no clean metric is under-measured, the same blind spot as [[Concept - The Evaluation Gap]] and the METR horizon caveat.

## The non-obvious

Aggregate unemployment is the wrong dashboard. The early, real signal is **compositional**. A ~13% relative decline for 22-25-year-olds in exposed jobs coexists with a flat *national* unemployment rate and *no clear aggregate signal* in exposed occupations as of early 2026. Both hold because the adjustment happens at the margin, in hiring composition, not in mass layoffs. Anyone watching the unemployment rate will conclude "nothing is happening" until the pipeline effect has set in. Watch entry-level hiring by occupation exposure. That's where the canary sings first, and by the time it reaches the aggregate the adjustment is well past its early stage.

## Evolution

The evidence moved from projection to measurement. 2013-2020 was the era of task-based *forecasts* (Frey-Osborne, McKinsey), which aged poorly. 2023 brought the first *causal* micro-evidence (the call-center RCT). 2025 brought the first large *population* panel (Stanford/ADP) and continuous first-party *telemetry* (Anthropic Economic Index). The current frontier is separating augmentation from automation as capability crosses the reliability threshold. The augment share is falling slowly, and the open question is whether it stabilizes (complements win, jobs persist in reshaped form) or inverts (automation dominates, the pipeline erodes). That fork, and the unresolved net creation-vs-destruction question, is tracked in [[Reference - The Open Questions Ledger]]; the market-scenario context is [[Deep Dive - Bubble or Boom]].

## Connections
- [[Concept - Support Deflection Economics]] — the call-center RCT is the mechanism behind support-desk deflection and its skill-leveling.
- [[Reference - AI Impact by Business Function]] — the per-function deployment detail this note abstracts into a labor pattern.
- [[Reference - Developer Productivity Studies]] — the developer-specific measured evidence, including where perceived gains exceeded real ones.
- [[Concept - The Capability-Reliability Gap]] — why augmentation leads automation: models do short tasks reliably, long ones only sometimes.
- [[Concept - METR Time Horizons]] — the 50/80 reliability gap that gates when a task crosses from augment to automate.
- [[Reference - The AI Forecasting Track Record]] — why "X% of jobs" projections are E1 and systematically mis-timed.
- [[Lore - Failed AI Predictions]] — the radiologist and self-driving busts that teach task-vs-job confusion.
- [[Concept - What Stays Valuable Through Any Scenario]] — senior judgment/taste hold value precisely because AI supplies junior skill.
- [[Deep Dive - Bubble or Boom]] — the market-scenario frame the labor question sits inside.
- [[Concept - The Pilot-to-Production Gap]] — why measured P&L (and headcount) impact lags the capability hype.
- [[Reference - The Open Questions Ledger]] — the unresolved net-labor-effect question, tracked with resolution criteria.
- [[Concept - The AGI Timeline Debate]] — the capability-timeline spread that bounds how fast the automation share can rise.
- [[Breakdown - The METR Developer Slowdown RCT]] — the sharpest measured case of perceived-vs-real AI productivity in knowledge work.

## Sources
- Brynjolfsson, E., Li, D., Raymond, L. (2023) — "Generative AI at Work," NBER w31161. +14%/+34%/~0 across 5,179 agents; skill compression (E3 RCT).
- Brynjolfsson et al. / Stanford Digital Economy Lab (Aug 2025, updated Nov 2025) — "Canaries in the Coal Mine? Six Facts…" ADP payroll; ~13% relative decline for 22-25yos in exposed jobs (E2/E3 panel).
- Anthropic (2025-26) — Anthropic Economic Index reports. ~52% augment / ~45% automate (Nov 2025); automation rising; API automates more than consumer (E2, company data).
- Frey, C. & Osborne, M. (2013) — "The Future of Employment." 47% of US jobs "high risk"; the canonical mis-timed projection (E1, model).
