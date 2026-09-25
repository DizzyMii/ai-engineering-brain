---
tags: [concept, domain/neural-networks, level/core]
aliases: [softmax function, normalized exponential, softargmax]
summary: "Logits to probabilities. Shift-invariant, saturating, overflow-prone — only the max-subtracted form is numerically safe."
---

# Concept - Softmax
> **One-paragraph hook:** Softmax turns a vector of unnormalized scores (logits) into a probability distribution. It sits at the output layer of every classifier and language model, and inside every attention head, once per row of the score matrix. It's a two-line function whose interest is all in its pathologies: implemented naively it overflows, its gradient dies right when the model is confident, and it caps how expressive an LM's output distribution can be.

## The mechanism

$$\mathrm{softmax}(z)_i = \frac{e^{z_i}}{\sum_{j=1}^{C} e^{z_j}}$$

Adding a constant to every logit changes nothing, since $e^{z_i + c} / \sum_j e^{z_j + c} = e^{z_i}/\sum_j e^{z_j}$. The stable form uses this to subtract $m = \max_j z_j$ before exponentiating, and it's mandatory. $e^x$ overflows fp32 at $x > \ln(3.4\times10^{38}) \approx 88.7$ and fp16 at $x > \ln(65504) \approx 11.09$. Trained LMs routinely produce logits in the 10–30 range, so a naive fp16 softmax NaNs on the first real batch.

Compute **log-softmax** through the log-sum-exp identity (see [[Snippet - The Log-Sum-Exp Trick]]), never as `log(softmax(x))`:

$$\log \mathrm{softmax}(z)_i = z_i - \mathrm{LSE}(z), \qquad \mathrm{LSE}(z) = m + \log \sum_j e^{z_j - m}$$

PyTorch fuses `log_softmax + nll_loss` into `F.cross_entropy` for stability; hand-rolling the pair is a classic NaN source (see [[Concept - Loss Functions for Neural Networks]]).

**The Jacobian** is $\partial s_i / \partial z_j = s_i(\delta_{ij} - s_j)$. It's rank-deficient (rows sum to 0), shift invariance again. Composed with cross-entropy it collapses to the famously clean gradient $\partial L/\partial z = \hat{y} - y$. That's why softmax+CE dominates classification and why the fused pair backpropagates cheaply (see [[Concept - Backpropagation]]).

**Temperature** divides the logits before the exp: $\mathrm{softmax}(z/T)$. As $T \to 0$ it approaches argmax (one-hot); as $T \to \infty$, uniform. One knob, three jobs: sampling sharpness at inference, soft-target smoothing in distillation, and post-hoc calibration (temperature scaling).

## In practice

- **LM head:** softmax over the vocabulary, 50,257 entries for GPT-2 and ~128K for Llama 3. At V=128K, softmax + sampling is a nontrivial slice of per-token decode cost.
- **Attention:** every row of $QK^\top/\sqrt{d_k}$ goes through softmax. The [[Concept - Attention Mechanism]] applies it $N \times h$ times per layer, so fused/online softmax kernels matter a lot.
- **Sampling:** temperature, top-k and top-p all act on or after the softmax; see [[Concept - Sampling and Decoding Parameters]]. The same $T$ produces the soft targets in [[Concept - Knowledge Distillation]] (Hinton et al. 2015 used $T$ in the 2–5 range for most experiments).
- **Kernels:** online softmax (Milakov & Gimelshein 2018) keeps a running max and sum in one pass, allowing the tiled, fused implementations FlashAttention is built on. See [[Snippet - Fused Softmax Kernel in Triton]].

## Failure modes

- **Overflow NaN.** Symptom: NaN loss on step ~1, especially under fp16. Cause: naive $e^{z}$ without max subtraction, or `log(softmax(...))`. Detection: `assert torch.isfinite(loss)`; in half precision, check whether the max logit exceeds ~11. Fix: stable form, fused cross-entropy, softmax computed in fp32.
- **Saturation and logit drift.** Once one logit dominates, the winning probability pins near 1 and the softmax gradient $s_i(1-s_i)$ goes to ~0. Nothing in the loss pushes the logits back down, so their scale drifts up. In the LM head that means unbounded logit growth (remedies: label smoothing, weight decay on the head, or PaLM's z-loss auxiliary penalty $\sim 10^{-4}\log^2 Z$; see [[Concept - z-loss and Logit Soft-Capping]]). In attention, the same saturation shows up as near-one-hot rows. See [[Concept - Attention Entropy Collapse]] and the related [[Concept - Attention Sinks]], where the shift-invariant, must-sum-to-1 structure forces heads to park probability mass somewhere even when no token deserves it.
- **The softmax bottleneck.** Factoring an $N \times V$ log-probability matrix through a $d$-dimensional hidden state caps its rank at roughly $d$ (Yang et al. 2018). That limits which output distributions the model can express at all; more is in [[Concept - The Softmax Bottleneck]].

## The non-obvious

Logits are defined only **up to an additive constant per row**. A raw logit of 14.2 means nothing by itself; only differences within a row carry information. You can't compare absolute logit magnitudes across models, checkpoints, or even positions. The partition function $\log Z$ is a free parameter that wanders during training unless something (z-loss, weight decay) pins it. Interpretability tools that read logits, like [[Concept - The Logit Lens]], only speak to relative structure. Folklore corollary: if two implementations match on probabilities but differ on logits by a constant per row, they're the same model, and chasing that diff wastes an afternoon.

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
