---
tags: [gotchas, domain/architectures, level/advanced]
aliases: []
summary: "The masking, scaling, dtype, reshape, RoPE, and GQA bugs that let a hand-implemented attention layer train while being subtly wrong."
---

# Gotchas - Implementing Attention

The bugs that let a hand-implemented [[Concept - Attention Mechanism|attention]] layer *run*, produce a plausible-looking loss curve, and still be wrong. None of these throw an exception; all of them cost days of misdirected debugging elsewhere in the stack. Ordered by how much pain they cause, worst first.

## 1. Causal mask leakage — loss looks great, eval is garbage

**Symptom:** training loss drops faster and lower than the model size and data should allow — implausibly good, often within the first few hundred steps at a scale where that shouldn't happen — while downstream generation or held-out eval is clearly broken.

**Cause:** the causal mask is built with the wrong triangle or an off-by-one on the diagonal — e.g. masking $j \geq i$ instead of $j > i$ (hiding a token from itself) is merely wasteful, but the dangerous direction is leaving $j > i$ unmasked, letting position $i$ see future tokens. Since training targets are the input sequence shifted by one, an unmasked future position lets the model read its own answer directly off the input — textbook label leakage, and the loss curve looks fantastic while doing it.

**Fix:** set $S_{ij} = -\infty$ for $j > i$ before the softmax, keeping the diagonal ($j=i$) visible; verify against a tiny hand-checked example before trusting it on real data.

**Detection:** a causality self-test — perturb a future token in the input and confirm the output at every earlier position is bit-for-bit (or numerically) unchanged. A loss-at-init or early-training curve that looks too good for the model/data scale is the first clue; run the self-test before spending compute on a real run.

## 2. RoPE ported to the wrong dims, split, or base

**Symptom:** short-context behavior looks fine; quality degrades sharply at longer context, or a checkpoint ported between frameworks (e.g. a custom implementation loading Hugging Face weights) silently underperforms with no error.

**Cause:** [[Concept - Rotary Position Embeddings (RoPE)|RoPE]] has two incompatible conventions for pairing dimensions (interleaved vs. half-split "rotate_half"), and mixing them between a reference checkpoint and your implementation silently garbles the rotation. Related variants of the same bug: applying the rotation before the head split instead of after, on the wrong axis, or with a `base`/`theta` that doesn't match the checkpoint it was trained with.

**Fix:** match the exact convention your weights were trained under — half-split `rotate_half` is the modern default (LLaMA, Hugging Face); apply the rotation only to Q and K, only after the head reshape, on the $d_{head}$ axis, never to V.

**Detection:** the empirical relative-position check — the dot product of rotated $q_m$ and $k_n$ should depend only on $(m-n)$, not on $m$ and $n$ individually — and diff logits token-for-token against a reference implementation using the [[Playbook - Numerically Matching a Reference Implementation|numerical-matching playbook]] rather than trusting an aggregate loss number.

## 3. GQA/MQA `repeat` vs `repeat_interleave` mis-grouping

**Symptom:** the model trains and metrics look "close enough" to a reference but are consistently a bit worse; a checkpoint loaded from a different framework underperforms its published numbers with no crash.

**Cause:** expanding $n_{kv}$ KV heads up to $n_{heads}$ query heads requires tiling each KV head across a contiguous block of query heads. Using `repeat()` (which tiles the whole tensor) where the reference uses `repeat_interleave()` (which tiles each element) — or vice versa — changes which query heads end up sharing which KV head, silently mis-grouping keys and values without any shape error, since both produce a tensor of the correct size.

**Fix:** write out the exact query-head-to-KV-head mapping the reference implementation uses before writing the expansion code, and match it precisely (`repeat_interleave` along the head dimension is the common convention, per [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)|GQA/MQA]]).

**Detection:** a unit test with distinguishable, per-head-identifiable KV values (e.g. each KV head filled with its own index) confirms every query head attends to the KV head the mapping intends.

## 4. Head reshape/transpose scrambles heads while shapes still check out

**Symptom:** no crash, no shape mismatch, loss trains but plateaus at noticeably worse quality than an equivalent reference implementation.

