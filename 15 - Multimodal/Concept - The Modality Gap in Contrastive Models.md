---
tags: [concept, domain/multimodal, level/unicorn]
aliases: [modality gap, cone effect, CLIP embedding gap]
summary: "Why CLIP image and text embeddings live in two separate cones despite being trained to match, and what that breaks."
---

# Concept - The Modality Gap in Contrastive Models

> **One-paragraph hook:** You train a dual encoder with a contrastive loss to pull matched image-text pairs together, and you expect a single unified embedding space. You do not get one. Image embeddings and text embeddings occupy two distinct, non-overlapping cones separated by a persistent offset — the *modality gap*. It is not a training bug you can anneal away; it is baked in at initialization and the contrastive objective has no incentive to close it. If you compare cross-modal cosine similarities as if they were within-modal, do cross-modal vector arithmetic, or feed raw [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]] features straight into an LLM, this gap is silently corrupting your results.

## The mechanism

In a CLIP-style model, an image encoder and a text encoder each map their input to a $d$-dimensional vector, which is then L2-normalized to the unit hypersphere and compared by cosine similarity. Intuitively, since the loss maximizes similarity of matched pairs, the two clouds of embeddings should interleave. Empirically they do not: **Liang et al. 2022 ("Mind the Gap")** showed that if you PCA-project CLIP's image and text embeddings, they form two clearly separated cones, and the mean image embedding and mean text embedding stay separated by a consistent offset vector even after full training.

Two mechanisms combine to produce and preserve this.

**1. The cone effect (origin at initialization).** A deep network with random weights and nonlinearities does not spread its outputs uniformly over the sphere — it maps *all* inputs into a narrow cone with small angular spread. This is a generic property of deep post-nonlinearity representations, not something specific to vision or language. Crucially, two *different* randomly initialized networks (the image tower and the text tower) land in *different* cones. So before a single gradient step, image and text embeddings already occupy separate regions, and the angle between the two cone axes is the seed of the gap.

**2. The contrastive loss only needs relative ordering.** The InfoNCE objective is satisfied when, for each anchor, the matched pair is *closer than the mismatched in-batch negatives*:

$$\mathcal{L} = -\log \frac{\exp(\langle z_i^{img}, z_i^{txt}\rangle / \tau)}{\sum_j \exp(\langle z_i^{img}, z_j^{txt}\rangle / \tau)}$$

This is a purely *relative* constraint. A rigid translation applied to the entire text cone leaves every one of these ranking comparisons unchanged. The loss therefore has zero gradient signal pushing the two cones to co-locate globally — it can drive matched-pair similarity up *within* the existing offset. The gap is a flat direction of the loss landscape, so optimization never removes it.

**Temperature makes it worse, not better.** The learned temperature $\tau$ (initialized to 0.07 in CLIP, log-parameterized and clamped) scales the logits. A low $\tau$ sharpens the softmax so the loss concentrates on the *hardest* negatives — the ones already nearly on top of the positive. Hard-negative focus is a local, fine-grained pressure; it does nothing to pull the two modalities together at the global cone scale, so a well-tuned low temperature actively entrenches the gap.

The practical scale: matched image-text cosine similarity in CLIP is typically only ~0.2-0.3, far below the within-modality similarities of ~0.5-0.9 you see among texts or among images. That asymmetry alone should warn you that cross-modal and within-modal cosines are not on the same scale.

## In practice

The gap is measurable and, surprisingly, *manipulable*. Liang et al. showed you can shrink it by simply shifting one modality's embeddings along the gap offset vector — and doing so sometimes *improves* zero-shot classification accuracy and fairness metrics. That is strong evidence the gap is partly a nuisance artifact carrying no useful signal, rather than a meaningful structure the model needs. This connects to the **alignment/uniformity** decomposition of contrastive learning (Wang & Isola 2020): the objective trades off pulling positives together (alignment) against spreading representations over the sphere (uniformity), and neither term rewards inter-modal co-location.

Concrete consequences for systems you build:

