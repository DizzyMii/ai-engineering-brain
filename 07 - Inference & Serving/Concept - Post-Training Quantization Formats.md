---
tags: [concept, domain/inference-serving, level/core]
aliases: [PTQ, GPTQ, AWQ, GGUF, weight quantization]
summary: "The landscape of formats (GPTQ, AWQ, GGUF k-quants, fp8) used to compress a trained model's weights for inference, and where each loses quality."
---
# Concept - Post-Training Quantization Formats
> **One-paragraph hook:** A model trained in bf16 is too big to serve cheaply; [[Concept - Why Models Don't Fit on One GPU]] applies at inference time as well as training. Post-training quantization (PTQ) compresses already-trained weights into lower-precision formats with no further training. The choice of *how* (GPTQ, AWQ, GGUF's k-quants, or fp8) decides how much memory and bandwidth you save and how much capability leaks out without anyone noticing.

## The mechanism
The first split is **weight-only vs. weight+activation** quantization. Weight-only int4/int8 stores compressed weights and dequantizes them back to bf16 right before the matmul. That saves memory and the HBM bandwidth needed to *read* the weights, which is the decode bottleneck described in [[Concept - Prefill and Decode Phases]]. It does nothing for FLOPs, since the multiply still happens in bf16. W8A8 and fp8 schemes quantize *activations* as well, so the hardware can run the matmul on faster low-precision tensor-core paths. That's a different lever, covered in [[Concept - FP8 and Low-Precision Inference]].

**GPTQ** (Frantar et al. 2022) is layer-wise and second-order. Using the Optimal Brain Quantization (OBQ) Hessian trick over a small calibration set, it minimizes the quantization error of each layer's output: it quantizes weights column by column and updates the remaining unquantized columns to compensate for the error just introduced. Typical output is 3-4 bit weights with per-group scales. The `desc_act` (activation-order) setting reorders columns by activation-magnitude importance before quantizing. It materially improves quality, but inference has to replicate the reorder exactly. If it doesn't, the dequantization mapping is wrong and output corrupts silently. That's a serving-engine-vs-quantizer format mismatch, not a quality tradeoff.

**AWQ** (Lin et al. 2023) is much cheaper. It starts from the observation that only a small fraction of weight channels (empirically ~1%) are "salient", meaning their activations are consistently large. It protects those channels by scaling them up before quantization and back down after (a form of per-channel equalization) and lets the rest quantize normally. No backprop, no Hessian, only activation statistics from a calibration pass. AWQ is typically faster to produce than GPTQ and tends to hold up better on instruction-tuned models.

**GGUF k-quants** (llama.cpp) are finer-grained and block-wise, e.g. blocks of 32 weights, each with its own scale and minimum. They also mix precision *per tensor type* within one model. `Q4_K_M` gives attention and embedding layers more bits than the less sensitive feed-forward weights, because uniform quantization damages components unevenly. The i-quants (`IQ2`, `IQ3`) go below 4 bits per weight using an *importance matrix* (imatrix), a calibration-derived weighting of which weights matter most, to keep degradation manageable at extreme compression.

Two knobs apply to all of them:
- **Group size** (128 is the de facto standard) is the number of weights sharing one scale/zero-point. Smaller groups cost more metadata and track the true weight distribution better. Larger groups are cheaper and blunter.
- **Symmetric vs. asymmetric.** Symmetric fixes the zero-point at 0, which is simpler and faster. Asymmetric learns a zero-point offset and wins on skewed weight distributions whose values aren't centered on zero.

Under everything is the outlier problem. Dettmers' LLM.int8() work found that a small number of activation *feature dimensions* carry disproportionately large magnitudes across almost every token. Naive int8 activation quantization blows up on those outliers. So activation quantization needs outlier-aware handling (SmoothQuant moves the outlier magnitude from activations into weights, where it's easier to represent), or you stay weight-only.

| Format | Bits | Calibration data? | Saves FLOPs? | Best for |
|---|---|---|---|---|
| GPTQ | 3-4 (weight) | Yes (small set) | No | GPU serving, older instruct/base models |
| AWQ | 4 (weight) | Yes (activation stats) | No | GPU serving, instruction-tuned models |
| GGUF k-quants | 2-8 (weight, mixed) | Optional (imatrix) | No | CPU/Apple-silicon/local, widest quant zoo |
| fp8 (W8A8) | 8 | No (dynamic) or minimal | Yes | Hopper+ GPUs, near-lossless + real speedup |

