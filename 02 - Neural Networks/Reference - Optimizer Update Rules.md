---
tags: [reference, domain/neural-networks, level/advanced]
aliases: [optimizer cheat sheet, update rule table]
summary: "Lookup sheet of optimizer update equations, default hyperparameters, and per-parameter memory cost, from SGD through Adafactor."
---

# Reference - Optimizer Update Rules

*State variables, per-step update expressions and default hyperparameters for the optimizers used in [[Concept - Stochastic Gradient Descent and Momentum]] and [[Concept - Adam and AdamW]]. Numbers are date-stamped (as of 2026). Derivations and intuition live in those concept notes.*

## Table 1: update rules

$g_t$ is the gradient, $\theta_t$ the parameter, $\eta$ the learning rate. Operations on vector state ($m, v, G$) are elementwise.

| Optimizer | State | Update |
|---|---|---|
| SGD | none | $\theta_t = \theta_{t-1} - \eta\, g_t$ |
| SGD + Momentum | $v$ | $v_t = \mu v_{t-1} + g_t$; $\quad \theta_t = \theta_{t-1} - \eta\, v_t$ |
| Nesterov (Sutskever form) | $v$ | $v_t = \mu v_{t-1} + g_t$; $\quad \theta_t = \theta_{t-1} - \eta\,(g_t + \mu v_t)$ |
| Adagrad | $G$ (sum of squares) | $G_t = G_{t-1} + g_t^2$; $\quad \theta_t = \theta_{t-1} - \eta\, g_t / (\sqrt{G_t} + \epsilon)$ |
| RMSProp | $v$ (EMA of squares) | $v_t = \rho v_{t-1} + (1-\rho) g_t^2$; $\quad \theta_t = \theta_{t-1} - \eta\, g_t / (\sqrt{v_t} + \epsilon)$ |
| Adam | $m, v$ | $m_t = \beta_1 m_{t-1} + (1-\beta_1) g_t$, $\; v_t = \beta_2 v_{t-1} + (1-\beta_2) g_t^2$; bias-correct $\hat m_t, \hat v_t$; $\quad \theta_t = \theta_{t-1} - \eta\, \hat m_t / (\sqrt{\hat v_t} + \epsilon)$ |
| AdamW | $m, v$ | Adam's update **plus** decoupled decay: $\quad \theta_t = \theta_{t-1} - \eta\left(\hat m_t/(\sqrt{\hat v_t}+\epsilon) + \lambda\theta_{t-1}\right)$ |
| Nadam | $m, v$ | Adam with Nesterov-style lookahead applied to $\hat m_t$ before the division (Dozat 2016) |
| Adafactor | factored $v$ (row + col sums, no $m$ by default) | Reconstructs an approximate $v$ from rank-1 row/column accumulators instead of storing the full second-moment tensor (Shazeer & Stern 2018) |

## Table 2: default hyperparameters (as of 2026)

| Optimizer | Learning rate | Momentum / $\beta_1$ | $\beta_2$ / $\rho$ | $\epsilon$ | Weight decay |
|---|---|---|---|---|---|
| SGD + Momentum (vision) | ~0.1 | 0.9 | — | — | 1e-4 (L2) |
| Adam/AdamW, small nets | 1e-3 | 0.9 | 0.999 | 1e-8 | 0.01 |
| AdamW, LLM pretraining | 1e-4 – 3e-4 | 0.9 | 0.95 | 1e-6 – 1e-5 | 0.1 |
| RMSProp | 1e-3 | — | 0.9 (a.k.a. $\rho$) | 1e-8 | — |
| Adafactor | relative step size, ~1e-2 scale | — | 0.8 – 0.999 (decayed) | 1e-30 (inside sqrt) | 0.0 typical |

The $\beta_2 = 0.95$ LLM-pretraining default swaps a ~2000-step second-moment memory ($1/(1-\beta_2)$ at $0.999$) for a ~20-step one. You get faster, more stable adaptation at large batch and fewer loss spikes; see [[Concept - Adam and AdamW]].

## Table 3: optimizer-state memory per parameter

Assumes fp32 optimizer state, which is the norm even under bf16/fp16 compute ([[Concept - Mixed Precision Training]]).

