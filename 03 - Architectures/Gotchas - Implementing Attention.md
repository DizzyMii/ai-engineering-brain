---
tags: [gotchas, domain/architectures, level/advanced]
aliases: []
summary: "The masking, scaling, dtype, reshape, RoPE, and GQA bugs that let a hand-implemented attention layer train while being subtly wrong."
---

# Gotchas - Implementing Attention

These are the bugs that let a hand-written [[Concept - Attention Mechanism|attention]] layer *run*, produce a plausible loss curve, and still be wrong. None of them throws an exception. Each one costs days of debugging in the wrong part of the stack. Worst first.

## 1. Causal mask leakage: loss looks great, eval is garbage

**Symptom:** training loss drops faster and lower than the model size and data should allow, often within the first few hundred steps at a scale where that shouldn't happen. Downstream generation or held-out eval is clearly broken.

**Cause:** the causal mask uses the wrong triangle or is off by one on the diagonal. Masking $j \geq i$ instead of $j > i$ hides a token from itself, which only wastes capacity. The dangerous direction is leaving $j > i$ unmasked, so position $i$ sees future tokens. Training targets are the input shifted by one, so an unmasked future position lets the model read its answer straight off the input. That's textbook label leakage, and the loss curve looks fantastic the whole time.

**Fix:** set $S_{ij} = -\infty$ for $j > i$ before the softmax and keep the diagonal ($j=i$) visible. Check it on a tiny hand-worked example before trusting it on real data.

**Detection:** a causality self-test. Perturb a future token in the input and confirm the output at every earlier position is bit-for-bit (or numerically) unchanged. The first clue is a loss-at-init or early-training curve too good for the model/data scale. Run the self-test before spending compute on a real run.

## 2. RoPE ported to the wrong dims, split, or base

**Symptom:** short-context behavior is fine, but quality degrades sharply at longer context. Or a checkpoint ported between frameworks (a custom implementation loading Hugging Face weights, say) underperforms with no error.

**Cause:** [[Concept - Rotary Position Embeddings (RoPE)|RoPE]] has two incompatible ways of pairing dimensions: interleaved and half-split "rotate_half". Mixing them between a reference checkpoint and your code garbles the rotation without complaint. Variants of the same bug: rotating before the head split instead of after, rotating on the wrong axis, or using a `base`/`theta` that doesn't match the one the checkpoint was trained with.

**Fix:** match the convention your weights were trained under. Half-split `rotate_half` is the modern default (LLaMA, Hugging Face). Rotate only Q and K, never V, and only after the head reshape, on the $d_{head}$ axis.

**Detection:** check relative position empirically: the dot product of rotated $q_m$ and $k_n$ should depend only on $(m-n)$, not on $m$ and $n$ separately. Then diff logits token by token against a reference using the [[Playbook - Numerically Matching a Reference Implementation|numerical-matching playbook]]. An aggregate loss number won't show this.

## 3. GQA/MQA `repeat` vs `repeat_interleave` mis-grouping

**Symptom:** the model trains and metrics are "close enough" to a reference but consistently a bit worse. A checkpoint loaded from another framework underperforms its published numbers without crashing.

**Cause:** expanding $n_{kv}$ KV heads to $n_{heads}$ query heads means tiling each KV head across a contiguous block of query heads. `repeat()` tiles the whole tensor; `repeat_interleave()` tiles each element. Using one where the reference uses the other changes which query heads share which KV head. Both produce a tensor of the correct size, so there's no shape error to catch it.

**Fix:** write out the reference's query-head-to-KV-head mapping before writing the expansion code, and match it. `repeat_interleave` along the head dimension is the common convention (see [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)|GQA/MQA]]).

**Detection:** a unit test with KV values you can tell apart per head (fill each KV head with its own index, for example) confirms every query head attends to the KV head the mapping intends.

## 4. Head reshape/transpose scrambles heads while shapes still check out

**Symptom:** no crash, no shape mismatch. Loss trains but plateaus noticeably worse than an equivalent reference implementation.

**Cause:** splitting `[B, T, d_model]` into heads means reshaping to `[B, T, H, d_head]` *then* transposing to `[B, H, T, d_head]`. Going straight to `.view(B, H, T, d_head)` misreads the memory layout. `d_model` is laid out as `H` contiguous chunks of `d_head` in row-major order, but the target shape puts `H` before `T`. Features from different positions end up in the same "head", and the output looks plausible but is wrong.

**Fix:** reshape to `[B, T, H, d_head]` first, then `.transpose(1, 2)` (or `.permute`) to get `[B, H, T, d_head]`. Never `.view()` across a dimension reordering.

