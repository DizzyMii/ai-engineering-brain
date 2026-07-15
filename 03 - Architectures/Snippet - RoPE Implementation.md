---
tags: [snippet, domain/architectures, level/advanced]
aliases: [RoPE from scratch, rotate_half, rotary embedding code]
summary: "Runnable RoPE: frequency-band cache, rotate_half rotation of Q/K, and an empirical check that scores depend only on relative position."
---

# Snippet - RoPE Implementation

**What it does:** builds the RoPE frequency cache (`inv_freq`, `cos`, `sin`), applies rotation to `Q` and `K` via the `rotate_half` trick, and empirically verifies the property the whole scheme exists for: the dot product of a rotated query at position $m$ and a rotated key at position $n$ depends only on $(m-n)$. This is a runnable version of the math in [[Concept - Rotary Position Embeddings (RoPE)]] — read that note for the derivation, this file for the exact tensor ops.

**Dependencies:** `torch >= 2.0` (CPU is fine).

**Expected output:**
```text
q_rot, k_rot shape: torch.Size([1, 1, 16, 8])
relative-position check passed: True
```

```python
"""
Snippet - RoPE Implementation

Builds RoPE's frequency bands and cos/sin cache, applies rotation to Q and
K via rotate_half, and empirically checks the defining property:
<R_m q, R_n k> depends only on (m - n), never on m and n individually.
See Concept - Rotary Position Embeddings (RoPE) for the derivation.

Dependencies: torch>=2.0 (CPU is fine)
Expected output:
    q_rot, k_rot shape: torch.Size([1, 1, 16, 8])
    relative-position check passed: True
"""

import torch


def build_rope_cache(seq_len: int, d_head: int, base: float = 10000.0):
    assert d_head % 2 == 0, "RoPE needs an even head dim to form 2D rotation pairs"
    # theta_i = base^(-2i/d) for i in [0, d/2). Low i rotates fast (short
    # wavelength, local/fine-grained position); high i rotates slowly
    # (long wavelength, long-range position). `base` is the extrapolation
    # knob -- LLaMA-3 raised it from 10000 to 500000 specifically to push
    # the slow dims' wavelength past its target context length. Swap this
    # single line for an NTK/YaRN-scaled theta to hook in context
    # extension (see Concept - Context Length Extension) without touching
    # anything else below.
    inv_freq = 1.0 / (base ** (torch.arange(0, d_head, 2).float() / d_head))
    positions = torch.arange(seq_len).float()
    angles = torch.outer(positions, inv_freq)            # [seq_len, d_head/2]
    # Half-split convention (GPT-NeoX / rotate_half style): each frequency
    # is duplicated across both halves of d_head rather than interleaved
    # across even/odd indices. This must match whatever convention the
    # reference checkpoint used -- see Gotchas - Implementing Attention.
    angles = torch.cat([angles, angles], dim=-1)          # [seq_len, d_head]
    return angles.cos(), angles.sin()


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    # x: [batch, heads, seq_len, d_head]; cos/sin: [seq_len, d_head]
    return x * cos + rotate_half(x) * sin


if __name__ == "__main__":
    torch.manual_seed(0)
    seq_len, d_head = 16, 8
    cos, sin = build_rope_cache(seq_len=seq_len, d_head=d_head, base=10000.0)

    B, H = 1, 1
    q = torch.randn(B, H, seq_len, d_head)
    k = torch.randn(B, H, seq_len, d_head)

    q_rot = apply_rope(q, cos, sin)   # V is never rotated -- position is a
    k_rot = apply_rope(k, cos, sin)   # Q/K-only signal, not content

    print(f"q_rot, k_rot shape: {q_rot.shape}")
    assert q_rot.shape == (B, H, seq_len, d_head)

    # Relative-position check: rotate a FIXED (q0, k0) pair by every valid
    # m and its offset partner (m - offset), and confirm the dot product
    # <R_m q0, R_{m-offset} k0> is identical for every m -- i.e. it depends
    # only on the offset, never on m and (m - offset) individually.
    q0, k0 = q[0, 0, 0].clone(), k[0, 0, 0].clone()

    def rotated_dot(m: int, n: int) -> float:
        qm = q0 * cos[m] + rotate_half(q0) * sin[m]
        kn = k0 * cos[n] + rotate_half(k0) * sin[n]
        return (qm * kn).sum().item()

    offset = 3
    dots = [rotated_dot(m, m - offset) for m in range(offset, seq_len)]
    check = (max(dots) - min(dots)) < 1e-4
    print(f"relative-position check passed: {check}")
    assert check
```

