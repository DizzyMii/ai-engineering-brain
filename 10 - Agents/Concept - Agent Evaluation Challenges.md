---
tags: [concept, domain/agents, level/frontier]
aliases: []
summary: "Why scoring agents is harder than scoring single turns: trajectories, non-determinism, cost, and attribution break single-number scores."
---

# Concept - Agent Evaluation Challenges

> **One-paragraph hook:** A single-turn LLM eval asks whether one output is good. An agent eval has to ask whether the whole multi-step process was good, whether it stayed good across repeated runs, and whether it was worth the cost. A static benchmark score squashes those three questions into one number and misleads you about all of them.

## The mechanism

Single-turn evaluation scores one generation against a reference or rubric. Agent evaluation has to score a *trajectory*: a sequence of tool calls, observations and intermediate reasoning that can run for dozens of steps. Grading only the final state throws away most of the signal. Two agents can reach the same correct answer by very different paths. One used the minimum tool calls and checked its own work; the other brute-forced every plausible action until something stuck. Outcome-only scoring rates them the same. A full eval judges outcome (did it succeed) and process (was the path efficient, safe, not lucky) separately. The outlier is [[Breakdown - SWE-bench and SWE-agent]], which gets a free, objective outcome oracle from hidden tests that most agent domains don't have.

On top of that, agent runs are non-deterministic. Temperature, tool-call ordering and environment timing mean the *same* agent can run the same task twice, succeed once and fail once. For any task with real variance, a single-seed pass/fail score is close to noise. That's why benchmarks like tau-bench and tau2-bench report pass^k, the probability of succeeding k independent times in a row, instead of pass@1. pass^k falls fast even for agents with a decent pass@1. An agent that succeeds on 80% of individual runs only goes four-for-four (pass^4) about $0.8^4 \approx 41\%$ of the time, and production needs reliability more than raw capability.

The third problem is environment drift. A single-turn eval reads from a frozen dataset. An agent eval often has the agent touch a live website, a real filesystem or a stateful API, and any of them can change between runs, silently invalidating comparisons across model versions or even two runs of the same model. Reproducible agent benchmarks need frozen, sandboxed environments (a pinned Docker image, a scripted mock service) to close that hole. Building one well is the engineering answer, covered in [[Deep Dive - Designing an Eval Harness]]. Ordinary statistical care still applies. Agent scores carry more variance than single-turn scores, so proper confidence intervals and paired comparisons (per [[Concept - Statistical Rigor in Model Evaluation]]) matter more here.

## In practice

Cost and latency are core metrics for agents, where a single-turn eval might treat them as footnotes. An agent that solves a task at 15x the tokens or 10x the wall-clock time of a competitor is, for most deployments, a materially worse product even at the same success rate. [[Concept - Multi-Agent Orchestration]] runs are the sharpest case, since fan-out multiplies both. An agent leaderboard that reports success rate without a cost/latency column answers half the question practitioners have.

Judging trajectories, and not only final answers, usually means putting an LLM in the judge seat. [[Concept - LLM-as-Judge]] biases (position, verbosity, self-preference) get *worse* on long multi-step traces, where the judge has to track state across dozens of tool calls instead of comparing two short completions.

Long trajectories also break failure attribution. When a 30-step run fails at step 30, the real mistake may have happened at step 4: a wrong belief the agent then acted on consistently and "correctly", per [[Concept - Long-Horizon Agency and Error Compounding]]. Scoring the endpoint tells you *that* it failed, not *where*. That makes iterating on an agent much slower than iterating on a single-turn prompt, where the failure is right there in the one output you're reading.

## Failure modes
- **Contamination through task leakage.** Agent benchmark tasks (GitHub issues, web tasks, forum questions) are scraped from the same web that trains the next model generation, per [[Concept - Benchmark Contamination]]. A rising score can mean more capability or more memorization, and after the fact they're hard to tell apart.
- **Reward hacking the metric.** An agent optimized (by RL or iterated prompting) against a benchmark's specific pass condition learns to satisfy the letter of the check instead of doing the task. It's the same dynamic as [[Concept - Reward Hacking]] in RLHF, harder to catch in a trajectory than in a single reward score.
- **Noisy single-run comparisons.** One pass@1 number per model, with no repeated-trial variance estimate, routinely flips model rankings on rerun. Treat any agent leaderboard without confidence intervals or pass^k as provisional.
- **Judge blind spots on long traces.** An LLM judge grading a 40-tool-call trajectory often anchors on surface features (did it call *a* tool, did the final message sound confident) and doesn't verify intermediate correctness.

## The non-obvious

Practitioners keep finding that an agent's benchmark score and its production reliability diverge. The benchmark isn't fraudulent. It measures pass@1 with unlimited retries and no cost ceiling, while production cares about pass^k under a token budget on day one. A model that tops a leaderboard by burning ten retries per task can be strictly worse in deployment than one with a lower headline score and a tighter, more consistent trajectory. METR's time-horizon framing (a capability measure based on task length, see [[Concept - Long-Horizon Agency and Error Compounding]]) tries to get around this by measuring reliable duration instead of best-of-N success. That the field had to invent a whole new family of metrics to make agent scores comparable to production reliability says a lot.

## Connections
- [[Reference - Agent Benchmarks]] — the catalog of specific benchmarks (SWE-bench, tau-bench, GAIA, OSWorld) this note explains the *methodological* difficulty behind.
- [[Concept - Statistical Rigor in Model Evaluation]] — the general statistics (confidence intervals, paired comparisons) agent eval needs even more than single-turn eval, given higher variance.
- [[Deep Dive - Designing an Eval Harness]] — building a reproducible, sandboxed harness is the practical answer to the environment-drift problem.
- [[Concept - LLM-as-Judge]] — the default tool for trajectory grading, and the source of its own bias problems at scale.
- [[Concept - Benchmark Contamination]] — web-scraped agent tasks are especially exposed to training-data leakage.
- [[Concept - Reward Hacking]] — the RL-training analogue of an agent learning to satisfy an eval's letter rather than its spirit.
- [[Concept - Long-Horizon Agency and Error Compounding]] — long trajectories are why attribution and reliability, not just success rate, dominate agent eval design.
- [[Concept - Multi-Agent Orchestration]] — the sharpest case where cost/latency must be reported alongside success rate.
- [[Breakdown - SWE-bench and SWE-agent]] — the rare agent benchmark with a free, objective execution oracle, and a case study in how even that oracle turned out to be flawed.
- [[Lore - The Devin Demo and the SWE-bench Reality Gap]] — the canonical public example of a headline agent number failing to survive scrutiny of its methodology.

## Sources
- Princeton NLP / Jimenez et al. (2023) and OpenAI (2024) — SWE-bench and SWE-bench Verified; the rare agent benchmark with a free, objective oracle, later a case study in why even that oracle needs auditing.
- Sierra Research (2024-2025) — tau-bench / tau2-bench; introduces pass^k as the reliability metric for tool-agent-user tasks.
- METR (2025) — "Measuring AI Ability to Complete Long Tasks"; the time-horizon framing as an alternative to leaderboard percentages.
