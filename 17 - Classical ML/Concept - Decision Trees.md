---
tags: [concept, domain/classical-ml, level/surface]
aliases: [CART, decision tree]
summary: "Recursive axis-aligned partitioning that greedily maximizes impurity decrease; the atomic, high-variance learner every tree ensemble is built from."
---

# Concept - Decision Trees

> A decision tree is a piecewise-constant function built by greedily and recursively partitioning feature space along single-feature thresholds to maximize a purity gain at each step. It is the atomic learner beneath random forests, gradient boosting, and every serious tabular ML system — understanding one tree's mechanics and failure modes is the prerequisite for understanding why *ensembles* of them dominate structured data.

## The mechanism

At each node, given a subset of rows, the algorithm searches over every feature $j$ and every candidate threshold $t$ for the split maximizing the decrease in impurity:

$$\Delta I = I(\text{parent}) - \left(\frac{n_L}{n} I(\text{left}) + \frac{n_R}{n} I(\text{right})\right)$$

For classification, impurity is Gini impurity $I_{gini} = 1 - \sum_k p_k^2$ or entropy $I_{ent} = -\sum_k p_k \log p_k$ (see [[Concept - Entropy and Cross-Entropy]]). Gini is cheaper to compute — no logarithm — and empirically produces near-identical splits to entropy, which is why most production libraries default to it. Regression trees split on variance / SSE reduction instead: find the threshold that best separates rows into two groups, each with low internal variance around its own mean.

This is a greedy, one-split-at-a-time search, and it is provably suboptimal: constructing the *globally* optimal decision tree is NP-hard (Hyafil & Rivest, 1976), so every practical tree learner is a heuristic that can get locked into a bad early split it never revisits.

CART (Breiman et al., 1984) is the canonical formalization: strictly binary splits, plus cost-complexity pruning. Pruning fixes overfitting by growing a large tree and trimming it back against a penalized objective

$$R_\alpha(T) = R(T) + \alpha |T|$$

where $R(T)$ is training error and $|T|$ the leaf count; sweeping $\alpha$ produces a nested sequence of subtrees, and the best is chosen by cross-validation. CART also introduced *surrogate splits*: when the primary split feature is missing for a row, fall back to the next-most-correlated feature's split — the classical answer to missing data that [[Breakdown - XGBoost]]'s learned default-direction later replaced with something faster. Contrast this with ID3/C4.5 (Quinlan), which historically used multiway categorical splits and information-gain *ratio* specifically to counteract information gain's bias toward high-cardinality features.

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

Because splits only compare values on either side of a threshold, trees are invariant to any monotone transform of a feature (log, rank, min-max) and need no feature scaling — a real practical edge over linear models. But that same rank-based mechanism biases split selection toward high-cardinality and continuous features, which offer more candidate thresholds and are more likely to find a spuriously good one by chance.

## In practice

A trained tree partitions $\mathbb{R}^p$ into axis-aligned rectangular regions, one per leaf, predicting a constant — majority class or mean target — within each:

```
        [age < 30?]
        /         \
      yes          no
      /              \
 [income<50k?]     [credit>700?]
   /      \           /      \
 deny   approve    approve   deny
```

This piecewise-constant structure is the whole story of where trees win and lose. Real production trees are shallow leaves inside an ensemble ([[Concept - Gradient Boosting]], [[Concept - Bagging and Random Forests]]) — a single unconstrained tree is essentially never shipped alone, because it overfits catastrophically and its structure is unstable to the exact training sample it saw.

## Failure modes

- **Unbounded depth memorizes noise.** A tree grown to purity on every leaf hits 100% training accuracy by definition — a lookup table, not a model. Detect via a large train/validation gap; fix with `max_depth`, `min_samples_leaf`, or cost-complexity pruning.
- **Class imbalance skews splits.** Impurity-decrease splitting is dominated by the majority class; a rare class can vanish from every split decision entirely. Detect by checking per-class recall, never aggregate accuracy (see [[Concept - Learning from Imbalanced Data]]).
- **Instability.** Because the split search is greedy, perturbing a handful of training rows can flip which feature wins the very first split — and a different root reshapes the entire downstream tree. This is not numerical wobble; a single tree's structure is nearly non-reproducible across bootstrap resamples of the same data. Detect by refitting on resampled data and diffing tree structure or predictions; the fix is not to stabilize the tree but to average many unstable ones.
- **Cannot extrapolate.** A leaf's prediction is a constant fit to whichever training rows landed there; outside the observed range of a feature the prediction stays flat instead of continuing a trend. This silently breaks any numeric feature — price, timestamp, sensor reading — that drifts past its training range in production.

## The non-obvious

The instability failure mode is not a bug to be engineered away — it is the entire reason ensembling works. A high-variance, low-bias tree is exactly the raw material bagging wants: average many trees whose *errors* are only loosely correlated, and the variance cancels while the low bias survives. If single decision trees were stable, random forests would have nothing to average away. This reframes "instability" from defect to designed-for property once you know the tree is destined for an ensemble — but it also means a lone tree kept for interpretability is trustworthy for *showing the logic path* and untrustworthy for *quantitative prediction*.

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
