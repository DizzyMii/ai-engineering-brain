---
tags: [concept, domain/classical-ml, level/core]
aliases: [GBM, GBDT, gradient boosted trees, boosting, gradient boosting machine]
summary: "Fitting an additive ensemble by gradient descent in function space, sequentially correcting residual errors with shallow trees."
---

# Concept - Gradient Boosting

> Gradient boosting builds a model as a sum of weak learners added one at a time, each trained to correct the errors the current ensemble still makes. It's the mechanism behind the tabular-ML flagships (XGBoost, LightGBM, CatBoost), and why "just gradient-boost it" is still a defensible first move on structured data a decade after it started winning competitions.

## The mechanism

Friedman (2001, *Greedy Function Approximation: A Gradient Boosting Machine*) recast boosting as gradient descent in **function space** instead of parameter space. The model is an additive sum of weak learners:

$$F_m(x) = F_{m-1}(x) + \nu \cdot h_m(x)$$

Each new weak learner $h_m$, almost always a shallow [[Concept - Decision Trees|decision tree]], is fit to the **negative gradient** of the loss with respect to the current predictions at each training point, not to the original targets $y$. These are the pseudo-residuals: $r_i = -\left[\frac{\partial L(y_i, F(x_i))}{\partial F(x_i)}\right]_{F=F_{m-1}}$. For squared-error loss that's the ordinary residual $y_i - F_{m-1}(x_i)$. For log loss (binary classification) it's $y_i - p_i$, the gap between the true label and the predicted probability. Plug in any differentiable loss and you get the right target automatically. That's why GBM handles regression, classification, ranking and quantile loss with the same machinery, and why it dominates heterogeneous, mixed-signal tabular problems where the choice of loss matters.

$\nu$, the shrinkage or learning rate (typically 0.01–0.3), scales how much of each tree's correction gets applied. It regularizes by trading trees for accuracy. A smaller $\nu$ needs more rounds to reach the same training loss but generally generalizes better, since no single tree can overcorrect and lock in a quirk of the current residuals. The $\nu$-vs-$M$ (number of trees) tradeoff is the first knob everyone tunes.

Stochastic gradient boosting (Friedman, 2002) adds row subsampling inside the sequential loop, fitting each tree to a random 50–80% of rows. You get bagging-style regularization and a speed win in an algorithm that's inherently sequential and so harder to parallelize than [[Concept - Bagging and Random Forests|bagging]].

```
F0(x) = argmin_c sum_i L(y_i, c)          # e.g. mean(y) for squared loss
for m in 1..M:
    r_i = -dL(y_i, F_{m-1}(x_i)) / dF_{m-1}(x_i)     # pseudo-residuals
    h_m = fit_shallow_tree(X, r)                      # weak learner on the gradient
    F_m(x) = F_{m-1}(x) + nu * h_m(x)
return F_M
```

The weak learners are shallow trees, depth 3–8 or 31–255 leaves in leaf-wise implementations, and each one is deliberately underfit. AdaBoost (Freund & Schapire, 1997) is the historical ancestor and can be shown to be the special case of this framework under exponential loss. Its margin theory (larger margins on training examples go with better generalization, even after training error hits zero) is the classical explanation for why boosting resists overfitting far longer than intuition says it should.

## In practice

The defining contrast with bagging is **what gets reduced, and how**. Boosting reduces **bias** through sequential error correction: each tree patches what the ensemble still gets wrong. Bagging reduces **variance** by averaging independently trained, parallel trees over resampled data (see [[Concept - Bagging and Random Forests]]). Everything else follows. Boosting is inherently sequential (tree $m$ needs tree $m-1$'s residuals), so it's harder to parallelize across trees, though split finding within a tree parallelizes fine. Bagging is embarrassingly parallel across trees but has a lower accuracy ceiling.

If you come from deep learning, think of it this way. [[Concept - Backpropagation|Backprop]] takes a gradient step in *parameter space* (nudge the weights). Gradient boosting takes a gradient step in *function space* (append a whole new function). Both move in the direction that reduces loss fastest, but the thing being updated is different, which is why boosting's building blocks (trees) don't have to be differentiable. Only the loss does.

In production, gradient boosting is almost never used bare. It's XGBoost, LightGBM or CatBoost, each adding systems engineering (histogram binning, second-order Newton steps, categorical handling) on top of this loop; [[Breakdown - XGBoost]] and [[Breakdown - LightGBM]] have the specifics.

## Failure modes

Gradient boosting **does** overfit as trees accumulate, unlike random forests. There's no "more trees can't hurt" guarantee, because each new tree chases the residuals of an ensemble that may already be fitting noise. Early stopping on a held-out metric isn't optional. It's what sets the right number of trees, and skipping it is the most common way to ship an overfit boosted model. [[Gotchas - Gradient Boosting in Practice]] has the full catalog (leakage, categorical traps, miscalibration) that makes this worse.

## The non-obvious

The bias/variance split between boosting and bagging decides the whole tuning philosophy. With random forests you tune for "enough trees, don't overfit the split search" and it's hard to go far wrong. With gradient boosting every hyperparameter (learning rate, depth, number of rounds, subsampling) is a bias-variance dial you have to balance, because left unchecked the algorithm keeps pushing training error toward zero indefinitely. People who carry over the "random forests are basically tuning-free" intuition get burned. A GBM on default hyperparameters with no early stopping will often *look* fine on a quick train/test split, then underperform badly under real distribution shift, because it has fit residual noise the validation split didn't happen to expose.

## Connections
- [[Concept - Decision Trees]] — the weak learner every boosting round fits to the current pseudo-residuals.
- [[Concept - Bagging and Random Forests]] — the parallel, variance-reducing counterpart; the bias/variance contrast is the core mental model for choosing between them.
- [[Breakdown - XGBoost]] — the system that turned this algorithm into a fast, regularized, production-grade implementation.
- [[Breakdown - LightGBM]] — the histogram-based, leaf-wise implementation that traded some of XGBoost's exactness for speed on large data.
- [[Concept - Backpropagation]] — the parameter-space analog to boosting's function-space gradient step, useful as a bridge concept for deep learning engineers.
- [[Concept - Entropy and Cross-Entropy]] — log loss, whose gradient (y - p) is the pseudo-residual boosting fits to in classification.
- [[Decision - Deep Learning vs Gradient Boosting for Tabular Data]] — the build decision this mechanism underlies for structured-data problems.
- [[Gotchas - Gradient Boosting in Practice]] — the pitfalls (leakage, miscalibration, non-determinism) that show up once this mechanism hits a real pipeline.
- [[Concept - Knowledge Distillation]] — another technique that builds a model by fitting to a signal derived from an existing predictor, worth contrasting with fitting to residuals.

## Sources
- Friedman (2001) — *Greedy Function Approximation: A Gradient Boosting Machine*. The functional-gradient-descent formalization that defines the algorithm.
- Friedman (2002) — *Stochastic Gradient Boosting*. Adds row subsampling for regularization and speed.
- Freund & Schapire (1997) — *A Decision-Theoretic Generalization of On-Line Learning and an Application to Boosting*. AdaBoost, the exponential-loss ancestor and margin-theory foundation.
