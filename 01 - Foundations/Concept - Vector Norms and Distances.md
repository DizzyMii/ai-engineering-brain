---
tags: [concept, domain/foundations, level/surface]
aliases: [Lp norms, cosine similarity, Euclidean distance, spectral norm]
summary: "Lp and matrix norms and the distances built from them: what each measures, where each is used, and how each silently misleads."
---

# Concept - Vector Norms and Distances

> **One-paragraph hook:** Every regularizer, clipping rule, retrieval metric, and stability bound in deep learning is a choice of norm — and each choice smuggles in an assumption about what "big" and "close" mean. Weight decay assumes L2, retrieval assumes cosine, Lipschitz bounds assume spectral. Picking the wrong measuring stick doesn't throw an error; it silently penalizes, ranks, or clips the wrong thing, and the model just gets quietly worse.

## The mechanism

**The Lp family.** For a vector $x \in \mathbb{R}^d$:

$$\|x\|_p = \Big(\sum_i |x_i|^p\Big)^{1/p}$$

$p=1$ is Manhattan (sum of absolute values), $p=2$ is Euclidean, $p\to\infty$ gives $\|x\|_\infty = \max_i |x_i|$. The behavior differences are geometric, visible in the unit balls. The L2 ball is round and rotation-invariant — the only rotation-invariant Lp norm, which is why L2 is the default whenever no coordinate system is privileged. The L1 ball is a cross-polytope whose corners sit exactly on the coordinate axes: a loss's level sets almost always first touch that ball at a corner, where coordinates are *exactly* zero. That is why an L1 penalty induces exact sparsity while an L2 penalty only shrinks every coordinate proportionally and never zeroes one out. The L∞ ball is a hypercube — it bounds the worst single coordinate, which is why adversarial perturbation budgets are usually stated in L∞.

**Cosine similarity and its L2 identity.**

$$\cos(a,b) = \frac{a \cdot b}{\|a\|_2\,\|b\|_2}, \qquad \|a-b\|_2^2 = 2 - 2\cos(a,b) \;\text{ for unit vectors}$$

