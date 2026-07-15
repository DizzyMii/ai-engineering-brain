---
tags: [concept, domain/foundations, level/advanced]
aliases: [SVD, singular values, truncated SVD, low-rank approximation]
summary: "Every matrix is rotation → axis scaling → rotation; the scaling factors explain PCA, spectral norms, low-rank compression, and LoRA."
---

# Concept - Singular Value Decomposition

> **One-paragraph hook:** The SVD is the factorization that tells you what a linear map *actually does*, and — unlike eigendecomposition — it exists for every matrix, square or not. It is the load-bearing theorem under half of applied ML: PCA, spectral norms, whitening, low-rank compression, and the entire premise of LoRA all reduce to reading off singular values. When someone says "this weight matrix is effectively rank 40," the SVD is the instrument that statement was measured with.

## The mechanism

Any real $m \times n$ matrix factors as

$$A = U \Sigma V^\top$$

where $U \in \mathbb{R}^{m \times m}$ and $V \in \mathbb{R}^{n \times n}$ have orthonormal columns and $\Sigma$ is diagonal with singular values $\sigma_1 \ge \sigma_2 \ge \dots \ge 0$. The columns of $V$ are the principal input directions, the columns of $U$ the corresponding output directions, and each $\sigma_i$ is the gain along that axis. Geometrically, every linear map is *rotation → axis-aligned scaling → rotation*: the image of the unit sphere is an ellipsoid whose semi-axes have lengths $\sigma_1, \dots, \sigma_r$.

```text
 unit sphere        V^T (rotate)      Σ (scale axes)      U (rotate)
     ___                ___              _______              ___
   /     \    -->     /     \    -->    (       )    -->    (    \
   \ ___ /            \ ___ /            \______/            \ ___)
                                        σ1 long axis,       ellipsoid,
                                        σ2 short axis       reoriented
```

The relations that make it the master decomposition:

- $\sigma_i(A) = \sqrt{\lambda_i(A^\top A)}$ — the SVD is the eigendecomposition of $A^\top A$ (and $AA^\top$) done stably, without ever forming those products.
- PCA **is** the SVD of the centered data matrix (equivalently, eig of the covariance).
- Spectral norm $= \sigma_{\max}$ (the Lipschitz constant / max gain of the map); Frobenius norm $= \sqrt{\sum_i \sigma_i^2}$; nuclear norm $= \sum_i \sigma_i$, the convex surrogate for rank — see [[Concept - Vector Norms and Distances]] for where each norm earns its keep.
- The condition number $\kappa = \sigma_{\max}/\sigma_{\min}$ — the subject of [[Concept - The Condition Number]] — is a ratio of the two extreme singular values.

**Eckart–Young(–Mirsky):** the best rank-$k$ approximation of $A$, in *both* Frobenius and spectral norm, is the truncation $A_k = \sum_{i \le k} \sigma_i u_i v_i^\top$. The error is exactly $\sigma_{k+1}$ in spectral norm and $\sqrt{\sum_{i>k} \sigma_i^2}$ in Frobenius. This is the theorem behind every low-rank compression scheme: it says the singular spectrum's tail *is* your approximation error, so a fast-decaying spectrum means the matrix is compressible and a flat one means it is not.

## In practice

