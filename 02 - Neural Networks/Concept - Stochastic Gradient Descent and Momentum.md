---
tags: [concept, domain/neural-networks, level/core]
aliases: [SGD, momentum, Nesterov momentum, heavy-ball momentum]
summary: "Mini-batch SGD and momentum: the EMA update, why gradient noise regularizes, and the LR as the hyperparameter that decides everything."
---

# Concept - Stochastic Gradient Descent and Momentum
> **One-paragraph hook:** Every deep-learning optimizer is built on SGD: take a noisy gradient estimate from a mini-batch, step downhill, repeat a million times. People chronically underestimate two things: the *noise is a feature* doing real regularization work, and momentum silently multiplies your effective learning rate by 10. Everything in [[Concept - Adam and AdamW]] is a per-coordinate refinement of what's written here.

## The mechanism

**Plain SGD** updates parameters against the mini-batch gradient:

$$\theta_{t+1} = \theta_t - \eta\, g_t, \qquad g_t = \frac{1}{B}\sum_{i \in \mathcal{B}} \nabla_\theta \ell_i(\theta_t)$$

The mini-batch gradient is an **unbiased estimator** of the full-dataset gradient, with variance scaling as $\sim 1/B$. That $1/B$ sets batch-size economics. Doubling the batch halves the gradient variance, which buys roughly a halving of steps-to-target, but only up to the **critical batch size**. Past it the gradient is accurate enough and extra data per step is wasted. The gradient noise scale (McCandlish et al. 2018) formalizes where that knee sits; see [[Concept - Critical Batch Size]].

**Momentum** (heavy-ball, Polyak 1964) replaces the raw gradient with a running velocity:

$$v_t = \mu\, v_{t-1} + g_t, \qquad \theta_{t+1} = \theta_t - \eta\, v_t$$

The velocity is an exponential moving average over roughly $1/(1-\mu)$ recent gradients, so $\mu = 0.9$ averages the last ~10. Where consecutive gradients agree (the long axis of a loss valley) the contributions add up. Where they alternate sign (the steep, oscillating short axis) they cancel, which damps the zig-zag in ill-conditioned valleys; for quadratics it improves the dependence on the [[Concept - The Condition Number]] $\kappa$ from $O(\kappa)$ to $O(\sqrt{\kappa})$. Heavy-ball is physically a discretized damped oscillator, so too little damping (too-high $\mu$) overshoots and rings.

**Nesterov momentum** evaluates the gradient at the look-ahead point $\theta - \eta\mu v$, where the velocity is about to carry you, instead of at $\theta$. It improves the constants in convex theory (Nesterov 1983) and helped in the Sutskever et al. (2013) era; in modern deep nets it rarely changes outcomes.

**The hidden effective-LR trap:** with a steady gradient $g$, the velocity converges to $g/(1-\mu)$, so the asymptotic step size is $\eta/(1-\mu)$. That's **10× the nominal LR at $\mu=0.9$**. Some frameworks and papers use the normalized form $v \leftarrow \mu v + (1-\mu)g$ instead, which hides the factor. PyTorch doesn't. Comparing LRs across papers, frameworks or momentum values without correcting for it is a classic silent divergence.

## In practice

- The canonical vision recipe (as of 2026, essentially unchanged for a decade): ResNet-50 on ImageNet with SGD, $\mu = 0.9$, LR 0.1 at batch 256, weight decay 1e-4, cosine or step decay. The **linear scaling rule** (Goyal et al. 2017) scales LR with batch size ($\eta = 0.1 \cdot B/256$) plus ~5 epochs of warmup. It holds to batch ~8K and degrades beyond.
- The learning rate is the most important hyperparameter in the whole stack. Too high diverges to NaN. Too low crawls, or sticks at a bad plateau that looks like a bug. The **LR range test** (Smith 2015) is still the fastest way to find the usable band: sweep LR up within one run until loss diverges, then back off somewhat.
- Where SGD still survives (as of 2026): vision CNNs and some fine-tuning. Transformer training effectively requires adaptive methods, because the sparse, heavy-tailed gradients from embeddings and normalization layers make plain SGD impractical (full story: [[Lore - The Adam vs SGD Generalization Wars]]). Exact update rules side by side are in [[Reference - Optimizer Update Rules]].
- At scale, batch size, LR and compute budget are coupled; the noise-scale knee feeds [[Concept - Scaling Laws]]-style budget planning, and the loop mechanics (accumulation, clipping, ordering) are in [[Concept - The Training Loop]].

