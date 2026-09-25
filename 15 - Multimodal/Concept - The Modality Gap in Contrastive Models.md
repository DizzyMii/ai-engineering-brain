---
tags: [concept, domain/multimodal, level/unicorn]
aliases: [modality gap, cone effect, CLIP embedding gap]
summary: "Why CLIP image and text embeddings live in two separate cones despite being trained to match, and what that breaks."
---

# Concept - The Modality Gap in Contrastive Models

> **One-paragraph hook:** Train a dual encoder with a contrastive loss that pulls matched image-text pairs together and you'd expect one unified embedding space. You don't get one. Image embeddings and text embeddings sit in two distinct, non-overlapping cones separated by a persistent offset: the *modality gap*. More annealing won't remove it. It's baked in at initialization, and the contrastive objective has no incentive to close it. If you compare cross-modal cosine similarities as though they were within-modal, do cross-modal vector arithmetic, or feed raw [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]] features straight into an LLM, this gap is silently corrupting your results.

## The mechanism

In a CLIP-style model, an image encoder and a text encoder each map their input to a $d$-dimensional vector, L2-normalize it onto the unit hypersphere, and compare by cosine similarity. Since the loss maximizes similarity for matched pairs, you'd expect the two clouds to interleave. They don't. **Liang et al. 2022 ("Mind the Gap")** PCA-projected CLIP's image and text embeddings and found two clearly separated cones, with the mean image embedding and mean text embedding separated by a consistent offset vector even after full training.

Two mechanisms create the gap and keep it there.

**1. The cone effect (it starts at initialization).** A deep network with random weights and nonlinearities doesn't spread its outputs evenly over the sphere. It maps *all* inputs into a narrow cone with a small angular spread. That's a generic property of deep post-nonlinearity representations and has nothing to do with vision or language in particular. Two *different* randomly initialized networks (the image tower and the text tower) land in *different* cones, so before the first gradient step the two modalities already occupy separate regions. The angle between the cone axes is the seed of the gap.

**2. The contrastive loss only needs relative ordering.** InfoNCE is satisfied when, for each anchor, the matched pair is *closer than the mismatched in-batch negatives*:

$$\mathcal{L} = -\log \frac{\exp(\langle z_i^{img}, z_i^{txt}\rangle / \tau)}{\sum_j \exp(\langle z_i^{img}, z_j^{txt}\rangle / \tau)}$$

The constraint is purely *relative*. Translate the whole text cone rigidly and none of these ranking comparisons change. So the loss has zero gradient pushing the cones to co-locate globally, and it can raise matched-pair similarity *within* the existing offset. The gap is a flat direction of the loss, and optimization never removes it.

**Temperature makes it worse.** The learned temperature $\tau$ (initialized to 0.07 in CLIP, log-parameterized and clamped) scales the logits. A low $\tau$ sharpens the softmax so the loss focuses on the *hardest* negatives, the ones already almost on top of the positive. That's a local, fine-grained pressure. It does nothing to pull the modalities together at the scale of the cones, so a well-tuned low temperature actually entrenches the gap.

For scale: matched image-text cosine similarity in CLIP is typically only ~0.2-0.3, far below the ~0.5-0.9 you see among texts or among images. That asymmetry alone should tell you cross-modal and within-modal cosines aren't on the same scale.

## In practice

The gap can be measured and, surprisingly, *manipulated*. Liang et al. showed you can shrink it by shifting one modality's embeddings along the gap offset vector, and that doing so sometimes *improves* zero-shot classification accuracy and fairness metrics. That's strong evidence the gap is partly a nuisance artifact with no useful signal, not structure the model needs. It fits the **alignment/uniformity** decomposition of contrastive learning (Wang & Isola 2020): the objective trades pulling positives together (alignment) against spreading representations over the sphere (uniformity), and neither term rewards the modalities sharing a location.

What this means for systems you build:

- **Retrieval thresholds have to be modality-aware.** A cosine of 0.28 might be an excellent image→text match and a terrible text→text match. Don't reuse one similarity cutoff across modalities.
- **Cross-modal arithmetic is unreliable.** "image + (text_A − text_B)" analogies look tempting in a "shared" space, but they cross the cone boundary and land in a region the model never saw in training.
- **VLM projectors have to *bridge* the gap.** Resizing isn't enough. That's the underlying reason a single linear resize of [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]] features into an LLM's token space does worse than a properly trained [[Concept - Vision-Language Connectors|connector]]: the connector must learn a cross-cone transformation on top of matching dimensions. See [[Concept - VLM Architectures]].

## Failure modes

- **Treating cross-modal cosine as a calibrated probability.** Symptom: retrieval or zero-shot confidence scores that all look low and won't threshold cleanly. Detection: histogram within-modal vs. cross-modal similarities and you'll see two different distributions. Fix: calibrate per modality, or mean-center each modality before comparing.
- **Assuming more training closes the gap.** Symptom: engineers waiting for the gap to vanish with scale or epochs. It won't; it comes from initialization plus the objective. Detection: track the mean-embedding offset over training. It plateaus early and stays.
- **Naive feature transplant into an LLM.** Symptom: a "blind" VLM that answers from language priors. Part of the cause is handing the LLM features from an alien cone with no learned bridge. Detection: the counterfactual image-swap test (swap the image, see whether the answer changes).

## The non-obvious

**The gap doesn't mean alignment failed. It's compatible with perfect ranking.** A model can reach state-of-the-art retrieval with the two modalities never overlapping in space, because retrieval only cares about *ordering within a query* and the gap is orthogonal to that. "The embeddings should overlap if alignment worked" is a wrong intuition that trips people up when they debug multimodal retrieval. The gap has a small *upside*, too: the modalities are linearly separable, so telling an image embedding from a text embedding is trivial, and some multimodal indexing schemes use that. For anything that treats the space as truly unified, though, the offset is a liability you have to correct for explicitly.

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
