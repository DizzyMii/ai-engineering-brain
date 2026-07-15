---
tags: [concept, domain/neural-networks, level/advanced]
aliases: [Adam, AdamW, decoupled weight decay, adaptive moment estimation]
summary: "Adam's moment-EMA update, why AdamW's decoupled decay is not Adam+L2, the 8 bytes/param cost, and the sign-descent intuition."
---

# Concept - Adam and AdamW

> **One-paragraph hook:** AdamW is the optimizer under essentially every model you use *(as of 2026)*. It maintains two exponential moving averages per parameter — a smoothed gradient and a smoothed squared gradient — and divides one by the square root of the other, giving each parameter its own effective learning rate. The two things practitioners chronically get wrong about it: what the "W" actually changes (decoupled weight decay is *not* the same update as L2 regularization under Adam), and what it costs (the optimizer state is the single largest consumer of training memory, bigger than the model itself).

## The mechanism

Adam (Kingma & Ba 2015) tracks first and second moments of the gradient $g_t$ as EMAs, corrects their startup bias, and takes a preconditioned step. Building on the momentum EMA from [[Concept - Stochastic Gradient Descent and Momentum]]:

$$m_t = \beta_1 m_{t-1} + (1-\beta_1)\, g_t \qquad v_t = \beta_2 v_{t-1} + (1-\beta_2)\, g_t^2$$

$$\hat m_t = \frac{m_t}{1-\beta_1^t} \qquad \hat v_t = \frac{v_t}{1-\beta_2^t} \qquad \theta_t = \theta_{t-1} - \eta\, \frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon}$$

Everything is elementwise: each parameter gets its own step size $\eta/\sqrt{\hat v_t}$, large where gradients have been consistently small, small where they've been large or noisy. The bias correction terms $(1-\beta^t)^{-1}$ exist because $m_0 = v_0 = 0$ makes early EMAs underestimates; without correction the first thousands of steps are silently too small (the full arcana — epsilon placement, warmup interaction, RAdam — lives in [[Concept - Adam's Epsilon and Bias Correction]]).

**The AdamW fix** (Loshchilov & Hutter 2019). Classical L2 regularization adds $\lambda\theta$ *to the gradient*, so under Adam it flows through $m$ and gets divided by $\sqrt{\hat v}$ — parameters with large gradient history receive *less* shrinkage, which inverts the regularizer's intent and couples its strength to the loss landscape. AdamW applies decay directly to the weights, outside the adaptive machinery:

$$\theta_t = \theta_{t-1} - \eta \left( \frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon} + \lambda\, \theta_{t-1} \right)$$

Same $\lambda$ for every parameter, uniform multiplicative shrinkage per step, independent of $v$. This is why "Adam+L2" and "AdamW" at identical hyperparameters produce measurably different models, and why weight-decay values don't transfer between the two. The full family of update rules is tabulated in [[Reference - Optimizer Update Rules]].

## In practice

- **Defaults:** $\beta_1 = 0.9$, $\beta_2 = 0.999$, $\epsilon = 10^{-8}$, from the original paper — still right for small models. LLM pretraining runs $\beta_2 = 0.95$: at large batch the gradient estimate is already low-variance, and a ~20-step second-moment memory ($1/(1-\beta_2)$) adapts to curvature shifts faster than a 1000-step one, which materially reduces loss spikes. This is the "0.95 for transformers" folklore, now near-universal in published configs (GPT-3, LLaMA, and descendants). Weight decay $\lambda \approx 0.1$, applied only to matmul weights.
- **Learning rates:** $10^{-3}$ for small nets, $1\text{–}3 \times 10^{-4}$ for LLM pretraining. Because $\hat m/\sqrt{\hat v} \approx \pm 1$ elementwise for a persistent gradient, the per-step update magnitude is roughly *bounded by $\eta$ itself* — Adam behaves like smoothed sign descent. This is why Adam LRs are small, and why they transfer across model scales far better than SGD LRs, where the step scales with raw gradient magnitude.
- **Memory:** $m$ and $v$ in fp32 cost **8 bytes/param** — on top of 2-byte bf16 weights and gradients and a 4-byte fp32 master copy under [[Concept - Mixed Precision Training]], the optimizer states dominate the ~16 bytes/param training footprint (the full accounting is in [[Reference - Memory Math for Transformers]]). A 70B model carries 560 GB of Adam state alone. This is precisely what [[Concept - Data Parallelism and ZeRO]] stage 1 shards first, and why 8-bit optimizer states exist. The at-scale engineering — state sharding, fused kernels, bf16 states — belongs to [[Concept - AdamW at Scale]].
- **When Adam wins:** transformers, embeddings, anything with sparse or heavy-tailed gradients and per-layer scale disparities. Vision CNNs trained fine on SGD+momentum for a decade; transformers effectively require Adam-family preconditioning.

## Failure modes

- **Generalization gap vs SGD** — Adam can settle into sharper minima that test worse, the finding that launched a five-year argument ([[Lore - The Adam vs SGD Generalization Wars]]); much of the originally reported gap turned out to be the coupled-L2 artifact AdamW fixed, and what flatness buys you is the subject of [[Concept - Generalization in Deep Learning]]. **Detection:** train/val gap that shrinks when you switch optimizer or fix decay coupling.
- **Non-convergence, formally** — Reddi et al. 2018 constructed a convex problem where Adam provably fails because the EMA forgets rare, informative gradients; AMSGrad's $\max$-of-$v$ fixes the counterexample. In deep learning practice it almost never bites, but it killed the original paper's convergence proof.
- **Stale-momentum updates to unused parameters** — rows of an embedding not present in the batch still get moved (nonzero $m$) and decayed. Silent drift on rare tokens; part of why embeddings are excluded from weight decay.
- **$\epsilon$ under low precision** — $10^{-8}$ vanishes against fp16's smallest normal ($\sim 6 \times 10^{-5}$), and tiny $\hat v$ makes the update explode; large-model configs raise $\epsilon$ to $10^{-6}$/$10^{-5}$ and keep states in fp32. Details in [[Concept - Adam's Epsilon and Bias Correction]].

## The non-obvious

The sign-descent view is the load-bearing intuition: because the update is $\approx \eta \cdot \text{sign}(\text{gradient trend})$ per coordinate, Adam mostly ignores gradient *magnitude* and responds to gradient *consistency*. Two consequences practitioners learn the hard way: (1) loss scale barely matters to Adam — multiply your loss by 100 and training is nearly unchanged, since $m$ and $\sqrt{v}$ scale together (only $\epsilon$'s relative position moves); the same rescaling under SGD is a 100x LR change. (2) Gradient clipping interacts with Adam differently than intuition suggests — a clipped spike still enters $v$ and *suppresses that coordinate's LR for the next $\sim 1/(1-\beta_2)$ steps*, which is a feature (self-quenching after shocks) but also means one bad batch leaves a multi-hundred-step scar with $\beta_2 = 0.999$.

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
