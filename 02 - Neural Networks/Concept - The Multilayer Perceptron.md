---
tags: [concept, domain/neural-networks, level/surface]
aliases: [MLP, feedforward network, fully connected network, dense layers]
summary: "Stacked affine-plus-nonlinearity layers — the base neural network, and literally the FFN block inside every transformer."
---

# Concept - The Multilayer Perceptron

> **One-paragraph hook:** The multilayer perceptron is the minimal neural network: a stack of matrix multiplies, each followed by a pointwise nonlinearity. Every architecture you will ever debug — CNN, LSTM, transformer — is this object with structure bolted on, and the position-wise FFN that holds roughly two-thirds of a transformer's non-embedding parameters *is* an MLP, unchanged. Understand the MLP's math, parameter count, and failure modes and you have the substrate for everything downstream.

## The mechanism

One layer computes an affine map followed by a nonlinearity:

$$h = \sigma(Wx + b), \qquad W \in \mathbb{R}^{d_\text{out} \times d_\text{in}},\; b \in \mathbb{R}^{d_\text{out}}$$

where $\sigma$ is a pointwise nonlinearity (see [[Concept - Activation Functions]]). A network is $L$ of these composed:

```
x ──▶ [W1x+b1] ──▶ σ ──▶ [W2h1+b2] ──▶ σ ──▶ [W3h2+b3] ──▶ logits
        layer 1            layer 2            output head
```

**The nonlinearity is the entire source of expressivity.** Remove $\sigma$ and the stack collapses algebraically: $W_3(W_2(W_1x)) = (W_3 W_2 W_1)x$, a single linear map, no matter how many layers you stack. This is not a theoretical curiosity — `nn.Sequential(nn.Linear(d, h), nn.Linear(h, c))` with a forgotten activation runs without error, trains without warning, and silently caps the model at linear-classifier capacity.

**Why a hidden layer matters — XOR.** A single perceptron draws one hyperplane, and XOR's four points are not linearly separable. Minsky and Papert made this limitation precise in *Perceptrons* (1969), and the result — widely read as "neural networks can't do anything interesting" — helped freeze the field for a decade. One hidden layer solves XOR trivially (two hyperplanes, then combine), and the rediscovery that hidden layers are trainable via [[Concept - Backpropagation]] is the historical hinge that revived the field in 1986.

**Universal approximation, and its fine print.** One hidden layer of sufficient width can approximate any continuous function on a compact set to arbitrary accuracy (Cybenko 1989 for sigmoids; Hornik 1991 for general non-polynomial activations). The fine print is that "sufficient width" can be exponential in the input dimension. Depth is the efficient axis: there exist functions computable by a deep network of modest size that require exponentially many units in any shallow network (Telgarsky 2016; Eldan-Shamir 2016). Universal approximation says nothing about *learnability* either — it guarantees a good network exists, not that gradient descent finds it.

**Counting parameters and FLOPs.** A layer has $d_\text{in} \cdot d_\text{out} + d_\text{out}$ parameters; the weight matrix dominates and the bias is negligible (0.1% of a 1024×1024 layer). The forward pass costs ~2 FLOPs per parameter per input token — one multiply and one add per weight, because the layer is a [[Concept - Matrix Multiplication as the Atom of Deep Learning|matrix multiplication]] at heart. This "forward ≈ 2 × params" rule is the base unit of all compute accounting up through scaling-law arithmetic.

## In practice

The MLP survives inside every modern architecture as the transformer's position-wise FFN: expand by 4×, apply the nonlinearity, project back. In GPT-2 small ($d_\text{model}=768$) that is $768 \to 3072 \to 768$, about 4.7M parameters per block — versus $4d^2 \approx 2.4$M for the attention projections, i.e. the MLP is ~2/3 of each block. Everything in this note — the collapse-without-activation bug, the 2-FLOPs-per-param rule, the width/capacity tradeoff — transfers verbatim to [[Deep Dive - The Transformer]]; the modern gated variants of that block are covered in [[Concept - Feed-Forward Networks and GLU Variants]].

