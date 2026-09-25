---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [SAE, SAEs, sparse dictionary learning, dictionary learning for LLMs]
summary: "Overcomplete autoencoders that decompose superposed activations into a wide, sparse basis of mostly-monosemantic features."
---
> **One-paragraph hook:** [[Concept - Why Neural Networks Are Hard to Interpret|You can't read a transformer's activations directly]], because the model packs in more concepts than it has dimensions and accepts the interference, which is what [[Concept - Superposition|Superposition]] formalizes. A sparse autoencoder (SAE) is the practical response. Project the activation into a much wider space where a sparsity constraint allows only a handful of dimensions to be active per token, then reconstruct the original vector from that sparse code. With a wide enough projection and strong enough sparsity pressure, individual dimensions of the wide space ("features" or "latents") start responding to single, nameable concepts instead of many unrelated ones. SAEs are currently the field's main tool for turning an uninterpretable activation vector into something a human, or another model, can read.

## The mechanism

An SAE is a single-hidden-layer autoencoder trained on activations $x \in \mathbb{R}^d$ taken from one point in the network, almost always the [[Concept - The Residual Stream|residual stream]] at a chosen layer. The encoder maps up to a dictionary of size $m$, 8x to 256x wider than $d$:

$$f(x) = \text{ReLU}\big(W_{enc}(x - b_{dec}) + b_{enc}\big) \in \mathbb{R}^{m}$$

The decoder reconstructs the vector as a linear combination of dictionary directions (columns of $W_{dec}$):

$$\hat x = W_{dec}\, f(x) + b_{dec}$$

Training minimizes reconstruction error plus a sparsity penalty on the code:

$$\mathcal{L} = \|x - \hat x\|_2^2 + \lambda \|f(x)\|_1$$

The shape is a down-projection and an up-projection around a nonlinearity, like a [[Deep Dive - LoRA|LoRA]] adapter. The difference is that LoRA is *low*-rank for parameter efficiency, while an SAE is deliberately *wide* (overcomplete) for interpretability: the point is more dictionary directions than input dimensions. The $L1$ penalty on $f(x)$ forces sparsity, so only a few of the $m$ latents fire per token. Sparsity is what gets around superposition's interference. If two features rarely co-activate, giving each its own dictionary direction costs almost nothing in reconstruction error, even with $m \gg d$.

There's a zoo of variants because vanilla ReLU+L1 has known problems. **Gated SAEs** (DeepMind) separate "is this feature on" (a binary gate) from "how strongly" (a magnitude). The reason is shrinkage bias: L1 systematically shrinks the magnitude of features it doesn't kill outright, which corrupts reconstruction even for correctly detected features. **TopK SAEs** (OpenAI, Gao et al. 2024) drop the penalty. They keep only the $k$ largest activations per token and zero the rest, so sparsity is set directly ($L0=k$ by construction) instead of penalized indirectly with the shrinkage/sparsity fight that brings. **JumpReLU** (DeepMind) learns a per-feature threshold so a feature fires at its true magnitude once past it, approximating an $L0$ objective with a differentiable surrogate. **Matryoshka SAEs** nest several widths in one training run so a narrow prefix of the dictionary is itself a coherent smaller SAE, a partial fix for feature splitting (below).

## In practice

The work that established SAEs as scalable is [[Deep Dive - Mechanistic Interpretability|Anthropic's]] two-paper arc. "Towards Monosemanticity" (2023) trained SAEs on a one-layer transformer and showed the latents were far more monosemantic than raw neurons: proof of concept on a small model. "Scaling Monosemanticity" (2024) ran the method on Claude 3 Sonnet, a production frontier model, with dictionaries up to roughly 34 million features on the mid-layer residual stream. That was the first evidence dictionary learning holds up on a deployed model and not only a toy. OpenAI's TopK work (2024) went further, scaling to tens of millions of latents on GPT-4-class activations and showing TopK's reconstruction/sparsity Pareto frontier beats vanilla L1 at matched sparsity.

An SAE gets judged on several numbers. **L0** is the average count of active latents per token, i.e. the sparsity actually achieved, usually tuned to the tens. **Reconstruction loss**, or fraction of variance explained, is how much of the original activation the sparse code recovers. **Dead-latent count** is the number of dictionary directions that never fire on the training distribution and are pure waste. And there's **human- or LLM-judged interpretability** of each latent's top-activating examples. These pull against each other. Push $L0$ down for sparser, more interpretable-looking latents and reconstruction loss rises; widen the dictionary to cut reconstruction loss and dead latents pile up. Training an SAE is a Pareto-frontier search, not one objective to minimize.

Tooling has settled on SAELens for training and Neuronpedia for hosting per-feature activation dashboards, so most practitioners load a released dictionary and browse or query it instead of training their own. Once you have interpretable directions, [[Concept - Activation Steering|clamping one to a fixed value at inference]] is the standard way to test (and exploit) what it does causally. It's the technique behind [[Breakdown - Golden Gate Claude|Golden Gate Claude]].

## Failure modes

- **Dead latents.** A meaningful fraction of directions never activate on held-out data after training, which wastes capacity and makes the effective dictionary smaller than its nominal width. Detection: track per-latent firing frequency over a large eval set. Standard fixes are periodically resampling dead latents toward under-served activation directions, or "ghost gradients" that give them a training signal while inactive.
- **Feature splitting.** One concept fractures into several narrower, correlated latents as width grows (a single "profanity" feature at width 4k becomes three language-specific profanity features at width 16k, say). Detection: look for near-duplicate top-activating examples and correlated co-activation across latents. Matryoshka training is a partial fix.
- **Feature absorption.** A general feature swallows a more specific one. A broad "starts with a vowel" latent can take over what should be a "starts with A" latent where they overlap, leaving the specific feature firing only on leftover cases and making both harder to interpret alone.
- **Mistaking reconstruction fidelity for understanding.** An SAE can reach low reconstruction loss while its latents aren't the units the model's own computation uses. High fraction-of-variance-explained is necessary but not sufficient evidence of real features, and even wide, well-trained dictionaries leave a large share of activation variance ("dark matter") unexplained. [[Gotchas - Interpreting Model Internals]] covers how this plays out across the wider toolkit.

## The non-obvious

The 2024-2025 shift in how people talk about SAEs gives it away. Early papers asked "did we find monosemantic features?" By 2025 the sharper question was "did we find the features the model *computes with*, or a plausible alternative basis that reconstructs well for reasons unrelated to the model's algorithm?" Reconstruction is a proxy. An SAE optimizes purely for compressing and decompressing $x$, and nothing in that objective guarantees its directions are the intermediate variables the network's computation actually depends on, as opposed to convenient statistical regularities in the activation distribution. That's why [[Concept - Attribution Graphs|attribution graphs]] moved from SAEs, which reconstruct *representations*, to transcoders, which approximate *computation* from input features to output features. If you need the computational units, reconstructing the static activation vector was never quite the right objective. It was the tractable one.

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
