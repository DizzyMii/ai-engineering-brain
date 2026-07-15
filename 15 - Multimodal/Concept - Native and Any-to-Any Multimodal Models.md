---
tags: [concept, domain/multimodal, level/frontier]
aliases: [any-to-any models, native multimodality, early-fusion multimodal models, unified multimodal models, mixed-modal models]
summary: "Models that process and generate multiple modalities in one transformer with no bolted-on encoder — past projector/cross-attention VLMs."
---

# Concept - Native and Any-to-Any Multimodal Models

> **One-paragraph hook:** Every VLM covered elsewhere in this domain — [[Breakdown - LLaVA]]'s projector, [[Breakdown - Flamingo]]'s cross-attention — bolts a separately-pretrained vision encoder onto a language model. Native and any-to-any models take the more radical bet: one transformer, no dedicated vision tower, images and audio represented as tokens in (or alongside) the same vocabulary as text, trained end-to-end from scratch on mixed modalities. The payoff is a model that can both understand and *generate* any modality it was trained on through one unified interface; the cost is that mixing modalities inside one softmax turns out to be genuinely destabilizing, and this is where the field is actively fighting out the tokenization question that projector-style VLMs got to sidestep.

## The mechanism

Four architectures span the design space, from simplest to most structurally ambitious:

**Fuyu (Adept, 2023).** The minimal version: no vision encoder at all. Image patches are linearly projected straight into a decoder-only LLM's token stream, exactly as if they were text-embedding lookups — the same "patchify + linear project" step a [[Concept - Vision Transformers|ViT]] performs internally, except there is no separate pretrained tower and no fixed input resolution. Radically simple, and it handles arbitrary image size natively since there's no fixed-grid encoder to outgrow.

**Chameleon (Meta, 2024).** Early-fusion with discrete tokens: images are quantized to a fixed vocabulary of visual codes via [[Concept - VQ-VAE and Discrete Visual Tokenization|VQ tokenization]] (Chameleon's tokenizer encodes a 512×512 image into roughly 1,024 discrete tokens from an ~8,192-entry codebook), and those image tokens are interleaved with text tokens in one shared vocabulary, trained mixed-modal from random initialization. Because the same transformer emits image tokens as easily as text tokens, Chameleon can *generate* images as well as understand them — genuinely any-to-any within its trained modalities.

**Transfusion (Meta, 2024).** A hybrid loss instead of a hybrid vocabulary: a single transformer is trained with standard next-token cross-entropy on text tokens *and* a [[Deep Dive - Diffusion Models|diffusion]] denoising loss on continuous image patches, simultaneously, in the same forward pass. This sidesteps VQ tokenization's fidelity loss entirely — images stay continuous — at the cost of running two different objectives inside one model and one optimization.

**GPT-4o / Gemini — natively multimodal, closed.** Trained end-to-end on interleaved modalities from the start rather than adapted post-hoc; GPT-4o processes and generates both image and audio at low latency (folklore, weakly sourced: widely believed to route audio through discrete tokens produced by a [[Concept - Neural Audio Codecs and Residual Vector Quantization|neural audio codec]] to hit realtime latency, though the exact mechanism is undisclosed).

**The core tension.** Discrete tokenization (VQ) unifies the training objective — everything is next-token prediction over one vocabulary — but the quantization step is lossy, capping visual fidelity at whatever the codebook can represent. Continuous representations plus a diffusion or flow-matching loss preserve fidelity but break the single clean cross-entropy story, forcing the model to reconcile two different loss geometries in one training run. Any-to-any research is, right now, mostly a fight over which side of this tradeoff to sit on.

```
Fuyu:        [text][img-patch][img-patch]...[text]     -- one loss (CE), continuous patches as tokens
Chameleon:    [text][VQ-code][VQ-code]...[text]         -- one loss (CE), discrete codes as tokens
Transfusion:  [text][image patches........]             -- two losses (CE on text, diffusion on patches)
```

## In practice

Mixed-modal training from scratch surfaces a stability problem that pure-text pretraining mostly doesn't: image and text tokens have very different embedding-norm statistics, and letting them share unconstrained logit scale lets one modality's activations dominate the residual stream and destabilize the other. Chameleon's own report describes needing [[Concept - RMSNorm and LayerNorm|QK-Norm]] (normalizing queries and keys before the attention dot product) and reordering where normalization sits in the block, specifically to keep logits from diverging when text and image tokens are mixed in the same sequence — without those fixes, training mixed-modal-from-scratch is reported to blow up in ways pure-text runs at the same scale don't. This is the load-bearing tribal detail practitioners actually need before attempting a from-scratch any-to-any model: the instability is real, reproducible, and requires architectural intervention, not just a lower learning rate.

## Failure modes

- **Modality competition.** With two modalities sharing one loss (or one model with two losses), one can dominate optimization — commonly text, since text tokens vastly outnumber image tokens in typical corpora — leaving the other modality undertrained relative to a dedicated single-modality model of the same size.
- **Logit-scale divergence across modalities.** Image and text token embeddings can drift to very different norm scales during mixed training, destabilizing attention and requiring the QK-Norm / norm-reordering fixes described above; symptom is loss spikes or divergence specifically correlated with the ratio of image-to-text tokens in a batch, not seen in text-only ablations.
- **Vocabulary and compute inflation.** A shared vocabulary spanning text tokens and thousands of visual codes is much larger than a text-only vocabulary, inflating the embedding table and softmax cost.
- **Evaluation is genuinely hard to design.** There is no single settled benchmark for "how good is this model at any-to-any," so claims of any-to-any capability are harder to verify against a leaderboard than a text-only or single-modality-output claim.

## The non-obvious

The instability Chameleon reports isn't really a new, exotic multimodal phenomenon — it's the same failure mode that motivates pure-text logit-stabilization tricks like [[Concept - z-loss and Logit Soft-Capping|z-loss and soft-capping]], just triggered by a new source: instead of vocabulary-size or depth pushing logits to extreme values, it's the norm mismatch between two token populations with very different statistics sharing one embedding space and one attention mechanism. Practitioners who've fought loss spikes in large pure-text runs will recognize the symptom immediately; the fix Chameleon reached for (QK-Norm) is drawn from the same toolbox large-scale text pretraining had already built for a structurally similar problem. Any-to-any modeling isn't inventing new training-stability physics — it's finding new ways to trigger the old ones.

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
