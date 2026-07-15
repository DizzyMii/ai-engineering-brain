---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [SAE, SAEs, sparse dictionary learning, dictionary learning for LLMs]
summary: "Overcomplete autoencoders that decompose superposed activations into a wide, sparse basis of mostly-monosemantic features."
---
> **One-paragraph hook:** [[Concept - Why Neural Networks Are Hard to Interpret|You cannot read a transformer's activations directly]] because the model packs more concepts than it has dimensions and accepts interference as the price — the phenomenon [[Concept - Superposition|Superposition]] formalizes. A sparse autoencoder (SAE) is the practical answer: project the activation into a much wider space where a sparsity constraint forces only a handful of dimensions active per token, then reconstruct the original vector from that sparse code. If the projection is wide enough and the sparsity pressure strong enough, individual dimensions of the wide space — "features" or "latents" — start responding to single, nameable concepts instead of many unrelated ones. SAEs are currently the field's primary lever for turning an uninterpretable activation vector into something a human (or another model) can actually read.

## The mechanism

An SAE is a single hidden-layer autoencoder trained on activations $x \in \mathbb{R}^d$ pulled from one point in the network — almost always the [[Concept - The Residual Stream|residual stream]] at a chosen layer. The encoder maps up to a dictionary of size $m$, where $m$ is 8x to 256x wider than $d$:

$$f(x) = \text{ReLU}\big(W_{enc}(x - b_{dec}) + b_{enc}\big) \in \mathbb{R}^{m}$$

and the decoder reconstructs the original vector as a linear combination of dictionary directions (columns of $W_{dec}$):

$$\hat x = W_{dec}\, f(x) + b_{dec}$$

Training minimizes reconstruction error plus a sparsity penalty on the code:

$$\mathcal{L} = \|x - \hat x\|_2^2 + \lambda \|f(x)\|_1$$

Structurally this is a down-projection followed by an up-projection around a nonlinearity — the same shape as a [[Deep Dive - LoRA|LoRA]] adapter, except LoRA is *low*-rank for parameter efficiency and an SAE is deliberately *wide* (overcomplete) for interpretability: the whole point is more dictionary directions than input dimensions, not fewer. The $L1$ penalty on $f(x)$ is what forces sparsity — only a small number of the $m$ latents fire per token — and it is exactly that sparsity that lets the decomposition dodge superposition's interference: if two features rarely co-activate, giving each its own dictionary direction costs almost nothing in reconstruction error even though $m \gg d$.

The variant zoo exists because vanilla ReLU+L1 has known pathologies. **Gated SAEs** (DeepMind) split "is this feature on" (a binary gate) from "how strongly" (a magnitude), because L1 systematically shrinks the magnitude of features it doesn't kill outright (shrinkage bias), corrupting reconstruction even for correctly-detected features. **TopK SAEs** (OpenAI, Gao et al. 2024) sidestep the penalty entirely: keep only the $k$ largest activations per token and zero the rest, directly controlling sparsity ($L0=k$ by construction) instead of penalizing it indirectly and fighting the shrinkage/sparsity tradeoff. **JumpReLU** (DeepMind) learns a per-feature activation threshold so a feature can fire with its true magnitude once past threshold, approximating an $L0$ objective with a differentiable surrogate. **Matryoshka SAEs** nest several widths inside one training run so that a narrow prefix of the dictionary is itself a valid, coherent smaller SAE — a partial fix for feature splitting (below).

## In practice

The lineage that established this as a scalable technique is [[Deep Dive - Mechanistic Interpretability|Anthropic's]] two-paper arc: "Towards Monosemanticity" (2023) trained SAEs on a one-layer transformer and showed the resulting latents were dramatically more monosemantic than raw neurons — proof of concept, small model. "Scaling Monosemanticity" (2024) repeated the method on Claude 3 Sonnet, a production frontier model, training dictionaries up to roughly 34 million features on the mid-layer residual stream — the first demonstration that dictionary learning survives contact with a deployed model rather than only a toy one. OpenAI's TopK work (2024) pushed dictionary size further, scaling to tens of millions of latents on GPT-4-class activations and showing TopK's reconstruction/sparsity Pareto frontier beats vanilla L1 at matched sparsity.

You evaluate an SAE on a handful of numbers, not one: **L0** (the average count of active latents per token — the actual sparsity achieved, typically tuned to the tens), **reconstruction loss** or fraction of variance explained (how much of the original activation the sparse code recovers), **dead-latent count** (dictionary directions that never fire on the training distribution and are pure waste), and **human- or LLM-judged interpretability** of the top-activating examples per latent. These trade off against each other — push $L0$ down (sparser, more interpretable-looking latents) and reconstruction loss rises; push the dictionary wider to reduce reconstruction loss and dead latents accumulate — so training an SAE is genuinely a Pareto-frontier search, not a single objective to minimize. Tooling has converged around SAELens for training and Neuronpedia for hosting per-feature activation dashboards, so most practitioners don't train from scratch — they load a released dictionary and browse or query it. Once you have interpretable directions, [[Concept - Activation Steering|clamping one to a fixed value at inference time]] is the standard way to test — and exploit — what it does causally, the technique behind [[Breakdown - Golden Gate Claude|Golden Gate Claude]].

## Failure modes

- **Dead latents.** A meaningful fraction of dictionary directions never activate on held-out data after training, wasting capacity and shrinking the effective dictionary size below its nominal width. Detection: track per-latent firing frequency over a large eval set; standard fixes are periodic resampling of dead latents to under-served activation directions or "ghost gradients" that give them a training signal even while inactive.
- **Feature splitting.** The same underlying concept fractures into several narrower, correlated latents as dictionary width increases (e.g., one "profanity" feature at width 4k becomes three language-specific profanity features at width 16k). Detection: look for near-duplicate top-activating examples across latents and correlated co-activation; Matryoshka training is a partial structural fix.
- **Feature absorption.** A general feature "absorbs" a more specific one — e.g., a broad "starts with a vowel" latent quietly swallows what should be a "starts with A" latent on the subset where they overlap, leaving the specific feature to fire only on the residual cases and making both harder to interpret in isolation.
- **Reconstruction fidelity mistaken for understanding.** An SAE can hit a low reconstruction loss while its latents are not the units the model's own computation actually uses — high fraction-of-variance-explained is necessary but not sufficient evidence that you've found real features, and a large share of activation variance ("dark matter") remains unexplained by even wide, well-trained dictionaries. See [[Gotchas - Interpreting Model Internals]] for how this plays out across the broader toolkit.

## The non-obvious

The 2024-2025 shift in how the field talks about SAEs is the tell: early papers asked "did we find monosemantic features," and by 2025 the sharper question is "did we find the features the model *computes with*, or a plausible-looking alternative basis that reconstructs well for reasons unrelated to the model's actual algorithm." Reconstruction is a proxy, not the target — an SAE optimizes purely for compressing-and-decompressing $x$, and nothing in that objective guarantees the resulting directions correspond to causally load-bearing intermediate variables in the network's computation rather than convenient statistical regularities in the activation distribution. This is exactly why [[Concept - Attribution Graphs|attribution graphs]] moved from SAEs (which reconstruct *representations*) to transcoders (which approximate *computation*, input features to output features): if you actually need the computational units, reconstructing the static activation vector was never quite the right objective to begin with — it was the tractable one.

## Connections
- [[Concept - Superposition]] — the theoretical mechanism (more features than dimensions, sparsity as enabler) that motivates dictionary learning as a solution in the first place.
- [[Concept - Why Neural Networks Are Hard to Interpret]] — the surface-level problem statement SAEs are the field's primary attempt to answer; start here if this note assumes too much.
- [[Concept - The Residual Stream]] — the specific activation site SAEs are almost always trained on (cross-domain: architectures).
- [[Deep Dive - LoRA]] — the structurally similar down-project/up-project shape used for the opposite purpose (parameter efficiency, not interpretability) — clarifies what's actually novel about the SAE design (cross-domain: fine-tuning).
- [[Concept - Activation Steering]] — the main downstream use of a trained SAE: clamp an interpretable latent to control behavior at inference time.
- [[Breakdown - Golden Gate Claude]] — the public demonstration that pushed SAE features from research artifact to a steerable production behavior.
- [[Concept - Attribution Graphs]] — the 2025 evolution that swaps SAEs for transcoders to capture computation rather than just representation.
- [[Gotchas - Interpreting Model Internals]] — the accumulated pitfalls (dead latents, splitting, absorption, dark matter) of using SAEs and the rest of the mech-interp toolkit in practice.
- [[Deep Dive - Mechanistic Interpretability]] — the full research program SAEs are the current centerpiece technique of.

## Sources
- Bricken et al. (2023, Anthropic) — "Towards Monosemanticity: Decomposing Language Models With Dictionary Learning." Establishes SAEs recover more monosemantic features than raw neurons on a one-layer transformer.
- Templeton et al. (2024, Anthropic) — "Scaling Monosemanticity: Extracting Interpretable Features from Claude 3 Sonnet." Scales SAEs to a production frontier model, ~34M features.
- Gao et al. (2024, OpenAI) — "Scaling and Evaluating Sparse Autoencoders." Introduces TopK SAEs and scales dictionary learning to tens of millions of latents on GPT-4-class activations.
