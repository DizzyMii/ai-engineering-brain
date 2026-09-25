---
tags: [concept, domain/multimodal, level/frontier]
aliases: [any-to-any models, native multimodality, early-fusion multimodal models, unified multimodal models, mixed-modal models]
summary: "Models that process and generate multiple modalities in one transformer with no bolted-on encoder — past projector/cross-attention VLMs."
---

# Concept - Native and Any-to-Any Multimodal Models

> **One-paragraph hook:** Every other VLM in this domain ([[Breakdown - LLaVA]]'s projector, [[Breakdown - Flamingo]]'s cross-attention) bolts a separately pretrained vision encoder onto a language model. Native and any-to-any models make a more radical bet: one transformer, no dedicated vision tower, images and audio as tokens in (or next to) the text vocabulary, trained end to end from scratch on mixed modalities. You get one model that can both understand and *generate* every modality it was trained on through one interface. The price is that mixing modalities inside one softmax turns out to be destabilizing, and this is where the field is still fighting over the tokenization question that projector-style VLMs got to dodge.

## The mechanism

Four architectures cover the design space, from simplest to most ambitious.

**Fuyu (Adept, 2023).** The minimal version, with no vision encoder at all. Image patches are linearly projected straight into a decoder-only LLM's token stream as if they were text-embedding lookups. It's the "patchify + linear project" step a [[Concept - Vision Transformers|ViT]] does internally, minus the separate pretrained tower and the fixed input resolution. Very simple, and any image size works natively since no fixed-grid encoder exists to outgrow.

