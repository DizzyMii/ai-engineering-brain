---
tags: [concept, domain/evaluation, level/advanced]
aliases: [human eval, HITL evaluation, inter-annotator agreement]
summary: "How to design human evaluation studies so the resulting numbers are actually reliable, not just plausible-looking."
---

> **One-paragraph hook:** Human evaluation is treated as the ground truth that [[Concept - LLM-as-Judge]] gets benchmarked against, but a human eval is only as good as its study design — the wrong task format, an unmeasured agreement rate, or the wrong rater pool produces numbers that look authoritative and are actually noise. Getting this right is a statistics-and-operations problem, not a "just ask people" problem.

## The mechanism

**Study designs, ranked by reliability.** Pairwise preference (show raters output A and output B for the same prompt, ask which is better) has the lowest cognitive load and the highest inter-rater consistency, because humans are much better at relative judgments than absolute ones — this is the same reason Chatbot Arena (see [[Breakdown - Chatbot Arena]]) uses battles instead of ratings. Likert/rubric scoring (rate 1–5 or 1–10 on a dimension) is cheaper per comparison but suffers from scale-anchoring drift between raters and over time. Best-of-n ranking generalizes pairwise to more candidates at once but multiplies the comparison burden combinatorially. Structured error annotation (mark specific spans as factually wrong, unsafe, or off-topic) trades raw throughput for diagnostic detail. The general rule: whenever you can reduce a judgment to a binary or small-n relative comparison, do it — every step toward absolute, high-cardinality scoring degrades consistency.

**Measuring whether your raters agree at all.** Raw percent agreement is misleading because it doesn't correct for the agreement you'd expect from chance alone — two raters flipping coins on a binary task already agree 50% of the time. The standard corrections:

$$\kappa = \frac{P_o - P_e}{1 - P_e}$$

where $P_o$ is observed agreement and $P_e$ is chance-expected agreement. Cohen's kappa handles two raters; Fleiss' kappa extends this to $n$ raters over a fixed item set; Krippendorff's alpha generalizes further to arbitrary numbers of raters, arbitrary measurement scales (nominal, ordinal, interval), and missing data (not every rater sees every item). Landis & Koch's conventional bands: kappa 0.0–0.2 is slight agreement, 0.2–0.4 fair, 0.4–0.6 moderate, 0.6–0.8 substantial, 0.8–1.0 almost perfect. An eval reporting a headline number with kappa below ~0.6 is reporting noise with a confidence-inspiring decimal point.

**Rater-quality-aware aggregation.** Naive majority vote treats every annotator as equally reliable, which is false — some raters are careless, some are systematically biased, and a few are adversarial (click-through spam). Dawid-Skene and MACE (Multi-Annotator Competence Estimation) instead jointly infer each annotator's reliability and the latent true label via expectation-maximization, down-weighting unreliable raters instead of discarding or trusting them uniformly. For pairwise battle data specifically, Bradley-Terry or Elo aggregation (the same math as [[Breakdown - Chatbot Arena]]) converts a large set of individual A-vs-B votes into a single latent-strength ranking with defensible confidence intervals — see [[Concept - Statistical Rigor in Model Evaluation]] for the general machinery.

## In practice

Match the rater pool to the judgment being asked. Domain-knowledge questions (is this legal analysis correct? is this medical answer accurate?) need subject-matter experts — a general crowd worker has no way to tell a plausible-sounding wrong answer from a right one, so their "agreement" is agreement on fluency, not correctness. Preference and helpfulness questions ("which response would you rather receive?") can legitimately use a broader crowd, since the judgment is about the rater's own experience. Getting this wrong is a silent error: InstructGPT (Ouyang et al. 2022) used trained, vetted contractors rather than raw crowd workers specifically because preference-labeling quality mattered enough to the resulting reward model to justify the cost — a lesson often skipped when teams reach for the cheapest labeling platform.

Reliability failure modes to actively guard against: annotator drift (a rater's internal scale shifts over a long session — refresh calibration examples periodically), fatigue (quality degrades after dozens of consecutive items — cap session length), low-effort/spam responses (insert gold-standard items with known answers as attention checks and discard raters who fail them), ambiguous guidelines (pilot the guidelines on a small batch and revise before scaling — most disagreement traces back to guideline ambiguity, not rater incompetence), and cultural/demographic bias in subjective preferences (helpfulness and tone preferences are not culturally universal; a single rater pool's consensus is not a universal ground truth).

