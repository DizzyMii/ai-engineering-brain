---
tags: [concept, domain/foundations, level/advanced]
aliases: [SVD, singular values, truncated SVD, low-rank approximation]
summary: "Every matrix is rotation → axis scaling → rotation; the scaling factors explain PCA, spectral norms, low-rank compression, and LoRA."
---

# Concept - Singular Value Decomposition

> **One-paragraph hook:** The SVD tells you what a linear map *actually does*, and unlike eigendecomposition it exists for every matrix, square or not. Half of applied ML sits on it: PCA, spectral norms, whitening, low-rank compression, and the whole premise of LoRA all come down to reading off singular values. When someone says "this weight matrix is effectively rank 40," the SVD is how they measured it.

## The mechanism

Any real $m \times n$ matrix factors as

$$A = U \Sigma V^\top$$

where $U \in \mathbb{R}^{m \times m}$ and $V \in \mathbb{R}^{n \times n}$ have orthonormal columns and $\Sigma$ is diagonal with singular values $\sigma_1 \ge \sigma_2 \ge \dots \ge 0$. Columns of $V$ are the principal input directions, columns of $U$ the matching output directions, each $\sigma_i$ the gain along that axis. Geometrically, every linear map is *rotation → axis-aligned scaling → rotation*. The unit sphere maps to an ellipsoid with semi-axes of length $\sigma_1, \dots, \sigma_r$.

```text
 unit sphere        V^T (rotate)      Σ (scale axes)      U (rotate)
     ___                ___              _______              ___
   /     \    -->     /     \    -->    (       )    -->    (    \
   \ ___ /            \ ___ /            \______/            \ ___)
                                        σ1 long axis,       ellipsoid,
                                        σ2 short axis       reoriented
```

What ties it to everything else:

- $\sigma_i(A) = \sqrt{\lambda_i(A^\top A)}$. The SVD is the eigendecomposition of $A^\top A$ (and $AA^\top$) done stably, without ever forming those products.
- PCA **is** the SVD of the centered data matrix (equivalently, eig of the covariance).
- Spectral norm $= \sigma_{\max}$, the Lipschitz constant or max gain of the map. Frobenius norm $= \sqrt{\sum_i \sigma_i^2}$. Nuclear norm $= \sum_i \sigma_i$, the convex surrogate for rank. [[Concept - Vector Norms and Distances]] covers where each norm is useful.
- The condition number $\kappa = \sigma_{\max}/\sigma_{\min}$ ([[Concept - The Condition Number]]) is a ratio of the two extreme singular values.

**Eckart–Young(–Mirsky):** the best rank-$k$ approximation of $A$, in *both* Frobenius and spectral norm, is the truncation $A_k = \sum_{i \le k} \sigma_i u_i v_i^\top$. The error is $\sigma_{k+1}$ in spectral norm and $\sqrt{\sum_{i>k} \sigma_i^2}$ in Frobenius. Every low-rank compression scheme rests on this. The tail of the singular spectrum *is* your approximation error: a fast-decaying spectrum means the matrix compresses, a flat one means it doesn't.

## In practice

- **LoRA.** The update $\Delta W = BA$ in [[Deep Dive - LoRA]] is rank-$r$ by construction, a bet that the fine-tuning update lives in a low-dimensional subspace. [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] takes that literally with SVD-based init: PiSSA (Meng et al. 2024) initializes $B, A$ from the top-$r$ singular triplets of the pretrained $W$, trains those, and freezes the residual.
- **Trained weight spectra are heavy-tailed.** Random init gives a Marchenko–Pastur-shaped bulk. Training drags out a power-law tail of large singular values (Martin & Mahoney 2021). Spectrum shape is good forensics: if a fine-tuned matrix's top few $\sigma_i$ moved and the bulk stayed put, that's empirical evidence for the low-rank-update hypothesis, and it's why a rank-16 LoRA on a 4096×4096 projection (0.4% of the parameters) works at all. Compare the near-flat bulk in [[Concept - The Hessian Spectrum in Deep Learning]].
- **Spectral normalization** divides each weight matrix by its $\sigma_{\max}$, estimated with one power-iteration step per forward pass (~free), to bound the network's Lipschitz constant. That trick stabilized GAN discriminators (Miyato et al. 2018).
- **Embeddings.** Whitening and isotropy corrections for [[Concept - Embedding Models]] are SVD operations on the embedding matrix. Dropping the top 1–2 dominant components is a classic retrieval win, since those directions often encode frequency instead of semantics. The SVD also shows low *intrinsic* rank (nominal dimension 1024, most variance in far fewer directions), which product quantization and graph indexes like [[Concept - HNSW]] implicitly exploit. It's the same spectral concentration story as [[Concept - The Geometry of High-Dimensional Spaces]]. Low-rank and low-bit compression sit at opposite ends of one accuracy-per-byte tradeoff; [[Concept - Post-Training Quantization Formats]] covers the bit side.
- **Compute.** Full SVD is $O(mn\min(m,n))$. A dense $10^4 \times 10^4$ SVD takes ~minutes on CPU plus $d^2$ memory for $U, V$, so you never do it at scale. Randomized SVD (Halko, Martinsson & Tropp 2011) gets the top-$k$ triplets in $O(mnk)$ with 1–2 power iterations: multiply $A$ by a random $n \times (k{+}10)$ Gaussian sketch, orthogonalize, solve the small problem. `torch.svd_lowrank` and scikit-learn's `TruncatedSVD` both implement it. A network is just a matmul chain (see [[Concept - Matrix Multiplication as the Atom of Deep Learning]]), and sketch-multiply-factor is cheap whenever the matmul is.
- **Numerical rank** is the count of $\sigma_i$ above a tolerance, conventionally $\sigma_{\max} \cdot \max(m,n) \cdot \varepsilon$. Counting nonzero $\sigma_i$ is meaningless in floating point.

