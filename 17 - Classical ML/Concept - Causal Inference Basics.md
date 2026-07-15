---
tags: [concept, domain/classical-ml, level/advanced]
aliases: [causal ML, treatment effect estimation, ATE, CATE, uplift modeling]
summary: "Estimating what an intervention causes, not just what correlates with it, when you cannot randomize — and why predictive ML alone can't do this."
---

> Predictive ML answers "what will happen"; causal inference answers "what would happen if I intervened" — and the two questions have different math, different data requirements, and get conflated constantly by engineers who ship a feature-importance chart as if it were an intervention recommendation. This note is the engineering-relevant core: potential outcomes, confounding, and the estimators — propensity scores, difference-in-differences, instrumental variables, uplift models — you reach for when an A/B test isn't possible.

## The mechanism

The **potential outcomes** framework (the Rubin causal model) makes the problem precise: for unit $i$, let $Y_i(1)$ be the outcome under treatment and $Y_i(0)$ the outcome under control. The individual treatment effect $Y_i(1) - Y_i(0)$ is fundamentally unobservable — you only ever see one of the two counterfactuals for any given unit, never both — so causal inference estimates averages instead, most commonly the average treatment effect $\text{ATE} = \mathbb{E}[Y(1) - Y(0)]$.

**Confounding** is the formal reason correlation isn't causation: a variable that affects both treatment assignment and the outcome opens a spurious statistical path between them. Pearl's backdoor criterion says: adjust for a set of variables that blocks every backdoor path from treatment to outcome. Critically, this means *not* adjusting for every available variable indiscriminately — two specific mistakes are common:

```
Confounder (DO adjust):        Collider (do NOT adjust):      Mediator (do NOT adjust for total effect):
      Z                              T → C ← Y                       T → M → Y
     ↙ ↘
    T    Y
```

- **Adjusting for a collider** (a variable caused by *both* treatment and outcome) opens a spurious association path that didn't exist before — conditioning on it induces bias rather than removing it.
- **Adjusting for a mediator** (a variable on the causal pathway from treatment to outcome) blocks the very effect you're trying to measure.

**Propensity scores** $e(x) = P(T=1 \mid x)$ (Rosenbaum & Rubin, 1983) summarize confounders into a single balancing score, usable for matching, stratification, or inverse-propensity weighting (weight treated units by $1/e(x)$, controls by $1/(1-e(x))$). This requires two assumptions: overlap/positivity ($0 < e(x) < 1$ everywhere) and unconfoundedness — that you've measured all confounders, which is untestable from data alone. Doubly-robust estimation (AIPW) combines an outcome model $\hat{\mu}$ with a propensity model $\hat{e}$:

$$\hat{\tau}_{\text{AIPW}} = \frac{1}{n}\sum_i \left[\hat{\mu}_1(x_i) - \hat{\mu}_0(x_i) + \frac{T_i(Y_i - \hat{\mu}_1(x_i))}{\hat{e}(x_i)} - \frac{(1-T_i)(Y_i - \hat{\mu}_0(x_i))}{1-\hat{e}(x_i)}\right]$$

The point of this construction is that the estimate stays consistent if *either* $\hat{\mu}$ or $\hat{e}$ is correctly specified — "two chances to get it right" instead of one.

When you can't measure confounders at all, three quasi-experimental designs substitute for randomization. **Difference-in-differences** compares treated-vs-control units before and after treatment, relying on the parallel-trends assumption (absent treatment, both groups would have moved together); naive two-way fixed effects is biased under staggered adoption timing across units, a correction only properly diagnosed by Goodman-Bacon (2021) — a live methodological fix still propagating through applied work. **Instrumental variables** use an exogenous instrument that affects treatment but has no direct path to the outcome (relevance + exclusion), estimated via two-stage least squares. **Regression discontinuity** exploits a hard cutoff (a score threshold, an age limit) as a source of local, as-if-random assignment right around the boundary.

