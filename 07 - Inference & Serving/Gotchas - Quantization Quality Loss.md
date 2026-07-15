---
tags: [gotchas, domain/inference-serving, level/advanced]
aliases: [quantization pitfalls, quantized model quality bugs]
summary: "Six ways quantized models lose real capability while perplexity looks fine, from proxy-metric traps to hardware precision gating."
---

# Gotchas - Quantization Quality Loss

## 1. Perplexity is a weak proxy for the capability you actually shipped

**Symptom:** a quantized checkpoint reports a WikiText perplexity delta under 1% versus the bf16 baseline — a number that looks like "basically lossless" — yet the same model drops 10-20 points on HumanEval, mangles tool-call JSON it previously produced correctly, or fails multi-step arithmetic it used to get right.
**Cause:** perplexity averages next-token prediction error over ordinary prose, and most of that probability mass sits on easy, high-frequency continuations that survive quantization noise easily. The capabilities that break are concentrated in rare, high-precision decision points — the exact digit in a calculation, the exact brace in JSON, the exact function name in a tool call — where a small quantization-induced logit shift is enough to flip the argmax even though it moves the aggregate perplexity number by almost nothing. See [[Concept - Post-Training Quantization Formats]] for why weight-only quantization concentrates error this way.
**Fix:** never gate a quantization decision on perplexity alone. Evaluate on the actual downstream tasks the model will be asked to do in production — coding benchmarks, structured tool-calling, math — and treat perplexity as a cheap sanity check, not a quality bar. See [[Concept - Statistical Rigor in Model Evaluation]] for how to run that comparison with enough samples to trust the delta.
**Detection:** run a small generative/agentic eval suite (not just log-likelihood scoring) before and after quantization; a perplexity delta under 1% combined with a double-digit-point drop on a generative benchmark is the signature of this exact trap, and it is the single most common reason quantized models get reverted after they've already shipped.

## 2. Calibration-set mismatch skews the scales that matter most

**Symptom:** a GPTQ or AWQ quantization looks fine on general chat but is measurably worse than expected specifically on the domain the model is meant to serve — code, a non-English language, a specific document format — even though the same quant recipe worked well for a similar model.
**Cause:** GPTQ and AWQ (see [[Concept - Post-Training Quantization Formats]]) fit per-group scales (and, for AWQ, per-channel salient-weight protection) against a calibration corpus. If that corpus is generic web text but the deployment domain is code or a non-English language, the scales are optimized for activation statistics the model won't actually see in production, and the weights that matter for the real domain get quantized as if they didn't matter. Over-fitting to a too-small calibration set has the mirror failure: scales tuned tightly to a handful of examples generalize poorly to anything slightly different.
**Fix:** calibrate on data that resembles the actual serving distribution — production-representative prompts, not a generic default corpus — and use enough examples (typically hundreds, not a handful) to get stable per-group statistics without overfitting to them.
**Detection:** compare quantization quality across two calibration sets (generic vs. in-domain) on a domain-specific eval; a material gap between them confirms the calibration set, not the bit-width, was the limiting factor.

## 3. Activation outliers blow up naive int8 activation quantization

