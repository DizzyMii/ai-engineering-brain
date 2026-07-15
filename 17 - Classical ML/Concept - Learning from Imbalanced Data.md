---
tags: [concept, domain/classical-ml, level/core]
aliases: [class imbalance, SMOTE, imbalanced classification, imbalanced learning]
summary: "Why accuracy and ROC-AUC lie under class imbalance, and the threshold, cost-weighting, and resampling fixes — with the leakage trap that ruins them."
---

> A fraud model trained on 0.5% positives that "predicts negative always" scores 99.5% accuracy and is worthless. Imbalance doesn't just make learning harder — it makes the metrics you'd normally trust actively lie to you, and the standard "fix," resampling, has its own well-documented failure modes.

## The mechanism

With a rare positive class, the base rate dominates every aggregate metric. **Accuracy** rewards the majority-class-always classifier outright. **ROC-AUC** is deceptively robust-looking because its false-positive-rate axis is normalized by the (huge) number of negatives, so a model can accumulate a large absolute number of false positives while barely moving the curve; Davis & Goadrich (2006) formalized why **PR-AUC** (precision-recall) is the metric that actually degrades visibly under skew and should be preferred whenever positives are rare.

Three families of fix operate at different points in the pipeline:

1. **Threshold moving.** Train the classifier normally on the natural distribution, then move the decision threshold away from 0.5 to optimize F1, a cost matrix, or a target precision/recall point. This is the cheapest and safest lever because it touches nothing about training — the model's probability estimates stay honest (see [[Concept - Probability Calibration]]), only the operating point changes.
2. **Cost-sensitive learning / reweighting the loss.** Give minority-class errors more weight in the objective: `scale_pos_weight = n_negative / n_positive` in the tree ensembles behind [[Concept - Gradient Boosting]], or class-weighted cross-entropy generally. **Focal loss** (Lin et al. 2017) goes further and down-weights *easy* examples regardless of class via a $(1-p_t)^\gamma$ modulating factor on the standard [[Concept - Entropy and Cross-Entropy]] term, $FL(p_t) = -(1-p_t)^\gamma \log(p_t)$, so gradient signal concentrates on hard minority-class examples instead of being swamped by easy majority-class ones.
3. **Resampling.** SMOTE (Chawla et al. 2002, Synthetic Minority Oversampling Technique) generates synthetic minority points by interpolating between a minority point and one of its $k$ nearest minority neighbors: $x_{\text{new}} = x_i + \lambda(x_{\text{nn}} - x_i)$, $\lambda \sim U(0,1)$. Borderline-SMOTE and ADASYN bias the synthetic points toward the decision boundary. Undersampling instead discards majority rows; EasyEnsemble and BalancedRandomForest recover the discarded signal by training multiple undersampled models and ensembling them.

## In practice

```
WRONG (leaks the boundary):
  SMOTE(all_data) -> split into train/test -> fit -> score
  # synthetic minority points can be interpolated using
  # neighbors that end up on the "test" side of the split

RIGHT:
  for each CV fold:
      train_fold, val_fold = split(data)
      train_fold_resampled = SMOTE(train_fold)   # only the fold's training rows
      fit(train_fold_resampled)
      score(val_fold)   # val_fold untouched, natural distribution
```

**Resample inside each fold, on the training split only, never before the split** — this is the cardinal rule. Resampling before splitting lets synthetic neighbors leak across the train/validation boundary and inflates every downstream score; it is one of the most common review-catchable bugs in imbalanced pipelines, and it is exactly the bug catalogued in [[Gotchas - Gradient Boosting in Practice]] alongside the related calibration damage.

In practice, plain class weights frequently match or beat SMOTE. "To SMOTE or not to SMOTE" (Elor & Averbuch-Elor 2022) is a direct empirical challenge to SMOTE-by-default: on many benchmarks `scale_pos_weight` alone was competitive with or better than SMOTE variants, while being far cheaper and not distorting the feature space. SMOTE — a narrow, structured special case of the broader [[Concept - Synthetic Training Data]] problem — also actively hurts in regions where classes overlap, since it can synthesize points deep in majority territory. Text classification (see [[Concept - TF-IDF and the Bag of Words]]) is a common home for severe imbalance — rare intent categories, rare toxic-content labels — where the same threshold-first discipline applies.

