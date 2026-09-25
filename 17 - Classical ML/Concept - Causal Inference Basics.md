---
tags: [concept, domain/classical-ml, level/advanced]
aliases: [causal ML, treatment effect estimation, ATE, CATE, uplift modeling]
summary: "Estimating what an intervention causes, not just what correlates with it, when you cannot randomize — and why predictive ML alone can't do this."
---

> Predictive ML answers "what will happen." Causal inference answers "what would happen if I intervened." The two questions need different math and different data, and engineers conflate them constantly, shipping a feature-importance chart as if it were an intervention recommendation. This note covers the engineering-relevant core: potential outcomes, confounding, and the estimators you reach for when an A/B test isn't possible (propensity scores, difference-in-differences, instrumental variables, uplift models).

## The mechanism

The **potential outcomes** framework (the Rubin causal model) states the problem precisely. For unit $i$, $Y_i(1)$ is the outcome under treatment and $Y_i(0)$ the outcome under control. The individual effect $Y_i(1) - Y_i(0)$ can never be observed, because you only ever see one of the two counterfactuals for a given unit. So causal inference estimates averages, most commonly the average treatment effect $\text{ATE} = \mathbb{E}[Y(1) - Y(0)]$.

**Confounding** is the formal reason correlation isn't causation. A variable that affects both treatment assignment and the outcome opens a spurious statistical path between them. Pearl's backdoor criterion: adjust for a set of variables that blocks every backdoor path from treatment to outcome. That does *not* mean adjusting for every variable you have. Two mistakes are common:

```
Confounder (DO adjust):        Collider (do NOT adjust):      Mediator (do NOT adjust for total effect):
      Z                              T → C ← Y                       T → M → Y
     ↙ ↘
    T    Y
```

- **Adjusting for a collider** (a variable caused by *both* treatment and outcome) opens an association path that wasn't there before. Conditioning on it adds bias.
- **Adjusting for a mediator** (a variable on the causal path from treatment to outcome) blocks the effect you're trying to measure.

**Propensity scores** $e(x) = P(T=1 \mid x)$ (Rosenbaum & Rubin, 1983) compress the confounders into one balancing score you can use for matching, stratification, or inverse-propensity weighting (treated units weighted by $1/e(x)$, controls by $1/(1-e(x))$). Two assumptions are required: overlap/positivity ($0 < e(x) < 1$ everywhere), and unconfoundedness, meaning you've measured all confounders. The data alone can't test the second one. Doubly-robust estimation (AIPW) combines an outcome model $\hat{\mu}$ with a propensity model $\hat{e}$:

$$\hat{\tau}_{\text{AIPW}} = \frac{1}{n}\sum_i \left[\hat{\mu}_1(x_i) - \hat{\mu}_0(x_i) + \frac{T_i(Y_i - \hat{\mu}_1(x_i))}{\hat{e}(x_i)} - \frac{(1-T_i)(Y_i - \hat{\mu}_0(x_i))}{1-\hat{e}(x_i)}\right]$$

The estimate stays consistent if *either* $\hat{\mu}$ or $\hat{e}$ is correctly specified. You get two chances to get it right.

When you can't measure confounders at all, three quasi-experimental designs stand in for randomization:

- **Difference-in-differences** compares treated and control units before and after treatment, relying on parallel trends (without treatment, both groups would have moved together). Naive two-way fixed effects is biased when adoption timing is staggered across units. It wasn't properly diagnosed until Goodman-Bacon (2021), and the fix is still working its way through applied work.
- **Instrumental variables** use an exogenous instrument that affects treatment but has no direct path to the outcome (relevance + exclusion), estimated with two-stage least squares.
- **Regression discontinuity** uses a hard cutoff (a score threshold, an age limit) as a source of local, as-if-random assignment right at the boundary.

Prediction and causal inference split furthest for ML engineers on **heterogeneous treatment effects**: the conditional average treatment effect $\text{CATE}(x) = \mathbb{E}[Y(1)-Y(0) \mid X=x]$, i.e. uplift modeling. The question is "who should get it," not "does this treatment work." S-, T- and X-learners (Künzel et al., 2019) are meta-algorithms that plug in any standard regressor. The S-learner fits one model with treatment as a feature, the T-learner fits a separate model per arm, and the X-learner cross-imputes to correct for unequal arm sizes. Causal forests (Wager & Athey, 2018) extend [[Concept - Bagging and Random Forests]] with **honest splitting**: the subsample that chooses a tree's splits is disjoint from the one that estimates the leaf's treatment effect, so a leaf never uses the same data to decide its shape and to report its answer. It's the direct analogue of the leakage discipline gradient-boosting pipelines need for target encoding. Evaluate CATE estimators with Qini and uplift curves, never plain accuracy. Accuracy answers a prediction question, and targeting is a different one.

## In practice

The industrial use for uplift/CATE models is targeting. Marketing wants to know whom a promo will *cause* to buy, as opposed to who merely correlates with buying after getting it. A promo sent to someone who'd have bought anyway wastes margin; the CATE model finds the persuadable segment.

Positivity in practice means checking the overlap of estimated propensity scores between treated and control groups. Where $\hat{e}(x)$ is near 0 or 1, IPW weights blow up and dominate the estimate's variance. A common fix is trimming or clipping propensity scores outside roughly [0.05, 0.95] before weighting.

