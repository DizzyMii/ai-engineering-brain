---
tags: [concept, domain/neural-networks, level/advanced]
aliases: [LayerNorm, RMSNorm, LN, layer normalization, root mean square normalization]
summary: "Per-token feature normalization: LayerNorm's mean/variance rescale, why RMSNorm dropped re-centering and won, and the fp32 rule."
---

# Concept - RMSNorm and LayerNorm

> **One-paragraph hook:** Every transformer block you'll debug has a normalization layer that rescales each token's activation vector to a fixed magnitude before the expensive sublayers see it. LayerNorm was the incumbent. RMSNorm, which is LayerNorm minus the mean subtraction and the bias, is what LLaMA, T5 and essentially every modern LLM ships *(as of 2026)*. The interesting part is why per-token (not per-batch) normalization made transformers trainable, why dropping re-centering cost nothing, and why this one op has to run in fp32 while everything around it runs bf16.

## The mechanism

**LayerNorm** (Ba et al. 2016) normalizes over the *feature* dimension, separately for every token. For $x \in \mathbb{R}^d$:

$$\mu = \frac{1}{d}\sum_i x_i \qquad \sigma^2 = \frac{1}{d}\sum_i (x_i-\mu)^2 \qquad y = \gamma \odot \frac{x-\mu}{\sqrt{\sigma^2+\epsilon}} + \beta$$

with learnable gain $\gamma$ and bias $\beta$ (both $\in \mathbb{R}^d$). Every statistic comes from a single token's vector, so LayerNorm doesn't depend on batch size. It behaves the same at batch 1, with variable-length sequences, in RNNs and in autoregressive decoding, which are all places where the cross-example statistics of [[Breakdown - Batch Normalization]] break by design.

**RMSNorm** (Zhang & Sennrich 2019) deletes the mean subtraction and $\beta$:

$$y = \frac{x}{\sqrt{\tfrac{1}{d}\sum_i x_i^2 + \epsilon}} \odot \gamma$$

One reduction instead of two, no bias parameters. The paper measured a 7–64% wall-clock speedup on the norm op across models at the same final quality. So LayerNorm's re-centering half was never doing necessary work; rescaling to unit RMS is the whole job.

### Why it stabilizes training

The forward pass becomes invariant to input scale: $\text{RMSNorm}(\alpha x) = \text{RMSNorm}(x)$ for any $\alpha > 0$. Each sublayer gets inputs at a fixed scale however activations drift across depth or training. Going backward, the same property keeps per-layer gradient magnitudes comparable, a major part of the fix stack for [[Concept - Vanishing and Exploding Gradients]]. Where the norms *sit* relative to the residual stream (pre-norm vs post-norm) changes trainability as much as which norm you pick. That placement question belongs to [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]].

The backward pass is sneakier than "divide by sigma." Ignoring $\gamma$, LayerNorm's input gradient is

$$\frac{\partial L}{\partial x} = \frac{1}{\sigma}\Big(\,\bar y - \underbrace{\text{mean}(\bar y)}_{\text{re-centering}} - \hat x \odot \underbrace{\text{mean}(\bar y \odot \hat x)}_{\text{projection onto } \hat x}\Big)$$

where $\bar y$ is the upstream gradient and $\hat x$ the normalized activation. It subtracts both the gradient's mean and its component *along the activation direction*, so the gradient ends up orthogonal to $\hat x$. Beyond rescaling gradients, a norm layer filters out the component that would change the activation's magnitude and leaves only directional updates. RMSNorm keeps the projection term and drops the mean term.

## In practice

- **Configs:** $\epsilon = 10^{-5}$ (GPT-2 lineage, PyTorch default) or $10^{-6}$ (LLaMA, T5); $\gamma$ initialized to 1.0. These matter: an $\epsilon$ mismatch between training and a reimplementation causes small systematic logit drift that shows up as a benchmark regression nobody can localize. Many modern stacks drop LayerNorm's $\beta$ (and all linear-layer biases) even when they keep the mean subtraction, since bias terms turned out to be nearly free to remove.
- **Where it runs:** [[Deep Dive - The Transformer]] has two norms per block (before attention and before the FFN, in pre-norm placement) plus one final norm before the LM head. A 7B model makes ~65 norm calls per forward. Each is cheap; together they're memory-bandwidth-bound. So every serious stack fuses the reduction, the scale and (in fused residual variants) the preceding add into one kernel via [[Concept - Kernel Fusion]]. RMSNorm has a single reduction and fuses tighter, which is part of why "7–64% faster on the op" carries into end-to-end gains.
- **The fp32 rule:** under bf16/fp16 [[Concept - Mixed Precision Training]], the norm's internal statistics are computed in fp32 and cast back down. The sum of squares over $d = 4096$–16384 elements piles up rounding error in half precision. With bf16's 8-bit mantissa, the variance of near-uniform activations can quantize to garbage. fp16 can also overflow in $\sum x_i^2$ ($x_i \sim 100$ at $d{=}8192$ already exceeds 65504 in the sum). [[Concept - Floating Point for Deep Learning]] explains why bf16 and fp16 fail differently. Every production implementation (Megatron, LLaMA reference, PyTorch `F.rms_norm`) upcasts. Hand-rolled ones that don't are a classic slow-divergence bug.

