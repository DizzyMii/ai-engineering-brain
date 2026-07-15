---
tags: [snippet, domain/hardware-systems, level/frontier]
aliases: [FlashAttention Triton kernel, minimal flash attention, online softmax kernel]
summary: "A runnable forward FlashAttention kernel in Triton showing the online-softmax streaming loop that keeps the N×N score matrix out of HBM."
---

**What it does:** computes a forward pass of scaled dot-product attention with the [[Deep Dive - FlashAttention]] algorithm — streaming key/value blocks past a resident query tile and maintaining a running softmax so the `N×N` score matrix `S = QKᵀ` is **never materialized in HBM**. Supports optional causal masking. This is the pedagogical core of FA1; the production kernels add the v2/v3 machinery this note points to at the end.
**Dependencies:** `torch>=2.1`, `triton>=2.2`, an NVIDIA GPU (Ampere or newer for the `tl.dot` tensor-core path). CUDA only.
**Expected output:** matches a plain PyTorch attention reference to fp16 tolerance (`atol=rtol=1e-2`) for both `causal=False` and `causal=True`, at `HEAD_DIM=64`.

```python
import torch
import triton
import triton.language as tl


@triton.jit
def _flash_attn_fwd(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    H, N_CTX, sm_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    HEAD_DIM: tl.constexpr, CAUSAL: tl.constexpr,
):
    # Grid = (num query blocks, batch*heads). Each program owns one BLOCK_M x HEAD_DIM
    # tile of queries for one (batch, head) and streams all of K/V past it.
    start_m = tl.program_id(0)
    off_zh = tl.program_id(1)
    off_z, off_h = off_zh // H, off_zh % H

    q_base = Q + off_z * stride_qz + off_h * stride_qh
    k_base = K + off_z * stride_kz + off_h * stride_kh
    v_base = V + off_z * stride_vz + off_h * stride_vh
    o_base = O + off_z * stride_oz + off_h * stride_oh

    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)   # query rows this program owns
    offs_d = tl.arange(0, HEAD_DIM)

    # Load the Q tile ONCE. It stays in registers/SRAM for the whole KV loop --
    # this is the reuse that makes the kernel compute-bound instead of streaming Q from HBM.
    q_ptrs = q_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=offs_m[:, None] < N_CTX, other=0.0)

    # Online-softmax running state, kept in fp32 regardless of the fp16 I/O dtype.
    m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)   # running row max
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)                 # running denominator (sum of exp)
    acc = tl.zeros([BLOCK_M, HEAD_DIM], dtype=tl.float32)       # running sum of softmax-weighted V

    # Causal attention: a query at row m only attends to keys n <= m, so blocks
    # entirely above the diagonal contribute nothing -- skip them by ending the loop early.
    n_end = (start_m + 1) * BLOCK_M if CAUSAL else N_CTX

    for start_n in range(0, n_end, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)

        k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=offs_n[:, None] < N_CTX, other=0.0)

        # Score tile S = scale * Q @ Kᵀ  ->  [BLOCK_M, BLOCK_N]. This is the tile
        # that lives and dies in SRAM. The full N x N matrix is never assembled anywhere.
        s = tl.dot(q, tl.trans(k)) * sm_scale

        if CAUSAL:
            s = tl.where(offs_m[:, None] >= offs_n[None, :], s, -float("inf"))

        # ---- the online-softmax recurrence (the entire trick) ----
        m_new = tl.maximum(m_i, tl.max(s, axis=1))   # extend the running max with this block
        alpha = tl.exp(m_i - m_new)                  # how much the OLD running state must shrink
        p = tl.exp(s - m_new[:, None])               # stable exp of this block (max is now 0)

        l_i = l_i * alpha + tl.sum(p, axis=1)        # rescale old denominator, add this block's
        acc = acc * alpha[:, None]                   # rescale the accumulated output...

        v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=offs_n[:, None] < N_CTX, other=0.0)
        acc += tl.dot(p.to(v.dtype), v)              # ...then add this block's PV contribution

        m_i = m_new

    acc = acc / l_i[:, None]                          # normalize by the final denominator, ONCE

    o_ptrs = o_base + offs_m[:, None] * stride_om + offs_d[None, :] * stride_od
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=offs_m[:, None] < N_CTX)


def flash_attention(q, k, v, causal=False):
    # q, k, v: [Z (batch), H (heads), N_CTX, HEAD_DIM]
    Z, H, N_CTX, HEAD_DIM = q.shape
    o = torch.empty_like(q)
    sm_scale = 1.0 / (HEAD_DIM ** 0.5)
    BLOCK_M = BLOCK_N = 64                             # equal blocks keep the causal diagonal simple
    grid = (triton.cdiv(N_CTX, BLOCK_M), Z * H)
    _flash_attn_fwd[grid](
        q, k, v, o,
        *q.stride(), *k.stride(), *v.stride(), *o.stride(),
        H, N_CTX, sm_scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, HEAD_DIM=HEAD_DIM, CAUSAL=causal,
        num_warps=4, num_stages=2,
    )
    return o


if __name__ == "__main__":
    torch.manual_seed(0)
    Z, H, N_CTX, HEAD_DIM = 2, 4, 1024, 64
    q = torch.randn(Z, H, N_CTX, HEAD_DIM, device="cuda", dtype=torch.float16)
    k, v = torch.randn_like(q), torch.randn_like(q)

    for causal in (False, True):
        tri = flash_attention(q, k, v, causal=causal)
        # reference: full-materialization attention in fp32
        scale = 1.0 / (HEAD_DIM ** 0.5)
        s = (q.float() @ k.float().transpose(-1, -2)) * scale
        if causal:
            mask = torch.tril(torch.ones(N_CTX, N_CTX, device="cuda", dtype=torch.bool))
            s = s.masked_fill(~mask, float("-inf"))
        ref = (torch.softmax(s, dim=-1) @ v.float()).to(q.dtype)
        torch.testing.assert_close(tri, ref, atol=1e-2, rtol=1e-2)
        print(f"causal={causal}: match  out={tuple(tri.shape)}")
```