Where prediction and causal inference diverge most sharply for ML engineers is **heterogeneous treatment effects** — the conditional average treatment effect $\text{CATE}(x) = \mathbb{E}[Y(1)-Y(0) \mid X=x]$, i.e. uplift modeling: not "does this treatment work" but "who should get it." S-, T-, and X-learners (Künzel et al., 2019) are meta-algorithms that reuse any standard regressor as a plug-in component — S-learner fits one model with treatment as a feature, T-learner fits two separate models per arm, X-learner cross-imputes to correct for imbalanced arm sizes. Causal forests (Wager & Athey, 2018) extend [[Concept - Bagging and Random Forests]] with **honest splitting**: the subsample used to choose tree splits is disjoint from the subsample used to estimate the leaf's treatment effect, so a leaf never uses the same data both to decide its own shape and to report its own answer — the direct analogue of the leakage-avoidance discipline gradient-boosting pipelines need for target encoding. Evaluate CATE estimators with Qini curves and uplift curves, never plain accuracy — accuracy answers a prediction question, not a targeting question.

## In practice

The industrial use case for uplift/CATE modeling is targeting: marketing wants to know who a promo campaign will actually *cause* to purchase, not who is merely correlated with purchasing after receiving it — sending a promo to someone who was going to buy anyway wastes margin; the CATE model finds the persuadable segment. Positivity in practice means checking the overlap of estimated propensity scores between treated and control groups — regions where $\hat{e}(x)$ is near 0 or 1 blow up IPW weights and dominate the variance of the estimate; a common practical fix is trimming or clipping propensity scores outside roughly [0.05, 0.95] before weighting. Because a lot of observational causal work reuses [[Concept - Gradient Boosting]] or random-forest models as the plug-in outcome/propensity learners, the same tuning discipline from [[Reference - Gradient Boosting Hyperparameters]] applies — but a well-tuned *predictive* model is not automatically a well-specified *causal* nuisance model, since the CV objective (minimize prediction error) doesn't target the same thing as unbiased effect estimation.

## Failure modes

- **Adjusting for a collider.** Conditioning on a variable caused by both treatment and outcome (a classic case: conditioning on a post-treatment "engagement" metric that both the treatment and the outcome influence) induces a spurious association where none existed. Detect by drawing the DAG before choosing covariates, not after.
- **Adjusting for a mediator.** Controlling for a variable on the causal path zeroes out the indirect effect and understates the total effect you actually wanted. Detect by asking, for every covariate: could treatment plausibly cause this?
- **Positivity violations.** Regions of covariate space where one arm has near-zero probability produce extreme IPW weights and wildly unstable estimates. Detect by plotting the propensity score distribution split by treatment group and checking for non-overlapping regions.
- **Naive two-way fixed effects under staggered treatment timing.** Goodman-Bacon (2021) showed this classic diff-in-diff setup implicitly uses already-treated units as controls for later-treated units, which can produce negative weights and a biased, even sign-flipped, estimate. Detect by decomposing the estimate into its constituent 2x2 comparisons or switching to a staggered-adoption-robust estimator.
- **Treating feature importance as a causal effect.** A high SHAP or gain-based importance from a [[Concept - Gradient Boosting]] model tells you the feature was useful for *prediction* under the training distribution's correlational structure — it does not tell you that intervening on that feature would change the outcome. Simpson's paradox is the sharpest version of this trap: the classic real-world example is kidney-stone treatment success rates (Charig et al., 1986), where one treatment has a higher overall success rate but the *other* treatment wins within both the small-stone and large-stone subgroups, because physicians preferentially used the first treatment on easier cases.

## The non-obvious

The AIPW "two chances to get it right" property is the practical reason doubly-robust estimators have become the default over plain IPW or plain outcome-regression: engineering teams rarely trust either their propensity model or their outcome model to be perfectly specified, but they don't need to — only one has to be right for the ATE estimate to stay consistent. The second, quieter insight is that causal forests' honest splitting is the same discipline as [[Snippet - Leakage-Free Target Encoding]] wearing a different hat: never let a data point inform both the *structure* of the estimator and the *value* it reports for that same point. Anyone who has internalized leakage discipline for gradient boosting already has the right instinct for honest splitting in causal forests — it's the identical bug in a different variable's clothing.

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
