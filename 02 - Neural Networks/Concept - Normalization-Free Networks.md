---
tags: [concept, domain/neural-networks, level/frontier]
aliases: [NF-Nets, NFNet, normalizer-free networks, AGC, ReZero, Fixup, SkipInit, DeepNorm]
summary: "Training deep nets without BatchNorm/LayerNorm via scaled residuals, adaptive gradient clipping, and near-zero residual init."
---
# Concept - Normalization-Free Networks

> **One-paragraph hook:** Normalization layers are load-bearing scaffolding — they let deep nets train at high learning rates, but they also drag along a train/eval statistics discrepancy, cross-example information leakage, and per-step compute. Normalization-free networks ask: can we keep the stability and throw away the scaffolding? The answer, for ImageNet CNNs, is yes — NF-Nets matched or beat BatchNorm ResNets at higher training throughput. The answer, for frontier transformers, is still no: [[Concept - RMSNorm and LayerNorm|RMSNorm]] remains the default, and "no norm" has not been shown to scale.

## The mechanism

A normalization layer does two real jobs during training, and any norm-free scheme has to reproduce both by other means:

1. **Control residual-stream variance growth with depth.** Because [[Concept - Residual Connections|residual blocks]] *add* their output to a running stream, the stream's variance grows roughly linearly with the number of blocks unless something rescales it. Norm resets the scale at every block for free.
2. **Keep gradients well-conditioned.** Norm smooths the loss landscape and makes the network forgiving of learning-rate and [[Concept - Weight Initialization|initialization]] choices — the same landscape-smoothing (not the "internal covariate shift" the original paper claimed) that [[Breakdown - Batch Normalization|BatchNorm's post-mortem]] pins its benefit on.

Norm-free methods substitute **precise initialization plus gradient control** for runtime normalization. There are three families:

**Near-zero residual init (Fixup, SkipInit, ReZero).** Initialize each residual branch so the block starts as the identity. ReZero (Bachlechner et al. 2020) is the cleanest form: $x_{l+1} = x_l + \alpha_l\, f(x_l)$ with a *learnable scalar* $\alpha_l$ initialized to $0$. At step 0 the whole network is exactly identity — signal and gradients pass through untouched — and the $\alpha_l$ grow only as far as training needs, so arbitrarily deep stacks train without norm. Fixup (Zhang et al. 2019) reaches the same place more surgically: rescale each residual branch's weights by a factor decaying in the block count $L$ (e.g. $L^{-1/(2m-2)}$ for an $m$-layer branch), zero-initialize the last layer of each branch, and add learnable scalar multipliers and biases.

**Analytic signal-propagation scaling + adaptive gradient clipping (NF-Nets).** Brock et al. (2021) design the forward pass so activation variance is *predictable* at every layer using Signal Propagation Plots, with scaled residual blocks $x_{l+1} = x_l + \alpha\, f_l(x_l / \beta_l)$ where $\beta_l$ is set analytically to the incoming standard deviation and $\alpha$ is small. That alone matches small-batch BatchNorm; to reach *large*-batch training they add **Adaptive Gradient Clipping (AGC)**. AGC clips each layer's gradient by its ratio to the weight norm, unit-wise:

$$\text{if } \frac{\|G_i\|_F}{\|W_i\|_F} > \lambda \;\Rightarrow\; G_i \leftarrow \lambda\,\|W_i\|_F\,\frac{G_i}{\|G_i\|_F},$$

with $\lambda \approx 0.01$–$0.16$. This bounds the *relative* update per unit, recovering the large-batch training stability that BatchNorm gave for free — the piece [[Concept - Vanishing and Exploding Gradients|plain gradient clipping]] does not provide because it clips by a global norm rather than per-layer relative scale.

## In practice

NF-Nets were a genuine result, not a curiosity: **NFNet-F1 matched EfficientNet-B7's ImageNet accuracy while training substantially faster**, and the larger NFNet-F5 reached ~86% top-1, a SOTA-class number in 2021, all with no normalization layer anywhere. The win was throughput and the removal of BatchNorm's pathologies (batch-size dependence, the train/eval running-stat gap, cross-example leakage), not raw accuracy.

For **transformers**, the story bifurcates:

- Fully norm-free transformers are hard, because norm *placement* is itself load-bearing for stability — the pre-norm/post-norm/DeepNorm choice covered in [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] governs whether a deep transformer trains at all. Most just keep RMSNorm.
- The successful "scale the residual, don't remove the norm" line is **DeepNorm / DeepNet** (Wang et al. 2022), which scales the residual branch by a depth-dependent constant (and adjusts init to match) to keep the residual stream stable, enabling **1000-layer transformers**. This is a norm-*taming* idea, not a norm-*free* one — it targets exactly the residual-variance job above while retaining LayerNorm, and it is the piece that actually shipped at depth into large-scale [[Concept - Training Stability and Loss Spikes|training-stability]] engineering.
- The partial victory that *did* stick is RMSNorm: dropping mean-subtraction was one step toward "less normalization" that survived. Dropping norm entirely did not.

The pragmatic decision — norm vs no-norm, and which norm — lives in [[Decision - Choosing a Normalization Layer]].

## Failure modes

- **Brittleness to LR and init.** This is the real reason norm-free never became default. Norm makes a network *forgiving*; remove it and you inherit its stabilization job manually, so the usable learning-rate and init ranges narrow sharply. A norm-free net that trains beautifully at one LR diverges at 1.5×. Detection: a much steeper LR-sensitivity sweep than the normalized baseline.
- **Depth-scaling constants must be exact.** Fixup/NF-Net scaling factors depend on the block count and branch depth; get the exponent wrong and either the residual stream explodes with depth or the branches contribute nothing and the deep net silently behaves like a shallow one. Detection: per-layer activation-variance and gradient-norm profiles that drift with depth instead of staying flat.
- **AGC's $\lambda$ is a real hyperparameter.** Too tight and it throttles learning; too loose and it fails to prevent the large-batch instability it exists for. Unlike norm, it does not self-tune.

## The non-obvious

The thing practitioners get wrong is assuming normalization's job is the *forward-pass scale* — that if you just fix activation magnitudes at init, you can drop norm. Init handles the forward pass fine. What you actually lose is the **implicit gradient conditioning and hyperparameter robustness**, and that is worth more than its compute cost at frontier scale. This is why the field's revealed preference is telling: given a decade and enormous incentive to shave the norm op out of the hottest loop in every LLM, the frontier still ships RMSNorm. Norm-free is a proven idea in vision and an unproven bet in language, and the reason is not that nobody tried — it is that norm's stabilization keeps paying for itself exactly at the scales where a mistake costs a seven-figure run, a lesson enumerated in the [[Gotchas - Training Neural Networks|training-bug catalog]].

Open (as of 2026): whether a genuinely norm-free architecture can match RMSNorm transformers at frontier scale is unresolved; the honest default remains RMSNorm.

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
