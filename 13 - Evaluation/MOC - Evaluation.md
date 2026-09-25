---
tags: [moc, domain/evaluation, level/surface]
aliases: []
summary: "Map of Evaluation: benchmark design, scoring mechanics, LLM-as-judge, contamination, and the statistics that separate a real gap from noise."
---

# MOC - Evaluation

This domain covers how a model's behavior becomes a number you can trust: benchmark taxonomy and scoring mechanics, LLM-as-judge and human evaluation, contamination and how to detect it, and the statistical tests that separate a real capability gap from noise. Every other domain in the vault reports its results through an eval (post-training's reward signals, fine-tuning's before/after comparisons, agent benchmarks, safety red-teaming), and a broken eval silently corrupts every decision made on top of it. Goodhart's Law runs through all of these notes: once a benchmark becomes a target, contamination, format sensitivity, judge bias and leaderboard gaming start eating the signal it was built to measure. The question here is: *given a claim that model A beats model B, what has to be true (decontaminated data, enough eval items, a validated judge, a real effect size) for the claim to hold?*

## Start here

- **Surface** → [[Concept - Benchmark Taxonomy]]: the two independent axes (capability measured, scoring method) every other note here assumes.
- **Core** → [[Concept - LLM-as-Judge]]: the dominant 2026 scoring technique for open-ended output. Fast and cheap, with named biases you have to correct for.
- **Advanced** → [[Deep Dive - Designing an Eval Harness]]: how a harness turns a dataset and a model into a comparable score, and why the same benchmark gives different numbers across harnesses.
- **Frontier** → [[Concept - Private and Dynamic Benchmarks]]: the research response to contamination, meaning private holdouts, date-windowing, procedural generation and adversarial-in-the-loop eval.
- **Unicorn** → [[Lore - Benchmark Scandals]]: benchmark numbers that turned out to be marketing. Read it before trusting another headline score.

## Foundations: what evaluation is and why it breaks

- [[Concept - Benchmark Taxonomy]]: benchmarks vary on two independent axes, the capability tested and how it's scored, and the scoring axis is the one that governs reproducibility.
- [[Concept - Goodhart's Law in Model Evaluation]]: any benchmark you optimize toward stops measuring the capability it stood in for. It's the root cause of contamination, leaderboard hacking and reward hacking alike.
- [[Concept - Capability versus Propensity]]: what a model can do under maximal elicitation versus what it does by default. Mixing them up is how "the model can't do X" claims get falsified by a better prompt.

## Scoring mechanics: how a benchmark becomes a number

- [[Breakdown - MMLU]]: the 57-subject MCQ benchmark that became the headline number, saturated, and then turned out to carry roughly 6.5% label errors.
- [[Concept - Answer Scoring and Normalization]]: log-likelihood versus generation scoring, and the acc/acc_norm/PMI normalization choices that silently decide which model gets called SOTA.
- [[Concept - Multiple-Choice Symbol Binding and Position Bias]]: MCQ scores are confounded by which letter or position holds the right answer, independent of content, and letter scoring understates real knowledge.
- [[Concept - Prompt Format Sensitivity in Evaluation]]: semantically equivalent formatting changes swing scores by many points and can flip model rankings outright.
- [[Concept - Pass@k and Sampling-Based Evaluation]]: the unbiased estimator for "at least one of k samples passes," and why quoting it against a rival's pass@1 inflates a launch chart.

## Contamination and benchmark integrity

- [[Concept - Benchmark Contamination]]: test data or near-duplicates leaking into training corpora inflates scores with no real capability gain, and perfect decontamination is impossible at web scale.
- [[Concept - Membership Inference for Contamination Detection]]: black-box methods for detecting whether text was in training data, and why most barely beat random once distribution shift is controlled.
- [[Concept - Private and Dynamic Benchmarks]]: contamination resistance through private holdouts, date-windowing, procedural generation and adversarial-in-the-loop evaluation.

## Judges: LLM-as-judge and human evaluation

- [[Concept - LLM-as-Judge]]: a strong LLM scores or ranks outputs in place of humans. Fast and cheap, with named, measurable biases you have to correct for.
- [[Gotchas - LLM-as-Judge Evaluations]]: the failures that corrupt judge scores, ordered by pain: position bias, length bias, self-preference, injection, drift.
- [[Concept - Meta-Evaluation of LLM Judges]]: how to check that a judge agrees with ground truth, and why the check has to repeat as optimization pressure against the judge builds.
- [[Concept - Human Evaluation Methodology]]: designing human eval studies (rater selection, inter-rater agreement, comparative versus absolute scoring) so the numbers are reliable.
- [[Breakdown - Chatbot Arena]]: how anonymous pairwise human votes become a Bradley-Terry leaderboard, plus the length/style confounds and the 2025 governance dispute.

## Statistical rigor and model comparison

- [[Concept - Statistical Rigor in Model Evaluation]]: a benchmark score is a random variable with a confidence interval, and most reported model-vs-model gaps sit inside the noise.
- [[Snippet - Paired Bootstrap for Model Comparison]]: runnable paired bootstrap and McNemar's test code for deciding whether one model beats another on the same items.

## Building and trusting eval infrastructure

- [[Deep Dive - Designing an Eval Harness]]: how a harness turns a dataset and a model into a comparable score, and why one benchmark gives different numbers across harnesses.
- [[Gotchas - Benchmark Harness Pitfalls]]: the implementation traps (chat templates, acc_norm, few-shot formatting, tokenizer quirks) that make one model score differently across harnesses.
- [[Playbook - Building a Production Eval Suite]]: end-to-end procedure for an offline-plus-online LLM eval suite that catches product regressions before users do.
- [[Decision - Choosing an Evaluation Method]]: choosing between execution-based, exact-match, LLM-judge, human eval and online A/B for a given question.
- [[Checklist - Trusting a Benchmark Number]]: checks to run before believing a leaderboard cell, a paper's headline score or a vendor launch chart.
- [[Reference - LLM Benchmark Landscape]]: comparison matrix of major LLM benchmarks with capability, format, size, baselines, 2026 saturation status and headline flaws.

## Folklore

- [[Lore - Benchmark Scandals]]: war stories where benchmark numbers turned out to be marketing: fraud, overfitting, harness discrepancies, length gaming, cherry-picking.

## Adjacent domains

- [[MOC - Post-Training]]: reward hacking and RLVR verifiers are Goodhart's law inside training itself, and the methods here are what make a verifier trustworthy.
- [[MOC - Agents]]: agent evaluation inherits every problem in this domain (contamination, judge bias, statistical noise) and adds trajectories and non-determinism.
- [[MOC - Safety & Interpretability]]: red-teaming and jailbreak benchmarks apply this domain's methods to an adversarial capability instead of a cooperative one.
- [[MOC - AI in Software Engineering]]: SWE-bench and coding-agent benchmarks are this domain's harness-design and contamination problems at their highest stakes.