The recurrence in the loop is exact, not approximate: after processing block `j`, `acc / l_i` equals the softmax over all keys seen *so far*. Each new block that raises the running max `m_new` shrinks every previously accumulated term by `alpha = exp(m_old - m_new)`, which is precisely the correction needed to have pretended the true max was `m_new` all along. The [[Snippet - Fused Softmax Kernel in Triton]] does the same max-subtraction stability trick in one shot for a whole row; this kernel streams it across blocks so a row of length 128k never has to fit in one program.

## Why it's written this way

- **fp32 running state (`m_i`, `l_i`, `acc`) with fp16 I/O:** the accumulator sums `BLOCK_N` softmax-weighted value vectors per block across the whole sequence; doing that in fp16 loses bits fast and the rescale-by-`alpha` step compounds it. Q, K, V stay fp16 to hit the tensor-core `tl.dot` path, but everything that accumulates is fp32 — the same operand-fp16/accumulate-fp32 discipline the [[Concept - Tensor Cores|tensor cores]] use internally and that [[Concept - Softmax]] stability demands.
- **Q resident, K/V streamed:** loading the query tile once and looping over K/V blocks is what turns attention from a [[Concept - GPU Memory Hierarchy|memory-bound]] op (naive attention reads/writes the `N×N` score matrix to HBM) into a compute-bound one. The block sizes `BLOCK_M × BLOCK_N × HEAD_DIM` are chosen so `q`, `k`, `v`, and the score tile all fit in shared memory / registers; on Hopper's 228 KB/SM that budget is what caps the tile.
- **`p.to(v.dtype)` before the second `tl.dot`:** the probabilities are computed in fp32 for stability but downcast to fp16 to keep the `PV` matmul on the tensor-core path — a deliberate precision/throughput trade the FA papers make explicitly.
- **Causal early-exit, not just masking:** ending the K/V loop at `(start_m+1)*BLOCK_M` skips every block strictly above the diagonal, roughly halving the work for causal attention; only the diagonal block needs the elementwise `tl.where` mask. Masking without the early-exit computes and discards the upper triangle — correct but 2x slower.

## Connections
- [[Deep Dive - FlashAttention]] — the full algorithm, IO-complexity proof, and the v2/v3 optimizations (warp partitioning, wgmma/TMA) this minimal kernel omits (up-link, advanced).
- [[Concept - Triton]] — the block-programming language and compiler (`tl.load`/`tl.dot`/`tl.where`) this kernel targets (down-link, core).
- [[Snippet - Fused Softmax Kernel in Triton]] — the same max-subtract stability trick done in one pass; this snippet streams it across blocks.
- [[Concept - GPU Memory Hierarchy]] — the shared-memory budget that bounds the block sizes and the HBM round-trips the streaming loop avoids (down-link, core).
- [[Concept - Attention Mechanism]] — the operation being implemented; the math the kernel makes concrete (domain 03, cross-domain).
- [[Concept - Softmax]] — the numerically-stable online-softmax recurrence at the kernel's heart (domain 02, cross-domain).
- [[Concept - Warp Specialization and Async Pipelines on Hopper]] — how the production FA3 kernel reaches peak by overlapping these same matmuls with async loads (up-link, unicorn).

## Sources
- Dao, T. et al. (2022) — "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness" — the tiling + online-softmax + recomputation algorithm this kernel implements.
- Dao, T. (2023) — "FlashAttention-2" — the work-partitioning and sequence-parallel improvements the production kernel adds.
- OpenAI Triton fused-attention tutorial (triton-lang.org) — the standard Triton structure this minimal version is distilled from.
