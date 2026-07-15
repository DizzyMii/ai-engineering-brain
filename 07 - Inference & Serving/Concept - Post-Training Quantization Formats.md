---
tags: [concept, domain/inference-serving, level/core]
aliases: [PTQ, GPTQ, AWQ, GGUF, weight quantization]
summary: "The landscape of formats (GPTQ, AWQ, GGUF k-quants, fp8) used to compress a trained model's weights for inference, and where each loses quality."
---
# Concept - Post-Training Quantization Formats
> **One-paragraph hook:** A model trained in bf16 is too big to serve cheaply — [[Concept - Why Models Don't Fit on One GPU]] applies at inference time too, not just training. Post-training quantization (PTQ) compresses already-trained weights into lower-precision formats without any further training, and the choice of *how* — GPTQ, AWQ, GGUF's k-quants, or fp8 — determines how much memory and bandwidth you save versus how much capability quietly leaks out.

## The mechanism
The first fork in the road is **weight-only vs. weight+activation** quantization. Weight-only int4/int8 stores compressed weights but dequantizes back to bf16 immediately before the matmul — this saves memory and the HBM bandwidth needed to *read* the weights (which is exactly the bottleneck [[Concept - Prefill and Decode Phases]] identifies for decode) but does nothing for FLOPs, since the actual multiply still happens in bf16. W8A8 and fp8 schemes instead quantize *activations* too, which lets the hardware actually execute the matmul on faster low-precision tensor-core paths — that's a genuinely different lever, covered in [[Concept - FP8 and Low-Precision Inference]].

**GPTQ** (Frantar et al. 2022) is a layer-wise, second-order method: it minimizes the quantization error of each layer's output using the Optimal Brain Quantization (OBQ) Hessian trick over a small calibration set, quantizing weights column-by-column and updating the remaining unquantized columns to compensate for the error just introduced. Typical output is 3-4 bit weights with per-group scales. The `desc_act` (activation-order) setting reorders columns by activation-magnitude importance before quantizing them — this materially improves quality, but the reordering must be replicated exactly at inference time, or the dequantization mapping is wrong and output corrupts silently (a serving-engine-vs-quantizer format mismatch, not a quality tradeoff).

**AWQ** (Lin et al. 2023) takes a different, much cheaper approach: it observes that only a small fraction of weight channels (empirically ~1%) are "salient" — their activations have consistently large magnitude — and protects exactly those channels by scaling them up before quantization and back down after (a form of per-channel equalization), leaving the rest to quantize normally. No backprop, no Hessian, just activation statistics from a calibration pass. AWQ is typically faster to produce than GPTQ and tends to hold up better specifically on instruction-tuned models.

**GGUF k-quants** (llama.cpp) work at a finer, block-wise granularity — e.g., blocks of 32 weights, each with its own scale and minimum — and mix precision *per tensor type* within one model: `Q4_K_M` puts more bits on attention and embedding layers than on less-sensitive feed-forward weights, because uniform quantization damages components unevenly. The i-quants (`IQ2`, `IQ3`) push below 4 bits per weight using an *importance matrix* (imatrix), a calibration-derived weighting of which weights matter most, to keep degradation manageable at extreme compression.

Two knobs cut across all of these:
- **Group size** (128 is the de facto standard): the number of weights sharing one scale/zero-point. Smaller groups mean more metadata overhead but better fidelity to the true weight distribution; larger groups are cheaper but blunter.
- **Symmetric vs. asymmetric quantization**: symmetric fixes the zero-point at 0 (simpler, faster), asymmetric learns a zero-point offset — asymmetric wins for skewed weight distributions where the values aren't centered around zero.

Underneath all of it sits the outlier problem: Dettmers' LLM.int8() work identified that a small number of activation *feature dimensions* carry disproportionately large magnitudes across almost every token — naive int8 activation quantization blows up on these outliers, which is why activation quantization needs either outlier-aware handling (SmoothQuant migrates the outlier magnitude from activations into weights, where it's easier to represent) or simply staying weight-only.

| Format | Bits | Calibration data? | Saves FLOPs? | Best for |
|---|---|---|---|---|
| GPTQ | 3-4 (weight) | Yes (small set) | No | GPU serving, older instruct/base models |
| AWQ | 4 (weight) | Yes (activation stats) | No | GPU serving, instruction-tuned models |
| GGUF k-quants | 2-8 (weight, mixed) | Optional (imatrix) | No | CPU/Apple-silicon/local, widest quant zoo |
| fp8 (W8A8) | 8 | No (dynamic) or minimal | Yes | Hopper+ GPUs, near-lossless + real speedup |

## In practice
Group size 128 with per-group asymmetric scales is the practical default across GPTQ and AWQ tooling. GGUF's naming convention (`Q4_0`, `Q4_K_M`, `Q5_K_M`, `IQ2_XS`, ...) encodes both the bit-width and whether mixed precision / an imatrix was used — two files both called "4-bit" can differ noticeably in quality depending on which `K`-variant and whether an imatrix was applied during quantization. On the quality side, the number everyone quotes first — WikiText perplexity delta — is often deceptively small: **under 1% perplexity increase at 4-bit is typical**, which is why perplexity alone is treated as a weak proxy in this domain (see [[Gotchas - Quantization Quality Loss]]); downstream coding, math, and tool-calling accuracy can degrade sharply and *silently* even when perplexity looks fine, because perplexity averages over the whole distribution while a single wrong JSON brace or off-by-one in a function call is catastrophic for the specific task even though it barely moves next-token log-loss.

## Failure modes
**desc_act / group-size mismatch:** if a GPTQ checkpoint was quantized with `desc_act=True` (activation-order column reordering) and the serving engine doesn't apply the identical reorder at load time, the dequantization is wrong and output is garbage — not subtly degraded, actually broken. This is a format-contract bug, not a quality tradeoff, and it's the single most common "why does my quantized model output nonsense" report.

**Calibration-set mismatch:** GPTQ and AWQ both fit their scales (and, for AWQ, salient-channel selection) on a calibration corpus. A calibration set that's out-of-domain relative to the served traffic, or too small, skews the scales toward protecting the wrong weights — the fix is calibrating on data that resembles production traffic, not a generic corpus.

**Sensitive components quantized uniformly:** MoE expert layers, the `lm_head`, embeddings, and final norm are disproportionately damaged by uniform quantization; most serious quantization recipes keep these at higher precision (or skip them) even while aggressively compressing the bulk of the transformer blocks.

**Hardware gating that silently defeats the point:** fp8 kernels require Hopper-generation tensor cores or newer; running an fp8 model on Ampere/Ada either falls back to slow software emulation or errors outright — you pay the quality cost of quantization with none of the speed benefit if the tensor-core path never actually engages, and this failure is easy to miss because the model still "runs."

## The non-obvious
The industry's default sanity check — perplexity on WikiText — is close to the *worst* metric for deciding whether a quantized model is safe to ship, precisely because it's a smooth, averaged signal and the failures that matter (a malformed tool call, a dropped negative sign in a multi-step calculation) are sharp, rare, and task-specific. The practitioner discipline this forces: always evaluate quantization on the actual downstream task the model will run in production — coding benchmarks, tool-calling success rate, math accuracy — not next-token loss, and treat a clean perplexity number as necessary but nowhere near sufficient.

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
