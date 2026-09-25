---
tags: [concept, domain/esoterica, level/advanced]
aliases: [outlier features, massive activations, LLM.int8 outliers, super weights]
summary: "A few hidden-state dims carry activations 20-1000x the rest, act as a learned bias the model depends on, and wreck naive quantization."
---
> **One-paragraph hook:** Log the per-dimension maximum magnitude of a production LLM's residual stream across a batch and a handful of numbers jump out. Sometimes it's fewer than a dozen dimensions, sometimes literally four scalar values in the whole model, sitting one to three orders of magnitude above everything else. They aren't numerical bugs or broken neurons. The network built them on purpose and depends on them, and a quantization scheme that treats them like ordinary values will silently wreck the model.

## The mechanism
Dettmers et al. 2022, "LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale," first pinned this down at production scale. Past roughly 6.7B parameters, a small, consistent set of hidden dimensions (often under 0.1% of all dims) emerges with magnitudes 20–100x the rest, and they appear consistently across tokens once a model crosses that scale. Naive per-tensor [[Concept - Post-Training Quantization Formats]] INT8 quantization takes its scale factor from the tensor's max. With an outlier present, the outlier sets the scale and every ordinary value gets crushed toward zero, which destroys accuracy. The paper's fix is mixed-precision decomposition: find the outlier feature columns, keep them in FP16, and quantize only the rest to INT8.

Sun et al. 2024, "Massive Activations in Large Language Models," went further. An even sparser subset, sometimes just **four scalar activations** across the entire model, reaches magnitudes in the thousands, another order of magnitude past the LLM.int8()-style outliers. They aren't spread evenly. They sit at specific feature dimensions *and* specific token positions, disproportionately BOS, delimiters and punctuation like periods, and their magnitude is nearly constant across input sequences, as if the model computed the same fixed value whatever the content.

That input-independence gives the mechanism away. Sun et al.'s central ablation: **zeroing** a massive activation collapses output quality catastrophically, but **replacing it with its mean across inputs** does not. If these carried meaningful signal, averaging would break things too. The model doesn't care *which* value it sees, only that *some* large value is there. That's how a fixed learned bias behaves; a data-dependent feature wouldn't survive the substitution. It's the same object [[Concept - Attention Sinks]] describes from the attention side. A head that wants to attend to nothing needs a stable, always-available target, and the massive-activation dimensions at sink positions are the residual-stream substrate for that target. Sink and outlier are two instruments pointed at one mechanism.

## In practice
Quantization tooling is organized around this, because a handful of 100–1000x outliers dominate any per-tensor scale factor.

**SmoothQuant** moves the difficulty from activations into weights. It multiplies activations by a per-channel smoothing factor, which shrinks the outlier channels, and divides the matching weight columns by the same factor. The computation is mathematically unchanged, but the activation distribution to quantize is much flatter.

**AWQ** (Activation-aware Weight Quantization) finds the "salient" weight channels, the ones that interact with high-magnitude activation channels, and keeps just that small set at higher precision while the bulk of weights go to low bit-width.

Both respond to the same measurement. Hook the residual stream, track per-dimension max magnitude over a representative batch, and the outlier dims light up immediately. That's the standard first diagnostic before designing or debugging a quantization pipeline for a new model family.

Some useful folklore: for a given checkpoint the outlier channels are stable enough to enumerate once and reuse. They correlate with the gain parameters of [[Concept - RMSNorm and LayerNorm]] and with the highest-variance residual-stream directions, so the outlier "fingerprint" is a fixed property of the checkpoint and doesn't shift from input to input.

## Failure modes
- **Per-tensor INT8/INT4 quantization with no outlier handling.** Severe accuracy loss that shows up only above ~6.7B parameters, or only on checkpoints trained past a certain scale. A handful of outliers set the scale and crush the informative majority toward zero. Fix: mixed-precision decomposition (LLM.int8()), channel migration (SmoothQuant) or salient-channel protection (AWQ).
- **FP8/INT4 KV-cache quantization that ignores outlier channels.** Quality drops on long-context tasks, often silently: no crash, just worse retrieval and coherence. [[Concept - KV Cache]] entries at sink positions carry the massive-activation dimensions, and uniform compression throws away the bias term the model relies on.
- **Zeroing outliers as "cleanup."** Removing a few weird-looking large values seems harmless and collapses quality catastrophically. The mean-substitution ablation shows the model needs *some* large value at that position. It's a bias the model is built around, not noise to prune.
- **Training instability in the same channels.** Outlier query/key channels that grow unchecked during training are implicated in [[Concept - Attention Entropy Collapse]]. The high-magnitude directions that cause quantization trouble at inference can drive runaway attention-logit growth in pretraining if left unnormalized.

## The non-obvious
The zeroing-versus-mean ablation changes how you should think about these values. They behave less like large signal and more like a hard-coded bias the network made for itself and wired into the computation. So the engineering question shifts from "how do I compress this signal without losing information" to "how do I preserve a near-constant the model treats as infrastructure." That's why protecting a tiny, fixed, enumerable set of channels (AWQ's approach) tends to beat schemes that adaptively track "important" activations per input: the important ones barely vary with input. Packing a lot into a few dimensions is a special case of [[Concept - Superposition]], though massive activations are a far more extreme, near-binary version than the typical superposed feature.

## Connections
- [[Concept - Attention Sinks]] — the sink and the massive activation are two views of the same mechanism: a fixed, always-attended, high-magnitude bias channel, observed from attention weights on one side and residual-stream magnitude on the other.
- [[Concept - Post-Training Quantization Formats]] — the entire practical motivation for characterizing outlier features: naive quantization schemes are dominated and broken by them.
- [[Concept - RMSNorm and LayerNorm]] — outlier channels correlate with specific normalization gain parameters, which is part of why they're stable and enumerable per checkpoint.
- [[Concept - Attention Entropy Collapse]] — unchecked growth in the same high-magnitude query/key channels during training is implicated in the entropy-collapse instability tracked there.
- [[Concept - Superposition]] — massive activations are an extreme, near-discrete case of packing disproportionate importance into very few dimensions, the general phenomenon superposition studies.
- [[Concept - KV Cache]] — cache compression and eviction schemes that don't special-case outlier-carrying positions silently degrade long-context quality.
- [[Snippet - Softmax-Off-By-One (Quiet Attention)]] — an engineering response aimed at the attention-weights side of the same underlying phenomenon this note describes on the activation side.
- [[Concept - Mixed Precision Training]] — the training-time analogue of the inference-time quantization problem: numeric formats with limited dynamic range must accommodate these same multi-order-of-magnitude outliers without overflow or underflow.

## Sources
- Dettmers, Lewis, Belkada & Zettlemoyer (2022) — "LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale." Identifies outlier feature emergence at ~6.7B parameters and introduces mixed-precision decomposition as the fix.
- Sun, Chen, Bair & Kolter (2024) — "Massive Activations in Large Language Models." Documents the far sparser, far larger massive-activation phenomenon and the zero-vs-mean ablation showing it functions as a fixed learned bias.
- Xiao, Lin, Seznec, Wu, Demouth & Han (2023) — "SmoothQuant: Accurate and Efficient Post-Training Quantization for Large Language Models." Migrates quantization difficulty from activations into weights via per-channel smoothing.
- Lin, Tang, Tang, Yang, Dang & Han (2023) — "AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration." Protects a small salient weight-channel set identified via activation magnitude.
