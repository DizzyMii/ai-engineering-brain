---
tags: [moc, domain/neural-networks, level/surface]
aliases: []
summary: "Map of neural network fundamentals: training loop, optimizers, normalization, and generalization theory beneath every architecture."
---

# MOC - Neural Networks

This domain covers how a network turns inputs into predictions and a loss signal into updated weights. Every architecture in [[MOC - Architectures]] and every distributed run in [[MOC - Training at Scale]] takes this layer for granted. "Call `.backward()`" hides a stack of decisions (activation choice, initialization scale, optimizer state, normalization placement), each with its own failure mode, and most "my model won't train" bugs live here and not in the architecture. The notes run from the perceptron and the training loop (surface), through backprop and optimizer internals (core/advanced), to open questions: why SGD and Adam generalize differently, and why some networks train stably with no normalization at all (frontier/unicorn). Read this before architecture-specific material. Attention variants, MoE routing and RoPE all assume you know why residual connections rescue gradient flow and why Adam's epsilon matters more than its name suggests.

## Start here

- **Surface** → [[Concept - The Multilayer Perceptron]]: stacked affine transforms plus nonlinearities is the whole idea, and everything else refines it.
- **Core** → [[Concept - Backpropagation]]: reverse-mode autodiff over the computational graph, the algorithm that makes any of this trainable.
- **Advanced** → [[Playbook - Debugging a Neural Network That Won't Train]]: this domain's internals applied to the question every practitioner actually has.
- **Frontier** → [[Concept - The Edge of Stability]]: the empirical finding that broke classical optimization theory's assumptions about how gradient descent behaves near convergence.
- **Unicorn** → [[Lore - The Adam vs SGD Generalization Wars]]: the still-unresolved dispute over why SGD often generalizes better than Adam despite converging slower.

## Foundations of the network

- [[Concept - The Multilayer Perceptron]]: affine transforms stacked with nonlinearities between them turn a linear model into a universal function approximator.
- [[Concept - Loss Functions for Neural Networks]]: cross-entropy vs. MSE isn't a style choice. The shape of the loss's gradient sets how fast and how stably the network learns.
- [[Concept - Softmax]]: exponentiate and normalize into a probability distribution. Large logits make it numerically unstable, so every real implementation subtracts the max first.
- [[Concept - Activation Functions]]: ReLU's dead-neuron failure mode and the smoother gradients of GELU/SiLU explain why modern transformers dropped sigmoid and tanh almost entirely.
- [[Concept - Embeddings as Learned Representations]]: a lookup table trained by gradient descent. Its geometry (analogy arithmetic, clustering) is discovered, not designed.

## Training mechanics

- [[Concept - Backpropagation]]: the chain rule at scale via reverse-mode automatic differentiation. A backward pass costs roughly the same FLOPs as the forward pass that produced it.
- [[Concept - The Training Loop]]: forward, loss, backward, step. Every framework wraps these four stages in ceremony, and their order decides whether gradients accumulate correctly.
- [[Snippet - A Minimal Training Loop in PyTorch]]: the loop with nothing hidden, so you can see where `.zero_grad()`, `.backward()` and `.step()` each do their work.
- [[Concept - Weight Initialization]]: get the initial variance wrong by a constant factor and a deep network's activations vanish or explode before the first gradient step. Xavier and Kaiming derive the fix from forward-pass variance.
- [[Concept - Vanishing and Exploding Gradients]]: repeated multiplication through depth compounds gradient magnitude exponentially. Initialization, normalization and residual connections each attack this independently.

## Optimization

- [[Concept - Stochastic Gradient Descent and Momentum]]: momentum accumulates a velocity term that smooths noisy per-batch gradients into a trajectory, so it escapes the shallow oscillation vanilla SGD gets stuck in.
- [[Concept - Adam and AdamW]]: per-parameter adaptive learning rates from running first- and second-moment estimates, plus AdamW's decoupled weight decay, which fixes what plain Adam's L2-in-the-gradient formulation silently breaks.
- [[Reference - Optimizer Update Rules]]: the update equations for SGD, momentum, RMSProp, Adam and AdamW side by side, with the state each one carries and its memory cost.
- [[Concept - Adam's Epsilon and Bias Correction]]: the stability epsilon isn't cosmetic. At low gradient magnitudes it silently caps the effective step size. Bias correction exists because the moment estimates start at zero.
- [[Lore - The Adam vs SGD Generalization Wars]]: the long-running dispute over why SGD often generalizes better than Adam despite converging faster, and what the "flat minima" explanation gets right and wrong.

## Normalization, residuals, and regularization

- [[Concept - RMSNorm and LayerNorm]]: LayerNorm's mean-centering turns out to be dispensable. RMSNorm keeps only the rescaling term and now runs in nearly every modern LLM because it's cheaper and just as stable.
- [[Breakdown - Batch Normalization]]: the technique that made deep CNNs trainable, how it works (batch statistics, not the originally claimed "internal covariate shift"), and why it breaks at small batch sizes and in autoregressive models.
- [[Decision - Choosing a Normalization Layer]]: BatchNorm vs. LayerNorm vs. RMSNorm is set by whether your batch statistics are stable (CNNs) or your sequence lengths vary and inference is autoregressive (transformers). Taste doesn't enter into it.
- [[Concept - Normalization-Free Networks]]: careful initialization and residual scaling can replace normalization layers. You gain speed and lose a lot of margin for error.
- [[Concept - Residual Connections]]: an identity shortcut around a block makes the gradient path additive instead of multiplicative, the single biggest reason networks past ~20 layers became trainable at all.
- [[Concept - Dropout]]: randomly zeroing activations in training forces redundancy across units and approximates ensembling at inference for free. Get the ordering wrong and it interacts badly with normalization layers.

## Generalization and optimization dynamics

- [[Concept - Generalization in Deep Learning]]: overparameterized networks that could easily memorize their training data generalize instead, and classical VC-dimension theory can't explain it. The current best answers point to gradient descent's implicit bias toward flat, simple solutions.
- [[Concept - The Edge of Stability]]: full-batch gradient descent settles where loss curvature sits right at the learning rate's divergence threshold, contradicting the fixed smooth-surface assumption behind classical convergence proofs.
- [[Concept - Sharpness-Aware Minimization]]: optimizes for a flat loss region as well as low loss, perturbing weights toward the worst nearby point before each step. It costs roughly 2x compute for measurably better generalization.

## Debugging in practice

- [[Playbook - Debugging a Neural Network That Won't Train]]: the order in which to check whether a stuck loss is a data bug, an initialization bug, a learning-rate bug, or an honest optimization plateau.
- [[Gotchas - Training Neural Networks]]: recurring failure signatures (loss is NaN, loss doesn't move, train loss fine but val loss diverges) ranked by how much debugging time each wastes.

## Adjacent domains

- [[MOC - Foundations]]: the linear algebra, calculus and numerics under this domain's mechanisms.
- [[MOC - Architectures]]: every attention variant and normalization-placement decision there assumes the residual-stream and normalization mechanics taught here.
- [[MOC - Training at Scale]]: the same loop and optimizers stretched across thousands of GPUs, where distributed failure modes build on the single-GPU mechanics here.
- [[MOC - Frontier & Esoterica]]: double descent and the lottery ticket hypothesis pick up where this domain's generalization and edge-of-stability notes stop.
