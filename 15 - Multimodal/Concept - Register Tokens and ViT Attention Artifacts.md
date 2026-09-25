---
tags: [concept, domain/multimodal, level/unicorn]
aliases: [ViT registers, register tokens, attention artifacts, high-norm tokens]
summary: "ViTs stash high-norm global features in junk background patches, wrecking attention maps; register tokens give them a scratchpad instead."
---

# Concept - Register Tokens and ViT Attention Artifacts

> **One-paragraph hook:** Visualize the attention map of a trained [[Concept - Vision Transformers|Vision Transformer]] and you'll usually see a few bright spots in blank sky, blurred wall or empty grass: patches with nothing in them lighting up harder than the subject. It isn't a rendering glitch. The ViT has taken over a few low-information patches as scratch space for *global* image features, overwriting their local content and inflating their activation norm by ~10x. The map is corrupted, dense predictions built on those tokens are noisy, and the interpretability picture is false. The fix is almost embarrassingly cheap: give the model a few dedicated **register tokens** so it stops hijacking real patches.

## The mechanism

**Darcet et al. 2023 ("Vision Transformers Need Registers")** looked at internal token norms of trained ViTs across training regimes (supervised, [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]] and self-supervised DINO) and found the same anomaly everywhere. A small fraction of patch tokens (on the order of ~2%) have an L2 activation norm roughly an *order of magnitude* above the typical token. The norm distribution is bimodal, a main lobe of normal tokens plus a small high-norm outlier lobe. The outliers aren't on the salient object. They turn up preferentially in redundant, uniform, low-information patches like background sky and flat texture.

The explanation is about *storage*. In the forward pass the model needs somewhere to gather and carry global, image-level information (the kind that ends up in the [CLS] token or the pooled representation). It doesn't spend extra capacity on it. It recycles patches it has judged locally uninformative and overwrites their content with a global summary. The evidence: probes show the outlier tokens hold *less* local/positional information about their own patch and *more* global information about the whole image than normal tokens do. The patch has been demoted from "describe this region" to "hold a running global accumulator."

That costs you twice:

1. **Attention maps stop being interpretable.** Other tokens attend heavily to these high-norm accumulators (they carry useful global context), so attention rollout and raw attention visualizations light up empty background instead of the object. Every "CLIP attention looks broken" screenshot is this.
2. **Dense features are corrupted.** Anything that reads *per-patch* features (semantic segmentation, monocular depth, keypoint matching, open-vocabulary grounding) gets garbage at the outlier locations, because those patches no longer describe their own region.

It depends on scale and training time. The artifacts appear in *sufficiently large* models (ViT-L and up) and only *after enough training*; small models and early checkpoints often don't show them. That's how it went unnoticed for years: it's a big-model, late-training effect.

**The fix: register tokens.** Append a handful of extra learnable tokens (Darcet et al. use **4**) to the input sequence next to the patch tokens and [CLS]. They carry no image content and get *discarded* at the output. They're dedicated scratch slots, so the model dumps its global-accumulator work there and leaves real patches alone. You get a clean, unimodal token-norm distribution, attention maps that follow the object, measurably better dense predictions, and honest interpretability, for a few extra tokens (negligible: 4 tokens on top of 196-256).

```
Without registers:                With 4 registers:
[CLS] p1 p2 ... pN                [CLS] r1 r2 r3 r4 p1 p2 ... pN
        ^ p37 (sky) norm ~10x             ^ registers absorb the
          holds global junk                 global "scratchpad" load
          -> attention map noisy            -> patch tokens stay local
          -> dense features corrupt         -> clean attention + features
```

## In practice

DINOv2 adopted register tokens (the "DINOv2 with registers" variants) because its whole selling point is *clean dense features* for downstream reuse, and the artifacts were hurting segmentation and depth. If you pull DINOv2 features for a grounding or robotics stack, use the register variant.

