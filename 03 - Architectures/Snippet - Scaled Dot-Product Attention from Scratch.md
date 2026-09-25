---
tags: [snippet, domain/architectures, level/core]
aliases: [SDPA from scratch, causal self-attention snippet, attention from scratch]
summary: "Minimal runnable causal multi-head attention in PyTorch: projections, reshape, scaled masked scores, fp32 softmax, causality self-test."
---

# Snippet - Scaled Dot-Product Attention from Scratch

**What it does:** implements causal multi-head [[Concept - Attention Mechanism]] from raw [[Concept - Matrix Multiplication as the Atom of Deep Learning|matmuls]]: QKV projection, head split, scaled scores, causal masking, an fp32-upcast softmax, merge, output projection. This is the reference math that a fused kernel like [[Deep Dive - FlashAttention]] speeds up without changing. One config of plain multi-head attention: no KV cache, no [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)|GQA/MQA]] head-sharing. It's meant to be read top to bottom, and it isn't fast.

**Dependencies:** `torch >= 2.0` (CPU is fine).

**Expected output:**
```text
output shape: torch.Size([2, 8, 64])
causality check passed: True
```

```python
"""
Snippet - Scaled Dot-Product Attention from Scratch

Minimal causal multi-head attention module: projections, head reshape,
scaled scores, causal masking, fp32-upcast softmax, output projection.
This is the reference math, not the fast path -- see Deep Dive -
FlashAttention for the fused kernel that computes the same result without
materializing the full [seq, seq] score matrix in HBM.

Dependencies: torch>=2.0 (CPU is fine)
Expected output:
    output shape: torch.Size([2, 8, 64])
    causality check passed: True
"""

import math
import torch
import torch.nn as nn


class CausalSelfAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int):
        super().__init__()
        assert d_model % n_heads == 0, "d_model must divide evenly into n_heads"
        self.n_heads = n_heads
        self.d_head = d_model // n_heads

        self.qkv_proj = nn.Linear(d_model, 3 * d_model, bias=False)
        self.out_proj = nn.Linear(d_model, d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape

        qkv = self.qkv_proj(x)                            # [B, T, 3*D]
        q, k, v = qkv.chunk(3, dim=-1)                     # each [B, T, D]

        # [B, T, D] -> [B, H, T, d_head]. The head dim must come out of the
        # FEATURE dim via view (a real reinterpretation of contiguous
        # memory) then transpose -- not a permute that mixes sequence and
        # head axes, which silently scrambles heads while the output shape
        # still looks completely plausible.
        def split_heads(t: torch.Tensor) -> torch.Tensor:
            return t.view(B, T, self.n_heads, self.d_head).transpose(1, 2)

        q, k, v = split_heads(q), split_heads(k), split_heads(v)

        scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.d_head)  # [B,H,T,T]

        # Upper-triangular -inf, diagonal EXCLUDED (diagonal=1): position i
        # may attend to itself and everything before it, never after.
        causal_mask = torch.triu(
            torch.full((T, T), float("-inf"), device=x.device), diagonal=1
        )
        scores = scores + causal_mask

        # Softmax in fp32 even if the model runs in bf16/fp16: low-precision
        # softmax over near-tied logits loses probability mass and, after
        # the max-subtraction step, is one large activation away from NaN.
        attn = torch.softmax(scores.float(), dim=-1).to(q.dtype)

        out = attn @ v                                     # [B, H, T, d_head]
        out = out.transpose(1, 2).contiguous().view(B, T, D)  # merge heads
        return self.out_proj(out)


if __name__ == "__main__":
    torch.manual_seed(0)
    B, T, D, H = 2, 8, 64, 8

    attn = CausalSelfAttention(d_model=D, n_heads=H)
    x = torch.randn(B, T, D)
    out = attn(x)
    print(f"output shape: {out.shape}")
    assert out.shape == (B, T, D)

    # Causality self-test: the output at position t must be UNCHANGED when
    # tokens at positions > t are perturbed. This is the single highest-
    # value unit test for a hand-rolled attention layer -- a broken mask
    # doesn't crash and doesn't obviously hurt the loss; it makes training
    # loss look BETTER, because the model is reading a few tokens of the
    # label ahead of time. That failure is invisible in a loss curve and
    # only shows up here.
    t = 3
    x2 = x.clone()
    x2[:, t + 1 :, :] += torch.randn_like(x2[:, t + 1 :, :]) * 10.0
    out2 = attn(x2)
    causal_ok = torch.allclose(out[:, : t + 1], out2[:, : t + 1], atol=1e-5)
    print(f"causality check passed: {causal_ok}")
    assert causal_ok
```

## Why it's written this way

1. **fp32 softmax, cast back to the working dtype.** Attention scores can be large before masking and near-tied after it, so a native bf16/fp16 `softmax` risks saturating precision on the max-subtracted exponentials. Frameworks and fused kernels do the reduction in fp32 and the matmuls in low precision. The snippet writes that split out where a library call would hide it.
2. **`torch.triu(..., diagonal=1)`, not `diagonal=0`.** With `diagonal=1` the diagonal stays out of the masked region, so position $i$ can attend to itself. Get this one integer wrong and either a token sees the future (silent label leakage, and loss looks *better*) or it can't see itself (loss plateaus visibly high). [[Gotchas - Implementing Attention]] catalogs both.
3. **`view` then `transpose` inside `split_heads`, in that order.** `view(B, T, H, d_head)` just reinterprets contiguous memory, which works only because the last dimension really is `H * d_head` features. `transpose(1, 2)` then moves the head axis without scrambling the layout. A single `permute` with the wrong axis order gives a tensor of the *same shape* with heads and sequence positions mixed, and no shape assertion will catch it.
4. **The causality self-test is in `__main__`.** Perturbing future tokens and diffing the untouched prefix costs one extra forward pass. It catches the mask bugs from point 2 directly, so you don't have to trust your eyes on the mask tensor.

## Connections
- [[Concept - Attention Mechanism]] — the theory this code implements verbatim: $Q$, $K$, $V$ projections, the $1/\sqrt{d_k}$ scale, and why softmax needs fp32.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — this snippet implements plain MHA; that note covers the KV-cache-driven variants (MQA, GQA, MLA) this code deliberately omits.
- [[Snippet - RoPE Implementation]] — the natural next addition to this module: RoPE rotates `q` and `k` right after `split_heads`, before the score matmul.
- [[Gotchas - Implementing Attention]] — the full catalog of bugs this snippet is written to avoid (mask off-by-one, reshape scrambles, missing fp32 upcast, scale errors).
- [[Deep Dive - FlashAttention]] — the fused kernel that computes the identical result as this snippet without ever materializing the `[B,H,T,T]` score tensor in HBM.
- [[Concept - Softmax]] — the fp32-upcast discipline used here is the general stable-softmax pattern applied to attention specifically.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — every line of substance in this module (`qkv_proj`, `q @ k.T`, `attn @ v`, `out_proj`) is a matmul; attention is that primitive composed four times with a mask and a softmax in between.
- [[Concept - Encoder-Decoder and Decoder-Only Architectures]] — the causal mask implemented here is exactly what makes a model decoder-only rather than encoder-style bidirectional.

## Sources
- Vaswani et al. (2017) — "Attention Is All You Need." Section 3.2.1 gives the scaled dot-product formula and the motivation for the $1/\sqrt{d_k}$ scale reproduced here.
