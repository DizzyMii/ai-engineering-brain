---
tags: [concept, domain/classical-ml, level/core]
aliases: [random forest, RF, bootstrap aggregating, bagging]
summary: "Variance reduction by averaging decorrelated trees trained on bootstrap resamples and random feature subsets."
---

# Concept - Bagging and Random Forests

> Bagging and random forests are the parallel half of tree learning: instead of correcting errors sequentially like boosting, they train many independent, high-variance [[Concept - Decision Trees|decision trees]] and average their predictions, relying on the statistical fact that averaging cancels variance faster than it cancels signal. Random forests remain the great low-effort default baseline for tabular problems — hard to overfit, embarrassingly parallel, and competitive out of the box.

## The mechanism

Bagging — bootstrap aggregating (Breiman, 1996) — trains $B$ trees, each on an independent bootstrap resample (sampling $n$ rows with replacement from an $n$-row dataset), and combines them by averaging (regression) or majority vote (classification). The theoretical justification is a simple variance identity: if you average $B$ i.i.d. predictors each with variance $\sigma^2$, the variance of the average is $\sigma^2 / B$. But real bootstrap trees are **not** independent — they're trained on heavily overlapping resamples of the same data — so raw bagging's variance reduction plateaus well short of this ideal as $B$ grows.

Random forests (Breiman, 2001) fix this by adding a second source of randomness: at every split, only a random subset of features is considered — $\sqrt{p}$ for classification, $p/3$ for regression, where $p$ is the total feature count — rather than searching all features as CART does. This deliberately **decorrelates** the trees: two trees trained on the same bootstrap sample but different feature subsets will disagree more often, because they can't both lock onto the same dominant feature at the root. The general variance-of-the-average identity for correlated predictors makes the mechanism explicit:

$$\text{Var}(\bar{h}) = \rho\sigma^2 + \frac{1-\rho}{B}\sigma^2$$

where $\rho$ is the pairwise correlation between trees and $\sigma^2$ is each tree's individual variance. As $B \to \infty$, the second term vanishes but the first, $\rho\sigma^2$, does not — so **driving down $\rho$**, not adding more trees, is the entire trick once $B$ is reasonably large. Feature subsampling is precisely the lever that reduces $\rho$.

A structural bonus falls out of the bootstrap sampling for free: each tree is trained on a resample that, in expectation, omits about $1 - 1/e \approx 36.8\%$ of the original rows (the classic "not drawn in $n$ draws with replacement" limit). Evaluating each row only on the trees that never saw it — its **out-of-bag (OOB)** trees — yields an unbiased, cross-validation-quality error estimate with zero held-out data sacrificed and no extra training runs.

```
for b in 1..B:
    sample_b = bootstrap_resample(train_data)          # rows w/ replacement
    tree_b = grow_tree(sample_b, feature_subsample=sqrt(p))  # RF: random feature subset per split
forest_prediction(x) = average_or_vote(tree_b(x) for b in 1..B)
```

## In practice

