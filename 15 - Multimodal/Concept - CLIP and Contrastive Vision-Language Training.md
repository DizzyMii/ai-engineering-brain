---
tags: [concept, domain/multimodal, level/core]
aliases: [CLIP, contrastive language-image pretraining]
summary: "Dual-encoder contrastive pretraining on image-text pairs that produces a shared embedding space usable zero-shot."
---

# Concept - CLIP and Contrastive Vision-Language Training

> **One-paragraph hook:** CLIP (Radford et al. 2021) trains an image encoder and a text encoder together on noisy web-scraped (image, caption) pairs and nothing else. No per-class labels. It comes out able to classify images from classes it never saw a training example for. It was the default vision tower for VLMs for years, the text conditioner inside Stable Diffusion, and the baseline every later contrastive method, [[Concept - SigLIP and the Sigmoid Contrastive Loss]] included, gets compared to.

## The mechanism

**Architecture.** An image encoder (a [[Concept - Vision Transformers|Vision Transformer]] or ResNet) and a text encoder (a standard transformer) each map their input into a shared $d$-dimensional space. Both outputs are L2-normalized, so image-caption similarity is plain cosine similarity: direction counts, magnitude doesn't.

**Loss.** For a batch of $N$ (image, text) pairs, CLIP builds the full $N \times N$ matrix of cosine similarities between every image and every text embedding. True pairs sit on the diagonal and everything off it is a negative. The loss is [[Concept - Entropy and Cross-Entropy|cross-entropy]] applied twice and averaged: once with each row as a [[Concept - Softmax|softmax]] over texts (image→text), once with each column as a softmax over images (text→image):

$$
\mathcal{L} = \frac{1}{2}\left[\underbrace{-\frac{1}{N}\sum_i \log \frac{e^{\tau \cdot s_{ii}}}{\sum_j e^{\tau \cdot s_{ij}}}}_{\text{image} \to \text{text}} + \underbrace{-\frac{1}{N}\sum_j \log \frac{e^{\tau \cdot s_{jj}}}{\sum_i e^{\tau \cdot s_{ij}}}}_{\text{text} \to \text{image}}\right]
$$

Here $s_{ij}$ is the cosine similarity between image $i$ and text $j$, and $\tau$ is a learned temperature (initialized around 0.07 and clamped in training so it can't collapse the loss). It's the standard InfoNCE contrastive objective, run in both directions.

**Batch size matters a lot.** A pair's only negatives are the *other* pairs in the same batch. A small batch makes discrimination easy (few negatives, often trivially different). A large batch forces hard discrimination, and that's what drives representation quality. CLIP used a batch of 32,768, chosen because contrastive quality scales with it. Tying the negative set to the global batch is the main scaling pain of the softmax version: every data-parallel rank has to all-gather embeddings before the loss can even be computed. SigLIP's per-pair sigmoid loss was built to remove that bottleneck.

**Data.** CLIP trained on 400M web-scraped image-text pairs (WIT). The captions are noisy alt-text, not curated labels, but at enough scale the noise averages out. Later work (LAION, DataComp) showed *data curation* is usually the dominant lever on final CLIP quality. Filtering for caption-image agreement matters more than encoder tweaks.

## In practice

**Zero-shot classification** is the headline trick. Embed the class names as prompts ("a photo of a {class}"), embed the image once, and pick the class whose text embedding has the highest cosine similarity. Averaging embeddings over ~80 hand-written templates recovers several points of accuracy over a single template, since no one wording is unbiased. CLIP ViT-L/14 gets roughly 75% zero-shot top-1 on ImageNet this way, competitive with supervised baselines of the time, with zero labeled ImageNet training examples. It's a direct case of the shared-space mechanism in [[Concept - Cross-Modal Representation Alignment]]: classification is retrieval against a corpus of label names.

The encoders get reused well beyond classification. As a **frozen vision tower**, CLIP ViT-L/14 was the default input to [[Concept - VLM Architectures|projector-style VLMs]] for years (LLaVA's original configuration among many others). The text encoder became the conditioning signal for text-to-image diffusion. Stable Diffusion 1.x feeds CLIP text embeddings into the U-Net's cross-attention layers, so Stable Diffusion's sensitivity to prompt wording comes from the same brittleness you see in CLIP zero-shot classification ([[Concept - Latent Diffusion]] covers the conditioning). The embed-then-nearest-neighbor pattern CLIP specializes to images and text is the same one [[Concept - Embedding Models]] use for text-only retrieval.

## Failure modes

CLIP acts more like a bag-of-words model over captions than a compositional reasoner. It has trouble telling "a red cube on a blue sphere" from "a blue cube on a red sphere", because the contrastive objective rewards matching salient nouns to salient objects and never forces the model to bind attributes and relations correctly. Counting, OCR and fine spatial relations are weak for the same reason: noisy alt-text rarely states exact counts or precise layout, so there's no gradient pressure to learn them. Zero-shot accuracy also depends on prompt wording and breaks under distribution shift. A template that works on natural photos can drop sharply on sketches, renders or other out-of-distribution domains, since "a photo of" was implicitly tuned against natural-image captions.

## The non-obvious

The symmetric softmax optimizes something subtly different from "pull matched pairs together". Normalization runs over the whole row (or column), so the loss only needs the true pair to beat every negative *in the current batch*. It never asks image and text embeddings to land in the same region of space. That's the root of [[Concept - The Modality Gap in Contrastive Models]]: CLIP meets its objective perfectly while image and text embeddings sit in visibly separate cones of the embedding sphere. If you do vector arithmetic across the two modalities (e.g., "image embedding + text-A embedding − text-B embedding"), you're working across a gap the training objective never asked the model to close.

## Connections
- [[Concept - Vision Transformers]] — the standard image-encoder backbone CLIP pairs with a text transformer.
- [[Concept - SigLIP and the Sigmoid Contrastive Loss]] — the successor that replaces CLIP's global-batch softmax with a per-pair sigmoid loss to remove the batch-size coupling.
- [[Concept - The Modality Gap in Contrastive Models]] — the cone-separation phenomenon that CLIP's own loss formulation leaves unresolved.
- [[Concept - Entropy and Cross-Entropy]] — the loss family CLIP's symmetric InfoNCE is built from.
- [[Concept - Softmax]] — the row/column normalization that turns the similarity matrix into a classification loss.
- [[Concept - Embedding Models]] — the general embed-and-retrieve pattern CLIP specializes to the image-text case.
- [[Concept - VLM Architectures]] — where CLIP's frozen output typically plugs in as the vision tower.
- [[Concept - Latent Diffusion]] — where CLIP's text encoder conditions image generation via cross-attention.
- [[Concept - Cross-Modal Representation Alignment]] — the domain-level framing of the contrastive-alignment paradigm CLIP instantiates.

## Sources
- Radford et al. (2021) — Learning Transferable Visual Models From Natural Language Supervision: the original CLIP architecture, symmetric InfoNCE loss, and zero-shot classification recipe.
- Gadre et al. (2023) — DataComp; Schuhmann et al. (2022) — LAION-5B: evidence that data curation dominates architecture for CLIP-style quality.
