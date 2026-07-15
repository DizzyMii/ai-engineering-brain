---
tags: [concept, domain/multimodal, level/unicorn]
aliases: [ViT registers, register tokens, attention artifacts, high-norm tokens]
summary: "ViTs stash high-norm global features in junk background patches, wrecking attention maps; register tokens give them a scratchpad instead."
---

# Concept - Register Tokens and ViT Attention Artifacts

> **One-paragraph hook:** Visualize the attention map of a trained [[Concept - Vision Transformers|Vision Transformer]] and you will usually see a handful of bright spots sitting in blank sky, blurred wall, or empty grass — patches with nothing in them lighting up harder than the actual subject. These are not a rendering glitch. The ViT has quietly repurposed a few low-information patches as a scratchpad for *global* image features, overwriting their local content and blowing up their activation norm by ~10x. The map is corrupted, dense predictions built on those tokens are noisy, and interpretability is a lie. The fix is almost embarrassingly cheap: give the model a few dedicated **register tokens** so it stops hijacking real patches.

## The mechanism

**Darcet et al. 2023 ("Vision Transformers Need Registers")** examined the internal token norms of trained ViTs across training regimes — supervised, [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]], and self-supervised DINO — and found a consistent anomaly: a small fraction of patch tokens (on the order of ~2%) carry an L2 activation norm roughly an *order of magnitude* larger than the typical token. The norm distribution is bimodal: a main lobe of normal tokens and a small high-norm outlier lobe. These outliers are not on the salient object; they appear preferentially in patches that are redundant, uniform, low-information — background sky, flat texture.

The interpretation is a *storage* story. During the forward pass the model needs somewhere to aggregate and carry global, image-level information (the kind that ends up feeding the [CLS] token or the pooled representation). Rather than using extra capacity, it recycles patches it has decided are locally uninformative, overwriting their patch content with a global summary. Evidence for this: probing the outlier tokens shows they hold *less* local/positional information about their own patch and *more* global information about the whole image than normal tokens. The patch has been demoted from "describe this region" to "hold a running global accumulator."

This has two costs:

1. **Attention maps become uninterpretable.** Other tokens attend heavily to these high-norm accumulators (they carry useful global context), so attention rollout and raw attention visualizations light up empty background instead of the object. Every "CLIP attention looks broken" screenshot is this.
2. **Dense features are corrupted.** Tasks that read *per-patch* features — semantic segmentation, monocular depth, keypoint matching, open-vocabulary grounding — get garbage at the outlier locations, because those patches no longer describe their own region.

The emergence is scale- and time-dependent: the artifacts show up in *sufficiently large* models (ViT-L and up) and only *after enough training*; small models or early checkpoints often do not exhibit them. This is why it went unnoticed for years — it is a big-model, late-training phenomenon.

**The fix — register tokens.** Append a handful of extra learnable tokens (Darcet et al. use **4**) to the input sequence alongside the patch tokens and the [CLS] token. They carry no image content and are simply *discarded* at the output. They function as dedicated scratchpad slots: the model dumps its global-accumulator computation into the registers instead of hijacking real patches. The result is a clean, unimodal token-norm distribution, attention maps that actually track the object, measurably better dense-prediction performance, and honest interpretability — at the cost of a few extra tokens (negligible: 4 tokens on top of 196-256).

```
Without registers:                With 4 registers:
[CLS] p1 p2 ... pN                [CLS] r1 r2 r3 r4 p1 p2 ... pN
        ^ p37 (sky) norm ~10x             ^ registers absorb the
          holds global junk                 global "scratchpad" load
          -> attention map noisy            -> patch tokens stay local
          -> dense features corrupt         -> clean attention + features
```

## In practice

DINOv2 adopted register tokens (the "DINOv2 with registers" variants) precisely because its whole value proposition is *clean dense features* for downstream reuse, and the artifacts were degrading segmentation and depth. If you pull DINOv2 features for a grounding or robotics stack, prefer the register variant. When building a projector-style VLM directly on raw ViT patch features (see [[Concept - Vision-Language Connectors]]), the outlier tokens inject high-norm noise straight into the LLM's token stream — a subtle contributor to weak grounding that no amount of LLM instruction tuning fixes, because the defect is upstream in the encoder. Note that many production VLMs use an encoder *without* registers (legacy CLIP-336, SigLIP-So400m), so the artifact tokens are still in the features you feed forward; the connector has to learn to route around them.

For interpretability work on vision features, always check the token-norm histogram first. If it is bimodal, your attention visualizations and any per-patch attribution are contaminated, and you should either switch to a register-equipped encoder or explicitly mask the high-norm outliers before analysis.

## Failure modes

- **Trusting a raw ViT attention map as a saliency/segmentation signal.** Symptom: bright attention on empty background, object under-attended. Detection: overlay the attention on the image; if hotspots sit on blank regions, you have artifacts. Fix: use a register-equipped encoder, or read features from DINO-style self-distillation heads designed to be clean.
- **Noisy dense predictions from a large ViT.** Symptom: speckle noise in segmentation/depth localized to a few background patches. Detection: correlate error locations with per-token norm — outliers align with errors. Fix: registers.
- **Silent VLM grounding degradation.** Symptom: a VLM that describes scenes plausibly but mislocates or hallucinates objects. Partial cause: high-norm outlier patch tokens feeding the connector. Detection: inspect encoder token norms before the projector.

## The non-obvious

This is the **vision analog of the [[Concept - Attention Sinks|attention-sink]] story in LLMs** — the same mechanism recurring across modalities. Xiao et al. 2023 (StreamingLLM) showed language models dump excess attention mass onto the first token(s), and Sun et al. 2024 ([[Concept - Massive Activations and Outlier Features|"Massive Activations in Large Language Models"]]) documented a tiny number of dimensions/tokens with enormous activation magnitude that act as fixed biases the model relies on. In both cases the transformer has learned it needs *a place to put stuff* — a no-op sink for attention it cannot avoid emitting, or a scratchpad for global state — and if you do not give it one explicitly, it improvises by commandeering a real token. Register tokens (vision) and dedicated attention-sink tokens (language) are the *same fix*: provision the scratchpad on purpose so the model stops corrupting content-bearing positions. Recognizing this cross-modal recurrence tells you where to look the next time a transformer's internals look inexplicably noisy: find what it is being forced to store, and give it somewhere to store it.

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
