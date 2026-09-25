---
tags: [concept, domain/foundations, level/core]
aliases: [cross-entropy, Shannon entropy, perplexity, bits-per-byte, NLL]
summary: "Entropy is optimal code length; cross-entropy = entropy + KL is the LM loss; perplexity and bits-per-byte are its exchange rates."
---

# Concept - Entropy and Cross-Entropy

> **One-paragraph hook:** Essentially every language model ever shipped was trained on cross-entropy loss, and perplexity, its exponential, is the number pretraining teams stare at for months. Both come from coding theory. They measure, in bits or nats, how badly a model's probability estimates compress reality. Read that way, "the loss went from 2.11 to 2.07" has physical meaning instead of being numerology.

## The mechanism

**Entropy.** For a distribution $p$ over symbols, the surprisal of outcome $x$ is $-\log p(x)$, and entropy is its expectation:

$$H(p) = -\sum_x p(x) \log p(x)$$

Shannon's source coding theorem (Shannon 1948) says $H(p)$ is the minimum average code length for symbols drawn from $p$: the hard floor for lossless compression. The log base sets the unit, bits for $\log_2$ and nats for $\ln$ (1 nat ≈ 1.443 bits). A uniform distribution over $K$ outcomes maximizes it at $\log K$. A point mass has zero.

**Cross-entropy.** $H(p, q) = -\sum_x p(x) \log q(x)$ is the average code length when the data comes from $p$ but you built the code for $q$. The identity everything hangs on:

$$H(p, q) = H(p) + D_{KL}(p \,\|\, q) \;\ge\; H(p)$$

The excess over the floor is the [[Concept - KL Divergence]] from truth to model, so cross-entropy is minimized iff $q = p$. Any cross-entropy loss splits into "how random is the data" (irreducible) plus "how wrong is my model" (reducible).

**As a training loss.** With one-hot targets, $H(\text{onehot}, q) = -\log q(\text{correct token})$, the negative log-likelihood. Cross-entropy training *is* [[Concept - Maximum Likelihood Estimation]]. The gradient with respect to the logits $z$ is the famously clean

$$\frac{\partial L}{\partial z} = \text{softmax}(z) - \text{onehot}$$

It's bounded, smooth, and doesn't saturate like MSE-on-probabilities, which is why the [[Concept - Softmax]]-plus-cross-entropy pairing is universal.

**Exchange rates.** Perplexity $= e^{H}$ (cross-entropy in nats) is the effective branching factor: a model at 20 ppl is, per token, as uncertain as a fair 20-sided die. Bits-per-byte divides total loss in bits by total *bytes* of text, so results compare across tokenizers. Worked conversion: 2.08 nats/token = 3.0 bits/token, and at 4 bytes/token average that's 0.75 BPB.

## In practice

- **Real magnitudes.** Shannon's human-subject experiments put printed English at roughly 0.6–1.3 bits/character (Shannon 1951). Strong LLMs on clean English web text land inside that band. The Chinchilla loss fit $L(N, D) = E + A/N^{0.34} + B/D^{0.28}$ estimated the irreducible term at $E \approx 1.69$ nats/token *in its tokenizer* (Hoffmann et al. 2022). That's $H(p)$ measured empirically, and it's why [[Concept - Scaling Laws]] curves flatten toward an asymptote above zero.
- **The tokenizer trap.** Cross-entropy and perplexity are *per token*. A tokenizer that chops text finer makes more, easier tokens, so per-token loss drops while total bits stay roughly constant. Comparing perplexities across different tokenizers is meaningless, yet it has shown up in real leaderboard comparisons. Bits-per-byte (used by The Pile, Gao et al. 2020) is the honest cross-tokenizer unit; the old WikiText convention of per-word normalization existed for the same reason. The tokenizer itself comes from [[Concept - Byte-Pair Encoding]], so loss and tokenizer are never independent choices.
- **Numerics.** Compute cross-entropy from logits via log-softmax with [[Snippet - The Log-Sum-Exp Trick]]. Never softmax-then-log, or a probability clamped to zero feeds $\log(0) = -\infty$. Keep the loss reduction in fp32 even in a bf16 model ([[Concept - Floating Point for Deep Learning]], [[Gotchas - Numerical Stability]]).
- **Label smoothing** replaces the one-hot target with $(1-\epsilon)\cdot\text{onehot} + \epsilon/K$ (typically $\epsilon = 0.1$; Szegedy et al. 2016). It bounds the logits, since a pure one-hot target rewards driving them to infinity, and improves calibration. The cost: a worse distillation teacher (Müller et al. 2019).

