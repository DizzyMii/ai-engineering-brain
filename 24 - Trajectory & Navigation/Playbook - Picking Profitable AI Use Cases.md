---
tags: [playbook, domain/trajectory, level/core]
aliases: [use case selection, AI use case prioritization, picking AI projects]
summary: "Six-step procedure for selecting AI use cases that pay off: filter by error tolerance, price verification, set a kill criterion up front."
---

# Playbook - Picking Profitable AI Use Cases
> **Goal:** stop funding pilots that can't survive contact with production. **When to run this:** before committing budget to any new AI initiative, or when triaging an existing pilot backlog. **Prerequisites:** a candidate task list and someone willing to name a baseline metric before building.

## Steps

**1. Filter by error tolerance.**
Action: for each candidate task, ask "if the model is wrong, who catches it, and how expensive is the miss?" Map the task onto the [[Concept - The Capability-Reliability Gap]] — draft-then-review workflows (a human skims before anything ships) versus unattended-decision workflows (the output acts without a human gate).
Expected observation: tasks split cleanly into "cheap to catch and undo" and "expensive or silent to get wrong."
Deviation: if you can't say who catches the error, you don't have a workflow yet, you have a demo. METR's own reliability data makes this concrete — the 50%-success time horizon on frontier models is roughly 5x longer than the 80%-success horizon (E2, [[Concept - METR Time Horizons]], METR Time Horizon 1.1, Jan 2026), meaning a task the model "does" half the time is a very different bet than one it does reliably. Stop here if the task needs unattended 80%+ reliability and you're asking a frontier model to hit it cold.

**2. Prefer augmentation over automation as the default shape.**
Action: design the first version as a human-in-the-loop copilot, not a fire-and-forget agent, unless step 1 cleared the task for unattended use.
Expected observation: value concentrates where AI closes a skill gap for your weaker performers, not where it replaces your strongest.
Deviation: the cleanest causal evidence for this is Brynjolfsson, Li & Raymond's NBER/QJE randomized controlled trial of a conversational AI tool at a Fortune-500 support operation (5,179 agents): +14% issues resolved per hour on average, +34% for novice and low-tenure agents, and roughly zero effect for the most experienced agents (E3, RCT, published QJE 2025). The Anthropic Economic Index's November 2025 telemetry shows the same shape at the usage-pattern level: 52% of Claude.ai conversations are augmentation (iterate, learn, get feedback) versus 45% automation (task handed off wholesale), with augmentation share rising 5 points in three months (E2, single-company telemetry, Jan 2026 report). Contrast: on paid API traffic, where tasks are pre-scoped and programmatic, automation dominates at 75% — augmentation-first is the safe default for open-ended human workflows, not a universal law. If your target users skew expert already, expect Brynjolfsson-Li-Raymond's near-zero effect, not the 34% novice number.

**3. Score value, not vibes.**
Action: compute `value = (value per task) x (volume) x (automatable fraction) − (verification cost + integration cost)` for every candidate, using real counts, not guesses.
Expected observation: high-volume, low-stakes, language-in/language-out tasks (support deflection, drafting, first-pass code review, coding assist) dominate the ranking — see [[Reference - AI Impact by Business Function]] for per-function magnitudes and [[Concept - Support Deflection Economics]] for the deflection-specific version of this math.
Deviation: if the top of your ranked list is a low-volume, high-complexity workflow, someone is scoring excitement, not value. Re-run the formula with real numbers before proceeding.

**4. Price verification honestly — it is the hidden killer.**
Action: estimate the cost of checking the model's output. If checking costs nearly as much as doing the task, the ROI is gone regardless of model quality.
Expected observation: tasks with cheap, mechanical verification (unit tests, schema validation, a five-second human skim) survive; tasks needing an expert to re-derive the answer do not.
Deviation: this is why MIT NANDA's 2025 "State of AI in Business" study — 150 leader interviews, a 350-employee survey, and 300 public deployments analyzed — found that after an estimated $30-40B in enterprise genAI spend, roughly 95% of pilots showed no measurable P&L impact (E2, single-study, widely cited, methodology not independently replicated as of mid-2026). The report's own diagnosis matches this step: failure tracked to workflow integration and a "learning gap," not model capability — vendor-bought tools that adapt to existing workflow succeeded roughly 2x as often as internal builds. If verification cost is rising as you scale a pilot, that is a signal the task is a poor fit, not a prompting problem (link [[Concept - The Pilot-to-Production Gap]]).