A lot of observational causal work plugs [[Concept - Gradient Boosting]] or random-forest models in as the outcome/propensity learners, so the tuning discipline from [[Reference - Gradient Boosting Hyperparameters]] applies. But a well-tuned *predictive* model isn't automatically a well-specified *causal* nuisance model. Its CV objective (minimize prediction error) doesn't target unbiased effect estimation.

## Failure modes

- **Adjusting for a collider.** Conditioning on a variable caused by both treatment and outcome creates an association where none existed. A classic case is conditioning on a post-treatment "engagement" metric that both treatment and outcome influence. Detect it by drawing the DAG before choosing covariates.
- **Adjusting for a mediator.** Controlling for a variable on the causal path zeroes out the indirect effect and understates the total effect you wanted. For every covariate, ask: could treatment plausibly cause this?
- **Positivity violations.** Where one arm has near-zero probability in covariate space, IPW weights get extreme and estimates become wildly unstable. Plot the propensity score distribution split by treatment group and look for regions that don't overlap.
- **Naive two-way fixed effects under staggered timing.** Goodman-Bacon (2021) showed that this classic diff-in-diff setup implicitly uses already-treated units as controls for later-treated ones, which can produce negative weights and a biased, even sign-flipped, estimate. Decompose the estimate into its constituent 2x2 comparisons, or switch to a staggered-adoption-robust estimator.
- **Reading feature importance as a causal effect.** A high SHAP or gain importance from a [[Concept - Gradient Boosting]] model says the feature helped *prediction* under the training distribution's correlations. It says nothing about whether intervening on it would change the outcome. Simpson's paradox is the sharpest form of the trap. The classic real case is kidney-stone treatment success rates (Charig et al., 1986): one treatment has the higher overall success rate, but the *other* wins within both the small-stone and large-stone subgroups, because physicians preferred the first treatment for easier cases.

## The non-obvious

"Two chances to get it right" is the practical reason doubly-robust estimators became the default over plain IPW or plain outcome regression. Teams rarely trust either their propensity model or their outcome model to be perfectly specified, and they don't have to: only one needs to be right for the ATE estimate to stay consistent.

The quieter point is that causal forests' honest splitting is the same discipline as [[Snippet - Leakage-Free Target Encoding]] in a different setting: never let a data point shape the estimator's *structure* and also the *value* it reports for that same point. If you've absorbed leakage discipline for gradient boosting, you already have the right instinct for honest splitting. It's the same bug on a different variable.

## Connections
- [[Concept - Statistical Rigor in Model Evaluation]] — the general framework for trusting an estimate that a causal effect estimate must satisfy just as rigorously as any other statistic.
- [[Concept - Reward Models]] — reward models trained on human preference data are themselves susceptible to confounding between what raters rate highly and what is actually good.
- [[Concept - Gradient Boosting]] — S/T-learners and causal forests routinely reuse tree ensembles as the plug-in outcome or propensity model.
- [[Concept - Bagging and Random Forests]] — causal forests are random forests modified with honest splitting to estimate heterogeneous treatment effects instead of point predictions.
- [[Deep Dive - RLHF End to End]] — RLHF's reward-model-then-policy-optimization pipeline is a live case of conflating "the policy scores higher on the reward model" (correlational) with "the policy is actually better" (causal).
- [[Concept - Learning from Imbalanced Data]] — treatment/control group imbalance produces the same IPW-weight variance blow-up that class imbalance produces for classification metrics.
- [[Concept - Time Series Cross-Validation and Leakage]] — panel-data causal estimators like diff-in-differences are exactly as vulnerable to look-ahead leakage as time series forecasting.
- [[Concept - Conformal Prediction]] — both are model-agnostic frameworks with formal statistical guarantees, but conformal guarantees coverage of an outcome while causal inference guarantees (under assumptions) an unbiased effect — a useful contrast in what "rigorous" means in each case.
- [[Reference - Gradient Boosting Hyperparameters]] — the tuning knobs for the tree ensembles S/T-learners and causal forests commonly reuse as plug-in nuisance models.
- [[Snippet - Leakage-Free Target Encoding]] — the same never-let-a-row-inform-its-own-estimate discipline that causal forests' honest splitting independently reinvents for treatment-effect estimation.

## Sources
- Rubin (1974) — "Estimating Causal Effects of Treatments in Randomized and Nonrandomized Studies." The potential-outcomes formalization.
- Pearl (1995) — "Causal Diagrams for Empirical Research." The backdoor criterion for choosing adjustment sets from a DAG.
- Rosenbaum & Rubin (1983) — "The Central Role of the Propensity Score in Observational Studies for Causal Effects."
- Goodman-Bacon (2021) — "Difference-in-Differences with Variation in Treatment Timing." The bias correction for two-way fixed effects under staggered adoption.
- Künzel, Sekhon, Bickel & Yu (2019) — "Metalearners for Estimating Heterogeneous Treatment Effects" (S-, T-, X-learners).
- Wager & Athey (2018) — "Estimation and Inference of Heterogeneous Treatment Effects using Random Forests." Honest splitting for causal forests.
