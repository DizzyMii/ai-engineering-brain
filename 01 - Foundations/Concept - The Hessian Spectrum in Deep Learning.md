---
tags: [concept, domain/foundations, level/frontier]
aliases: [loss curvature, Hessian eigenspectrum, sharpness]
summary: "The loss Hessian's spectrum - a near-zero bulk plus a few outliers - and why lambda_max is set by your learning rate, not vice versa."
---

# Concept - The Hessian Spectrum in Deep Learning

> **One-paragraph hook:** The Hessian of a 7B-parameter loss is a $7{\times}10^9 \times 7{\times}10^9$ matrix, about $2 \times 10^{20}$ bytes in fp32, so you will never materialize it. Its top eigenvalue still decides whether your next step converges or explodes. Its bulk explains why [[Deep Dive - LoRA]] at rank 8 works, and its behavior during training (edge of stability) broke a piece of classical optimization theory. You never form $H$. You query it through matrix-vector products.

## The mechanism

**The object.** $H = \nabla^2 L(\theta)$ is symmetric, so it has a real eigendecomposition $H = Q \Lambda Q^\top$. This is the symmetric case where eigen- and singular decompositions coincide up to signs (see [[Concept - Singular Value Decomposition]]). Eigenvalues are curvatures along eigendirections, and the local quadratic model is $L(\theta + \delta) \approx L + g^\top\delta + \tfrac{1}{2}\delta^\top H \delta$. For gradient descent on a quadratic, step $\eta$ is stable iff $\eta < 2/\lambda_{max}$. Convergence speed depends on $\kappa = \lambda_{max}/\lambda_{min}$, at rate $((\kappa-1)/(\kappa+1))^t$: the optimization face of [[Concept - The Condition Number]]. Negative eigenvalues mark saddle directions, which are the dominant critical points of [[Concept - Convexity and the Loss Landscape]].

**What the spectrum looks like.** Empirically, nothing like a well-conditioned quadratic. Across architectures it splits in two (Sagun et al. 2017; Papyan 2018; Ghorbani et al. 2019):

```
density
  |█
  |█
  |██
  |███
  |█████
  |████████▂▁▁_________________▪____▪__▪   ← isolated outliers
  +----|-----------------------------|----→ eigenvalue
       0                          λ_max
   huge bulk at ~0            few large positives
```

- A **dense bulk piled up near zero.** The overwhelming majority of directions are nearly flat. That degenerate subspace is what overparameterization buys you.
- A **handful of large positive outliers.** Their count tracks the number of classes / the logit structure (Sagun et al. 2017; Papyan 2018 traced them to the class-mean structure of the Gauss–Newton term). Ghorbani et al. (2019) measured full spectral densities at ImageNet scale with stochastic Lanczos quadrature. They found large negative eigenvalues early in training that melt away, and found that BatchNorm suppresses the outliers.

**Edge of stability.** Cohen et al. (2021) showed that full-batch GD doesn't stay below the classical threshold. Training shows *progressive sharpening*: $\lambda_{max}$ rises until it reaches $\approx 2/\eta$, then hovers there while the loss keeps falling non-monotonically. That's [[Concept - The Edge of Stability]]. It violates the descent-lemma assumption most convergence proofs rest on, namely curvature comfortably below $2/\eta$. Adaptive optimizers do the same thing against a preconditioned sharpness.

**Querying $H$ without forming it.** Everything runs on Hessian-vector products: $Hv = \nabla_\theta(g^\top v)$ via double [[Concept - Backpropagation]] (Pearlmutter 1994), at roughly one extra forward-backward per product. Built on HVPs:
- Lanczos iteration gets the top-$k$ eigenvalues in a few dozen products.
- Hutchinson's estimator gives the trace, $\mathbb{E}[v^\top H v] = \mathrm{tr}(H)$ for random $\pm 1$ $v$.
- Stochastic Lanczos quadrature gives the full spectral density.

Curvature-aware optimizers swap $H$ for cheaper structured surrogates from the Gauss–Newton / Fisher family: K-FAC (Martens & Grosse 2015), Shampoo, and spectral-normalization-flavored methods like [[Concept - Muon Optimizer]]. The engineering is in [[Concept - Second-Order Optimizers at Scale]]. Near a minimum of an NLL loss, Fisher information $\approx$ Gauss–Newton $\approx$ Hessian. That [[Concept - Maximum Likelihood Estimation]] identity is why natural gradient makes sense.

## In practice

- **Measuring $\lambda_{max}$ on a real model.** Fix a batch and run 20–50 Lanczos iterations of HVPs, each ~2× a gradient step. That's minutes of overhead, not hours. PyTorch supports HVPs natively (`torch.autograd.functional.hvp`, or `functorch`-style composed transforms).
- **LR warmup is curvature management.** Early curvature is large and changes fast. A too-large step at $t=0$ oscillates along the top eigendirection and can diverge; warmup lets progressive sharpening happen under control. Loss spikes in large runs frequently coincide with curvature excursions along a few directions. War stories are in [[Lore - The Loss Spike Chronicles]].
- **Sharpness and generalization.** Large-batch training finds visibly sharper minima that generalize worse (Keskar et al. 2017). [[Concept - Sharpness-Aware Minimization]] optimizes a worst-case perturbed loss to flatten $\lambda_{max}$ and reliably helps on vision. "Flat ⇒ generalizes" is contested, though. Dinh et al. (2017) showed reparameterization can make any minimum arbitrarily sharp without changing the function, so comparing raw $\lambda_{max}$ across models or scales means nothing.
- **Adam as diagonal preconditioning.** The second-moment scaling in [[Concept - Adam and AdamW]] is a crude diagonal inverse-curvature estimate. It's enough to tame the wildly different per-parameter scales that inflate $\kappa$, and that's most of why Adam dominates for transformers.
- **The bulk is the budget.** With most directions flat, the *effective* dimension of training is tiny. That observation sits behind [[Concept - The Lottery Ticket Hypothesis]], pruning and low-rank adaptation. [[Concept - muP and Hyperparameter Transfer]] works by parameterizing so curvature scales predictably with width, which ties into [[Concept - Scaling Laws]] at the recipe level.

