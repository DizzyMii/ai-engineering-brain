---
tags: [concept, domain/multimodal, level/core]
aliases: [ViT]
summary: "Treating an image as a sequence of patch tokens and running it through a standard transformer instead of a CNN."
---

# Concept - Vision Transformers

> **One-paragraph hook:** A Vision Transformer (ViT) does not do anything vision-specific — it turns an image into a sequence of tokens and hands it to the exact same transformer block used for text (see [[Deep Dive - The Transformer]]). That one design decision is why ViT features became the default substrate for CLIP, VLMs, and image generators: everything downstream — attention, position handling, scaling behavior — inherits directly from language-model infrastructure instead of needing a separate vision stack.

## The mechanism

**Patchify.** An image is split into non-overlapping $P \times P$ patches — $P=16$ is the typical choice, so a 224×224 image yields $(224/16)^2 = 14 \times 14 = 196$ patches. Each patch is flattened to a $3P^2 = 768$-dimensional raw pixel vector and linearly projected to the model width $d$. Mechanically this is identical to a strided convolution with kernel size and stride both equal to $P$ — a single [[Concept - Matrix Multiplication as the Atom of Deep Learning]] applied patch-wise, not a learned hierarchy of receptive fields the way a CNN builds one.

**Sequence assembly.** The original ViT (Dosovitskiy et al. 2021) prepends a learnable `[CLS]` token to the 196 patch tokens; its final-layer state is used for classification, and because `[CLS]` attends to every patch, its attention weights double as a rough saliency map via attention rollout. Many later models (including most VLM vision towers) drop `[CLS]` in favor of mean-pooling over patch tokens, which tends to produce cleaner dense features for segmentation and detection.

**Position.** ViT uses learned 1D position embeddings, one per patch slot — not [[Concept - Rotary Position Embeddings (RoPE)|Rotary Position Embeddings]] as in most modern text transformers. This has a real consequence: running the model at a resolution it wasn't trained at requires bicubically interpolating the learned position grid (e.g., a 14×14 grid stretched to 24×24 for a higher-res input), and this interpolation is a quiet, easy-to-miss source of degradation — the model was never trained on those exact position vectors. Later systems that need native resolution flexibility route around this with 2D-RoPE or factorized position schemes (see [[Concept - Any-Resolution Vision Encoding]]).

**Config numerology.** ViT-B/16 = 12 layers, $d=768$, 12 heads (head-dim 64), 86M params. ViT-L/14 = 304M params. Halving the patch size quadruples the token count (4×) and, because self-attention is $O(n^2)$ in sequence length, multiplies attention FLOPs by roughly 16×. This quadratic wall is why ViT throughput is patch-size-sensitive in a way CNNs never were.

**Data hunger.** ViT has far less inductive bias than a CNN — no built-in translation equivariance or locality prior — so it needs more data to learn what convolution gets for free, unlike [[Concept - Convolutional Neural Networks]], which encode locality directly into the architecture. ViT-B underperforms similarly-sized ResNets below roughly 100M training images; JFT-300M was the dataset that unlocked ViT's advantage in the original paper. Touvron et al. (2021, DeiT) later showed you could recover strong ImageNet-only training (no JFT needed) via distillation from a CNN teacher plus heavy data augmentation — proving the data-hunger problem was about training signal, not an architectural ceiling.

## In practice

ViT backbones rarely train from scratch anymore for downstream use — they're pretrained once at large scale and reused. [[Concept - CLIP and Contrastive Vision-Language Training]] pairs a ViT image encoder with a text encoder under a contrastive objective, producing the vision tower most VLMs bolt onto an LLM. Self-supervised variants sidestep labels entirely: MAE (He et al. 2022) masks ~75% of patches and reconstructs pixels, learning strong representations cheaply since only the visible patches run through the (expensive) encoder; DINO and DINOv2 (Caron et al. 2021, Oquab et al. 2023) use self-distillation between a student and a momentum-teacher to produce dense features so strong they're now reused directly as the vision backbone in generation and grounding pipelines, not just classification.

## Failure modes

The quadratic attention cost in patch count is the first wall you hit at high resolution — doubling image side length quadruples patch count and roughly 16×'s attention compute, which is why practical systems tile or downsample rather than run a single ViT forward pass over a 4K image (see [[Concept - Any-Resolution Vision Encoding]] for the mitigations). Position-embedding interpolation at off-training resolutions produces subtle artifacts: features near tile boundaries or at unusual aspect ratios degrade in ways that are easy to miss in aggregate metrics but show up as localized hallucination or OCR errors downstream. A more insidious failure, discovered well after ViT was standard: trained ViTs (supervised, CLIP, and DINO alike) dump a handful of high-norm outlier activations into low-information background patches, corrupting attention maps and any dense feature extraction built on top — the full mechanism and fix are covered in [[Concept - Register Tokens and ViT Attention Artifacts]].

## The non-obvious

The `[CLS]`-token-as-saliency-map trick that made early ViT interpretability demos so compelling stopped being reliable once register tokens entered the picture — those high-norm outlier patches were quietly corrupting what looked like clean attention rollout visualizations for years before anyone diagnosed why. If you're building interpretability tooling or grounding pipelines on raw ViT attention maps, assume some fraction of the mass is scratchpad noise, not signal, and validate against a register-token variant if one exists for your backbone.

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
