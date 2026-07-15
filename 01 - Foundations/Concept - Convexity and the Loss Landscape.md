---
tags: [concept, domain/foundations, level/advanced]
aliases: [non-convex optimization, loss landscape geometry, saddle points in deep learning]
summary: "Why non-convex deep learning losses are reliably trainable: saddle-point geometry, SGD noise, and mode connectivity between minima."
---

# Concept - Convexity and the Loss Landscape

> **One-paragraph hook:** Textbook optimization theory promises convergence guarantees for convex functions and offers little for anything else — and every loss surface a modern network actually optimizes is non-convex. Training should, by the textbook, be a coin flip against an unknown number of bad local traps. It isn't, reliably, at every scale from a two-layer MLP to a trillion-parameter transformer. Understanding *why* non-convexity turns out not to matter the way it should is the difference between panicking at a training plateau and correctly diagnosing it as a saddle, not a dead end.

## The mechanism

A function is convex if for all $x, y$ and $\lambda \in [0,1]$:

$$f(\lambda x + (1-\lambda) y) \leq \lambda f(x) + (1-\lambda) f(y)$$

— every chord lies above the curve. Convexity's payoff is strong: every local minimum is automatically global, there are no saddle traps to escape, and strong convexity additionally guarantees a *unique* minimum with a linear convergence rate governed exactly by [[Concept - The Condition Number]]. None of this applies to a deep net's loss. Composing nonlinear layers destroys convexity outright, and even a single hidden layer has an exact non-convexity source that has nothing to do with the nonlinearities: permutation symmetry. Swap any two hidden units (and their associated weights) and the function computed is identical, so every minimum comes with at least $h!$ exact duplicates for $h$ hidden units — the loss surface is provably riddled with symmetric copies of every solution before you even account for genuine multimodality.

Given this, the fact that gradient-based training reliably finds good solutions is the central empirical surprise this note has to explain, and the resolution is a fact about geometry in high dimension, not about the loss surface being secretly nice. At a random critical point of a generic high-dimensional function, the Hessian's eigenvalues are, to a good approximation, independent random signs; the probability that *all* of them are positive (a true local minimum) or all negative (a local maximum) vanishes exponentially as dimension grows. What remains overwhelmingly likely at any given critical point is a mix of signs — a saddle. Dauphin et al. (2014), drawing on Bray & Dean's spin-glass theory of random Gaussian fields, showed this saddle-point dominance is not a curiosity of toy models but the expected structure of high-dimensional non-convex loss landscapes in general: the obstacles slowing training down are saddle plateaus, not a maze of bad local minima.

## In practice

This reframes what SGD actually has to do: not "avoid bad local minima" but "escape saddle-point plateaus efficiently." Gradient noise from minibatching helps here directly — an exact-gradient method can stall for a long time near a saddle where the gradient magnitude is tiny in every direction, while stochastic noise kicks the iterate off the degenerate directions faster. This same noise is implicated in an *implicit regularization* effect: SGD's trajectory is biased toward flatter regions of the loss relative to what full-batch gradient descent would find. The flat-vs-sharp-minima generalization story (Hochreiter & Schmidhuber 1997 first connected flatness to generalization; Keskar et al. 2016 showed large-batch training finds measurably sharper minima that generalize worse) is influential and widely cited, but genuinely contested — sharpness is basis-dependent and can be manipulated by reparameterization without changing the function computed, so treat "flat minima generalize better" as a real but incomplete piece of the story rather than a settled law.

A second and increasingly load-bearing piece of the picture is mode connectivity: distinct trained minima, found from different initializations, are joined by paths of near-constant loss rather than separated by high barriers (Garipov et al. 2018; Draxler et al. 2018). Accounting for the permutation symmetry described above sharpens this further — Entezari et al. (2021) conjectured, and Ainsworth et al. (2022, "Git Re-Basin") demonstrated practically, that after the right permutation of hidden units, independently trained networks are often connected by an essentially *linear* low-loss path. This is not just a theoretical curiosity: it is the geometric fact that makes naive weight-space [[Concept - Knowledge Distillation|model merging]] work at all for models sharing an initialization lineage.

