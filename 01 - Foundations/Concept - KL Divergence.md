---
tags: [concept, domain/foundations, level/core]
aliases: [KL, relative entropy, Kullback-Leibler divergence]
summary: "The asymmetric gap between distributions: forward KL covers modes (MLE), reverse KL seeks them (RLHF); estimating it well is subtle."
---

# Concept - KL Divergence

> **One-paragraph hook:** KL divergence is the quantity you implicitly optimize during pretraining, explicitly penalize during RLHF, match during distillation, and bound in every variational objective. It looks like a distance but isn't one. Its *asymmetry* explains why MLE-trained models hallucinate broadly while RLHF-trained models collapse narrowly. Engineers who treat "the KL" as one number with one meaning get bitten by both directions.

## The mechanism

$$D_{KL}(p \,\|\, q) = \sum_x p(x) \log \frac{p(x)}{q(x)} = \mathbb{E}_{x \sim p}\big[\log p(x) - \log q(x)\big]$$

Gibbs' inequality gives $D_{KL} \ge 0$ with equality iff $p = q$ (one-line proof via Jensen: $\mathbb{E}_p[-\log(q/p)] \ge -\log \mathbb{E}_p[q/p] = -\log 1 = 0$). It is **not symmetric**, has **no triangle inequality** (unlike the true metrics in [[Concept - Vector Norms and Distances]]), and is **infinite** whenever $q$ puts zero mass where $p$ doesn't. It is jointly convex in $(p, q)$, one of the few globally convex objects in this field ([[Concept - Convexity and the Loss Landscape]]). From $H(p,q) = H(p) + D_{KL}(p\|q)$, minimizing cross-entropy over $q$ is the same as minimizing forward KL from data to model. So pretraining is KL minimization, and [[Concept - Entropy and Cross-Entropy]] and [[Concept - Maximum Likelihood Estimation]] are two faces of this note.

The asymmetry shows up as behavior. Forward KL $D(p\|q)$ takes the expectation under the *data*. It charges heavily wherever $p > 0$ but $q \approx 0$, so the model has to put mass on **every** data mode: *mode-covering / zero-avoiding*. Fit a unimodal $q$ to a bimodal $p$ under forward KL and it bridges the modes, putting mass where the data has none. Reverse KL $D(q\|p)$ takes the expectation under the *model*. It charges wherever $q > 0$ but $p \approx 0$, so the model retreats into a subset of high-$p$ regions: *mode-seeking / zero-forcing* (taxonomy per Minka 2005). Same "distance," opposite pathologies. Forward KL over-generalizes; reverse KL over-commits.

## In practice

- **RLHF.** The policy objective maximizes reward minus $\beta \cdot D_{KL}(\pi \,\|\, \pi_{\text{ref}})$, a *reverse* KL from the policy to the frozen reference, applied per token (Ouyang et al. 2022; typical $\beta$ in the 0.01–0.1 range, InstructGPT-era recipes ~0.02). Zero-forcing is why an over-optimized policy collapses onto narrow high-reward modes: the repetitive phrasings and formats that scored well with [[Concept - Reward Models]]. [[Concept - KL Control in RLHF]] covers the engineering of this penalty, and [[Deep Dive - RLHF End to End]] the pipeline around it.
- **DPO.** KL-constrained reward maximization has the closed form $\pi^*(y|x) \propto \pi_{\text{ref}}(y|x)\, e^{r(x,y)/\beta}$. Invert it to write reward as $\beta \log(\pi/\pi_{\text{ref}})$ and the RL problem becomes a classification loss. That inversion *is* [[Concept - Direct Preference Optimization (DPO)]] (Rafailov et al. 2023).
- **Distillation.** The student matches the teacher's temperature-softened distribution under KL. Gradients scale as $1/T^2$, so the loss gets multiplied by $T^2$ to keep the balance (Hinton et al. 2015); see [[Concept - Knowledge Distillation]].
- **Variational objectives.** The ELBO is reconstruction minus $D_{KL}(q(z|x)\,\|\,p(z))$, with the Gaussian closed form $\frac{1}{2}(\mu^2 + \sigma^2 - \log\sigma^2 - 1)$ (Kingma & Welling 2013). The diffusion training bound is a ladder of KLs between Gaussians ([[Deep Dive - Diffusion Models]]).
- **Estimating KL from samples.** With samples $x \sim p$ and ratio $r = q(x)/p(x)$, the naive estimator $k_1 = -\log r$ is unbiased but high-variance, and can go *negative* on a batch. Schulman's $k_3 = (r - 1) - \log r$ is unbiased (because $\mathbb{E}_p[r] = 1$), pointwise non-negative (since $r - 1 \ge \log r$), and much lower variance (Schulman 2020). It's what PPO/GRPO implementations actually log. Compute $\log r$ as a difference of log-probs from log-softmax, never by dividing probabilities, and clamp the log-ratio (±20 is common) against support-mismatch blowups.

