---
tags: [concept, domain/classical-ml, level/core]
aliases: [class imbalance, SMOTE, imbalanced classification, imbalanced learning]
summary: "Why accuracy and ROC-AUC lie under class imbalance, and the threshold, cost-weighting, and resampling fixes — with the leakage trap that ruins them."
---

> A fraud model trained on 0.5% positives that always predicts negative scores 99.5% accuracy and is worthless. Imbalance makes learning harder, and it also makes the metrics you'd normally trust lie to you. The standard fix, resampling, has its own well-documented failure modes.

## The mechanism

With a rare positive class, the base rate dominates every aggregate metric. **Accuracy** rewards the always-majority classifier outright. **ROC-AUC** looks deceptively robust: its false-positive-rate axis is normalized by the huge number of negatives, so a model can pile up false positives in absolute terms while the curve barely moves. Davis & Goadrich (2006) formalized why **PR-AUC** (precision-recall) visibly degrades under skew and should be preferred whenever positives are rare.

Three families of fix act at different points in the pipeline:

1. **Threshold moving.** Train normally on the natural distribution, then move the decision threshold off 0.5 to optimize F1, a cost matrix, or a target precision/recall point. It's the cheapest and safest lever because training is untouched. The model's probability estimates stay honest (see [[Concept - Probability Calibration]]); only the operating point moves.
2. **Cost-sensitive learning / reweighting the loss.** Weight minority-class errors more in the objective: `scale_pos_weight = n_negative / n_positive` in the tree ensembles behind [[Concept - Gradient Boosting]], or class-weighted cross-entropy in general. **Focal loss** (Lin et al. 2017) goes further and down-weights *easy* examples of either class with a $(1-p_t)^\gamma$ modulating factor on the standard [[Concept - Entropy and Cross-Entropy]] term, $FL(p_t) = -(1-p_t)^\gamma \log(p_t)$. Gradient signal then concentrates on hard minority examples and isn't swamped by easy majority ones.
3. **Resampling.** SMOTE (Chawla et al. 2002, Synthetic Minority Oversampling Technique) makes synthetic minority points by interpolating between a minority point and one of its $k$ nearest minority neighbors: $x_{\text{new}} = x_i + \lambda(x_{\text{nn}} - x_i)$, $\lambda \sim U(0,1)$. Borderline-SMOTE and ADASYN push the synthetic points toward the decision boundary. Undersampling discards majority rows instead; EasyEnsemble and BalancedRandomForest get the discarded signal back by training several undersampled models and ensembling them.

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

**Resample inside each fold, on the training split only, never before the split.** That's the cardinal rule. Resampling first lets synthetic neighbors leak across the train/validation boundary and inflates every downstream score. It's one of the most common bugs a reviewer can catch in imbalanced pipelines, and [[Gotchas - Gradient Boosting in Practice]] catalogs it alongside the related calibration damage.

In practice, plain class weights frequently match or beat SMOTE. "To SMOTE or not to SMOTE" (Elor & Averbuch-Elor 2022) directly challenges SMOTE-by-default: on many benchmarks `scale_pos_weight` alone was competitive with or better than SMOTE variants, far cheaper, and it doesn't distort the feature space. SMOTE, a narrow structured case of the broader [[Concept - Synthetic Training Data]] problem, also hurts where classes overlap, because it can synthesize points deep in majority territory. Text classification (see [[Concept - TF-IDF and the Bag of Words]]) is a common home for severe imbalance (rare intent categories, rare toxic-content labels), and the same threshold-first discipline applies.

The metrics that matter operationally are usually not accuracy or plain F1:

- **precision@k**: of the top-k scored items, how many are true positives. The right frame when humans review a fixed capacity.
- **recall at fixed precision**: what fraction of fraud you catch while keeping false-positive review cost under budget.
- **Matthews correlation coefficient**: one balanced summary that holds up under imbalance.
- an explicit **cost matrix** when false positives and false negatives cost different amounts of money.

All of these are instances of the general discipline in [[Concept - Statistical Rigor in Model Evaluation]].

## Failure modes

- **Accuracy or plain ROC-AUC as the headline metric** on a >90/10 imbalanced problem. Check the positive rate before trusting any reported number, and switch to PR-AUC.
- **Resampling before the train/test or CV split.** The classic leakage bug above. The tell is a suspiciously high CV score that falls apart on a true holdout.
- **SMOTE in high-dimensional or overlapping-class regions.** It synthesizes noise, because "nearest neighbor" gets unstable in high dimensions (see [[Concept - Clustering and Dimensionality Reduction]]) and interpolation can cross into majority-class regions. The tell is a precision drop after adding SMOTE that class weights alone don't cause.
- **Forgetting that resampling and reweighting both distort predicted probabilities.** After either fix, scores no longer mean $P(y=1\mid x)$. Hand off to [[Concept - Probability Calibration]] and recalibrate, or correct with the prior-shift log-odds formula, before scores are used downstream.
- **Undersampling throws away signal you need.** With severe imbalance (<0.1% positive), aggressive undersampling can leave too few majority examples to describe the decision boundary. Watch for degraded performance on majority-heavy validation slices. The class-conditional (Mondrian) variants of [[Concept - Conformal Prediction]] address a related failure, where marginal coverage guarantees hide undercoverage on the rare class.

## The non-obvious

Order of operations is the whole game. Fix the metric first (drop accuracy/ROC-AUC). Try threshold moving before touching training data. Then cost weighting. Reach for SMOTE last, inside the fold, with a specific reason to think interpolation will help this dataset. Teams that SMOTE by reflex risk the leakage bug and frequently find out later that class weights alone would have matched it for a fraction of the complexity. Read Elor & Averbuch-Elor as "SMOTE is not a free lunch," not "SMOTE never helps."

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
