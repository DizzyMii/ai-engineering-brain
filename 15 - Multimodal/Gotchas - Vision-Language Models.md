---
tags: [gotchas, domain/multimodal, level/advanced]
aliases: []
summary: "Recurring VLM failure modes — blind models, token-budget blowup, OCR failure, hallucination — symptoms, causes, fixes, detection."
---

# Gotchas - Vision-Language Models

One `##` per gotcha, ordered by how much pain it causes.

## 1. The blind VLM: answering from language priors, not the image
**Symptom:** Confident, plausible answers that suggest the model never looked at the pixels. Asked "what color is the car", it gives the *typical* color for that car model, whatever the image shows. Swap in a different image and the answer often stays the same.
**Cause:** [[Concept - VLM Architectures]] wiring sends image features through a frozen or lightly tuned encoder and a [[Concept - Vision-Language Connectors|connector]] into an LLM whose language prior is far stronger than the gradient signal from a modest multimodal SFT set. If Stage 1 alignment (the [[Breakdown - LLaVA]] recipe) undertrains the connector, or Stage 2 SFT data skews text-heavy, the model learns that ignoring image tokens costs little loss on most examples. Captions of "typical" scenes reward the prior.
**Fix:** Raise the weight/share of image-dependent QA pairs (counting, spatial relations, rare attributes) in SFT. Check that the projector actually moved during Stage 1: alignment loss should approach the caption-model floor instead of plateauing early. Consider an auxiliary loss that penalizes answers that don't change under image ablation.
**Detection:** Run a counterfactual image-swap test; same question, different image, same answer means blind. Also run a POPE-style probe (ask about objects known to be absent from a given image). A model that looks gives chance-level answers; a blind or hallucinating one says "yes" systematically.

## 2. Object and attribute hallucination
**Symptom:** The model names plausible objects that aren't there ("a dog is sitting on the grass" with no dog) or gets color, count or material wrong.
**Cause:** The same root as #1, in generative form. Strong LLM priors fill in "what's usually there" (grass scenes usually have dogs in web captions), and SFT data heavy on prototypical scene descriptions reinforces it. The POPE benchmark (Li et al. 2023) measures it directly with yes/no presence questions calibrated against ground-truth object lists.
**Fix:** Curate SFT data with hard negatives (scenes deliberately missing an expected object), and penalize over-long, over-confident captions. At inference, [[Concept - Sampling and Decoding Parameters|lower the temperature]] or add a self-consistency check for open-ended description.
**Detection:** POPE accuracy/F1 split by random, popular and adversarial negative sampling. A big gap between random and adversarial POPE scores is the fingerprint of prior-driven hallucination.

## 3. Image-token budget blowup
**Symptom:** Latency spikes, context truncation and OOM on multi-image or high-resolution inputs that were fine in small-scale testing.
**Cause:** [[Concept - Any-Resolution Vision Encoding]] tiling (AnyRes/LLaVA-NeXT, InternVL dynamic tiling) turns one high-res image into a grid of tiles plus a thumbnail. 4 tiles + 1 thumbnail at 576 tokens/tile is ~2880 tokens for a *single* image, multiplied again by multi-image or video input. The [[Concept - KV Cache]] for those tokens then dominates memory and prefill time.
**Fix:** Budget tokens up front (cap tile count, use pixel-shuffle/unshuffle token reduction in the connector). Treat image-token count as a primary latency/cost variable next to text length from the start.
**Detection:** Log image-token count per request in production. Alert on P99 prefill latency and context-window utilization as well as total request latency.

## 4. OCR / small-text failure at low resolution
**Symptom:** The model reads large headline text fine but garbles or skips small text, dense tables or fine print. Common on document and screenshot tasks.
**Cause:** A 336px CLIP-class encoder doesn't have the pixel density to resolve small glyphs. Downsampling a 2000px document image to 336px destroys the information before the LLM sees it.
**Fix:** Route document/OCR-heavy inputs through higher-resolution encoding (any-resolution tiling, or a doc-specialized high-res encoder; see [[Decision - Choosing a Vision Encoder for a VLM]]) and accept the token cost from #3.
**Detection:** A dedicated OCR eval slice (dense small text vs. large text). Aggregate VQA accuracy averages the failure away.

## 5. Image-placeholder / chat-template mismatch
**Symptom:** Quality silently collapses after a refactor. No crash, no error, just much worse output or garbled/shifted responses.
**Cause:** The number of `<image>` placeholder tokens in the chat template has to equal the number of tokens the connector emits for that image (e.g. 576 for one 336px CLIP tile, or a tile-dependent count under AnyRes). A train/inference templating mismatch, or a connector change that alters the output token count without updating the template, silently desyncs positions. The forward pass doesn't error; it just attends to the wrong things.
**Fix:** Assert placeholder count equals connector output count on every request, not only at training setup, and version-lock the chat template to the connector configuration.
**Detection:** A unit test that runs a fixed image through the full pipeline and checks exact token count and position alignment before any long training or serving run.

## 6. Masking and padding bugs with multi-image batches
**Symptom:** Multi-image inputs do far worse than single-image inputs on matched content, or quality varies with batch composition when batches carry different image counts.
**Cause:** Image tokens sometimes get a causal mask when the encoder output should be attended bidirectionally within the image. Batches that mix image counts need careful left-padding, and naive padding can leak position information or misalign image-token blocks across examples.
**Fix:** Build and test the attention-mask construction in isolation (a unit test with synthetic multi-image batches of varying counts) before trusting end-to-end loss curves.
**Detection:** Compare single-image and multi-image eval scores on matched content. A large unexplained gap points here before it points to "the model is bad at multi-image".

## 7. The frozen-encoder ceiling
**Symptom:** No amount of LLM-side SFT pushes fine-grained perception metrics (small-object detection, precise counting, subtle attribute discrimination) past a hard ceiling.
**Cause:** When the vision encoder ([[Concept - CLIP and Contrastive Vision-Language Training]] or [[Concept - SigLIP and the Sigmoid Contrastive Loss]]) stays frozen, the common and safest choice, its features cap what the whole system can perceive. The LLM can only re-describe what the encoder already extracted. It's worse than a resolution problem: some of the frozen encoder's patch tokens carry high-norm, non-local information in place of clean local content (the [[Concept - Register Tokens and ViT Attention Artifacts]] phenomenon), which feeds noise into the LLM at any resolution.
**Fix:** Work on the encoder side: higher resolution, a stronger or dense-feature encoder, or careful unfreezing with a low LR and lots of data. More LLM-side SFT won't help.
**Detection:** Fine-grained-perception eval curves plateau while general VQA/instruction-following metrics keep improving with more SFT. You're SFT-ing the wrong component.

## 8. Multi-image and video generalization gaps
**Symptom:** A model trained almost only on single-image examples degrades sharply on multi-image reasoning and loses temporal/ordering information in video frame sequences.
**Cause:** Single-image SFT data teaches "one image, one set of facts". The model never learns to track identity or order across a sequence, so given several images it conflates them or attends mostly to the first or last.
**Fix:** Include real multi-image and temporally ordered training examples (unrelated images concatenated together don't count). Explicit position/ordering cues in the prompt (frame indices) help.
**Detection:** Evaluate on multi-image and video benchmarks separately from single-image VQA, and read the numbers with the same caution as any benchmark; [[Concept - Benchmark Contamination]] and prompt-format sensitivity apply here too.

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
