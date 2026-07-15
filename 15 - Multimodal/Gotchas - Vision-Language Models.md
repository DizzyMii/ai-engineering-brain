---
tags: [gotchas, domain/multimodal, level/advanced]
aliases: []
summary: "Recurring VLM failure modes — blind models, token-budget blowup, OCR failure, hallucination — symptoms, causes, fixes, detection."
---

# Gotchas - Vision-Language Models

One `##` per gotcha, ordered by how much pain it causes.

## 1. The blind VLM: answering from language priors, not the image
**Symptom:** The model produces confident, plausible answers to visual questions that are wrong in ways suggesting it never looked at the pixels — e.g. it answers "what color is the car" correctly for the *typical* color of that car model, regardless of what's actually in the image. Swap the image for a different one and the answer often doesn't change.
**Cause:** [[Concept - VLM Architectures]] wiring routes image features through a frozen or lightly-tuned encoder and a [[Concept - Vision-Language Connectors|connector]] into an LLM whose language prior is enormously stronger than the gradient signal from a modest multimodal SFT set. If Stage 1 alignment (the [[Breakdown - LLaVA]] recipe) undertrains the connector, or Stage 2 SFT data skews text-heavy, the model learns that ignoring image tokens costs little loss on most training examples — captions of "typical" scenes reward the prior.
**Fix:** Increase the weight/proportion of genuinely image-dependent QA pairs (counting, spatial relations, rare attributes) in SFT; verify the projector actually moved during Stage 1 (alignment loss should approach the caption-model floor, not plateau early); consider an auxiliary loss that penalizes answers unchanged under image ablation.
**Detection:** Run a counterfactual image-swap test — same question, different image, same answer means blind. Also run a POPE-style probe (ask about objects known absent from a specific image); chance-level answers if not blind, systematic "yes" if blind or hallucinating.

