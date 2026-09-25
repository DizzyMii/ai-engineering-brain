---
tags: [concept, domain/training-at-scale, level/frontier]
aliases: [Shampoo, SOAP, Lion, Kronecker-factored optimizers, preconditioned optimizers]
summary: "Shampoo, SOAP, and Lion trade AdamW's cheap diagonal update for curvature-aware or memory-lean alternatives at LLM scale."
---

# Concept - Second-Order Optimizers at Scale

> **One-paragraph hook:** [[Concept - AdamW at Scale|AdamW's]] diagonal preconditioner is blind to cross-parameter curvature. It scales each weight coordinate by its own running gradient variance and never sees how coordinates within a layer move together. Shampoo and its descendant SOAP buy some of that curvature information back with a Kronecker-factored per-layer preconditioner. Lion goes the other way and buys memory back by dropping the second moment entirely. All three are frontier 2018-2024 attempts to beat AdamW's steps-to-target at real LLM scale, and their wins are real but narrower than they sound.

## The mechanism

**Shampoo** (Gupta et al. 2018) approximates full-matrix Adagrad, which would need an intractable $mn \times mn$ preconditioner for an $m\times n$ weight $W$, with a Kronecker factorization. It keeps two small statistics matrices, $L \in \mathbb{R}^{m\times m}$ (an accumulation of $G G^T$) and $R \in \mathbb{R}^{n\times n}$ (an accumulation of $G^T G$), and updates as:

$$W_{t+1} = W_t - \eta \, L_t^{-1/4} \, G_t \, R_t^{-1/4}$$

Applying the fourth-root inverses of $L$ and $R$ on either side of the gradient approximates the inverse square root of the full preconditioner, via $L \otimes R \approx$ (full Adagrad preconditioner). Distributed Shampoo (Anil et al. 2020, used at Google) makes this tractable at LLM scale three ways: (1) it computes the expensive matrix inverse-root only every ~100+ steps and reuses a stale root in between, amortizing the $O(m^3)$/$O(n^3)$ eigendecomposition cost; (2) it blocks large matrices into smaller sub-blocks so $L$/$R$ stay small; (3) it shards the $L$/$R$ factors across ranks the same way [[Concept - Data Parallelism and ZeRO]] shards Adam's $m,v$.

**SOAP** (Vyas et al. 2024, "SOAP: Improving and Stabilizing Shampoo using Adam") uses the same statistics differently. It rotates the gradient into Shampoo's eigenbasis (derived from the same $L$/$R$ factors) and runs plain Adam's per-coordinate update *inside* that rotated basis, skipping Shampoo's direct inverse-root update. That pairs Shampoo's curvature-aware basis with Adam's cheap, well-understood update, needs fewer delicate extra hyperparameters (no separate root-order or damping schedule to tune), and it stays competitive on wall-clock.

**Lion** (Chen et al. 2023, "Symbolic Discovery of Optimization Algorithms") came out of an automated symbolic search over update-rule programs; nobody derived it analytically. Its update is sign-based where Adam's is magnitude-based:

```python
c = beta1 * m + (1 - beta1) * g          # interpolated momentum for this step's direction
W = W - lr * (sign(c) + wd * W)          # update magnitude is uniform per coordinate
m = beta2 * m + (1 - beta2) * g          # momentum buffer carried forward (only buffer stored)
```

Lion stores one momentum buffer $m$ and no second moment $v$, which halves Adam's optimizer-state memory. But `sign(c)` has a much smaller and more uniform effective magnitude than a raw gradient or an Adam-normalized update. So Lion needs a markedly smaller LR (roughly 3-10x smaller than the AdamW LR it replaces) and typically larger weight decay to compensate.

## In practice

For Shampoo, the preconditioner matmuls and periodic inverse-root computation add roughly 10-40% wall-clock overhead per step, plus memory for the $L$, $R$ factors (small relative to the weight matrix if blocked well). In return it can meaningfully cut steps to a target loss. Distributed Shampoo won an MLCommons AlgoPerf training-algorithm track, a controlled steps-to-target competition across a fixed suite of workloads, and variants are reportedly used in some Google production training runs.

The eigh/inverse-root computation is the expensive $O(n^3)$ part. It runs only every 100+ steps, with a stale preconditioner reused in between, and large weight matrices are blocked into smaller chunks so this cost stays tractable at transformer-scale matrix dimensions.

Lion needs half of Adam's optimizer memory ($m$ only, no $v$). That matters at the scale where the 12-bytes/param Adam state is the biggest memory line item, the one [[Concept - Data Parallelism and ZeRO|ZeRO]] exists partly to shard. But at LLM pretraining scale Lion sometimes matches AdamW and sometimes clearly underperforms it. It hasn't displaced AdamW as a default, though it briefly threatened to in the smaller vision-model literature.

## Failure modes

- **Shampoo numerical issues in the inverse-root computation.** An ill-conditioned $L$ or $R$ (a direct symptom of a badly-conditioned layer; see [[Concept - The Condition Number]]) makes the fourth-root inversion numerically unstable unless you compute it in fp32 with damping, adding a small $\epsilon I$ before inverting. Skimp on precision here and the preconditioner gets corrupted without any crash.
- **Block-size vs accuracy tradeoff.** Blocking a large matrix too coarsely approximates the per-layer curvature poorly (converging toward plain Adam). Blocking too finely blows the compute/memory budget the method exists to control. It's a real tunable, not set-and-forget.
- **Lion's LR/weight-decay retuning is mandatory.** An AdamW-tuned LR on Lion reliably diverges, because the sign update's effective step size behaves very differently from AdamW's roughly gradient-magnitude-normalized step. A lot of "Lion doesn't work" bring-up reports turn out to be an un-retuned LR.
- **Stale preconditioners at the wrong moment.** If the refresh interval is too long for how fast curvature is changing (early in training, right after a [[Concept - Training Stability and Loss Spikes|loss spike]], or right after an LR schedule inflection), the reused inverse-root can point the wrong way for a stretch of steps. It shows up as a stall or minor divergence that clears once the preconditioner refreshes.

## The non-obvious

The AlgoPerf win is real but narrower than it sounds. It's a controlled steps-to-target benchmark on fixed workloads and hardware. It doesn't demonstrate a wall-clock or dollar win on a frontier-scale pretraining run with sharding, cross-device communication, and bf16/fp8 numerical stability layered on top. Winning a benchmark that holds workload and hardware fixed is a long way from being worth adopting on a run costing tens of millions of dollars, where every systems interaction has to be re-validated from scratch. So AdamW remains the default outside a handful of labs willing to pay the integration cost. My takeaway: second-order methods reliably buy steps-to-target, but not necessarily GPU-hours-to-target once you price in per-step overhead and the risk of integrating a new optimizer.

## Connections
- [[Concept - AdamW at Scale]] — the incumbent default these preconditioned and sign-based methods are measured against, and, for SOAP, partly built from.
- [[Concept - Muon Optimizer]] — a cheaper, matmul-only alternative that captures a related whitening effect for 2D matrices without Shampoo's explicit preconditioner.
- [[Concept - Adam and AdamW]] — the base diagonal-preconditioner update rule that Shampoo's factored preconditioner and Lion's sign update both depart from.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — Shampoo's $L$, $R$ factor computation and inverse-root are themselves matmul- and decomposition-heavy operations layered on top of every step.
- [[Reference - LLM Pretraining Hyperparameters]] — where Shampoo/SOAP/Lion's LR, damping, and refresh-interval values sit alongside AdamW's defaults.
- [[Concept - Training Stability and Loss Spikes]] — a stale Shampoo preconditioner right after a spike, or Lion's narrower LR margin, are stability failure modes distinct from AdamW's.
- [[Concept - The Condition Number]] — the exact ill-conditioning that makes Shampoo's inverse-root computation numerically fragile without damping.
- [[Concept - The Hessian Spectrum in Deep Learning]] — Shampoo's Kronecker-factored preconditioner is an explicit, cheap approximation to the curvature this note describes in full generality.

## Sources
- Gupta et al. (2018) — "Shampoo: Preconditioned Stochastic Tensor Optimization" — introduces the Kronecker-factored preconditioner.
- Anil et al. (2020) — "Scalable Second Order Optimization for Deep Learning" — the distributed Shampoo implementation used at production scale, with amortized inverse-roots and blocking.
- Vyas et al. (2024) — "SOAP: Improving and Stabilizing Shampoo using Adam" — runs Adam inside Shampoo's eigenbasis.
- Chen et al. (2023) — "Symbolic Discovery of Optimization Algorithms" — introduces Lion via automated program search over optimizer update rules.
