---
tags: [moc, domain/evaluation, level/surface]
aliases: []
summary: "Map of Evaluation: benchmark design, scoring mechanics, LLM-as-judge, contamination, and the statistics that separate a real gap from noise."
---

# MOC - Evaluation

This domain owns the machinery for turning a model's behavior into a trustworthy number: benchmark taxonomy and scoring mechanics, LLM-as-judge and human evaluation, contamination and its detection, and the statistical tests that separate a real capability gap from noise. It matters because every other domain in this vault — post-training's reward signals, fine-tuning's before/after comparisons, agent benchmarks, safety red-teaming — ultimately reports its results through an eval, and a broken eval silently corrupts every decision built on top of it. The thread running through these notes is Goodhart's Law: the moment a benchmark becomes a target, contamination, format sensitivity, judge bias, and leaderboard gaming start eating the signal it was built to measure. The question this domain answers: *given a claim that model A beats model B, what would have to be true — decontaminated data, enough eval items, a validated judge, a real effect size — for that claim to actually hold?*

## Start here

- **Surface** → [[Concept - Benchmark Taxonomy]] — the two independent axes (capability measured, scoring method) that every other note in this domain assumes.
- **Core** → [[Concept - LLM-as-Judge]] — the dominant 2026 scoring technique for open-ended output, fast and cheap but carrying named biases that must be actively corrected.
- **Advanced** → [[Deep Dive - Designing an Eval Harness]] — how a harness actually turns a dataset and a model into a comparable score, and why the same benchmark yields different numbers across harnesses.
- **Frontier** → [[Concept - Private and Dynamic Benchmarks]] — the active research response to contamination: private holdouts, date-windowing, procedural generation, adversarial-in-the-loop eval.
- **Unicorn** → [[Lore - Benchmark Scandals]] — the gallery of benchmark numbers that turned out to be marketing, read before trusting any headline score again.

## Foundations: what evaluation is and why it breaks

- [[Concept - Benchmark Taxonomy]] — benchmarks vary along two independent axes, what capability they test and how they're scored, and the scoring axis is the one that actually governs reproducibility.
- [[Concept - Goodhart's Law in Model Evaluation]] — any benchmark you optimize toward stops measuring the capability it was built to proxy — the root cause behind contamination, leaderboard-hacking, and reward hacking alike.
- [[Concept - Capability versus Propensity]] — what a model can do under maximal elicitation versus what it does by default; conflating the two is how "the model can't do X" claims get falsified by a better prompt.

## Scoring mechanics: how a benchmark becomes a number

- [[Breakdown - MMLU]] — the 57-subject MCQ benchmark that became the headline number, then saturated, then turned out to carry roughly 6.5% label errors.
- [[Concept - Answer Scoring and Normalization]] — log-likelihood versus generation scoring, and acc/acc_norm/PMI normalization choices that silently decide which model gets reported as SOTA.
- [[Concept - Multiple-Choice Symbol Binding and Position Bias]] — MCQ scores are confounded by which letter or position holds the correct answer, independent of content, and letter-scoring understates real knowledge.
- [[Concept - Prompt Format Sensitivity in Evaluation]] — semantically-equivalent formatting changes swing benchmark scores by many points and can flip model rankings outright.
- [[Concept - Pass@k and Sampling-Based Evaluation]] — the unbiased estimator for "at least one of k samples passes," and why quoting it against a rival's pass@1 inflates a launch chart.

## Contamination and benchmark integrity

- [[Concept - Benchmark Contamination]] — test data or its near-duplicates leaking into training corpora inflates scores without real capability gain, and perfect decontamination is impossible at web scale.
- [[Concept - Membership Inference for Contamination Detection]] — black-box methods for detecting whether text was in training data, and why most barely beat random once distribution shift is controlled for.
- [[Concept - Private and Dynamic Benchmarks]] — contamination resistance via private holdouts, date-windowing, procedural generation, and adversarial-in-the-loop evaluation.

## Judges: LLM-as-judge and human evaluation

- [[Concept - LLM-as-Judge]] — using a strong LLM to score or rank outputs instead of humans: fast and cheap, but carries named, measurable biases that must be actively corrected for.
- [[Gotchas - LLM-as-Judge Evaluations]] — the failure catalogue that corrupts judge scores, ordered by pain: position bias, length bias, self-preference, injection, drift.
- [[Concept - Meta-Evaluation of LLM Judges]] — how you validate that a judge actually agrees with ground truth, and why that validation has to repeat as optimization pressure against the judge mounts.
- [[Concept - Human Evaluation Methodology]] — how to design human eval studies — rater selection, inter-rater agreement, comparative versus absolute scoring — so the resulting numbers are actually reliable.
- [[Breakdown - Chatbot Arena]] — how anonymous pairwise human votes become a Bradley-Terry leaderboard, and the length/style confounds and 2025 governance dispute complicating it.

## Statistical rigor and model comparison

- [[Concept - Statistical Rigor in Model Evaluation]] — a benchmark score is a random variable with a confidence interval, not a fixed fact — most reported model-vs-model gaps sit inside the noise.
- [[Snippet - Paired Bootstrap for Model Comparison]] — runnable paired bootstrap and McNemar's test code to decide whether one model actually beats another on the same benchmark items.

## Building and trusting eval infrastructure

- [[Deep Dive - Designing an Eval Harness]] — how a harness turns a dataset and a model into a comparable score, and why the same benchmark yields different numbers across different harnesses.
- [[Gotchas - Benchmark Harness Pitfalls]] — the implementation traps — chat templates, acc_norm, few-shot formatting, tokenizer quirks — that make one model score differently across harnesses.
- [[Playbook - Building a Production Eval Suite]] — end-to-end procedure for building an offline-plus-online LLM eval suite that catches product regressions before users do.
- [[Decision - Choosing an Evaluation Method]] — picking between execution-based, exact-match, LLM-judge, human eval, and online A/B for a given evaluation question.
- [[Checklist - Trusting a Benchmark Number]] — pre-flight checks to run before believing a leaderboard cell, a paper's headline score, or a vendor launch chart.
- [[Reference - LLM Benchmark Landscape]] — comparison matrix of major LLM benchmarks: capability, format, size, baselines, 2026 saturation status, and headline flaws.

## Folklore

- [[Lore - Benchmark Scandals]] — war stories where benchmark numbers turned out to be marketing: fraud, overfitting, harness discrepancies, length gaming, and cherry-picking.

## Adjacent domains

- [[MOC - Post-Training]] — reward hacking and RLVR verifiers are Goodhart's law playing out inside training itself; the methodology here is what makes a verifier trustworthy.
- [[MOC - Agents]] — agent evaluation inherits every problem in this domain (contamination, judge bias, statistical noise) and adds trajectories and non-determinism on top.
- [[MOC - Safety & Interpretability]] — red-teaming and jailbreak benchmarks are this domain's methodology applied to an adversarial capability instead of a cooperative one.
- [[MOC - AI in Software Engineering]] — SWE-bench and coding-agent benchmarks are this domain's harness-design and contamination problems in their highest-stakes applied form.
