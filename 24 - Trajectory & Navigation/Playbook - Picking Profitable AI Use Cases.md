---
tags: [playbook, domain/trajectory, level/core]
aliases: [use case selection, AI use case prioritization, picking AI projects]
summary: "Six-step procedure for selecting AI use cases that pay off: filter by error tolerance, price verification, set a kill criterion up front."
---

# Playbook - Picking Profitable AI Use Cases
> **Goal:** stop funding pilots that can't survive production. **When to run this:** before committing budget to any new AI initiative, or when triaging an existing pilot backlog. **Prerequisites:** a candidate task list and someone willing to name a baseline metric before building.

## Steps

**1. Filter by error tolerance.**
For each candidate task, ask: if the model is wrong, who catches it, and how expensive is the miss? Place the task on [[Concept - The Capability-Reliability Gap]]: draft-then-review workflows (a human skims before anything ships) versus unattended-decision workflows (the output acts with no human gate). Tasks should split cleanly into "cheap to catch and undo" and "expensive, or silent, to get wrong."

If you can't say who catches the error, you have a demo, not a workflow. METR's reliability data makes this concrete. The 50%-success time horizon on frontier models is roughly 5x longer than the 80%-success horizon (E2, [[Concept - METR Time Horizons]], METR Time Horizon 1.1, Jan 2026), so a task the model "does" half the time is a very different bet from one it does reliably. Stop here if the task needs unattended 80%+ reliability and you're asking a frontier model to hit it cold.

**2. Default to augmentation over automation.**
Build the first version as a human-in-the-loop copilot, not a fire-and-forget agent, unless step 1 cleared the task for unattended use. Expect value to concentrate where AI closes a skill gap for your weaker performers, not where it replaces your strongest.

The cleanest causal evidence is Brynjolfsson, Li & Raymond's NBER/QJE randomized controlled trial of a conversational AI tool at a Fortune-500 support operation (5,179 agents): +14% issues resolved per hour on average, +34% for novice and low-tenure agents, and roughly zero for the most experienced (E3, RCT, published QJE 2025). The Anthropic Economic Index's November 2025 telemetry shows the same shape in usage patterns. 52% of Claude.ai conversations are augmentation (iterate, learn, get feedback) versus 45% automation (task handed off wholesale), with augmentation's share up 5 points in three months (E2, single-company telemetry, Jan 2026 report). On paid API traffic, where tasks are pre-scoped and programmatic, automation dominates at 75%. So augmentation-first is the safe default for open-ended human workflows, not a universal law. If your target users already skew expert, expect Brynjolfsson-Li-Raymond's near-zero effect, not the 34% novice number.

**3. Score value, not vibes.**
Compute `value = (value per task) x (volume) x (automatable fraction) − (verification cost + integration cost)` for every candidate with real counts, not guesses. High-volume, low-stakes, language-in/language-out tasks (support deflection, drafting, first-pass code review, coding assist) should top the ranking; [[Reference - AI Impact by Business Function]] has per-function magnitudes and [[Concept - Support Deflection Economics]] the deflection-specific version of this math. If a low-volume, high-complexity workflow tops your list, someone is scoring excitement. Re-run the formula with real numbers before going further.

**4. Price verification honestly. It's the hidden killer.**
Estimate what it costs to check the model's output. If checking costs nearly as much as doing the task, the ROI is gone whatever the model quality. Tasks with cheap, mechanical verification (unit tests, schema validation, a five-second human skim) survive. Tasks that need an expert to re-derive the answer don't.

MIT NANDA's 2025 "State of AI in Business" study (150 leader interviews, a 350-employee survey, 300 public deployments analyzed) found that after an estimated $30-40B in enterprise genAI spend, roughly 95% of pilots showed no measurable P&L impact (E2, single study, widely cited, methodology not independently replicated as of mid-2026). The report's diagnosis matches this step: failure tracked to workflow integration and a "learning gap," not model capability, and vendor-bought tools that adapt to existing workflow succeeded roughly 2x as often as internal builds. If verification cost climbs as you scale a pilot, the task is a poor fit. It isn't a prompting problem ([[Concept - The Pilot-to-Production Gap]]).

**5. Default to buy or wrap for commodity capability.**
Unless you own proprietary data or a durable workflow, buy or wrap an existing model/product instead of building custom infrastructure. Token prices for a fixed quality bar have fallen roughly 10x per year since 2022 (E2, a16z "LLMflation" analysis of published price lists, Nov 2024). GPT-3-equivalent (MMLU 42) quality fell from ~$60/M tokens (late 2021) to ~$0.06/M (late 2024), a ~1000x drop in three years. GPT-4-class output pricing fell separately, from roughly $30/M (early 2023) to the $0.40-0.80/M range by 2026, an ~40-70x drop. Different magnitude; don't conflate the two curves. Epoch AI's independent 2025 analysis agrees on direction but finds no single rate: it ranges 9x-900x/yr depending on which capability tier is held fixed. Under that deflation, in-house infrastructure ages fast ([[Concept - Token Price Deflation]], [[Decision - Build vs Buy vs Wrap]]).

If a vendor really can't reach your data or compliance boundary, that's a legitimate case for building. Check it isn't just NIH bias. Durable moats sit in data and workflow lock-in, not the model layer ([[Concept - Moats in the AI Application Layer]], [[Concept - What Stays Valuable Through Any Scenario]]).

**6. Set a kill criterion before you start.**
Before any code ships, write down the metric, the baseline, and the 3-6 month bar the pilot has to clear. With a named baseline, a pilot either clears the bar (keep funding) or doesn't (kill it on schedule). MIT NANDA found this discipline missing in the 95% that stalled, and its absence is the best single predictor of a pilot silently draining budget for a year ([[Concept - The Evaluation Gap]]).

## Verification
The playbook ran correctly if every candidate that reaches a build/buy decision has: an error-tolerance classification (step 1), an augmentation-first design unless explicitly cleared for automation (step 2), a value score from real volume and cost numbers (step 3), an honest verification-cost line (step 4), a buy/build decision with a stated reason (step 5), and a written kill metric with a deadline (step 6). A candidate missing any of these isn't ready to fund.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| No one can name the baseline metric | Kill criterion was never written | Step 6: stop and write it before spending further |
| Error is too costly to risk | Task needs unattended reliability the model can't hit today | Step 1: narrow scope to draft-then-review, or add a mandatory human gate |
| Margins are thin even after launch | You built commodity capability that a vendor now sells cheaper | Step 5: re-evaluate buy/wrap given current token pricing |
| Verification overhead keeps growing as you scale | The task lacks a cheap, mechanical check | Step 4: this is a poor-fit task, not a prompt-engineering problem |
| Pilot "works" in demo but stalls at rollout | Augmentation designed as automation, or integration cost was never scored | Steps 2-3: redesign around human-in-the-loop and re-run the value formula |
| Everyone loves it, nobody can say what it saved | No baseline was set, so there's nothing to compare against | Step 6, retroactively: set one now or kill it |

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
