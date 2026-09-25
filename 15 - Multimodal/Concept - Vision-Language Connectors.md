---
tags: [concept, domain/multimodal, level/advanced]
aliases: [VLM projector, multimodal projector, Q-Former, Perceiver resampler, pixel shuffle]
summary: "The module that turns vision-encoder features into LLM tokens — MLP vs resampler vs pixel-shuffle — and the token-count/detail tradeoff it controls."
---

# Concept - Vision-Language Connectors

> **One-paragraph hook:** In a projector-style VLM (see [[Concept - VLM Architectures]]), the connector is the small module between the vision encoder and the LLM that turns patch features into "image tokens" the language model can attend to. It's often just an MLP, but the job is hard: it bridges the [[Concept - The Modality Gap in Contrastive Models|modality gap]] *and* the encoder-vs-LLM distribution mismatch, and it sets the system's most important cost knob, the image-token count. Pick the connector and you've picked your OCR ceiling, your latency and how much context an image eats.

## The mechanism

A [[Concept - Vision Transformers|ViT]] encoder emits $N$ patch features of dimension $d_{vis}$ (e.g., $N=576$ patches at 336px, $d_{vis}=1024$ for CLIP ViT-L/14). The LLM wants tokens of dimension $d_{llm}$ (e.g., 4096). The connector maps $\mathbb{R}^{N \times d_{vis}} \rightarrow \mathbb{R}^{M \times d_{llm}}$ and chooses both the projection *and* the output token count $M$. The three archetypes differ in whether $M = N$, $M \ll N$, or $M$ is a merged fraction of $N$.

**1. Linear / MLP projector ($M = N$, one token per patch).** The simplest option: project each patch feature on its own.

$$t_i = W_2 \,\sigma(W_1 h_i + b_1) + b_2, \quad i = 1 \dots N$$

[[Breakdown - LLaVA|LLaVA]]-1.5 went from a single linear layer to a **2-layer MLP** and got a measurable benchmark bump for essentially nothing. The extra nonlinearity helps the connector learn the cross-cone bridge instead of an affine resize. All $N$ tokens survive, so detail is maximal and so is the token cost (576 tokens per 336px image straight into the LLM's context and [[Concept - KV Cache|KV cache]]).

**2. Query-based resamplers ($M \ll N$, learned compression).** BLIP-2's **Q-Former** uses ~**32 learned query tokens** that cross-[[Concept - Attention Mechanism|attend]] to the $N$ vision features and compress them to a fixed 32 output tokens whatever the image size. [[Breakdown - Flamingo|Flamingo]]'s / Idefics' **Perceiver Resampler** is the same idea (Flamingo compresses to 64 latents). The appeal is a *fixed, small* token budget independent of resolution. The catch: they're notoriously hard to train and they bottleneck information. With only 32-64 tokens they discard fine spatial detail, which is what OCR and small-object grounding need.

**3. Token-reduction mergers (spatial downsampling, $M = N / k^2$).** The modern middle ground. **Pixel-shuffle/unshuffle** (InternVL) folds a $2\times2$ neighborhood of patches into a *single* token and moves the spatial information into the channel dimension:

$$\mathbb{R}^{2 \times 2 \times d} \rightarrow \mathbb{R}^{1 \times 4d} \xrightarrow{\text{MLP}} \mathbb{R}^{1 \times d_{llm}}$$

You get $4\times$ fewer tokens (576 → 144), and the information comes along as extra channels instead of being thrown away. **Qwen2-VL** uses an MLP merger over $2\times2$ blocks in the same spirit. It's the main practical lever on the token budget, and empirically it *loses less detail than a resampler at the same token count*, because it merges local neighborhoods deterministically where a resampler learns a lossy global compression.

## In practice

The connector sets a direct **token-count ↔ quality tradeoff**:

| Connector | Tokens (336px) | Detail preserved | Training difficulty | Used by |
|---|---|---|---|---|
| Linear / MLP | 576 (1:1) | Highest | Easy | LLaVA-1.5 |
| Pixel-shuffle merge (2×2) | 144 (1:4) | High | Easy | InternVL, Qwen2-VL |
| Q-Former / Perceiver | 32-64 (fixed) | Lower (bottleneck) | Hard | BLIP-2, Flamingo, Idefics |

Fewer tokens give a cheaper LLM forward pass, less [[Concept - KV Cache|KV-cache]] pressure and more room for text, with worse OCR and fine-detail perception. More tokens flip it. [[Concept - Any-Resolution Vision Encoding|Any-resolution]] tiling multiplies the base token count per tile, so the connector's compression ratio is what stops a multi-tile high-res image from ballooning to tens of thousands of tokens.

Two implementation choices people underrate:

- **Which feature layer.** LLaVA reads the ViT's **penultimate** layer, not the last. The final layer of a contrastively trained encoder is over-specialized to the [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]] / [[Concept - SigLIP and the Sigmoid Contrastive Loss|SigLIP]] objective (it's optimized to produce a pooled matching vector, not rich per-patch features), so the penultimate layer gives the LLM better spatial detail.
- **The connector is a learned bridge, not a resize.** It has to cross the modality gap and fix the mismatch between the encoder's output statistics and what the LLM's embedding space expects. That's why a naive linear resize underperforms, and why the connector, small as it is, trains first and alone in stage-1 alignment.

