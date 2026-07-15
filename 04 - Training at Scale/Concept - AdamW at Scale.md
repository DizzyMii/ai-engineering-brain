---
tags: [concept, domain/training-at-scale, level/core]
aliases: [distributed AdamW, sharded Adam, decoupled weight decay at scale]
summary: "Engineering AdamW for LLM pretraining: decoupled decay, the beta2=0.95 folklore, fused kernels, and the 12 bytes/param it costs."
---

# Concept - AdamW at Scale

> **One-paragraph hook:** AdamW is a five-line update rule you could implement in an afternoon, and yet getting it right for a trillion-token pretraining run is most of what separates a stable loss curve from a career-defining incident. The interesting engineering isn't the math — it's the memory it eats, the betas nobody derives but everybody copies, and the dozen small decisions (which params get decay, what happens on a NaN gradient, how the state gets sharded) that the original paper never mentions.

## The mechanism

[[Concept - Adam and AdamW]] already covers the base per-parameter update; what changes at LLM-pretraining scale is how that update gets engineered around a cluster. The decoupled-decay form (Loshchilov & Hutter, 2017) is:

$$m_t = \beta_1 m_{t-1} + (1-\beta_1) g_t \qquad v_t = \beta_2 v_{t-1} + (1-\beta_2) g_t^2$$
$$\hat m_t = \frac{m_t}{1-\beta_1^t} \qquad \hat v_t = \frac{v_t}{1-\beta_2^t}$$
$$\theta_t = \theta_{t-1} - \eta\left(\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon} + \lambda\,\theta_{t-1}\right)$$

The last term is the whole point of the "W": decay is applied straight to the weight, not folded into $g_t$ before the adaptive scaling touches it. Fold it in instead (plain L2 regularization) and the adaptive per-parameter learning rate scales the decay term too, so parameters with a large gradient history get decayed less — an arithmetic accident, not a design choice. Decoupling makes decay strength independent of the Adam denominator; typical $\lambda = 0.1$.

Three engineering layers sit on top of this formula at scale:

- **Kernel fusion.** A 70B-parameter model has hundreds of distinct weight tensors; launching one CUDA kernel per tensor per step is pure overhead. Fused (single-kernel) or foreach (batched-launch) optimizer implementations apply the update to every parameter tensor in one or a handful of launches instead.
- **Clipping on the fully accumulated gradient.** Global-norm clipping (usually to 1.0) has to happen after [[Concept - Gradient Accumulation and Microbatching]] sums every microbatch and after the [[Concept - Data Parallelism and ZeRO]] all-reduce — never per microbatch, or the effective clip threshold silently changes with the accumulation window.
- **Param groups.** Weight decay is excluded from 1D parameters — layernorm/RMSNorm gains, biases, and often embeddings — by routing them into a separate optimizer param group with $\lambda=0$. Nobody derives this from first principles; it's copied run to run because decaying a normalization gain toward zero measurably hurts.

## In practice

The betas are the most-copied, least-explained hyperparameter in the field: $\beta_1=0.9$, $\beta_2=0.95$ (not PyTorch's default of 0.999) is near-universal LLM folklore, used by GPT-3, OPT, and PaLM. A lower $\beta_2$ makes the second-moment estimate track recent gradient variance faster, which damps the run's sensitivity to any single bad batch — directly relevant to [[Concept - Training Stability and Loss Spikes]]. $\epsilon=10^{-8}$ is standard, with occasional $10^{-15}$ experiments for extra-low-precision setups.

Memory is the other reason this note exists separately from the base Adam concept: the optimizer keeps fp32 $m$ and $v$ (4 bytes each) plus an fp32 master-weight copy (4 bytes) — **12 bytes/param** on top of the 2-byte bf16 working weight and 2-4 byte gradient. That 12 bytes/param is exactly the state [[Concept - Data Parallelism and ZeRO]] shards across ranks starting at ZeRO-1, because it's the largest single contributor to the memory wall in [[Concept - Why Models Don't Fit on One GPU]] — for a 70B model, roughly 840GB of pure optimizer state before a single activation is stored. AdamW remains the default optimizer for production pretraining as of 2026; challengers like [[Concept - Muon Optimizer]] and other [[Concept - Second-Order Optimizers at Scale]] aim to beat its cheap diagonal preconditioner but haven't displaced it at frontier scale.