## Failure modes

Long flat plateaus followed by a sudden loss drop are frequently misread as "the model has converged" when they are in fact a saddle region being slowly traversed — premature stopping on a plateau is a real and recoverable mistake, not evidence the architecture or data is bad. Oversized batches, by averaging away the gradient noise that helps escape saddles and biases toward flat regions, can land training in measurably sharper minima with worse held-out generalization even at equal or lower training loss — a failure mode that shows up as a training/validation gap that widens as batch size grows, not as an obviously broken loss curve. The permutation-symmetry degeneracy itself is usually harmless (it just means "the minimum" is really an equivalence class), but it does mean that comparing two checkpoints' raw weights, or averaging weights from differently-permuted runs, can silently produce nonsense.

## The non-obvious

Stop worrying about local minima as the enemy; in the parameter counts modern networks operate at, they are vanishingly rare relative to saddles. Start worrying about conditioning ([[Concept - The Condition Number]]) and saddle-induced plateaus, and treat large-batch sharpness as a real but secondary lever. Concretely, warmup and learning-rate schedules ([[Concept - The Training Loop]]) exist largely to manage this geometry: a low initial learning rate lets the optimizer navigate the sharply-curved early region of a fresh initialization without diverging, and decaying the rate later trades some saddle-escaping noise for the ability to settle precisely into a low-loss basin once one has been found.

## Connections

- [[Concept - The Condition Number]] — condition-number theory is the convex-case version of everything this note generalizes; strong convexity ties the two together exactly.
- [[Concept - The Hessian Spectrum in Deep Learning]] — the empirical eigenspectrum (bulk-plus-outliers) that shows saddle/minimum geometry in real trained networks, going past the random-matrix idealization used above.
- [[Concept - Maximum Likelihood Estimation]] — the estimation principle that defines the loss surface being discussed; the geometry here is the geometry of an MLE objective.
- [[Concept - Backpropagation]] — the mechanism computing the gradients whose noise (from minibatching) drives saddle escape (cross-domain: neural networks).
- [[Concept - Adam and AdamW]] — an adaptive optimizer whose per-coordinate scaling interacts with this landscape geometry differently than plain SGD (cross-domain: neural networks).
- [[Concept - The Training Loop]] — where warmup and LR schedules operationalize the plateau/sharpness management described above (cross-domain: neural networks).
- [[Concept - Grokking]] — a training-dynamics phenomenon (delayed generalization long after fitting) that plays out on this same non-convex landscape (cross-domain: frontier & esoterica).
- [[Concept - Double Descent]] — another landscape-geometry surprise (test error falls, rises, then falls again with capacity) adjacent to the saddle/flat-minima story here (cross-domain: frontier & esoterica).
- [[Concept - Knowledge Distillation]] — model merging by weight averaging is a direct practical payoff of mode connectivity and permutation-symmetry results (cross-domain: post-training).

## Sources

- Dauphin, Y. et al. (2014) — *Identifying and Attacking the Saddle Point Problem in High-Dimensional Non-Convex Optimization.* Establishes saddle-point dominance over local minima via random-matrix/spin-glass arguments.
- Hochreiter, S. & Schmidhuber, J. (1997) — *Flat Minima.* Original connection between minimum flatness and generalization.
- Keskar, N. et al. (2016) — *On Large-Batch Training for Deep Learning: Generalization Gap and Sharp Minima.* Empirical evidence that large-batch training finds sharper minima with worse generalization.
- Garipov, T. et al. (2018) — *Loss Surfaces, Mode Connectivity, and Fast Ensembling of DNNs.* Shows independently trained minima are joined by low-loss paths.
- Entezari, R. et al. (2021) — *The Role of Permutation Invariance in Linear Mode Connectivity of Neural Networks.* Conjectures permutation symmetry accounts for most apparent loss barriers between minima.
- Ainsworth, S., Hayase, J., & Srinivasa, S. (2022) — *Git Re-Basin: Merging Models modulo Permutation Symmetries.* Practical algorithm realizing near-linear mode connectivity after re-permutation.
