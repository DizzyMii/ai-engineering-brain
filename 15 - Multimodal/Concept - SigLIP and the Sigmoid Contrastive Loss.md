---
tags: [concept, domain/multimodal, level/advanced]
aliases: [SigLIP, sigmoid loss for language-image pretraining]
summary: "The per-pair sigmoid contrastive loss that decouples image-text pretraining from global batch size and became the default VLM vision tower."
---

# Concept - SigLIP and the Sigmoid Contrastive Loss

> **One-paragraph hook:** [[Concept - CLIP and Contrastive Vision-Language Training|CLIP's]] softmax InfoNCE loss ties representation quality to an enormous global batch. Every image is normalized against every negative in the batch, so embeddings have to be all-gathered across every data-parallel rank before the loss can even be computed. SigLIP (Zhai et al. 2023) drops the row/column normalization and treats each image-text pair as its own binary classification problem. That small change to the loss removes the batch-size coupling, and it made SigLIP the default vision encoder in a wave of 2024–25 open VLMs (PaliGemma, Idefics2/3 and others).

## The mechanism

For every image, CLIP's loss takes a softmax over *all* texts in the batch (and the reverse). The normalization term $\sum_j e^{\tau s_{ij}}$ needs every negative at once, which forces a global all-gather of embeddings across [[Concept - Data Parallelism and ZeRO|data-parallel]] ranks before any gradient exists. SigLIP's loss splits into one independent term per (image, text) pair, with no [[Concept - Softmax|softmax]] normalization:

$$
\mathcal{L} = -\frac{1}{N}\sum_{i=1}^{N}\sum_{j=1}^{N} \log \sigma\big(z_{ij}(t \cdot s_{ij} + b)\big)
$$

$s_{ij}$ is the cosine similarity between image $i$ and text $j$, $t$ and $b$ are a learned temperature and bias, and $z_{ij} = 1$ if $(i,j)$ is a true pair (the diagonal) and $-1$ otherwise. Each term is an independent sigmoid binary cross-entropy ("is this pair a match, yes or no") that doesn't depend on any other pair in the batch.

**Why the global batch stops mattering.** The loss is a sum of independent per-pair terms, so you don't need every negative in one place to get a valid gradient. Each device computes its local block of the similarity matrix and swaps negatives with peers through a comparatively small all-gather; the full batch's embeddings never have to be resident and normalized together. SigLIP trains well at modest batch sizes (16K) and scales up without the softmax memory blowup that makes CLIP-scale batches (32K+) expensive to shard.

**The learnable bias, and why it starts so negative.** A batch of size $N$ has $N$ positive pairs and $N^2 - N$ negative pairs, an extreme imbalance that grows quadratically with batch size. Uncorrected, early training would be dominated by the trivial "predict negative" signal. SigLIP initializes the bias $b$ strongly negative (around $-10$), so at the start the sigmoid output sits near zero for almost everything, matching the true base rate of positives. The loss then only has to push the diagonal up, instead of fighting an uncalibrated prior across millions of negatives.

## In practice

SigLIP matches or beats CLIP quality at a much smaller batch (16K vs. CLIP's 32K). The workhorse is SigLIP-So400m, a "shape-optimized" 400M-parameter configuration typically run at 384–448px, a noticeably higher native resolution than CLIP's common 336px. Once the encoder feeds a [[Concept - Vision-Language Connectors|connector]] into an LLM, that extra resolution shows up directly as better OCR and fine-detail perception. SigLIP2 (2025) adds captioning and self-distillation objectives on top of the sigmoid contrastive loss, improving feature quality further without bringing back the global-batch dependency.

As of 2025, SigLIP-So400m at 384–448px is the modern default vision tower. [[Decision - Choosing a Vision Encoder for a VLM]] has the full comparison against CLIP and DINOv2. It underpins PaliGemma, Idefics2/3 and a large fraction of the open [[Concept - VLM Architectures|VLMs]] released in 2024–25.

## Failure modes

SigLIP is less batch-sensitive than CLIP, not batch-*insensitive*. It still gains meaningfully from scale. Reading "the sigmoid loss removes the scaling problem" as "batch size doesn't matter anymore" is wrong; the constraint moves from hard (global normalization) to soft (more data/compute still helps).

The bias-temperature interaction needs care. An undertrained or badly initialized bias can keep the loss stuck predicting near-uniform negatives longer than expected, which looks like a stalled loss curve early in the run instead of a clean monotonic descent.

SigLIP also inherits all of CLIP's compositional weaknesses. The sigmoid reformulation changes *how* the contrastive signal is computed, not *what* noisy web alt-text pairs can teach, so weak counting, OCR without tiling and poor spatial-relation understanding all persist.

## The non-obvious

Since SigLIP treats every pair as an independent binary decision and not a relative ranking, it never forces one modality's embedding to be *closer* to a target than to some other negative. It only needs each pair's logit sign to be right. That's a strictly weaker geometric constraint than CLIP's row/column softmax, and empirically it closes [[Concept - The Modality Gap in Contrastive Models|the modality gap]] no better than CLIP does. If anything, the gap comes from using two independent encoders under any contrastive-style loss, sigmoid or softmax, and isn't specific to the normalization choice. Switching loss functions won't fix downstream modality-gap problems (unreliable cross-modal arithmetic, connector undertraining). Those need an architectural change.

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
