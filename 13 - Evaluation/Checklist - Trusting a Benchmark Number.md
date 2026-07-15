---
tags: [checklist, domain/evaluation, level/core]
aliases: [benchmark trust checklist, is this benchmark number real]
summary: "Pre-flight checks before believing a leaderboard cell, a paper's headline score, or a vendor launch chart."
---

# Checklist - Trusting a Benchmark Number

Run every item below before a benchmark number changes a decision — a model choice, a launch claim, or a "we beat the competition" slide. A number that fails even one of these checks is not disqualified outright, but it needs a caveat attached before it goes anywhere near a decision document.

## Reproducibility

- [ ] The evaluation harness is named and version-pinned (e.g., a specific lm-evaluation-harness commit), not just "we ran the benchmark."
- [ ] The prompt template and few-shot count are reported explicitly (0-shot vs. 5-shot changes the number materially).
- [ ] The scoring method is stated: log-likelihood vs. free generation, and if MCQ, accuracy (`acc`) vs. length-normalized accuracy (`acc_norm`).
- [ ] If comparing against a published number, the same harness version was used for both — cross-harness comparisons are not valid without re-running.

## Contamination

- [ ] The model's training data cutoff is checked against the benchmark's release date; problems dated before the cutoff are presumptively at risk.
- [ ] Decontamination methodology (if any) is reported, not just asserted.
- [ ] If the benchmark ships canary strings (e.g., BIG-bench's), the report states whether they were respected — see [[Concept - Benchmark Contamination]].

## Statistics

- [ ] Sample size (`n`) is reported for every score, not just the percentage.
- [ ] A confidence interval or standard error accompanies the point estimate.
- [ ] The claimed gap between two models is larger than the overlap of their confidence intervals — and ideally, a paired test (same items for both models) was used rather than comparing two independent marginal CIs, per [[Concept - Statistical Rigor in Model Evaluation]].
- [ ] On small benchmarks (roughly under a few hundred items, e.g. AIME's ~30/year), the per-item granularity is stated so a reader can judge whether the reported gap could be one or two flipped questions.

## Apples-to-apples

- [ ] Every compared model used the same number of shots, the same benchmark subset/version, and the same answer-parsing logic.
- [ ] Instruct/chat models were run with their correct chat template applied — an untemplated instruct model can lose 10–20 points for reasons unrelated to capability.
- [ ] If one model's number is `pass@k`, `cons@k`, or `maj@k` and another's is `pass@1`, they are labeled as such and not silently presented as comparable — see [[Concept - Pass@k and Sampling-Based Evaluation]].

## Judge / human

- [ ] For LLM-judged results, the judge model (and its version/date) is disclosed, and position-debiasing (swap-and-average or equivalent) was applied.
- [ ] For human-eval results, inter-annotator agreement (kappa or alpha) is reported, not just a raw preference percentage.

## Gaming

- [ ] There is no indication the model (or a close variant) was trained on data overlapping the train or test split of the benchmark being reported.
- [ ] There is no sign the release was tuned specifically to a leaderboard metric (a suspiciously large gain on one narrow benchmark relative to broad capability elsewhere is a warning sign, not a badge).
- [ ] For win-rate/judged metrics, length or formatting is not obviously correlated with the score (a win-rate without length control is a known gaming vector).

## Why these items

- **Harness version-pinning** is on this list because of the 2023 Open LLM Leaderboard MMLU discrepancy: HuggingFace's own leaderboard, the original MMLU code, and Stanford HELM produced materially different numbers for the *same model*, purely from harness implementation differences — documented by the leaderboard maintainers themselves.
- **The gaming check** exists because of Reflection-70B (Sept 2024): a claimed state-of-the-art release that independent evaluators could not reproduce, with evidence the serving API was silently proxying to another vendor's model — a well-documented fiasco, not a rumor.
- **The length/formatting check under judge/human and gaming** exists because AlpacaEval's raw win-rate was measurably inflated by output length until the authors shipped a length-controlled version specifically to close that loophole.
- **The statistics section's paired-test item** exists because GSM1k rebuilding GSM8K-style problems fresh exposed 8–13% drops in several model families that a same-benchmark, no-CI comparison would never have surfaced — the original number wasn't statistically wrong, it was measuring something narrower than "math capability" all along.
- **Chat-template application** is here because it's one of the single largest, most silent sources of score variance in the field: the exact same weights can look like a materially weaker model purely from a missing template.

## Connections

- [[Concept - Statistical Rigor in Model Evaluation]] — the full statistical machinery (confidence intervals, paired testing, multiple-comparison correction) the Statistics section compresses into checklist items.
- [[Concept - Benchmark Contamination]] — the mechanisms and detection methods behind the Contamination section, including why canary strings only work as a norm.
- [[Concept - Answer Scoring and Normalization]] — the scoring-method arcana (`acc` vs. `acc_norm`, log-likelihood vs. generation) behind the Reproducibility and Apples-to-apples sections.
- [[Lore - Benchmark Scandals]] — the full narratives behind the incidents cited in "Why these items": Reflection-70B, the Open LLM Leaderboard discrepancy, AlpacaEval length gaming, and GSM1k.
- [[Deep Dive - Designing an Eval Harness]] — the harness internals that make the Reproducibility section's items possible to check in the first place.
- [[Reference - LLM Benchmark Landscape]] — the per-benchmark lookup table this checklist should be run against before citing any specific row's SOTA cell.
- [[Concept - Goodhart's Law in Model Evaluation]] — the general principle the Gaming section is a concrete operational instance of: a benchmark a lab optimizes toward stops measuring what it was built to proxy.
- [[Gotchas - Reading Model Announcements]] — the companion pitfall catalogue (owned by domain 19) for reading vendor launch charts specifically, one of the main places a benchmark number that fails this checklist ends up in front of a decision-maker.
- [[Concept - The Emergent Abilities Debate]] — a case where the trustworthiness question this checklist raises turns out to change the scientific conclusion entirely: claimed "emergent" jumps have been shown to be metric-choice artifacts rather than real capability discontinuities.
- [[Concept - Pass@k and Sampling-Based Evaluation]] — the metric family behind the Apples-to-apples section's `pass@k` vs. `pass@1` labeling check.

## Sources
- HuggingFace (2023) — "What's Going On with the Open LLM Leaderboard?" Documents the cross-harness MMLU discrepancy.
- Zhang et al. (2024) — A Careful Examination of Large Language Model Performance on Grade School Arithmetic (GSM1k). Source of the 8–13% contamination-linked drop.
- Dubois et al. (2024) — Length-Controlled AlpacaEval: A Simple Way to Debias Automatic Evaluators. Source of the length-gaming fix.
