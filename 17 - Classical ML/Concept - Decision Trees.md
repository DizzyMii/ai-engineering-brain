---
tags: [concept, domain/classical-ml, level/surface]
aliases: [CART, decision tree]
summary: "Recursive axis-aligned partitioning that greedily maximizes impurity decrease; the atomic, high-variance learner every tree ensemble is built from."
---

# Concept - Decision Trees

> A decision tree is a piecewise-constant function, built by greedily and recursively partitioning feature space on single-feature thresholds so each step maximizes a purity gain. It's the base learner under random forests, gradient boosting and every serious tabular ML system. You need one tree's mechanics and failure modes before you can see why *ensembles* of them dominate structured data.

## The mechanism

At each node, given a subset of rows, the algorithm searches every feature $j$ and every candidate threshold $t$ for the split with the largest impurity decrease:

$$\Delta I = I(\text{parent}) - \left(\frac{n_L}{n} I(\text{left}) + \frac{n_R}{n} I(\text{right})\right)$$

For classification, impurity is Gini $I_{gini} = 1 - \sum_k p_k^2$ or entropy $I_{ent} = -\sum_k p_k \log p_k$ (see [[Concept - Entropy and Cross-Entropy]]). Gini skips the logarithm, so it's cheaper, and empirically it picks nearly the same splits as entropy; most production libraries default to it. Regression trees split on variance/SSE reduction: find the threshold that best separates rows into two groups, each with low variance around its own mean.

The search is greedy, one split at a time, and provably suboptimal. Building the *globally* optimal tree is NP-hard (Hyafil & Rivest, 1976), so every practical tree learner is a heuristic that can lock in a bad early split and never revisit it.

CART (Breiman et al., 1984) is the canonical formalization: strictly binary splits plus cost-complexity pruning. Pruning handles overfitting by growing a large tree and trimming it back against a penalized objective

$$R_\alpha(T) = R(T) + \alpha |T|$$

where $R(T)$ is training error and $|T|$ the leaf count. Sweeping $\alpha$ gives a nested sequence of subtrees, and cross-validation picks the best. CART also introduced *surrogate splits*: if a row is missing the primary split feature, fall back to the split on the next most correlated feature. That was the classical answer to missing data, until [[Breakdown - XGBoost]]'s learned default direction replaced it with something faster. ID3/C4.5 (Quinlan) went a different way, with multiway categorical splits and information-gain *ratio* to counter information gain's bias toward high-cardinality features.

```
Split(rows):
    if stopping_condition(rows): return Leaf(rows)
    best_gain = 0
    for feature j in features:
        for threshold t in candidate_thresholds(rows, j):
            gain = impurity(rows) - weighted_impurity(split(rows, j, t))
            if gain > best_gain: best_gain, best_j, best_t = gain, j, t
    left, right = split(rows, best_j, best_t)
    return Node(best_j, best_t, Split(left), Split(right))
```

Splits only compare values on either side of a threshold, so trees are invariant to any monotone transform of a feature (log, rank, min-max) and need no feature scaling. That's a real practical edge over linear models. The same rank-based mechanism biases split selection toward high-cardinality and continuous features, though: they offer more candidate thresholds and are more likely to find a spuriously good one by chance.

## In practice

A trained tree partitions $\mathbb{R}^p$ into axis-aligned rectangles, one per leaf, and predicts a constant (majority class or mean target) inside each:

```
        [age < 30?]
        /         \
      yes          no
      /              \
 [income<50k?]     [credit>700?]
   /      \           /      \
 deny   approve    approve   deny
```

That piecewise-constant structure explains where trees win and where they lose. In production, trees are shallow members of an ensemble ([[Concept - Gradient Boosting]], [[Concept - Bagging and Random Forests]]). A single unconstrained tree is essentially never shipped alone: it overfits catastrophically, and its structure depends heavily on the exact sample it saw.

## Failure modes

- **Unbounded depth memorizes noise.** Grow a tree to purity on every leaf and it hits 100% training accuracy by definition. That's a lookup table, not a model. You'll see a large train/validation gap; fix it with `max_depth`, `min_samples_leaf` or cost-complexity pruning.
- **Class imbalance skews splits.** The majority class dominates impurity-decrease splitting, and a rare class can drop out of every split decision. Check per-class recall, never aggregate accuracy (see [[Concept - Learning from Imbalanced Data]]).
- **Instability.** Because the search is greedy, perturbing a handful of training rows can flip which feature wins the first split, and a different root reshapes the whole tree below it. It isn't numerical wobble. A single tree's structure is close to non-reproducible across bootstrap resamples of the same data. Refit on resampled data and diff structure or predictions to see it. The fix is to average many unstable trees, not to stabilize one.
- **Cannot extrapolate.** A leaf predicts a constant fit to whichever training rows landed in it, so outside a feature's observed range the prediction goes flat instead of following the trend. Any numeric feature that drifts past its training range in production (price, timestamp, sensor reading) breaks without warning.

## The non-obvious

Instability isn't a bug to engineer away. It's the reason ensembling works. A high-variance, low-bias tree is the raw material bagging wants: average many trees whose *errors* are only loosely correlated, and the variance cancels while the low bias stays. If single trees were stable, random forests would have nothing to average away. Once you know a tree is headed for an ensemble, instability is a property you're counting on. It also means a lone tree kept for interpretability is trustworthy for *showing the logic path* and untrustworthy for *quantitative prediction*.

## Connections
- [[Concept - Entropy and Cross-Entropy]] — entropy is one of the two standard impurity measures a split search maximizes the decrease of.
- [[Concept - Bagging and Random Forests]] — exploits exactly the instability described above by averaging many trees trained on bootstrap resamples.
- [[Concept - Gradient Boosting]] — uses shallow trees as the weak learner fit sequentially to pseudo-residuals.
- [[Decision - Deep Learning vs Gradient Boosting for Tabular Data]] — the axis-aligned, piecewise-constant inductive bias here is the mechanistic reason tree ensembles beat neural nets on tabular data.
- [[Concept - Backpropagation]] — the contrasting parameter-space gradient method neural nets use, versus a tree's greedy structural search.
- [[Gotchas - Gradient Boosting in Practice]] — most categorical/leakage/extrapolation pitfalls in boosted trees trace back to single-tree split mechanics.
- [[Concept - Clustering and Dimensionality Reduction]] — an alternative, unsupervised way to partition feature space, worth contrasting with a tree's supervised axis-aligned partitioning.
- [[Breakdown - XGBoost]] — replaces CART's surrogate-split missing-value handling with a faster learned default direction.
- [[Concept - Learning from Imbalanced Data]] — impurity-based splitting is dominated by the majority class, so class skew directly degrades a tree's split quality.

## Sources
- Breiman, Friedman, Olshen, Stone (1984) — *Classification and Regression Trees*. Defines CART: binary splits, Gini impurity, cost-complexity pruning, surrogate splits.
- Hyafil & Rivest (1976) — *Constructing Optimal Binary Decision Trees is NP-Complete*. The theoretical reason every tree learner is a greedy heuristic.
- Quinlan — ID3/C4.5. The multiway-split, information-gain-ratio lineage that CART's binary approach superseded in most production libraries.
