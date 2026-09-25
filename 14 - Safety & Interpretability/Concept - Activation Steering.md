---
tags: [concept, domain/safety-interp, level/frontier]
aliases: [representation engineering, RepE, CAA, contrastive activation addition, ITI]
summary: "Adding a direction vector to the residual stream at inference time to steer behavior toward or away from a concept, no weight updates."
---
> **One-paragraph hook:** Fine-tuning changes what a model knows how to do by updating weights over many steps through a training pipeline. Activation steering changes what a model *does right now* by adding one vector to the residual stream during a forward pass. No gradients, no optimizer state, and you undo it by not adding the vector. It's the diff-in-means trick behind the [[Concept - Refusal Mechanics|refusal direction]], generalized into a control primitive for arbitrary concepts, and it cuts both ways: the knob that suppresses an unwanted trait installs one just as easily with the sign flipped.

## The mechanism

At a chosen layer $\ell$, add a vector $v$ scaled by a coefficient $\alpha$ to the residual stream during the forward pass:

$$h'_\ell(x) = h_\ell(x) + \alpha v$$

It's applied at every position of a generated sequence, or a chosen subset. The residual stream is the shared linear channel every downstream component reads from, so this one addition propagates through the rest of the network. The same linearity is why [[Concept - Activation Patching]] and the [[Concept - The Logit Lens|logit lens]] work.

**Contrastive Activation Addition** (Rimsky et al. 2023) extracts $v$ with the refusal-direction recipe. Run the model on matched contrastive pairs (sycophantic vs. non-sycophantic completions of the same prompt, say), cache the residual-stream activation at layer $\ell$, and take the difference of means. No gradient descent, just a handful of forward passes and an average.

**Inference-Time Intervention** (Li et al. 2023, "ITI") is more surgical. Instead of one whole-stream vector, it linearly probes *each attention head* for a target direction (originally truthfulness), picks the top-K heads whose activations best predict the concept, and shifts only those heads along their local direction at generation time. The paper reports a substantial TruthfulQA accuracy gain from intervening on a small fraction of heads, so steering doesn't have to touch the whole model to move a targeted behavior.

**Representation Engineering** (Zou et al. 2023, "RepE") makes this a general top-down program. Read high-level concepts (honesty, power-seeking, fairness, refusal) as linear directions via mean-difference, linear probing or PCA over contrastive activations, then add or subtract them at inference to control the behavior. "Find and move a direction" becomes a reusable primitive instead of a one-off trick per concept.

**SAE-feature clamping** replaces the diff-in-means direction with one interpretable feature found by a [[Concept - Sparse Autoencoders|sparse autoencoder]] and forces its activation to an artificially high (or zero) value. That's how [[Breakdown - Golden Gate Claude]] worked: Anthropic clamped one SAE feature so high that Claude mentioned the Golden Gate Bridge in almost every reply, a public, vivid demonstration that one named feature can visibly dominate a production model's output.

```
                     residual stream at layer ℓ
                              │
   CAA:  h_ℓ + α·(mean_pos − mean_neg)  ─┐
   ITI:  shift top-K heads' outputs      ├──►  downstream layers compute
         along local truth direction     │      on the perturbed stream,
   SAE:  clamp one feature's activation ─┘      behavior shifts accordingly
```

## In practice

Three knobs matter. **Layer**: usually a middle layer, mirroring where the refusal direction extracts most cleanly. **Coefficient** $\alpha$: the sign sets add-toward vs. subtract-away, the magnitude sets strength. **Target**: the whole residual stream, a subset of heads, or one SAE feature. Push $\alpha$ too far and generation degrades into incoherent or looping text, which shows steering is dragging the activation off the manifold the rest of the network was trained on. It isn't "just" turning a concept dial.

Steering is cheap next to fine-tuning. A CAA-style vector takes a handful of forward passes on contrastive pairs, with no optimizer, no training pipeline and no risk of the catastrophic forgetting that can come with SFT or DPO passes. At inference it costs one vector addition per targeted layer, negligible beside a forward pass. That cheapness puts it on both sides of the safety fence. The technique that suppresses [[Concept - Sycophancy|sycophancy]] in production or strengthens refusal is, with the sign flipped, the one that produces "abliterated" open-weight forks ([[Snippet - Ablating the Refusal Direction]]) or induces broad [[Concept - Emergent Misalignment|emergent misalignment]] within hours of a model's release.

## Failure modes

- **Symptom:** text turns incoherent, repetitive or loops once a steering vector is applied. **Cause:** too large an $\alpha$ pushes the activation outside the region the rest of the network was trained on, which breaks downstream computation instead of adjusting one concept. **Detection/fix:** sweep $\alpha$ against a held-out coherence eval (perplexity or side-by-side judge scoring) before picking a production coefficient, and make coherence a release gate.
- **Symptom:** a vector that works reliably on its extraction prompts fails on new prompt templates. **Cause:** diff-in-means over a small contrastive set is a linear approximation of a concept that may be nonlinear or entangled, and the extraction sample doesn't cover the deployment distribution. **Detection:** validate on an eval set disjoint from the extraction pairs, across several prompt templates, before trusting the vector.
- **Symptom:** a vector meant to reduce one behavior measurably hurts an unrelated capability. **Cause:** directions for distinct concepts aren't perfectly orthogonal in a residual stream that packs many features via [[Concept - Superposition|superposition]], so steering along one axis projects onto others. **Detection:** run the full production eval suite after any steering deployment, not only the targeted metric. A clean win on one benchmark can hide a regression elsewhere.
- **Symptom:** an "uncensored" or fully compliant fork of a new open-weight model appears within days. **Cause:** the extraction-and-add mechanism used defensively works offensively with the sign flipped. Anyone with weight access can extract the refusal direction and subtract it. **Detection:** expect this for every open release (see [[Concept - Refusal Mechanics]]); it isn't a surprise incident.

## The non-obvious

Steering is control, not alignment, and the mechanism can't tell them apart. Adding and subtracting the same vector are symmetric operations, so the *sign* decides whether an intervention makes a model safer or does what an attacker wants. Think of steering as a runtime dial on top of whatever training installed. It changes the readout of a forward pass, not necessarily the computation or disposition the model was trained toward. So the literature has it both as a proposed mitigation and as a demonstrated attack on the same code path: a technique that suppresses [[Concept - Emergent Misalignment|emergent misalignment]] in one experiment can, by construction, induce it in the next.

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
