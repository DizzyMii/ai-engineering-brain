---
tags: [playbook, domain/multimodal, level/advanced]
aliases: []
summary: "Recipe for building a projector-style VLM from a pretrained vision encoder and LLM: two-stage training, wire-checks, verification probes."
---

# Playbook - Training a VLM from a Vision Encoder and an LLM

> **Goal:** build a working projector-style [[Concept - VLM Architectures|VLM]] from an off-the-shelf pretrained vision encoder and an off-the-shelf pretrained LLM. **When to run this:** you have (or can get) a vision encoder and an LLM checkpoint and want a multimodal instruction-following model without pretraining either one from scratch. **Prerequisites:** a captioning/interleaved dataset for alignment, a multimodal instruction dataset for SFT, and GPU budget for a short (~1 epoch, single-digit-days) run.

## Steps

1. **Select components.** Pick an encoder (e.g. SigLIP-So400m or CLIP ViT-L/14; see [[Decision - Choosing a Vision Encoder for a VLM]]), an LLM (e.g. Qwen or Llama family) and a connector (linear/MLP for simplicity, pixel-shuffle for token efficiency; see [[Concept - Vision-Language Connectors]]). Fix the target resolution and image-token budget now. Every later cost number depends on them.
   *Expected observation:* a concrete token-per-image count (e.g. 576 for one 336px tile) you can budget against context length.
   *Deviation:* if you can't state the token count before training starts, this step isn't done. Go compute it.

2. **Stage 1: feature alignment.** Freeze the encoder and the LLM, and train only the connector on ~0.5–1M caption or interleaved image-text pairs. This is the [[Breakdown - LLaVA]] recipe. At this stage the connector's only job is mapping vision features into a region of LLM-embedding space the LLM already reads as "a caption of something."
   *Expected observation:* alignment loss drops steadily and approaches the loss floor of a caption-only model trained on the same data.
   *Deviation:* a high early plateau usually means the connector LR is too low or the wrong feature layer was picked (step 3), not bad data.

3. **Wire-check before any long run.** Use the penultimate encoder feature layer (empirically stronger than the last), and confirm that the number of image tokens the connector emits equals the number of `<image>` placeholder tokens in the chat template.
   *Expected observation:* a unit test on one fixed image passes with an exact token-count match.
   *Deviation:* any mismatch is the [[Gotchas - Vision-Language Models|placeholder/chat-template gotcha]], waiting to silently wreck a multi-day run. Don't go on until this passes.

4. **Stage 2: instruction tuning.** Unfreeze the LLM (keep the encoder frozen unless you have abundant data and a good reason). Fine-tune on high-quality multimodal instruction data, a multimodal case of [[Concept - Supervised Fine-Tuning (SFT)]], mixed with some text-only data so language capability doesn't regress. Use LR ≈ 2e-5 for the LLM and a higher LR for the connector, for roughly one epoch.
   *Expected observation:* instruction-following and VQA metrics climb while a held-out text-only eval stays roughly flat.
   *Deviation:* if text-only capability drops noticeably, the text-only replay fraction in the mix is too low.

5. **Enable resolution handling if the task needs it.** If OCR or fine detail matters, turn on [[Concept - Any-Resolution Vision Encoding]] tiling and re-budget the token count against context length and prefill latency. A 4-tile-plus-thumbnail image can be ~2880 tokens.
   *Expected observation:* OCR-slice eval score rises measurably.
   *Deviation:* if OCR doesn't improve at higher resolution, suspect a tiling/position mismatch before concluding resolution doesn't help.

6. **Verify with targeted probes as well as aggregate VQA.** Run VQA accuracy, an OCR-slice eval, a hallucination probe (POPE-style) and a counterfactual image-swap test (same question, different image; the answer must change) to confirm the model conditions on the image and isn't running on the language prior.
   *Expected observation:* image-swap changes the answer where image content differs; POPE adversarial-negative accuracy is well above chance.
   *Deviation:* if image-swap doesn't change answers, you've trained a [[Gotchas - Vision-Language Models|blind VLM]]. Go back to step 4's data mix.