## Failure modes

- **Divergence.** Symptom: loss climbs, then NaN within tens of steps. Cause: LR past the stable band (classically $\eta > 2/\lambda_{max}$ in the quadratic picture). Detection: the LR range test bounds this before you commit a run. Fix: lower LR, add warmup, clip gradients.
- **The momentum-change trap.** Symptom: a run that was healthy at $\mu=0.9$ explodes when someone "just tries" $\mu=0.99$. Cause: effective LR is $\eta/(1-\mu)$, and that change multiplied it by 10. Fix: co-tune. When raising $\mu$, start by lowering $\eta$ by the same factor.
- **Crawling.** Symptom: loss falls at a glacially linear rate and the run gets nowhere. Cause: LR one to two orders of magnitude too low (or a disconnected graph posing as slow learning). Detection: an LR sweep separates the two immediately.
- **Sustained oscillation.** Symptom: loss rings at a fixed amplitude, neither diverging nor converging. Cause: under-damped momentum, or an LR sitting at the stability boundary. Modern training in fact *equilibrates* at that boundary; that's the [[Concept - The Edge of Stability]] finding.

## The non-obvious

First piece of tribal knowledge: **the noise does real work.** SGD's gradient noise biases the trajectory toward flat, low-norm minima. That implicit regularization, and no explicit penalty in the loss, is the leading explanation for why plain SGD often test-generalizes better than Adam on vision (see [[Concept - Generalization in Deep Learning]]). Cranking batch size to "fix" noisy training sometimes trades test accuracy for a smoother curve.

Second, **folklore, weakly sourced:** nobody derived the universal $\mu = 0.9$ default. It happens to match typical curvature timescales: averaging over ~10 steps fits, empirically, how fast the local loss geometry changes under typical LRs. It survives because it works, not because anyone proved it should.

## Connections

- [[Concept - Loss Functions for Neural Networks]] — the objective whose gradient this whole machine descends; loss scale and reduction directly rescale the effective LR.
- [[Concept - The Training Loop]] — where the update actually executes, and where ordering (clip, step, zero) makes or breaks it.
- [[Concept - Adam and AdamW]] — the per-coordinate adaptive refinement stacked on top of these update rules; the default everywhere SGD isn't.
- [[Reference - Optimizer Update Rules]] — the exact-formula lookup sheet for every variant named here.
- [[Concept - Critical Batch Size]] — the gradient-noise-scale knee that decides when bigger batches stop buying faster training.
- [[Concept - The Condition Number]] — the quantity momentum is fighting; $\kappa \to \sqrt{\kappa}$ is momentum's whole theoretical case.
- [[Concept - Generalization in Deep Learning]] — SGD's implicit bias toward flat minima is a central pillar of why overparameterized nets generalize.
- [[Lore - The Adam vs SGD Generalization Wars]] — the decade of practitioner argument over exactly the noise-and-flatness claims made here.
- [[Concept - The Edge of Stability]] — modern training runs at the classical stability boundary rather than below it; the frontier sequel to this note's LR story.
- [[Concept - Scaling Laws]] — batch size, LR, and noise scale enter compute-optimal planning at scale.

## Sources

- Robbins & Monro (1951) — "A Stochastic Approximation Method." The original convergence theory for noisy-gradient descent.
- Polyak (1964) — heavy-ball momentum and the $\sqrt{\kappa}$ acceleration argument.
- Nesterov (1983) — accelerated gradient with the look-ahead evaluation point.
- Sutskever et al. (2013) — "On the importance of initialization and momentum in deep learning." Made momentum + careful init standard practice in deep nets.
- Smith (2015) — "Cyclical Learning Rates for Training Neural Networks." Source of the LR range test.
- Goyal et al. (2017) — "Accurate, Large Minibatch SGD: Training ImageNet in 1 Hour." Linear scaling rule + warmup, and its ~8K batch limit.
- McCandlish et al. (2018) — "An Empirical Model of Large-Batch Training." The gradient noise scale and critical batch size.
