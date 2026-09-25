---
tags: [concept, domain/foundations, level/core]
aliases: [MLE, maximum likelihood, negative log-likelihood, NLL]
summary: "Every standard loss is a negative log-likelihood under an assumed noise model; choosing the loss is choosing that assumption."
---

# Concept - Maximum Likelihood Estimation

> **One-paragraph hook:** Every model you've trained was doing maximum likelihood estimation, whether you knew it or not. MSE, L1, cross-entropy and binary cross-entropy are each the negative log-likelihood of the data under a specific noise model, so picking a loss silently asserts a distributional assumption about your targets. MLE is also why next-token pretraining works at all: it's the estimation principle with the strongest asymptotic guarantees in statistics, applied at trillion-token scale. What MLE promises (consistency, efficiency) and what it doesn't (calibration, robustness to a wrong noise model) explains a surprising number of everyday training pathologies.

## The mechanism

MLE picks the parameters that make the observed data most probable:

$$\hat{\theta}_{\text{MLE}} = \arg\max_\theta \prod_{i=1}^N p(x_i \mid \theta) = \arg\min_\theta \; -\sum_{i=1}^N \log p(x_i \mid \theta)$$

Taking the log doesn't move the argmax (it's monotone), and it fixes the computation. A product of $N$ probabilities underflows any float format for large $N$ ([[Concept - Floating Point for Deep Learning]]). The log-sum is numerically sane, decomposes per example (hence minibatches), and has well-scaled gradients.

Every standard loss is an NLL under some noise model. Assume $y = f_\theta(x) + \epsilon$ with $\epsilon \sim \mathcal{N}(0, \sigma^2)$ and the NLL is $\frac{(y - f_\theta(x))^2}{2\sigma^2} + \text{const}$, which is MSE. The full table:

| Loss | Implied noise model |
|---|---|
| MSE | Gaussian with fixed variance |
| L1 | Laplace (heavier tails; median, not mean) |
| Cross-entropy | Categorical over classes/tokens |
| Binary cross-entropy | Bernoulli |

Choosing a loss is a distributional assumption, intended or not; [[Concept - Loss Functions for Neural Networks]] has the catalog.

MLE is also cross-entropy minimization and forward KL. In expectation over the data distribution, the NLL is $\mathbb{E}_{x \sim p_{\text{data}}}[-\log p_\theta(x)] = H(p_{\text{data}}) + D_{\text{KL}}(p_{\text{data}} \| p_\theta)$. The entropy term is constant, so minimizing [[Concept - Entropy and Cross-Entropy]] is the same as minimizing the *forward* [[Concept - KL Divergence]] from data to model. That's the mode-covering direction, which forces mass everywhere the data has it. Next-token pretraining factorizes the sequence likelihood $p(x_{1:T}) = \prod_t p(x_t \mid x_{<t})$ and minimizes per-token NLL, so everything in [[Deep Dive - Anatomy of a Pretraining Run]] is "just" MLE. The gradient through [[Concept - Softmax]] is the famously clean $\nabla_z \mathcal{L} = \text{softmax}(z) - \text{onehot}(y)$.

Under regularity conditions MLE is *consistent* ($\hat\theta \to \theta^*$ as $N \to \infty$), *asymptotically efficient* (it attains the Cramér–Rao lower bound $\text{Var}(\hat\theta) \geq I(\theta)^{-1}$), and *asymptotically normal*: $\sqrt{N}(\hat\theta - \theta^*) \to \mathcal{N}(0, I(\theta^*)^{-1})$. Here $I(\theta) = \mathbb{E}[\nabla_\theta \log p \, \nabla_\theta \log p^\top] = -\mathbb{E}[\nabla^2_\theta \log p]$ is the Fisher information: the expected curvature of the log-likelihood, i.e. the expected Hessian of the loss. Near an optimum, Fisher ≈ Gauss–Newton ≈ Hessian, so the empirical curvature structure in [[Concept - The Hessian Spectrum in Deep Learning]] doubles as the statistical-information structure. Flat likelihood directions mean low Fisher information, poorly determined parameters and ill-conditioned optimization ([[Concept - The Condition Number]]). Statistically and numerically, it's the same problem.

MAP is MLE plus a prior: maximizing the posterior adds $\log p(\theta)$ to the objective. An L2 penalty is a zero-mean Gaussian prior; an L1 penalty is a Laplace prior. Weight decay is MAP estimation under a Gaussian prior, with one footnote: AdamW's *decoupled* decay (Loshchilov & Hutter 2019) is deliberately not the exact gradient of an L2-penalized loss ([[Concept - Adam and AdamW]]).

## In practice

