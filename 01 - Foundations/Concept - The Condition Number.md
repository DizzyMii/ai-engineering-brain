---
tags: [concept, domain/foundations, level/advanced]
aliases: [kappa, matrix condition number, condition number of the Hessian]
summary: "The single number governing both how much a linear solve amplifies numerical error and how fast gradient descent converges."
---

# Concept - The Condition Number

> **One-paragraph hook:** Ill-conditioning hides behind two pains that look unrelated: a linear solve that returns garbage despite correct code, and a training run that zig-zags for thousands of steps before the loss moves. Both trace back to one scalar, $\kappa$. Once you can name it, "this converges slowly" and "this result is untrustworthy" stop being separate mysteries.

## The mechanism

For a matrix $A$, the condition number is:

$$\kappa(A) = \frac{\sigma_{\max}}{\sigma_{\min}} = \|A\| \, \|A^{-1}\|$$

where $\sigma_{\max}, \sigma_{\min}$ are the largest and smallest singular values ([[Concept - Singular Value Decomposition]]). It bounds worst-case relative error amplification when solving $Ax = b$: the relative error in $x$ can be up to $\kappa$ times the relative error in the inputs. Rule of thumb: $\log_{10}\kappa$ is roughly the number of decimal digits of accuracy you lose. In fp32 (machine epsilon $\approx 1.19\text{e-}7$, see [[Reference - Floating Point Formats]]), a matrix with $\kappa \sim 1/\epsilon \approx 10^7$ has effectively zero trustworthy digits left in its solution. The answer is noise, not a code bug. So in practice you never invert a matrix explicitly; you factor and solve ([[Decision - Choosing a Matrix Factorization]]), because factorization-based solves are far more numerically stable for a given $\kappa$ than forming $A^{-1}$.

The same scalar governs optimization speed. For a quadratic loss $\mathcal{L}(x) = \frac{1}{2}x^\top H x$ with Hessian $H$, gradient descent with the optimal fixed step size converges at rate:

$$\left(\frac{\kappa - 1}{\kappa + 1}\right)^t, \qquad \kappa = \kappa(H)$$

At $\kappa = 1$ (perfectly conditioned, isotropic bowl) convergence is instant. As $\kappa \to \infty$ the rate approaches 1, meaning no progress per step, and the trajectory zig-zags across a narrow valley. Steep in high-curvature directions, nearly flat in low-curvature ones: a step size stable for one is too timid or explosive for the other. Momentum improves the rate to roughly $\sqrt{\kappa}$ dependence (Nesterov's accelerated gradient hits the theoretical optimum for this problem class). Full Newton's method rescales by $H^{-1}$, which makes the effective condition number 1 regardless of $H$'s actual spectrum, at the cost of forming and solving with $H$ itself.

## In practice

Ill-conditioning costs you on both the numerical and the optimization side, so a large share of deep learning engineering is conditioning control under other names:

- **Normalization layers.** [[Concept - RMSNorm and LayerNorm]] rescale activations to unit-ish variance per layer. That stops the effective curvature downstream from varying by orders of magnitude across features, which attacks input-scale ill-conditioning directly.
- **Adam's per-coordinate scaling.** The second-moment normalization $g / (\sqrt{v} + \epsilon)$ in [[Concept - Adam and AdamW]] is a diagonal preconditioner. It divides each parameter's update by an estimate of that parameter's own gradient scale. It's cheap because it needs only the diagonal of an implicit curvature matrix, not the full Hessian.
- **Whitening and muP.** Whitening (decorrelating and rescaling inputs) removes the correlated-feature source of ill-conditioning directly. Maximal-update parameterization (muP) picks per-layer learning rates and init scales so the effective conditioning, and with it good hyperparameters, transfers across model widths.

## Failure modes

Where ill-conditioning comes from in real networks:
- correlated input features (redundant directions inflate $\sigma_{\max}/\sigma_{\min}$ directly)
- parameters on wildly different natural scales (a bias term next to a weight matrix, or early vs. late layers in a deep stack)
- deep function compositions that multiply Jacobians together
- the vanishing/exploding gradient regime ([[Concept - Backpropagation]]), where per-layer conditioning compounds across depth

Detection doesn't need a full SVD, which at $O(mn\min(m,n))$ is too expensive per step anyway. Power iteration cheaply estimates $\sigma_{\max}$ (apply $A^\top A$ repeatedly and normalize); inverse iteration or Lanczos on the inverse estimates $\sigma_{\min}$. Symptoms are cheaper still: a loss curve that plateaus and then abruptly moves, or visibly oscillates along one direction while crawling along another, is the classic zig-zag signature of a high-$\kappa$ region.

## The non-obvious

The Hessian's $\kappa$, the condition number of the loss, predicts trainability better than raw depth or parameter count. Plenty of training "tricks" that read as unrelated folk wisdom are conditioning fixes under different names: normalize your inputs, don't mix learning rates across wildly different parameter groups, warm up the learning rate, use Adam over vanilla SGD on transformers. If a run is inexplicably slow to move with a reasonable learning rate and no NaNs, check whether the effective problem is ill-conditioned before reaching for a bigger learning rate or more steps. That's usually the faster diagnosis.

## Connections

- [[Concept - Singular Value Decomposition]] — $\kappa$ is defined directly from the singular value spectrum; this note is the "so what" of that decomposition.
- [[Concept - Convexity and the Loss Landscape]] — condition number theory is exact for convex quadratics; this is the bridge to what actually happens in the non-convex loss landscapes deep nets optimize.
- [[Concept - The Hessian Spectrum in Deep Learning]] — the empirical eigenspectrum of real network Hessians, where $\kappa$ stops being a clean textbook number and becomes a messy bulk-plus-outliers distribution.
- [[Concept - Floating Point for Deep Learning]] — the numerical-error side of $\kappa$: how many digits a given format can actually preserve through an ill-conditioned computation.
- [[Decision - Choosing a Matrix Factorization]] — the practical consequence of $\kappa$'s numerical-stability role: why you factor instead of invert, and which factorization to pick.
- [[Concept - Adam and AdamW]] — a concrete, shipped preconditioner that exists specifically to reduce the effective condition number Adam's optimizer sees (cross-domain: neural networks).
- [[Concept - RMSNorm and LayerNorm]] — the architectural-level conditioning fix that runs on every forward pass (cross-domain: neural networks).
- [[Concept - Backpropagation]] — where compounding-across-depth ill-conditioning (vanishing/exploding gradients) originates (cross-domain: neural networks).
- [[Concept - Scaling Laws]] — muP's hyperparameter-transfer guarantees rest on keeping effective conditioning stable across model widths as you scale up (cross-domain: training at scale).

## Sources

- Trefethen, L. N. & Bau, D. (1997) — *Numerical Linear Algebra.* Standard reference for the condition number's role in error amplification for linear solves.
- Nocedal, J. & Wright, S. (2006) — *Numerical Optimization.* Derivation of the $((\kappa-1)/(\kappa+1))^t$ gradient-descent convergence rate and the $\sqrt{\kappa}$ improvement from momentum/acceleration.
- Yang, G. et al. (2021) — *Tensor Programs V: Tuning Large Neural Networks via Zero-Shot Hyperparameter Transfer.* The muP parameterization that keeps effective conditioning (and thus good hyperparameters) stable across width.