| Optimizer | Extra state bytes/param | Notes |
|---|---|---|
| SGD | 0 | No persistent state beyond the weight itself |
| SGD + Momentum / Nesterov | 4 | One fp32 buffer ($v$) |
| Adagrad | 4 | One fp32 buffer ($G$) that only grows, so the effective LR decays to 0 over training |
| RMSProp | 4 | One fp32 buffer ($v$) |
| Adam / AdamW | 8 | $m$ + $v$, both fp32; dominates training memory. Full accounting in [[Reference - Memory Math for Transformers]] |
| Nadam | 8 | Same as Adam |
| Adafactor | ≪8, sublinear | $O(d_{\text{in}} + d_{\text{out}})$ per matrix instead of $O(d_{\text{in}} \cdot d_{\text{out}})$, which is the point of the design; mild quality cost vs. full Adam |

A 70B-parameter model under AdamW carries **560 GB** of optimizer state alone (8 bytes × 70B). That's the largest single line item in LLM training memory, and it's what [[Concept - Data Parallelism and ZeRO]] stage-1 sharding goes after first. [[Concept - AdamW at Scale]] covers the engineering response: sharded, fused and 8-bit optimizer states.

## Footnotes

- **Epsilon placement.** Adam adds $\epsilon$ *outside* the square root, $\hat m_t/(\sqrt{\hat v_t}+\epsilon)$. LAMB and some variants add it *inside*, $\hat m_t/\sqrt{\hat v_t + \epsilon}$. The two differ a lot when $\hat v_t$ is tiny, which makes this a silent cross-framework reproducibility trap. Full treatment in [[Concept - Adam's Epsilon and Bias Correction]].
- **Coupled vs. decoupled decay.** "Adam + L2" folds $\lambda\theta$ into the gradient before it reaches $m$ and $v$, so the per-coordinate $1/\sqrt{v}$ scaling distorts what should be uniform shrinkage. AdamW applies $\lambda\theta$ directly to the weights, outside the adaptive scaling. At matched $\lambda$ the two are *not* interchangeable; see [[Concept - Adam and AdamW]].
- **Mixed precision still needs fp32 state.** With forward/backward in bf16 or fp16, $m$, $v$ and the master weight copy stay fp32, because low-precision accumulation underflows the small updates these buffers exist to track. Details in [[Concept - Mixed Precision Training]].

## Connections

- [[Concept - Adam and AdamW]] — the derivation and intuition behind the Adam/AdamW rows: the moment EMAs, bias correction, and the decoupled-decay argument.
- [[Concept - Stochastic Gradient Descent and Momentum]] — the substrate every adaptive method here builds on; the down-stack prerequisite for this table.
- [[Reference - Memory Math for Transformers]] — where Table 3's 8 bytes/param sits inside the full training memory budget (weights, gradients, activations, state).
- [[Concept - Mixed Precision Training]] — why optimizer state stays fp32 while compute runs low-precision, and where the master-weight copy fits.
- [[Concept - Data Parallelism and ZeRO]] — ZeRO stage-1 exists chiefly to shard Table 3's 8-bytes/param Adam state across data-parallel ranks.
- [[Concept - Adam's Epsilon and Bias Correction]] — the numerical arcana behind the epsilon-placement footnote: precision underflow, bias-correction/warmup interaction, RAdam.
- [[Concept - AdamW at Scale]] — the at-scale engineering layer this reference stops short of: sharded, fused, and low-precision optimizer states across a cluster.

## Sources

- Kingma & Ba (2015) — Adam: A Method for Stochastic Optimization. The Adam update rule and bias correction.
- Loshchilov & Hutter (2019) — Decoupled Weight Decay Regularization. The AdamW fix and the coupled-L2 argument.
- Duchi, Hazan & Singer (2011) — Adaptive Subgradient Methods for Online Learning and Stochastic Optimization. Adagrad.
- Tieleman & Hinton (2012) — Lecture 6.5, Coursera: Neural Networks for Machine Learning. RMSProp's original (unpublished-paper, widely-cited lecture) source.
- Dozat (2016) — Incorporating Nesterov Momentum into Adam. Nadam.
- Shazeer & Stern (2018) — Adafactor: Adaptive Learning Rates with Sublinear Memory Cost.