**Chameleon (Meta, 2024).** Early fusion with discrete tokens. [[Concept - VQ-VAE and Discrete Visual Tokenization|VQ tokenization]] turns images into codes from a fixed visual vocabulary (Chameleon's tokenizer maps a 512×512 image to roughly 1,024 discrete tokens from an ~8,192-entry codebook). Those image tokens are interleaved with text tokens in one shared vocabulary and trained mixed-modal from random initialization. The same transformer emits image tokens as easily as text tokens, so Chameleon *generates* images as well as understanding them: any-to-any within its trained modalities.

**Transfusion (Meta, 2024).** A hybrid loss in place of a hybrid vocabulary. One transformer trains with standard next-token cross-entropy on text tokens *and* a [[Deep Dive - Diffusion Models|diffusion]] denoising loss on continuous image patches, at the same time, in the same forward pass. Images stay continuous, so VQ's fidelity loss never happens. The cost is running two different objectives inside one model and one optimization.

**GPT-4o / Gemini: natively multimodal, closed.** Trained end to end on interleaved modalities from the start, not adapted afterward. GPT-4o processes and generates both image and audio at low latency (folklore, weakly sourced: it's widely believed to route audio through discrete tokens from a [[Concept - Neural Audio Codecs and Residual Vector Quantization|neural audio codec]] to reach realtime latency, but the mechanism is undisclosed).

**The core tension.** Discrete tokenization (VQ) unifies the training objective, since everything becomes next-token prediction over one vocabulary. But quantization is lossy, and visual fidelity is capped at what the codebook can represent. Continuous representations with a diffusion or flow-matching loss keep fidelity but break the single clean cross-entropy story, and the model has to reconcile two loss geometries in one run. Right now, any-to-any research is mostly a fight over which side of that tradeoff to take.

```
Fuyu:        [text][img-patch][img-patch]...[text]     -- one loss (CE), continuous patches as tokens
Chameleon:    [text][VQ-code][VQ-code]...[text]         -- one loss (CE), discrete codes as tokens
Transfusion:  [text][image patches........]             -- two losses (CE on text, diffusion on patches)
```

## In practice

Training mixed-modal from scratch hits a stability problem pure-text pretraining mostly doesn't. Image and text tokens have very different embedding-norm statistics, and if they share an unconstrained logit scale, one modality's activations take over the residual stream and destabilize the other. Chameleon's report describes needing [[Concept - RMSNorm and LayerNorm|QK-Norm]] (normalizing queries and keys before the attention dot product) and moving where normalization sits in the block, to keep logits from diverging when text and image tokens share a sequence. Without those fixes, mixed-modal-from-scratch training is reported to blow up in ways pure-text runs at the same scale don't. Know this before training an any-to-any model from scratch: the instability is real and reproducible, and it takes an architectural change. A lower learning rate won't fix it.

## Failure modes

- **Modality competition.** When two modalities share one loss (or one model carries two losses), one can dominate optimization. Commonly that's text, since text tokens vastly outnumber image tokens in typical corpora, leaving the other modality undertrained next to a dedicated single-modality model of the same size.
- **Logit-scale divergence across modalities.** Image and text embeddings can drift to very different norm scales during mixed training, destabilizing attention and calling for the QK-Norm / norm-reordering fixes above. The symptom is loss spikes or divergence that track the batch's image-to-text token ratio and don't appear in text-only ablations.
- **Vocabulary and compute inflation.** A shared vocabulary of text tokens plus thousands of visual codes is much larger than a text-only one, which inflates the embedding table and the softmax cost.
- **Evaluation is hard to design.** No single benchmark for "how good is this model at any-to-any" has settled, so any-to-any claims are harder to check against a leaderboard than text-only or single-output-modality claims.

## The non-obvious

The instability Chameleon reports isn't an exotic new multimodal phenomenon. It's the failure mode behind pure-text logit-stabilization tricks like [[Concept - z-loss and Logit Soft-Capping|z-loss and soft-capping]], set off by a new cause. In text runs, vocabulary size or depth pushes logits to extremes. Here it's the norm mismatch between two token populations with very different statistics sharing one embedding space and one attention mechanism. If you've fought loss spikes in large pure-text runs you'll recognize the symptom, and Chameleon's fix (QK-Norm) came from the toolbox text pretraining had already built for a very similar problem. Any-to-any modeling hasn't found new training-stability physics, only new ways to trigger the old ones.

## Connections
- [[Concept - VLM Architectures]] — native/any-to-any is the early-fusion endpoint of the same fusion taxonomy that projector- and cross-attention-style VLMs occupy the other points of.
- [[Breakdown - LLaVA]] — the projector-style VLM these early-fusion architectures are defined in contrast to: no separate pretrained encoder or connector at all.
- [[Breakdown - Flamingo]] — the cross-attention-fusion VLM at the other end of the same spectrum, keeping its LLM fully frozen rather than training one transformer over mixed tokens.
- [[Concept - Vision Transformers]] — Fuyu's linear patch projection is literally a ViT's patchify step run with no separate pretrained tower behind it.
- [[Concept - VQ-VAE and Discrete Visual Tokenization]] — the discrete tokenization scheme Chameleon and Fuyu-style discrete approaches depend on to represent images as vocabulary entries.
- [[Deep Dive - Diffusion Models]] — Transfusion's image-generation loss is exactly the diffusion denoising objective, applied per-patch inside one transformer alongside text cross-entropy.
- [[Concept - Flow Matching]] — modern any-to-any image-output heads increasingly reach for flow-matching objectives instead of DDPM-style diffusion for the continuous-modality loss.
- [[Deep Dive - The Transformer]] — every one of these architectures is still fundamentally one transformer; the innovation is entirely in what token stream and loss it's fed.
- [[Concept - RMSNorm and LayerNorm]] — the QK-Norm and norm-reordering fixes Chameleon needed are direct modifications to this normalization layer.
- [[Concept - Neural Audio Codecs and Residual Vector Quantization]] — GPT-4o-style low-latency audio in/out is widely believed to route through discrete audio tokens produced by exactly this class of codec.
- [[Concept - Mixed Precision Training]] — the logit-scale divergence across modalities interacts directly with bf16/fp16 dynamic-range choices during mixed-modal training.
- [[Concept - z-loss and Logit Soft-Capping]] — the same family of logit-stabilization tricks built for pure-text training instability is what Chameleon had to borrow to keep mixed-modality logits from diverging.

## Sources
- Bavishi et al. (2023) — Fuyu-8B technical report (Adept) — no-vision-encoder linear patch projection into a decoder-only LLM.
- Chameleon Team (2024) — "Chameleon: Mixed-Modal Early-Fusion Foundation Models" (Meta) — discrete early-fusion tokenization, QK-Norm and norm-reordering stability fixes.
- Zhou et al. (2024) — "Transfusion: Predict the Next Token and Diffuse Images with One Multi-Modal Model" (Meta) — combined autoregressive text and diffusion image objective in one transformer.
- OpenAI (2024) — GPT-4o system card — natively multimodal, low-latency image and audio input/output.
