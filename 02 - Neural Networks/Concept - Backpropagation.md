---
tags: [concept, domain/neural-networks, level/core]
aliases: [backprop, reverse-mode autodiff, reverse-mode automatic differentiation, autograd]
summary: "Reverse-mode autodiff over the computation graph: cached forward activations, per-op vector-Jacobian products, ~2x forward cost."
---

# Concept - Backpropagation

> **One-paragraph hook:** Backpropagation is the chain rule plus dynamic programming over the computation graph. It differentiates one scalar (the loss) with respect to millions or trillions of inputs (the parameters) in a single backward sweep costing roughly two forward passes — a price that is *independent of parameter count*. That absurdly favorable exchange rate is the reason gradient-based deep learning is economically possible at all, and its one hidden cost — every forward activation must be kept alive until the backward pass consumes it — is the memory wall that shapes how large models are actually trained.

## The mechanism

Training a network builds a directed acyclic graph: nodes are operations, edges carry tensors, and the loss is the single sink. Backprop is reverse-mode automatic differentiation on this DAG:

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

Two details carry all the weight. First, each op needs only its *local* VJP — the full Jacobian is never materialized (for a batch matmul it would be a $(B \cdot d_\text{out}) \times (B \cdot d_\text{in})$ monster; the VJP is just another matmul). Second, adjoints *accumulate* (`+=`) where a tensor fans out to multiple consumers — the same accumulate-by-default semantics that surfaces in [[Concept - The Training Loop]] as the forgot-`zero_grad` bug.

**Matrix form is the whole game.** For a linear layer $Y = XW$ feeding a stack like [[Concept - The Multilayer Perceptron]], the backward is:

$$\bar{X} = \bar{Y} W^\top, \qquad \bar{W} = X^\top \bar{Y}$$

Two matmuls per layer's one forward matmul. So the backward pass is also matmul-bound — the same kernels, tensor cores, and roofline arithmetic as the forward; see [[Concept - Matrix Multiplication as the Atom of Deep Learning]]. Per token this gives forward ≈ $2P$ FLOPs and backward ≈ $4P$ ($2P$ for $\bar{X}$, $2P$ for $\bar{W}$), which is the "backward is 2× forward" rule of thumb and the origin of the $C \approx 6ND$ training-compute approximation.

**Why reverse-mode and not forward-mode.** Reverse-mode costs one sweep per *output*; forward-mode costs one sweep per *input direction*. Training has exactly one output (the scalar loss) and $10^6$–$10^{12}$ inputs (parameters): reverse-mode needs 1 backward pass, forward-mode would need one pass per parameter. Forward-mode wins only in the transposed regime — few inputs, many outputs (e.g., Jacobians of a simulator w.r.t. a handful of controls).

**Memory.** The FLOPs are cheap; the activations are not. Every cached tensor must live from its creation in forward until its consumer's VJP fires in backward — for layer 1, that is the *entire* duration of the step. Activation memory scales with batch × sequence length × width × depth and routinely exceeds parameter + optimizer memory; the accounting is in [[Reference - Memory Math for Transformers]].

## In practice

PyTorch autograd, JAX, and every modern framework implement exactly this: `loss.backward()` is the reverse sweep, `.grad` fields are the adjoints, and each op registers its VJP. The gradients then feed an optimizer step — [[Concept - Stochastic Gradient Descent and Momentum]] or Adam — inside the loop shown runnable in [[Snippet - A Minimal Training Loop in PyTorch]].

**Gradient checking is the canonical unit test** for any hand-written backward (custom CUDA op, custom autograd.Function). Compare the analytic gradient against central finite differences $\big(f(\theta + h) - f(\theta - h)\big)/2h$ in float64 with $h \approx 10^{-6}$; relative error below $10^{-5}$ passes, $10^{-3}$-ish means a bug (often a missing transpose or a dropped term). Backprop computes *exact* analytic gradients — any mismatch is an implementation defect, not "numerical noise."

**Activation recomputation (gradient checkpointing)** trades the memory cost back into compute: keep checkpoints every ~$\sqrt{L}$ layers, discard the rest, and recompute each segment's activations during backward. Memory drops from $O(L)$ to $O(\sqrt{L})$ for roughly one extra forward pass (~33% more compute) — Chen et al. 2016. This is standard practice in large-model training, and the same recompute-don't-store logic is how [[Deep Dive - FlashAttention]] avoids ever writing the $O(N^2)$ attention matrix to HBM.

## Failure modes

- **Vanishing / exploding gradients.** The backward pass *multiplies* local Jacobians across depth, so gradient norms scale like a product of per-layer spectral norms — exponentially shrinking or growing with depth. Symptoms, detection, and the fix stack (init, normalization, residuals, clipping) live in [[Concept - Vanishing and Exploding Gradients]].
- **Silently severed graph.** A `.detach()`, `torch.no_grad()`, or conversion through NumPy cuts the DAG: everything upstream gets zero (or `None`) gradient, no error raised. Symptom: loss flat from step 0, some `param.grad is None`. Detection: assert every trainable parameter has a finite, nonzero grad after the first backward.
- **In-place ops corrupting cached activations.** An in-place mutation (`relu_()`, `x += y`) that overwrites a tensor needed by a VJP either raises PyTorch's version-counter error or — worse, in custom code — silently produces wrong gradients.
- **Softmax/exp overflow in the loss.** The backward through a naive [[Concept - Softmax]] inherits any forward instability; use the fused, max-subtracted forms so the $\hat{y} - y$ gradient path stays finite.

## The non-obvious

Backprop's binding constraint in 2026 is almost never its FLOPs — it is the *lifetime* of cached activations. Once you see the backward pass as a memory-scheduling problem ("which tensors must survive until when"), a whole family of techniques becomes one idea: gradient checkpointing recomputes activations, FlashAttention recomputes attention scores, reversible architectures reconstruct activations from outputs. All exploit the same hardware fact — recomputing a tensor is now cheaper than storing it and reading it back from HBM. The algorithm from 1986 is unchanged; the engineering around *what it caches* is where the last decade of scale came from.

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
