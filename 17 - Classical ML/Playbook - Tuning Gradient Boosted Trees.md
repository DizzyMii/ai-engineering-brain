---
tags: [playbook, domain/classical-ml, level/advanced]
aliases: [GBDT hyperparameter tuning, tuning XGBoost, tuning LightGBM]
summary: "The ordered, leak-checked procedure for tuning XGBoost/LightGBM/CatBoost from a baseline to a squeezed final model without fooling yourself."
---

# Playbook - Tuning Gradient Boosted Trees

> **Goal:** turn a default-hyperparameter gradient-boosted tree model into a properly regularized, near-optimal one without overfitting the *tuning process* itself. **When to run this:** after a working, leak-free baseline exists and before shipping a tabular model to production. **Prerequisites:** a working train/eval pipeline, [[Concept - Gradient Boosting]] fundamentals, and the hyperparameter meanings catalogued in [[Reference - Gradient Boosting Hyperparameters]].

## Steps

**1. Build a leak-free CV scheme first.**
Action: set up stratified k-fold for i.i.d. tabular data, or forward-chaining / time-aware CV for temporal data ([[Concept - Time Series Cross-Validation and Leakage]]).
Expected observation: fold scores cluster tightly — standard deviation small relative to the mean.
What deviation means: high fold-to-fold variance signals leakage, too little data, or a CV scheme mismatched to the data's actual structure. Stop here and fix it — every later step inherits whatever bias this one has, and tuning on top of a broken CV scheme just optimizes the leak harder.

**2. Fix the learning rate, let early stopping choose the tree count.**
Action: set `learning_rate`/`eta = 0.1`, a large `num_boost_round` (several thousand), and `early_stopping_rounds ≈ 50` on the CV eval metric.
Expected observation: the validation metric improves, plateaus, then rises; the selected best-iteration sits comfortably below the round ceiling.
What deviation means: best-iteration pinned at the ceiling means `num_boost_round` wasn't large enough — raise it. Near-instant early stopping (a handful of rounds) suggests the learning rate is too high, or — more worryingly — that the model is "solving" the problem trivially because of leakage. Never grid-search the number of trees directly; it is mechanically coupled to the learning rate and early stopping already answers this question correctly.

**3. Tune tree complexity.**
Action: sweep `max_depth` (3-10) with `min_child_weight` (XGBoost), or `num_leaves` (31-255, kept below `2^max_depth`) with `min_data_in_leaf` (LightGBM) — via Bayesian/TPE search (e.g. Optuna) rather than an exhaustive grid, since the useful region of this space is much smaller than the full grid.
Expected observation: the CV metric improves noticeably — this is usually the single biggest lever in the whole procedure.
What deviation means: if increasing complexity barely moves the CV metric, the model is likely feature- or data-limited rather than complexity-limited; stop tuning complexity and go back to feature engineering instead of continuing to search this axis.

**4. Tune sampling.**
Action: sweep `subsample`/`bagging_fraction` and `colsample_bytree`/`feature_fraction`, typically in the 0.6-0.9 range.
Expected observation: a modest further CV improvement, faster wall-clock training, and a narrower train-validation gap.
What deviation means: if sampling hurts the CV score, the dataset is likely too small for stochastic subsampling to pay off — push these back toward 1.0 rather than forcing regularization the data doesn't need.

**5. Tune regularization.**
Action: sweep `reg_lambda`/`reg_alpha` (L2/L1 on leaf weights) and `gamma`/`min_split_loss` (minimum gain required to split).
Expected observation: the train-validation gap narrows further without the validation score itself dropping.
What deviation means: if closing the gap costs real validation score, you were regularizing away genuine signal, not just noise — back off toward the step-4 configuration.