## Failure modes

- **Half-precision statistics.** Symptom: training runs but diverges after thousands of steps, or a reimplementation matches on short sequences and drifts on long ones. Cause: the norm computed natively in bf16/fp16. Detection: diff per-layer activations against an fp32 reference forward; the norm layers diverge first.
- **Gain drift / decayed gains.** Weight decay on $\gamma$ pulls it toward 0 and silently shrinks the residual stream's effective scale. Put $\gamma$ in the no-decay param group. Detection: monitor $\gamma$ norms. A layer whose mean gain drifts far from 1.0 is compensating for something upstream.
- **Wrong-axis normalization.** `LayerNorm(d)` over `(B, T, d)` normalizes the last dim, which is correct. Code ported from CNNs, where the channel dim sits elsewhere, gives a model that trains, badly. Detection: unit-test that output mean/RMS per token is (0,1)/(1) at init.
- **$\epsilon$ inside vs outside the sqrt, and eps-value mismatches** across frameworks. Same class of silent reproducibility trap as optimizer epsilon.

## The non-obvious

The gradient-orthogonalization view explains a surprise. Networks with norms barely care about the *scale* of their weight initialization (the norm eats any constant), but they stay sensitive to its *direction and rank structure*. Normalization partly substitutes for careful init; it doesn't fully replace it. It also means the effective learning rate on a weight matrix behind a norm grows as the weight norm grows ($\partial L/\partial W \propto 1/\lVert W \rVert$ through the scale-invariance), a feedback loop that weight decay regulates in the background. Remove the norm and you have to rebuild all of this by hand with careful init and clipping. [[Concept - Normalization-Free Networks]] do that, and they're still fragile at frontier scale. Choosing among BatchNorm/LayerNorm/RMSNorm/GroupNorm by architecture and batch regime is covered in [[Decision - Choosing a Normalization Layer]].

## Connections

- [[Breakdown - Batch Normalization]] — the predecessor whose batch-statistics coupling is exactly what LayerNorm removed; the contrast defines this note.
- [[Decision - Choosing a Normalization Layer]] — the practical chooser across BN/LN/RMSNorm/GroupNorm/no-norm.
- [[Concept - Vanishing and Exploding Gradients]] — the pathology normalization exists to suppress; norms are one layer of that fix stack.
- [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] — *where* the norm sits changes trainability as much as which norm; the placement half of the story.
- [[Deep Dive - The Transformer]] — the host architecture: two norms per block, and the reason LayerNorm displaced BatchNorm entirely in sequence models.
- [[Concept - Normalization-Free Networks]] — the frontier counterfactual: what you must re-engineer (init, clipping) if you delete the norm.
- [[Concept - Mixed Precision Training]] — the training regime that forces the fp32-statistics rule.
- [[Concept - Floating Point for Deep Learning]] — why bf16 and fp16 corrupt the variance computation through different mechanisms.
- [[Concept - Kernel Fusion]] — norms are bandwidth-bound reduction ops; fusion is where RMSNorm's structural simplicity pays end-to-end.

## Sources

- Ba, Kiros & Hinton (2016) — Layer Normalization. The per-token normalization mechanism and RNN motivation.
- Zhang & Sennrich (2019) — Root Mean Square Layer Normalization. Drops re-centering; the 7–64% op-level speedup measurement.
- Xu et al. (2019) — Understanding and Improving Layer Normalization. Evidence that the backward's gradient re-centering/re-scaling, not the forward normalization alone, carries much of LN's benefit.
- Touvron et al. (2023) — LLaMA. The config (RMSNorm, $\epsilon{=}10^{-6}$, pre-norm) that became the open-model default.