## Failure modes

- **$\eta > 2/\lambda_{max}$ divergence.** Loss oscillates with period ~2 steps along one direction, then explodes. Catch it with a cheap running power-iteration estimate of $\lambda_{max}$, or by noticing that halving LR fixes it. At scale it shows up as recurring spike-recover-spike patterns.
- **Stale measurements.** Because of progressive sharpening, curvature at init says little about step 10k. Tuning LR from an init-time $\lambda_{max}$ systematically overestimates the safe step.
- **Lanczos ghosts.** Without full reorthogonalization, floating-point Lanczos produces spurious duplicate eigenvalues, and naive implementations report a fake cluster at $\lambda_{max}$. Use reorthogonalized or restarted variants.
- **Mini-batch curvature noise.** The batch Hessian is a noisy draw. Outlier eigenvalues are fairly stable; the bulk edge isn't. Check a few batches before believing a number.
- **Cross-model sharpness comparisons.** Per Dinh et al. (2017), scale-invariant architectures (anything behind normalization layers) make raw sharpness gauge-dependent. Compare only within a fixed parameterization, or use scale-corrected measures.

## Causality runs backwards

At the edge of stability the classical picture flips. You don't measure curvature and then pick a step size. *Your step size picks the curvature*: training sharpens until $\lambda_{max} \approx 2/\eta$ and then self-regulates there. So "measure sharpness to set the LR" is circular in the regime where modern nets train, and a measured $\lambda_{max} \approx 2/\eta$ tells you about your optimizer settings, not the intrinsic geometry of your problem. The intrinsic signal is in the outlier *count* and the bulk's mass near zero.

## Connections

- [[Concept - The Condition Number]] — $\kappa(H)$ is the convergence-rate dial; this note is what $\kappa$ empirically looks like for deep nets.
- [[Concept - Convexity and the Loss Landscape]] — the critical-point taxonomy (saddles vs minima) that the spectrum's signs diagnose.
- [[Concept - Maximum Likelihood Estimation]] — Fisher information = expected Hessian of the NLL; the statistical identity behind natural gradient.
- [[Concept - Singular Value Decomposition]] — the spectral toolkit; for symmetric $H$, eigen-analysis is SVD up to signs.
- [[Concept - Backpropagation]] — double-backprop is the mechanism that makes Hessian-vector products cheap.
- [[Concept - Adam and AdamW]] — a diagonal preconditioner attacking the conditioning problem the spectrum reveals.
- [[Concept - The Edge of Stability]] — the full treatment of progressive sharpening and the $2/\eta$ hover.
- [[Concept - Sharpness-Aware Minimization]] — the optimizer that treats $\lambda_{max}$ as the thing to minimize.
- [[Concept - Second-Order Optimizers at Scale]] — K-FAC/Shampoo-family engineering built on the Gauss–Newton surrogate.
- [[Concept - Muon Optimizer]] — spectral preconditioning of weight updates, a direct descendant of curvature reasoning.
- [[Concept - muP and Hyperparameter Transfer]] — parameterize so curvature scales predictably with width; why LRs transfer.
- [[Concept - Scaling Laws]] — the compute-optimal recipes whose hyperparameter choices curvature analysis underwrites.
- [[Concept - The Lottery Ticket Hypothesis]] — the near-zero bulk is why tiny subnetworks and sparse solutions exist.
- [[Deep Dive - LoRA]] — low-rank updates suffice because the loss-relevant subspace is a few outlier directions wide.
- [[Concept - Grokking]] — delayed generalization dynamics studied partly through curvature and flatness lenses.
- [[Concept - Double Descent]] — the interpolation-threshold phenomenon that shares the overparameterized-geometry explanation.
- [[Lore - The Loss Spike Chronicles]] — what curvature excursions look like from the trenches of a large pretraining run.

## Sources

- Pearlmutter (1994) — "Fast Exact Multiplication by the Hessian" — the HVP trick everything else builds on.
- Sagun et al. (2017) — "Eigenvalues of the Hessian in Deep Learning" — bulk-plus-outliers, outlier count tracks classes.
- Papyan (2018) — "The Full Spectrum of Deepnet Hessians at Scale" — Gauss–Newton decomposition of the outlier structure.
- Ghorbani et al. (2019) — "An Investigation into Neural Net Optimization via Hessian Eigenvalue Density" — SLQ spectra at ImageNet scale; BatchNorm suppresses outliers.
- Keskar et al. (2017) — "On Large-Batch Training for Deep Learning" — sharp minima from large batches.
- Dinh et al. (2017) — "Sharp Minima Can Generalize for Deep Nets" — the reparameterization critique of sharpness.
- Cohen et al. (2021) — "Gradient Descent on Neural Networks Typically Occurs at the Edge of Stability" — progressive sharpening to $2/\eta$.
- Foret et al. (2021) — "Sharpness-Aware Minimization" — optimizing the perturbed worst-case loss.
- Martens & Grosse (2015) — "Optimizing Neural Networks with Kronecker-factored Approximate Curvature" — K-FAC.