**6. Lower the learning rate for the final squeeze.**
Action: drop `learning_rate` to 0.01-0.03, refit with proportionally more rounds (early stopping again decides the final count), then recalibrate probabilities and, if the task is imbalanced, retune the decision threshold ([[Concept - Probability Calibration]], [[Concept - Learning from Imbalanced Data]]).
Expected observation: a final, usually modest, accuracy gain over the step 3-5 model.
What deviation means: no gain here is normal and fine — it means steps 3-5 already found a good complexity/regularization balance. A *large* jump at this stage is worth treating with suspicion rather than celebration; re-check for leakage before shipping it.

## Verification
The CV score should improve step over step while the train-validation gap stays sane rather than widening, and the improvement must survive on a genuinely held-out test set that was never touched during tuning — or nested CV — not merely on the folds used for the search itself. A model that only looks better on the tuning folds and not on the untouched set has been tuned *to the folds*, not to the problem, which is the same multiple-comparisons trap that [[Concept - Hypothesis Testing and p-values|repeated significance testing]] runs into: enough configurations tried against the same folds will eventually look good by chance alone.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Validation score far below train (big gap) | Overfitting: complexity too high, or too little data | Reduce `max_depth`/`num_leaves`, raise `min_child_weight`/`min_data_in_leaf`, add subsampling and L2 — return to step 3 |
| Both train and validation score low (underfit) | Complexity too low, or too few effective rounds | Increase depth/leaves, lower the learning rate with more rounds, reduce `min_data_in_leaf` |
| Fold scores noisy and unstable throughout tuning | The CV scheme itself is leaking, or the dataset is too small/nonstationary for stable folds | Stop tuning immediately, return to step 1, and audit for leakage (see [[Gotchas - Gradient Boosting in Practice]]) |
| Tuning improves CV but the production metric doesn't move | `eval_metric` mismatched to the actual business objective, or train/serve preprocessing skew | Re-derive `eval_metric` from the deployed cost function; audit the serving pipeline for preprocessing drift before touching hyperparameters further |

## Connections
- [[Concept - Gradient Boosting]] — the mechanism (`learning_rate`, sequential trees, bias reduction) this playbook's step order is built around.
- [[Reference - Gradient Boosting Hyperparameters]] — the lookup table for what each knob named in these steps actually does and its typical range across libraries.
- [[Breakdown - XGBoost]] — the system whose `eta`, `max_depth`, `reg_lambda` and early-stopping mechanics this procedure tunes.
- [[Breakdown - LightGBM]] — the system whose `num_leaves`, `bagging_fraction`, and leaf-wise growth this procedure's step 3 is calibrated for.
- [[Gotchas - Gradient Boosting in Practice]] — the pitfalls (leakage, `num_leaves` misconfiguration, miscalibration) that invalidate this playbook's results if skipped over.
- [[Concept - Statistical Rigor in Model Evaluation]] — the general evaluation discipline (proper holdouts, avoiding metric-shopping) that the Verification step depends on.
- [[Concept - Time Series Cross-Validation and Leakage]] — the specific CV machinery step 1 requires whenever the data has temporal structure.
- [[Concept - Probability Calibration]] — the recalibration pass required in step 6 whenever imbalance handling or resampling was used upstream.
- [[Concept - Learning from Imbalanced Data]] — the threshold-tuning and class-weighting techniques step 6 applies on imbalanced tasks.
- [[Concept - Hypothesis Testing and p-values]] — the statistical-multiple-comparisons framing behind the Verification section's warning about tuning-to-the-folds.

## Sources
- Chen, T. & Guestrin, C. (2016) — "XGBoost: A Scalable Tree Boosting System." Source of the early-stopping and regularization design this procedure's steps 2 and 5 are built around.
- Ke, G. et al. (2017) — "LightGBM: A Highly Efficient Gradient Boosting Decision Tree." Source of the `num_leaves` guidance underlying step 3's LightGBM branch.
- Bergstra, J. & Bengio, Y. (2012) — "Random Search for Hyper-Parameter Optimization." The empirical case for random/Bayesian search over exhaustive grid search used to justify step 3's search strategy.
