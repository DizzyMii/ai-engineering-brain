---
tags: [gotchas, domain/inference-serving, level/advanced]
aliases: [quantization pitfalls, quantized model quality bugs]
summary: "Six ways quantized models lose real capability while perplexity looks fine, from proxy-metric traps to hardware precision gating."
---

# Gotchas - Quantization Quality Loss

## 1. Perplexity is a weak proxy for the capability you shipped

**Symptom:** a quantized checkpoint shows a WikiText perplexity delta under 1% against the bf16 baseline, which reads as "basically lossless." The same model drops 10-20 points on HumanEval, mangles tool-call JSON it used to get right, or fails multi-step arithmetic it used to pass.
**Cause:** perplexity averages next-token error over ordinary prose, and most of that probability mass sits on easy, high-frequency continuations that shrug off quantization noise. What breaks is concentrated in rare, high-precision decision points: the right digit in a calculation, the right brace in JSON, the right function name in a tool call. There a small quantization-induced logit shift can flip the argmax while barely moving aggregate perplexity. [[Concept - Post-Training Quantization Formats]] explains why weight-only quantization concentrates error this way.
**Fix:** don't gate a quantization decision on perplexity alone. Evaluate on the downstream tasks the model will do in production (coding benchmarks, structured tool-calling, math) and treat perplexity as a cheap sanity check, not a quality bar. [[Concept - Statistical Rigor in Model Evaluation]] covers running that comparison with enough samples to trust the delta.
**Detection:** run a small generative/agentic eval suite, not only log-likelihood scoring, before and after quantization. Perplexity delta under 1% plus a double-digit drop on a generative benchmark is this trap. It's the single most common reason quantized models get reverted after they've shipped.

## 2. Calibration-set mismatch skews the scales that matter most

**Symptom:** a GPTQ or AWQ quant looks fine on general chat but is measurably worse than expected on the domain the model is for (code, a non-English language, a specific document format), even though the same recipe worked on a similar model.
**Cause:** GPTQ and AWQ ([[Concept - Post-Training Quantization Formats]]) fit per-group scales, plus per-channel salient-weight protection for AWQ, against a calibration corpus. Calibrate on generic web text and deploy on code or another language, and the scales are tuned to activation statistics the model won't see in production. The weights that matter for the real domain get quantized as if they didn't. A too-small calibration set fails the opposite way: scales fit tightly to a handful of examples generalize badly to anything slightly different.
**Fix:** calibrate on data that looks like the serving distribution (production-representative prompts, not a default generic corpus), and use enough examples, typically hundreds and not a handful, for stable per-group statistics without overfitting.
**Detection:** quantize with two calibration sets (generic vs. in-domain) and compare on a domain-specific eval. A material gap means the calibration set was the limit, not the bit-width.

## 3. Activation outliers blow up naive int8 activation quantization

