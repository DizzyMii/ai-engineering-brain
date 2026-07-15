---
tags: [playbook, domain/evaluation, level/core]
aliases: [eval-driven development, production eval pipeline]
summary: "End-to-end procedure for building an offline-plus-online LLM eval suite that catches product regressions before users do."
---

# Playbook - Building a Production Eval Suite

> **Goal:** turn "does the model still work" from a vibe check into a versioned, automatable pipeline that blocks a bad deploy before it reaches users. **When to run this:** standing up eval infrastructure for a shipped or soon-to-ship LLM product, or when an existing suite has stopped catching real regressions. **Prerequisites:** a stream of real production traffic or logged failures to mine from, a CI system that can gate a deploy, and someone with authority to say "no" when the suite goes red.

## Steps

1. **Mine real production failures and edge cases into a versioned golden set.** Action: pull logged failures, user complaints, and near-misses from production, and hand-curate them into a labeled dataset checked into version control. Expected observation: a working set in the range of roughly 100–300 well-chosen, segment-sliced cases (by user type, task category, or failure class). What deviation means: teams that instead dump 10,000 auto-scraped, unreviewed transcripts into the set get a suite that's noisy and slow without being more discriminating — a small curated set that actually spans your real failure modes catches more regressions than a large uncurated one, because every case in it was chosen for a reason.

2. **Define per-capability metrics instead of one blended score.** Action: for each capability the product depends on (task success, output-format/schema compliance, safety, latency, cost), define a separate metric rather than averaging everything into a single "quality" number. Expected observation: a regression in one capability (e.g., schema compliance drops after a prompt change) shows up as a visible drop in its own metric. What deviation means: a single blended score can stay flat while one capability quietly regresses and another improves to compensate — you find out about the regression from users, not from the suite.

3. **Pick the cheapest sufficient grader per metric, and pin the judge.** Action: for each metric, choose the weakest grading method that's still reliable — exact-match/regex for deterministic outputs, code execution for verifiable tasks, an [[Concept - LLM-as-Judge]] with a pinned rubric for open-ended quality, human spot-check for anything safety- or launch-critical — and record the exact judge model snapshot (dated version, not "latest") in the suite's config. Expected observation: every metric has a named grader and, where relevant, a pinned model ID. What deviation means: using an LLM judge where exact-match would do adds cost, latency, and judge-bias risk for no benefit; leaving the judge model unpinned means a silent provider-side model upgrade can shift every historical score with no changelog entry to explain why.

4. **Wire the suite into CI so a regression blocks deploy.** Action: run the golden set against every candidate build in CI, and configure the pipeline to fail the build (not just log a warning) when a per-capability metric drops below its threshold. Expected observation: a deliberately-introduced regression in a test branch fails the CI check. What deviation means: if CI stays green through a known-bad change, the suite is decorative — go back to step 2 or 3 and find why the metric didn't move.

5. **Replay sampled production traffic offline, then run online A/B with guardrail metrics.** Action: before shipping a change broadly, replay a sample of real recent production requests offline against the candidate build and compare metrics to the current production build; then ship to a small online cohort with explicit guardrail metrics (error rate, latency, cost, safety flags) monitored in real time. Expected observation: offline replay metrics move in the expected direction, and the online guardrails stay within bounds through the rollout. What deviation means: an offline win that doesn't replicate online usually means the golden set has drifted from real traffic distribution — refresh it from step 1's mining process rather than trusting the offline number blindly.

## Verification

Inject a known-bad prompt or a documented past regression into the golden set and confirm the suite actually fails on it, end to end, through the same CI gate a real deploy would hit. An eval suite that has never once gone red in production is not passing — it is unverified, and most suites that fit that description are decorative rather than working.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| Suite stays green through a change users report as broken | Golden set doesn't cover the failure mode, or the metric threshold is set too loosely | Return to step 1; mine the specific user-reported failure into the set as a new case |
| Scores drift over time with no code or prompt changes | Judge-model version drift — a provider silently updated the backing judge model | Re-pin the judge to a dated snapshot (step 3); re-baseline historical scores against the new pin |
| Suite passes in CI but the model still fails the same way in production | The golden set was built or tuned by the same team shipping the change, and has been implicitly overfit to — a [[Concept - Goodhart's Law in Model Evaluation]] instance | Rotate in fresh cases from ongoing production mining; treat a static golden set as decaying evidence, not a permanent oracle |
| LLM-judge scores bounce run to run on the identical input | Judge nondeterminism (temperature, sampling) not controlled for | Lower judge temperature toward 0, run multiple judge samples and aggregate, or switch the metric to a deterministic grader |
| Offline replay looks great, online guardrails fire | Golden set or replay sample no longer represents current production traffic distribution | Refresh the sample from the most recent traffic window before trusting offline numbers again |
| Team can't agree whether a score change is "real" | No confidence interval or paired comparison was run on the delta | Apply the discipline in [[Checklist - Trusting a Benchmark Number]] before arguing about a number that may be noise |

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