**Symptom:** weight-only int4/int8 quantization works fine, but the moment activations are also quantized (W8A8, for the FLOP speedup rather than just the memory saving), quality craters — not gracefully, but with occasional wildly wrong outputs.
**Cause:** LLM activations have a small number of persistent, large-magnitude outlier channels (documented in Dettmers et al.'s LLM.int8() work) that dominate the dynamic range. A naive per-tensor int8 quantizer sets its scale to cover those outliers, which crushes the resolution available to every other (normal-magnitude) channel — the vast majority of the signal gets quantized into a handful of int8 buckets while a few outlier channels hog the range.
**Fix:** use an outlier-aware scheme — SmoothQuant-style migration of outlier magnitude from activations into weights before quantizing (weights are easier to quantize accurately than activations), or keep the outlier channels/layers in higher precision rather than forcing uniform int8 everywhere. This is exactly the problem [[Concept - FP8 and Low-Precision Inference|fp8 formats]] with fine-grained (per-token/per-channel/block) scaling are designed to sidestep, since fp8's wider dynamic range per element tolerates outliers that int8 cannot.
**Detection:** compare weight-only vs. weight+activation quantization on the same model — a large quality gap between the two that isn't explained by bit-width alone points at activation outliers, and inspecting activation magnitude histograms per channel will show a small number of channels with order-of-magnitude larger range than the rest.

## 4. Format and runtime settings silently disagree

**Symptom:** a quantized checkpoint produces plausible-looking but measurably degraded output on one serving engine while working correctly on the one it was produced with — same weights file, same claimed bit-width, different quality.
**Cause:** quantization formats carry metadata that must match between producer and consumer. GPTQ's `desc_act` (activation-order column reordering) either matches between the quantizer and the serving kernel or the dequantized weights land in the wrong positions — silent, not a crash. Group size (commonly 128) must also match. On the GGUF side, quant-level naming that looks similar (`Q4_0` vs. `Q4_K_M`) encodes materially different per-block precision and mixed-precision-per-tensor layouts, and the presence or absence of an **imatrix** (importance matrix, calibrated against real activations) changes quality substantially at the same nominal bit-width — see [[Lore - The llama.cpp Insurgency]] for how this k-quant naming scheme and the imatrix technique emerged from community practice rather than a spec.
**Fix:** treat the full quantization recipe (format, group size, `desc_act`, imatrix presence, calibration set) as part of the model's identity, pinned and versioned alongside the weights — not a free variable the serving team can silently change.
**Detection:** a quality regression that appears only after a serving-engine migration, with unchanged weight files, is the signature; diff the quantization config/metadata between the two engines' expectations before assuming the model itself changed.

## 5. Uniformly quantizing precision-sensitive components causes disproportionate damage

**Symptom:** a model quantized "successfully" by every aggregate metric fails specifically on tasks that stress routing, rare-token prediction, or output-layer precision — a mixture-of-experts model degrades more than a dense model at the same bit-width, or a model that seemed fine loses accuracy on numerically dense outputs.
**Cause:** not every parameter tolerates the same quantization error equally. MoE router/expert weights (see [[Concept - MoE Inference and Expert Parallelism]]), the `lm_head`, embedding tables, and final normalization layers are disproportionately sensitive because errors there directly corrupt the final token distribution or the routing decision that selects which expert computes at all — a small routing-logit perturbation can send a token to the wrong expert entirely, which is a much bigger failure than a small precision loss in a mid-network matmul.
**Fix:** keep these components at higher precision (bf16 or fp8) even when the bulk of the transformer blocks go to int4 — most production quantization recipes exempt `lm_head`, embeddings, and MoE routers by default for exactly this reason; verify your recipe actually does this rather than assuming it.
**Detection:** a targeted eval that stresses rare-token output or routing-sensitive behavior (long-tail vocabulary, expert-specialized domains for MoE models) degrading far more than aggregate perplexity would predict is the signature of insufficiently protected sensitive components.

## 6. Hardware precision gating produces slow emulation with no quality shortcut

**Symptom:** a team deploys an fp8- or fp4-quantized model expecting both the memory savings and the throughput speedup, gets the memory savings, but throughput is no better than bf16 — or is *worse*.
**Cause:** [[Concept - FP8 and Low-Precision Inference]] formats require native hardware support to deliver their throughput win: fp8 tensor-core paths require Hopper or newer (H100/H200), and fp4 (MXFP4/NVFP4) requires Blackwell. Running these formats on Ampere/Ada silicon means the kernel either emulates the format in software (slow) or the framework silently falls back to a different, unintended precision path. You pay the quality cost of quantization (some, even at fp8/fp4) without banking the throughput benefit that was the entire point.
**Fix:** verify the target GPU generation actually supports the tensor-core path for the chosen format before committing to it in a capacity plan; check the [[Concept - Tensor Cores]] generation against the format, not just whether the serving framework "supports" the format nominally.
**Detection:** profile the actual kernel dispatched at runtime (not just the model's declared dtype) — if an fp8 model shows no throughput improvement over bf16 on the same hardware, the tensor-core fp8 path did not engage, and you're paying for quantization with none of its upside.

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
