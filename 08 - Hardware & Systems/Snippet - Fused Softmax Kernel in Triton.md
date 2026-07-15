---
tags: [snippet, domain/hardware-systems, level/advanced]
aliases: []
summary: "A runnable Triton kernel that fuses row-max, exp, sum, and divide into one bandwidth-bound pass, replacing four HBM round-trips with one."
---

**What it does:** computes a numerically-stable row-wise softmax over a 2D tensor in a single fused [[Concept - Triton]] kernel — one read of the row, one write, versus the four-to-five separate HBM passes `torch.softmax`'s unfused equivalent would need if you built it from primitive ops.
**Dependencies:** `torch>=2.1`, `triton>=2.1` (ships with recent PyTorch; `pip install triton` on Linux/CUDA).
**Expected output:** matches `torch.softmax(x, dim=1)` to within float32 tolerance (`torch.allclose(..., atol=1e-5)` passes) and is measurably faster than an unfused eager-mode softmax on rows that don't fit in L1/registers, because it is bandwidth-bound and this kernel touches HBM half as many times.

```python
import torch
import triton
import triton.language as tl


@triton.jit
def _softmax_kernel(
    out_ptr, in_ptr,
    in_row_stride, out_row_stride,
    n_cols,
    BLOCK_SIZE: tl.constexpr,
):
    # One program instance = one row. Grid is launched with one program per row.
    row_idx = tl.program_id(0)

    row_start_ptr_in = in_ptr + row_idx * in_row_stride
    row_start_ptr_out = out_ptr + row_idx * out_row_stride

    col_offsets = tl.arange(0, BLOCK_SIZE)
    mask = col_offsets < n_cols  # guards the ragged tail when n_cols < BLOCK_SIZE

    # Single load of the row. Out-of-bounds lanes read -inf so they never win the max
    # and contribute exp(-inf) = 0 to the sum -- the mask does double duty.
    row = tl.load(row_start_ptr_in + col_offsets, mask=mask, other=-float("inf"))

    # Max-subtraction stability trick: without it, exp() of a moderately large
    # logit (e.g. 30+ in fp16) overflows to inf and the whole row becomes NaN
    # after the divide. Subtracting the row max makes the largest exponent 0.
    row_max = tl.max(row, axis=0)
    row_minus_max = row - row_max

    numerator = tl.exp(row_minus_max)
    # Accumulate the sum in fp32 even if the I/O dtype is fp16 -- summing many
    # fp16 values loses precision fast, and the sum feeds a division that
    # every output element depends on.
    denominator = tl.sum(numerator, axis=0)
    result = numerator / denominator

    tl.store(row_start_ptr_out + col_offsets, result, mask=mask)


def triton_softmax(x: torch.Tensor) -> torch.Tensor:
    assert x.ndim == 2 and x.is_cuda
    n_rows, n_cols = x.shape
    out = torch.empty_like(x)

    # BLOCK_SIZE must be >= n_cols since this is a single-block-per-row kernel
    # (no cross-block reduction). Round up to the next power of 2 -- Triton
    # requires power-of-2 block sizes for tl.arange.
    BLOCK_SIZE = triton.next_power_of_2(n_cols)

    # More warps for wider rows so the single block has enough parallelism
    # to hide the load latency; a heuristic, not a law -- @triton.autotune
    # would sweep this properly in production code.
    num_warps = 4
    if BLOCK_SIZE >= 2048:
        num_warps = 8
    if BLOCK_SIZE >= 4096:
        num_warps = 16

    _softmax_kernel[(n_rows,)](
        out, x,
        x.stride(0), out.stride(0),
        n_cols,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=num_warps,
    )
    return out


if __name__ == "__main__":
    torch.manual_seed(0)
    x = torch.randn(1823, 781, device="cuda", dtype=torch.float32)

    out_triton = triton_softmax(x)
    out_torch = torch.softmax(x, dim=1)

    torch.testing.assert_close(out_triton, out_torch, atol=1e-5, rtol=1e-5)
    print("correctness OK:", out_triton.shape, out_triton.dtype)

    # Rough bandwidth-bound timing comparison
    import triton.testing as tt
    ms_triton = tt.do_bench(lambda: triton_softmax(x))
    ms_torch = tt.do_bench(lambda: torch.softmax(x, dim=1))
    print(f"triton: {ms_triton:.4f} ms   torch: {ms_torch:.4f} ms")
```

