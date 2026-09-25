---
tags: [concept, domain/architectures, level/unicorn]
aliases: [QK-Norm, QK Normalization, Query-Key Normalization, Logit Soft-Capping, Attention Soft-Capping, QKNorm]
summary: "Small architectural clamps — QK-norm, logit soft-capping, z-loss — that bound attention logits and keep training stable at scale."
---

# Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)

> **One-paragraph hook:** Deep transformers can diverge silently. Attention logits grow without bound during training until the softmax saturates, entropy collapses to near zero, gradients vanish through the winning key, and you get a loss spike or NaN, sometimes 20B parameters and three weeks into a run. The fixes are cheap, unglamorous, and almost never explained outside a model card: normalize queries and keys before the dot product (QK-norm), squash the pre-softmax scores through a `tanh` clamp (logit soft-capping), or regularize the softmax normalizer (z-loss). Getting them wrong, or worse, silently dropping them at serving time, keeps producing "the ported model is subtly dumber" bugs.

## The mechanism

Scaled dot-product attention (see the [[Concept - Attention Mechanism]]) computes a score $s_{ij} = \frac{q_i \cdot k_j}{\sqrt{d_h}}$ for each query–key pair. The $1/\sqrt{d_h}$ factor exists because $q\cdot k$ has variance $\propto d_h$ at initialization; it normalizes score variance to $\approx 1$ so softmax starts in a high-entropy regime. That argument only holds *at init*. During training nothing pins the query/key projection weight norms, and they drift upward. Zhai et al. (2023, "Stabilizing Transformer Training by Preventing Attention Entropy Collapse") tie this to growth in the **spectral norm** of the QK weights, which inflates effective logit magnitude well past what the fixed $1/\sqrt{d_h}$ compensates for.

It's a positive feedback loop. Larger logits $\Rightarrow$ a sharper (lower-entropy) softmax $\Rightarrow$ nearly all mass on one key $\Rightarrow$ a large gradient concentrated on that key's logit $\Rightarrow$ even larger logits. That's [[Concept - Attention Entropy Collapse]]: attention entropy falls toward zero, and the collapse *precedes* the visible loss spike by many steps. Three families of clamp break the loop.

**QK-norm.** Normalize $q$ and $k$ per head, over the $d_h$ dimension, before the dot product. Two variants:

- *L2 / cosine form* (Henry et al. 2020, "Query-Key Normalization for Transformers"): $s_{ij} = g\,\dfrac{q_i \cdot k_j}{\lVert q_i\rVert\,\lVert k_j\rVert}$. The dot product becomes a cosine similarity, hard-bounded in $[-1,1]$, times one learned scalar $g$ per head. Logits live in $[-g, g]$, **fully decoupled** from the projection weight norms, and the learned $g$ replaces the fixed $1/\sqrt{d_h}$.
- *RMSNorm/LayerNorm form* (ViT-22B, Dehghani et al. 2023; OLMo 2; Gemma 3): apply [[Concept - RMSNorm and LayerNorm]] with a learnable gain to $q$ and $k$ before the score. This pins each query/key RMS to $\approx 1$ and removes the weight-norm dependence, without a hard bound.

**Logit soft-capping.** Squash the pre-softmax scores through a scaled `tanh`:
$$\tilde s_{ij} = c \cdot \tanh\!\left(\frac{s_{ij}}{c}\right)$$
For $|s|\ll c$ it's near-identity ($\tanh x \approx x$). For large $|s|$ it saturates smoothly toward $\pm c$. A hard `clamp` kills the gradient at the boundary; `tanh` keeps it nonzero, so the model can still nudge saturated logits. Gemma 2 (Gemma Team, 2024) used it in two places: **attention logits with cap $c=50$** and the **final vocab logits with cap $c=30$**.

**z-loss.** A training-only regularizer on the *output* softmax normalizer $Z=\sum_v e^{z_v}$: $\mathcal{L}_z = \lambda_z (\log Z)^2$. PaLM (Chowdhery et al. 2022) used $\lambda_z = 10^{-4}$. Pushing $\log Z \to 0$ keeps vocab logits from drifting to large absolute values. Keep the split straight: QK-norm and attention soft-capping stabilize the **attention softmax** (over keys), while z-loss and final-logit soft-capping stabilize the **output softmax** (over vocab). [[Concept - z-loss and Logit Soft-Capping]] covers the training dynamics.

## In practice

- **ViT-22B** forced the issue. Without QK LayerNorm the 22B run diverged with attention collapsing to one-hot, and adding it was required to reach that scale.
- **Chameleon** (Meta 2024) hit "logit drift" because mixing image and text tokens under one softmax pushed logits apart. QK-norm was their fix.
- **Gemma 2** chose soft-capping (caps 50/30) plus sandwich RMSNorm; see [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]]. **Gemma 3** then *dropped soft-capping and switched to QK-norm*. Two solutions to one problem, and the field is converging on QK-norm because it's kernel-friendly (below).
- **OLMo 2** pairs QK-norm with reordered norms. QK-norm is now common in 2024–2025 open frontier models.
- QK-norm is **per head**, so it interacts with head-sharing schemes ([[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]]). With GQA the norm gains are typically shared across the query heads in a KV group.