## 2. Object and attribute hallucination
**Symptom:** The model names plausible-but-absent objects ("a dog is sitting on the grass" when there's no dog) or misattributes color, count, or material.
**Cause:** Same root as #1 but generative rather than binary: strong LLM priors fill in "what's usually there" (grass scenes usually have dogs in web captions), and SFT data over-representing prototypical scene descriptions reinforces it. Measured directly by the POPE benchmark (Li et al. 2023), which asks yes/no presence questions calibrated against ground-truth object lists.
**Fix:** Curate SFT data with hard negatives (scenes deliberately missing an expected object); penalize over-length, over-confident captions; at inference, [[Concept - Sampling and Decoding Parameters|lower temperature]] or add a self-consistency check for open-ended description tasks.
**Detection:** POPE accuracy/F1 stratified by random, popular, and adversarial negative sampling — a big gap between random and adversarial POPE scores is the fingerprint of prior-driven hallucination.

## 3. Image-token budget blowup
**Symptom:** Latency spikes, context truncation, and OOM on multi-image or high-resolution inputs that worked fine in small-scale testing.
**Cause:** [[Concept - Any-Resolution Vision Encoding]] tiling schemes (AnyRes/LLaVA-NeXT, InternVL dynamic tiling) turn one high-res image into a grid of tiles plus a thumbnail — 4 tiles + 1 thumbnail at 576 tokens/tile is ~2880 tokens for a *single* image, and this multiplies with multi-image or video input. The [[Concept - KV Cache]] for those tokens then dominates memory and prefill time.
**Fix:** Budget tokens up front (cap tile count, use pixel-shuffle/unshuffle token reduction in the connector) and treat image-token count as a first-class latency/cost variable alongside text length, not an afterthought.
**Detection:** Log image-token count per request in production; alert on P99 prefill latency and context-window utilization, not just total request latency.

## 4. OCR / small-text failure at low resolution
**Symptom:** The model reads large headline text fine but garbles or omits small text, dense tables, or fine print — common on document/screenshot tasks.
**Cause:** A 336px CLIP-class encoder simply doesn't have the pixel density to resolve small glyphs; downsampling a 2000px document image to 336px destroys the information before the LLM ever sees it.
**Fix:** Route document/OCR-heavy inputs through higher-resolution encoding (any-resolution tiling, or a doc-specialized high-res encoder) — see [[Decision - Choosing a Vision Encoder for a VLM]] — accepting the token cost from #3.
**Detection:** A dedicated OCR eval slice (dense small text vs. large text) rather than aggregate VQA accuracy, which averages the failure away.

## 5. Image-placeholder / chat-template mismatch
**Symptom:** Quality silently collapses after a refactor — no crash, no obvious error, just a model that suddenly performs much worse — or garbled/shifted responses.
**Cause:** The number of `<image>` placeholder tokens in the chat template must exactly equal the number of tokens the connector actually emits for that image (e.g. 576 for one 336px CLIP tile, or a tile-dependent count under AnyRes). A mismatch between train-time and inference-time templating, or a connector change that alters output token count without updating the template, desyncs positions silently — the forward pass doesn't error, it just attends to the wrong things.
**Fix:** Assert placeholder count equals connector output count at every request, not just at training setup time; version-lock the chat template to the connector configuration.
**Detection:** A unit test that runs a fixed image through the full pipeline and checks the exact token count and position alignment before any long training or serving run.

## 6. Masking and padding bugs with multi-image batches
**Symptom:** Multi-image inputs perform far worse than single-image inputs on matched content, or batches with different image counts produce inconsistent quality depending on batch composition.
**Cause:** Image tokens are sometimes given a causal mask when the encoder output should be attended to bidirectionally within the image; batches mixing different numbers of images need careful left-padding, and naive padding can leak position information or misalign image-token blocks across examples.
**Fix:** Write and test the attention-mask construction in isolation (a unit test with synthetic multi-image batches of varying counts) before trusting end-to-end loss curves.
**Detection:** Compare single-image vs. multi-image eval scores on matched content; a large unexplained gap points here before it points to "the model is bad at multi-image."

## 7. The frozen-encoder ceiling
**Symptom:** No amount of SFT on the LLM side moves fine-grained perception metrics (small-object detection, precise counting, subtle attribute discrimination) past a hard ceiling.
**Cause:** If the vision encoder ([[Concept - CLIP and Contrastive Vision-Language Training]] or [[Concept - SigLIP and the Sigmoid Contrastive Loss]]) stays frozen — the common and safest choice — its features are the perceptual ceiling for the whole system; the LLM can only re-describe what the encoder already extracted. It's worse than a pure resolution problem: some of the frozen encoder's patch tokens carry high-norm, non-local information rather than clean local content — the [[Concept - Register Tokens and ViT Attention Artifacts]] phenomenon — which injects noise into the LLM regardless of resolution.
**Fix:** If the ceiling is the bottleneck, fix the encoder side — higher resolution, a stronger/dense-feature encoder, or careful unfreezing with a low LR and large data — not more LLM-side SFT.
**Detection:** Plateaued fine-grained-perception eval curves while general VQA/instruction-following metrics keep improving with more SFT — a clear signature you're SFT-ing the wrong component.

## 8. Multi-image and video generalization gaps
**Symptom:** A model trained almost entirely on single-image examples degrades sharply on multi-image reasoning and loses temporal/ordering information on video frame sequences.
**Cause:** Single-image SFT data teaches the model "one image, one set of facts"; it never learns to track identity or order across a sequence, so with multiple images it conflates them or attends mostly to the first/last.
**Fix:** Include genuinely multi-image and temporally-ordered training examples (not just concatenated unrelated images); explicit position/ordering cues (frame indices) in the prompt help.
**Detection:** Eval on multi-image and video benchmarks separately from single-image VQA, and treat the numbers with the same eval-methodology caution as any benchmark — [[Concept - Benchmark Contamination]] and prompt-format sensitivity apply here too.

## Connections
- [[Concept - VLM Architectures]] — the fusion family (projector vs. cross-attention vs. native) determines which of these failure modes you inherit by default.
- [[Concept - Any-Resolution Vision Encoding]] — the direct cause of the token-budget blowup (#3) and the resolution/OCR tradeoff (#4).
- [[Concept - Vision-Language Connectors]] — the placeholder-count mismatch (#5) is a connector-output-vs-template bug specifically.
- [[Breakdown - LLaVA]] — the reference implementation whose two-stage recipe and design choices are the baseline these gotchas are measured against.
- [[Concept - KV Cache]] — image tokens occupy KV cache just like text tokens, so the token-budget blowup is also a serving-memory problem, not just a context problem.
- [[Concept - Benchmark Contamination]] — multi-image/video eval numbers are especially prone to the same contamination and format-sensitivity issues that plague text-only benchmarks.
- [[Concept - Sampling and Decoding Parameters]] — hallucination (#2) interacts with decoding temperature, not just training data quality.
- [[Concept - Register Tokens and ViT Attention Artifacts]] — high-norm outlier tokens from the frozen ViT are a subtler contributor to the frozen-encoder ceiling (#7): the encoder isn't just low-resolution, some of its patch tokens carry corrupted, non-local information.

## Sources
- Li et al. (2023) — POPE: Evaluating Object Hallucination in Large Vision-Language Models. Defines the random/popular/adversarial negative-sampling probe used to detect hallucination (#1, #2).
- Liu et al. (2023, 2024) — LLaVA / LLaVA-1.5 / LLaVA-NeXT. Source of the two-stage training recipe and AnyRes tiling that several gotchas here reference directly.
