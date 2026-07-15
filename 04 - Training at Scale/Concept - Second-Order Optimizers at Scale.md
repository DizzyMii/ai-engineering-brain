---
tags: [concept, domain/training-at-scale, level/frontier]
aliases: [Shampoo, SOAP, Lion, Kronecker-factored optimizers, preconditioned optimizers]
summary: "Shampoo, SOAP, and Lion trade AdamW's cheap diagonal update for curvature-aware or memory-lean alternatives at LLM scale."
---

# Concept - Second-Order Optimizers at Scale

> **One-paragraph hook:** [[Concept - AdamW at Scale|AdamW's]] diagonal preconditioner is blind to cross-parameter curvature — it scales every weight coordinate by its own running gradient variance and never sees how coordinates within a layer move together. Shampoo and its descendant SOAP buy some of that missing curvature information back with a Kronecker-factored per-layer preconditioner; Lion goes the opposite direction and buys memory back by discarding the second moment entirely. All three are frontier 2018-2024 attempts to beat AdamW's steps-to-target at real LLM scale, with real but narrower-than-they-sound wins.

## The mechanism

**Shampoo** (Gupta et al. 2018) approximates full-matrix Adagrad — which would need an intractable $mn \times mn$ preconditioner for an $m\times n$ weight $W$ — with a Kronecker factorization. It maintains two small statistics matrices, $L \in \mathbb{R}^{m\times m}$ (an accumulation of $G G^T$) and $R \in \mathbb{R}^{n\times n}$ (an accumulation of $G^T G$), and updates as:

$$W_{t+1} = W_t - \eta \, L_t^{-1/4} \, G_t \, R_t^{-1/4}$$

The fourth-root inverses of $L$ and $R$, applied on either side of the gradient, approximate the inverse square root of the full preconditioner via $L \otimes R \approx$ (full Adagrad preconditioner). Distributed Shampoo (Anil et al. 2020, used at Google) makes this tractable at LLM scale three ways: (1) computing the expensive matrix inverse-root only every ~100+ steps and reusing a stale root in between, amortizing the $O(m^3)$/$O(n^3)$ eigendecomposition cost; (2) blocking large matrices into smaller sub-blocks so $L$/$R$ stay small; and (3) sharding the $L$/$R$ factors themselves across ranks the same way [[Concept - Data Parallelism and ZeRO]] shards Adam's $m,v$.

**SOAP** (Vyas et al. 2024, "SOAP: Improving and Stabilizing Shampoo using Adam") reframes the same statistics: instead of applying Shampoo's inverse-root update directly, it rotates the gradient into Shampoo's eigenbasis (derived from the same $L$/$R$ factors) and then runs plain Adam's per-coordinate update *inside* that rotated basis. This combines Shampoo's curvature-aware basis with Adam's cheap, well-understood per-step update, and needs fewer delicate extra hyperparameters (no separate root-order or damping schedule to tune) while staying competitive on wall-clock.

**Lion** (Chen et al. 2023, "Symbolic Discovery of Optimization Algorithms") was found by an automated symbolic search over update-rule programs rather than derived analytically. Its update is strikingly simple — sign-based rather than magnitude-based:

```python
c = beta1 * m + (1 - beta1) * g          # interpolated momentum for this step's direction
W = W - lr * (sign(c) + wd * W)          # update magnitude is uniform per coordinate
m = beta2 * m + (1 - beta2) * g          # momentum buffer carried forward (only buffer stored)
```

Lion stores a single momentum buffer $m$ — no second moment $v$ — halving Adam's optimizer-state memory. But `sign(c)` has a much smaller and more uniform effective magnitude than a raw gradient or an Adam-normalized update, so Lion needs a markedly smaller LR (roughly 3-10x smaller than the AdamW LR it replaces) and typically larger weight decay to compensate.

## In practice

Cost/benefit for Shampoo: the preconditioner matmuls plus periodic inverse-root computation add roughly 10-40% wall-clock overhead per step and extra memory for the $L$, $R$ factors (small relative to the weight matrix if blocked well), but can meaningfully cut the number of steps needed to reach a target loss. Distributed Shampoo won an MLCommons AlgoPerf training-algorithm track — a controlled steps-to-target competition across a fixed suite of workloads — and variants are reportedly used in some Google production training runs.

The eigh/inverse-root computation (the expensive $O(n^3)$ part) is deliberately done only every 100+ steps and reused as a stale preconditioner in between; large weight matrices are blocked into smaller chunks specifically so this cost stays tractable at transformer-scale matrix dimensions.

Lion's practical footprint is half of Adam's optimizer memory ($m$ only, no $v$) — which matters at the scale where the 12-bytes/param Adam state is the dominant memory line item that [[Concept - Data Parallelism and ZeRO|ZeRO]] exists partly to shard. But Lion sometimes matches AdamW and sometimes clearly underperforms it at LLM pretraining scale, so it hasn't displaced AdamW as a default the way it briefly threatened to in smaller vision-model literature.

## Failure modes

- **Shampoo numerical issues in the inverse-root computation.** An ill-conditioned $L$ or $R$ — a direct symptom of a badly-conditioned layer, see [[Concept - The Condition Number]] — makes the fourth-root inversion numerically unstable unless computed in fp32 with damping (adding a small $\epsilon I$ before inverting); skimping on precision here silently corrupts the preconditioner rather than crashing outright.
- **Block-size vs accuracy tradeoff.** Too-coarse blocking of a large matrix approximates the true per-layer curvature poorly (converging toward plain Adam); too-fine blocking blows the compute/memory budget the whole method exists to control. This is a real tunable, not a set-and-forget default.
- **Lion's LR/weight-decay retuning is mandatory.** Reusing an AdamW-tuned LR with Lion reliably diverges, because the sign-update's effective step size is a fundamentally different animal from AdamW's roughly gradient-magnitude-normalized step. A common "Lion doesn't work" bring-up report is actually just an un-retuned LR.
- **Stale preconditioners at the wrong moment.** If the refresh interval is too long relative to how fast the loss landscape's curvature is changing — early in training, right after a [[Concept - Training Stability and Loss Spikes|loss spike]], or right after an LR schedule inflection — the reused inverse-root can actively point the wrong way for a stretch of steps, showing up as a stall or minor divergence that resolves once the preconditioner refreshes.

## The non-obvious

The AlgoPerf win is real but narrower than it sounds: it's a controlled steps-to-target benchmark across fixed workloads and hardware, not a demonstrated wall-clock or dollar win on a frontier-scale pretraining run with sharding, cross-device communication, and bf16/fp8 numerical stability all layered on top. The gap between "wins a benchmark that holds workload and hardware fixed" and "worth adopting for a run costing tens of millions of dollars where every systems interaction has to be re-validated from scratch" is exactly why AdamW, not Shampoo, remains the default outside a handful of labs willing to eat that integration cost. The practical lesson: second-order methods reliably buy steps-to-target, but not necessarily GPU-hours-to-target, once the per-step overhead and new-optimizer integration risk are priced in.

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