- **Match the loss to the tails.** MSE on heavy-tailed targets (latencies, financial returns, physical sensor data) underperforms because the Gaussian assumption punishes residuals quadratically, so a few outliers dominate every gradient step. Huber or L1 encode heavier tails and fix it at the modeling level.
- **None of this is specific to deep learning.** [[Concept - Gradient Boosting]] fits stagewise MLE with logloss, Poisson or Tweedie objectives. [[Deep Dive - Diffusion Models]] train by maximizing a variational lower bound on log-likelihood. Same principle, other function classes.
- **Heteroscedastic regression for free.** Have the model predict $\sigma(x)$ too and minimize the full Gaussian NLL $\frac{(y-\mu(x))^2}{2\sigma(x)^2} + \frac{1}{2}\log \sigma(x)^2$. The model learns to down-weight regions it can't predict. Guard $\sigma$ with a softplus floor or it collapses.
- **Reading loss values.** LM training loss is per-token NLL in nats, so it converts directly to perplexity and bits-per-byte. It's an interpretable statistical quantity in its own right.

## Failure modes

- **Overfitting / memorization.** Given finite data and enough capacity, unregularized MLE happily piles mass onto the training set. Detection: train NLL falls while held-out NLL rises. Remedies: the MAP view (weight decay), early stopping (implicit regularization), data scale.
- **Divergence on separable data.** If the classes (or next tokens) are perfectly predictable, cross-entropy is only minimized as logits $\to \infty$. Logistic regression's classic pathology; in LLM training it shows up as unbounded logit-norm growth. Remedies: label smoothing (raises the loss floor to a finite optimum), weight decay, and logit-norm control like [[Concept - z-loss and Logit Soft-Capping]]. Detection: track mean max-logit over training.
- **Miscalibration out of the box.** MLE optimizes fit, not calibrated uncertainty. Modern overparameterized nets trained to low NLL are systematically overconfident (Guo et al. 2017). Detection: reliability diagrams / ECE on held-out data. Remedies: temperature scaling, label smoothing.

## The non-obvious

Two things people learn late. First, the plain MLE of variance is biased: $\hat\sigma^2 = \frac{1}{N}\sum(x_i - \bar{x})^2$ has expectation $\frac{N-1}{N}\sigma^2$. MLE is only *asymptotically* unbiased, and small-sample estimates (per-group statistics, small eval sets) inherit the bias.

Second, and deeper: **the model believes its noise model even when the noise model is wrong.** White (1982) showed misspecified MLE converges to the KL-closest member of your model family. An L2 loss on heavy-tailed data doesn't "sort of work"; it faithfully finds the best *Gaussian* explanation, which systematically misses. No optimizer, scheduler or learning-rate sweep will fix that modeling bug. If a regression stubbornly underperforms, question the implied noise model before the architecture.

## Connections

- [[Concept - Entropy and Cross-Entropy]] — cross-entropy loss is the finite-sample face of MLE; the identities in that note make this one precise.
- [[Concept - KL Divergence]] — MLE minimizes forward KL, and the forward/reverse asymmetry explains mode-covering behavior of pretrained models.
- [[Concept - The Hessian Spectrum in Deep Learning]] — Fisher information is the expected Hessian; the curvature story continues there.
- [[Concept - The Condition Number]] — ill-conditioned Fisher information means both statistically ill-determined parameters and slow gradient descent.
- [[Deep Dive - Anatomy of a Pretraining Run]] — the industrial-scale execution of the MLE objective this note derives.
- [[Concept - Softmax]] — the output layer whose composition with NLL yields the softmax-minus-onehot gradient.
- [[Concept - Adam and AdamW]] — weight decay as Gaussian-prior MAP, and where the decoupled variant breaks the exact correspondence.
- [[Concept - Loss Functions for Neural Networks]] — the practical catalog of losses this note reinterprets as noise models.
- [[Concept - Gradient Boosting]] — the same NLL principle driving classical ML objectives (logloss, Poisson, Tweedie).
- [[Deep Dive - Diffusion Models]] — trained by a variational bound on log-likelihood; MLE's lineage in generative modeling beyond LMs.
- [[Concept - z-loss and Logit Soft-Capping]] — the engineering remedy for MLE's logit-divergence pathology at pretraining scale.
- [[Concept - Floating Point for Deep Learning]] — why likelihoods must live in log-space: raw probability products underflow every hardware format.

## Sources

- Fisher (1922) — *On the Mathematical Foundations of Theoretical Statistics.* Introduced likelihood and the MLE principle.
- White (1982) — *Maximum Likelihood Estimation of Misspecified Models.* Quasi-MLE converges to the KL-closest model — the "believes its noise model" result.
- Guo et al. (2017) — *On Calibration of Modern Neural Networks.* Modern nets trained by MLE are overconfident; temperature scaling as remedy.
- Loshchilov & Hutter (2019) — *Decoupled Weight Decay Regularization.* Why AdamW's decay is not exactly the L2-prior gradient.
