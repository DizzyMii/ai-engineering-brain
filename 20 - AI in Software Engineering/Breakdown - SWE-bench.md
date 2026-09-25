---
tags: [breakdown, domain/applied-software, level/advanced]
aliases: [SWE-bench, SWE-bench Verified, SWE-bench Pro, SWE-bench Lite]
summary: "The defining agentic-coding benchmark: real GitHub issues graded by hidden tests — why its 2026 scores are the best proxy, still misleading."
---

# Breakdown - SWE-bench

> SWE-bench (Jimenez et al., Princeton, 2023) is the benchmark that came to define "can an AI agent do software engineering." A model is graded on whether its patch resolves a real GitHub issue and passes the repository's hidden tests. Almost every headline agentic-coding claim from 2024–2026 is a SWE-bench number, from Devin's launch to every "our model scores X% on SWE-bench." Read those numbers wrong and you make a fooled deployment decision. Date-stamped: as of mid-2026 OpenAI had effectively retired the flagship variant over contamination.

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

Two rows matter. The 2023→2026 climb from 1.96% to ~80% looks like solved software engineering, and it isn't. The Verified→Pro drop of 20–50 points on the *same models* is the number that tells the truth.

## How it works

The construction is the honest core of the design:

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

Ground truth is *execution of the human-written tests that came with the real fix*. There's no LLM judge and no string match. That's how SWE-bench became the standard, and why it belongs in any [[Deep Dive - Designing an Eval Harness]] discussion: a hidden, executable oracle is the gold standard, and most benchmarks lack one. It's also the concrete case of the [[Concept - AI in Software Testing]] idea that a correct test *is* the specification.

## The clever parts

- **Execution-graded, real issues.** No rubric, no judge model. The repo's own regression tests decide, which resists the gaming common in [[Concept - LLM-as-Judge]] evals and gives a passing patch a concrete meaning.
- **Verified paid down the noise floor.** For SWE-bench Verified (Aug 2024, 500 tasks), OpenAI had human engineers filter out underspecified issues and broken or over-strict tests from the original set. It was a real improvement in signal, and it's why "Verified" became the quoted number.
- **The scaffold is part of the score.** The same model scores wildly differently under different agent harnesses: retrieval strategy, turn budget, whether it can run tests, the prompt. A "SWE-bench score" belongs to a **model + scaffold + prompt** tuple, not to the model. So [[Deep Dive - Agentic Coding in Production]] treats the scaffold as a primary design concern, and cross-vendor leaderboard comparisons are frequently apples-to-oranges.

## What it got wrong / what's dated

SWE-bench is the best public proxy and, read as an absolute number, actively misleading.

- **The Devin score inflation (2024).** Cognition's March 2024 launch quoted 13.86%, ~7x the prior public SOTA, plus a viral Upwork demo of Devin completing a paid job. Carl Brown's "Debunking Devin" (April 2024) showed the figure came from a non-standard subset and the demo was oversold. It's the standard [[Concept - The Capability-Reliability Gap]] cautionary tale and a fixture of [[Lore - AI Coding War Stories]]. Treat any launch-day benchmark number as an upper bound produced under ideal conditions.
- **Contamination is now the dominant confound.** The tasks come from public GitHub history that predates training cutoffs, so models may have *seen the fix*. In Feb 2026 OpenAI reported frontier models could reproduce gold-patch solutions from the task ID alone, a fingerprint of training-data leakage. Independent work found ~32% of successful Verified patches involved solution leakage, with correct file-path recall up to ~76% of the time. [[Concept - Benchmark Contamination]] doesn't get purer than this.
- **The tests are flawed too.** OpenAI (Feb 23, 2026) stopped evaluating on Verified after auditing a ~27.6% subset (~138 of the 500, drawn from frequently-failed tasks). **≥59.4% had flawed test cases**: ~35.5% too strict, rejecting functionally correct patches by enforcing implementation details, and ~18.8% too loose, checking behavior the issue never specified. It moved to **SWE-bench Pro** while acknowledging Pro is imperfect too (E1, no clean independent audit of Pro's task quality as of mid-2026). No benchmark here is clean.
- **The format leaves out most real work.** Python bug-fixes with a known failing test exclude code review, security, ambiguous requirements, private stacks, cross-service effects and greenfield design, which is most of the job. The Verified→Pro collapse to ~23–58% is [[Concept - The Evaluation Gap]] put in numbers. It matches the [[Breakdown - The METR Developer Slowdown RCT]] finding that benchmark competence doesn't equal real-repo productivity.

## What to steal

- **Compare score deltas under a fixed scaffold, never absolute percentages.** The number belongs to a model+scaffold+prompt tuple and the dataset is contaminated. The only defensible internal use is comparing models *under identical harnesses* and ignoring the absolute value. The [[Reference - Developer Productivity Studies]] catalog applies the same discipline to every study.
- **Never quote a Verified % as "% of real engineering work."** It's the most common misuse. An 80% Verified model is not 80% of an engineer. The [[Concept - AI Coding Assistants]] framing and the [[Concept - METR Time Horizons]] measurement both exist because benchmark peaks overstate deployed reliability.
- **Build your own held-out, post-cutoff, execution-graded eval.** Take SWE-bench's oracle (hidden real tests) and apply it to *your* private codebase, which is contamination-free and representative, instead of trusting a public leaderboard. The [[Concept - AI's Effect on Code Quality and Security]] worry about tests that freeze buggy behavior applies here as well. A benchmark is only as honest as its tests, and SWE-bench's own tests were 59% flawed.

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