## Failure modes

- **Weight decay applied to the wrong params.** Decaying layernorm gains or embedding rows toward zero degrades quality in ways that look like a bad learning rate, not a bad decay config — an easy misdiagnosis.
- **Epsilon swamping in bf16.** When $\sqrt{\hat v_t}$ is tiny and $\epsilon$ is comparable in magnitude to the update in low precision, the update rounds away entirely; this interacts with [[Concept - Floating Point for Deep Learning]]'s mantissa-width limits and shows up as parameters that silently stop moving.
- **Skipping gradient clipping.** No global-norm clip — or a clip applied per microbatch instead of on the accumulated gradient — invites exactly the spikes cataloged in [[Concept - Training Stability and Loss Spikes]].
- **Unsharded optimizer state.** Running plain (unsharded) AdamW on a model too large for the 12-bytes/param budget to fit on one device OOMs at optimizer-init time, not at step 0 of forward — a distinct failure signature from an activation-memory OOM.

## The non-obvious

Excluding 1D parameters from weight decay is standard practice at every major lab and almost never written down in a paper — you learn it by reading someone else's training config, or by watching a run degrade without it. More broadly, $\beta_2$, warmup length ([[Concept - Learning Rate Schedules for Pretraining]]), and the clip threshold are not independent knobs: a short warmup combined with Adam's second-moment estimate still "unconfident" from too few steps is the single most common cause of an early spike, and the folklore fix (drop $\beta_2$ to 0.95) works precisely because it shortens the denominator's effective memory — not because 0.95 is a magic number.

## Connections
- [[Concept - Adam and AdamW]] — the base per-parameter update rule this note engineers around a cluster.
- [[Concept - Gradient Accumulation and Microbatching]] — clipping and decay must be applied on the fully accumulated gradient, not per microbatch.
- [[Concept - Data Parallelism and ZeRO]] — the sharding mechanism that spreads AdamW's 12 bytes/param across ranks.
- [[Concept - Training Stability and Loss Spikes]] — a mistuned beta2/clip/warmup combination is a leading cause of the spikes this note exists to prevent.
- [[Concept - Why Models Don't Fit on One GPU]] — AdamW's optimizer state is the single largest line item in the memory budget that note derives.
- [[Concept - Floating Point for Deep Learning]] — epsilon swamping is a direct consequence of bf16's narrow mantissa.
- [[Concept - Learning Rate Schedules for Pretraining]] — warmup length and peak LR are tuned jointly with beta2 to avoid early instability.
- [[Concept - Muon Optimizer]] — the frontier alternative that replaces AdamW's diagonal preconditioner with an orthogonalized update for some layers.
- [[Concept - Second-Order Optimizers at Scale]] — where curvature-aware methods attempt to beat AdamW's cheap diagonal approximation.
- [[Reference - LLM Pretraining Hyperparameters]] — the lookup table of the exact beta/decay/clip values real published runs used.

## Sources
- Loshchilov & Hutter (2017) — "Decoupled Weight Decay Regularization" — introduces AdamW and shows decoupling decay from the adaptive gradient update improves generalization over L2-regularized Adam.
- Kingma & Ba (2015) — "Adam: A Method for Stochastic Optimization" — the base optimizer AdamW's decay term is added to.
- Brown et al. (2020) — "Language Models are Few-Shot Learners" (GPT-3) — an early large-scale run documenting beta2=0.95 and global-norm clipping at 1.0 as pretraining defaults.