## Failure modes

- **The FlashAttention silent drop (the big one).** Soft-capping has to hit the raw scores *inside* the fused kernel, before the online softmax. Stock [[Deep Dive - FlashAttention]]-2 had no hook for an elementwise op on the scores, so at Gemma 2's release, enabling FA2 **silently skipped the cap**. No error, just a few points of quality gone. HuggingFace fell back to eager attention and warned. Many people ran FA2 anyway and mis-served the model. FA 2.6+ later added a `softcap` argument and vLLM followed, but this porting footgun is why "Gemma 2 is worse than the benchmarks say" circulated. **Detection:** diff eager-attention vs FA2 logits on a fixed prompt. A perplexity mismatch means the cap was dropped.
- **QK-norm ordering vs RoPE.** RoPE is norm-preserving, but the *learnable gain* makes RMSNorm-before-RoPE and RMSNorm-after-RoPE non-equivalent element-wise. Get the order wrong when porting and long context gets garbled. **Detection:** activation-diff the first divergent layer against the reference.
- **Divergence during training.** **Detection:** log per-layer max $|s_{ij}|$ and attention softmax entropy. A monotonic logit climb or entropy sliding toward zero is the early warning, visible in [[Deep Dive - Anatomy of a Pretraining Run]] telemetry long before the loss line moves.
- **Over-capping.** Set the cap too low and attention gets over-smoothed, blunting sharp exact-match/induction lookups. The 50/30 values aren't derived.

## The non-obvious

- **The architectural clamp is more dangerous to port than the training clamp.** z-loss only changes the backward pass and disappears harmlessly at inference. Soft-capping and QK-norm change the *forward* pass and have to be replicated bit-for-bit at serving time. Forget the loss term and it costs nothing; forget the clamp and every generation silently degrades. Hence the damage from the FlashAttention drop.
- **QK-norm and soft-capping are partially redundant.** Gemma 3 removed soft-capping *because* QK-norm already bounds attention logits and soft-capping's kernel incompatibility wasn't worth the cost. The ecosystem picked the hardware-friendly stabilizer over the mathematically tidy one.
- **Low precision raises the stakes.** bf16 won't overflow on a large logit, but fp8 e4m3 tops out around $\pm 448$, and an uncapped $q\cdot k$ can blow past that ([[Concept - Mixed Precision Training]]). For fp8 attention, bounded logits are a *prerequisite*, beyond being a stability nicety.
- **Folklore, weakly sourced:** the exact caps (50 for attention, 30 for vocab) have no published derivation. They're what worked in the Gemma 2 ablations, copied forward without a principled story. Treat them as tuned constants, not laws.
- Zhai et al.'s own fix wasn't a clamp. It was **σReparam**, reparameterizing each weight as $W = (\gamma/\sigma(W))\,W$ to hold the spectral norm down at the root cause. QK-norm and soft-capping won on simplicity, not because they address the mechanism more directly.

## Connections

- [[Concept - Attention Mechanism]] — the scaled dot product whose $1/\sqrt{d_h}$ scale these tricks repair once weight norms drift past init.
- [[Concept - Attention Entropy Collapse]] — the exact pathology (Zhai et al. 2023) that unbounded logits trigger; this note is the fix, that note is the disease.
- [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] — QK-norm and final-logit norm are auxiliary stabilizers layered on top of the pre/post/sandwich-norm choice.
- [[Concept - RMSNorm and LayerNorm]] — the norm layer QK-norm reuses, now applied to Q and K instead of the residual stream.
- [[Concept - z-loss and Logit Soft-Capping]] — the training-side sibling that regularizes the output softmax normalizer rather than clamping the forward pass.
- [[Deep Dive - FlashAttention]] — the fused kernel whose lack of a score hook silently dropped Gemma 2's soft-cap, the field's canonical porting bug here.
- [[Concept - Mixed Precision Training]] — fp8 attention needs bounded logits to stay inside e4m3 range, making these clamps a precision prerequisite.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where you watch per-layer logit magnitude and attention entropy to catch collapse before the loss spike.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — QK-norm is per-head, so its gains must be shared correctly across query heads in a GQA/MQA group.

## Sources

- Zhai et al. (2023) — *Stabilizing Transformer Training by Preventing Attention Entropy Collapse*. Links logit growth to spectral-norm growth and entropy collapse; proposes σReparam.
- Dehghani et al. (2023) — *Scaling Vision Transformers to 22 Billion Parameters*. QK LayerNorm as the fix that made 22B training converge.
- Henry et al. (2020) — *Query-Key Normalization for Transformers*. The cosine/L2 QKNorm form bounding logits to a learned $[-g,g]$.
- Gemma Team (2024) — *Gemma 2 technical report*. Attention soft-cap 50, final soft-cap 30, sandwich RMSNorm.
- Gemma Team (2025) — *Gemma 3 technical report*. Drops soft-capping, adopts QK-norm.
- Chowdhery et al. (2022) — *PaLM*. z-loss with $\lambda_z = 10^{-4}$ on the output softmax normalizer.
- OLMo 2 (Allen AI, 2024) and Chameleon (Meta, 2024) — QK-norm in production LLM/multimodal training against logit drift.