If you build a projector-style VLM on raw ViT patch features (see [[Concept - Vision-Language Connectors]]), the outlier tokens push high-norm noise straight into the LLM's token stream. It's a subtle contributor to weak grounding, and no amount of LLM instruction tuning fixes it because the defect sits upstream in the encoder. Many production VLMs use an encoder *without* registers (legacy CLIP-336, SigLIP-So400m), so the artifact tokens are still in the features you pass forward and the connector has to learn to route around them.

For interpretability work on vision features, check the token-norm histogram first. If it's bimodal, your attention visualizations and any per-patch attribution are contaminated. Switch to a register-equipped encoder or mask the high-norm outliers before analysis.

## Failure modes

- **Trusting a raw ViT attention map as a saliency/segmentation signal.** Symptom: bright attention on empty background, the object under-attended. Detection: overlay the attention on the image; hotspots on blank regions mean artifacts. Fix: a register-equipped encoder, or features from DINO-style self-distillation heads built to be clean.
- **Noisy dense predictions from a large ViT.** Symptom: speckle noise in segmentation/depth, localized to a few background patches. Detection: correlate error locations with per-token norm; the outliers line up with the errors. Fix: registers.
- **Silent VLM grounding degradation.** Symptom: a VLM that describes scenes plausibly but mislocates or hallucinates objects. Partial cause: high-norm outlier patch tokens feeding the connector. Detection: inspect encoder token norms before the projector.

## The non-obvious

This is the **vision version of the [[Concept - Attention Sinks|attention-sink]] story in LLMs**, the same mechanism turning up in another modality. Xiao et al. 2023 (StreamingLLM) showed language models dump excess attention mass onto the first token(s). Sun et al. 2024 ([[Concept - Massive Activations and Outlier Features|"Massive Activations in Large Language Models"]]) found a tiny number of dimensions/tokens with enormous activation magnitude that act as fixed biases the model depends on. Either way, the transformer has learned it needs *a place to put stuff*: a no-op sink for attention it can't avoid emitting, or scratch space for global state. If you don't provide one, it improvises by commandeering a real token. Register tokens in vision and dedicated attention-sink tokens in language are the *same fix*, a scratchpad provisioned on purpose so the model stops corrupting positions that carry content. Next time a transformer's internals look inexplicably noisy, look for what it's being forced to store and give it somewhere to store it.

## Connections

- [[Concept - Vision Transformers]] — the architecture whose trained internals exhibit the artifacts; this note is its unicorn-tier pathology.
- [[Concept - Attention Sinks]] — the LLM-side twin phenomenon (StreamingLLM); registers are the vision version of a dedicated sink token.
- [[Concept - Massive Activations and Outlier Features]] — Sun et al. 2024; the high-norm outlier tokens here are the vision instance of massive activations.
- [[Concept - The Modality Gap in Contrastive Models]] — another way trained contrastive vision features are quietly not what you assume.
- [[Concept - Sparse Autoencoders]] — the interpretability tooling that must account for outlier tokens or it decomposes noise.
- [[Concept - VLM Architectures]] — projector VLMs on raw patch features inherit the artifact tokens as input noise.
- [[Concept - CLIP and Contrastive Vision-Language Training]] — CLIP ViTs show the artifacts; explains "broken" CLIP attention visualizations.
- [[Concept - Vision-Language Connectors]] — the connector must route around outlier tokens when bridging encoder to LLM.

## Sources

- Darcet, Oquab, Mairal, Bojanowski (2023) — *Vision Transformers Need Registers* (ICLR 2024 oral). Identifies high-norm background outlier tokens across supervised/CLIP/DINO ViTs, explains them as a global-feature scratchpad, and fixes them with 4 learnable register tokens.
- Oquab et al. (2023) — *DINOv2*. The self-supervised encoder that adopted registers for clean dense features.
- Sun et al. (2024) — *Massive Activations in Large Language Models*. The language-model analog: a few activations with outsized magnitude acting as fixed biases.
- Xiao et al. (2023) — *Efficient Streaming Language Models with Attention Sinks* (StreamingLLM). The attention-sink mechanism the register story parallels.