- **Retrieval thresholds must be modality-aware.** A cosine of 0.28 might be an excellent image→text match but a terrible text→text match. Do not reuse a single similarity cutoff across modalities.
- **Cross-modal arithmetic is unreliable.** "image + (text_A − text_B)" style analogies, which look tempting in a "shared" space, cross the cone boundary and land in a region the model never sees during training.
- **VLM projectors must *bridge* the gap, not resize.** This is the deep reason a single linear resize of [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]] features into an LLM's token space underperforms a properly trained [[Concept - Vision-Language Connectors|connector]]: the connector has to learn a cross-cone transformation, not just a dimensionality match. See [[Concept - VLM Architectures]].

## Failure modes

- **Treating cross-modal cosine as calibrated probability.** Symptom: retrieval or zero-shot confidence scores that look uniformly low and refuse to threshold cleanly. Detection: histogram within-modal vs cross-modal similarities — you will see two different distributions. Fix: calibrate per-modality, or mean-center each modality before comparison.
- **Assuming more training closes the gap.** Symptom: engineers wait for the gap to disappear with scale or epochs. It does not — it is an initialization-and-objective property. Detection: measure the mean-embedding offset over training; it plateaus early and stays.
- **Naive feature transplant into an LLM.** Symptom: a "blind" VLM that answers from language priors. Partly caused by handing the LLM features that live in an alien cone with no learned bridge. Detection: counterfactual image-swap test (swap the image, see if the answer changes).

## The non-obvious

**The gap is not evidence of poor alignment — it is compatible with perfect ranking.** A model can achieve state-of-the-art retrieval while the two modalities never spatially overlap, because retrieval only cares about *ordering within a query*, and the gap is orthogonal to that. This is why "the embeddings should overlap if alignment worked" is a wrong intuition that trips up people debugging multimodal retrieval. The gap also has a mild *upside*: because modalities are linearly separable, you can trivially tell an image embedding from a text embedding, which some multimodal indexing schemes exploit. But for anything that treats the space as truly unified, the offset is a liability you must correct for explicitly.

## Connections

- [[Concept - CLIP and Contrastive Vision-Language Training]] — the training setup whose InfoNCE objective produces and preserves the gap; this note is its pathology.
- [[Concept - SigLIP and the Sigmoid Contrastive Loss]] — the sigmoid pairwise loss changes the negative structure but does not eliminate the initialization-driven gap.
- [[Concept - Vision-Language Connectors]] — the module that must learn to cross the gap when feeding a vision encoder into an LLM; the gap is *why* a learned connector beats a resize.
- [[Concept - VLM Architectures]] — projector-style VLMs inherit the gap at the encoder→LLM seam.
- [[Concept - Embedding Models]] — the same contrastive machinery in the text-only retrieval world, where the cone effect also shows up as anisotropy.
- [[Concept - Embedding Space Geometry]] — the broader story of anisotropy, cones, and non-uniform occupancy of embedding spaces.
- [[Concept - Contrastive Learning for Text Embeddings]] — alignment/uniformity tradeoff (Wang & Isola 2020) framing that explains why the loss tolerates the offset.
- [[Concept - Superposition]] — a different geometry-of-representation phenomenon; both are cases where the learned space is not the "obvious" one.
- [[Concept - Vision Transformers]] — the image tower whose random initialization seeds the image cone.

## Sources

- Liang et al. (2022) — *Mind the Gap: Understanding the Modality Gap in Multi-modal Contrastive Representation Learning* (NeurIPS 2022). Names the phenomenon, traces it to the cone effect and initialization, and shows shifting embeddings can improve accuracy/fairness.
- Wang & Isola (2020) — *Understanding Contrastive Representation Learning through Alignment and Uniformity on the Hypersphere* (ICML 2020). The alignment/uniformity decomposition that explains why the objective leaves the offset intact.
- Radford et al. (2021) — *Learning Transferable Visual Models From Natural Language Supervision* (CLIP). The dual-encoder + learned-temperature InfoNCE setup in which the gap was first observed.
