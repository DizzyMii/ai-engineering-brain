---
tags: [concept, domain/multimodal, level/core]
aliases: [ViT]
summary: "Treating an image as a sequence of patch tokens and running it through a standard transformer instead of a CNN."
---

# Concept - Vision Transformers

> **One-paragraph hook:** A Vision Transformer (ViT) does nothing vision-specific. It turns an image into a sequence of tokens and hands them to the same transformer block used for text (see [[Deep Dive - The Transformer]]). That one decision is why ViT features became the default substrate for CLIP, VLMs and image generators: attention, position handling and scaling behavior all come straight from language-model infrastructure, with no separate vision stack.

## The mechanism

**Patchify.** Split the image into non-overlapping $P \times P$ patches. $P=16$ is typical, so a 224×224 image gives $(224/16)^2 = 14 \times 14 = 196$ patches. Each patch is flattened into a $3P^2 = 768$-dimensional raw pixel vector and linearly projected to the model width $d$. Mechanically that's a strided convolution with kernel size and stride both equal to $P$: one [[Concept - Matrix Multiplication as the Atom of Deep Learning]] applied per patch, with none of the learned hierarchy of receptive fields a CNN builds.

**Sequence assembly.** The original ViT (Dosovitskiy et al. 2021) prepends a learnable `[CLS]` token to the 196 patch tokens and classifies from its final-layer state. Since `[CLS]` attends to every patch, its attention weights double as a rough saliency map via attention rollout. Many later models (including most VLM vision towers) drop `[CLS]` and mean-pool the patch tokens, which tends to give cleaner dense features for segmentation and detection.

**Position.** ViT uses learned 1D position embeddings, one per patch slot, where most modern text transformers use [[Concept - Rotary Position Embeddings (RoPE)|Rotary Position Embeddings]]. That has a real consequence. Running at a resolution the model wasn't trained at means bicubically interpolating the learned position grid (e.g., stretching a 14×14 grid to 24×24 for a higher-res input), and the interpolation is an easy-to-miss source of degradation, since the model never trained on those position vectors. Later systems that need native resolution flexibility get around it with 2D-RoPE or factorized position schemes (see [[Concept - Any-Resolution Vision Encoding]]).

**Config numerology.** ViT-B/16 = 12 layers, $d=768$, 12 heads (head-dim 64), 86M params. ViT-L/14 = 304M params. Halving the patch size quadruples the token count (4×), and because self-attention is $O(n^2)$ in sequence length, attention FLOPs go up roughly 16×. That quadratic wall makes ViT throughput sensitive to patch size in a way CNNs never were.

**Data hunger.** ViT has far less inductive bias than a CNN: no built-in translation equivariance or locality prior. [[Concept - Convolutional Neural Networks]] encode locality directly in the architecture, so ViT needs more data to learn what convolution gets for free. ViT-B underperforms similar-sized ResNets below roughly 100M training images, and JFT-300M was the dataset that gave ViT its edge in the original paper. Touvron et al. (2021, DeiT) later got strong ImageNet-only training (no JFT) through distillation from a CNN teacher plus heavy data augmentation, which showed the data-hunger problem was about training signal and not an architectural ceiling.

## In practice

ViT backbones rarely train from scratch for downstream use anymore. They're pretrained once at large scale and reused. [[Concept - CLIP and Contrastive Vision-Language Training]] pairs a ViT image encoder with a text encoder under a contrastive objective and produces the vision tower most VLMs bolt onto an LLM. Self-supervised variants skip labels. MAE (He et al. 2022) masks ~75% of patches and reconstructs pixels, which learns strong representations cheaply because only the visible patches go through the (expensive) encoder. DINO and DINOv2 (Caron et al. 2021, Oquab et al. 2023) use self-distillation between a student and a momentum teacher, and their dense features are good enough to be reused directly as the vision backbone in generation and grounding pipelines, well beyond classification.

## Failure modes

Quadratic attention cost in patch count is the first wall at high resolution. Doubling the image side quadruples the patch count and roughly 16×'s attention compute, so practical systems tile or downsample instead of running one ViT forward pass over a 4K image ([[Concept - Any-Resolution Vision Encoding]] covers the mitigations).

Position-embedding interpolation at off-training resolutions causes subtle artifacts. Features near tile boundaries or at unusual aspect ratios degrade in ways aggregate metrics hide, and they surface downstream as localized hallucination or OCR errors.

A nastier failure was found well after ViT became standard. Trained ViTs (supervised, CLIP and DINO alike) dump a handful of high-norm outlier activations into low-information background patches, which corrupts attention maps and any dense feature extraction built on them. [[Concept - Register Tokens and ViT Attention Artifacts]] covers the mechanism and the fix.

## The non-obvious

The `[CLS]`-token-as-saliency-map trick that made early ViT interpretability demos so convincing stopped being reliable once register tokens came along. Those high-norm outlier patches had been corrupting what looked like clean attention-rollout visualizations for years before anyone worked out why. If you build interpretability tooling or grounding pipelines on raw ViT attention maps, assume part of the mass is scratchpad noise, and validate against a register-token variant if your backbone has one.

## Connections
- [[Deep Dive - The Transformer]] — ViT reuses the exact block (MHA, FFN, residual stream) developed for text; nothing vision-specific in the layer itself.
- [[Concept - Attention Mechanism]] — the $O(n^2)$ operation whose cost in patch count drives every resolution/tiling tradeoff in vision transformers.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — patchify-and-project is literally a strided-conv matmul, the same primitive underlying every layer above it.
- [[Concept - Convolutional Neural Networks]] — the inductive-bias baseline ViT lacks, which is exactly why it needs more data or distillation to match CNN performance at moderate scale.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the position scheme ViT does *not* use by default, and the fix modern any-resolution encoders adopt instead of interpolating learned grids.
- [[Concept - CLIP and Contrastive Vision-Language Training]] — the dominant large-scale pretraining recipe that turns a ViT into a reusable, language-aligned vision tower.
- [[Concept - Any-Resolution Vision Encoding]] — the follow-on techniques (tiling, dynamic resolution, NaViT packing) built specifically to route around ViT's fixed-resolution position embeddings.
- [[Concept - Register Tokens and ViT Attention Artifacts]] — the outlier-token pathology discovered in trained ViTs and its scratchpad-token fix.

## Sources
- Dosovitskiy et al. (2021) — An Image is Worth 16x16 Words: the original ViT paper; patchify, `[CLS]` token, JFT-300M data requirement.
- Touvron et al. (2021) — Training data-efficient image transformers & distillation through attention (DeiT): recovering ViT performance on ImageNet-only data via CNN-teacher distillation.
- He et al. (2022) — Masked Autoencoders Are Scalable Vision Learners (MAE): self-supervised masked-patch reconstruction pretraining.
- Caron et al. (2021) — Emerging Properties in Self-Supervised Vision Transformers (DINO); Oquab et al. (2023) — DINOv2: self-distillation producing reusable dense ViT features.
