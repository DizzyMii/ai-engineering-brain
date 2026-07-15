---
tags: [concept, domain/classical-ml, level/core]
aliases: [GBM, GBDT, gradient boosted trees, boosting, gradient boosting machine]
summary: "Fitting an additive ensemble by gradient descent in function space, sequentially correcting residual errors with shallow trees."
---

# Concept - Gradient Boosting

> Gradient boosting builds a model as a sum of weak learners added one at a time, where each new learner is trained to correct the errors the current ensemble is still making. It is the mechanism behind the tabular-ML flagship — XGBoost, LightGBM, CatBoost — and the reason "just gradient-boost it" remains a defensible first move on structured data a decade after it started winning competitions.

## The mechanism

Friedman (2001, *Greedy Function Approximation: A Gradient Boosting Machine*) reframed boosting as gradient descent, not in parameter space, but in **function space**. The model is an additive sum of weak learners:

$$F_m(x) = F_{m-1}(x) + \nu \cdot h_m(x)$$

where $h_m$ is a new weak learner — almost always a shallow [[Concept - Decision Trees|decision tree]] — fit not to the original targets $y$, but to the **negative gradient** of the loss with respect to the current predictions, evaluated at each training point. These are called pseudo-residuals: $r_i = -\left[\frac{\partial L(y_i, F(x_i))}{\partial F(x_i)}\right]_{F=F_{m-1}}$. For squared-error loss, the pseudo-residual reduces to the ordinary residual $y_i - F_{m-1}(x_i)$; for log loss (binary classification) it becomes $y_i - p_i$, the gap between the true label and the predicted probability. This "plug in any differentiable loss and get the right target automatically" generality is exactly why GBM handles regression, classification, ranking, and quantile loss with the same machinery, and why it dominates heterogeneous, mixed-signal tabular problems where a hand-picked loss matters.

$\nu$, the shrinkage or learning rate (typically 0.01–0.3), scales how much of each new tree's correction is actually applied. It regularizes by trading trees for accuracy: a smaller $\nu$ needs more boosting rounds to reach the same training loss, but generally generalizes better, because no single tree is allowed to overcorrect and lock in an idiosyncrasy of the current residuals. This $\nu$-vs-$M$ (number of trees) tradeoff is the first knob every practitioner tunes.

Stochastic gradient boosting (Friedman, 2002) adds row subsampling — fitting each tree to a random 50–80% of rows — inside the otherwise-sequential boosting loop. This injects bagging-style regularization and a speed win into an algorithm that is inherently sequential and therefore harder to parallelize than [[Concept - Bagging and Random Forests|bagging]].

```
F0(x) = argmin_c sum_i L(y_i, c)          # e.g. mean(y) for squared loss
for m in 1..M:
    r_i = -dL(y_i, F_{m-1}(x_i)) / dF_{m-1}(x_i)     # pseudo-residuals
    h_m = fit_shallow_tree(X, r)                      # weak learner on the gradient
    F_m(x) = F_{m-1}(x) + nu * h_m(x)
return F_M
```

The weak learners themselves are shallow trees — depth 3–8, or 31–255 leaves in leaf-wise implementations — deliberately underfit individually. AdaBoost (Freund & Schapire, 1997) is the historical ancestor: it can be shown to be the special case of this framework under exponential loss, and its margin theory (larger margins on training examples correlate with better generalization even as training error hits zero) is the classical explanation for why boosting resists overfitting far longer than intuition suggests it should.

## In practice

The defining contrast with bagging is **what is reduced, and how**: boosting reduces **bias** through sequential error correction — each tree is a deliberate patch on what the ensemble still gets wrong — while bagging reduces **variance** by averaging independently-trained, parallel trees over resampled data (see [[Concept - Bagging and Random Forests]]). That difference cascades into everything else: boosting is inherently sequential (tree $m$ needs tree $m-1$'s residuals) and thus harder to parallelize across trees, though split-finding within a tree parallelizes fine; bagging is embarrassingly parallel across trees but has a lower accuracy ceiling.

For an engineer coming from deep learning, the useful mental model is: [[Concept - Backpropagation|backprop]] takes a gradient step in *parameter space* (nudge the weights); gradient boosting takes a gradient step in *function space* (append an entirely new function). Both are, at bottom, "move in the direction that reduces loss fastest" — but the object being updated is fundamentally different, and that's why boosting's building blocks (trees) don't need to be differentiable themselves; only the loss does.

In production, gradient boosting is almost never used bare — it's XGBoost, LightGBM, or CatBoost, each of which adds systems engineering (histogram binning, second-order Newton steps, categorical handling) on top of this core loop; see [[Breakdown - XGBoost]] and [[Breakdown - LightGBM]] for the specifics.

## Failure modes

Unlike random forests, gradient boosting **does** overfit as trees accumulate — there is no "more trees can't hurt" guarantee the way there is for bagging, because each new tree is chasing the residuals of an ensemble that may already be fitting noise. Early stopping on a held-out metric is not an optional nicety here; it is the mechanism that determines the correct number of trees, and skipping it is the single most common way to ship an overfit boosted model. Watch [[Gotchas - Gradient Boosting in Practice]] for the full catalog — leakage, categorical traps, miscalibration — that compounds this.

## The non-obvious

The bias/variance split between boosting and bagging is not just a taxonomy — it dictates the entire tuning philosophy. With random forests, you tune for "enough trees, don't overfit the split search" and mostly can't go too far wrong; with gradient boosting, every hyperparameter (learning rate, tree depth, number of rounds, subsampling) is a bias-variance dial you must actively balance, because the algorithm's default behavior, run unchecked, is to keep reducing training error toward zero indefinitely. Practitioners who transfer their "random forests are basically tuning-free" intuition to gradient boosting without adjusting for this get burned — a GBM with default hyperparameters and no early stopping will often *look* fine on a quick train/test split and then underperform badly under real distribution shift, because it has quietly fit residual noise the validation split happened not to expose.

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