## Failure modes

- **Support mismatch → KL explosion.** $q \to 0$ where $p > 0$ makes the ratio infinite. In RLHF you see per-token KL spikes when the policy samples tokens the reference model finds nearly impossible, or when the reference runs in different precision or behind truncated sampling. Detection: watch max per-token KL, not only the mean.
- **Estimator noise mistaken for drift.** A batch-mean $k_1$ that goes negative or jumps is often variance, not policy movement. Detection: compare $k_1$ and $k_3$ traces. If they disagree wildly, it's estimator noise.
- **Mode collapse under reverse KL.** Reward climbs while sample entropy and distinct-n-gram counts fall. That's zero-forcing doing its job. Whether it's a feature (sharpening onto correct answers) or a bug (sycophantic template collapse) depends entirely on the task. Detection: track sample entropy next to reward.
- **Direction and API mistakes.** Swapping the arguments silently swaps mode-covering for mode-seeking. PyTorch's `F.kl_div(input, target)` computes $D_{KL}(\text{target}\,\|\,\text{input-dist})$ and expects `input` already in log-space, and people get the argument order and log-space convention wrong constantly. Detection: unit-test against a hand-computed two-point distribution.

## The non-obvious

The "KL" on your RLHF dashboard is an *estimate* with its own bias–variance profile. In many codebases the logged estimator isn't even the quantity being optimized (e.g., $k_1$ logged, $k_3$ or a penalty-in-reward form optimized). A rising reported KL can be estimator noise, a support-mismatch artifact, or real policy drift. Those are three problems with three fixes, and teams have retuned $\beta$ to chase what turned out to be variance. Before touching the coefficient, check the estimator, the max-token KL and the reference model's numerics, in that order.

## Connections

- [[Concept - Entropy and Cross-Entropy]] — cross-entropy = entropy + KL; this note is the "excess" term of that one.
- [[Concept - Maximum Likelihood Estimation]] — MLE is forward-KL minimization from data to model; the statistical identity behind pretraining.
- [[Concept - Convexity and the Loss Landscape]] — KL's joint convexity is a rare guarantee, and the loss geometry frame for why KL-regularized objectives are well-behaved.
- [[Concept - Vector Norms and Distances]] — the contrast case: true metrics with symmetry and triangle inequality, everything KL is not.
- [[Deep Dive - RLHF End to End]] — where the reverse-KL penalty sits inside the full PPO training system.
- [[Concept - KL Control in RLHF]] — the direct engineering of $\beta$, estimators, and schedules for the penalty introduced here.
- [[Concept - Direct Preference Optimization (DPO)]] — the closed-form solution of the KL-constrained objective, turned into a supervised loss.
- [[Concept - Reward Models]] — the reward source whose over-optimization the KL penalty exists to restrain.
- [[Concept - Knowledge Distillation]] — soft-target matching is KL at temperature, with the $T^2$ gradient-scale correction.
- [[Deep Dive - Diffusion Models]] — the variational bound trained in practice is a sum of closed-form Gaussian KLs.

## Sources

- Kullback & Leibler (1951) — "On Information and Sufficiency" — the original definition.
- Minka (2005) — "Divergence Measures and Message Passing" — the mode-seeking vs mode-covering taxonomy.
- Schulman (2020) — "Approximating KL Divergence" (blog) — the $k_1/k_2/k_3$ estimators and why $k_3$ wins.
- Ouyang et al. (2022) — "Training language models to follow instructions" (InstructGPT) — the per-token reverse-KL penalty in production RLHF.
- Rafailov et al. (2023) — "Direct Preference Optimization" — the closed-form inversion of the KL-constrained objective.
- Hinton et al. (2015) — "Distilling the Knowledge in a Neural Network" — KL matching of soft targets, $T^2$ scaling.
- Kingma & Welling (2013) — "Auto-Encoding Variational Bayes" — the ELBO's KL term and its Gaussian closed form.