## Failure modes

- **NaN loss from log(0).** Cause: softmax-then-log on underflowed probabilities. The loss goes NaN immediately or a few steps in. Fix it with fused from-logits cross-entropy, and catch it with finite-value asserts on logits.
- **Cross-tokenizer perplexity comparisons.** A model "beats" another on ppl while losing on every downstream eval. Check the tokenizers match before believing any perplexity delta; renormalize to BPB if not.
- **Nats/bits confusion.** 2.08 nats and 3.0 bits are the same loss. Mix units in a comparison and you silently misstate model quality by 44%. Label the unit, every time.
- **Misreading the floor.** Loss plateaus near the data's irreducible entropy and someone declares training "stalled." The floor belongs to the data (and its noise level), so no model can get past it by definition. Grinding against it means improve the *data*; training longer won't help.

## The non-obvious

A language model is literally a lossless compressor. Total cross-entropy in nats × 1.443 / 8 equals the size in bytes that arithmetic coding driven by the model's next-token distribution would achieve (Delétang et al. 2023 made this literal). It's the cleanest sanity check on loss numbers: a 0.75 BPB model compresses text to ~9.4% the size of its UTF-8 bytes. If a claimed loss implies better compression than the best known compressors for that data, the claim is contaminated or broken.

Second, and subtler: at LLM vocab sizes label smoothing raises the achievable loss floor a lot. With $\epsilon = 0.1$ and $K = 32{,}000$, the minimum cross-entropy is ~1.36 nats *before the model gets anything wrong*. That's a big reason modern LLM pretraining dropped it. It wrecks the interpretability of the loss curve to fix a logit-divergence problem that weight decay and z-loss already handle.

## Connections

- [[Concept - KL Divergence]] — the "excess" term in cross-entropy; the identity $H(p,q) = H(p) + D_{KL}(p\|q)$ is the bridge between the two notes.
- [[Concept - Maximum Likelihood Estimation]] — cross-entropy with one-hot targets *is* NLL minimization; the statistical frame for why this loss is principled.
- [[Concept - Softmax]] — the layer that turns logits into $q$; its pairing with cross-entropy yields the clean softmax-minus-onehot gradient.
- [[Snippet - The Log-Sum-Exp Trick]] — the runnable stable implementation of everything in the numerics paragraph.
- [[Gotchas - Numerical Stability]] — the broader catalog the log(0) and fp32-reduction rules come from.
- [[Concept - Floating Point for Deep Learning]] — why the loss and its reductions stay in fp32 under mixed precision.
- [[Concept - Byte-Pair Encoding]] — the tokenizer determines what "per token" means, hence the entire cross-tokenizer comparability problem.
- [[Concept - Scaling Laws]] — loss curves are cross-entropy curves; their irreducible asymptote $E$ is this note's $H(p)$ measured empirically.

## Sources

- Shannon (1948) — "A Mathematical Theory of Communication" — entropy as optimal code length; the source coding theorem.
- Shannon (1951) — "Prediction and Entropy of Printed English" — the 0.6–1.3 bits/char human estimates.
- Hoffmann et al. (2022) — "Training Compute-Optimal Large Language Models" — the fitted irreducible loss $E \approx 1.69$ nats/token.
- Gao et al. (2020) — "The Pile" — bits-per-byte as the cross-tokenizer evaluation unit.
- Szegedy et al. (2016) — "Rethinking the Inception Architecture" — label smoothing introduced.
- Müller et al. (2019) — "When Does Label Smoothing Help?" — calibration benefit, distillation cost.
- Delétang et al. (2023) — "Language Modeling Is Compression" — the LM-as-arithmetic-coder equivalence made empirical.