Cost and scale trade off directly against reliability. Human evaluation runs roughly $0.5–5 per sample and takes days to schedule and collect, versus seconds and sub-cent cost for an [[Concept - LLM-as-Judge]] call — which is exactly why production pipelines use LLM judges for the high-volume dev loop and reserve human eval for periodic audits and launch-gating decisions (see [[Decision - Choosing an Evaluation Method]]). Chatbot Arena is the scale extreme of human eval: crowdsourced, uncontrolled-prompt-distribution, self-selected raters generating millions of votes, trading experimental control for sheer volume and ecological validity. Human-eval agreement statistics are also the yardstick used in [[Concept - Meta-Evaluation of LLM Judges]] — an LLM judge is only trusted to the extent it reproduces the same kappa-quality agreement a well-designed human study would get.

## Failure modes

- **Reporting a score with no agreement statistic.** A mean Likert score across raters with no kappa or alpha reported gives no way to tell if the raters were even measuring the same thing.
- **Mismatched rater expertise.** Using generalist crowd workers to grade domain-expert content (legal, medical, code correctness) produces confident-looking labels that reward fluency over correctness.
- **Uncontrolled scale drift.** Likert scores collected over weeks without recalibration checkpoints silently shift as raters' internal anchors change, making "5/10 in week 1" not comparable to "5/10 in week 4."
- **Majority vote on unreliable raters.** Naive majority voting without Dawid-Skene/MACE-style reliability weighting lets a cluster of low-effort raters swamp a smaller set of careful ones.
- **Underpowered studies.** Running human eval on too few samples to detect the effect size you actually care about, then treating a non-significant result as "no difference" — this is the same statistical-power problem covered in [[Concept - Statistical Rigor in Model Evaluation]].

## The non-obvious

Pairwise beats absolute scoring not just for statistical reasons but because it changes what raters are cognitively doing: absolute scoring asks a rater to hold an implicit, unstated rubric in their head and apply it consistently across hundreds of items and days of sessions, which is a memory and calibration task humans are bad at; pairwise asks only "which of these two is better," a comparison humans do reliably even when they can't articulate the criterion. This is why serious human-eval pipelines convert almost everything to pairwise or forced-ranking form even when the underlying question ("how good is this response") feels like it should be absolute — the absolute framing is a trap that produces plausible-looking, poorly-calibrated numbers.

## Connections
- [[Concept - LLM-as-Judge]] — the cheap, fast substitute for human eval; its own reliability is validated against human-eval agreement rates.
- [[Concept - Statistical Rigor in Model Evaluation]] — the significance-testing and confidence-interval machinery that turns raw human-eval scores into defensible comparisons.
- [[Breakdown - Chatbot Arena]] — the largest-scale human eval in the field, and a case study in the pairwise-plus-Bradley-Terry design this note recommends.
- [[Deep Dive - RLHF End to End]] — the pairwise preference data this note's methodology produces is the direct input to reward-model training in RLHF.
- [[Concept - Reward Models]] — reward models are trained on exactly the human preference judgments this note's designs collect.
- [[Decision - Choosing an Evaluation Method]] — the cost/reliability tradeoff between human eval, LLM-judge, and execution-based grading that determines when human eval is worth its price.
- [[Concept - Hypothesis Testing and p-values]] — the foundational statistics (Foundations domain) underlying kappa significance and study power calculations.
- [[Concept - Meta-Evaluation of LLM Judges]] — the frontier problem of validating an automated judge against exactly the kind of rigorous human-eval agreement data this note describes how to collect.

## Sources
- Ouyang, L. et al. (2022) — "Training Language Models to Follow Instructions with Human Feedback" (InstructGPT). Used trained contractors rather than raw crowd workers for preference labeling — the expert-vs-crowd mismatch example.
- Dawid, A. P. & Skene, A. M. (1979) — "Maximum Likelihood Estimation of Observer Error-Rates Using the EM Algorithm." The foundational rater-reliability-weighted aggregation method, still the basis of MACE and modern crowd-labeling pipelines.
- Landis, J. R. & Koch, G. G. (1977) — "The Measurement of Observer Agreement for Categorical Data." Source of the conventional kappa interpretation bands (slight/fair/moderate/substantial/almost perfect).
- Chiang, W.-L. et al. (2024) — Chatbot Arena / LMSYS paper. The large-scale crowdsourced pairwise human-eval design referenced throughout.
