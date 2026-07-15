---
tags: [concept, domain/neural-networks, level/frontier]
aliases: [EoS, edge of stability]
summary: "Gradient descent drives sharpness up to ~2/η and trains non-monotonically there, violating the classical descent lemma."
---
# Concept - The Edge of Stability

> **One-paragraph hook:** Every textbook derivation of gradient descent says: pick a step size below the stability limit and the loss falls monotonically. Real neural-network training does the opposite. It lets the loss landscape's curvature *rise* until it is exactly at the edge of what your learning rate can tolerate, then trains right there — loss bouncing up and down step to step while trending down overall. This "edge of stability" (EoS) is one of the cleanest demonstrations that the optimization theory we teach does not describe the optimization we run, and it quietly explains warmup, learning-rate selection, and why smaller LRs generalize better.

## The mechanism

Classical optimization gives a hard threshold. If the loss is $\beta$-smooth — meaning the largest Hessian eigenvalue (the **sharpness**) satisfies $\lambda_{\max} \le \beta$ everywhere — then a gradient step $\theta_{t+1} = \theta_t - \eta \nabla L$ obeys the descent lemma:

$$L(\theta_{t+1}) \le L(\theta_t) - \eta\left(1 - \tfrac{\eta \beta}{2}\right)\|\nabla L\|^2.$$

The loss is guaranteed to decrease monotonically only while $\eta < 2/\beta$, i.e. while $\lambda_{\max} < 2/\eta$. The intuition is a 1-D quadratic $L = \tfrac{1}{2}\lambda\theta^2$: the update becomes $\theta_{t+1} = (1 - \eta\lambda)\theta_t$, which converges iff $|1 - \eta\lambda| < 1$, i.e. $\eta\lambda < 2$. At exactly $\eta\lambda = 2$ the iterate flips sign with constant magnitude — a period-2 oscillation that neither grows nor shrinks. Above it, divergence; the same reasoning that governs how [[Concept - Stochastic Gradient Descent and Momentum|SGD]] behaves along an ill-conditioned valley.

Cohen et al. (2021) instrumented full-batch [[Concept - The Training Loop|gradient-descent training]] and measured $\lambda_{\max}$ (the top eigenvalue of the loss Hessian, via power iteration on Hessian-vector products — see [[Concept - The Hessian Spectrum in Deep Learning]]) throughout. Two things happen, in order:

1. **Progressive sharpening.** From initialization, $\lambda_{\max}$ climbs steadily as training proceeds — the model actively moves into sharper regions of the landscape.
2. **The edge.** Once $\lambda_{\max}$ reaches $2/\eta$, it stops climbing and *hovers there*, typically within a few percent, for the rest of training. Because sharpness is pinned at the divergence boundary, the loss no longer falls monotonically — it oscillates step to step (a period-2 wobble along the top eigenvector) while the moving average keeps decreasing.

This directly violates the monotone descent lemma. The network is not training in the stable regime the lemma assumes; it is balanced on the knife-edge of that regime, and stays balanced because any further sharpening would trigger the oscillation that pushes it back down.

## In practice

The load-bearing consequence: **the learning rate sets the curvature the model equilibrates at.** Since $\lambda_{\max} \to 2/\eta$, a smaller $\eta$ forces the model into a *flatter* solution (lower final sharpness), and a larger $\eta$ into a sharper one. This couples LR directly to flatness, which is the leading (if contested) proxy for [[Concept - Generalization in Deep Learning|generalization]] — a mechanistic reason smaller LRs often find better-generalizing minima, and a bridge to [[Concept - Mode Connectivity and Flat Minima|flat-minima geometry]].

It reframes two pieces of training folklore as consequences rather than tricks:

- **Warmup works because sharpening is gradual.** Sharpness starts low and climbs. If you apply full $\eta$ from step 0 while $\lambda_{\max}$ is still adapting, the product $\eta\lambda_{\max}$ can transiently blow past 2 and trigger a loss spike (Gilmer et al. 2021 tie [[Concept - Training Stability and Loss Spikes|training instability]] directly to this curvature crossing). Linear LR warmup gives $\lambda_{\max}$ time to co-adapt, which is why it is near-universal in [[Concept - Scaling Laws|large-scale pretraining]].
- **"Too large" LRs sometimes just work** because the model self-regulates its sharpness down to match; the edge is a stable attractor, not a cliff.

The phenomenon is not confined to plain GD. Cohen et al. (2022) showed [[Concept - Adam and AdamW|Adam]] and other adaptive methods have an exact analog: they hover at an edge of stability measured in the *preconditioned* norm (the sharpness of the Hessian after Adam's $1/\sqrt{v}$ rescaling), with an optimizer-specific threshold rather than the plain $2/\eta$. So EoS is a property of the optimization geometry, not a quirk of vanilla GD.

## Failure modes

- **Monitoring the wrong signal.** Because the loss legitimately oscillates at the edge, a naive "loss went up this step → something is broken" alarm fires constantly on a healthy run. The correct signal is the *moving average* plus the sharpness estimate, not the per-step loss.
- **Mistaking the edge for divergence.** A run sitting at EoS looks jittery; a run that has actually crossed the threshold ($\eta\lambda_{\max}$ genuinely $> 2$) diverges to NaN. Telling them apart requires tracking $\lambda_{\max}$ (a periodic Lanczos/power-iteration probe), not eyeballing the loss curve — a distinction that shows up as a real bug in the [[Gotchas - Training Neural Networks|training-bug catalog]].
- **Extrapolating full-batch results to SGD blindly.** The crispest EoS results are full-batch. With minibatch noise the picture blurs into a related "edge of stochastic stability," and the effective threshold shifts with batch size — carrying its own detection subtleties.

## The non-obvious

Progressive sharpening means **the network chooses to make its own loss landscape harder to optimize**, right up to the stability limit, and this is not pathological — it is where the best solutions apparently live. The practical inversion of the textbook: you do not pick a learning rate to stay safely inside the stable region; you pick a learning rate to *select which sharpness* the model will settle at, because it will always settle at $2/\eta$ regardless. That reframes LR from "how fast do I descend" to "how flat a minimum do I want," which is why LR is the one hyperparameter whose optimum barely moves with tricks and why methods like [[Concept - Sharpness-Aware Minimization|SAM]] — which attack sharpness directly instead of via $\eta$ — are a coherent idea rather than a hack.

Folklore, weakly sourced (as of 2026): the precise interaction of EoS with minibatch noise, batch size, and normalization layers is unsettled. The clean $2/\eta$ story is a full-batch result; how much of it survives at the batch sizes and normalization stacks of real pretraining is an open question, not a solved one.

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
