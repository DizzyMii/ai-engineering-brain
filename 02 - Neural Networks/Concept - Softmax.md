---
tags: [concept, domain/neural-networks, level/core]
aliases: [softmax function, normalized exponential, softargmax]
summary: "Logits to probabilities. Shift-invariant, saturating, overflow-prone — only the max-subtracted form is numerically safe."
---

# Concept - Softmax
> **One-paragraph hook:** Softmax converts a vector of unnormalized scores (logits) into a probability distribution, and it sits at every output layer of every classifier and language model — plus inside every attention head, once per row of the score matrix. It looks like a two-line function; nearly everything an engineer needs to know about it lives in its pathologies: it overflows if implemented naively, its gradient dies exactly when the model is confident, and it structurally caps the expressivity of an LM's output distribution.

## The mechanism

$$\mathrm{softmax}(z)_i = \frac{e^{z_i}}{\sum_{j=1}^{C} e^{z_j}}$$

The defining algebraic fact: softmax is **invariant to adding a constant** to every logit, since $e^{z_i + c} / \sum_j e^{z_j + c} = e^{z_i}/\sum_j e^{z_j}$. The mandatory numerically stable form exploits this by subtracting $m = \max_j z_j$ before exponentiating. This is not optional: $e^x$ overflows fp32 at $x > \ln(3.4\times10^{38}) \approx 88.7$ and fp16 at $x > \ln(65504) \approx 11.09$ — and trained LMs routinely produce logits in the 10–30 range, so a naive fp16 softmax NaNs on the first real batch.

**log-softmax** is computed via the log-sum-exp identity (see [[Snippet - The Log-Sum-Exp Trick]]), never as `log(softmax(x))`:

$$\log \mathrm{softmax}(z)_i = z_i - \mathrm{LSE}(z), \qquad \mathrm{LSE}(z) = m + \log \sum_j e^{z_j - m}$$

PyTorch fuses `log_softmax + nll_loss` into `F.cross_entropy` for exactly this stability reason — hand-rolling the composition is a classic NaN source (see [[Concept - Loss Functions for Neural Networks]]).

**The Jacobian** is $\partial s_i / \partial z_j = s_i(\delta_{ij} - s_j)$ — a rank-deficient matrix (rows sum to 0, another face of shift invariance). Composed with cross-entropy the whole thing collapses to the famously clean gradient $\partial L/\partial z = \hat{y} - y$, which is the reason softmax+CE dominates classification and why the fused pair backpropagates cheaply (see [[Concept - Backpropagation]]).

**Temperature** divides logits before the exp: $\mathrm{softmax}(z/T)$. $T \to 0$ approaches argmax (one-hot), $T \to \infty$ approaches uniform. It is one knob wearing three hats: sampling sharpness at inference, soft-target smoothing in distillation, and calibration post-hoc (temperature scaling).

## In practice

- **LM head:** softmax over the vocabulary — 50,257 entries for GPT-2, ~128K for Llama 3. At V=128K the softmax + sampling step is a nontrivial slice of per-token decode cost.
- **Attention:** every row of $QK^\top/\sqrt{d_k}$ goes through softmax — the [[Concept - Attention Mechanism]] is softmax applied $N \times h$ times per layer, which is why fused/online softmax kernels matter so much.
- **Sampling:** temperature, top-k, and top-p all operate on or after the softmax; see [[Concept - Sampling and Decoding Parameters]]. The same $T$ produces the soft targets in [[Concept - Knowledge Distillation]] (Hinton et al. 2015 used $T$ in the 2–5 range for most experiments).
- **Kernels:** online softmax (Milakov & Gimelshein 2018) computes the running max and running sum in a single pass, enabling tiled, fused implementations — the numerical trick FlashAttention is built on. See [[Snippet - Fused Softmax Kernel in Triton]].

## Failure modes

