---
tags: [concept, domain/classical-ml, level/frontier]
aliases: [conformal prediction, split conformal, inductive conformal, CQR, APS, RAPS, conformalized quantile regression]
summary: "Distribution-free prediction sets with finite-sample coverage that wrap any trained model."
---

# Concept - Conformal Prediction

> **Hook:** Conformal prediction wraps *any* already-trained model — a random forest, a neural net, an LLM — and turns its point predictions into **prediction sets or intervals with a guaranteed coverage rate**: choose α = 0.1 and the set contains the true label at least 90% of the time. The guarantee is finite-sample (not asymptotic), distribution-free (no Gaussian assumption, no well-specified model), and model-agnostic. It is the closest thing classical ML has to a free lunch, and it is the natural complement to [[Concept - Probability Calibration|probability calibration]]: calibration fixes what a score *means*, conformal puts an honest set *around the output*.

## The mechanism

Take **split (inductive) conformal**, the version everyone actually uses. Hold out a calibration set of `n` labeled points that the model never trained on. Define a **nonconformity score** `s(x, y)` — how badly a candidate label `y` fits the model's opinion about `x`:

- Regression: `s = |y − ŷ(x)|` (absolute residual).
- Classification: `s = 1 − p̂_y(x)` (one minus the softmax probability the model assigned to label `y`).

Compute the scores $s_1, \dots, s_n$ on the calibration set. Then take the empirical quantile

$$\hat{q} = \text{the } \big\lceil (n+1)(1-\alpha) \big\rceil \text{-th smallest of } \{s_1, \dots, s_n\}.$$

At test time, output the set of every label whose score falls under that threshold:

$$C(x) = \{\, y : s(x, y) \le \hat{q} \,\}.$$

For regression that yields the interval $\hat{y}(x) \pm \hat{q}$; for classification it yields the set of classes whose predicted probability exceeds $1 - \hat{q}$. The theorem (Vovk, Gammerman & Shafer; see the Angelopoulos & Bates 2021 tutorial for the modern treatment) is that if the calibration and test points are **exchangeable**,

$$1 - \alpha \;\le\; P\big(Y \in C(X)\big) \;\le\; 1 - \alpha + \tfrac{1}{n+1}.$$

The lower bound is the promise; the upper bound says you don't massively over-cover if `n` is reasonable. The `(n+1)` and the ceiling are not cosmetic — they are exactly what make the bound hold in finite samples rather than in the limit. The proof is a one-line symmetry argument: under exchangeability the test score is equally likely to land in any rank position among the `n+1` scores, so the probability it exceeds the `⌈(n+1)(1−α)⌉`-th is at most α.

## In practice

- **Cost is one held-out set and one quantile.** No retraining, no gradient access. A production recipe: reserve 1,000–5,000 calibration points, compute scores once, cache `q̂`, and you have coverage on every future prediction. It composes with anything — wrap a [[Concept - Gradient Boosting|gradient-boosted]] model or a [[Breakdown - TabPFN|TabPFN]] posterior identically.
- **Adaptive classification sets** are the version worth shipping. Plain `1 − p̂_y` sets can be a fixed size; **APS** (Adaptive Prediction Sets) and **RAPS** (Regularized APS; Romano et al., Angelopoulos et al.) accumulate sorted class probabilities so the set *grows on hard inputs and shrinks on easy ones*. A large set is then a built-in, calibrated "I don't know" — vastly better than a confident wrong top-1. RAPS adds a regularizer to stop the set from ballooning on many-class problems.
- **Conformalized Quantile Regression (CQR; Romano, Patterson & Candès 2019)** fixes conformal regression's ugliest default. Naive split conformal gives a *constant-width* interval `±q̂` everywhere, which is too wide where the model is confident and too narrow where it isn't. CQR conformalizes a pair of quantile-regression models instead, producing **adaptive-width** intervals that widen exactly where the data is noisy.
- **Deployment reality:** coverage is only as valid as the exchangeability assumption. Recompute `q̂` on a fresh calibration window whenever the input distribution moves — see [[Concept - Production Monitoring and Drift Detection|drift monitoring]] — and log realized coverage as a first-class metric.

## Failure modes