As a standalone model, an MLP with 1-3 hidden layers of width 128-1024 is still the right first tool for tabular features, small classification heads, learned gating/routing functions, and reward-model heads. It is trained like everything else: pick an objective from [[Concept - Loss Functions for Neural Networks]], compute gradients with backpropagation, iterate [[Concept - The Training Loop]].

Width and depth are the capacity knobs: more of either lets the network fit more complex functions, and also fit noise. The surface intuition is the classical bias-variance tradeoff — but note that heavily overparameterized networks routinely violate the classical picture and generalize anyway; that story lives in [[Concept - Generalization in Deep Learning]].

## Failure modes

- **Silent linear collapse.** Missing activation between Linear layers (or an activation applied only to the last layer). Symptom: training converges but plateaus at the accuracy of a logistic-regression baseline. Detection: always run the linear baseline first; if the MLP can't beat it, inspect the module list before touching hyperparameters.
- **Width starvation / capacity misallocation.** A hidden layer narrower than the intrinsic dimensionality of the task bottlenecks everything after it; no amount of depth downstream recovers information destroyed early. Symptom: train loss floors well above zero even when overfitting a tiny batch.
- **Trusting universal approximation.** "An MLP can represent it" gets read as "an MLP will learn it." Parity-like functions and sharp discontinuities are representable but brutal for SGD. If a shallow-wide net stalls, depth (or a different inductive bias entirely — a [[Concept - Convolutional Neural Networks|CNN]] for images) is the fix, not more width.

## The non-obvious

The MLP is not a pedagogical stepping stone you graduate from — it is where most of a frontier model's parameters and FLOPs live. When interpretability work talks about "MLP neurons" storing facts, when serving math accounts for FFN FLOPs, when MoE swaps the FFN for routed experts, they are all talking about this exact object. Practitioners who internalized the humble $\sigma(Wx+b)$ debug transformer FFN issues by inspection; those who skipped it treat two-thirds of the model as a black box.

## Connections

- [[Concept - Backpropagation]] — how the gradients that train this stack are actually computed; the up-link for *how it learns*.
- [[Concept - Activation Functions]] — the $\sigma$ that supplies all the expressivity; its saturation pathologies are the MLP's training pathologies.
- [[Concept - The Training Loop]] — the procedure that turns the forward pass and a loss into weight updates.
- [[Concept - Loss Functions for Neural Networks]] — the objective the output head is trained against; choice of loss shapes the gradients the MLP receives.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — each layer is one matmul; all FLOP and hardware reasoning reduces to this.
- [[Deep Dive - The Transformer]] — the position-wise FFN block is this note's MLP with a 4× expansion; ~2/3 of block parameters.
- [[Concept - Feed-Forward Networks and GLU Variants]] — the modern gated evolutions (SwiGLU et al.) of the transformer's MLP block.
- [[Concept - Generalization in Deep Learning]] — why the capacity story here (width/depth → overfitting) is incomplete for large networks.
- [[Concept - Convolutional Neural Networks]] — what you reach for when the MLP's lack of spatial inductive bias makes it the wrong tool.

## Sources

- Minsky & Papert (1969) — *Perceptrons*. Proved single-layer limits (XOR); the book that stalled the field.
- Rumelhart, Hinton & Williams (1986) — Learning representations by back-propagating errors. Made hidden layers trainable and revived the MLP.
- Cybenko (1989) — Approximation by superpositions of a sigmoidal function. Universal approximation for one hidden layer.
- Hornik (1991) — Approximation capabilities of multilayer feedforward networks. Generalized universal approximation beyond sigmoids.
- Telgarsky (2016) — Benefits of depth in neural networks. Depth separation: deep-small beats shallow-exponential.
- Eldan & Shamir (2016) — The power of depth for feedforward neural networks. A concrete function easy for depth 3, exponential for depth 2.
