---
tags: [concept, domain/neural-networks, level/core]
aliases: [backprop, reverse-mode autodiff, reverse-mode automatic differentiation, autograd]
summary: "Reverse-mode autodiff over the computation graph: cached forward activations, per-op vector-Jacobian products, ~2x forward cost."
---

# Concept - Backpropagation

> **One-paragraph hook:** Backpropagation is the chain rule plus dynamic programming over the computation graph. It differentiates one scalar (the loss) with respect to millions or trillions of inputs (the parameters) in a single backward sweep that costs roughly two forward passes, and that price is *independent of parameter count*. That exchange rate is why gradient-based deep learning is economically possible. The hidden cost: every forward activation stays alive until the backward pass consumes it, and that memory wall shapes how large models get trained.

## The mechanism

Training a network builds a directed acyclic graph. Nodes are operations, edges carry tensors, and the loss is the single sink. Backprop is reverse-mode automatic differentiation on this DAG:

1. **Forward pass:** evaluate nodes in topological order, *caching* each intermediate activation.
2. **Backward pass:** seed the sink with $\bar{L} = \partial L / \partial L = 1$, then walk the graph in reverse topological order. Each node receives the adjoint $\bar{v} = \partial L / \partial v$ of its output and computes the adjoints of its inputs via its local **vector-Jacobian product (VJP)**.

```text
# forward
for v in topo_order(graph):
    v.out = v.op(v.inputs)          # cache v.out (and often v.inputs)

# backward
loss.grad = 1.0
for v in reversed(topo_order(graph)):
    for u in v.inputs:
        u.grad += vjp(v.op, u, cached, v.grad)   # += : fan-out sums adjoints
```

Two details matter most. Each op needs only its *local* VJP, so the full Jacobian is never materialized. For a batch matmul it would be a $(B \cdot d_\text{out}) \times (B \cdot d_\text{in})$ monster, while the VJP is just another matmul. And adjoints *accumulate* (`+=`) wherever a tensor fans out to multiple consumers. That accumulate-by-default behavior is what shows up in [[Concept - The Training Loop]] as the forgot-`zero_grad` bug.

For a linear layer $Y = XW$ feeding a stack like [[Concept - The Multilayer Perceptron]], the backward is:

$$\bar{X} = \bar{Y} W^\top, \qquad \bar{W} = X^\top \bar{Y}$$

Two matmuls per forward matmul, so backward is matmul-bound too: same kernels, tensor cores and roofline arithmetic (see [[Concept - Matrix Multiplication as the Atom of Deep Learning]]). Per token, forward ≈ $2P$ FLOPs and backward ≈ $4P$ ($2P$ for $\bar{X}$, $2P$ for $\bar{W}$). Hence the "backward is 2× forward" rule of thumb, and the $C \approx 6ND$ training-compute approximation.

**Why reverse-mode and not forward-mode.** Reverse-mode costs one sweep per *output*; forward-mode costs one sweep per *input direction*. Training has one output (the scalar loss) and $10^6$–$10^{12}$ inputs (parameters). Reverse-mode needs 1 backward pass; forward-mode would need one pass per parameter. Forward-mode only wins with few inputs and many outputs, e.g. Jacobians of a simulator w.r.t. a handful of controls.

**Memory.** The FLOPs are cheap. The activations aren't. Every cached tensor lives from its creation in forward until its consumer's VJP fires in backward, which for layer 1 is the *entire* step. Activation memory scales with batch × sequence length × width × depth and routinely exceeds parameter + optimizer memory; the accounting is in [[Reference - Memory Math for Transformers]].

## In practice

PyTorch autograd, JAX and every modern framework implement this. `loss.backward()` is the reverse sweep, the `.grad` fields are the adjoints, and each op registers its VJP. The gradients then feed an optimizer step ([[Concept - Stochastic Gradient Descent and Momentum]] or Adam) inside the loop shown runnable in [[Snippet - A Minimal Training Loop in PyTorch]].

Gradient checking is the standard unit test for any hand-written backward (custom CUDA op, custom autograd.Function). Compare the analytic gradient against central finite differences $\big(f(\theta + h) - f(\theta - h)\big)/2h$ in float64 with $h \approx 10^{-6}$. Relative error below $10^{-5}$ passes; $10^{-3}$-ish means a bug, often a missing transpose or a dropped term. Backprop computes *exact* analytic gradients, so any mismatch is an implementation defect and can't be written off as "numerical noise."

