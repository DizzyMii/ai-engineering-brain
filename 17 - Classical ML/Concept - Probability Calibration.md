---
tags: [concept, domain/classical-ml, level/core]
aliases: [calibration, reliability diagrams, Platt scaling, temperature scaling, ECE]
summary: "Making a classifier's scores mean P(y=1|score=p)=p, and the Platt/isotonic/temperature methods that enforce it after the fact."
---

> A model can post great accuracy or AUC and still be dangerously wrong about *how sure it is*. A boosted tree that outputs 0.95 where the true positive rate at that score is 60% will corrupt any downstream decision that takes the number literally: triage thresholds, bet sizing, prediction sets. Calibration is the work of making scores mean probabilities.

## The mechanism

A classifier is calibrated when, among all examples it scores near $p$, the empirical positive rate is also $p$: $P(y=1 \mid \hat p(x) = p) = p$. You check this. You never assume it.

**Reliability diagrams** bin predictions (say by decile of $\hat p$) and plot mean predicted probability against observed frequency per bin. A perfectly calibrated model traces the diagonal. **Expected Calibration Error (ECE)** puts a number on the gap:

$$\text{ECE} = \sum_{b=1}^{B} \frac{|D_b|}{n} \, \big| \, \text{acc}(D_b) - \text{conf}(D_b) \, \big|$$

where $D_b$ is bin $b$'s examples, $\text{acc}$ the empirical positive rate, and $\text{conf}$ the mean predicted probability. The **Brier score** ($\frac{1}{n}\sum(\hat p_i - y_i)^2$) decomposes (Murphy 1973) into reliability (calibration error; want it low), resolution (how much scores vary and separate classes; want it high) and irreducible uncertainty. Predicting the base rate for every example is therefore *perfectly calibrated* with zero resolution. Calibration alone is a floor, not a target.

Minimizing [[Concept - Entropy and Cross-Entropy]] loss is a proper scoring rule: it rewards outputting the true conditional probability. That's why a well-trained logistic regression comes out close to calibrated by construction. Margin-maximizing objectives don't have this property. SVMs and boosted trees via [[Concept - Gradient Boosting]] are trained to reward margin, not likelihood, which pushes scores toward 0 and 1 and gives a sigmoidal reliability curve, so they need a separate fix.

Two standard fixes recalibrate a trained model's scores on a held-out set without retraining it:

- **Platt scaling** (Platt 1999): fit a 1-D logistic regression $P(y=1) = \sigma(a \cdot f(x) + b)$ on the raw score $f(x)$. It's parametric, needs only a few hundred points, and has the right shape for the sigmoidal distortion that margin-maximizers produce.
- **Isotonic regression**: a non-parametric monotone step function fit with the pool-adjacent-violators algorithm (PAVA). More flexible than Platt, but it needs thousands of calibration points or it overfits into a visible staircase.

For neural nets, **temperature scaling** (Guo et al. 2017) divides the pre-[[Concept - Softmax]] logits by a single learned scalar $T > 1$, i.e. $\text{softmax}(z/T)$. That flattens overconfident distributions without moving the argmax, so accuracy stays the same and only confidence changes. It's fit by minimizing NLL on a validation set. The same logit scaling shows up in LLM decoding as [[Concept - Sampling and Decoding Parameters]]: identical math, used to control generation diversity instead of fixing calibration.

## In practice

- scikit-learn's `CalibratedClassifierCV` wraps a base estimator and fits the calibrator on a held-out fold. Fitting the calibrator on the classifier's own training data is a leakage trap that yields an optimistic reliability diagram.
- Multiclass calibration extends temperature scaling to the softmax vector, or uses Dirichlet calibration / vector scaling (per-class scale + bias) when classes miscalibrate differently.
- GBDT libraries expose raw margins/logits, not probabilities, unless `predict_proba` is explicitly requested. Teams that skip calibration and ship boosting scores as "probability of default" or "probability of churn" are shipping false precision. [[Gotchas - Gradient Boosting in Practice]] catalogs this bug.
- Typical numbers: an uncalibrated deep net can show a 5–15 percentage-point confidence-accuracy gap (ECE) on ImageNet-scale classification (Guo et al. 2017). A single temperature parameter typically cuts that by more than half.

