---
tags: [concept, domain/neural-networks, level/advanced]
aliases: [LayerNorm, RMSNorm, LN, layer normalization, root mean square normalization]
summary: "Per-token feature normalization: LayerNorm's mean/variance rescale, why RMSNorm dropped re-centering and won, and the fp32 rule."
---

# Concept - RMSNorm and LayerNorm

> **One-paragraph hook:** Every transformer block you will ever debug contains a normalization layer that rescales each token's activation vector to a fixed magnitude before the expensive sublayers see it. LayerNorm was the incumbent; RMSNorm — LayerNorm minus the mean subtraction and the bias — is what LLaMA, T5, and essentially every modern LLM ships *(as of 2026)*. The interesting content is in the deltas: why per-token (not per-batch) normalization is what made transformers trainable, why dropping re-centering cost nothing, and why this one op must run in fp32 while everything around it runs bf16.

## The mechanism

**LayerNorm** (Ba et al. 2016) normalizes over the *feature* dimension, independently for every token. For $x \in \mathbb{R}^d$:

$$\mu = \frac{1}{d}\sum_i x_i \qquad \sigma^2 = \frac{1}{d}\sum_i (x_i-\mu)^2 \qquad y = \gamma \odot \frac{x-\mu}{\sqrt{\sigma^2+\epsilon}} + \beta$$

with learnable gain $\gamma$ and bias $\beta$ (both $\in \mathbb{R}^d$). Because every statistic is computed within a single token's vector, LayerNorm is batch-size independent — it works identically at batch 1, with variable-length sequences, in RNNs, and in autoregressive decoding, all the places where [[Breakdown - Batch Normalization]]'s cross-example statistics fail structurally.

**RMSNorm** (Zhang & Sennrich 2019) deletes the mean subtraction and $\beta$:

$$y = \frac{x}{\sqrt{\tfrac{1}{d}\sum_i x_i^2 + \epsilon}} \odot \gamma$$

One reduction instead of two, no bias parameters. The paper measured 7–64% wall-clock speedup on the norm op across models, at parity of final quality — which is the empirical verdict that the re-centering half of LayerNorm was never doing load-bearing work. Rescaling to unit RMS is the whole job.

**Why it stabilizes training.** The forward pass becomes scale-invariant to its input: $\text{RMSNorm}(\alpha x) = \text{RMSNorm}(x)$ for any $\alpha > 0$, so no matter how activation magnitudes drift across depth or training time, each sublayer receives inputs at a fixed scale. In the backward direction, the same property keeps per-layer gradient magnitudes commensurate, which is a major part of the fix stack for [[Concept - Vanishing and Exploding Gradients]]. Where the norms *sit* relative to the residual stream — pre-norm vs post-norm — changes trainability as much as which norm you use; that placement question is owned by [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]].

The backward pass is sneakier than "divide by sigma." Ignoring $\gamma$, LayerNorm's input gradient is

$$\frac{\partial L}{\partial x} = \frac{1}{\sigma}\Big(\,\bar y - \underbrace{\text{mean}(\bar y)}_{\text{re-centering}} - \hat x \odot \underbrace{\text{mean}(\bar y \odot \hat x)}_{\text{projection onto } \hat x}\Big)$$

where $\bar y$ is the upstream gradient and $\hat x$ the normalized activation. It subtracts both the gradient's mean and its component *along the activation direction* — the gradient is orthogonalized against $\hat x$. A norm layer doesn't just rescale gradients; it filters out exactly the component that would change the activation's magnitude, leaving only directional updates. RMSNorm keeps the projection term and drops the mean term.

## In practice

- **Configs:** $\epsilon = 10^{-5}$ (GPT-2 lineage, PyTorch default) or $10^{-6}$ (LLaMA, T5); $\gamma$ initialized to 1.0. These are load-bearing: an $\epsilon$ mismatch between training and a reimplementation produces small systematic logit drift that surfaces as a benchmark regression nobody can localize. Many modern stacks drop LayerNorm's $\beta$ (and all linear-layer biases) even when keeping the mean subtraction — bias terms turned out to be nearly free to remove.
- **Where it runs:** in [[Deep Dive - The Transformer]], two norms per block (before attention, before the FFN in pre-norm placement), plus one final norm before the LM head. For a 7B model that's ~65 norm calls per forward — individually cheap, collectively memory-bandwidth-bound, which is why every serious stack fuses the reduction, scale, and (in fused residual variants) the preceding add into one kernel via [[Concept - Kernel Fusion]]. RMSNorm's single-reduction structure fuses tighter — part of why "7–64% faster on the op" survives into end-to-end gains.
- **The fp32 rule:** under bf16/fp16 [[Concept - Mixed Precision Training]], the norm's internal statistics are computed in fp32 and cast back down. The sum of squares over $d = 4096$–16384 elements accumulates rounding error badly in half precision, and with bf16's 8-bit mantissa the variance of near-uniform activations can quantize to garbage; fp16 additionally risks overflow in $\sum x_i^2$ ($x_i \sim 100$ at $d{=}8192$ already exceeds 65504 in the sum) — see [[Concept - Floating Point for Deep Learning]] for why bf16 and fp16 fail differently here. Every production implementation (Megatron, LLaMA reference, PyTorch `F.rms_norm`) upcasts; hand-rolled ones that don't are a classic slow-divergence bug.

## Failure modes

- **Half-precision statistics.** Symptom: training that runs but diverges after thousands of steps, or a reimplementation that matches for short sequences and drifts on long ones. Cause: norm computed natively in bf16/fp16. Detection: diff per-layer activations against an fp32 reference forward; the norm layers show the first divergence.
- **Gain drift / decayed gains.** Applying weight decay to $\gamma$ pulls it toward 0, quietly shrinking the residual stream's effective scale; $\gamma$ belongs in the no-decay param group. Detection: monitor $\gamma$ norms — a layer whose mean gain drifts far from 1.0 is compensating for something upstream.
- **Wrong-axis normalization.** `LayerNorm(d)` over `(B, T, d)` normalizes the last dim — correct; porting code from CNN land where the channel dim sits elsewhere produces a model that trains, badly. Detection: unit-test that output mean/RMS per token is (0,1)/(1) at init.
- **$\epsilon$ inside vs outside the sqrt and eps-value mismatches** across frameworks — same class of silent reproducibility trap as optimizer epsilon.

## The non-obvious

The gradient-orthogonalization view explains a thing that surprises people: networks with norms are nearly immune to the *scale* of their weight initialization (the norm eats any constant), but remain sensitive to its *direction and rank structure* — normalization is a partial substitute for careful init, not a full one. It also means the effective learning rate on a weight matrix behind a norm grows as the weight norm grows ($\partial L/\partial W \propto 1/\lVert W \rVert$ through the scale-invariance), a feedback loop that weight decay quietly regulates. Remove the norm and you must reintroduce all of this by hand with precise init and clipping — which is exactly what [[Concept - Normalization-Free Networks]] do, and why they remain fragile at frontier scale. For choosing among BatchNorm/LayerNorm/RMSNorm/GroupNorm for a given architecture and batch regime, the decision framework lives in [[Decision - Choosing a Normalization Layer]].

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