## Why it's written this way

1. **Rotation is applied to `Q` and `K` only, never `V`.** Position is a signal that should shape *which* keys a query attends to, not a signal baked into the *content* being retrieved. Rotating `V` would make the attention output itself rotate with absolute position instead of leaving position purely as a relative-distance effect on the attention weights.
2. **`rotate_half` splits the vector in half, not by interleaving even/odd indices.** There are two mathematically-equivalent-in-theory, bit-incompatible conventions for pairing up the `d_head` dimension for rotation. This snippet uses the half-split (`rotate_half`) convention that GPT-NeoX-style code and most modern open-weight checkpoints use — porting weights from a checkpoint trained with the *other* (interleaved) convention into this code produces a model that runs, generates plausible text, and is silently wrong. This single mismatch is the most common RoPE bug in practice; see [[Gotchas - Implementing Attention]].
3. **The relative-position check rotates one fixed `(q0, k0)` pair by every position, not random per-position vectors.** Random `q`/`k` at each of two positions confirms nothing about the relative-position *property* — you need to hold content fixed and vary only where you rotate it to, so that a constant dot product across varying `m` (fixed offset) is proof, not coincidence.
4. **`base` is exposed as a plain function argument, not hardcoded.** Every context-extension technique — Position Interpolation, NTK-aware scaling, YaRN — works by changing what goes into this one line (either the position indices or `base`/`theta` itself). Isolating it here is what makes those techniques a one-line intervention rather than a rewrite; see [[Concept - Context Length Extension]] and the extrapolation folklore in [[Concept - RoPE Extrapolation and Context Extension]].

## Connections
- [[Concept - Rotary Position Embeddings (RoPE)]] — the full derivation (the 2D rotation matrix, the $R_m^\top R_n = R_{n-m}$ composition identity) that this code implements and empirically checks.
- [[Concept - Context Length Extension]] — Position Interpolation, NTK-scaling, and YaRN all work by modifying the `base` or `positions` inputs to `build_rope_cache` above, without touching `rotate_half` or `apply_rope`.
- [[Snippet - Scaled Dot-Product Attention from Scratch]] — where this rotation gets inserted: right after `split_heads`, before the `q @ k.transpose` score matmul.
- [[Gotchas - Implementing Attention]] — catalogs the interleaved-vs-half-split ordering bug and base/theta mismatches this snippet is written to sidestep.
- [[Playbook - Numerically Matching a Reference Implementation]] — RoPE ordering and base value are top-of-list "usual culprits" in that playbook's activation-diffing procedure.
- [[Concept - Floating Point for Deep Learning]] — `m * theta_i` for large `m` and small `theta_i` can lose precision in low precision; cos/sin tables are conventionally cached in fp32 for exactly this reason.
- [[Concept - RoPE Extrapolation and Context Extension]] — the frontier-adjacent folklore on why raising `base` works better in practice than published theory strictly justifies.

## Sources
- Su et al. (2021) — "RoFormer: Enhanced Transformer with Rotary Position Embedding." Introduces RoPE and the relative-position derivation this snippet verifies numerically.
- Xiong et al. (2023) — "Effective Long-Context Scaling of Foundation Models." The base-change (ABF) approach — later adopted by LLaMA-3 — that this snippet's exposed `base` parameter is designed to support.