## In practice
Group size 128 with per-group asymmetric scales is the practical default in GPTQ and AWQ tooling. GGUF names (`Q4_0`, `Q4_K_M`, `Q5_K_M`, `IQ2_XS`, ...) encode the bit-width and whether mixed precision or an imatrix was used. Two files both labeled "4-bit" can differ noticeably in quality depending on the `K`-variant and whether an imatrix went into the quantization.

The number everyone quotes first, WikiText perplexity delta, is often deceptively small: **under 1% perplexity increase at 4-bit is typical**. That's why this domain treats perplexity alone as a weak proxy (see [[Gotchas - Quantization Quality Loss]]). Coding, math and tool-calling accuracy can degrade sharply and *silently* while perplexity looks fine. Perplexity averages over the whole distribution, and a single wrong JSON brace or off-by-one in a function call barely moves next-token log-loss even though it ruins that task.

## Failure modes
**desc_act / group-size mismatch.** If a GPTQ checkpoint was quantized with `desc_act=True` (activation-order column reordering) and the serving engine doesn't apply the identical reorder at load time, dequantization is wrong and the output is garbage. Actually broken, not subtly degraded. It's a format-contract bug, and it's the single most common "why does my quantized model output nonsense" report.

**Calibration-set mismatch.** GPTQ and AWQ both fit their scales (and, for AWQ, the salient-channel selection) on a calibration corpus. If that set is out-of-domain for the served traffic, or too small, the scales end up protecting the wrong weights. Calibrate on data that resembles production traffic instead of a generic corpus.

**Sensitive components quantized uniformly.** MoE expert layers, the `lm_head`, embeddings and the final norm take disproportionate damage from uniform quantization. Most serious recipes keep them at higher precision (or skip them) while compressing the bulk of the transformer blocks hard.

**Hardware gating that silently defeats the point.** fp8 kernels need Hopper-generation tensor cores or newer. On Ampere/Ada an fp8 model either falls back to slow software emulation or errors out. If the tensor-core path never engages, you pay the quality cost of quantization and get none of the speed, and it's easy to miss because the model still "runs."

## The non-obvious
The industry's default sanity check, perplexity on WikiText, is close to the *worst* metric for deciding whether a quantized model is safe to ship. It's a smooth, averaged signal, and the failures that matter (a malformed tool call, a dropped negative sign in a multi-step calculation) are sharp, rare and task-specific. So evaluate quantization on the downstream task the model will run in production (coding benchmarks, tool-calling success rate, math accuracy) and not on next-token loss. A clean perplexity number is necessary but nowhere near sufficient.

## Connections
- [[Concept - KV Cache Quantization]] — the parallel, independent quantization axis (compressing the KV cache rather than weights); the two are tuned separately because they bind different bottlenecks.
- [[Concept - FP8 and Low-Precision Inference]] — the hardware-native low-precision path that quantizes activations too and actually saves FLOPs, not just bandwidth.
- [[Decision - Choosing a Quantization Method]] — the decision framework for picking among these formats given hardware and accuracy budget.
- [[Gotchas - Quantization Quality Loss]] — the aggregated pitfalls (perplexity-as-weak-proxy, calibration mismatch, outliers) referenced throughout this note.
- [[Concept - Floating Point for Deep Learning]] — the number-representation fundamentals (exponent/mantissa tradeoffs) that underlie why quantization loses precision where it does.
- [[Reference - Memory Math for Transformers]] — the byte-accounting this note's memory savings plug into.
- [[Concept - Mixed Precision Training]] — the training-time analog (fp16/bf16 mixed with fp32 master weights); PTQ is the inference-time counterpart applied after training is already done.
- [[Concept - Why Models Don't Fit on One GPU]] — the motivating problem PTQ is one answer to: making a trained model small enough to serve on the hardware you actually have.
- [[Concept - Prefill and Decode Phases]] — weight-only quantization saves exactly the HBM bandwidth this note identifies as decode's bottleneck, which is why it helps latency even without saving FLOPs.

## Sources
- Frantar et al. (2022) — *GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers*. Layer-wise second-order (OBQ/Hessian) weight quantization.
- Lin et al. (2023) — *AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration*. Salient-channel protection via activation statistics, no backprop.
- Dettmers et al. (2022) — *LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale*. Identified the outlier-feature problem that motivates SmoothQuant-style activation handling.
