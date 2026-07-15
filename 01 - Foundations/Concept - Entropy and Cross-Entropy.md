---
tags: [concept, domain/foundations, level/core]
aliases: [cross-entropy, Shannon entropy, perplexity, bits-per-byte, NLL]
summary: "Entropy is optimal code length; cross-entropy = entropy + KL is the LM loss; perplexity and bits-per-byte are its exchange rates."
---

# Concept - Entropy and Cross-Entropy

> **One-paragraph hook:** Cross-entropy is the loss on which essentially every language model ever shipped was trained, and perplexity — its exponential — is the number pretraining teams stare at for months. Both are coding-theory quantities: they measure, in bits or nats, how badly a model's probability estimates compress reality. Reading them that way turns "the loss went from 2.11 to 2.07" from numerology into a statement with physical meaning.

## The mechanism

**Entropy.** For a distribution $p$ over symbols, the surprisal of outcome $x$ is $-\log p(x)$, and entropy is its expectation:

$$H(p) = -\sum_x p(x) \log p(x)$$

Shannon's source coding theorem (Shannon 1948) makes this concrete: $H(p)$ is the minimum average code length for symbols drawn from $p$ — the hard floor for lossless compression. Units follow the log base: bits for $\log_2$, nats for $\ln$ (1 nat ≈ 1.443 bits). Uniform over $K$ outcomes maximizes it at $\log K$; a point mass has zero.

**Cross-entropy.** $H(p, q) = -\sum_x p(x) \log q(x)$ is the average code length when the data comes from $p$ but you built the code for $q$. The master identity:

$$H(p, q) = H(p) + D_{KL}(p \,\|\, q) \;\ge\; H(p)$$

The excess over the floor is exactly the [[Concept - KL Divergence]] from truth to model, so cross-entropy is minimized iff $q = p$. Every point of cross-entropy loss decomposes into "how random is the data" (irreducible) plus "how wrong is my model" (reducible).

**As a training loss.** With one-hot targets, $H(\text{onehot}, q) = -\log q(\text{correct token})$ — the negative log-likelihood, so cross-entropy training *is* [[Concept - Maximum Likelihood Estimation]]. The gradient with respect to the logits $z$ is the famously clean

$$\frac{\partial L}{\partial z} = \text{softmax}(z) - \text{onehot}$$

— bounded, smooth, and never saturating the way MSE-on-probabilities does, which is the practical reason the [[Concept - Softmax]]-plus-cross-entropy pairing is universal.

**Exchange rates.** Perplexity $= e^{H}$ (cross-entropy in nats) is the effective branching factor: a model at 20 ppl is, per token, as uncertain as a fair 20-sided die. Bits-per-byte divides total loss in bits by total *bytes* of text, making results comparable across tokenizers. Worked conversion: 2.08 nats/token = 3.0 bits/token; at 4 bytes/token average, that's 0.75 BPB.

## In practice

- **Real magnitudes.** Shannon's human-subject experiments put printed English at roughly 0.6–1.3 bits/character (Shannon 1951); strong LLMs on clean English web text land inside that band. The Chinchilla loss fit $L(N, D) = E + A/N^{0.34} + B/D^{0.28}$ estimated the irreducible term at $E \approx 1.69$ nats/token *in its tokenizer* (Hoffmann et al. 2022) — the empirical face of $H(p)$, and the reason [[Concept - Scaling Laws]] curves flatten toward an asymptote rather than zero.
- **The tokenizer trap.** Cross-entropy and perplexity are *per token*. A tokenizer that chops text finer produces more, easier tokens: per-token loss drops while total bits stay roughly constant. Comparing perplexities across different tokenizers is therefore meaningless — a mistake that has appeared in real leaderboard comparisons. Bits-per-byte (as used by The Pile — Gao et al. 2020) is the honest cross-tokenizer unit, and it's why per-word normalization was the old WikiText convention. The tokenizer itself is built by [[Concept - Byte-Pair Encoding]], so loss and tokenizer are never independent choices.
- **Numerics.** Always compute cross-entropy from logits via log-softmax using [[Snippet - The Log-Sum-Exp Trick]] — never softmax-then-log, or a clamped-to-zero probability feeds $\log(0) = -\infty$. Keep the loss reduction in fp32 even in a bf16 model ([[Concept - Floating Point for Deep Learning]], [[Gotchas - Numerical Stability]]).
- **Label smoothing** replaces the one-hot target with $(1-\epsilon)\cdot\text{onehot} + \epsilon/K$ (typically $\epsilon = 0.1$; Szegedy et al. 2016). It bounds the logits (a pure one-hot target rewards driving them to infinity) and improves calibration, though it degrades the model as a distillation teacher (Müller et al. 2019).

## Failure modes

- **NaN loss from log(0).** Softmax-then-log on underflowed probabilities. Symptom: loss goes NaN immediately or a few steps in. Fix: fused from-logits cross-entropy; detect with finite-value asserts on logits.
- **Cross-tokenizer perplexity comparisons.** Symptom: a model "beats" another on ppl while losing on every downstream eval. Check whether the tokenizers match before believing any perplexity delta; renormalize to BPB if not.
- **Nats/bits unit confusion.** 2.08 nats and 3.0 bits are the same loss; mixing units in a comparison silently misstates model quality by 44%. Always label the unit.
- **Misreading the floor.** Loss plateaus near the data's irreducible entropy and someone declares training "stalled." The floor is a property of the data (and its noise level), not of the model — pushing past it is definitionally impossible, and grinding against it is a signal to improve *data*, not to train longer.

## The non-obvious

A language model *is* a lossless compressor, not metaphorically: total cross-entropy in nats × 1.443 / 8 = the size in bytes that arithmetic coding driven by the model's next-token distribution would actually achieve (made literal in Delétang et al. 2023). This is the cleanest way to sanity-check loss numbers against reality — a 0.75 BPB model compresses text to ~9.4% the size of its UTF-8 bytes, and if a claimed loss implies compression better than the best known compressors for that data, the claim is contaminated or broken. Second, subtler: label smoothing raises the achievable loss floor by a lot at LLM vocab sizes — with $\epsilon = 0.1$ and $K = 32{,}000$ the minimum cross-entropy is ~1.36 nats *before the model gets anything wrong* — which is a big reason modern LLM pretraining dropped it: it destroys the interpretability of the loss curve while solving a logit-divergence problem that weight decay and z-loss already handle.

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
