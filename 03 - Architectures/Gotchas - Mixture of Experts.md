---
tags: [gotchas, domain/architectures, level/advanced]
aliases: [MoE gotchas, MoE pitfalls, MoE routing bugs]
summary: "MoE pitfalls that survive past training: routing collapse, token dropping, batch nondeterminism, PTQ brittleness, router bugs."
---

# Gotchas - Mixture of Experts

The training-time fix for routing collapse (an auxiliary load-balance loss, or DeepSeek-V3's aux-loss-free bias) belongs to [[Concept - MoE Training and Load Balancing]] in domain 04. This note covers what still bites when that machinery is absent (a from-scratch reimplementation), frozen (fine-tuning), or only part of the picture ([[Concept - Post-Training Quantization Formats|post-training quantization]], serving batch effects). Worst first. The common thread: a router is a tiny, brittle component making discrete decisions in front of most of a [[Concept - Mixture of Experts Architecture|MoE]] model's parameters, and small errors near its decision boundary have large, silent consequences.

## 1. Routing collapse: a few experts eat all the traffic

**Symptom:** the per-expert token-count histogram is spiky. One or two experts absorb most tokens and the rest sit near zero utilization, across an entire run or, at inference, across a diverse prompt sample. Training loss looks fine while most of the parameter budget sits idle.
**Cause:** a positive feedback loop. An expert that gets slightly more tokens early gets more gradient, improves on those tokens, attracts more similar ones, and the imbalance compounds every step. Unchecked, gradient descent finds it easiest to route everything to a handful of experts. That's the lower-loss path; the router isn't buggy.
**Fix:** the actual fix (aux-loss or bias-based balancing) is a domain-04 training concern. Architecturally, two things are yours. Don't bias the router at init: near-zero weight init starts near-uniform, while large or correlated init can pre-bake a collapse. And don't set top-k so close to N that "most experts always fire" hides an imbalance in the unselected remainder.
**Detection:** log per-expert token counts (or their coefficient of variation) from step zero. Collapse shows within a few hundred steps, long before eval loss moves.

## 2. Token dropping under a capacity factor below 1.0

**Symptom:** quality degrades in a way aggregate loss doesn't show, and the degradation changes when the model is evaluated with a different batch composition than it was trained with.
**Cause:** each expert has capacity $C = \text{capacity\_factor} \times \frac{\text{tokens per batch}}{N_{\text{experts}}}$ (the GShard/Switch convention). A token routed to a full expert overflows, skips that layer's expert computation entirely, and passes straight through the residual. It's a deliberate systems tradeoff (fixed-size buffers make dispatch tractable), and the damage is set entirely by the capacity_factor knob. Fedus, Zoph, and Shazeer (2021, Switch Transformer) report 1.0–1.25 as the efficient operating range. Going lower trades dropped tokens for memory and communication savings.
**Fix:** keep capacity_factor high enough that dropping is rare (≥1.25 is a common default). Use the *same* capacity setting at eval as at train time. A mismatch shows up as a fake regression unrelated to model quality.
**Detection:** log the per-layer drop rate (overflowed tokens ÷ total tokens). If it differs between your train and eval harness, every number you report carries that confound.

## 3. Batch-composition-dependent nondeterminism at inference

**Symptom:** the same prompt at temperature 0 gives different completions depending on what else is in its batch.
**Cause:** batch-mates change each expert's load. With a capacity cap active, that changes which tokens overflow, so the computation applied to a given token depends on its neighbors. Expert-parallel dispatch implementations often impose a cap just to bound buffer sizes, whatever the training-time balancing looked like.
**Fix:** raise capacity until dropping never triggers at production batch sizes, or remove the cap at inference and accept the (usually small) load imbalance. Most production MoE serving does the latter, because inference doesn't need training's fixed-buffer discipline.
**Detection:** run one prompt inside batches of varying composition and diff outputs token by token. Divergence beyond legitimate sampling randomness is a capacity artifact, not a model property.

## 4. Fine-tuning re-collapses a balance pretraining spent trillions of tokens building

**Symptom:** after fine-tuning on a small, narrow dataset, behavior degrades on inputs unlike the fine-tuning set, though fine-tuning loss looked healthy throughout.
**Cause:** a narrow dataset pushes the router toward whichever experts specialize on it, or just receive its gradient. That unwinds a balance pretraining built over a far larger and more diverse token stream. The router is a tiny linear layer, so a handful of gradient steps can move its decisions far more than its parameter count suggests.
**Fix:** common tribal practice is to freeze router weights during fine-tuning, or give the router a learning rate roughly an order of magnitude below the expert FFN weights' LR so routing can't move faster than the experts it routes to (fine-tuning-time treatment is in domain 12).
**Detection:** compare the per-expert load histogram on a fixed, diverse eval set before and after fine-tuning. A large shift means the router re-collapsed; the experts didn't get better.

## 5. Post-training quantization silently flips routing decisions

**Symptom:** a GPTQ- or AWQ-quantized MoE model scores worse than the bit-width alone would predict for a dense model at the same precision.
**Cause:** top-k is a hard, discrete boundary. A small perturbation to router logits from [[Concept - Post-Training Quantization Formats|post-training quantization]] error can change which experts a token gets. That's qualitatively different from a dense matmul, where a small weight error just nudges the output. Expert weights also see a narrower, more specialized token distribution than a dense FFN's single weight set, tend to have a smaller effective dynamic range, and are correspondingly more sensitive at the same bit-width.
**Fix:** keep the router in fp16/bf16 even when experts go to INT4/INT8. It's a $d_{\text{model}} \times N_{\text{experts}}$ matrix and costs almost nothing to leave unquantized. Calibrate each expert's quantization on its own routed-token distribution instead of one global calibration set.
**Detection:** compare per-token top-k selections between the fp16 and quantized model on a fixed calibration batch. Even a few percent disagreement explains quality loss a smooth-error model wouldn't predict.

## 6. Missing gate renormalization or low-precision gate math

**Symptom:** output magnitude drifts subtly, or a port of a reference produces plausible but numerically different logits.
**Cause:** two easy-to-miss steps. One is computing the router softmax in bf16/fp16, which carries the same saturation risk as attention softmax in low precision. The other is forgetting to renormalize the selected top-$k$ gate weights to sum to 1. Without renormalization, the combined output scale depends on how much probability mass fell *outside* the top-$k$ set. That varies per token, so the MoE sublayer's contribution to the residual stream drifts unpredictably.
**Fix:** compute the gate softmax in fp32 and renormalize the selected weights (`gate_i / sum(gate_selected)`) before combining expert outputs. [[Snippet - Top-2 MoE Routing Layer]] has the line that does it.
**Detection:** sum the applied gate weights per token after top-$k$ selection. If they don't come to exactly 1.0, renormalization is missing or is running in a precision that loses bits.

## 7. Shared-expert bookkeeping errors in fine-grained MoE

**Symptom:** active-parameters-per-token or FLOP estimates for a DeepSeek-style model don't match the published number, or a reimplementation's parameter count is off by a small, confusing amount.
**Cause:** fine-grained designs ([[Breakdown - DeepSeek-V3 Architecture|DeepSeekMoE]]) add one or more always-on shared experts beside the top-$k$ routed pool. It's easy to leave the shared expert's compute out of active-parameter math (undercounting). It's also easy to double-count it when it's implemented as "expert 0, always selected" inside the routed top-$k$ loop instead of as a separate path.
**Fix:** implement the shared expert as an unconditional, separate module call, never a member of the routed pool, and add its parameters and FLOPs explicitly when reporting active-parameter counts.
**Detection:** recompute active params/FLOPs by hand from the config (routed: $k \times$ expert size, plus shared: $n_{\text{shared}} \times$ expert size) and diff against what the code reports.

## Connections

- [[Concept - Mixture of Experts Architecture]] — the mechanism every gotcha here is a pathology of; read it first for the router/capacity/shared-expert vocabulary used above.
- [[Concept - MoE Training and Load Balancing]] — owns the actual fix for gotcha 1 (aux-loss vs bias-based balancing); this note only covers what's visible at the architecture level.
- [[Breakdown - Mixtral 8x7B]] — the clean top-2 reference system these gotchas were first widely reported against.
- [[Breakdown - DeepSeek-V3 Architecture]] — the fine-grained-plus-shared-expert design that gotcha 7's bookkeeping trap applies to directly.
- [[Concept - Tensor and Pipeline Parallelism]] — expert placement across devices is what turns capacity limits (gotchas 2–3) into a hard systems constraint rather than a pure quality knob.
- [[Concept - Post-Training Quantization Formats]] — the general PTQ mechanism whose interaction with routing is gotcha 5's specific failure mode.
- [[Snippet - Top-2 MoE Routing Layer]] — a runnable router that makes gotcha 6's renormalization step and gotcha 1's load histogram concrete.
- [[Decision - Dense vs Mixture-of-Experts]] — several of these gotchas (capacity, batch-dependence, PTQ brittleness) are exactly the "serving complexity" cost that decision framework weighs against MoE's capacity gain.

## Sources
- Fedus, Zoph, Shazeer (2021) — Switch Transformer. Reports the 1.0–1.25 capacity-factor operating range and the token-dropping mechanism behind gotcha 2.
- Lepikhin et al. (2020) — GShard. The top-2 expert-parallel dispatch design whose capacity-buffer discipline underlies gotchas 2 and 3.
- Dai et al. (2024) — DeepSeekMoE. Introduces the fine-grained-plus-shared-expert design whose bookkeeping is gotcha 7.
- Frantar & Alistarh (2023) — GPTQ; Lin et al. (2023) — AWQ. The post-training quantization methods whose interaction with routing decisions is gotcha 5.