## Failure modes

- **Near-equal singular values → unstable singular vectors.** A singular subspace's sensitivity scales like $1/\text{gap}$ between adjacent singular values (Wedin's theorem, the SVD analog of Davis–Kahan). If $\sigma_3 \approx \sigma_4$, the individual vectors $v_3, v_4$ are essentially arbitrary rotations within their shared plane. Only the *span* is stable. Check the spectral gap before interpreting individual components. If you rerun PCA and "component 3" changed meaning, this is the cause.
- **Sign/rotation ambiguity.** Each pair $(u_i, v_i)$ can be jointly negated with no change to $A$. Comparing singular vectors across runs, checkpoints, or libraries (LAPACK vs cuSOLVER) without sign-fixing (e.g., forcing the largest-magnitude entry positive) gives spurious "differences."
- **Forgetting to center before PCA.** On uncentered data the first singular vector points at the data mean instead of the direction of maximum variance. The answer is wrong and looks fine.
- **Backprop through SVD** has gradient singularities where singular values repeat or cross, because the gradient contains $1/(\sigma_i^2 - \sigma_j^2)$ terms. If a differentiable-SVD layer NaNs intermittently, suspect degenerate $\sigma$'s first. Workarounds and when to switch factorizations are in [[Decision - Choosing a Matrix Factorization]].
- **Full SVD as a reflex.** Computing all $\min(m,n)$ triplets when you need 50 wastes orders of magnitude of compute and memory. The numerics beyond overflow (cancellation, accumulation error in $A^\top A$) are in [[Gotchas - Numerical Stability]].

## The non-obvious

Rank is a *numerical* property. Every trained weight matrix is technically full-rank, since no $\sigma_i$ is exactly zero. The rank that matters is how many singular values sit above the noise floor $\sigma_{\max}\cdot\max(m,n)\cdot\varepsilon$, and in bf16 that floor is high ($\varepsilon \approx 7.8\times10^{-3}$). The corollary people learn the hard way: the *span* of the top-$k$ singular subspace is robust and reproducible, but the individual singular vectors inside it are only as stable as their spectral gaps. Trust subspaces, not components.

## Connections

- [[Concept - The Condition Number]] — $\kappa = \sigma_{\max}/\sigma_{\min}$ is read directly off the singular spectrum; this note supplies the object, that one the consequences.
- [[Decision - Choosing a Matrix Factorization]] — when SVD's stability is worth its cost versus QR/Cholesky/eig; the operational sequel to this note.
- [[Concept - Vector Norms and Distances]] — spectral, Frobenius, and nuclear norms are all functions of the $\sigma_i$; the norms note is the prerequisite vocabulary.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the SVD explains *what* a matmul does; randomized SVD's cost model is matmul's cost model.
- [[Concept - The Geometry of High-Dimensional Spaces]] — spectral decay vs nominal dimension is the intrinsic-dimension story; the deeper geometry of why high-d spaces leave room for low-rank structure.
- [[Concept - The Hessian Spectrum in Deep Learning]] — the same bulk-plus-outliers spectral analysis applied to curvature instead of weights; the eigen-sibling of this note.
- [[Deep Dive - LoRA]] — Eckart–Young is the theoretical license for rank-$r$ adapter updates; the empirical heavy-tailed spectra are the evidence.
- [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] — PiSSA literally initializes adapters from the top singular triplets of the frozen weight.
- [[Concept - Embedding Models]] — whitening, isotropy correction, and dominant-component removal are SVD surgery on the embedding space.
- [[Concept - HNSW]] — ANN indexes are fast because real embedding spectra decay; flat-spectrum vectors would break their distance-computation shortcuts.
- [[Concept - Post-Training Quantization Formats]] — low-rank (drop small $\sigma_i$) and low-bit (drop mantissa bits) are the two axes of compression; SVD gives the error bound for the first.
- [[Gotchas - Numerical Stability]] — forming $A^\top A$ to get singular values squares the condition number; the catalog of what else goes wrong in the arithmetic.

## Sources

- Eckart & Young (1936) — "The approximation of one matrix by another of lower rank." The low-rank optimality theorem everything above leans on.
- Halko, Martinsson & Tropp (2011) — "Finding Structure with Randomness." The randomized SVD algorithm that made truncated SVD practical at scale.
- Martin & Mahoney (2021) — "Implicit Self-Regularization in Deep Neural Networks" (JMLR). Heavy-tailed singular spectra of trained weight matrices.
- Hu et al. (2021) — "LoRA: Low-Rank Adaptation of Large Language Models." The low-rank-update bet, stated and validated.
- Meng et al. (2024) — "PiSSA: Principal Singular Values and Singular Vectors Adaptation." SVD-initialized LoRA.
- Miyato et al. (2018) — "Spectral Normalization for Generative Adversarial Networks." $\sigma_{\max}$ control via power iteration in production training.
