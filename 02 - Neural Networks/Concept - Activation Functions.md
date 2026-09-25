---
tags: [concept, domain/neural-networks, level/core]
aliases: [nonlinearities, ReLU, GELU, SiLU, Swish]
summary: "Pointwise nonlinearities and their gradients: why sigmoid stalled depth, ReLU dies, and GELU/SiLU won transformers by convention."
---

# Concept - Activation Functions
> **One-paragraph hook:** The activation function is the pointwise nonlinearity between the affine layers of a [[Concept - The Multilayer Perceptron]], and it is the *entire* source of a network's expressivity: a stack of linear maps with no nonlinearity collapses to one linear map. Trainable depth largely followed activation derivatives. Sigmoid's 0.25-max derivative walled off depth before ~2010, ReLU's exact 0-or-1 derivative broke the wall open, and every modern transformer ships the smooth GELU/SiLU family, more by convention than mechanism.

## The mechanism

[[Concept - Backpropagation]] multiplies each layer's upstream gradient elementwise by $f'(\text{pre-activation})$ on the way back. Whatever that derivative does across depth, the gradient does exponentially.

| Function | $f(x)$ | $f'(x)$ | max $f'$ | Pathology |
|---|---|---|---|---|
| Sigmoid | $1/(1+e^{-x})$ | $f(1-f)$ | 0.25 | saturates both tails, not zero-centered |
| Tanh | $\tanh x$ | $1-f^2$ | 1.0 | saturates both tails |
| ReLU | $\max(0,x)$ | $\{0, 1\}$ | 1 | dying units |
| Leaky ReLU | $\max(\alpha x, x)$, $\alpha\approx0.01$ | $\{\alpha, 1\}$ | 1 | mostly fixes dying; marginal gains |
| GELU | $x\,\Phi(x)$ | $\Phi(x) + x\phi(x)$ | ≈1.1 | exact-vs-tanh variant mismatch |
| SiLU / Swish | $x\,\sigma(x)$ | $\sigma(x)(1 + x(1-\sigma(x)))$ | ≈1.1 | none major; slightly costlier |

**Saturation kills depth.** Sigmoid's derivative peaks at 0.25 and decays to 0 in both tails, so a 10-layer sigmoid stack shrinks gradients by at worst $0.25^{10} \approx 10^{-6}$ before any weight matrix gets a say. That compounding is the core of [[Concept - Vanishing and Exploding Gradients]] and why deep nets wouldn't train before ~2010.

**ReLU** ($\max(0,x)$, Nair & Hinton 2010; Glorot et al. 2011) has derivative 1 on the active half: gradients pass through undiminished, with no positive-side saturation at any magnitude. It also outputs true zeros (~50% of units at init with symmetric inputs), which is real sparsity. The price is the **dying ReLU** absorbing state. One oversized update pushes a unit's pre-activation negative for the whole data distribution, its derivative becomes 0 for every example, and no gradient reaches it again. It's dead for good. He init's factor-of-2 variance compensates for ReLU zeroing half the activation variance (see [[Concept - Weight Initialization]]).

**The leaky family** (Leaky ReLU, PReLU, ELU, SELU) adds a negative-side slope so gradients stay alive. Gains over plain ReLU are usually marginal. SELU (Klambauer et al. 2017) is the exception: self-normalizing, but only with LeCun init and no normalization layers.