- **LoRA.** The update $\Delta W = BA$ in [[Deep Dive - LoRA]] is a rank-$r$ matrix by construction — a bet that the fine-tuning update lives in a low-dimensional subspace. SVD-based initialization in [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] takes this literally: PiSSA (Meng et al. 2024) initializes $B, A$ from the top-$r$ singular triplets of the pretrained $W$ and trains those, freezing the residual.
- **Trained weight spectra are heavy-tailed.** Random init gives a Marchenko–Pastur-shaped bulk; training drags out a power-law tail of large singular values (Martin & Mahoney 2021). Spectrum shape is a useful forensic: a fine-tuned matrix whose top few $\sigma_i$ moved while the bulk stayed put is empirical evidence for the low-rank-update hypothesis — the reason a rank-16 LoRA on a 4096×4096 projection (0.4% of the parameters) works at all. This is one operational face of the near-flat bulk in [[Concept - The Hessian Spectrum in Deep Learning]].
- **Spectral normalization** divides each weight matrix by its $\sigma_{\max}$ (estimated by one power-iteration step per forward pass, ~free) to bound the network's Lipschitz constant — the trick that stabilized GAN discriminators (Miyato et al. 2018).
- **Embeddings.** Whitening/isotropy corrections for [[Concept - Embedding Models]] are SVD operations on the embedding matrix; removing the top 1–2 dominant components is a classic post-processing win for retrieval, because those directions often encode frequency rather than semantics. The low *intrinsic* rank that the SVD reveals — nominal dimension 1024, most variance in far fewer directions — is also what product quantization and graph indexes like [[Concept - HNSW]] implicitly exploit, and it is the same spectral concentration story as [[Concept - The Geometry of High-Dimensional Spaces]]. Low-rank and low-bit compression are complementary ends of the same accuracy-per-byte tradeoff that [[Concept - Post-Training Quantization Formats]] covers from the bit side.
- **Compute.** Full SVD is $O(mn\min(m,n))$ — a dense $10^4 \times 10^4$ SVD is ~minutes on CPU, and $d^2$ memory for $U, V$; you never do this at scale. Randomized SVD (Halko, Martinsson & Tropp 2011) gets the top-$k$ triplets in $O(mnk)$ with 1–2 power iterations: multiply $A$ by a random $n \times (k{+}10)$ Gaussian sketch, orthogonalize, solve the small problem. `torch.svd_lowrank` and scikit-learn's `TruncatedSVD` are this algorithm. Since a matmul chain is all a network is (see [[Concept - Matrix Multiplication as the Atom of Deep Learning]]), sketch-multiply-factor is cheap exactly when the matrix is.
- **Numerical rank** is the count of $\sigma_i$ above a tolerance, conventionally $\sigma_{\max} \cdot \max(m,n) \cdot \varepsilon$ — not the count of nonzero $\sigma_i$, which is meaningless in floating point.

## Failure modes

- **Near-equal singular values → unstable singular vectors.** The sensitivity of a singular subspace scales like $1/\text{gap}$ between adjacent singular values (Wedin's theorem, the SVD analog of Davis–Kahan). If $\sigma_3 \approx \sigma_4$, the individual vectors $v_3, v_4$ are essentially arbitrary rotations within their shared plane — only the *span* is stable. Detection: always check the spectral gap before interpreting individual components; if you rerun PCA and "component 3" flipped meaning, this is why.
- **Sign/rotation ambiguity.** Each pair $(u_i, v_i)$ can be jointly negated with no change to $A$. Comparing singular vectors across runs, checkpoints, or libraries (LAPACK vs cuSOLVER) without sign-fixing (e.g., forcing the largest-magnitude entry positive) produces spurious "differences."
- **Forgetting to center before PCA.** Uncentered data makes the first singular vector point at the data mean, not the direction of maximum variance — a silent, plausible-looking wrong answer.
- **Backprop through SVD** has gradient singularities where singular values are repeated or cross (the gradient contains $1/(\sigma_i^2 - \sigma_j^2)$ terms). If a differentiable-SVD layer NaNs intermittently, degenerate $\sigma$'s are the first suspect; the workarounds (and when to pick a different factorization entirely) live in [[Decision - Choosing a Matrix Factorization]].
- **Full SVD as a reflex.** Computing all $\min(m,n)$ triplets when you need 50 wastes orders of magnitude of compute and memory; the numerics beyond overflow — cancellation, accumulation error in $A^\top A$ — are cataloged in [[Gotchas - Numerical Stability]].

## The non-obvious

Rank is a *numerical* property, not an algebraic one. Every trained weight matrix is technically full-rank — no $\sigma_i$ is exactly zero — but "rank" that matters is how many singular values stand above the noise floor $\sigma_{\max}\cdot\max(m,n)\cdot\varepsilon$, and in bf16 that floor is brutally high ($\varepsilon \approx 7.8\times10^{-3}$). Corollary practitioners hit the hard way: the *span* of the top-$k$ singular subspace is a robust, reproducible object, but the individual singular vectors inside it are only as stable as their spectral gaps. Trust subspaces, not components.

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
