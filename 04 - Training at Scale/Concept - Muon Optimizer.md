---
tags: [concept, domain/training-at-scale, level/frontier]
aliases: [Muon, MomentUm Orthogonalized by Newton-schulz]
summary: "Muon replaces AdamW's per-coordinate scaling with Newton-Schulz orthogonalized momentum for 2D weight matrices."
---

# Concept - Muon Optimizer

> **One-paragraph hook:** [[Concept - AdamW at Scale|AdamW's]] diagonal preconditioner scales each weight coordinate on its own and never sees the cross-coordinate structure of a weight matrix. Muon (Jordan et al. 2024) goes after the 2D matrices that make up most of a transformer's parameters (attention projections, MLP up/down projections) and swaps their per-coordinate Adam update for an orthogonalized momentum step. It reported roughly 2x compute efficiency at small scale, and Kimi's Moonlight model (2025) is real evidence that it survives the jump to production scale.

## The mechanism

Keep plain heavy-ball momentum on the gradient of a 2D weight $W \in \mathbb{R}^{m\times n}$: $M_t = \mu M_{t-1} + G_t$. SGD-momentum would use $M_t$ directly and Adam would divide it element-wise by $\sqrt{v_t}$. Muon instead replaces $M_t$ with its **nearest orthogonal matrix**, the $O_t$ that minimizes $\lVert O_t - M_t \rVert_F$ subject to having orthonormal rows or columns. If $M_t = U\Sigma V^T$ is the [[Concept - Singular Value Decomposition|SVD]] of the momentum buffer, that matrix is $O_t = UV^T$. Every singular value becomes 1, so each momentum direction gets equal weight regardless of how much gradient energy it carried.

A full SVD per step is far too slow for a matrix with millions of entries, so Muon approximates $UV^T$ with a few rounds of the **Newton-Schulz iteration**, a classical numerical-analysis method that computes the orthogonal polar factor of a matrix without forming eigenvalues:

```python
# Newton-Schulz orthogonalization (quintic, ~5 iterations)
def orthogonalize(M, iters=5, a=3.4445, b=-4.7750, c=2.0315):
    X = M / (M.norm() + 1e-7)          # Frobenius-normalize so the iteration converges
    if X.shape[0] > X.shape[1]:
        X = X.T                          # orient on the smaller dimension
    for _ in range(iters):
        A = X @ X.T
        B = b * A + c * (A @ A)
        X = a * X + B @ X                # quintic (5th-order) polynomial update
    return X.T if M.shape[0] > M.shape[1] else X
```

The coefficients $(a, b, c)$ are tuned for the singular-value range typical of neural-network gradients, so a handful of iterations is enough; the generic Newton-Schulz coefficients $(3, -3, 1)$ converge more slowly. After convergence $X \to UV^T$. The update is $W_{t+1} = W_t - \eta \cdot O_t$ (plus weight decay). With every singular value of $O_t$ at 1, the step is equal-sized along every singular direction of the layer: a whitening-like effect similar to [[Concept - Second-Order Optimizers at Scale|Shampoo]], with no explicit per-layer preconditioner to form or invert. Newton-Schulz is all matmuls, so it costs about as much as plain momentum and runs natively on tensor cores.

"Singular direction" only means something for a real 2D matrix, so Muon is restricted to hidden weight matrices: QKVO and MLP projections. Embeddings, the unembedding layer, RMSNorm/LayerNorm gains and biases are either 1D or have a privileged basis (vocabulary index, per-channel scale) where orthogonalizing makes no sense. Those stay on AdamW, which makes Muon a **hybrid** optimizer.

## In practice

Muon's update has unit spectral norm by construction, while AdamW's is roughly unit-normalized per coordinate. So Muon needs its own learning rate, separate from the LR used for the AdamW-optimized embedding/output/1D parameters. The scales don't transfer; typical guidance ties Muon's LR to the matrix dimensions instead of reusing an AdamW-tuned value. Weight decay is also applied separately from the AdamW parameter group. For non-square matrices the Newton-Schulz iteration is oriented on the smaller dimension, which keeps per-step cost down for the very rectangular matrices in MLP up/down projections.

Numbers: Jordan et al. 2024 reported roughly 2x wall-clock/compute efficiency over AdamW at small NanoGPT-speedrun scale. Moonlight (Kimi, ~16B-parameter MoE, 2025) is the first large-scale production validation. Trained with Muon, it reported roughly 2x token efficiency plus real memory savings: Muon keeps only momentum for 2D matrices (no second-moment buffer), which roughly halves the optimizer memory Adam would need for that majority-of-parameters pool. That's the same 12-bytes/param [[Concept - Data Parallelism and ZeRO|ZeRO shards]] for AdamW.

Distributed training is where Muon gets harder than it looks on paper. Newton-Schulz needs the momentum buffer for the *entire* weight matrix to orthogonalize correctly. A matrix sharded across ranks under ZeRO-3/FSDP needs either a gather of the momentum buffer before orthogonalizing (extra communication every step) or a distributed Newton-Schulz formulation. That part is still an open systems-engineering question as of 2026, separate from the pure-math algorithm.

## Failure modes

- **Applying Muon to embeddings, the output layer, or 1D parameters breaks it.** They have no meaningful singular-value structure to orthogonalize. Forgetting to whitelist only 2D hidden matrices and fall back to AdamW elsewhere is the most common bring-up bug.
- **Wrong LR scaling relative to AdamW.** An AdamW-tuned LR on Muon either does nothing (too small, since the orthogonalized update has a different scale by construction) or diverges (too large). You need a fresh LR sweep or the dimension-dependent scaling rule.
- **Newton-Schulz instability from too few iterations or skipped normalization.** An under-converged orthogonalization leaves a non-orthogonal update that behaves unpredictably. It shows up like an Adam epsilon-swamping bug: training looks fine early, then destabilizes later.
- **Naive per-shard orthogonalization is silently wrong.** Orthogonalizing each rank's shard of a sharded matrix separately does *not* give the same result as orthogonalizing the whole matrix, because shards aren't independently orthogonal even when the full matrix is. Nothing crashes; loss is just worse than expected, which is much harder to root-cause.

## The non-obvious

Muon is still a 2024-2025 result and hasn't become the settled default the way AdamW is. Moonlight shows it survives past speedrun scale. Whether it holds at hundreds-of-billions-of-parameters scale with every interacting [[Concept - Training Stability and Loss Spikes|stability trick]] on top is open as of 2026. I'd frame it this way: Muon is less a new optimization theory than a cheap, matmul-only approximation of the whitening Shampoo gets "properly" from an explicit Kronecker-factored preconditioner. It trades Shampoo's preconditioner storage and inversion for a few extra matmuls per step. That trade is why it's the one second-order-flavored method cheap enough to challenge AdamW seriously instead of staying a niche academic win.

## Connections
- [[Concept - AdamW at Scale]] — the incumbent optimizer Muon partially replaces for 2D matrices while still relying on it for embeddings, output layer, and 1D parameters.
- [[Concept - Second-Order Optimizers at Scale]] — Muon's orthogonalization is a cheap matmul-only approximation to the whitening effect Shampoo achieves with an explicit preconditioner.
- [[Concept - Adam and AdamW]] — the base per-coordinate adaptive update Muon's hybrid design falls back to outside 2D hidden matrices.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — Newton-Schulz orthogonalization is built entirely from the matmul primitive, which is what makes it cheap enough to run every step.
- [[Reference - LLM Pretraining Hyperparameters]] — where Muon's LR, momentum, and weight-decay values sit alongside the AdamW defaults it partially displaces.
- [[Concept - Learning Rate Schedules for Pretraining]] — Muon needs its own LR scale and schedule, decoupled from whatever schedule governs the AdamW-optimized parameters.
- [[Concept - Singular Value Decomposition]] — the exact linear-algebra operation ($UV^T$ from $M=U\Sigma V^T$) that Newton-Schulz iteration approximates without ever forming $\Sigma$.
- [[Concept - Data Parallelism and ZeRO]] — Muon's momentum-only state roughly halves the optimizer memory ZeRO/FSDP has to shard for 2D matrices, but also complicates sharded orthogonalization.
- [[Concept - Training Stability and Loss Spikes]] — whether Muon holds up alongside every other stability trick at hundreds-of-billions-of-parameters scale is the open question keeping it from AdamW's default status.

## Sources
- Jordan et al. (2024) — "Muon: An Optimizer for Hidden Layers in Neural Networks" — introduces Muon and the tuned quintic Newton-Schulz orthogonalization scheme, developed through the NanoGPT speedrun community.
- Moonlight team, Kimi (2025) — "Moonlight: a ~16B-parameter MoE trained with Muon" — the first large-scale production validation, reporting token-efficiency and memory gains over AdamW.