- **Marginal coverage is not conditional coverage — the number-one misread.** The guarantee holds *on average over the whole population*, not per subgroup. A classifier can satisfy 90% marginal coverage while systematically **under-covering a minority class** and over-covering the majority — the exact failure mode that also plagues [[Concept - Learning from Imbalanced Data|imbalanced problems]]. Detection: stratify realized coverage by class/segment. Fix: **Mondrian (class-conditional) conformal** runs a separate calibration quantile per group, restoring per-group coverage at the cost of needing enough calibration points in each.
- **Exchangeability breaks under distribution shift, which voids the guarantee entirely.** This is not a soft degradation — the coverage theorem simply no longer applies. Time series are the canonical violator: yesterday and tomorrow are not exchangeable. Detection: realized coverage drifts away from `1 − α` over time. Remedies are the active research frontier — **weighted conformal** (reweight calibration points by a likelihood ratio to the test distribution) and **Adaptive Conformal Inference** (Gibbs & Candès 2021), which updates α online to chase the target coverage as the series evolves. The leakage that quietly destroys these guarantees on temporal data is the subject of [[Concept - Time Series Cross-Validation and Leakage]].
- **Tiny calibration sets give noisy quantiles.** With `n = 50`, the `1/(n+1)` slack is ~2% and `q̂` itself is high-variance; realized coverage wobbles. Use hundreds to thousands of calibration points, or cross-conformal / jackknife+ variants that reuse data more efficiently.
- **A degenerate model still conforms.** Conformal guarantees *coverage*, not *usefulness*: a set containing all classes has perfect coverage and zero information, just as predicting the base rate is perfectly calibrated and useless. Track average set size (efficiency) alongside coverage, or you'll ship guaranteed-but-vacuous sets.

## The non-obvious

Conformal prediction decouples **validity** from **accuracy**. A terrible model still gets *valid* coverage — it simply pays with enormous sets or intervals. This is the property people miss: conformal never makes your model better, it makes your model *honest about how bad it is*. The set size is the diagnostic. If wrapping a model produces huge sets, that is not a conformal failure; it is conformal correctly reporting that the underlying model is uncertain, and the fix is a better model or better features, not a different wrapper. This is also why it is spreading into LLM evaluation and serving: you can conformalize an [[Concept - LLM-as-Judge|LLM judge's]] scores or wrap a model's answers into a guaranteed-coverage candidate set, trading a bounded [[Concept - Cost Engineering for LLM Applications|extra-call budget]] for a hard reliability contract — which is exactly what regulated deployments ask for and vibes-based confidence can't provide.

## Connections
- [[Concept - Probability Calibration]] — the complementary tool: calibration makes scores mean what they say; conformal puts a coverage-guaranteed set around outputs. Use both.
- [[Concept - Statistical Rigor in Model Evaluation]] — realized coverage and set size are the metrics that keep a conformal deployment honest, in the same spirit as proper evaluation discipline.
- [[Concept - Learning from Imbalanced Data]] — marginal-vs-conditional coverage fails exactly on rare classes; the imbalance and conformal pitfalls are the same underlying trap.
- [[Concept - Time Series Cross-Validation and Leakage]] — temporal data violates exchangeability, the assumption the whole guarantee rests on; the deeper leakage story lives there.
- [[Concept - LLM-as-Judge]] — conformalizing a judge's scores turns fuzzy confidence into guaranteed-coverage decisions, a growing use case.
- [[Concept - Cost Engineering for LLM Applications]] — wrapping LLM outputs in coverage sets trades a bounded compute budget for a hard reliability contract.
- [[Concept - Production Monitoring and Drift Detection]] — realized coverage is a drift signal; when it slips from 1−α the input distribution has moved and the calibration set must be refreshed.
- [[Breakdown - TabPFN]] — a natural base model to wrap: conformal supplies the finite-sample guarantee its amortized posterior doesn't formally promise.
- [[Concept - Gradient Boosting]] — the most common base learner conformal wraps in tabular pipelines; scores plug straight in with no retraining.

## Sources
- Vovk, Gammerman & Shafer (2005) — *Algorithmic Learning in a Random World.* The foundational text on conformal prediction and exchangeability.
- Angelopoulos & Bates (2021) — *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification.* The standard practitioner tutorial; split conformal, APS, RAPS.
- Romano, Patterson & Candès (2019) — *Conformalized Quantile Regression.* Adaptive-width intervals for regression.
- Gibbs & Candès (2021) — *Adaptive Conformal Inference Under Distribution Shift.* Online α-adjustment for non-exchangeable/time-series data.
