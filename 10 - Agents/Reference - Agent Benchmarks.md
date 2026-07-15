---
tags: [reference, domain/agents, level/advanced]
aliases: [agent eval benchmarks, LLM agent benchmark landscape]
summary: "Lookup matrix of agent capability benchmarks — coding, web, general-assistant, tool-use, computer-use — with metrics and approximate SOTA as of 2026."
---
# Reference - Agent Benchmarks

Scores below move quarterly and many task sources predate model training cutoffs, so treat every number as *(as of 2026)* and re-verify before quoting. See [[Concept - Benchmark Contamination]] for why contamination is close to unavoidable in this category, [[Concept - Agent Evaluation Challenges]] for the deeper reasons agent numbers are harder to trust than single-turn benchmark scores, and [[Deep Dive - Designing an Eval Harness]] for how to build the infrastructure these benchmarks assume you already have.

## Coding

| Benchmark | Task count | Metric | Approx. top score | Notes |
|---|---|---|---|---|
| SWE-bench | 2,294 real GitHub issue+PR pairs, 12 Python repos | % resolved (hidden tests pass) | ~2% (2023 retrieval baseline) → 60–70%+ on Verified (2026) | Construction and the Agent-Computer Interface breakthrough covered in [[Breakdown - SWE-bench and SWE-agent]] |
| SWE-bench Verified | 500, human-filtered subset | % resolved | 60–70%+ (2026) | OpenAI-curated (2024) to remove under-specified/broken tasks |
| SWE-bench Multimodal | Subset with visual bug reports | % resolved | Lower than text-only Verified | Adds screenshots to the issue description |

## Web / browsing

| Benchmark | What it tests | Metric | Notes |
|---|---|---|---|
| WebArena | Realistic tasks across 5 self-hosted site categories | Task success rate | DOM-based, no visual grounding required |
| VisualWebArena | WebArena + visual grounding | Task success rate | Adds screenshots as the primary observation |
| WebVoyager | Real, live production websites | Task success rate | Non-sandboxed — higher variance, environment drifts under you |
| BrowseComp | Hard retrieval-style browsing/search (OpenAI, 2025) | Accuracy | Deliberately designed to resist answer-memorization |

## General assistant

| Benchmark | What it tests | Metric | Notes |
|---|---|---|---|
| GAIA | Real multi-step tasks, 3 difficulty tiers (Meta, 2023) | % solved | Humans ~92% vs. early GPT-4-class agents ~15% at launch; gap narrowed sharply through 2025–26 |
| AgentBench | Multi-environment (OS, DB, web, games, more) | Aggregate score across environments | Breadth over depth — weak signal on any single environment |

## Tool-agent-user

| Benchmark | What it tests | Metric | Notes |
|---|---|---|---|
| tau-bench / tau2-bench | Retail/airline agent with a simulated user in the loop | pass^k (succeeds k independent times) | pass^k drops sharply relative to pass@1 — measures reliability, not one-shot capability |

## Computer use

| Benchmark | What it tests | Metric | Notes |
|---|---|---|---|
| OSWorld | Real desktop tasks across real applications and OS | Task success rate | [[Concept - Computer Use and GUI Grounding|Claude Computer Use]] scored roughly mid-teens vs. ~72% human (late 2024); improved through 2025–26 but still well below human reliability |
| ScreenSpot | Pixel-to-coordinate grounding accuracy | Grounding accuracy | Isolated grounding metric — doesn't capture full-task success |

## Specialized

| Benchmark | Domain | Metric |
|---|---|---|
| MLE-bench | ML engineering, Kaggle-style competitions | Medal-rate / leaderboard score |
| Cybench | Security / CTF-style tasks | % solved |
| Terminal-Bench | Terminal / shell-driven tasks | % solved |

An alternative capability framing that sidesteps fixed-task-suite saturation entirely is [[Concept - METR Time Horizons]], which measures the length of task an agent can complete autonomously at 50% success rather than a pass rate on a static suite — useful when the tables above start clustering near ceiling.

## Metric definitions

| Metric | Meaning |
|---|---|
| pass@1 | Succeeds on one independent attempt |
| pass^k | Succeeds all k times across k independent attempts — a reliability metric, not a capability ceiling |
| resolved-rate | % of tasks where an automated hidden-test oracle passes (SWE-bench family) |

pass@1, pass^k, and resolved-rate are **not comparable across benchmarks** — a 70% resolved-rate on SWE-bench Verified and a 70% pass@1 on GAIA measure structurally different things (unit-test ground truth vs. a scored/judged answer). Always footnote which metric a headline number uses before citing it, and don't take a single-run headline score at face value without the [[Concept - Statistical Rigor in Model Evaluation|variance/significance discipline]] applied to any other benchmark number. [[Concept - LLM-as-Judge|LLM-judged]] scoring (parts of GAIA and AgentBench) additionally inherits judge bias on top of run-to-run variance.

## Connections

- [[Concept - Agent Evaluation Challenges]] — the structural reasons (non-determinism, trajectory attribution, cost-as-metric) these benchmarks are harder to trust than single-turn evals.
- [[Breakdown - SWE-bench and SWE-agent]] — the full construction and history behind the SWE-bench row.
- [[Deep Dive - Designing an Eval Harness]] — how to build the harness infrastructure these benchmarks assume.
- [[Concept - Statistical Rigor in Model Evaluation]] — the variance/significance discipline missing from most headline agent-benchmark numbers.
- [[Concept - Benchmark Contamination]] — why many of these task sources leak into training data and inflate scores.
- [[Concept - Computer Use and GUI Grounding]] — the mechanism behind the OSWorld/ScreenSpot rows.
- [[Concept - LLM-as-Judge]] — the scoring mechanism behind GAIA/AgentBench's non-unit-test tasks, and its biases.
- [[Concept - METR Time Horizons]] — the time-horizon reframing of agent capability that this table's fixed task suites will eventually saturate against.

## Sources

- Jimenez, C. et al. (2023) — "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?" Original benchmark construction.
- Mialon, G. et al. (2023) — "GAIA: A Benchmark for General AI Assistants" (Meta). The three-tier difficulty design and human-vs-agent baseline.
- Yao, S. et al. (2024) — "tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains." Source of the pass^k reliability metric.
- Xie, T. et al. (2024) — "OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments."
