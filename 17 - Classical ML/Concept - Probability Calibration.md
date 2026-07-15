---
tags: [concept, domain/classical-ml, level/core]
aliases: [calibration, reliability diagrams, Platt scaling, temperature scaling, ECE]
summary: "Making a classifier's scores mean P(y=1|score=p)=p, and the Platt/isotonic/temperature methods that enforce it after the fact."
---

> A model can post great accuracy or AUC and still be dangerously wrong about *how sure it is* — a boosted tree that outputs 0.95 when the true positive rate at that score is 60% will corrupt any downstream decision (triage thresholds, bet sizing, prediction sets) that trusts the number literally. Calibration is the discipline of making scores mean probabilities.

## The mechanism

A classifier is calibrated when, among all examples it scores near $p$, the empirical positive rate is also $p$: $P(y=1 \mid \hat p(x) = p) = p$. This is checked, never assumed.

**Reliability diagrams** bin predictions (e.g. by decile of $\hat p$) and plot mean predicted probability against observed frequency per bin; a perfectly calibrated model traces the diagonal. **Expected Calibration Error (ECE)** quantifies the gap numerically:

$$\text{ECE} = \sum_{b=1}^{B} \frac{|D_b|}{n} \, \big| \, \text{acc}(D_b) - \text{conf}(D_b) \, \big|$$

where $D_b$ is bin $b$'s examples, $\text{acc}$ the empirical positive rate, $\text{conf}$ the mean predicted probability. The **Brier score** ($\frac{1}{n}\sum(\hat p_i - y_i)^2$) decomposes (Murphy 1973) into reliability (calibration error, want low) versus resolution (how much scores vary and separate classes, want high) plus irreducible uncertainty — which is why predicting the base rate for every example is *perfectly calibrated* and has zero resolution: calibration alone is a floor, not a target.

Minimizing [[Concept - Entropy and Cross-Entropy]] loss is a proper scoring rule that rewards outputting the true conditional probability, which is why a well-trained logistic regression is well-calibrated close to by construction. Margin-maximizing objectives don't share this property — that's exactly why SVMs and boosted trees via [[Concept - Gradient Boosting]] need a separate fix, since their training reward is margin, not likelihood, which pushes scores toward 0 and 1 and produces a sigmoidal reliability curve.

Two standard fixes recalibrate a trained model's scores on a held-out set, without retraining the base model:

- **Platt scaling** (Platt 1999): fit a 1-D logistic regression $P(y=1) = \sigma(a \cdot f(x) + b)$ on the raw score $f(x)$. Parametric, needs only a few hundred points, and is the right shape for the sigmoidal distortion margin-maximizers produce.
- **Isotonic regression**: a non-parametric monotone step function fit via the pool-adjacent-violators algorithm (PAVA). More flexible than Platt but needs thousands of calibration points or it overfits into a visible staircase.

For neural nets, **temperature scaling** (Guo et al. 2017) divides the pre-[[Concept - Softmax]] logits by a single learned scalar $T > 1$ — $\text{softmax}(z/T)$ — which flattens overconfident distributions without moving the argmax (accuracy is unchanged, only confidence is). It fits by minimizing NLL on a validation set. The same logit-scaling trick reappears in LLM decoding as [[Concept - Sampling and Decoding Parameters]] — identical math, opposite purpose: controlling generation diversity rather than fixing calibration.

## In practice

- scikit-learn's `CalibratedClassifierCV` wraps a base estimator and fits the calibrator on a held-out fold rather than the training fold; fitting the calibrator on the same data used to train the classifier is a leakage trap that produces an optimistic reliability diagram.
- Multiclass calibration extends temperature scaling to the softmax vector, or uses Dirichlet calibration / vector scaling (per-class scale + bias) when classes miscalibrate differently.
- GBDT libraries expose raw margins/logits, not probabilities, unless `predict_proba` is explicitly requested; teams that skip calibration and ship boosting scores as "probability of default" or "probability of churn" are shipping false precision. This exact bug is catalogued in [[Gotchas - Gradient Boosting in Practice]].
- Typical numbers: ECE on an uncalibrated deep net can sit at 5–15 percentage points of confidence-accuracy gap on ImageNet-scale classification (Guo et al. 2017); a single temperature parameter typically cuts that by more than half.

## Failure modes

- **Resampling silently destroys calibration.** After SMOTE oversampling or majority-class undersampling (see [[Concept - Learning from Imbalanced Data]]), the trained model's implied class prior no longer matches the deployment prior, and predicted probabilities skew toward the resampled ratio. Fix: recalibrate afterward, or apply the closed-form prior correction $\text{logit}(\hat p_{\text{corrected}}) = \text{logit}(\hat p) - \log\frac{\pi_{\text{train}}}{1-\pi_{\text{train}}} + \log\frac{\pi_{\text{true}}}{1-\pi_{\text{true}}}$.
- **Calibrating on too few points.** Isotonic regression with fewer than ~1,000 calibration examples per class visibly overfits into a jagged staircase; detect via an erratic reliability diagram and fall back to Platt scaling.
- **Distribution shift invalidates any fitted calibrator.** A calibrator fit on last quarter's data drifts as the input distribution or true base rate moves; monitor ECE in production the same way accuracy is monitored, not as a one-time offline step.
- **Confusing calibration with discrimination.** A model can be perfectly calibrated and useless (predict the base rate for everyone) or highly discriminative (high AUC) and badly calibrated at the same time — always report both a discrimination metric and a calibration metric, never one alone, the same duty of rigor codified generally in [[Concept - Statistical Rigor in Model Evaluation]].

## The non-obvious

Practitioners repeatedly get burned by the *order of operations*: calibrate last, after all resampling, threshold-tuning, and ensembling decisions are frozen. Recalibrating and then re-tuning a downstream decision threshold invalidates the calibration again, because threshold tuning implicitly assumes a fixed score distribution. The correct pipeline order is train → calibrate on a held-out fold → *then* pick operating thresholds on the calibrated scores; doing it in any other order is the most common calibration bug in production imbalanced-classification pipelines. For applications that need a hard guarantee rather than a best-effort recalibration, [[Concept - Conformal Prediction]] wraps the same trained model to produce prediction sets with a finite-sample coverage guarantee instead of a corrected point probability — a complementary tool, not a replacement.

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
