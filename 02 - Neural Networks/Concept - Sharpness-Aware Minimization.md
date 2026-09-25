---
tags: [concept, domain/neural-networks, level/frontier]
aliases: [SAM, ASAM, LookSAM]
summary: "Minimize the worst-case loss in a ρ-ball to bias training toward flat minima; costs two passes per step, real vision gains, unproven at LLM scale."
---
# Concept - Sharpness-Aware Minimization

> **One-paragraph hook:** Standard training minimizes the loss at a point. SAM minimizes it over a whole neighborhood, searching on purpose for parameter settings where *every nearby* setting is also good: flat minima. The trick is cheap: take one gradient step "uphill" to find the worst point in a small ball around you, then take your real optimization step from *there*. On vision it reliably buys a point or two of test accuracy and lets Vision Transformers train without heavy augmentation. It also doubles per-step compute, and that's why it never became a default for LLM pretraining.

## The mechanism

SAM (Foret et al. 2020) swaps the pointwise objective for a min–max over a radius-$\rho$ ball:

$$\min_\theta \; \max_{\|\epsilon\|_2 \le \rho} \; L(\theta + \epsilon).$$

The target is now the *worst loss within $\rho$ of $\theta$*. That pushes the optimizer away from sharp minima, where a small $\epsilon$ spikes the loss, and toward flat ones where the whole ball is low. The exact inner max is intractable, so SAM uses a first-order Taylor expansion. The worst-case perturbation comes out (approximately) as the ascent direction, normalized to the ball's surface:

$$\hat\epsilon(\theta) = \rho \cdot \frac{\nabla L(\theta)}{\|\nabla L(\theta)\|_2}.$$

It then takes the gradient *at the perturbed point* and applies it from the original point, dropping the second-order term:

```
g       = grad(L, theta)                     # 1st forward-backward
eps     = rho * g / (norm(g) + 1e-12)        # ascend to worst-case point
g_sam   = grad(L, theta + eps)               # 2nd forward-backward
theta   = base_optimizer.step(theta, g_sam)  # descend using the perturbed gradient
```

The base optimizer (usually SGD+momentum or [[Concept - Adam and AdamW|AdamW]]) doesn't change. SAM just hands it $g_{\text{sam}}$ in place of the raw gradient. The normalization in the ascent step makes the update act partly like a gradient-*norm* penalty, one way to see why SAM flattens where it lands. It targets the same curvature that [[Concept - The Edge of Stability|edge-of-stability]] dynamics leave the model sitting at when sharpness is tuned only indirectly, through the learning rate.

## In practice

- **$\rho$ is the one knob that matters.** It sets the neighborhood radius. $\rho \approx 0.05$ is the canonical default for CIFAR-scale vision, going up toward $0.1$–$0.2$ when data is scarce and overfitting is the enemy. Too large flattens past the useful minimum; too small collapses SAM to ordinary training.
- **ASAM** (Kwon et al. 2021) fixes a real weakness. A fixed-radius Euclidean ball isn't scale-invariant, so layers with large weight norms get under-perturbed and small-norm layers over-perturbed. ASAM scales $\rho$ to each parameter, so it transfers across layers and architectures without re-tuning.
- **Gains are real, modest, and mostly in vision.** Foret et al. reported consistent ImageNet top-1 improvements across ResNets (tenths of a percent up to ~1–2%, larger on smaller datasets). Chen et al. (2021) showed SAM lets [[Concept - Vision Transformers|ViTs]] and MLP-Mixers match or beat ResNets *without* large-scale pretraining or strong augmentation; the flat-minima bias stands in for the inductive bias those architectures otherwise lack. The benefit is biggest where a model would otherwise overfit: limited data, high capacity.
- **Cost blocks adoption.** Two forward-backward passes per step ≈ 2× compute and wall-clock. Mitigations: **LookSAM** reuses the ascent direction for several steps; applying SAM **every $k$ steps** (periodic SAM) keeps most of the gain for a fraction of the cost; efficient variants amortize or subsample the ascent pass.

SAM turns the flat-minima hypothesis into an *intervention*. Plain [[Concept - Stochastic Gradient Descent and Momentum|SGD]] finds flat minima only implicitly, through gradient noise. SAM optimizes flatness on purpose, which makes it a controlled probe of whether flatness *causes* [[Concept - Generalization in Deep Learning|generalization]] or just correlates with it, a live question in the [[Lore - The Adam vs SGD Generalization Wars|Adam-vs-SGD generalization debate]].