The metrics that matter operationally are usually not accuracy or plain F1: **precision@k** (of the top-k scored items, how many are true positives — the right frame when a human reviews a fixed capacity), **recall at fixed precision** (what fraction of fraud is caught while keeping false-positive review cost under budget), the **Matthews correlation coefficient** (a single balanced summary robust to imbalance), and an explicit **cost matrix** when false positives and false negatives have genuinely different dollar costs — all instances of the general discipline covered in [[Concept - Statistical Rigor in Model Evaluation]].

## Failure modes

- **Reporting accuracy or plain ROC-AUC as the headline metric** on a >90/10 imbalanced problem — detect by checking the positive rate before trusting any reported number; switch to PR-AUC.
- **Resampling before the train/test or CV split** — the classic leakage bug above; detect via an implausibly high CV score that doesn't survive a true holdout.
- **SMOTE in high-dimensional or overlapping-class regions** — synthesizes noise rather than signal because "nearest neighbor" becomes unstable in high dimensions (see [[Concept - Clustering and Dimensionality Reduction]]) and interpolation can cross into majority-class regions; detect via a precision drop after adding SMOTE that class weights alone don't cause.
- **Forgetting that resampling and reweighting both distort predicted probabilities** — after either fix, scores no longer mean $P(y=1\mid x)$, a direct handoff to [[Concept - Probability Calibration]] that must be recalibrated or corrected via the prior-shift log-odds formula before scores are used downstream.
- **Undersampling throwing away the signal needed** — with severe imbalance (<0.1% positive), aggressive undersampling can leave too few majority examples to characterize the decision boundary; detect via degraded performance on majority-class-heavy validation slices. [[Concept - Conformal Prediction]]'s class-conditional (Mondrian) variants directly address the related failure of marginal coverage guarantees hiding undercoverage on the rare class.

## The non-obvious

The order of operations is the whole game: fix the metric first (switch off accuracy/ROC-AUC), try threshold moving before touching training data at all, then cost weighting, and reach for SMOTE last — inside the fold, with a specific hypothesis about why interpolation will help this particular dataset. Teams that reach for SMOTE first, as a reflex, both risk the leakage bug and frequently discover afterward that class weights alone would have matched it for a fraction of the complexity — Elor & Averbuch-Elor's result is best read as "SMOTE is not a free lunch," not "SMOTE never helps."

## Connections

- [[Concept - Probability Calibration]] — resampling and reweighting both distort predicted probabilities, so any imbalance fix must be followed by recalibration before scores are trusted as probabilities.
- [[Concept - Gradient Boosting]] — `scale_pos_weight` is the concrete cost-sensitive-learning lever in the tree ensembles that dominate tabular imbalanced classification.
- [[Concept - Statistical Rigor in Model Evaluation]] — PR-AUC, MCC, and cost-matrix reporting are instances of the general discipline of choosing metrics that don't mislead under skewed or non-IID data.
- [[Concept - Synthetic Training Data]] — SMOTE is a narrow, structured special case of the broader synthetic-data-generation problem, with its own distortion risks at larger scale.
- [[Concept - Conformal Prediction]] — class-conditional (Mondrian) conformal prediction directly addresses the case where marginal coverage guarantees hide undercoverage on the rare class.
- [[Gotchas - Gradient Boosting in Practice]] — documents the specific failure of resampling-before-splitting and of shipping `scale_pos_weight`-adjusted scores as if they were still calibrated probabilities.
- [[Concept - Entropy and Cross-Entropy]] — the loss focal loss modifies; the unmodified cross-entropy gradient is why easy majority examples otherwise dominate training.
- [[Concept - TF-IDF and the Bag of Words]] — text classification is a common home for severe class imbalance, where the same threshold-moving-before-resampling discipline applies.

## Sources
- Davis & Goadrich (2006) — "The Relationship Between Precision-Recall and ROC Curves," the formal case for preferring PR-AUC under class skew.
- Chawla, Bowyer, Hall & Kegelmeyer (2002) — "SMOTE: Synthetic Minority Over-sampling Technique," the original algorithm.
- Lin, Goyal, Girshick, He & Dollár (2017) — "Focal Loss for Dense Object Detection," the origin of the $(1-p_t)^\gamma$ modulating factor.
- Elor & Averbuch-Elor (2022) — "To SMOTE or not to SMOTE," the empirical challenge to SMOTE-by-default.
