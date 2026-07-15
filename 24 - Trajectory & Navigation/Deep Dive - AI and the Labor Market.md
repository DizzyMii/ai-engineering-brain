---
tags: [deep-dive, domain/trajectory, level/advanced]
aliases: [AI and Jobs, AI Labor Market, AI Employment Impact, AI Automation Jobs]
summary: "The measured 2026 labor evidence, and why aggregate unemployment is the wrong dashboard to watch."
---

# Deep Dive - AI and the Labor Market

> **One-paragraph hook:** Almost everything written about AI and jobs is a forecast, and forecasts of this kind have a documented history of being wrong in both directions. This note ignores the projections and assembles the *measured* evidence available by mid-2026 — one clean randomized trial, one large payroll panel, and the labs' own usage telemetry. The evidence does not say "mass unemployment." It says something more specific and more actionable: AI compresses the skill distribution, and its first labor bite lands at the entry level — the exact rung that trains the next generation of experts. The right dashboard is not the unemployment rate; it is *who gets hired, at what level, into which tasks.*

## The mechanism — augmentation compresses the skill distribution

Start with the cleanest causal evidence, because it reveals the mechanism the rest of the data then confirms at scale.

**Brynjolfsson, Li & Raymond, "Generative AI at Work" (NBER w31161, 2023)** (E3, RCT-grade — staggered rollout across 5,179 support agents at a Fortune-500 firm): access to an LLM assistant raised issues-resolved-per-hour by **+14% on average**, decomposing to **+34% for novice/low-skilled agents and ~0% for experienced agents**. The interpretation is the load-bearing one: the tool works by *diffusing the tacit knowledge of the best agents to everyone else* — it moves novices down the experience curve. AI here is a **skill-leveler**, and its value concentrates precisely where it closes a skill gap. This is the mechanistic root of the augment-before-automate pattern that shows up everywhere downstream, and it directly informs **[[Playbook - Picking Profitable AI Use Cases]]** (deploy where AI closes a gap) and **[[Concept - Support Deflection Economics]]**.

If AI raises the floor toward the ceiling, two things follow: the *return to junior tacit skill falls* (the model supplies it), and the *return to whatever the model can't yet do rises*. That asymmetry is what the population data then picks up.

## Architecture / walkthrough — the three tiers of evidence

Rank labor evidence by causal strength; treat the tiers accordingly.

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

**Tier 2 — the population signal.** Stanford Digital Economy Lab, **"Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of AI"** (Brynjolfsson et al., ADP payroll, Aug 2025, updated Nov 2025) (E2/E3, large panel, single team): workers aged **22-25 in the most AI-exposed occupations** (entry-level software, customer service, some accounting) saw a **~13% relative employment decline** since late 2022 (some cuts of the data reach ~16%), while older cohorts in the same occupations held flat or grew. Crucially the effect is *compositional* — concentrated in automating applications, muted where AI augments — and it shows up at the entry level first.

**Tier 3 — the labs' own telemetry.** The **Anthropic Economic Index** (2025-26) classifies Claude usage as augmentation vs automation. As of the Nov 2025 sample, **~52% augmentation vs ~45% automation** on Claude.ai — but this is volatile: automation actually *led* 49-47% in the August 2025 sample before product changes (file creation, memory, Skills) pushed usage back toward collaborative patterns. Two durable facts survive the noise: **API users automate more than consumers** (so first-party consumer telemetry *understates* where automation is going), and **the automation share has trended up** across 2025-26 even as augmentation still leads. This is company data (E2) — informative about usage, not a labor-market census.

## The clever/contested parts

**The pattern that actually matters: automation hits the training ground first.** The entry-level tasks AI automates *are* the apprenticeship — the work through which juniors become seniors. The near-term threat is therefore less to incumbent employment than to the **talent pipeline** (the "canary" framing). A firm that automates its junior rung today may find it has no mid-career experts in five years. This is a genuinely non-obvious second-order effect and it reframes "AI took entry-level jobs" from a wage story into a human-capital-formation story. It connects to **[[Concept - What Stays Valuable Through Any Scenario]]** — judgment and taste, the senior skills, hold value precisely because the model supplies the junior ones.

**The augment→automate trajectory (E2, AEI).** Augmentation leads *today*, but the automation share is rising and API traffic automates more than consumer traffic. The honest read: augmentation is the current center of gravity, not a permanent equilibrium. The **[[Concept - The Capability-Reliability Gap]]** and **[[Concept - METR Time Horizons]]** 50/80 reliability gap explain *why* — models cross into unattended automation only as the reliable-task horizon lengthens, which is happening but bounded.

**Why the projections are E1 and to be discounted.** Frey & Osborne (2013) famously put **47% of US jobs at "high risk" of automation**; subsequent McKinsey/PwC waves gave other headline shares. These missed badly on *timing* and *net effect* — they counted automatable *tasks* and implied lost *jobs*, conflating the two, and did not anticipate that automating tasks within a job often *raises* demand for the job (the radiologist pattern). Treat any "X% of jobs" headline as low-tier, per **[[Reference - The AI Forecasting Track Record]]** and the war stories in **[[Lore - Failed AI Predictions]]**. The developer-specific slice of this evidence lives in **[[Reference - Developer Productivity Studies]]** and **[[Breakdown - The METR Developer Slowdown RCT]]** — where measured productivity effects were smaller and sometimes negative versus perceived gains.

## Failure modes

- **Watching aggregate unemployment.** By the time AI's effect shows in the headline unemployment rate, the compositional adjustment (who gets hired, at what level) is long underway. The rate is a lagging, aggregating dashboard that hides the signal.
- **Conflating task automation with job elimination.** The single most common error (see the radiologist story); a job is a bundle of tasks, and automating some can raise demand for the rest.
- **Over-trusting first-party telemetry.** Anthropic/OpenAI usage data is informative but self-selected and consumer-weighted; it *understates* automation because heavy automation runs on the API.
- **Extrapolating the RCT to all work.** The +34%-novice result is a call-center finding with a checkable success signal; open-ended judgment work with no clean metric is under-measured — the same blind spot as **[[Concept - The Evaluation Gap]]** and the METR horizon caveat.

## The non-obvious

Aggregate unemployment is the wrong dashboard. The early, real signal is **compositional**: a ~13% relative decline for 22-25-year-olds in exposed jobs coexists with a flat *national* unemployment rate and *no clear aggregate signal* in exposed occupations as of early 2026. Both facts are true at once because the adjustment is happening at the margin — in hiring composition, not in mass layoffs. Practitioners and policymakers watching the unemployment rate will conclude "nothing is happening" right up until the pipeline effect becomes structural. Watch entry-level hiring rates by occupation exposure; that is where the canary sings first, and by the time it reaches the aggregate the adjustment is well past its early stage.

## Evolution

The evidence base matured from projection to measurement: 2013-2020 was the era of task-based *forecasts* (Frey-Osborne, McKinsey), which aged poorly; 2023 brought the first *causal* micro-evidence (the call-center RCT); 2025 brought the first large *population* panel (Stanford/ADP) and continuous first-party *telemetry* (Anthropic Economic Index). The frontier now is disentangling augmentation from automation as capability crosses the reliability threshold — the augment-share is falling slowly, and the open question is whether it stabilizes (complements win, jobs persist reshaped) or inverts (automation dominates, the pipeline erodes). That fork, and the unresolved net job creation-vs-destruction question, is tracked in **[[Reference - The Open Questions Ledger]]**, and its market-scenario context is **[[Deep Dive - Bubble or Boom]]**.

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
