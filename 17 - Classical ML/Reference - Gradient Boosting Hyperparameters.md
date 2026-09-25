---
tags: [reference, domain/classical-ml, level/advanced]
aliases: [GBDT hyperparameters, XGBoost params, LightGBM params, CatBoost params]
summary: "Cross-library map of the same gradient-boosting knob across XGBoost, LightGBM, and CatBoost: names, ranges, defaults, and what each controls."
---
# Reference - Gradient Boosting Hyperparameters

> Same knob, three names, three defaults. This is for looking things up mid-tuning, not for reading start to finish. The order to touch them in is in [[Playbook - Tuning Gradient Boosted Trees]]; what breaks when you set them wrong is in [[Gotchas - Gradient Boosting in Practice]]. Date-stamped to XGBoost 2.x / LightGBM 4.x / CatBoost 1.2 *(as of 2026)*.

## Learning rate and boosting rounds

| Knob | XGBoost | LightGBM | CatBoost | Typical range | Controls |
|---|---|---|---|---|---|
| Shrinkage | `eta` (default 0.3) | `learning_rate` (default 0.1) | `learning_rate` (default 0.03) | 0.01–0.1 | Multiplier $\nu$ on each new tree in $F_m(x) = F_{m-1}(x) + \nu \cdot h_m(x)$ (see [[Concept - Gradient Boosting]]). Lower $\nu$ needs proportionally more rounds: the classic $\nu$-vs-$M$ tradeoff. |
| Number of trees | `num_boost_round` / `n_estimators` | `num_iterations` | `iterations` | set high, let early stopping choose | Upper bound only. Never grid-search it directly; it's coupled to the learning rate. |
| Early stopping | `early_stopping_rounds` | `early_stopping_round` | `early_stopping_rounds` | 20–100 rounds | Halts once a matched `eval_metric` on a held-out set stops improving. The right way to pick tree count. |

## Tree complexity: the biggest structural difference between the three

| Library | Growth strategy | Primary knob | Typical range |
|---|---|---|---|
| XGBoost | Level-wise (breadth-first, symmetric) | `max_depth` | 3–10 |
| LightGBM | Leaf-wise / best-first (deepest-loss-reduction leaf splits next) | `num_leaves` | 31–255, **must stay `< 2^max_depth`**¹ |
| CatBoost | Oblivious trees (same split rule at every node of a given depth) | `depth` | 6–10 |

¹ Setting `num_leaves` above what `2^max_depth` implies is the most common LightGBM overfitting footgun (see [[Gotchas - Gradient Boosting in Practice]]). Leaf-wise growth with no matching depth cap produces deep, lopsided, over-specialized trees.

## Regularization

| Knob | XGBoost | LightGBM | Controls |
|---|---|---|---|
| L1 / L2 on leaf weights | `reg_alpha` / `reg_lambda` | `lambda_l1` / `lambda_l2` | Shrinks leaf weight $w^* = -\sum g_i / (\sum h_i + \lambda)$ toward zero; it's the term added by [[Breakdown - XGBoost]]'s regularized objective $\Omega(f) = \gamma T + \tfrac12 \lambda \lVert w \rVert^2$. |
| Min samples/weight per leaf | `min_child_weight` (min Hessian sum in a leaf) | `min_child_samples` / `min_data_in_leaf` (min row count) | Refuses a split that would create a leaf with too little statistical support. The main defense against overfitting on small leaves. |
| Min gain to split | `gamma` / `min_split_loss` | `min_gain_to_split` | A split happens only if its gain exceeds this threshold, which prunes low-value splits before they're made. |

## Row / column sampling

| Knob | XGBoost | LightGBM | Typical range |
|---|---|---|---|
| Row subsampling | `subsample` | `bagging_fraction` + `bagging_freq` (how often to resample) | 0.6–0.9 |
| Column subsampling | `colsample_bytree` / `colsample_bylevel` / `colsample_bynode` | `feature_fraction` | 0.6–0.9 |

Both add bagging-style regularization *inside* the sequential boosting loop (Friedman's stochastic gradient boosting, 2002) and speed up each round proportionally.

## Categorical handling

| Library | Mechanism | Key knobs |
|---|---|---|
| LightGBM | Native: sorts categories by gradient statistic, finds optimal binary partition (Fisher 1958) | `categorical_feature`, `max_cat_threshold`, `cat_smooth` |
| CatBoost | Ordered target statistics: online, permutation-based mean encoding that avoids leakage by construction | `one_hot_max_size` |
| XGBoost | Native categorical splits (added 2.x) | `enable_categorical` |

Footnote: none of these is a free lunch. Native handling of a high-cardinality ID-like column (user ID, SKU) overfits without smoothing and proper cross-validation, the same failure as naive target encoding (see [[Snippet - Leakage-Free Target Encoding]]).

## Class imbalance

| Library | Knob |
|---|---|
| XGBoost | `scale_pos_weight` (≈ negative-count / positive-count) |
| LightGBM | `is_unbalance` or `scale_pos_weight` |
| CatBoost | `class_weights` |

Setting any of these reweights the loss and **breaks the meaning of the output as a probability**. Recalibrate downstream (see [[Concept - Probability Calibration]]) before using scores as probabilities.

## Backend / reproducibility

| Knob | XGBoost | LightGBM |
|---|---|---|
| Histogram vs exact split search | `tree_method = hist` / `gpu_hist` | `device = cpu` / `gpu`, `max_bin` (bin count for histogram, default 255) |
| Thread count | `nthread` | `num_threads` |

Footnote: GPU and multi-threaded histogram builds are **not bit-reproducible** run to run, because floating-point reduction order varies. Pin seeds *and* thread counts if you need audit-reproducible splits.

## Connections
- [[Concept - Gradient Boosting]] — the functional-gradient-descent mechanism every knob above parameterizes.
- [[Breakdown - XGBoost]] — the second-order objective and split-gain formula behind the XGBoost column.
- [[Breakdown - LightGBM]] — the histogram binning, GOSS, and EFB internals behind the LightGBM column and its speed advantage.
- [[Playbook - Tuning Gradient Boosted Trees]] — the order to touch these knobs in; this reference only tells you what each one does.
- [[Gotchas - Gradient Boosting in Practice]] — the concrete production failures (leaf-wise overfit, broken calibration, non-reproducibility) that misusing these knobs causes.
- [[Reference - LLM Pretraining Hyperparameters]] — the analogous cross-implementation hyperparameter lookup for neural pretraining, useful for seeing which knobs transfer conceptually (learning rate, regularization) and which have no neural analogue (tree depth, leaf count).
- [[Reference - Fine-Tuning Hyperparameters]] — the same "one knob, several library-specific names" lookup pattern applied to LoRA and full fine-tuning.
- [[Concept - Probability Calibration]] — why setting the imbalance-handling knobs above requires recalibrating the output scores afterward.
- [[Snippet - Leakage-Free Target Encoding]] — the leak-free alternative to the categorical-handling knobs above when native library handling of high-cardinality IDs overfits.

## Sources
- Friedman (2001) — "Greedy Function Approximation: A Gradient Boosting Machine." Defines the shrinkage/learning-rate mechanism these knobs regularize.
- Friedman (2002) — "Stochastic Gradient Boosting." The row-subsampling mechanism behind `subsample` / `bagging_fraction`.
- Chen & Guestrin (2016) — "XGBoost: A Scalable Tree Boosting System." Source of the regularized objective and second-order leaf-weight formula.
- Ke et al. (2017) — "LightGBM: A Highly Efficient Gradient Boosting Decision Tree." Source of histogram binning, GOSS, and leaf-wise growth.