7. **Train in mixed precision throughout.** Run both stages in [[Concept - Mixed Precision Training]] (bf16). Watch for loss NaNs; in VLM training they usually trace to un-normalized encoder outputs feeding an under-scaled projector, not to the LLM side.
   *Expected observation:* stable loss curves in both stages, no NaN spikes.
   *Deviation:* a NaN in Stage 1 almost always means an encoder-output/projector-init scale mismatch, not an LR issue.

*Note: this recipe is for the projector-style family. Native/any-to-any fusion ([[Concept - Native and Any-to-Any Multimodal Models]]) skips stages 1–3 by training everything jointly from scratch, which is a different and more expensive playbook.*

## Verification

The run is done when (a) Stage 1 alignment loss matches the caption-model floor, (b) the step 3 wire-check passes exactly, (c) Stage 2 VQA/instruction metrics hit target with text-only eval unchanged, (d) the counterfactual image-swap test shows the model responds to image content, and (e) POPE-style hallucination accuracy clears your threshold on the adversarial split in particular. The random-negative split is easy to pass by accident.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Model answers ignore the image (blind VLM) | Weak Stage 1 alignment, or Stage 2 data too text-heavy | More image-dependent SFT examples; re-check Stage 1 loss floor; re-verify step 3 wire-check |
| OCR / small text fails | Resolution too low for the encoder | Enable [[Concept - Any-Resolution Vision Encoding]] tiling; accept the token-cost tradeoff |
| Language skills regressed after Stage 2 | Text-only replay fraction too low | Increase text-only data proportion in the SFT mix |
| Loss goes NaN | bf16 under/overflow, or un-normalized encoder output feeding the projector | Check encoder-output normalization and projector init scale before touching LR |
| Quality collapses silently, no crash | Image-placeholder count ≠ connector output count | Re-run the step 3 wire-check; version-lock chat template to connector config |
| Multi-image inputs much worse than single-image | Attention-mask or padding bug for variable image counts | Unit-test the mask construction in isolation with synthetic multi-image batches |

## Connections
- [[Concept - VLM Architectures]] — the projector-style family this playbook builds; the two-stage recipe is specific to this architecture family, not cross-attention or native fusion.
- [[Breakdown - LLaVA]] — the canonical implementation of exactly this recipe, with the concrete data sizes and compute budget this playbook generalizes.
- [[Concept - Vision-Language Connectors]] — the component trained in Stage 1 and whose output-token count drives the step 3 wire-check.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the general instruction-tuning mechanism Stage 2 is a multimodal instance of.
- [[Concept - Any-Resolution Vision Encoding]] — the optional resolution upgrade in step 5, with its token-budget cost.
- [[Concept - Mixed Precision Training]] — the numerical setup this entire playbook assumes, and the usual suspect when Stage 1 NaNs.
- [[Decision - Choosing a Vision Encoder for a VLM]] — the upstream decision (step 1) this playbook takes as given.
- [[Gotchas - Vision-Language Models]] — the failure catalog this playbook's "when it goes wrong" table draws from and cross-references.
- [[Concept - Native and Any-to-Any Multimodal Models]] — the frontier alternative to this entire recipe: skip the bolted-on encoder and train jointly from scratch instead.

## Sources
- Liu et al. (2023) — Visual Instruction Tuning (LLaVA). Source of the two-stage alignment/instruction-tuning recipe this playbook operationalizes.
- Liu et al. (2024) — Improved Baselines with Visual Instruction Tuning (LLaVA-1.5) and LLaVA-NeXT. Source of the MLP-connector and AnyRes upgrades referenced in steps 1 and 5.
- Li et al. (2023) — POPE. Source of the hallucination probe used in step 6.