**Cause:** splitting `[B, T, d_model]` into per-head form requires reshaping to `[B, T, H, d_head]` *then* transposing to `[B, H, T, d_head]`. Going straight from `[B, T, d_model]` to a `.view(B, H, T, d_head)` reinterprets the underlying memory layout incorrectly, since `d_model` is contiguous as `H` chunks of `d_head` in row-major order but the target shape puts `H` before `T` — this mixes features from different positions into the same "head," a bug that produces plausible-looking but wrong output.

**Fix:** always reshape to `[B, T, H, d_head]` first, then `.transpose(1, 2)` (or `.permute`) to get `[B, H, T, d_head]`; never `.view()` directly across a dimension reordering.

**Detection:** a per-head identity unit test — zero out all heads' weights except one, set that one to identity, and confirm the output only reflects that head's designated slice of the input.

## 5. Padding interacts badly with the causal mask and RoPE position indices

**Symptom:** batched generation quality is noticeably worse than single-sequence generation of the identical prompt; outputs change depending on what else is in the batch.

**Cause:** two bugs share a root cause. During training, if the padding mask isn't combined (ANDed) with the causal mask, tokens can attend to pad positions and pad-position gradients can leak into real tokens. At inference, left-padding (the common choice for batched generation, so all sequences end at the same index) shifts every real token's position within the tensor — if position indices are computed as a raw `arange` instead of derived from the attention mask, RoPE rotates every token by the wrong angle, corrupting position information for exactly the padded sequences in the batch.

**Fix:** always combine the padding mask with the causal mask via a logical AND before applying $-\infty$; compute `position_ids` as a cumulative sum over the attention mask (so pad tokens consume no position slots) rather than a plain `arange`.

**Detection:** run the same real sequence once alone and once inside a padded batch (with different padding amounts) and confirm the outputs for that sequence match; any divergence means masking or position indices are wrong.

## 6. Missing or wrong attention scale collapses entropy

**Symptom:** loss plateaus at a stubbornly high value; per-head attention weights look nearly one-hot (or, less commonly, perfectly uniform) from very early in training.

**Cause:** omitting the $1/\sqrt{d_{head}}$ scale, or — a common copy-paste bug when multi-head splitting is bolted onto a single-head prototype — scaling by $d_{model}$ instead of $d_{head}$. Since $\text{Var}(S_{ij}) \propto d_k$, an unscaled or under-scaled score matrix has inflated variance, which pushes softmax into a saturated, near-one-hot regime and starves gradient flow through all but a handful of positions.

**Fix:** scale scores by $1/\sqrt{d_{head}}$, computed per-head, after the $QK^T$ product and before the softmax — not by $d_{model}$, and not once globally if heads have different widths.

**Detection:** log per-head attention entropy during the first few hundred steps; a scale bug shows up as entropy collapsing toward zero almost immediately, rather than the gradual sharpening a healthy run shows over many steps.

## 7. Softmax computed in bf16/fp16 loses probability mass

**Symptom:** intermittent NaNs in the loss, or — more insidiously — no crash at all but a small, persistent quality gap against a reference implementation that never shows up in the aggregate loss number.

**Cause:** computing softmax directly in low precision lets the exponentials of large (unmasked, unscaled-relative) scores overflow bf16/fp16's reduced dynamic range, and the running sum-of-exponentials in the denominator loses precision during accumulation — silently dropping probability mass rather than crashing outright. This is exactly the numerical structure [[Deep Dive - FlashAttention|FlashAttention]]'s kernel manages explicitly with fp32 accumulators while never materializing the full score matrix.

**Fix:** upcast scores to fp32 immediately before the max-subtraction and softmax, and cast the resulting weights back to bf16/fp16 only for the subsequent $AV$ matmul — see [[Concept - Floating Point for Deep Learning]] for why low-precision reductions are the recurring culprit.

**Detection:** run the identical forward pass once fully in fp32 and once in your target mixed precision, and diff the attention weight tensors directly rather than only the final loss — precision bugs here are frequently invisible in aggregate loss but visible immediately in per-position weight diffs.

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
