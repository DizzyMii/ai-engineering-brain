---
tags: [concept, domain/training-at-scale, level/frontier]
aliases: [Muon, MomentUm Orthogonalized by Newton-schulz]
summary: "Muon replaces AdamW's per-coordinate scaling with Newton-Schulz orthogonalized momentum for 2D weight matrices."
---

# Concept - Muon Optimizer

> **One-paragraph hook:** [[Concept - AdamW at Scale|AdamW's]] diagonal preconditioner scales each weight coordinate independently and never sees the cross-coordinate structure of a weight matrix. Muon (Jordan et al. 2024) targets exactly the 2D matrices — attention projections, MLP up/down projections — that dominate a transformer's parameter count, and replaces their per-coordinate Adam update with an orthogonalized momentum step, reporting roughly 2x compute efficiency at small scale and, as of Kimi's Moonlight model (2025), real evidence it survives the jump to production scale.

## The mechanism

Maintain ordinary heavy-ball momentum on the gradient of a 2D weight $W \in \mathbb{R}^{m\times n}$: $M_t = \mu M_{t-1} + G_t$. Instead of using $M_t$ directly (SGD-momentum) or dividing element-wise by $\sqrt{v_t}$ (Adam), Muon replaces $M_t$ with its **nearest orthogonal matrix** — the matrix $O_t$ minimizing $\lVert O_t - M_t \rVert_F$ subject to $O_t$ having orthonormal rows or columns. If $M_t = U\Sigma V^T$ is the [[Concept - Singular Value Decomposition|SVD]] of the momentum buffer, that nearest orthogonal matrix is exactly $O_t = UV^T$ — every singular value is replaced by 1, so every direction the momentum points in gets treated equally regardless of how much of the gradient's energy was in that direction.

Computing a full SVD every optimizer step is far too slow for a matrix with millions of entries. Muon instead approximates $UV^T$ with a few iterations of the **Newton-Schulz iteration**, a classical numerical-analysis method for computing the orthogonal polar factor of a matrix without ever forming eigenvalues:

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

The coefficients $(a, b, c)$ are tuned — not the slower-converging generic Newton-Schulz coefficients $(3, -3, 1)$ — specifically for the singular-value range typical of neural-network gradients, so a handful of iterations suffices. After convergence $X \to UV^T$. The final update is $W_{t+1} = W_t - \eta \cdot O_t$ (plus weight decay), and because every one of $O_t$'s singular values is exactly 1, the update's magnitude is equalized across every singular direction of that layer — a whitening-like effect similar to [[Concept - Second-Order Optimizers at Scale|Shampoo]] without ever forming or inverting an explicit per-layer preconditioner. Newton-Schulz needs only matmuls, so it's nearly as cheap as plain momentum and runs natively on tensor cores.

Because "singular direction" is only a meaningful concept for a genuine 2D matrix, Muon explicitly restricts itself to hidden weight matrices — QKVO and MLP projections. Embeddings, the unembedding layer, RMSNorm/LayerNorm gains, and biases are 1D or have a privileged basis (vocabulary index, per-channel scale) where orthogonalizing makes no sense, so those parameters keep using AdamW. Muon is a **hybrid** optimizer, not a full AdamW replacement.

## In practice

Because Muon's update has unit spectral norm by construction — unlike AdamW's roughly per-coordinate-unit-normalized update — it needs its own learning rate, decoupled from whatever LR the AdamW-optimized embedding/output/1D parameters use; the two scales don't transfer between each other, and typical guidance couples Muon's LR to the matrix dimensions rather than reusing an AdamW-tuned value outright. Weight decay is likewise applied separately from the AdamW parameter group. Non-square matrices are handled by orienting the Newton-Schulz iteration on the smaller dimension, keeping the per-step cost down for the very rectangular matrices common in MLP up/down projections.

Numbers: Jordan et al. 2024 reported roughly 2x wall-clock/compute efficiency over AdamW at small NanoGPT-speedrun scale. Moonlight (Kimi, ~16B-parameter MoE, 2025) is the first genuinely large-scale production validation — trained with Muon and reporting roughly 2x token efficiency plus real memory savings, because Muon's momentum-only state for 2D matrices (no second-moment buffer) roughly halves the optimizer memory Adam would need for that majority-of-parameters pool — the same 12-bytes/param [[Concept - Data Parallelism and ZeRO|ZeRO shards]] for AdamW.

Distributed training is where Muon gets genuinely harder than it looks on paper: Newton-Schulz needs the *entire* weight matrix's momentum buffer to orthogonalize correctly, so a matrix sharded across ranks under ZeRO-3/FSDP either needs the momentum buffer gathered before orthogonalizing (extra communication every step) or a distributed Newton-Schulz formulation — this remains a genuinely open systems-engineering question as of 2026, distinct from the pure-math version of the algorithm.

## Failure modes

- **Applying Muon to embeddings, the output layer, or 1D parameters breaks it.** These don't have meaningful singular-value structure to orthogonalize; forgetting to whitelist only 2D hidden matrices and fall back to AdamW elsewhere is the single most common bring-up bug.
- **Wrong LR scaling relative to AdamW.** Reusing an AdamW-tuned LR for Muon either does nothing (too small, since the orthogonalized update's scale is different by construction) or diverges (too large) — a fresh LR sweep or the dimension-dependent scaling rule is mandatory, not optional.
- **Newton-Schulz instability from too few iterations or skipped normalization.** An under-converged orthogonalization leaves a non-orthogonal update that behaves unpredictably, manifesting the same way as an Adam epsilon-swamping bug: training looks fine early, then destabilizes later.
- **Naive per-shard orthogonalization is silently wrong.** Orthogonalizing each rank's shard of a sharded matrix independently does *not* produce the same result as orthogonalizing the whole matrix — shards aren't independently orthogonal even when the full matrix is. This won't crash; it just produces worse-than-expected loss, which is far harder to root-cause.

## The non-obvious

Muon is still a 2024-2025 result, not yet the settled default the way AdamW is — Moonlight is real evidence it survives past speedrun scale, but whether it holds at hundreds-of-billions-of-parameters scale with every interacting [[Concept - Training Stability and Loss Spikes|stability trick]] layered on top remains open as of 2026. The sharper framing: Muon isn't a new optimization theory so much as a cheap, matmul-only approximation to the whitening effect Shampoo achieves "properly" via an explicit Kronecker-factored preconditioner — Muon trades Shampoo's preconditioner-storage-and-inversion cost for a handful of extra matmuls per step, which is exactly why it's the one second-order-flavored method cheap enough to be a serious AdamW challenger rather than a niche academic win.

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
