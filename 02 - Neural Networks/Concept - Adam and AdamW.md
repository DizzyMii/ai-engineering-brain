---
tags: [concept, domain/neural-networks, level/advanced]
aliases: [Adam, AdamW, decoupled weight decay, adaptive moment estimation]
summary: "Adam's moment-EMA update, why AdamW's decoupled decay is not Adam+L2, the 8 bytes/param cost, and the sign-descent intuition."
---

# Concept - Adam and AdamW

> **One-paragraph hook:** AdamW is the optimizer under essentially every model you use *(as of 2026)*. It keeps two exponential moving averages per parameter, a smoothed gradient and a smoothed squared gradient, and divides one by the square root of the other, so each parameter gets its own effective learning rate. Practitioners keep getting two things wrong: what the "W" changes (under Adam, decoupled weight decay is *not* the same update as L2 regularization), and what it costs (the optimizer state is the single largest consumer of training memory, bigger than the model itself).

## The mechanism

Adam (Kingma & Ba 2015) tracks the first and second moments of the gradient $g_t$ as EMAs, corrects their startup bias, and takes a preconditioned step. The $m$ term is the momentum EMA from [[Concept - Stochastic Gradient Descent and Momentum]]:

$$m_t = \beta_1 m_{t-1} + (1-\beta_1)\, g_t \qquad v_t = \beta_2 v_{t-1} + (1-\beta_2)\, g_t^2$$

$$\hat m_t = \frac{m_t}{1-\beta_1^t} \qquad \hat v_t = \frac{v_t}{1-\beta_2^t} \qquad \theta_t = \theta_{t-1} - \eta\, \frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon}$$

It's all elementwise. Each parameter gets its own step size $\eta/\sqrt{\hat v_t}$: large where gradients have been consistently small, small where they've been large or noisy. The bias-correction terms $(1-\beta^t)^{-1}$ are there because $m_0 = v_0 = 0$ makes the early EMAs underestimates. Without them the first thousands of steps are silently too small. (Epsilon placement, warmup interaction and RAdam are covered in [[Concept - Adam's Epsilon and Bias Correction]].)

### The AdamW fix

Loshchilov & Hutter (2019). Classical L2 regularization adds $\lambda\theta$ *to the gradient*, so under Adam it flows through $m$ and gets divided by $\sqrt{\hat v}$. Parameters with a large gradient history get *less* shrinkage, inverting the regularizer's intent and tying its strength to the loss surface. AdamW applies decay directly to the weights, outside the adaptive machinery:

$$\theta_t = \theta_{t-1} - \eta \left( \frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon} + \lambda\, \theta_{t-1} \right)$$

Same $\lambda$ for every parameter, uniform multiplicative shrinkage per step, independent of $v$. So "Adam+L2" and "AdamW" at identical hyperparameters give measurably different models, and weight-decay values don't transfer between them. [[Reference - Optimizer Update Rules]] tabulates the whole family.

## In practice

- **Defaults:** $\beta_1 = 0.9$, $\beta_2 = 0.999$, $\epsilon = 10^{-8}$, from the original paper, and still right for small models. LLM pretraining uses $\beta_2 = 0.95$. At large batch the gradient estimate is already low-variance, and a ~20-step second-moment memory ($1/(1-\beta_2)$) tracks curvature shifts faster than a 1000-step one, which materially cuts loss spikes. That's the "0.95 for transformers" folklore, now near-universal in published configs (GPT-3, LLaMA and descendants). Weight decay $\lambda \approx 0.1$, applied only to matmul weights.
- **Learning rates:** $10^{-3}$ for small nets, $1\text{–}3 \times 10^{-4}$ for LLM pretraining. For a persistent gradient $\hat m/\sqrt{\hat v} \approx \pm 1$ elementwise, so the per-step update is roughly *bounded by $\eta$ itself*: smoothed sign descent. Hence small Adam LRs, which also transfer across model scales far better than SGD LRs, where the step scales with raw gradient magnitude.
- **Memory:** $m$ and $v$ in fp32 cost **8 bytes/param**. Add 2-byte bf16 weights and gradients and a 4-byte fp32 master copy under [[Concept - Mixed Precision Training]], and the optimizer states dominate the ~16 bytes/param training footprint (full accounting in [[Reference - Memory Math for Transformers]]). A 70B model carries 560 GB of Adam state alone. That's what [[Concept - Data Parallelism and ZeRO]] stage 1 shards first, and why 8-bit optimizer states exist. Sharding, fused kernels and bf16 states belong to [[Concept - AdamW at Scale]].
- **When Adam wins:** transformers, embeddings, anything with sparse or heavy-tailed gradients and per-layer scale disparities. Vision CNNs trained fine on SGD+momentum for a decade. Transformers effectively require Adam-family preconditioning.

## Failure modes

- **Generalization gap vs SGD.** Adam can settle into sharper minima that test worse. It started a five-year argument ([[Lore - The Adam vs SGD Generalization Wars]]), and much of the originally reported gap turned out to be the coupled-L2 artifact AdamW fixed. What flatness buys you is covered in [[Concept - Generalization in Deep Learning]]. Detection: a train/val gap that shrinks when you switch optimizer or fix the decay coupling.
- **Non-convergence, formally.** Reddi et al. 2018 built a convex problem where Adam provably fails because the EMA forgets rare, informative gradients. AMSGrad's $\max$-of-$v$ fixes the counterexample. In deep learning practice it almost never bites, but it killed the original paper's convergence proof.
- **Stale-momentum updates to unused parameters.** Embedding rows absent from the batch still get moved (nonzero $m$) and decayed, so rare tokens drift without any signal. That's part of why embeddings are excluded from weight decay.
- **$\epsilon$ under low precision.** $10^{-8}$ vanishes against fp16's smallest normal ($\sim 6 \times 10^{-5}$), and a tiny $\hat v$ makes the update explode. Large-model configs raise $\epsilon$ to $10^{-6}$/$10^{-5}$ and keep states in fp32. Details in [[Concept - Adam's Epsilon and Bias Correction]].