So after L2 normalization, cosine ranking and Euclidean ranking are *the same ranking*. Cosine deliberately discards magnitude. That is correct when magnitude is nuisance (document length) and wrong when magnitude carries signal — in word2vec-style embeddings, vector norm tracks token frequency and specificity (Schakel & Wilson 2015), and throwing it away throws away information. The dot product itself is the inner loop of every matmul — see [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — so everything here is also a statement about what networks compute internally.

**Matrix norms** — three ways to size a weight matrix $W$, all read directly off the [[Concept - Singular Value Decomposition]] $W = U\Sigma V^\top$ with singular values $\sigma_1 \ge \sigma_2 \ge \dots$:

| Norm | Definition | Meaning |
|---|---|---|
| Frobenius $\|W\|_F$ | $\sqrt{\sum_{ij} w_{ij}^2} = \sqrt{\sum_i \sigma_i^2}$ | Entrywise L2; total "energy" of the map |
| Spectral $\|W\|_2$ | $\sigma_{\max}$ | Worst-case gain; the Lipschitz constant of $x \mapsto Wx$ |
| Nuclear $\|W\|_*$ | $\sum_i \sigma_i$ | L1 on the spectrum; the convex surrogate for rank |

The nuclear norm is to rank what the L1 norm is to sparsity — the same corner-touching geometry, applied to singular values.

## In practice

- **L2**: weight decay is an L2 penalty (decoupled from the adaptive rescaling in [[Concept - Adam and AdamW]]); gradient clipping in LLM training clips by the *global* L2 norm — concatenate every gradient into one vector, clip its norm to a threshold (1.0 in GPT-3/Llama-class recipes). Global-norm clipping preserves the update direction; per-tensor clipping does not.
- **Cosine**: the default for embedding retrieval ([[Concept - Embedding Models]]) and the vector half of hybrid ranking ([[Concept - Hybrid Search and Reciprocal Rank Fusion]]). FAISS/pgvector inner-product indexes only compute cosine if *you* normalized the vectors first.
- **Spectral**: spectral normalization (Miyato et al. 2018) divides $W$ by $\sigma_{\max}$, estimated with a single power-iteration step per update, pinning the discriminator's Lipschitz constant near 1 — one of the few GAN stabilizers that reliably worked.
- **Frobenius**: the Eckart–Young theorem says the best rank-$k$ approximation error is $\sqrt{\sum_{i>k}\sigma_i^2}$ in Frobenius norm ($\sigma_{k+1}$ in spectral) — the yardstick behind every low-rank compression argument.
- **Numerical care**: the naive $\sqrt{\sum x_i^2}$ overflows fp32 when any $|x_i| \gtrsim 1.8\times10^{19}$ and fp16 when any $|x_i| \ge 256$ (since $256^2 = 65536 > 65504$, the fp16 max — see [[Concept - Floating Point for Deep Learning]]). The hypot trick: factor out $m = \max_i |x_i|$ and compute $m \cdot \|x/m\|$. Long dot products accumulate rounding error growing roughly like $\sqrt{k}\,\varepsilon$ over a length-$k$ reduction — accumulate in fp32 ([[Gotchas - Numerical Stability]]).

## Failure modes

- **Inner-product index, unnormalized vectors.** You configured the ANN index for inner product intending cosine and nobody normalized. Ranking is silently dominated by vector magnitude — frequent/long documents win regardless of relevance. Detection: histogram your embedding norms; a wide spread on an IP index means you're ranking by length.
- **Train/serve normalization mismatch.** The embedding model was trained and evaluated with L2-normalized outputs; the query path skips normalization. Recall quietly degrades with no errors anywhere. Detection: a golden-set retrieval eval in CI catches it in one run.
- **Distance concentration in high dimension.** As $d$ grows, the gap between nearest and farthest neighbor distances collapses (Beyer et al. 1999), so raw L2 kNN loses contrast — the full story lives in [[Concept - The Geometry of High-Dimensional Spaces]].
- **fp16 norm/distance overflow** on perfectly reasonable activations (any component ≥ 256). Detection: `inf` appearing in norm computations under mixed precision.

## The non-obvious

"Should I use cosine or Euclidean distance?" is a non-question for normalized embeddings — the identity above makes them the same ranking. The *real* decision is whether to normalize at all, i.e., whether magnitude is signal or noise for your data. Most teams who report that "switching from L2 to cosine improved retrieval" actually just added normalization — and if magnitude did carry signal, they paid for the cleanup without noticing.

## Connections

- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the dot product measured here is the primitive that matmuls execute billions of times per forward pass.
- [[Concept - Singular Value Decomposition]] — spectral, Frobenius, and nuclear norms are all functions of the singular values; the SVD is where matrix norms come from.
- [[Concept - The Geometry of High-Dimensional Spaces]] — why these distances behave counterintuitively (concentration, near-orthogonality) once $d$ is in the hundreds.
- [[Concept - Floating Point for Deep Learning]] — the overflow thresholds (65504 in fp16) that make naive norm computation dangerous.
- [[Gotchas - Numerical Stability]] — the accumulated-rounding and cancellation pathologies of the reductions inside norms and dot products.
- [[Concept - Embedding Models]] — trained specifically to make cosine on their output space mean semantic similarity; the norm/normalization contract is part of the model card.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — combines cosine-space rankings with lexical rankings; wrong norm handling on the vector side poisons the fusion.
- [[Concept - Adam and AdamW]] — decoupled weight decay is the L2 penalty done right under adaptive optimizers; clipping by global L2 norm lives in the same update step.

## Sources

- Eckart & Young (1936) — Low-rank approximation optimality in Frobenius/spectral norm; the foundation of every compression bound.
- Beyer et al. (1999) — "When Is 'Nearest Neighbor' Meaningful?" — distance concentration in high dimensions.
- Miyato et al. (2018) — "Spectral Normalization for Generative Adversarial Networks" — spectral norm as a practical Lipschitz control.
- Schakel & Wilson (2015) — "Measuring Word Significance using Distributed Representations of Words" — embedding norm correlates with word frequency/significance.
