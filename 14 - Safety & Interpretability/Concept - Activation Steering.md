---
tags: [concept, domain/safety-interp, level/frontier]
aliases: [representation engineering, RepE, CAA, contrastive activation addition, ITI]
summary: "Adding a direction vector to the residual stream at inference time to steer behavior toward or away from a concept, no weight updates."
---
> **One-paragraph hook:** Fine-tuning changes what a model knows how to do by updating weights over many steps and a training pipeline. Activation steering changes what a model *does right now* by adding one vector to the residual stream during a forward pass — no gradients, no optimizer state, reversible by simply not adding it. It is the same diff-in-means trick that produces the [[Concept - Refusal Mechanics|refusal direction]], generalized into a control primitive for arbitrary concepts, and it is exactly as double-edged as that sounds: the same knob that suppresses an unwanted trait installs one just as easily with the sign flipped.

## The mechanism

At a chosen layer $\ell$, add a vector $v$ (scaled by coefficient $\alpha$) to the residual stream during the forward pass:

$$h'_\ell(x) = h_\ell(x) + \alpha v$$

applied at every position, or a chosen subset, of a generated sequence. Because the residual stream is the shared linear channel every downstream component reads from, this single addition propagates through the rest of the network's computation — the same linearity that makes [[Concept - Activation Patching]] and the [[Concept - The Logit Lens|logit lens]] work at all.

**Contrastive Activation Addition** (Rimsky et al. 2023) extracts $v$ by the same recipe used to find the refusal direction: run the model on matched contrastive pairs (e.g., sycophantic vs. non-sycophantic completions of the same prompt), cache the residual-stream activation at layer $\ell$, and take the difference of means. No gradient descent required — a handful of forward passes and an average.

**Inference-Time Intervention** (Li et al. 2023, "ITI") is more surgical: rather than one whole-residual-stream vector, linearly probe *each attention head individually* for a target direction (originally truthfulness), identify the top-K heads whose activations most predict the concept, and shift only those heads along their local direction at generation time. The original paper reports a substantial TruthfulQA accuracy gain from intervening on a small fraction of heads — evidence that steering doesn't need to touch the whole model to move a targeted behavior.

**Representation Engineering** (Zou et al. 2023, "RepE") frames this as a general top-down program: read high-level concepts — honesty, power-seeking, fairness, refusal — as linear directions (via mean-difference, linear probing, or PCA over contrastive activations), then add or subtract them at inference to control the corresponding behavior, treating "find and move a direction" as a reusable primitive rather than a one-off trick per concept.

**SAE-feature clamping** swaps the diff-in-means direction for a single interpretable feature discovered by a [[Concept - Sparse Autoencoders|sparse autoencoder]] and forces its activation to an artificially high (or zero) value. This is the mechanism behind [[Breakdown - Golden Gate Claude]]: Anthropic clamped one SAE feature so high that Claude referenced the Golden Gate Bridge in almost every reply — a public, vivid demonstration that a single named feature can visibly dominate a production model's output.

```
                     residual stream at layer ℓ
                              │
   CAA:  h_ℓ + α·(mean_pos − mean_neg)  ─┐
   ITI:  shift top-K heads' outputs      ├──►  downstream layers compute
         along local truth direction     │      on the perturbed stream,
   SAE:  clamp one feature's activation ─┘      behavior shifts accordingly
```

## In practice

The knobs that matter: **layer** (usually a middle layer, mirroring where the refusal direction is most cleanly extracted), **coefficient** $\alpha$ (sign determines add-toward vs. subtract-away; magnitude determines strength), and which components receive the intervention (whole residual stream vs. a subset of heads vs. one SAE feature). Push $\alpha$ too far and generation degrades into incoherent or looping text — direct evidence that steering is dragging the activation off the manifold the rest of the network was trained to process, not "just" turning a concept dial.

Cost-wise, steering is cheap relative to fine-tuning: extracting a CAA-style vector needs only a handful of forward passes on contrastive pairs, no optimizer, no training pipeline, and no risk of the catastrophic forgetting that can accompany SFT or DPO passes; applying it at inference costs one vector addition per targeted layer, negligible next to a forward pass. That cheapness is exactly why it shows up on both sides of the safety fence — the same technique that suppresses [[Concept - Sycophancy|sycophancy]] in production, or strengthens refusal, is the technique that, run with the sign flipped, produces "abliterated" open-weight forks ([[Snippet - Ablating the Refusal Direction]]) or induces broad [[Concept - Emergent Misalignment|emergent misalignment]] within hours of a model's release.