**Detection:** a per-head identity test. Zero every head's weights except one, set that one to identity, and confirm the output only reflects that head's slice of the input.

## 5. Padding interacts badly with the causal mask and RoPE position indices

**Symptom:** batched generation is noticeably worse than generating the same prompt alone. Outputs change depending on what else is in the batch.

**Cause:** two bugs with one root. In training, if the padding mask isn't ANDed with the causal mask, tokens can attend to pad positions and pad-position gradients leak into real tokens. At inference, left-padding (the usual choice for batched generation, so every sequence ends at the same index) shifts each real token's position in the tensor. If position indices come from a raw `arange` instead of the attention mask, RoPE rotates every token by the wrong angle, and only the padded sequences in the batch get corrupted position information.

**Fix:** combine the padding mask with the causal mask via logical AND before applying $-\infty$. Compute `position_ids` as a cumulative sum over the attention mask, so pad tokens take no position slots, instead of a plain `arange`.

**Detection:** run one real sequence alone and again inside padded batches with different padding amounts. Its outputs should match. Any divergence means the masking or position indices are wrong.

## 6. Missing or wrong attention scale collapses entropy

**Symptom:** loss plateaus at a stubbornly high value. Per-head attention weights look nearly one-hot (or, less commonly, perfectly uniform) from very early in training.

**Cause:** the $1/\sqrt{d_{head}}$ scale is missing, or the code scales by $d_{model}$ instead of $d_{head}$. The second is a common copy-paste bug when multi-head splitting gets bolted onto a single-head prototype. Since $\text{Var}(S_{ij}) \propto d_k$, an unscaled or under-scaled score matrix has inflated variance. Softmax saturates into a near-one-hot regime and gradient flows through only a handful of positions.

**Fix:** scale scores by $1/\sqrt{d_{head}}$, per head, after the $QK^T$ product and before the softmax. Don't use $d_{model}$, and don't scale once globally if heads have different widths.

**Detection:** log per-head attention entropy over the first few hundred steps. With a scale bug, entropy collapses toward zero almost immediately. A healthy run sharpens gradually over many steps.

## 7. Softmax computed in bf16/fp16 loses probability mass

**Symptom:** intermittent NaNs in the loss. Or, worse, no crash at all, just a small persistent quality gap against a reference that never shows in the aggregate loss.

**Cause:** in low precision, the exponentials of large (unmasked, unscaled-relative) scores overflow the reduced dynamic range of bf16/fp16, and the running sum of exponentials in the denominator loses precision as it accumulates. Probability mass disappears without a crash. [[Deep Dive - FlashAttention|FlashAttention]]'s kernel handles this same numerical structure explicitly, with fp32 accumulators and without ever materializing the full score matrix.

**Fix:** upcast scores to fp32 right before the max-subtraction and softmax. Cast the weights back to bf16/fp16 only for the $AV$ matmul that follows. [[Concept - Floating Point for Deep Learning]] explains why low-precision reductions keep being the culprit.

**Detection:** run the same forward pass fully in fp32 and again in your target mixed precision, then diff the attention weight tensors directly. Precision bugs here are frequently invisible in aggregate loss and obvious in per-position weight diffs.

## Connections
- [[Concept - Attention Mechanism]] — the mechanism every gotcha above is a bug in; read this first if the scale/mask/softmax terms are unfamiliar.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — the GQA/MQA head-sharing mechanism whose expansion step gotcha #3 breaks.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the mechanism behind gotcha #2's convention and axis mismatches.
- [[Snippet - Scaled Dot-Product Attention from Scratch]] — a correct reference implementation that avoids every gotcha in this note by construction.
- [[Concept - Floating Point for Deep Learning]] — the precision mechanics behind gotcha #7's silent mass loss (cross-domain: foundations).
- [[Deep Dive - FlashAttention]] — the production kernel that manages gotcha #7's exact numerical structure at scale (cross-domain: hardware & systems).
- [[Playbook - Numerically Matching a Reference Implementation]] — the systematic procedure for catching gotchas #2–#4, which are all invisible from the loss curve alone.
- [[Concept - Attention Sinks]] — a real, *trained* phenomenon that looks superficially like several of these bugs (mass dumped on early tokens) but isn't one — useful to know before bug-hunting for it (cross-domain: frontier & esoterica).

## Sources
- Vaswani et al. (2017) — "Attention Is All You Need." The $1/\sqrt{d_k}$ scaling rationale behind gotcha #6.
- Su et al. (2021) — "RoFormer: Enhanced Transformer with Rotary Position Embedding." The RoPE mechanism whose convention mismatches drive gotcha #2.
- Dao et al. (2022) — "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness." The fp32-accumulation kernel design referenced in gotcha #7.
