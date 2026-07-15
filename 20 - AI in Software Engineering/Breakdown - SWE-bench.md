---
tags: [breakdown, domain/applied-software, level/advanced]
aliases: [SWE-bench, SWE-bench Verified, SWE-bench Pro, SWE-bench Lite]
summary: "The defining agentic-coding benchmark: real GitHub issues graded by hidden tests — why its 2026 scores are the best proxy, still misleading."
---

# Breakdown - SWE-bench

> SWE-bench (Jimenez et al., Princeton, 2023) is the benchmark that came to define "can an AI agent do software engineering." It grades a model on whether it can produce a patch that resolves a real GitHub issue and passes the repository's hidden tests. It matters because almost every headline agentic-coding claim from 2024–2026 — Devin's launch, every "our model scores X% on SWE-bench" — is a SWE-bench number, and reading those numbers correctly is the difference between a sound and a fooled deployment decision. Date-stamped: as of mid-2026 the benchmark's flagship variant was effectively retired by OpenAI over contamination.

## The headline numbers

| Fact | Value | Tier |
|---|---|---|
| Original dataset | 2,294 issue+PR pairs from 12 popular Python repos | E3 (paper) |
| Grading | model patch must make repo's **Fail-to-Pass** tests pass | E3 |
| Best model at release (2023) | Claude 2 — **1.96%** resolved | E3 |
| Devin launch claim (Mar 2024) | **13.86%** (on a subset) — ~7x prior SOTA | E2 (Cognition's own) |
| SWE-bench Verified | **500** human-validated tasks (OpenAI, Aug 2024) | E3 |
| Frontier agents on Verified (2026) | ~70–80%+ | E2 |
| Same models on SWE-bench Pro (2026) | ~23–58% | E2 |
| OpenAI audit (Feb 2026) | ≥**59.4%** of a hard subset had flawed tests; Verified retired | E2 (OpenAI's own) |

The two rows that matter: the 2023→2026 climb from 1.96% to ~80% looks like solved software engineering, and it is not. The Verified→Pro drop of 20–50 points on the *same models* is the number that tells the truth.

## How it actually works

Construction is the clever, honest core of the design:

```
Mine 12 popular Python repos (django, sympy, scikit-learn, flask, ...)
  For each merged Pull Request:
    Keep it IFF:
      - it is linked to a GitHub Issue (the "task": natural-language problem)
      - it modifies >=1 test file
    Extract:
      - the issue text            -> given to the model as the prompt
      - the repo state BEFORE the PR -> the model's working tree
      - the tests the PR added/changed -> HIDDEN grader
Grade a model's patch by EXECUTION, not similarity:
  FAIL_TO_PASS: tests that failed before the PR and pass after -> must now pass
  PASS_TO_PASS: tests that passed before -> must still pass (no regressions)
Resolved = every FAIL_TO_PASS and PASS_TO_PASS test passes.
```

The elegance is that the ground truth is *execution of the human-written tests that accompanied the real fix* — no LLM judge, no string match. That is why SWE-bench became the standard and why it belongs in any [[Deep Dive - Designing an Eval Harness]] discussion: a hidden, executable oracle is the gold standard, and most benchmarks don't have one. It is the concrete instance of the [[Concept - AI in Software Testing]] insight that a correct test *is* the specification.

## The clever parts

- **Execution-graded, real issues.** No rubric, no judge model — the repo's own regression tests decide. This resists the gaming that plagues [[Concept - LLM-as-Judge]] evals and makes a passing patch mean something concrete.
- **Verified: paying down the noise floor.** OpenAI's SWE-bench Verified (Aug 2024, 500 tasks) had human engineers filter out underspecified issues and broken/over-strict tests from the original set — a real improvement that made the benchmark a cleaner signal, and the reason "Verified" became the quoted number.
- **The scaffold is part of the score.** The same model scores wildly differently under different agent harnesses (retrieval strategy, how many turns, whether it can run tests, prompt). A "SWE-bench score" is a **model + scaffold + prompt** tuple, not a property of the model. This is why [[Deep Dive - Agentic Coding in Production]] treats the scaffold as first-class, and why cross-vendor leaderboard comparisons are frequently apples-to-oranges.

## What it got wrong / what's dated

This is where the note earns its keep — SWE-bench is simultaneously the best public proxy and actively misleading as an absolute number.

- **The Devin score-inflation episode (2024).** Cognition's March 2024 launch quoted 13.86%, ~7x the prior public SOTA, and a viral Upwork demo of Devin completing a paid job. Carl Brown's "Debunking Devin" (April 2024) showed the benchmark figure was on a non-standard subset and the demo was oversold — the canonical [[Concept - The Capability-Reliability Gap]] cautionary tale, and a fixture of [[Lore - AI Coding War Stories]]. Treat any launch-day benchmark number as an upper bound produced under ideal conditions.
- **Contamination is now the dominant confound.** The tasks come from public GitHub predating model training cutoffs, so models may have *seen the fix*. In Feb 2026 OpenAI reported frontier models could reproduce gold-patch solutions from the task ID alone — a fingerprint of training-data leakage — and independent work found ~32% of successful Verified patches involved solution leakage and correct file-path recall up to ~76% of the time. This is [[Concept - Benchmark Contamination]] in its purest form.
- **Even the tests are flawed.** OpenAI (Feb 23, 2026) stopped evaluating on Verified after auditing a ~27.6% subset (~138 of the 500, drawn from frequently-failed tasks) and finding **≥59.4% had flawed test cases**: ~35.5% too strict (rejecting functionally correct patches by enforcing implementation details) and ~18.8% too loose (checking behavior the issue never specified). It shifted to **SWE-bench Pro** — while itself acknowledging Pro is also imperfect (E1, no clean independent audit of Pro's task quality as of mid-2026). No benchmark here is clean.
- **The format omits most real work.** Python bug-fix with a known failing test excludes code review, security, ambiguous requirements, private stacks, cross-service effects, and greenfield design — i.e., most of the job. The Verified→Pro collapse to ~23–58% is the quantified [[Concept - The Evaluation Gap]], and it mirrors the [[Breakdown - The METR Developer Slowdown RCT]] finding that benchmark competence doesn't equal real-repo productivity.

## What to steal

- **Score deltas under a fixed scaffold, never absolute percentages.** Because the number is a model+scaffold+prompt tuple and the dataset is contaminated, the only defensible internal use is comparing models *under identical harnesses* and treating the absolute value as meaningless. This is the reading discipline the [[Reference - Developer Productivity Studies]] catalog applies to every study.
- **Never quote a Verified % as "% of real engineering work."** It is the single most common misuse. An 80% Verified model is not 80% of an engineer; the [[Concept - AI Coding Assistants]] framing and the [[Concept - METR Time Horizons]] measurement both exist because benchmark peaks overstate deployed reliability.
- **Build your own held-out, post-cutoff, execution-graded eval.** The transferable design pattern is SWE-bench's oracle (hidden real tests) applied to *your* private codebase — contamination-free and representative — rather than a public leaderboard. This is where the [[Concept - AI's Effect on Code Quality and Security]] concern about tests that freeze buggy behavior also bites: a benchmark is only as honest as its tests, and SWE-bench's own tests were 59% flawed.

## Connections

- [[Concept - The Capability-Reliability Gap]] — SWE-bench scores are capability peaks; the Verified→Pro drop is the reliability shortfall made numeric.
- [[Deep Dive - Agentic Coding in Production]] — production agents are scored on SWE-bench; the scaffold-is-the-score point is operationally central there.
- [[Concept - The Evaluation Gap]] — the benchmark-vs-reality collapse is the canonical example.
- [[Reference - Developer Productivity Studies]] — SWE-bench is the agentic-eval row in the broader evidence catalog.
- [[Concept - AI's Effect on Code Quality and Security]] — flawed graders and tests-freeze-behavior link the benchmark's failure to the code-quality failure mode.
- [[Breakdown - The METR Developer Slowdown RCT]] — benchmark competence ≠ real-repo productivity; the two notes bracket the hype.
- [[Concept - AI in Software Testing]] — SWE-bench's oracle is the "correct test is the spec" idea in benchmark form.
- [[Concept - AI Coding Assistants]] — the tools whose marketing quotes these scores.
- [[Concept - METR Time Horizons]] — an alternative, contamination-resistant way to track agent capability over time.
- [[Lore - AI Coding War Stories]] — Devin's oversold launch is the founding war story.
- [[Concept - Benchmark Contamination]] — the general mechanism behind the 2026 Verified retirement.
- [[Deep Dive - Designing an Eval Harness]] — SWE-bench is the reference design (and cautionary tale) for execution-graded evals.

## Sources
- Jimenez, Yang, Wettig, Yao, Pei, Press, Narasimhan (Princeton), 2023 — "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?", arXiv:2310.06770. Dataset construction and the 1.96% Claude 2 baseline (E3).
- OpenAI, Aug 2024 — SWE-bench Verified (500 human-validated tasks) and the containerized harness (E3).
- Cognition, Mar 2024 — Devin launch claiming 13.86% (E2); Carl Brown, "Debunking Devin", Apr 2024 — independent debunk (E2).
- OpenAI Frontier Evals, Feb 2026 — "Why we no longer evaluate SWE-bench Verified": ≥59.4% flawed tests in the audited subset, contamination fingerprints, shift to SWE-bench Pro (E2, OpenAI's own).
