---
tags: [concept, domain/training-at-scale, level/core]
aliases: [distributed AdamW, sharded Adam, decoupled weight decay at scale]
summary: "Engineering AdamW for LLM pretraining: decoupled decay, the beta2=0.95 folklore, fused kernels, and the 12 bytes/param it costs."
---

# Concept - AdamW at Scale

> **One-paragraph hook:** AdamW is a five-line update rule you could implement in an afternoon. Getting it right for a trillion-token pretraining run is still most of what separates a stable loss curve from a career-defining incident. The hard engineering is outside the math: the memory it eats, the betas nobody derives but everybody copies, and a dozen small decisions the original paper never mentions (which params get decay, what happens on a NaN gradient, how the state gets sharded).

## The mechanism

[[Concept - Adam and AdamW]] covers the base per-parameter update. At LLM-pretraining scale, what changes is how that update is engineered around a cluster. The decoupled-decay form (Loshchilov & Hutter, 2017) is:

$$m_t = \beta_1 m_{t-1} + (1-\beta_1) g_t \qquad v_t = \beta_2 v_{t-1} + (1-\beta_2) g_t^2$$
$$\hat m_t = \frac{m_t}{1-\beta_1^t} \qquad \hat v_t = \frac{v_t}{1-\beta_2^t}$$
$$\theta_t = \theta_{t-1} - \eta\left(\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon} + \lambda\,\theta_{t-1}\right)$$

The last term is what the "W" is for. Decay is applied straight to the weight instead of being folded into $g_t$ before the adaptive scaling touches it. Fold it in (plain L2 regularization) and the adaptive per-parameter learning rate scales the decay term too, so parameters with a large gradient history get decayed less. That's an arithmetic accident, not a design choice. Decoupling makes decay strength independent of the Adam denominator; typical $\lambda = 0.1$.

At scale, three engineering layers sit on top of the formula:

- **Kernel fusion.** A 70B-parameter model has hundreds of distinct weight tensors, and one CUDA kernel launch per tensor per step is pure overhead. Fused (single-kernel) or foreach (batched-launch) optimizer implementations update every parameter tensor in one or a handful of launches.
- **Clipping on the fully accumulated gradient.** Global-norm clipping (usually to 1.0) has to happen after [[Concept - Gradient Accumulation and Microbatching]] sums every microbatch and after the [[Concept - Data Parallelism and ZeRO]] all-reduce. Clip per microbatch and the effective threshold silently changes with the accumulation window.
- **Param groups.** 1D parameters (layernorm/RMSNorm gains, biases, often embeddings) are excluded from weight decay by putting them in a separate optimizer param group with $\lambda=0$. Nobody derives this from first principles. It gets copied run to run because decaying a normalization gain toward zero measurably hurts.

## In practice

The betas are the most-copied, least-explained hyperparameter in the field. $\beta_1=0.9$, $\beta_2=0.95$ (not PyTorch's default of 0.999) is near-universal LLM folklore, used by GPT-3, OPT and PaLM. A lower $\beta_2$ makes the second-moment estimate follow recent gradient variance faster, which damps the run's sensitivity to any single bad batch. That matters directly for [[Concept - Training Stability and Loss Spikes]]. $\epsilon=10^{-8}$ is standard, with occasional $10^{-15}$ experiments for extra-low-precision setups.

Memory is the other reason this note is separate from the base Adam concept. The optimizer keeps fp32 $m$ and $v$ (4 bytes each) plus an fp32 master-weight copy (4 bytes): **12 bytes/param** on top of the 2-byte bf16 working weight and the 2-4 byte gradient. [[Concept - Data Parallelism and ZeRO]] shards that 12 bytes/param across ranks starting at ZeRO-1, because it's the largest single contributor to the memory wall in [[Concept - Why Models Don't Fit on One GPU]]. For a 70B model that's roughly 840GB of optimizer state before a single activation is stored. AdamW remains the default optimizer for production pretraining as of 2026. Challengers like [[Concept - Muon Optimizer]] and other [[Concept - Second-Order Optimizers at Scale]] aim to beat its cheap diagonal preconditioner but haven't displaced it at frontier scale.

## Failure modes

- **Weight decay on the wrong params.** Decaying layernorm gains or embedding rows toward zero degrades quality in a way that looks like a bad learning rate, so it's easy to misdiagnose as one.
- **Epsilon swamping in bf16.** When $\sqrt{\hat v_t}$ is tiny and $\epsilon$ is comparable in magnitude to the update in low precision, the update rounds away entirely. This interacts with the mantissa-width limits in [[Concept - Floating Point for Deep Learning]] and shows up as parameters that silently stop moving.
- **Skipping gradient clipping.** No global-norm clip, or a clip applied per microbatch instead of on the accumulated gradient, invites the spikes cataloged in [[Concept - Training Stability and Loss Spikes]].
- **Unsharded optimizer state.** Plain AdamW on a model whose 12-bytes/param budget doesn't fit on one device OOMs at optimizer init, before step 0 of forward. That signature differs from an activation-memory OOM.

## The non-obvious

Every major lab excludes 1D parameters from weight decay, and it's almost never written down in a paper. You learn it from someone else's training config, or by watching a run degrade without it. More broadly, $\beta_2$, warmup length ([[Concept - Learning Rate Schedules for Pretraining]]) and the clip threshold aren't independent knobs. The single most common cause of an early spike is a short warmup while Adam's second-moment estimate is still "unconfident" from too few steps. The folklore fix, dropping $\beta_2$ to 0.95, works because it shortens the denominator's effective memory. There's nothing magic about 0.95.

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
