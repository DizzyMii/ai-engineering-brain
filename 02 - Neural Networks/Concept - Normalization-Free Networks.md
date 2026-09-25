---
tags: [concept, domain/neural-networks, level/frontier]
aliases: [NF-Nets, NFNet, normalizer-free networks, AGC, ReZero, Fixup, SkipInit, DeepNorm]
summary: "Training deep nets without BatchNorm/LayerNorm via scaled residuals, adaptive gradient clipping, and near-zero residual init."
---
# Concept - Normalization-Free Networks

> **One-paragraph hook:** Normalization layers let deep nets train at high learning rates. They also bring a train/eval statistics discrepancy, cross-example information leakage, and per-step compute. Normalization-free networks try to keep the stability and drop the layer. For ImageNet CNNs that worked: NF-Nets matched or beat BatchNorm ResNets at higher training throughput. For frontier transformers it hasn't. [[Concept - RMSNorm and LayerNorm|RMSNorm]] is still the default, and "no norm" has not been shown to scale.

## The mechanism

A normalization layer does two real jobs during training, and a norm-free scheme has to reproduce both some other way:

1. **Control residual-stream variance growth with depth.** [[Concept - Residual Connections|Residual blocks]] *add* their output to a running stream, so the stream's variance grows roughly linearly with the number of blocks unless something rescales it. Norm resets the scale at every block for free.
2. **Keep gradients well-conditioned.** Norm smooths the loss surface and makes the network forgiving of learning-rate and [[Concept - Weight Initialization|initialization]] choices. [[Breakdown - Batch Normalization|BatchNorm's post-mortem]] pins its benefit on this same smoothing, not on the "internal covariate shift" the original paper claimed.

Norm-free methods replace runtime normalization with careful initialization plus gradient control. There are three families.

**Near-zero residual init (Fixup, SkipInit, ReZero).** Initialize each residual branch so the block starts as the identity. ReZero (Bachlechner et al. 2020) is the simplest version: $x_{l+1} = x_l + \alpha_l\, f(x_l)$ with a *learnable scalar* $\alpha_l$ initialized to $0$. At step 0 the whole network is the identity, so signal and gradients pass through untouched. The $\alpha_l$ grow only as far as training needs, and arbitrarily deep stacks train without norm. Fixup (Zhang et al. 2019) gets to the same place more surgically. It rescales each residual branch's weights by a factor decaying in the block count $L$ (e.g. $L^{-1/(2m-2)}$ for an $m$-layer branch), zero-initializes the last layer of each branch, and adds learnable scalar multipliers and biases.

**Analytic signal-propagation scaling + adaptive gradient clipping (NF-Nets).** Brock et al. (2021) use Signal Propagation Plots to design the forward pass so activation variance is *predictable* at every layer. The residual blocks are scaled as $x_{l+1} = x_l + \alpha\, f_l(x_l / \beta_l)$, with $\beta_l$ set analytically to the incoming standard deviation and $\alpha$ small. That alone matches small-batch BatchNorm. For *large*-batch training they add **Adaptive Gradient Clipping (AGC)**, which clips each layer's gradient unit-wise by its ratio to the weight norm:

$$\text{if } \frac{\|G_i\|_F}{\|W_i\|_F} > \lambda \;\Rightarrow\; G_i \leftarrow \lambda\,\|W_i\|_F\,\frac{G_i}{\|G_i\|_F},$$

with $\lambda \approx 0.01$–$0.16$. This bounds the *relative* update per unit and recovers the large-batch stability BatchNorm gave for free. [[Concept - Vanishing and Exploding Gradients|Plain gradient clipping]] can't do this because it clips by a global norm, with no per-layer relative scale.

## In practice

NF-Nets were a real result. **NFNet-F1 matched EfficientNet-B7's ImageNet accuracy while training substantially faster**, and the larger NFNet-F5 reached ~86% top-1, a SOTA-class number in 2021, with no normalization layer anywhere. The win was throughput and getting rid of BatchNorm's pathologies (batch-size dependence, the train/eval running-stat gap, cross-example leakage). Raw accuracy wasn't the point.

Transformers split into three stories:

- Fully norm-free transformers are hard because norm *placement* itself decides stability. The pre-norm/post-norm/DeepNorm choice in [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] determines whether a deep transformer trains at all. Most just keep RMSNorm.
- The line that worked scales the residual and keeps the norm: **DeepNorm / DeepNet** (Wang et al. 2022). It scales the residual branch by a depth-dependent constant (with matching init) to keep the residual stream stable, which made **1000-layer transformers** trainable. That's norm-*taming*, not norm-*free*. It handles the residual-variance job above while keeping LayerNorm, and it's what actually shipped at depth into large-scale [[Concept - Training Stability and Loss Spikes|training-stability]] engineering.
- RMSNorm is the partial win that stuck. Dropping mean-subtraction was a step toward "less normalization" that survived; dropping norm entirely didn't.

The practical call (norm vs no-norm, and which norm) is in [[Decision - Choosing a Normalization Layer]].

## Failure modes

- **Brittleness to LR and init.** The main reason norm-free never became the default. Norm makes a network *forgiving*. Remove it and you take over its stabilization job by hand, and the usable learning-rate and init ranges narrow sharply. A norm-free net that trains beautifully at one LR diverges at 1.5×. Detection: an LR-sensitivity sweep much steeper than the normalized baseline's.
- **Depth-scaling constants must be right.** Fixup/NF-Net scaling factors depend on block count and branch depth. Get the exponent wrong and either the residual stream explodes with depth, or the branches contribute nothing and the deep net silently acts like a shallow one. Detection: per-layer activation-variance and gradient-norm profiles that drift with depth instead of staying flat.
- **AGC's $\lambda$ is a real hyperparameter.** Too tight throttles learning. Too loose fails to stop the large-batch instability it's there for. It doesn't self-tune the way norm does.

## The non-obvious

People assume normalization's job is the *forward-pass scale*, so fixing activation magnitudes at init should let you drop it. Init handles the forward pass fine. What you lose is the **implicit gradient conditioning and hyperparameter robustness**, and at frontier scale that's worth more than the compute. The field's revealed preference says a lot: after a decade of strong incentive to cut the norm op out of the hottest loop in every LLM, the frontier still ships RMSNorm. Norm-free is proven in vision and an unproven bet in language. Plenty of people tried. Norm's stabilization keeps paying for itself at the scales where a mistake costs a seven-figure run, as the [[Gotchas - Training Neural Networks|training-bug catalog]] shows.

Open (as of 2026): whether a norm-free architecture can match RMSNorm transformers at frontier scale is unresolved. The honest default is still RMSNorm.

## Connections

- [[Concept - RMSNorm and LayerNorm]] — the incumbent that norm-free methods try to replace; RMSNorm is itself the one step toward "less norm" that stuck.
- [[Breakdown - Batch Normalization]] — the norm whose specific pathologies (train/eval gap, batch dependence, leakage) motivate going norm-free in the first place.
- [[Concept - Residual Connections]] — the additive residual stream is why depth causes variance growth, the core problem norm-free init schemes must solve.
- [[Concept - Weight Initialization]] — norm-free methods push the stabilization burden back onto precise init (Fixup's depth-scaled weights, ReZero's zero-init scalars).
- [[Concept - Vanishing and Exploding Gradients]] — AGC and scaled residuals are gradient-control tools targeting the same failure norm otherwise prevents.
- [[Decision - Choosing a Normalization Layer]] — where "drop norm entirely" sits as an option against BatchNorm/LayerNorm/RMSNorm/GroupNorm.
- [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] — DeepNorm's residual scaling is the norm-*taming* cousin that actually scaled to 1000-layer transformers (cross-domain: architectures).
- [[Concept - Training Stability and Loss Spikes]] — residual-scaling and gradient-clipping tricks are part of the large-scale training-stability toolkit (cross-domain: training at scale).
- [[Concept - Vision Transformers]] — SAM-trained ViTs and NF-Nets are the two vision lines where careful init/regularization substitutes for scaffolding (cross-domain: multimodal).
- [[Gotchas - Training Neural Networks]] — the brittleness and depth-constant errors of norm-free training are concrete, hard-won debugging pitfalls.

## Sources

- Brock, De, Smith, Simonyan (2021) — "High-Performance Large-Scale Image Recognition Without Normalization" (NF-Nets). Scaled residual blocks + Adaptive Gradient Clipping; NFNet accuracy/throughput results.
- Zhang, Dauphin, Ma (2019) — "Fixup Initialization: Residual Learning Without Normalization." Depth-scaled residual init that trains 100+ layer ResNets with no norm.
- Bachlechner et al. (2020) — "ReZero is All You Need: Fast Convergence at Large Depth." Learnable zero-initialized residual scalars.
- Wang, Ma, Dong, Huang, Zhang, Wei (2022) — "DeepNet: Scaling Transformers to 1,000 Layers." DeepNorm residual scaling — norm-taming, not norm-removal.
