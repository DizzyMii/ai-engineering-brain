---
tags: [playbook, domain/evaluation, level/core]
aliases: [eval-driven development, production eval pipeline]
summary: "End-to-end procedure for building an offline-plus-online LLM eval suite that catches product regressions before users do."
---

# Playbook - Building a Production Eval Suite

> **Goal:** replace the "does the model still work" vibe check with a versioned, automatable pipeline that blocks a bad deploy before users see it. **When to run this:** you're standing up eval infrastructure for a shipped or soon-to-ship LLM product, or an existing suite has stopped catching real regressions. **Prerequisites:** real production traffic or logged failures to mine, a CI system that can gate a deploy, and someone with the authority to say "no" when the suite goes red.

## Steps

1. **Mine real production failures and edge cases into a versioned golden set.** Pull logged failures, user complaints and near-misses from production, hand-curate them into a labeled dataset, and check it into version control. Expect a working set of roughly 100–300 well-chosen cases, sliced by segment (user type, task category, failure class). Teams that dump 10,000 auto-scraped, unreviewed transcripts in instead get a suite that's noisy and slow without discriminating any better. A small curated set that spans your real failure modes catches more regressions than a big uncurated one, because every case is there for a reason.

2. **Define per-capability metrics instead of one blended score.** Give each capability the product depends on (task success, output-format/schema compliance, safety, latency, cost) its own metric. A regression in one, say schema compliance dropping after a prompt change, should show up as a visible drop in that metric. A blended score can stay flat while one capability regresses and another improves enough to hide it, and then you hear about the regression from users.

3. **Pick the cheapest sufficient grader per metric, and pin the judge.** Choose the weakest grading method that's still reliable: exact-match/regex for deterministic outputs, code execution for verifiable tasks, an [[Concept - LLM-as-Judge]] with a pinned rubric for open-ended quality, human spot checks for anything safety- or launch-critical. Record the exact judge snapshot (dated version, not "latest") in the suite's config. Every metric should end up with a named grader and, where relevant, a pinned model ID. An LLM judge where exact-match would do adds cost, latency and judge-bias risk for nothing. An unpinned judge means a silent provider-side upgrade can shift every historical score with no changelog entry to explain it.

4. **Wire the suite into CI so a regression blocks deploy.** Run the golden set against every candidate build and make the pipeline fail the build, not log a warning, when a per-capability metric drops below threshold. A deliberately introduced regression on a test branch should fail the check. If CI stays green through a known-bad change, the suite is decorative; go back to step 2 or 3 and work out why the metric didn't move.

5. **Replay sampled production traffic offline, then run online A/B with guardrail metrics.** Before a broad rollout, replay a sample of recent real requests offline against the candidate and compare with the current production build. Then ship to a small online cohort with guardrail metrics (error rate, latency, cost, safety flags) watched in real time. Offline metrics should move the expected way and guardrails should stay in bounds through the rollout. An offline win that doesn't replicate online usually means the golden set has drifted from the real traffic distribution. Refresh it through step 1's mining process instead of trusting the offline number.

## Verification

Put a known-bad prompt or a documented past regression into the golden set and confirm the suite fails on it, end to end, through the same CI gate a real deploy hits. A suite that has never gone red in production hasn't passed anything. It's unverified, and most suites like that are decorative.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| Suite stays green through a change users report as broken | Golden set doesn't cover the failure mode, or the threshold is too loose | Back to step 1; mine the reported failure into the set as a new case |
| Scores drift over time with no code or prompt changes | Judge-model drift: the provider silently updated the backing judge model | Re-pin the judge to a dated snapshot (step 3); re-baseline historical scores against the new pin |
| Suite passes in CI but the model still fails the same way in production | The team shipping the change built or tuned the golden set and has implicitly overfit to it, a [[Concept - Goodhart's Law in Model Evaluation]] instance | Rotate in fresh cases from ongoing production mining; treat a static golden set as decaying evidence, not a permanent oracle |
| LLM-judge scores bounce run to run on identical input | Judge nondeterminism (temperature, sampling) not controlled | Lower judge temperature toward 0, aggregate several judge samples, or switch the metric to a deterministic grader |
| Offline replay looks great, online guardrails fire | Golden set or replay sample no longer matches current production traffic | Refresh the sample from the most recent traffic window before trusting offline numbers again |
| Team can't agree whether a score change is "real" | No confidence interval or paired comparison on the delta | Apply [[Checklist - Trusting a Benchmark Number]] before arguing about a number that may be noise |

## Connections

- [[Deep Dive - Designing an Eval Harness]] — the internals of turning a dataset and a model into a comparable number, which this playbook assumes you can build or reuse rather than re-deriving from scratch.
- [[Concept - LLM-as-Judge]] — the mechanics, modes, and named biases of the grader step 3 reaches for when exact-match or execution won't do.
- [[Concept - Goodhart's Law in Model Evaluation]] — the general mechanism behind the "suite passes, product still fails" failure mode: once your own team optimizes against the golden set, it decouples from real quality.
- [[Concept - LLM Observability and Tracing]] — the production logging and tracing infrastructure (owned by domain 16) that step 1's failure-mining and step 5's traffic replay both depend on.
- [[Concept - Cost Engineering for LLM Applications]] — the cost metric referenced in step 2, and the budget tradeoffs behind choosing cheaper graders in step 3.
- [[Checklist - Trusting a Benchmark Number]] — the pre-flight discipline to apply before declaring any suite-reported delta a real regression rather than noise.
- [[Gotchas - Agents in Production]] — the adjacent pitfall catalogue (owned by domain 10) for suites specifically covering agentic, multi-step LLM products rather than single-turn ones.

## Sources
- Zheng et al. (2023) — Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. The judge methodology step 3's LLM-judge grader is built on, including why pinning matters.