**Symptom:** weight-only int4/int8 quantization is fine, but once activations are quantized too (W8A8, for the FLOP speedup on top of the memory saving) quality craters. It doesn't degrade gracefully; you get occasional wildly wrong outputs.
**Cause:** LLM activations have a few persistent, large-magnitude outlier channels (documented in Dettmers et al.'s LLM.int8() work) that dominate the dynamic range. A naive per-tensor int8 quantizer sizes its scale to cover them, which crushes the resolution left for every normal-magnitude channel. Most of the signal lands in a handful of int8 buckets while a few outlier channels hog the range.
**Fix:** use an outlier-aware scheme. SmoothQuant-style migration moves outlier magnitude from activations into weights before quantizing (weights quantize more accurately than activations). Or keep the outlier channels/layers at higher precision instead of forcing uniform int8. [[Concept - FP8 and Low-Precision Inference|fp8 formats]] with fine-grained (per-token/per-channel/block) scaling are designed to sidestep this: fp8's wider per-element dynamic range tolerates outliers that int8 cannot.
**Detection:** compare weight-only against weight+activation quantization on the same model. A big quality gap that bit-width alone doesn't explain points at outliers, and per-channel activation magnitude histograms will show a few channels with order-of-magnitude larger range than the rest.

## 4. Format and runtime settings silently disagree

**Symptom:** a quantized checkpoint gives plausible but measurably worse output on one serving engine and works correctly on the one that produced it. Same weights file, same claimed bit-width, different quality.
**Cause:** quantization formats carry metadata that producer and consumer must agree on. GPTQ's `desc_act` (activation-order column reordering) has to match between quantizer and serving kernel, or the dequantized weights land in the wrong positions, silently, with no crash. Group size (commonly 128) must match too. In GGUF, similar-looking quant names (`Q4_0` vs. `Q4_K_M`) encode materially different per-block precision and mixed-precision-per-tensor layouts. Whether an **imatrix** (importance matrix, calibrated on real activations) was used changes quality substantially at the same nominal bit-width. [[Lore - The llama.cpp Insurgency]] tells how the k-quant naming and the imatrix technique came out of community practice instead of a spec.
**Fix:** treat the whole quantization recipe (format, group size, `desc_act`, imatrix presence, calibration set) as part of the model's identity, pinned and versioned with the weights. The serving team shouldn't be able to change it silently.
**Detection:** the signature is a quality regression that shows up only after a serving-engine migration, with unchanged weight files. Diff the quantization config and metadata against what each engine expects before assuming the model changed.

## 5. Uniformly quantizing precision-sensitive components causes disproportionate damage

**Symptom:** a model quantized "successfully" by every aggregate metric fails on tasks that stress routing, rare-token prediction, or output-layer precision. A mixture-of-experts model degrades more than a dense one at the same bit-width, or a model that seemed fine loses accuracy on numerically dense outputs.
**Cause:** parameters don't all tolerate the same quantization error. MoE router/expert weights ([[Concept - MoE Inference and Expert Parallelism]]), the `lm_head`, embedding tables and final normalization layers are disproportionately sensitive, because errors there corrupt the final token distribution directly, or the routing decision that picks which expert computes at all. A small routing-logit perturbation can send a token to the wrong expert entirely, which is far worse than a small precision loss in a mid-network matmul.
**Fix:** keep these components at higher precision (bf16 or fp8) even when most transformer blocks go to int4. Most production recipes exempt `lm_head`, embeddings and MoE routers by default for this reason. Check that yours does instead of assuming it.
**Detection:** a targeted eval on rare-token output or routing-sensitive behavior (long-tail vocabulary, expert-specialized domains for MoE) that degrades far more than aggregate perplexity predicts means the sensitive components weren't protected enough.

## 6. Hardware precision gating produces slow emulation with no quality shortcut

**Symptom:** a team ships an fp8- or fp4-quantized model expecting memory savings and a throughput speedup. They get the memory savings, but throughput is no better than bf16, or *worse*.
**Cause:** [[Concept - FP8 and Low-Precision Inference]] formats need native hardware support to deliver their throughput win. fp8 tensor-core paths need Hopper or newer (H100/H200), and fp4 (MXFP4/NVFP4) needs Blackwell. On Ampere/Ada silicon the kernel either emulates the format in software (slow) or the framework silently falls back to a different, unintended precision path. You pay quantization's quality cost (some, even at fp8/fp4) and don't get the throughput that was the whole point.
**Fix:** before committing to a format in a capacity plan, confirm the target GPU generation supports its tensor-core path. Check the [[Concept - Tensor Cores]] generation against the format, not whether the framework nominally "supports" it.
**Detection:** profile the kernel actually dispatched at runtime, not the model's declared dtype. If an fp8 model shows no throughput gain over bf16 on the same hardware, the fp8 tensor-core path didn't engage and quantization is costing you with no upside.

## Connections
- [[Decision - Choosing a Quantization Method]] — the upstream decision this note's failure modes should inform; each gotcha here is a reason a specific choice on that decision tree can go wrong in practice.
- [[Concept - Post-Training Quantization Formats]] — the GPTQ/AWQ/GGUF algorithm mechanics that gotchas #2 and #4 assume as background.
- [[Concept - KV Cache Quantization]] — a parallel quantization axis (the cache, not the weights) with its own sink-token and key/value asymmetry failure modes, not covered here.
- [[Concept - FP8 and Low-Precision Inference]] — the hardware-native format whose scaling design mitigates gotcha #3 and whose hardware gating is gotcha #6.
- [[Concept - Statistical Rigor in Model Evaluation]] — cross-domain (13) grounding for running the downstream-task comparison gotcha #1 demands correctly, with real confidence intervals rather than a single noisy run.
- [[Concept - Floating Point for Deep Learning]] — cross-domain (01) grounding for why narrow numeric formats concentrate error the way gotcha #1 and #3 describe.
- [[Concept - Tensor Cores]] — cross-domain (08) grounding for the hardware precision paths gotcha #6 depends on actually engaging.
- [[Concept - Benchmark Contamination]] — cross-domain (13) caution that a downstream eval used to validate quantization quality (per gotcha #1) must itself be trustworthy and uncontaminated to mean anything.

## Sources
- Frantar et al. (2022) — *GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers*. The `desc_act`/group-size mechanics behind gotcha #4.
- Dettmers et al. (2022) — *LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale*. Identifies the emergent activation outlier features behind gotcha #3.
- Lin et al. (2023) — *AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration*. The activation-aware calibration approach relevant to gotcha #2.