## Failure modes

- **Symptom:** generated text becomes incoherent, repetitive, or loops after a steering vector is applied. **Cause:** too-large $\alpha$ pushes the activation outside the region of activation space the rest of the network was trained on, breaking downstream computation rather than cleanly adjusting one concept. **Detection/fix:** sweep $\alpha$ against a held-out coherence eval (perplexity or side-by-side judge scoring) before selecting a production coefficient; treat coherence as a release gate, not an afterthought.
- **Symptom:** a steering vector that reliably works on the prompts used to extract it fails to generalize to new prompt templates. **Cause:** diff-in-means over a small contrastive set is a linear approximation of what may be a nonlinear or entangled concept; the extraction sample doesn't cover the deployment distribution. **Detection:** validate on an eval set disjoint from the extraction pairs, spanning multiple prompt templates, before trusting the vector.
- **Symptom:** a vector meant to reduce one behavior measurably degrades an unrelated capability. **Cause:** directions for distinct concepts are not perfectly orthogonal in a residual stream packing many features via [[Concept - Superposition|superposition]] — steering along one axis has nonzero projection onto others. **Detection:** run the full production eval suite, not just the targeted metric, after any steering deployment; a clean win on one benchmark can hide a regression elsewhere.
- **Symptom:** an "uncensored" or fully compliant fork of a newly released open-weight model appears within days. **Cause:** the identical extraction-and-add mechanism used defensively works offensively with the sign flipped — anyone with weight access can extract the refusal direction and subtract it. **Detection:** treat this as a standing expectation for open releases (see [[Concept - Refusal Mechanics]]), not a surprise incident.

## The non-obvious

Steering is control, not alignment, and the mechanism itself cannot tell the difference: because adding and subtracting the same vector are symmetric operations, the *sign*, not the vector's existence, encodes whether an intervention makes a model safer or does exactly what an attacker wants. That means activation steering is best understood as a runtime dial layered on top of whatever training installed — it changes the readout of a forward pass, not necessarily the underlying computation or disposition the model was trained toward. This is precisely why steering shows up in the literature both as a proposed mitigation and as a demonstrated attack vector using the same code path: a technique that can suppress [[Concept - Emergent Misalignment|emergent misalignment]] in one experiment is, by construction, capable of inducing it in the next.

## Connections
- [[Concept - Sparse Autoencoders]] — SAE features are the highest-precision steering targets available, letting a single named feature replace a coarse diff-in-means direction.
- [[Concept - Refusal Mechanics]] — refusal ablation and reinforcement are the single most-studied special case of activation steering, using the identical diff-in-means recipe.
- [[Breakdown - Golden Gate Claude]] — the public demonstration of SAE-feature clamping steering a production frontier model via one feature.
- [[Concept - Sycophancy]] — a named production failure mode that steering along a sycophancy direction is used to suppress.
- [[Snippet - Ablating the Refusal Direction]] — the runnable code for the specific steering application of removing refusal entirely.
- [[Concept - Emergent Misalignment]] — steering's dual-use nature made concrete: the same mechanism that suppresses an unwanted trait can install a broad one.
- [[Concept - KL Divergence]] — a natural metric for quantifying how far a steered model's output distribution has drifted from the unsteered one, useful for bounding the coefficient safely.
- [[Deep Dive - RLHF End to End]] — steering is the inference-time alternative to the training-time alignment RLHF performs, with different cost, reversibility, and robustness tradeoffs.

## Sources
- Rimsky, Panickssery, Wu, Bowman, Turner, Hubinger (2023) — "Steering Llama 2 via Contrastive Activation Addition." Introduces CAA's diff-in-means extraction recipe.
- Li, Patel, Viégas, Pfister, Wattenberg (2023) — "Inference-Time Intervention: Eliciting Truthful Answers from a Language Model." Head-level probe-and-shift steering that raises TruthfulQA accuracy.
- Zou, Phan, Chen, et al. (2023) — "Representation Engineering: A Top-Down Approach to AI Transparency." General framework for reading and controlling concepts via linear directions.