## Failure modes

- **Resampling silently destroys calibration.** After SMOTE oversampling or majority undersampling (see [[Concept - Learning from Imbalanced Data]]), the model's implied class prior no longer matches deployment, and probabilities skew toward the resampled ratio. Recalibrate afterwards, or apply the closed-form prior correction $\text{logit}(\hat p_{\text{corrected}}) = \text{logit}(\hat p) - \log\frac{\pi_{\text{train}}}{1-\pi_{\text{train}}} + \log\frac{\pi_{\text{true}}}{1-\pi_{\text{true}}}$.
- **Too few calibration points.** Isotonic regression with fewer than ~1,000 examples per class overfits into a jagged staircase. An erratic reliability diagram gives it away; fall back to Platt scaling.
- **Distribution shift invalidates any fitted calibrator.** A calibrator fit on last quarter's data drifts as inputs or the true base rate move. Monitor ECE in production like you monitor accuracy, not as a one-off offline step.
- **Confusing calibration with discrimination.** A model can be perfectly calibrated and useless (base rate for everyone), or highly discriminative (high AUC) and badly calibrated. Always report a discrimination metric and a calibration metric together, the general rigor rule from [[Concept - Statistical Rigor in Model Evaluation]].

## The non-obvious

People keep getting burned by *order of operations*. Calibrate last, after resampling, threshold tuning and ensembling decisions are frozen. If you recalibrate and then re-tune a downstream threshold, you've invalidated the calibration again, because threshold tuning assumes a fixed score distribution. The right order is train → calibrate on a held-out fold → *then* pick operating thresholds on the calibrated scores. Any other order is the most common calibration bug in production imbalanced-classification pipelines.

When an application needs a hard guarantee instead of best-effort recalibration, [[Concept - Conformal Prediction]] wraps the same trained model and produces prediction sets with a finite-sample coverage guarantee in place of a corrected point probability. It complements calibration; it doesn't replace it.

## Connections

- [[Concept - Learning from Imbalanced Data]] — resampling to fix imbalance is exactly what breaks calibration; the two problems must be solved in a fixed order.
- [[Concept - Gradient Boosting]] — the model family whose margin-maximizing objective produces the classic sigmoidal miscalibration Platt scaling was designed for.
- [[Concept - Softmax]] — the function temperature scaling operates on; its saturation behavior explains why one scalar fixes most neural miscalibration.
- [[Concept - Entropy and Cross-Entropy]] — the proper scoring rule that makes a well-trained model's outputs approximately calibrated as an emergent property, unlike margin losses.
- [[Concept - Conformal Prediction]] — a complementary, distribution-free alternative: prediction sets with a coverage guarantee instead of a recalibrated point probability.
- [[Concept - Sampling and Decoding Parameters]] — LLM decoding temperature is the identical logit-scaling mechanism repurposed for diversity control rather than calibration.
- [[Concept - Statistical Rigor in Model Evaluation]] — calibration metrics (ECE, Brier) belong in the same rigor discipline as significance testing and confidence intervals for any reported model metric.
- [[Gotchas - Gradient Boosting in Practice]] — documents the recurring, concrete bug of setting `scale_pos_weight` for imbalance and shipping the resulting uncalibrated scores.

## Sources
- Platt (1999) — "Probabilistic Outputs for Support Vector Machines," the original Platt scaling paper.
- Guo, Pleiss, Sun & Weinberger (2017) — "On Calibration of Modern Neural Networks," establishing that modern deep nets are systematically overconfident and popularizing temperature scaling.
- Murphy (1973) — the Brier score decomposition into reliability, resolution, and uncertainty.
- Niculescu-Mizil & Caruana (2005) — "Predicting Good Probabilities With Supervised Learning," the applied comparison of Platt vs isotonic across model families.
