---
tags: [concept, domain/multimodal, level/advanced]
aliases: [SigLIP, sigmoid loss for language-image pretraining]
summary: "The per-pair sigmoid contrastive loss that decouples image-text pretraining from global batch size and became the default VLM vision tower."
---

# Concept - SigLIP and the Sigmoid Contrastive Loss

> **One-paragraph hook:** [[Concept - CLIP and Contrastive Vision-Language Training|CLIP's]] softmax InfoNCE loss ties representation quality to an enormous global batch, because every image needs to be normalized against every negative in the batch, which means an all-gather of embeddings across every data-parallel rank before you can even compute the loss. SigLIP (Zhai et al. 2023) throws out the row/column normalization entirely and treats every image-text pair as an independent binary classification problem — a small change to the loss function that removes the batch-size coupling and made SigLIP the default vision encoder in a wave of 2024–25 open VLMs (PaliGemma, Idefics2/3, and others).

## The mechanism

CLIP's loss requires, for every image, a softmax over *all* texts in the batch (and vice versa) — the normalization term $\sum_j e^{\tau s_{ij}}$ needs every negative simultaneously, which forces a global all-gather of embeddings across [[Concept - Data Parallelism and ZeRO|data-parallel]] ranks before any gradient can be computed. SigLIP replaces this with a loss that decomposes into one independent term per (image, text) pair — no [[Concept - Softmax|softmax]] normalization at all:

$$
\mathcal{L} = -\frac{1}{N}\sum_{i=1}^{N}\sum_{j=1}^{N} \log \sigma\big(z_{ij}(t \cdot s_{ij} + b)\big)
$$

where $s_{ij}$ is the cosine similarity between image $i$ and text $j$, $t$ and $b$ are a learned temperature and bias, and $z_{ij} = 1$ if $(i,j)$ is a true pair (the diagonal) and $-1$ otherwise. Every term is an independent sigmoid binary-cross-entropy classification — "is this specific pair a match, yes or no" — with no dependence on what any other pair in the batch looks like.

**Why this decouples from the global batch.** Because the loss is a sum of independent per-pair terms rather than a softmax over the whole batch, you don't need every negative present in one place to compute a valid gradient. In practice this means each device can compute its local block of the similarity matrix and swap negatives with peers via a comparatively small all-gather, rather than requiring the full batch's embeddings to be simultaneously resident and normalized together. The consequence: SigLIP trains well even at modest batch sizes (16K) and scales up without hitting the softmax memory blowup that makes CLIP-scale batches (32K+) expensive to shard.

**The learnable bias, and why it's initialized so negative.** In any batch of size $N$, there are $N$ positive pairs and $N^2 - N$ negative pairs — an extreme class imbalance that grows quadratically with batch size. Without correction, early training would be dominated by the trivial "predict negative" signal. SigLIP initializes the bias term $b$ strongly negative (around $-10$) so that at the start of training the sigmoid output is pinned close to zero for nearly everything, matching the true base rate of positives, and the loss only has to learn to push the diagonal up rather than fight an uncalibrated prior across millions of negatives.

## In practice

SigLIP matches or beats CLIP quality at far smaller batch size (16K vs. CLIP's 32K), and SigLIP-So400m — a "shape-optimized" 400M-parameter configuration — is the workhorse variant, typically run at 384–448px, noticeably higher native resolution than CLIP's common 336px. That resolution bump translates directly into better OCR and fine-detail perception once the encoder feeds a [[Concept - Vision-Language Connectors|connector]] into an LLM. SigLIP2 (2025) extends the recipe with added captioning and self-distillation objectives layered on top of the sigmoid contrastive loss, pushing feature quality further without reintroducing the global-batch dependency. As of 2025, SigLIP-So400m at 384–448px is the modern default vision tower choice — see [[Decision - Choosing a Vision Encoder for a VLM]] for the full comparison against CLIP and DINOv2 — and it underpins PaliGemma, Idefics2/3, and a large fraction of open [[Concept - VLM Architectures|VLMs]] released in 2024–25.

## Failure modes

SigLIP is less batch-sensitive than CLIP but is not batch-*insensitive* — it still benefits meaningfully from scale, so treating "sigmoid loss removes the scaling problem" as "batch size no longer matters" is a misread; it just moves the constraint from hard (global normalization) to soft (more data/compute still helps). The bias-temperature interaction needs care: an undertrained or poorly initialized bias can leave the loss stuck predicting near-uniform negatives for longer than expected, which shows up as a stalled loss curve early in a run rather than a clean monotonic descent. And SigLIP inherits CLIP's compositional weaknesses wholesale — the sigmoid reformulation changes *how* the contrastive signal is computed, not *what* signal noisy web alt-text pairs can teach, so weak counting, OCR-without-tiling, and spatial-relation understanding persist.

## The non-obvious

The fact that SigLIP treats every pair as an independent binary decision rather than a relative ranking means it never explicitly forces the embedding of one modality to be *closer* to any particular target than another negative — it just needs the sign of the logit to be right for each pair separately. This is a strictly weaker geometric constraint than CLIP's row/column softmax, and empirically it does not close [[Concept - The Modality Gap in Contrastive Models|the modality gap]] any more than CLIP does; if anything, the gap is a property of using two independent encoders under any contrastive-style loss, sigmoid or softmax, not an artifact specific to the normalization choice. Don't expect switching loss functions to fix modality-gap-related downstream issues (unreliable cross-modal arithmetic, connector undertraining) — that requires architectural intervention, not a loss swap.

## Connections
- [[Concept - CLIP and Contrastive Vision-Language Training]] — the softmax InfoNCE baseline SigLIP's per-pair loss directly replaces.
- [[Concept - Vision Transformers]] — the backbone architecture SigLIP trains with the sigmoid contrastive objective.
- [[Decision - Choosing a Vision Encoder for a VLM]] — where SigLIP-So400m is evaluated against CLIP and DINOv2 for real deployment choices.
- [[Concept - Data Parallelism and ZeRO]] — the distributed-training mechanism whose global all-gather requirement SigLIP's loss formulation avoids.
- [[Concept - Softmax]] — the normalization SigLIP deliberately removes, and the mechanism you need to understand to see why removing it changes the batch-size dependency.
- [[Concept - VLM Architectures]] — the downstream systems (PaliGemma, Idefics2/3) that adopted SigLIP as their default vision tower.
- [[Concept - The Modality Gap in Contrastive Models]] — the cone-separation phenomenon that persists under SigLIP just as it does under CLIP, since it isn't caused by the normalization choice.
- [[Concept - Vision-Language Connectors]] — the module that consumes SigLIP's higher-resolution features and must bridge them into an LLM's token space.

## Sources
- Zhai et al. (2023) — Sigmoid Loss for Language Image Pre-Training (SigLIP): the sigmoid pairwise loss, the negative bias initialization, and the batch-size decoupling result.
- Radford et al. (2021) — Learning Transferable Visual Models From Natural Language Supervision (CLIP): the softmax InfoNCE baseline SigLIP is compared against throughout.