The RF-vs-GBM contrast is the practical decision practitioners reach for constantly: random forests are embarrassingly parallel (every tree trains independently), notoriously hard to overfit by adding more trees (more $B$ only helps or plateaus, never hurts, unlike [[Concept - Gradient Boosting|gradient boosting]]'s sequential residual-chasing), and need almost no tuning to get a solid result. Gradient boosting is sequential, has a higher achievable accuracy ceiling, but requires early stopping and careful tuning to avoid overfitting. This makes random forests the natural first baseline on any new tabular problem, with boosted trees as the accuracy-squeeze that follows once the baseline is established (see [[Decision - Deep Learning vs Gradient Boosting for Tabular Data]]).

Feature importance comes in two flavors, and conflating them is a classic footgun. **Mean decrease in impurity (MDI)** is essentially free (it falls out of training) but is systematically biased toward high-cardinality and continuous features — the same greedy-split bias that affects a single tree. **Permutation importance** (Fisher, Rudin & Dominici, 2019) measures the actual drop in held-out performance when a feature's values are shuffled, which is unbiased with respect to cardinality — but it becomes misleading under correlated features, because shuffling one correlated feature barely hurts performance if a redundant partner is still present to carry its signal.

Extensions worth knowing: Extremely Randomized Trees (Extra-Trees, Geurts et al., 2006) push randomization further by randomizing the split *threshold* too, not just the feature subset, trading a little bias for even more variance reduction and faster training. Quantile regression forests repurpose the per-leaf sample distribution (rather than just its mean) to produce prediction intervals. Isolation forests invert the whole idea for anomaly detection: points that get isolated by very few random splits are the outliers.

## Failure modes

- **Cannot extrapolate.** Like any tree-based method, a random forest's prediction is an average of leaf constants, so it stays flat outside the range of values seen in training — dangerous for trending numeric features.
- **Memory blows up with deep, unpruned trees.** Hundreds of deep trees, each storing its own structure, can produce multi-gigabyte models; this rarely shows up in a notebook with a small dataset but bites hard at production scale.
- **Poorly calibrated probabilities.** A random forest's "probability" output is a vote fraction — the proportion of trees predicting the positive class — not a genuine likelihood estimate, and vote fractions are known to cluster away from 0 and 1 even for confident predictions. Don't use raw RF probabilities for anything threshold- or cost-sensitive without recalibrating (see [[Concept - Probability Calibration]]).

## The non-obvious

The variance identity $\rho\sigma^2 + \frac{1-\rho}{B}\sigma^2$ explains a result that surprises people moving from bagging to random forests for the first time: past a certain point, adding more trees to a random forest stops improving accuracy almost entirely, while the *feature subsampling fraction* keeps mattering. This is because $B$ only ever attacks the second, vanishing term — it cannot touch $\rho\sigma^2$, the floor set by how correlated the trees are. Practitioners who tune `n_estimators` exhaustively while leaving `max_features` at its default are optimizing the wrong knob; the correlation-reduction lever is the one that actually moves the needle, and it's also the reason random forests, unlike boosting, genuinely cannot overfit by adding more trees — more $B$ can only drive the estimate down toward the $\rho\sigma^2$ floor, never up.

## Connections
- [[Concept - Decision Trees]] — the unstable, high-variance base learner that bagging's averaging is specifically designed to exploit.
- [[Concept - Gradient Boosting]] — the sequential, bias-reducing counterpart; contrasting the two is the standard way to reason about which ensemble strategy fits a given problem.
- [[Decision - Deep Learning vs Gradient Boosting for Tabular Data]] — random forests are the low-effort baseline this build decision is measured against before reaching for boosting or neural nets.
- [[Concept - Statistical Rigor in Model Evaluation]] — OOB error is a specific, free instance of the general cross-validation discipline this note covers.
- [[Concept - Data Parallelism and ZeRO]] — random forests' embarrassingly-parallel tree training is a useful contrast to the communication-bound parallelism strategies used for training neural networks at scale.
- [[Concept - Probability Calibration]] — RF vote fractions require exactly the recalibration techniques this note describes before they can be trusted as probabilities.
- [[Concept - Causal Inference Basics]] — causal forests extend the random-forest mechanism (with honest splitting) to estimate heterogeneous treatment effects rather than plain predictions.
- [[Gotchas - Gradient Boosting in Practice]] — several pitfalls here (extrapolation, miscalibration, importance bias) reappear in an amplified form for boosted trees.

## Sources
- Breiman (1996) — *Bagging Predictors*. Establishes bootstrap aggregation as a variance-reduction technique.
- Breiman (2001) — *Random Forests*. Adds per-split feature subsampling to decorrelate trees, and derives the $\rho\sigma^2 + \frac{1-\rho}{B}\sigma^2$ variance decomposition.
- Fisher, Rudin & Dominici (2019) — *All Models are Wrong, but Many are Useful*. Formalizes permutation importance and its correlated-feature failure mode.
- Geurts, Ernst & Wehenkel (2006) — *Extremely Randomized Trees*. Randomizes split thresholds in addition to feature subsets.
