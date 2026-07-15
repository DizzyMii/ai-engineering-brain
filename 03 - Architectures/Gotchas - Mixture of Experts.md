---
tags: [gotchas, domain/architectures, level/advanced]
aliases: [MoE gotchas, MoE pitfalls, MoE routing bugs]
summary: "MoE pitfalls that survive past training: routing collapse, token dropping, batch nondeterminism, PTQ brittleness, router bugs."
---

# Gotchas - Mixture of Experts

The training-time fix for routing collapse — an auxiliary load-balance loss or DeepSeek-V3's aux-loss-free bias — belongs to [[Concept - MoE Training and Load Balancing]] in domain 04. What's cataloged here is everything that still bites once that machinery is either absent (a from-scratch reimplementation), frozen (fine-tuning), or simply not the whole story ([[Concept - Post-Training Quantization Formats|post-training quantization]], serving batch effects). Ordered by how much pain each causes in practice. The recurring theme: a router is a tiny, brittle, discrete-decision component sitting in front of most of a [[Concept - Mixture of Experts Architecture|MoE]] model's parameters, and small errors near that decision boundary have outsized, silent consequences.

## 1. Routing collapse: a few experts eat all the traffic

**Symptom:** The per-expert token-count histogram is spiky — one or two experts absorb most tokens, the rest sit near zero utilization across an entire run or, at inference, across a diverse prompt sample. Training loss looks fine even though the model is structurally wasting most of its parameter budget.
**Cause:** Positive feedback loop: an expert that gets slightly more tokens early gets more gradient signal, gets better at whatever those tokens look like, becomes more attractive to the router for similar tokens, and the imbalance compounds every step. Left unchecked, gradient descent finds it easiest to route everything to a handful of experts — it's the lower-loss path, not a bug in the router.
**Fix:** The real fix (aux-loss or bias-based balancing) is a domain-04 training concern. What you own architecturally: don't structurally bias the router at init (a router with near-zero weight init starts near-uniform; large or correlated init can pre-bake a collapse), and don't set top-k so close to N that "most experts always fire" masks a real imbalance in the unselected remainder.
**Detection:** Log per-expert token counts (or their coefficient of variation) from step zero — collapse is visible within a few hundred steps, long before it shows up in eval loss.

## 2. Token dropping under a capacity factor below 1.0

**Symptom:** Quality degrades in a way invisible in aggregate loss, and the degradation differs when the same model is evaluated with a different batch composition than it was trained with.
**Cause:** Each expert has capacity $C = \text{capacity\_factor} \times \frac{\text{tokens per batch}}{N_{\text{experts}}}$ (the GShard/Switch convention). Tokens routing to an already-full expert overflow and skip that layer's expert computation entirely, passing straight through the residual — a deliberate systems tradeoff (fixed-size buffers are what makes dispatch tractable), not a crash, but one whose damage is entirely controlled by the capacity_factor knob. Fedus, Zoph, and Shazeer (2021, Switch Transformer) report capacity_factor 1.0–1.25 as the efficient operating range; pushing it lower trades dropped tokens for memory and communication savings.
**Fix:** Keep capacity_factor high enough that dropping is rare (≥1.25 is a common default), and — critically — use the *same* capacity setting at eval as at train time, or the mismatch shows up as a fake regression that has nothing to do with model quality.
**Detection:** Log the per-layer drop rate (overflowed tokens ÷ total tokens); if it differs between your train and eval harness, that's a silent confound baked into any number you report.

## 3. Batch-composition-dependent nondeterminism at inference

**Symptom:** The identical prompt at temperature 0 produces different completions depending on what else shares its batch — surprising for an architecture that "just runs a forward pass."
**Cause:** Which tokens land in the same batch changes each expert's load; if a capacity cap is active, that changes which tokens overflow, which changes the actual computation performed on a given token as a function of its batch-mates. Expert-parallel dispatch implementations often impose a cap purely to bound buffer sizes, independent of any training-time balancing concern.
**Fix:** Either raise capacity high enough that dropping never triggers at production batch sizes, or drop the cap entirely at inference and accept the (usually small) load imbalance — most production MoE serving takes the latter path, since inference doesn't need training's fixed-buffer discipline.
**Detection:** Run an identical prompt inside batches of varying composition and diff outputs token-for-token; any divergence beyond legitimate sampling randomness is a capacity artifact, not a model property.