## The non-obvious

The sign-descent view is the intuition to keep. The update is $\approx \eta \cdot \text{sign}(\text{gradient trend})$ per coordinate, so Adam mostly ignores gradient *magnitude* and responds to gradient *consistency*. Two consequences people learn the hard way:

(1) Loss scale barely matters to Adam. Multiply your loss by 100 and training is nearly unchanged, since $m$ and $\sqrt{v}$ scale together (only $\epsilon$'s relative position moves). Under SGD the same rescaling is a 100x LR change.

(2) Clipping interacts with Adam differently than intuition suggests. A clipped spike still enters $v$ and *suppresses that coordinate's LR for the next $\sim 1/(1-\beta_2)$ steps*. That's a feature (self-quenching after shocks), but with $\beta_2 = 0.999$ it also means one bad batch leaves a multi-hundred-step scar.

## Connections

- [[Concept - Stochastic Gradient Descent and Momentum]] — the substrate: Adam's $m$ *is* momentum; the down-stack prerequisite.
- [[Concept - Adam's Epsilon and Bias Correction]] — the numerical arcana (eps placement, warmup/bias-correction interplay, RAdam) that only bites at scale.
- [[Reference - Optimizer Update Rules]] — the lookup sheet with exact update expressions, defaults, and per-param state bytes.
- [[Lore - The Adam vs SGD Generalization Wars]] — the decade-long fight over the generalization gap and how AdamW mostly ended it.
- [[Concept - Generalization in Deep Learning]] — the flat-vs-sharp-minima framework the Adam-vs-SGD debate was really about.
- [[Reference - Memory Math for Transformers]] — where the 8 bytes/param sits in the full training memory budget.
- [[Concept - Data Parallelism and ZeRO]] — ZeRO exists chiefly to shard Adam's optimizer states across data-parallel ranks.
- [[Concept - AdamW at Scale]] — the engineering layer: sharded/fused/low-precision optimizer states at cluster scale.
- [[Concept - Mixed Precision Training]] — why states stay fp32 while compute runs bf16, and where the master copy fits.

## Sources

- Kingma & Ba (2015) — Adam: A Method for Stochastic Optimization. The update rule and bias correction.
- Loshchilov & Hutter (2019) — Decoupled Weight Decay Regularization. The AdamW fix and the L2-coupling argument.
- Reddi et al. (2018) — On the Convergence of Adam and Beyond. The convex non-convergence counterexample and AMSGrad.
- Wilson et al. (2017) — The Marginal Value of Adaptive Gradient Methods in Machine Learning. Opened the generalization-gap debate.
