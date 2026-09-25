---
tags: [concept, domain/classical-ml, level/core]
aliases: [random forest, RF, bootstrap aggregating, bagging]
summary: "Variance reduction by averaging decorrelated trees trained on bootstrap resamples and random feature subsets."
---

# Concept - Bagging and Random Forests

> Bagging and random forests are the parallel half of tree learning. Boosting corrects errors one tree at a time; these methods train many independent, high-variance [[Concept - Decision Trees|decision trees]] and average their predictions, relying on the fact that averaging cancels variance faster than it cancels signal. Random forests are still the best low-effort default baseline for tabular problems: hard to overfit, embarrassingly parallel, and competitive out of the box.

## The mechanism

Bagging, or bootstrap aggregating (Breiman, 1996), trains $B$ trees, each on an independent bootstrap resample ($n$ rows drawn with replacement from an $n$-row dataset), and combines them by averaging (regression) or majority vote (classification). The justification is a variance identity: average $B$ i.i.d. predictors with variance $\sigma^2$ each, and the average has variance $\sigma^2 / B$. Real bootstrap trees are **not** independent, though. Their resamples overlap heavily, so plain bagging's variance reduction plateaus well short of that ideal as $B$ grows.

Random forests (Breiman, 2001) add a second source of randomness. At every split only a random subset of features is considered ($\sqrt{p}$ for classification, $p/3$ for regression, with $p$ the total feature count), where CART would search all of them. This **decorrelates** the trees. Two trees trained on the same bootstrap sample with different feature subsets disagree more often, because they can't both grab the same dominant feature at the root. The variance-of-the-average identity for correlated predictors shows why:

$$\text{Var}(\bar{h}) = \rho\sigma^2 + \frac{1-\rho}{B}\sigma^2$$

Here $\rho$ is the pairwise correlation between trees and $\sigma^2$ each tree's variance. As $B \to \infty$ the second term vanishes and the first, $\rho\sigma^2$, stays. Once $B$ is reasonably large, the whole trick is **driving down $\rho$**; more trees won't do it. Feature subsampling is the lever that lowers $\rho$.

Bootstrap sampling also gives you something for free. In expectation each tree's resample leaves out about $1 - 1/e \approx 36.8\%$ of the original rows (the classic "not drawn in $n$ draws with replacement" limit). Score each row only on the trees that never saw it, its **out-of-bag (OOB)** trees, and you get an unbiased, cross-validation-quality error estimate without holding out data or running extra training.

```
for b in 1..B:
    sample_b = bootstrap_resample(train_data)          # rows w/ replacement
    tree_b = grow_tree(sample_b, feature_subsample=sqrt(p))  # RF: random feature subset per split
forest_prediction(x) = average_or_vote(tree_b(x) for b in 1..B)
```

## In practice

RF vs. GBM is the choice practitioners make constantly. Random forests are embarrassingly parallel (each tree trains independently). They're notoriously hard to overfit by adding trees: more $B$ helps or plateaus and never hurts, unlike [[Concept - Gradient Boosting|gradient boosting]]'s sequential residual-chasing. And they need almost no tuning for a solid result. Gradient boosting is sequential and has a higher accuracy ceiling, but needs early stopping and careful tuning to avoid overfitting. So random forests are the natural first baseline on a new tabular problem, and boosted trees are the accuracy squeeze that comes after (see [[Decision - Deep Learning vs Gradient Boosting for Tabular Data]]).

Feature importance comes in two kinds, and mixing them up is a classic footgun. **Mean decrease in impurity (MDI)** is essentially free, since it falls out of training, but it's systematically biased toward high-cardinality and continuous features, the same greedy-split bias a single tree has. **Permutation importance** (Fisher, Rudin & Dominici, 2019) measures the actual drop in held-out performance when a feature's values are shuffled. It's unbiased with respect to cardinality but misleading under correlated features: shuffle one feature and performance barely drops if a redundant partner still carries its signal.

Extensions worth knowing:

- **Extremely Randomized Trees** (Extra-Trees, Geurts et al., 2006) also randomize the split *threshold*, on top of the feature subset, trading a little bias for more variance reduction and faster training.
- **Quantile regression forests** use the per-leaf sample distribution, and not only its mean, to produce prediction intervals.
- **Isolation forests** invert the idea for anomaly detection: points isolated by very few random splits are the outliers.

## Failure modes

- **Cannot extrapolate.** Like any tree method, a random forest predicts an average of leaf constants, so it goes flat outside the range seen in training. That's dangerous for trending numeric features.
- **Memory blows up with deep, unpruned trees.** Hundreds of deep trees, each storing its own structure, can add up to multi-gigabyte models. You rarely see it in a notebook with a small dataset; it bites at production scale.
- **Poorly calibrated probabilities.** An RF "probability" is a vote fraction, the share of trees predicting the positive class. It isn't a likelihood estimate, and vote fractions are known to cluster away from 0 and 1 even for confident predictions. Recalibrate before using raw RF probabilities for anything threshold- or cost-sensitive (see [[Concept - Probability Calibration]]).

## The non-obvious

The identity $\rho\sigma^2 + \frac{1-\rho}{B}\sigma^2$ explains something that surprises people moving from bagging to random forests: past some point, more trees stop improving accuracy almost entirely, while the *feature subsampling fraction* keeps mattering. $B$ only attacks the second, vanishing term. It can't touch $\rho\sigma^2$, the floor set by how correlated the trees are. If you tune `n_estimators` exhaustively and leave `max_features` at its default, you're turning the wrong knob. The correlation lever is the one that moves results. It's also why random forests, unlike boosting, can't overfit by adding trees: more $B$ only pushes the estimate down toward the $\rho\sigma^2$ floor, never up.

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