## 4. Fine-tuning re-collapses a balance pretraining spent trillions of tokens building

**Symptom:** After fine-tuning on a small, narrow dataset, behavior degrades on inputs unlike the fine-tuning set, even though fine-tuning loss looked healthy throughout.
**Cause:** A narrow fine-tuning set pushes the router toward whichever experts happen to specialize on — or simply receive gradient — from that data, unwinding a balance pretraining established over a much larger and more diverse token stream. The router is a tiny linear layer; a handful of gradient steps can move its decisions disproportionately relative to its parameter count.
**Fix:** Common tribal practice: freeze router weights entirely during fine-tuning, or give the router a learning rate roughly an order of magnitude below the expert FFN weights' LR, so routing can't move faster than the experts it's routing to (see the fine-tuning-time treatment in domain 12).
**Detection:** Compare the per-expert load histogram on a fixed, diverse eval set before and after fine-tuning; a large shift is the router re-collapsing, not the experts genuinely improving.

## 5. Post-training quantization silently flips routing decisions

**Symptom:** A GPTQ- or AWQ-quantized MoE model scores worse than the bit-width alone would predict for a dense model of the same precision.
**Cause:** Top-k is a hard, discrete decision boundary. A small perturbation to router logits from [[Concept - Post-Training Quantization Formats|post-training quantization]] error can flip which experts get selected for a token — a qualitatively different failure mode than the smooth degradation quantization causes inside a dense matmul, where a small weight error just nudges the output slightly. Expert weights, each seeing a narrower and more specialized token distribution than a dense FFN's single weight set, also tend to have a smaller effective dynamic range and are correspondingly more sensitive at the same bit-width.
**Fix:** Keep the router in fp16/bf16 even when experts drop to INT4/INT8 — it's a $d_{\text{model}} \times N_{\text{experts}}$ matrix, essentially free to leave unquantized. Calibrate each expert's quantization on its own routed-token distribution rather than a single global calibration set.
**Detection:** Compare per-token top-k selections between the fp16 and quantized model on a fixed calibration batch; a disagreement rate of even a few percent explains quality loss a smooth-error model wouldn't predict.

## 6. Missing gate renormalization or low-precision gate math

**Symptom:** Output magnitude drifts subtly wrong, or a reimplementation ported from a reference produces plausible-looking but numerically different logits.
**Cause:** Two easy-to-miss steps: computing the router softmax in bf16/fp16 (the same saturation risk as attention softmax under low precision), and forgetting to renormalize the selected top-$k$ gate weights to sum to 1. Without renormalization, the combined output scale depends on how much probability mass fell *outside* the top-$k$ set — which varies token to token — so the effective magnitude of the MoE sublayer's contribution to the residual stream drifts unpredictably.
**Fix:** Compute the gate softmax in fp32; renormalize the selected weights (`gate_i / sum(gate_selected)`) before combining expert outputs. See [[Snippet - Top-2 MoE Routing Layer]] for the line that does this.
**Detection:** Sum the applied gate weights per token after top-$k$ selection — if they don't sum to exactly 1.0, renormalization is missing or being computed in a precision that's losing bits.

## 7. Shared-expert bookkeeping errors in fine-grained MoE

**Symptom:** Reported active-parameters-per-token or FLOP estimates for a DeepSeek-style model don't match the published number, or a reimplementation's parameter count is off by a small but confusing amount.
**Cause:** Fine-grained designs ([[Breakdown - DeepSeek-V3 Architecture|DeepSeekMoE]]) add one or more always-on shared experts alongside the top-$k$ routed pool. It's easy to forget the shared expert's compute when reporting active-parameter math (undercounting), or to double-count it if it's implemented as "expert 0, always selected" inside the same top-$k$ loop as the routed experts rather than as a structurally separate path.
**Fix:** Implement the shared expert as an unconditional, separate module call — never a member of the routed pool — and add its parameters and FLOPs explicitly when reporting active-parameter counts.
**Detection:** Recompute active params/FLOPs by hand from the config (routed: $k \times$ expert size, plus shared: $n_{\text{shared}} \times$ expert size) and diff against whatever the code reports.

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
