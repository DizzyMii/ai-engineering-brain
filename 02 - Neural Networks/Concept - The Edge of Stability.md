---
tags: [concept, domain/neural-networks, level/frontier]
aliases: [EoS, edge of stability]
summary: "Gradient descent drives sharpness up to ~2/η and trains non-monotonically there, violating the classical descent lemma."
---
# Concept - The Edge of Stability

> **One-paragraph hook:** Every textbook derivation of gradient descent says: pick a step size below the stability limit and the loss falls monotonically. Real neural-network training does the opposite. It lets the curvature of the loss surface *rise* until it sits at the edge of what your learning rate can tolerate, then trains right there, with loss bouncing up and down step to step while trending down overall. This "edge of stability" (EoS) is one of the cleanest demonstrations that the optimization theory we teach doesn't describe the optimization we run. It also explains warmup, learning-rate selection, and why smaller LRs generalize better.

## The mechanism

Classical optimization gives a hard threshold. If the loss is $\beta$-smooth, meaning the largest Hessian eigenvalue (the **sharpness**) satisfies $\lambda_{\max} \le \beta$ everywhere, then a gradient step $\theta_{t+1} = \theta_t - \eta \nabla L$ obeys the descent lemma:

$$L(\theta_{t+1}) \le L(\theta_t) - \eta\left(1 - \tfrac{\eta \beta}{2}\right)\|\nabla L\|^2.$$

Monotone decrease is guaranteed only while $\eta < 2/\beta$, i.e. while $\lambda_{\max} < 2/\eta$. For intuition, take a 1-D quadratic $L = \tfrac{1}{2}\lambda\theta^2$: the update is $\theta_{t+1} = (1 - \eta\lambda)\theta_t$, which converges iff $|1 - \eta\lambda| < 1$, i.e. $\eta\lambda < 2$. At $\eta\lambda = 2$ the iterate flips sign at constant magnitude, a period-2 oscillation that neither grows nor shrinks. Above it, divergence. It's the same reasoning that governs [[Concept - Stochastic Gradient Descent and Momentum|SGD]] along an ill-conditioned valley.

Cohen et al. (2021) instrumented full-batch [[Concept - The Training Loop|gradient-descent training]] and tracked $\lambda_{\max}$ throughout (the top eigenvalue of the loss Hessian, via power iteration on Hessian-vector products; see [[Concept - The Hessian Spectrum in Deep Learning]]). Two things happen, in order:

1. **Progressive sharpening.** From initialization, $\lambda_{\max}$ climbs steadily; the model actively moves into sharper regions.
2. **The edge.** Once $\lambda_{\max}$ reaches $2/\eta$, it stops climbing and *hovers there*, typically within a few percent, for the rest of training. With sharpness pinned at the divergence boundary, the loss stops falling monotonically. It oscillates step to step (a period-2 wobble along the top eigenvector) while the moving average keeps going down.

That violates the monotone descent lemma. The network is balanced on the edge of the stable regime the lemma assumes, and stays there because any further sharpening would trigger the oscillation that pushes it back down.

## In practice

The main consequence: **the learning rate sets the curvature the model equilibrates at.** Since $\lambda_{\max} \to 2/\eta$, a smaller $\eta$ forces a *flatter* solution (lower final sharpness) and a larger $\eta$ a sharper one. That ties LR directly to flatness, the leading (if contested) proxy for [[Concept - Generalization in Deep Learning|generalization]]. It's a mechanistic reason smaller LRs often find better-generalizing minima, and links to [[Concept - Mode Connectivity and Flat Minima|flat-minima geometry]].

Two pieces of training folklore turn out to be consequences of this:

- **Warmup works because sharpening is gradual.** Sharpness starts low and climbs. Apply full $\eta$ from step 0 while $\lambda_{\max}$ is still adapting and the product $\eta\lambda_{\max}$ can briefly overshoot 2 and cause a loss spike (Gilmer et al. 2021 tie [[Concept - Training Stability and Loss Spikes|training instability]] directly to this curvature crossing). Linear LR warmup gives $\lambda_{\max}$ time to co-adapt, and it's near-universal in [[Concept - Scaling Laws|large-scale pretraining]].
- **"Too large" LRs sometimes just work** because the model self-regulates its sharpness down to match. The edge is a stable attractor, not a cliff.

