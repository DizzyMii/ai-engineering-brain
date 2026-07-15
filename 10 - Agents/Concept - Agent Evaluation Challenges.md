---
tags: [concept, domain/agents, level/frontier]
aliases: []
summary: "Why scoring agents is harder than scoring single turns: trajectories, non-determinism, cost, and attribution break single-number scores."
---

# Concept - Agent Evaluation Challenges

> **One-paragraph hook:** A single-turn LLM eval asks "is this one output good"; an agent eval has to ask "was the whole multi-step process good, did it stay good across repeated runs, and was it worth what it cost" — three questions a static benchmark score collapses into one number and quietly lies about.

## The mechanism

Single-turn evaluation scores one generation against a reference or a rubric. Agent evaluation has to score a *trajectory* — a sequence of tool calls, observations, and intermediate reasoning that can run for dozens of steps — and the naive approach of grading only the final state throws away most of the signal. Two agents can reach the same correct answer through very different paths: one used the minimum necessary tool calls and verified its own work, the other got there by brute-force retrying every plausible action until something stuck. Outcome-only scoring rates them identically; a full eval has to separately judge outcome (did it succeed) and process (was the path efficient, safe, non-lucky) — the outlier case is [[Breakdown - SWE-bench and SWE-agent]], which gets a free, objective outcome oracle from hidden tests that most agent domains simply don't have.

Compounding this, agent runs are non-deterministic: temperature, tool-call ordering, and environment timing mean the *same* task run twice by the same agent can succeed once and fail once. A single-seed pass/fail score is close to noise for any task with real variance, which is why benchmarks like tau-bench and tau2-bench report pass^k — the probability of succeeding k independent times in a row — rather than pass@1. pass^k drops fast even for agents with a respectable pass@1: an agent succeeding 80% of individual runs only clears pass^4 (four-for-four) about $0.8^4 \approx 41\%$ of the time, and reliability, not raw capability, is what production actually needs.

Environment drift is the third structural problem. A single-turn eval reads from a frozen dataset; an agent eval often has the agent touch a live website, a real filesystem, or a stateful API — any of which can change between runs, silently invalidating comparisons across model versions or even across two runs of the same model. Reproducible agent benchmarks require frozen, sandboxed environments (a pinned Docker image, a scripted mock service) specifically to close this hole — building one well is the concrete engineering answer, covered in [[Deep Dive - Designing an Eval Harness]]. None of this obviates ordinary statistical care either: because agent scores carry more variance than single-turn scores, proper confidence intervals and paired comparisons (per [[Concept - Statistical Rigor in Model Evaluation]]) matter more here, not less.

## In practice

Cost and latency are load-bearing metrics here, not footnotes the way they might be for a single-turn eval. An agent that resolves a task at 15x the tokens or 10x the wall-clock time of a competitor is, for most deployments, a materially worse product even at equal success rate — [[Concept - Multi-Agent Orchestration]] runs are the sharpest example, where fan-out multiplies both. Any agent leaderboard that reports success rate alone without a cost/latency column is answering half the question practitioners actually have.

Judging trajectories at all, rather than just final answers, usually means putting an LLM in the judge seat — and [[Concept - LLM-as-Judge]] biases (position, verbosity, self-preference) get *worse* over long multi-step traces, where the judge has to track state across dozens of tool calls rather than compare two short completions.

Long trajectories also break failure attribution. When a 30-step run fails at step 30, the actual mistake might have been made at step 4 — a wrong belief the agent then acted on consistently and "correctly" given that belief, per [[Concept - Long-Horizon Agency and Error Compounding]]. Scoring only the endpoint tells you *that* it failed, not *where*, which makes iterating on the agent much slower than iterating on a single-turn prompt where the failure is visible in the one output you're looking at.

## Failure modes
- **Contamination via task leakage:** agent benchmark tasks (GitHub issues, web tasks, forum questions) are scraped from the same web that trains the next model generation, per [[Concept - Benchmark Contamination]] — a rising score can mean rising capability or rising memorization, and the two are hard to tell apart after the fact.
- **Reward hacking the metric:** an agent optimized (via RL or iterated prompting) against a benchmark's specific pass condition learns to satisfy the letter of the check rather than the task — the same dynamic as [[Concept - Reward Hacking]] in RLHF, but harder to catch in a trajectory than in a single reward score.
- **Noisy single-run comparisons:** reporting one pass@1 number per model, with no repeated-trial variance estimate, routinely reverses model rankings on rerun — treat any agent leaderboard without confidence intervals or pass^k as provisional.
- **Judge blind spots on long traces:** an LLM judge asked to grade a 40-tool-call trajectory frequently anchors on surface features (did it call *a* tool, did the final message sound confident) rather than verifying intermediate correctness.

## The non-obvious

Practitioners consistently discover that an agent's benchmark score and its production reliability diverge — not because the benchmark is fraudulent, but because benchmarks measure pass@1-with-unlimited-retries-and-no-cost-ceiling, while production cares about pass^k-under-a-token-budget-on-day-one. A model that tops a leaderboard by burning ten retries per task can be strictly worse in deployment than a model with a lower headline score but a tighter, more consistent trajectory. The METR time-horizon framing (a task-length-based capability measure, see [[Concept - Long-Horizon Agency and Error Compounding]]) is an attempt to sidestep this by measuring reliable duration rather than best-of-N success — and it is telling that the field needed to invent a whole new metric family just to make agent scores mean something comparable to production reliability.

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