- **Overflow NaN.** Symptom: NaN loss on step ~1, especially under fp16. Cause: naive $e^{z}$ without max subtraction, or `log(softmax(...))`. Detection: `assert torch.isfinite(loss)`; check whether the logits' max exceeds ~11 in half precision. Fix: stable form, fused cross-entropy, compute the softmax in fp32.
- **Saturation and logit drift.** Once one logit dominates, the winning probability pins near 1 and the softmax gradient $s_i(1-s_i)$ goes to ~0 — nothing in the loss pushes the logits back down, so their scale drifts upward through training. In the LM head this produces unbounded logit growth (remedies: label smoothing, weight decay on the head, or the z-loss auxiliary penalty $\sim 10^{-4}\log^2 Z$ used in PaLM — see [[Concept - z-loss and Logit Soft-Capping]]). In attention the same saturation appears as near-one-hot attention rows — see [[Concept - Attention Entropy Collapse]] and the related [[Concept - Attention Sinks]] phenomenon, where the shift-invariant, must-sum-to-1 structure forces heads to park probability mass somewhere even when no token deserves it.
- **The softmax bottleneck.** Factoring an $N \times V$ log-probability matrix through a $d$-dimensional hidden state caps its rank at roughly $d$ (Yang et al. 2018), structurally limiting which output distributions the model can express at all — the full story is in [[Concept - The Softmax Bottleneck]].

## The non-obvious

Logits are only defined **up to an additive constant per row**. A raw logit value of 14.2 means nothing in isolation — only differences between logits in the same row carry information. Practical consequences: you cannot compare absolute logit magnitudes across models, checkpoints, or even positions; the partition function $\log Z$ is a free parameter that wanders during training unless something (z-loss, weight decay) pins it; and interpretability tools that read logits, like [[Concept - The Logit Lens]], are only meaningful about relative structure. Folklore corollary: when two implementations "match" on probabilities but differ on logits by a constant per row, they are the same model — chasing that diff is a waste of an afternoon.

## Connections

- [[Concept - Loss Functions for Neural Networks]] — the softmax+cross-entropy pair and its $\hat{y}-y$ gradient is the reason this function owns classification.
- [[Concept - Entropy and Cross-Entropy]] — the information-theoretic ground truth for what the softmax output distribution is scored against.
- [[Concept - Backpropagation]] — the Jacobian structure here is a worked example of how fused local gradients keep the backward pass cheap.
- [[Snippet - The Log-Sum-Exp Trick]] — the exact numerical recipe every stable softmax/log-softmax reduces to.
- [[Concept - Sampling and Decoding Parameters]] — temperature/top-k/top-p are all post-softmax (or logit-space) manipulations of this distribution at inference.
- [[Concept - Attention Mechanism]] — attention is softmax applied per score-matrix row; its stability and saturation issues inherit directly from here.
- [[Concept - Knowledge Distillation]] — distillation's soft targets are just this function run at elevated temperature.
- [[Concept - Attention Sinks]] — the must-sum-to-1 constraint is the mechanistic root of sink tokens absorbing surplus attention mass.
- [[Concept - Attention Entropy Collapse]] — the saturation pathology, playing out inside attention heads at scale.
- [[Concept - The Softmax Bottleneck]] — the rank-cap consequence of factoring log-probs through a $d$-dim hidden state.
- [[Concept - z-loss and Logit Soft-Capping]] — the production-grade fixes for the logit-drift failure mode described above.
- [[Concept - The Logit Lens]] — reads intermediate states through the LM head; only valid because of (and limited by) logit shift invariance.
- [[Snippet - Fused Softmax Kernel in Triton]] — what the mechanism looks like when written for SRAM residency with the online-softmax trick.

## Sources

- Bridle (1990) — "Probabilistic Interpretation of Feedforward Classification Network Outputs." Coined "softmax" and gave the probabilistic reading.
- Hinton et al. (2015) — "Distilling the Knowledge in a Neural Network." Temperature-scaled softmax as soft distillation targets.
- Milakov & Gimelshein (2018) — "Online normalizer calculation for softmax." The one-pass max/sum trick behind fused and Flash-style kernels.
- Yang et al. (2018) — "Breaking the Softmax Bottleneck." The rank-cap argument on the output distribution.
- Chowdhery et al. (2022) — PaLM. Introduced the z-loss ($10^{-4}\log^2 Z$) to control softmax logit drift at scale.
- Xiao et al. (2023) — "Efficient Streaming Language Models with Attention Sinks." The sum-to-1 constraint's downstream consequence in attention.