This kernel is deliberately single-block-per-row: `BLOCK_SIZE` must cover the whole row, so it caps out once a row's width times its dtype size exceeds what fits comfortably in registers/shared memory for the chosen `num_warps` (roughly tens of thousands of columns before a two-pass, cross-block reduction — the streaming pattern in [[Snippet - A Minimal FlashAttention Kernel in Triton]] — becomes necessary). For LLM-sized softmaxes over a vocabulary (32k-256k columns) or an attention row (context length), this single-block design is exactly the regime FlashAttention's online-softmax recurrence generalizes: the same max-subtract-and-rescale trick, just streamed across blocks instead of held in one.

## Why it's written this way

- **Masking with `other=-float("inf")` on load, not after:** padding lanes with `-inf` before the max reduction means they can never become the row max, and `exp(-inf - anything) = 0` automatically zeroes their contribution to the sum — one mask value does the job of two separate correctness checks.
- **fp32 accumulation of the sum regardless of I/O dtype:** [[Concept - Softmax]]'s division step means every output element inherits the sum's rounding error; summing a wide fp16 row in fp16 can lose several bits of precision, so the reduction is carried in fp32 (Triton's `tl.sum` promotes by default) even when `x` itself is fp16 — the same accumulate-high-precision discipline tensor cores use internally.
- **One program per row, not per element or per tile:** this maps directly onto the memory-access pattern — each row is contiguous in the common `[batch, vocab]` or `[batch, seqlen]` layout, so one program reading and writing one contiguous stretch gives fully [[Concept - GPU Memory Hierarchy|coalesced]] access with zero cross-program communication.
- **The fusion itself is the entire performance story:** an unfused `max` → `sub` → `exp` → `sum` → `div` pipeline in eager PyTorch touches HBM once per op (read+write each), roughly 8-10 tensor-sized memory transactions; this kernel does 1 read + 1 write. Per the [[Concept - The Roofline Model]], softmax is deeply memory-bound (O(1) arithmetic intensity — a handful of FLOPs per element loaded), so this ~4-5x cut in HBM traffic translates almost linearly into wall-clock speedup, not the modest gain fusion gives a compute-bound GEMM.

## Connections
- [[Concept - Triton]] — the block-programming language and compiler this kernel is written in; `tl.load`/`tl.store`/`tl.arange` are its core primitives.
- [[Concept - Kernel Fusion]] — the general principle this snippet is a worked example of: collapsing N memory-bound ops into one kernel to cut HBM round-trips.
- [[Concept - Softmax]] — the mathematical operation being implemented, including why the max-subtraction stability trick is necessary.
- [[Concept - The Roofline Model]] — the reasoning for why fusing this specific op yields a near-linear speedup: softmax sits deep in the memory-bound region.
- [[Snippet - A Minimal FlashAttention Kernel in Triton]] — the streaming generalization of this same max-rescale trick across blocks, for rows too large to hold in one program.
- [[Concept - GPU Memory Hierarchy]] — the coalesced-read/coalesced-write pattern this kernel relies on and the register/shared-memory budget that bounds `BLOCK_SIZE`.
- [[Gotchas - Numerical Stability]] — the max-subtraction trick implemented here is the canonical fix for the overflow failure mode that note catalogs generally.

## Sources
- Tillet, P. et al. (2019) — "Triton: An Intermediate Language and Compiler for Tiled Neural Network Computations" — the language and compiler this kernel targets.
- OpenAI Triton tutorials (triton-lang.org) — the fused-softmax tutorial this pattern is a standard variant of.