Cohen et al. (2022) showed [[Concept - Adam and AdamW|Adam]] and other adaptive methods have a direct analog: they hover at an edge of stability measured in the *preconditioned* norm (the sharpness of the Hessian after Adam's $1/\sqrt{v}$ rescaling), with an optimizer-specific threshold in place of the plain $2/\eta$. So EoS belongs to the optimization geometry and isn't a quirk of vanilla GD.

## Failure modes

- **Monitoring the wrong signal.** The loss legitimately oscillates at the edge, so a naive "loss went up this step, something's broken" alarm fires constantly on a healthy run. Watch the *moving average* plus the sharpness estimate instead of the per-step loss.
- **Mistaking the edge for divergence.** A run at EoS looks jittery. A run that has actually crossed the threshold ($\eta\lambda_{\max}$ really $> 2$) diverges to NaN. Telling them apart means tracking $\lambda_{\max}$ with a periodic Lanczos/power-iteration probe; eyeballing the loss curve won't do it. It shows up as a real bug in the [[Gotchas - Training Neural Networks|training-bug catalog]].
- **Carrying full-batch results over to SGD blindly.** The crispest EoS results are full-batch. Minibatch noise blurs the picture into a related "edge of stochastic stability," and the effective threshold shifts with batch size, with its own detection subtleties.

## The non-obvious

Progressive sharpening means **the network makes its own loss surface harder to optimize**, right up to the stability limit. That isn't pathological; it's apparently where the best solutions live. So you don't pick a learning rate to stay safely inside the stable region. You pick one to *select which sharpness* the model settles at, since it will settle at $2/\eta$ regardless. LR stops meaning "how fast do I descend" and starts meaning "how flat a minimum do I want." That's why LR is the one hyperparameter whose optimum barely moves with tricks, and why methods like [[Concept - Sharpness-Aware Minimization|SAM]], which go after sharpness directly instead of through $\eta$, are a coherent idea and not a hack.

Folklore, weakly sourced (as of 2026): how EoS interacts with minibatch noise, batch size and normalization layers is unsettled. The clean $2/\eta$ story is a full-batch result, and how much of it survives at the batch sizes and normalization stacks of real pretraining is an open question.

## Connections

- [[Concept - Stochastic Gradient Descent and Momentum]] — EoS is a statement about the base gradient-descent dynamics; the $(1-\eta\lambda)$ contraction argument is the same one that governs momentum on ill-conditioned valleys.
- [[Concept - The Training Loop]] — the phenomenon lives in the plain forward-backward-step loop; nothing exotic is required to observe it.
- [[Concept - Generalization in Deep Learning]] — EoS gives a mechanism linking LR to final sharpness to generalization, sharpening the flat-minima hypothesis into something measurable.
- [[Concept - Sharpness-Aware Minimization]] — SAM optimizes flatness explicitly rather than indirectly through $\eta$; EoS explains why controlling sharpness is a lever worth pulling.
- [[Concept - Adam and AdamW]] — adaptive optimizers have their own edge of stability in the preconditioned norm, so the phenomenon generalizes beyond vanilla GD.
- [[Concept - The Hessian Spectrum in Deep Learning]] — sharpness is the top Hessian eigenvalue; measuring EoS requires the Hessian-vector-product / Lanczos machinery from that note (cross-domain: foundations).
- [[Concept - Mode Connectivity and Flat Minima]] — EoS predicts which flatness the optimizer converges to, tying directly into the geometry of flat basins (cross-domain: esoterica).
- [[Concept - Training Stability and Loss Spikes]] — warmup and loss-spike behavior at scale are the practical face of the $\eta\lambda_{\max}$ crossing (cross-domain: training at scale).
- [[Concept - Scaling Laws]] — LR warmup, whose necessity EoS explains, is standard in the large pretraining runs scaling laws describe (cross-domain: training at scale).
- [[Gotchas - Training Neural Networks]] — distinguishing healthy edge-of-stability oscillation from real divergence is a concrete training-debugging pitfall.

## Sources

- Cohen, Kaur, Li, Kolter, Talwalkar (2021) — "Gradient Descent on Neural Networks Typically Occurs at the Edge of Stability." The original empirical result: progressive sharpening and the $2/\eta$ hover.
- Cohen et al. (2022) — "Adaptive Gradient Methods at the Edge of Stability." Extends EoS to Adam/RMSProp via the preconditioned Hessian.
- Gilmer, Ghorbani, Garg et al. (2021) — "A Loss Curvature Perspective on Training Instabilities of Deep Learning." Connects warmup, LR, and loss spikes to the curvature/stability threshold.