Activation recomputation (gradient checkpointing) trades the memory cost back into compute. Keep checkpoints every ~$\sqrt{L}$ layers, discard the rest, and recompute each segment's activations during backward. Memory drops from $O(L)$ to $O(\sqrt{L})$ for roughly one extra forward pass (~33% more compute), per Chen et al. 2016. It's standard in large-model training, and [[Deep Dive - FlashAttention]] uses the same recompute-don't-store logic to avoid ever writing the $O(N^2)$ attention matrix to HBM.

## Failure modes

- **Vanishing / exploding gradients.** The backward pass *multiplies* local Jacobians across depth, so gradient norms scale like a product of per-layer spectral norms and shrink or grow exponentially with depth. Symptoms, detection and the fix stack (init, normalization, residuals, clipping) are in [[Concept - Vanishing and Exploding Gradients]].
- **Silently severed graph.** A `.detach()`, `torch.no_grad()`, or a round trip through NumPy cuts the DAG. Everything upstream gets zero (or `None`) gradient and no error is raised. Symptom: loss flat from step 0, some `param.grad is None`. Detection: assert every trainable parameter has a finite, nonzero grad after the first backward.
- **In-place ops corrupting cached activations.** An in-place mutation (`relu_()`, `x += y`) that overwrites a tensor a VJP needs either raises PyTorch's version-counter error or, worse, in custom code silently produces wrong gradients.
- **Softmax/exp overflow in the loss.** The backward through a naive [[Concept - Softmax]] inherits any forward instability. Use the fused, max-subtracted forms so the $\hat{y} - y$ gradient path stays finite.

## The non-obvious

In 2026 the limit on backprop is almost never its FLOPs. It's the *lifetime* of cached activations. Treat backward as a memory-scheduling problem ("which tensors must survive until when") and several techniques become one idea: gradient checkpointing recomputes activations, FlashAttention recomputes attention scores, reversible architectures reconstruct activations from outputs. All rely on one hardware fact: recomputing a tensor is now cheaper than storing it and reading it back from HBM. The 1986 algorithm hasn't changed. The last decade of scale came from the engineering around *what it caches*.

## Connections

- [[Concept - The Multilayer Perceptron]] — the base network whose stacked layers backprop differentiates; the down-link for what is being trained.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — both backward matmuls per layer are the same atom as the forward; all cost accounting flows from this.
- [[Concept - The Training Loop]] — backward's accumulate-into-`.grad` semantics dictate the loop's `zero_grad`/`step` ordering.
- [[Concept - Stochastic Gradient Descent and Momentum]] — the consumer of the gradients backprop produces; backprop says nothing about *how* to use them.
- [[Concept - Vanishing and Exploding Gradients]] — the multiplicative-Jacobian pathology inherent to the reverse sweep, and its fix stack.
- [[Concept - Softmax]] — its Jacobian structure and the fused softmax+CE gradient are the standard nontrivial VJP worth knowing by heart.
- [[Reference - Memory Math for Transformers]] — quantifies the retained-activation memory that dominates backprop's footprint.
- [[Snippet - A Minimal Training Loop in PyTorch]] — the runnable form of forward/backward/step with correct ordering.
- [[Deep Dive - FlashAttention]] — the flagship example of the recompute-instead-of-store trade that backprop's memory profile motivates.

## Sources

- Rumelhart, Hinton & Williams (1986) — Learning representations by back-propagating errors. The paper that made backprop the field's engine.
- Linnainmaa (1970) — Master's thesis introducing reverse-mode automatic differentiation; the algorithm predates its neural-network fame by 16 years.
- Griewank & Walther (2008) — *Evaluating Derivatives*. The autodiff reference: VJPs, checkpointing theory, forward-vs-reverse cost analysis.
- Chen et al. (2016) — Training Deep Nets with Sublinear Memory Cost. The $O(\sqrt{L})$ gradient-checkpointing scheme.
- Dao et al. (2022) — FlashAttention. Recompute-in-backward applied to attention; the memory-over-FLOPs trade at its most consequential.