**5. Default to buy or wrap, not build, for commodity capability.**
Action: unless you own proprietary data or a genuinely durable workflow, default to buying or wrapping an existing model/product rather than building custom infrastructure.
Expected observation: token prices for a fixed quality bar have fallen roughly 10x per year since 2022 (E2, a16z "LLMflation" analysis of published price lists, Nov 2024) — GPT-3-equivalent (MMLU 42) output quality fell from ~$60/M tokens (late 2021) to ~$0.06/M (late 2024), a ~1000x drop in three years; GPT-4-class output pricing separately fell from roughly $30/M (early 2023) to the $0.40-0.80/M range by 2026, an ~40-70x drop, not the same magnitude — don't conflate the two curves. Epoch AI's independent 2025 analysis corroborates the direction but finds the rate isn't one number — it ranges 9x-900x/yr depending on which capability tier is held fixed. Under that deflation, in-house infrastructure investment ages fast (link [[Concept - Token Price Deflation]], [[Decision - Build vs Buy vs Wrap]]).
Deviation: if your candidate use case requires building because a vendor genuinely can't reach your data or compliance boundary, that's a legitimate build case — but check it isn't just NIH bias. Durable moats sit in data and workflow lock-in, not in the model layer (link [[Concept - Moats in the AI Application Layer]], [[Concept - What Stays Valuable Through Any Scenario]]).

**6. Set a kill criterion before you start, not after.**
Action: write down the metric, the baseline, and the 3-6 month bar the pilot must clear, before any code ships.
Expected observation: a pilot with a named baseline either clears the bar (keep funding) or doesn't (kill it on schedule).
Deviation: this is precisely the discipline MIT NANDA found missing in the 95% that stalled, and its absence is the single best predictor of a pilot silently draining budget for a year (link [[Concept - The Evaluation Gap]]).

## Verification
You've run this playbook correctly if every candidate use case that survives to a build/buy decision has: a named error-tolerance classification (step 1), an augmentation-first design unless explicitly cleared for automation (step 2), a value score computed from real volume and cost numbers (step 3), an honest verification-cost line item (step 4), a buy/build decision with a stated reason (step 5), and a written kill metric with a deadline (step 6). If any candidate is missing one of these, it isn't ready to fund.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| No one can name the baseline metric | Kill criterion was never written | Step 6 — stop and write it before spending further |
| Error is too costly to risk | Task needs unattended reliability the model can't hit today | Step 1 — narrow scope to draft-then-review, or add a mandatory human gate |
| Margins are thin even after launch | You built commodity capability that a vendor now sells cheaper | Step 5 — re-evaluate buy/wrap given current token pricing |
| Verification overhead keeps growing as you scale | The task lacks a cheap, mechanical check | Step 4 — this is a poor-fit task, not a prompt-engineering problem |
| Pilot "works" in demo but stalls at rollout | Augmentation designed as automation, or integration cost was never scored | Steps 2-3 — redesign around human-in-the-loop and re-run the value formula |
| Everyone loves it, nobody can say what it saved | No baseline was set, so there's nothing to compare against | Step 6, retroactively — set one now or kill it |

For the compact version of these numbers with dates, see [[Reference - The 2026 Navigation Cheatsheet]].

## Connections
- [[Concept - The Capability-Reliability Gap]] — step 1's error-tolerance filter is this gap applied task-by-task.
- [[Concept - METR Time Horizons]] — supplies the 50%/80% reliability-gap numbers that make step 1 concrete rather than qualitative.
- [[Concept - Support Deflection Economics]] — the worked example of step 3's value formula for the highest-volume applied use case (support).
- [[Concept - The Pilot-to-Production Gap]] — names the failure mode step 4 and step 6 exist to prevent.
- [[Decision - Build vs Buy vs Wrap]] — the detailed tradeoff framework behind step 5's default.
- [[Reference - The 2026 Navigation Cheatsheet]] — compact, date-stamped lookup of the numbers cited throughout this playbook.
- [[Concept - What Stays Valuable Through Any Scenario]] — why step 5's bias toward buy/wrap over build holds regardless of where the market goes next.
- [[Concept - Token Price Deflation]] — the deflation curve that makes in-house build a depreciating bet.
- [[Deep Dive - AI and the Labor Market]] — the population-level evidence behind step 2's augmentation-first default.
- [[Reference - AI Impact by Business Function]] — per-function magnitudes to plug into step 3's scoring formula.
- [[Concept - Moats in the AI Application Layer]] — the theory of why buy/wrap beats build absent proprietary data.
- [[Concept - The Evaluation Gap]] — what a rigorous kill criterion (step 6) actually requires.
- [[Gotchas - Enterprise AI Adoption]] — the broader failure taxonomy this playbook is trying to route around.

## Sources
- Brynjolfsson, E., Li, D. & Raymond, L. (NBER working paper 2023; *Quarterly Journal of Economics* 2025) — "Generative AI at Work." RCT on 5,179 support agents: +14% average, +34% novice, ~0 expert.
- MIT NANDA / Project NANDA (2025) — "The GenAI Divide: State of AI in Business 2025." 150 interviews, 350-employee survey, 300 deployments; ~95% of pilots showed no measured P&L impact.
- Anthropic (January 2026) — Anthropic Economic Index report (November 2025 usage data). Claude.ai augmentation 52% vs automation 45%; API automation 75%.
- Andreessen Horowitz, "Welcome to LLMflation" (Guido Appenzeller, Nov 2024) — ~10x/yr deflation for a fixed capability bar; GPT-3-equivalent (MMLU 42) quality ~$60/M (2021) to ~$0.06/M (2024).
- Epoch AI (2025) — "LLM inference prices have fallen rapidly but unequally across tasks." Independent corroboration; 9x-900x/yr range by capability milestone.
