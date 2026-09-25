---
tags: [concept, domain/foundations, level/advanced]
aliases: [non-convex optimization, loss landscape geometry, saddle points in deep learning]
summary: "Why non-convex deep learning losses are reliably trainable: saddle-point geometry, SGD noise, and mode connectivity between minima."
---

# Concept - Convexity and the Loss Landscape

> **One-paragraph hook:** Textbook optimization theory gives convergence guarantees for convex functions and very little for anything else, and every loss surface a modern network optimizes is non-convex. By the textbook, training should be a coin flip against an unknown number of bad local traps. In practice it works reliably at every scale, from a two-layer MLP to a trillion-parameter transformer. Knowing why non-convexity matters less than it should is what lets you look at a training plateau and call it a saddle instead of a dead end.

## The mechanism

A function is convex if for all $x, y$ and $\lambda \in [0,1]$:

$$f(\lambda x + (1-\lambda) y) \leq \lambda f(x) + (1-\lambda) f(y)$$

In words: every chord lies above the curve. The payoff is strong. Every local minimum is global, there are no saddle traps, and strong convexity adds a *unique* minimum with a linear convergence rate set by [[Concept - The Condition Number]]. None of it applies to a deep net's loss. Stacking nonlinear layers destroys convexity outright. Even a single hidden layer has a non-convexity source unrelated to the nonlinearities: permutation symmetry. Swap any two hidden units (with their weights) and the computed function is identical, so every minimum has at least $h!$ exact duplicates for $h$ hidden units. The surface is provably full of symmetric copies of every solution before you count any real multimodality.

So why does gradient-based training reliably find good solutions? The answer is about geometry in high dimension; the loss surface isn't secretly nice. At a random critical point of a generic high-dimensional function, the Hessian's eigenvalues are, to a good approximation, independent random signs. The probability that *all* are positive (a true local minimum) or all negative (a local maximum) vanishes exponentially as dimension grows. What's left at almost any critical point is a mix of signs: a saddle. Dauphin et al. (2014), building on Bray & Dean's spin-glass theory of random Gaussian fields, showed that saddle dominance is the expected structure of high-dimensional non-convex losses in general, toy models or not. What slows training down is saddle plateaus. A maze of bad local minima isn't the problem.

## In practice

SGD's job, then, is to escape saddle plateaus efficiently. Minibatch gradient noise helps directly. An exact-gradient method can stall near a saddle where the gradient is tiny in every direction, while stochastic noise kicks the iterate off the degenerate directions faster. The same noise is implicated in an *implicit regularization* effect: SGD's trajectory is biased toward flatter regions than full-batch gradient descent would find. The flat-vs-sharp-minima generalization story is influential and widely cited. Hochreiter & Schmidhuber 1997 first tied flatness to generalization, and Keskar et al. 2016 showed large-batch training finds measurably sharper minima that generalize worse. It's also contested. Sharpness is basis-dependent and can be changed by reparameterization without changing the computed function, so treat "flat minima generalize better" as a real but incomplete part of the picture and not a settled law.

The second piece, and one that matters more every year, is mode connectivity. Distinct trained minima from different initializations are joined by paths of near-constant loss instead of being separated by high barriers (Garipov et al. 2018; Draxler et al. 2018). Accounting for permutation symmetry sharpens this. Entezari et al. (2021) conjectured, and Ainsworth et al. (2022, "Git Re-Basin") showed in practice, that after the right permutation of hidden units, independently trained networks are often connected by an essentially *linear* low-loss path. This has practical weight: it's the geometric fact that makes naive weight-space [[Concept - Knowledge Distillation|model merging]] work at all for models that share an initialization lineage.

## Failure modes

Long flat plateaus followed by a sudden loss drop are frequently misread as convergence when they're a saddle region being slowly crossed. Stopping on a plateau is a real, recoverable mistake, and it says nothing bad about the architecture or data.

Oversized batches average away the gradient noise that helps escape saddles and pushes toward flat regions. They can land in measurably sharper minima with worse held-out generalization, even at equal or lower training loss. You see it as a train/validation gap that widens with batch size; the loss curve looks fine.

The permutation-symmetry degeneracy is usually harmless, since "the minimum" is really an equivalence class. But comparing two checkpoints' raw weights, or averaging weights from differently permuted runs, can silently produce nonsense.

## The non-obvious

Stop treating local minima as the enemy. At modern parameter counts they're vanishingly rare compared with saddles. Worry about conditioning ([[Concept - The Condition Number]]) and saddle-induced plateaus instead, and treat large-batch sharpness as a real but secondary lever. Warmup and learning-rate schedules ([[Concept - The Training Loop]]) exist largely to manage this geometry. A low initial learning rate lets the optimizer get through the sharply curved early region of a fresh initialization without diverging. Decaying the rate later gives up some saddle-escaping noise so the optimizer can settle into a low-loss basin once it has found one.

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