## Failure modes

- **Paying 2× for nothing at scale.** In [[Concept - Scaling Laws|LLM pretraining]], compute buys more tokens or parameters, and there's no clear evidence SAM's flatness gain beats spending that 2× on more data. It's still almost entirely a vision and fine-tuning tool, and in a pretraining budget it's usually a compute mistake.
- **A mis-set $\rho$ degrades without a signal.** SAM never errors, so a badly tuned $\rho$ just underperforms baseline. Only an ablation against SAM-off catches it; the loss curve won't.
- **Batch normalization and mixed precision.** Both passes need consistent statistics. A naive implementation that lets the ascent and descent passes see different [[Breakdown - Batch Normalization|BatchNorm]] batch stats computes an inconsistent $\hat\epsilon$. The practical trap is making the perturbation, the norm computation and the base optimizer's weight decay compose correctly.

## The non-obvious

SAM's benefit depends on the batch size used for the *ascent* step as well as the descent, the **m-sharpness** effect. Compute $\hat\epsilon$ per-GPU or per-microbatch (small $m$) instead of over the full batch and SAM works *better*. Nobody has a fully satisfying mechanistic account of why. A naive data-parallel SAM that averages the perturbation over the global batch throws away much of the gain; the folklore-correct version computes it on small local shards. SAM's "sharpness" also differs from the clean Hessian sharpness of [[Concept - The Edge of Stability|EoS]] and [[Concept - The Hessian Spectrum in Deep Learning|the Hessian spectrum]]. It's a stochastic, batch-dependent surrogate, and that gap is part of why the flatness-generalization story is still contested.

Open (as of 2026): whether SAM's flatness advantage survives, and pays for its compute, at frontier LLM scale. It's a proven regularizer for data-limited vision and fine-tuning and an unproven bet everywhere else.

## Connections

- [[Concept - Generalization in Deep Learning]] — SAM is the cleanest intervention testing the flat-minima → generalization hypothesis, turning an observation into a controllable lever.
- [[Concept - The Edge of Stability]] — EoS leaves the model at $2/\eta$ sharpness when you control it only via LR; SAM attacks sharpness directly, the complementary approach.
- [[Concept - Stochastic Gradient Descent and Momentum]] — SGD reaches flat minima implicitly via gradient noise; SAM does it explicitly, and layers on top of SGD/AdamW as the base optimizer.
- [[Concept - Adam and AdamW]] — the base optimizer SAM wraps; SAM changes only which gradient is fed to it, not the update rule.
- [[Concept - Vision Transformers]] — the headline SAM result: ViTs train competitively without heavy augmentation or JFT-scale pretraining when SAM supplies the flatness bias (cross-domain: multimodal).
- [[Concept - The Hessian Spectrum in Deep Learning]] — SAM's surrogate sharpness relates to, but is not, the top Hessian eigenvalue; the distinction matters for interpreting its gains (cross-domain: foundations).
- [[Concept - Mode Connectivity and Flat Minima]] — SAM biases toward the flat basins this geometry studies (cross-domain: esoterica).
- [[Concept - Scaling Laws]] — the 2× compute cost is why SAM loses to "just train on more tokens" in the pretraining regime scaling laws describe (cross-domain: training at scale).
- [[Lore - The Adam vs SGD Generalization Wars]] — SAM is a data point in the long argument over what actually drives generalization: the optimizer's implicit bias vs an explicit flatness objective.
- [[Breakdown - Batch Normalization]] — SAM's two passes must share consistent batch statistics; inconsistent BN stats across the ascent/descent passes corrupt the perturbation.

## Sources

- Foret, Kleiner, Mobahi, Neyshabur (2020) — "Sharpness-Aware Minimization for Efficiently Improving Generalization." The original SAM objective, two-step approximation, and vision results.
- Kwon, Kim, Park, Choi (2021) — "ASAM: Adaptive Sharpness-Aware Minimization." Scale-invariant $\rho$ that transfers across layers.
- Chen, Hsieh, Gong (2021) — "When Vision Transformers Outperform ResNets without Pre-training or Strong Data Augmentations." SAM as the enabling regularizer for ViT/MLP-Mixer.
- Andriushchenko, Flammarion (2022) — "Towards Understanding Sharpness-Aware Minimization." Analysis of the m-sharpness effect and why per-batch perturbation matters.