**GELU** $x\Phi(x)$ (Hendrycks & Gimpel 2016) and **SiLU/Swish** $x\sigma(x)$ (Ramachandran et al. 2017) are smooth and non-monotonic, with a small negative dip before rising (GELU's minimum is ≈ −0.17 near $x \approx -0.75$). The derivative never hard-switches, and the dip lets units pass small negative signal instead of gating it off. GELU is the default in BERT and GPT-2. SiLU lives on inside SwiGLU in the LLaMA lineage.

## In practice

- **Transformers:** GELU in the FFN for the BERT/GPT-2 generation. For LLaMA and most modern LLMs, SwiGLU: $(\mathrm{SiLU}(xW_1) \odot xW_3)W_2$, with hidden size $\tfrac{8}{3}d$ to hold parameter count constant. Shazeer (2020) proposed the GLU variants and credited their success to "divine benevolence", i.e. the mechanism is unclear. See [[Concept - Feed-Forward Networks and GLU Variants]] and [[Deep Dive - The Transformer]].
- **The two GELUs.** Exact GELU computes $\Phi(x)$ via `erf`; the tanh approximation is $0.5x\left(1+\tanh\left[\sqrt{2/\pi}(x + 0.044715x^3)\right]\right)$. They differ by up to ~0.1%. GPT-2 shipped the tanh form and PyTorch's `nn.GELU` defaults to exact, a real trap when porting checkpoints or matching a reference numerically.
- **Squared ReLU** ($\max(0,x)^2$, from Primer, So et al. 2021) comes back periodically. ReLU's true zeros also underpin activation-sparsity tricks in efficient inference.
- **Placement:** an activation follows each affine layer except the output. There the "nonlinearity" is [[Concept - Softmax]], a normalizing map over the whole vector and not a pointwise function. Norm layers sit next to activations and their ordering matters (see [[Concept - RMSNorm and LayerNorm]]).

## Failure modes

- **Dying ReLU.** Symptom: a layer's post-activation output is >90% zeros and stays there, and effective capacity shrinks silently. Cause: too-large LR or bad init pushing pre-activations permanently negative. Detection: track per-layer dead-unit fraction and activation histograms; put this on your default training dashboard. Fix: lower LR, He init, or switch to leaky/GELU.
- **Saturation (sigmoid/tanh).** Symptom: early-layer gradient norms orders of magnitude below late-layer norms, and loss crawls. Detection: activation histograms piled at the rails (0/1 for sigmoid, ±1 for tanh). Fix: ReLU-family activation, better init, normalization.
- **GELU variant mismatch.** Symptom: a ported model matches a reference to ~1e-3 but never exactly, and downstream logits drift. Cause: exact vs tanh GELU across frameworks. Detection: diff one FFN block's output on a fixed input before debugging anything else. Low-precision arithmetic adds to the confusion (see [[Concept - Floating Point for Deep Learning]]).

## The non-obvious

GELU's measured edge over ReLU is small and often within run-to-run noise. It stays the default largely by convention inherited from BERT/GPT-2, with no decisive mechanistic win. Whether your network trains is decided upstream: init scale, normalization and learning rate dominate. The corollary people learn the hard way: swapping activation functions is almost never the fix for a training problem, but activation *statistics* (dead fractions, saturation histograms) are among the best diagnostics for one.

## Connections

- [[Concept - The Multilayer Perceptron]] — the host structure; without the activation between affine layers the whole stack collapses to one linear map.
- [[Concept - Backpropagation]] — $f'$ multiplies into the backward pass per layer, which is why derivative shape decides trainability.
- [[Concept - Vanishing and Exploding Gradients]] — the depth-compounding pathology that saturating activations cause and ReLU-family ones mitigate.
- [[Concept - Weight Initialization]] — He init's factor of 2 is a direct correction for ReLU's variance halving; init and activation are one design decision.
- [[Concept - RMSNorm and LayerNorm]] — normalization keeps pre-activations in the activation's useful range, partially substituting for careful activation choice.
- [[Deep Dive - The Transformer]] — where GELU/SwiGLU actually live: the position-wise FFN block.
- [[Concept - Feed-Forward Networks and GLU Variants]] — the gated evolution of the FFN activation that won in modern LLMs.
- [[Concept - Softmax]] — the output layer's normalizing nonlinearity, categorically different from these pointwise functions.
- [[Concept - Dropout]] — the other pointwise train-time op in the block; both flip behavior between train and eval and both come off first when debugging.
- [[Concept - Floating Point for Deep Learning]] — erf-vs-tanh GELU and low-precision tails are where activation math meets numerics.

## Sources

- Nair & Hinton (2010) — "Rectified Linear Units Improve Restricted Boltzmann Machines." ReLU's first modern showing.
- Glorot, Bordes & Bengio (2011) — "Deep Sparse Rectifier Neural Networks." Made the case that ReLU unlocks trainable depth.
- Maas et al. (2013) — "Rectifier Nonlinearities Improve Neural Network Acoustic Models." Leaky ReLU.
- Hendrycks & Gimpel (2016) — "Gaussian Error Linear Units (GELUs)." The transformer era's default activation.
- Klambauer et al. (2017) — "Self-Normalizing Neural Networks." SELU and its init contract.
- Ramachandran et al. (2017) — "Searching for Activation Functions." Swish, found by architecture search.
- Shazeer (2020) — "GLU Variants Improve Transformer." SwiGLU and the "divine benevolence" honesty.
- So et al. (2021) — "Primer: Searching for Efficient Transformers for Language Modeling." Squared ReLU.
