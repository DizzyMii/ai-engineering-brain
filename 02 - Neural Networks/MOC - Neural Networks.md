---
tags: [moc, domain/neural-networks, level/surface]
aliases: []
summary: "Map of neural network fundamentals: training loop, optimizers, normalization, and generalization theory beneath every architecture."
---

# MOC - Neural Networks

This domain owns the mechanics of how a network turns inputs into predictions and turns a loss signal into updated weights — the substrate every architecture in [[MOC - Architectures]] and every distributed run in [[MOC - Training at Scale]] takes for granted. It exists because "call `.backward()`" hides a stack of decisions — activation choice, initialization scale, optimizer state, normalization placement — each with its own failure mode, and most "my model won't train" bugs live exactly here, not in the architecture. The notes span from the perceptron and the training loop (surface) through backprop and optimizer internals (core/advanced) to open questions about why SGD and Adam generalize differently and why some networks train stably with no normalization at all (frontier/unicorn). Read this domain before touching architecture-specific material — attention variants, MoE routing, and RoPE all assume you already know why residual connections rescue gradient flow and why Adam's epsilon matters more than its name suggests.

## Start here

- **Surface** → [[Concept - The Multilayer Perceptron]] — stacked affine transforms plus nonlinearities is the whole idea; everything else refines this.
- **Core** → [[Concept - Backpropagation]] — reverse-mode autodiff over the computational graph; the algorithm that makes any of this trainable.
- **Advanced** → [[Playbook - Debugging a Neural Network That Won't Train]] — the internals knowledge from this domain applied to the question every practitioner actually has.
- **Frontier** → [[Concept - The Edge of Stability]] — the empirical finding that broke classical optimization theory's assumptions about how gradient descent behaves near convergence.
- **Unicorn** → [[Lore - The Adam vs SGD Generalization Wars]] — the still-unresolved dispute over why SGD often generalizes better than Adam despite converging slower.

## Foundations of the network

- [[Concept - The Multilayer Perceptron]] — stacking affine transforms with nonlinearities between them is what turns a linear model into a universal function approximator.
- [[Concept - Loss Functions for Neural Networks]] — cross-entropy vs. MSE isn't a style choice: the loss's gradient shape determines how fast and how stably the network learns.
- [[Concept - Softmax]] — exponentiate-and-normalize into a probability distribution, and the numerical instability on large logits is why every real implementation subtracts the max first.
- [[Concept - Activation Functions]] — ReLU's dead-neuron failure mode and GELU/SiLU's smoother gradients explain why modern transformers abandoned sigmoid and tanh almost entirely.
- [[Concept - Embeddings as Learned Representations]] — a lookup table trained by gradient descent, and the geometry that falls out of it (analogy arithmetic, clustering) is discovered, not designed.

## Training mechanics

- [[Concept - Backpropagation]] — the chain rule applied at scale through reverse-mode automatic differentiation; a backward pass costs roughly the same FLOPs as the forward pass that produced it.
- [[Concept - The Training Loop]] — forward, loss, backward, step: the four-stage skeleton every framework wraps in ceremony, and the ordering that determines whether gradients accumulate correctly.
- [[Snippet - A Minimal Training Loop in PyTorch]] — the loop with nothing hidden, so you can see exactly where `.zero_grad()`, `.backward()`, and `.step()` each do their work.
- [[Concept - Weight Initialization]] — get the initial variance wrong by a constant factor and a deep network's activations vanish or explode before the first gradient step; Xavier and Kaiming derive the fix from forward-pass variance itself.
- [[Concept - Vanishing and Exploding Gradients]] — repeated multiplication through depth compounds gradient magnitude exponentially, the failure mode that initialization, normalization, and residual connections each independently attack.

## Optimization

- [[Concept - Stochastic Gradient Descent and Momentum]] — momentum accumulates a velocity term that smooths noisy per-batch gradients into a trajectory, which is why it escapes shallow oscillation that vanilla SGD gets stuck in.
- [[Concept - Adam and AdamW]] — per-parameter adaptive learning rates from running first- and second-moment estimates, plus the decoupled weight decay fix (AdamW) that plain Adam's L2-in-the-gradient formulation silently breaks.
- [[Reference - Optimizer Update Rules]] — the actual update equations for SGD, momentum, RMSProp, Adam, and AdamW side by side, showing exactly what state each one carries and what it costs in memory.
- [[Concept - Adam's Epsilon and Bias Correction]] — the epsilon added for numerical stability isn't cosmetic: at low gradient magnitudes it silently caps the effective step size, and bias correction exists because the moment estimates start at zero.
- [[Lore - The Adam vs SGD Generalization Wars]] — the long-running dispute over why SGD often generalizes better than Adam despite converging faster, and what the "flat minima" explanation gets right and wrong.

## Normalization, residuals, and regularization

- [[Concept - RMSNorm and LayerNorm]] — LayerNorm's mean-centering turns out to be dispensable; RMSNorm keeps only the rescaling term and now runs in nearly every modern LLM because it's cheaper and just as stable.
- [[Breakdown - Batch Normalization]] — the technique that made deep CNNs trainable, its actual mechanism (batch statistics, not "internal covariate shift" as originally claimed), and why it breaks down at small batch sizes and in autoregressive models.
- [[Decision - Choosing a Normalization Layer]] — BatchNorm vs. LayerNorm vs. RMSNorm isn't taste; it's set by whether your batch statistics are stable (CNNs) or your sequence lengths vary and inference is autoregressive (transformers).
- [[Concept - Normalization-Free Networks]] — normalization layers can be replaced with careful initialization and residual scaling; the payoff is speed, the cost is a much narrower margin for error.
- [[Concept - Residual Connections]] — an identity shortcut around a block turns the gradient signal into an additive path instead of a multiplicative one, the single biggest reason networks past ~20 layers became trainable at all.
- [[Concept - Dropout]] — randomly zeroing activations during training forces redundancy across units and approximates ensembling at inference for free, but interacts badly with normalization layers if the ordering is wrong.

## Generalization and optimization dynamics

- [[Concept - Generalization in Deep Learning]] — overparameterized networks that could easily memorize training data generalize instead, and classical VC-dimension theory doesn't explain why; the current best answers implicate gradient descent's implicit bias toward flat, simple solutions.
- [[Concept - The Edge of Stability]] — full-batch gradient descent settles into a regime where loss curvature sits right at the divergence threshold of the learning rate, contradicting the fixed-smooth-landscape assumption behind classical convergence proofs.
- [[Concept - Sharpness-Aware Minimization]] — explicitly optimizes for a flat loss region, not just low loss, by perturbing weights toward the worst nearby point before each step, trading roughly 2x compute for measurably better generalization.

## Debugging in practice

- [[Playbook - Debugging a Neural Network That Won't Train]] — the systematic order for isolating whether a stuck loss is a data bug, an initialization bug, a learning-rate bug, or a genuine optimization plateau.
- [[Gotchas - Training Neural Networks]] — the recurring failure signatures (loss is NaN, loss doesn't move, train loss fine but val loss diverges) ranked by how much debugging time each one wastes.

## Adjacent domains

- [[MOC - Foundations]] — the linear algebra, calculus, and numerics this domain's mechanisms are built on.
- [[MOC - Architectures]] — every attention variant and normalization-placement decision there assumes the residual-stream and normalization mechanics taught here.
- [[MOC - Training at Scale]] — the same training loop and optimizers stretched across thousands of GPUs, where distributed failure modes build directly on the single-GPU mechanics here.
- [[MOC - Frontier & Esoterica]] — double descent and the lottery ticket hypothesis pick up directly where this domain's generalization and edge-of-stability notes leave off.
