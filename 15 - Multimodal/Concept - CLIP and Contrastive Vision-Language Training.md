---
tags: [concept, domain/multimodal, level/core]
aliases: [CLIP, contrastive language-image pretraining]
summary: "Dual-encoder contrastive pretraining on image-text pairs that produces a shared embedding space usable zero-shot."
---

# Concept - CLIP and Contrastive Vision-Language Training

> **One-paragraph hook:** CLIP (Radford et al. 2021) trains an image encoder and a text encoder together on nothing but noisy web-scraped (image, caption) pairs, with no per-class labels at all, and comes out the other end able to classify images it never saw a training example for. It became the default vision tower for VLMs for years, the text conditioner inside Stable Diffusion, and the reference point every later contrastive method — including [[Concept - SigLIP and the Sigmoid Contrastive Loss]] — is measured against.

## The mechanism

**Architecture.** An image encoder (a [[Concept - Vision Transformers|Vision Transformer]] or ResNet) and a text encoder (a standard transformer) each map their input to a shared $d$-dimensional space. Both output vectors are L2-normalized, so similarity between an image and a caption is measured purely as cosine similarity — direction, not magnitude.

**Loss.** For a batch of $N$ (image, text) pairs, CLIP builds the full $N \times N$ matrix of cosine similarities between every image and every text embedding in the batch. The diagonal holds the true pairs; everything off-diagonal is a negative. The loss is symmetric [[Concept - Entropy and Cross-Entropy|cross-entropy]] applied twice — once treating each row as a [[Concept - Softmax|softmax]] classification over texts (image→text) and once treating each column as a softmax over images (text→image) — averaged together:

$$
\mathcal{L} = \frac{1}{2}\left[\underbrace{-\frac{1}{N}\sum_i \log \frac{e^{\tau \cdot s_{ii}}}{\sum_j e^{\tau \cdot s_{ij}}}}_{\text{image} \to \text{text}} + \underbrace{-\frac{1}{N}\sum_j \log \frac{e^{\tau \cdot s_{jj}}}{\sum_i e^{\tau \cdot s_{ij}}}}_{\text{text} \to \text{image}}\right]
$$

where $s_{ij}$ is the cosine similarity between image $i$ and text $j$, and $\tau$ is a learned temperature (initialized around 0.07 and clamped during training to prevent it from collapsing the loss landscape). This symmetric form is the standard InfoNCE contrastive objective applied bidirectionally.

**Why batch size matters so much.** The only negatives available to any given pair are the *other* pairs currently in the batch. A small batch gives the model an easy discrimination task (few, often trivially-different negatives); a large batch forces genuinely hard discrimination, which is what drives representation quality. CLIP trained with a batch of 32,768 — a number chosen specifically because contrastive quality scales with it. This coupling between negative-set size and global batch size is the central scaling pain of the softmax formulation: it requires an all-gather of embeddings across every data-parallel rank before the loss can even be computed, and it's precisely the bottleneck SigLIP's per-pair sigmoid loss was designed to remove.

**Data.** CLIP was trained on 400M web-scraped image-text pairs (WIT). The captions are noisy — alt-text, not curated labels — but at sufficient scale the noise averages out. Later work (LAION, DataComp) showed that *data curation*, not architecture, is usually the dominant lever on final CLIP quality: filtering for caption-image agreement matters more than encoder tweaks.

## In practice

**Zero-shot classification** is CLIP's headline trick: embed the class names as prompts ("a photo of a {class}"), embed the image once, and pick the class whose text embedding has maximum cosine similarity. Prompt-template ensembling — averaging embeddings across ~80 hand-written templates — recovers several points of accuracy over a single template, because no single wording is unbiased. CLIP ViT-L/14 reaches roughly 75% zero-shot top-1 on ImageNet this way, competitive with supervised baselines of the era, with zero labeled ImageNet training examples. This zero-shot capability is a direct instance of the general shared-space mechanism described in [[Concept - Cross-Modal Representation Alignment]]: classification is retrieval against a label-name corpus.

CLIP's encoders are reused far beyond classification. As a **frozen vision tower**, CLIP ViT-L/14 was the default input to [[Concept - VLM Architectures|projector-style VLMs]] for years (LLaVA's original configuration, among many others). Its text encoder also became the conditioning signal for text-to-image diffusion — Stable Diffusion 1.x feeds CLIP text embeddings into the U-Net's cross-attention layers, which is why prompt-wording sensitivity in Stable Diffusion traces back to the same brittleness observed in CLIP zero-shot classification; see [[Concept - Latent Diffusion]] for the conditioning mechanism. The general pattern of embedding-then-nearest-neighbor that CLIP specializes for images and text is the same pattern used by [[Concept - Embedding Models]] for text-only retrieval.

## Failure modes

CLIP behaves like a bag-of-words model over captions more than a compositional reasoner: it struggles to distinguish "a red cube on a blue sphere" from "a blue cube on a red sphere," because the contrastive objective rewards matching salient nouns to salient objects without forcing the model to bind attributes and relations correctly. Counting, OCR, and fine spatial relations are weak for the same underlying reason — the training signal (noisy alt-text) rarely specifies exact counts or precise spatial layout, so there's no gradient pressure to learn it. Zero-shot accuracy is also sensitive to prompt wording and brittle under distribution shift — a template that works well on natural photos can degrade sharply on sketches, renders, or out-of-distribution domains, since the "a photo of" framing was implicitly tuned against natural-image captions.

## The non-obvious

The symmetric-softmax formulation quietly optimizes something subtly different from "pull matched pairs together" — because normalization is over the whole row (or column), the loss only cares that the true pair beats every negative *currently in the batch*, not that image and text embeddings collapse into the same region of space. That's the root cause of [[Concept - The Modality Gap in Contrastive Models]]: CLIP satisfies its own objective perfectly while leaving image and text embeddings living in visibly separate cones of the embedding sphere. If you ever do vector arithmetic across CLIP's two modalities (e.g., "image embedding + text-A embedding − text-B embedding"), know that you're operating across a gap the training objective never asked the model to close.

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