## Failure modes

- **Undertrained projector → weak grounding.** Symptom: the VLM refers to the image only vaguely, or answers from language priors ("blind" behavior). Detection: freeze everything else and check whether more stage-1 alignment steps improve image-conditioned answers. Fix: more alignment data / longer stage 1.
- **Over-aggressive compression → OCR collapse.** Symptom: the model reads large text but fails on small/dense text and tables. Cause: too few tokens (Q-Former-scale) or too high a pixel-shuffle factor. Detection: OCR-heavy eval (DocVQA, small-font tests). Fix: raise resolution and/or lower the merge factor.
- **Feature-layer mistake.** Symptom: grounding weaker than expected from a good encoder. Cause: reading the final (objective-specialized) layer. Fix: use the penultimate layer.
- **Placeholder-count mismatch.** Symptom: quality silently collapses after a config change. Cause: the number of `<image>` placeholder tokens in the chat template no longer matches the connector's output token count $M$. Detection: assert `len(placeholders) == M` in the collator.

## The non-obvious

**The connector's compression ratio is the highest-leverage architecture decision in a projector VLM, and it's easy to set once and forget.** Teams pick 576 tokens because LLaVA did, or 32 because a resampler is elegant, then spend months tuning SFT data to fix an OCR ceiling the connector's token count imposed. The relationship is close to mechanical. Dense-document and small-text tasks want *many* tokens (linear or light pixel-shuffle at high resolution); latency-bound chat and multi-image/video want *few* (heavier merging). A resampler's *fixed* token count sounds like a clean abstraction but actively hurts OCR, because it caps information no matter how much text the image holds. When someone reports "our VLM can't read receipts", the fix is almost never more instruction data. It's the connector and the resolution feeding it.

## Connections

- [[Concept - VLM Architectures]] — the projector family this connector defines; the parent taxonomy (down-link to the core overview).
- [[Concept - Vision Transformers]] — the encoder whose patch features (and penultimate-layer choice) the connector consumes.
- [[Concept - The Modality Gap in Contrastive Models]] — *why* the connector must be a learned bridge, not a resize (up-link to the unicorn detail).
- [[Concept - Any-Resolution Vision Encoding]] — tiling multiplies base tokens; the connector's compression is what keeps the budget survivable.
- [[Breakdown - LLaVA]] — the linear→MLP switch and penultimate-layer finding originate here.
- [[Breakdown - Flamingo]] — the Perceiver Resampler, the cross-attention-side cousin of the Q-Former.
- [[Concept - Attention Mechanism]] — query-based resamplers are cross-attention from learned queries to vision features.
- [[Concept - KV Cache]] — output token count directly sets image KV-cache footprint and serving cost.
- [[Concept - SigLIP and the Sigmoid Contrastive Loss]] — the modern encoder whose features the connector typically maps; last-vs-penultimate layer logic applies.

## Sources

- Liu et al. (2023) — *Visual Instruction Tuning* (LLaVA) and *Improved Baselines with Visual Instruction Tuning* (LLaVA-1.5). Linear→MLP projector upgrade and penultimate-layer feature choice.
- Li et al. (2023) — *BLIP-2*. The Q-Former: 32 learned queries cross-attending to compress vision features.
- Alayrac et al. (2022) — *Flamingo*. The Perceiver Resampler producing a fixed 64 visual tokens.
- Chen et al. (2024) — *InternVL* / *InternVL 1.5*. Pixel-shuffle token reduction (2×2 → 1) as the token-budget lever.
- Wang et al. (2024) — *Qwen2-VL*. MLP merger over 2×2 blocks with native dynamic resolution.
