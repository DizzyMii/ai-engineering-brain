---
tags: [concept, domain/foundations, level/core]
aliases: [GEMM, matmul]
summary: "Every dense layer, attention op, and convolution lowers to GEMM; 2mnk FLOPs and arithmetic intensity set DL's entire cost model."
---

# Concept - Matrix Multiplication as the Atom of Deep Learning

> **One-paragraph hook:** Strip away the framework and every deep network is a chain of general matrix multiplies (GEMMs) with cheap elementwise glue between them. This is not a simplification — it is the reason GPUs won ([[Concept - Why GPUs for Deep Learning]]), the unit in which training budgets are denominated, and the lens through which every performance question ("why is decode slow?", "why is LoRA cheap?") has a one-line answer. If you can count a GEMM's FLOPs and bytes, you can predict the cost of almost anything in this field before running it.

## The mechanism

**Everything lowers to GEMM.** A dense layer is $Y = XW$. The [[Concept - Attention Mechanism]] is two batched matmuls with a softmax between them: $S = QK^\top/\sqrt{d_k}$, then $O = \text{softmax}(S)\,V$ — the insight that [[Deep Dive - FlashAttention]] exploits by tiling them. Convolution is lowered to matmul via im2col (Chellapilla et al. 2006): unroll each receptive field into a row (at a $k_h k_w$ memory duplication cost) and the convolution becomes one big GEMM. Even embedding lookups are matmuls against one-hot vectors, specialized into gathers.

**FLOP counting.** An $(m \times k)(k \times n)$ matmul costs $2mnk$ FLOPs ($mnk$ multiply-accumulates, 2 FLOPs each). For transformers this rolls up into the rule every compute budget is built on: **~6 FLOPs per parameter per token** — 2 in the forward pass (each weight participates in one MAC per token) and 4 in the backward, because backprop runs *two* GEMMs per layer, $\partial L/\partial X = \partial L/\partial Y \cdot W^\top$ and $\partial L/\partial W = X^\top \cdot \partial L/\partial Y$. Hence total training compute $C \approx 6ND$ for $N$ parameters and $D$ tokens (Kaplan et al. 2020) — the accounting identity underneath [[Concept - Scaling Laws]]. Worked example: Llama 2 70B on 2T tokens is $6 \times 7\times10^{10} \times 2\times10^{12} \approx 8.4\times10^{23}$ FLOPs. Caveat: 6ND ignores the $QK^\top$/$PV$ score matmuls, which is fine while context length is small relative to model width and materially wrong at 100k+ contexts.

**Arithmetic intensity decides speed.** Intensity = FLOPs / bytes moved. A square $n \times n$ GEMM does $2n^3$ FLOPs over $\sim 3 \cdot 2n^2$ bytes (bf16), so intensity grows like $n/3$ — big GEMMs are compute-bound and can approach [[Concept - Tensor Cores]] peak. A batch-1 matrix-vector product (every decode-step matmul in LLM inference) does 2 FLOPs per 2-byte weight read: intensity ≈ 1 FLOP/byte. On an H100 SXM (~989 TFLOPS dense bf16, 3.35 TB/s HBM, ridge point ~295 FLOPs/byte on [[Concept - The Roofline Model]]), a GEMV therefore tops out around 3.35 TFLOPS — **~0.3% of peak**. Same operation, same hardware, 300× apart purely on shape. This single number explains why inference servers batch requests and why decode is priced by memory bandwidth, not FLOPs ([[Concept - GPU Memory Hierarchy]]).

**Layout and alignment.** Row-major vs column-major, strides, and contiguity decide which kernel you get. Tensor cores consume fixed-size fragments and want M/N/K divisible by 8/16 (and libraries pad vocab dims to multiples of 64/128); a transpose or non-contiguous slice can silently force a copy or a slow non-tensor-core path. nanoGPT pads GPT-2's 50257-token vocab to 50304 ($= 64 \times 786$) purely for this alignment — Karpathy reported roughly a 25% training speedup from that one change.

**Associativity is a cost lever, not a math change.** $(AB)C$ and $A(BC)$ are mathematically identical and computationally wildly different. Low-rank update $\Delta W x = (UV)x$ with $U \in \mathbb{R}^{d\times r}, V \in \mathbb{R}^{r \times d}$, $d{=}4096$, $r{=}16$: forming $UV$ first costs $2d^2r \approx 5.4\times10^8$ FLOPs; computing $U(Vx)$ costs $4dr \approx 2.6\times10^5$ — a ~2000× difference. This parenthesization *is* why [[Deep Dive - LoRA]] adapters are nearly free at training time. The same spectral thinking (what a matrix does along its principal directions) is formalized by the [[Concept - Singular Value Decomposition]].

**Accumulation precision.** A matmul sums $k$ products, and rounding error grows roughly like $\sqrt{k}\,\varepsilon$; with $k = 4096$–$16384$ in modern layers and bf16's $\varepsilon \approx 7.8\times10^{-3}$, accumulating in bf16 would lose the tail of the sum outright. This is why tensor cores take bf16/fp16 *inputs* but accumulate in fp32 ([[Concept - Floating Point for Deep Learning]]), and why "which precision?" is really two questions — multiply precision and accumulate precision ([[Gotchas - Numerical Stability]]).

## In practice

- Budgeting: every pretraining plan starts from $C \approx 6ND$; every inference cost model starts from 2 FLOPs/param/token and weight bytes/token for decode.
- Utilization: well-tuned large training runs report 40–50% MFU (PaLM: 46.2% — Chowdhery et al. 2022); decode-phase inference sits orders of magnitude below peak FLOPs for the GEMV reason above, and that's expected, not a bug.
- Shapes: pick head dims of 64/128, pad vocab and hidden sizes to alignment-friendly multiples, call `.contiguous()` before hot matmuls, and check `tensor.stride()` when a permute precedes a matmul.

## Failure modes

- **Silent broadcast bugs.** A $(n,1)$ vs $(n,)$ shape slip turns an intended elementwise multiply into an outer product; loss still goes down, model is just worse. Detection: assert shapes at module boundaries, and unit-test with distinct prime dimensions ($m \ne k \ne n$) so any transposition error becomes a hard shape error instead of a silent one.
- **Non-contiguous inputs, 10× slower.** A view/permute upstream forces copies or non-tensor-core kernels. Detection: profiler shows unexpected `copy_`/`cat` kernels or a `sgemm` where you expected an `hgemm`/bf16 tensor-core kernel.
- **Mixed-dtype upcasting.** One stray fp32 tensor in a bf16 model drags the matmul onto the fp32 path (or inserts cast copies): 2× the memory traffic, no low-precision tensor cores. NumPy/JAX promote silently; PyTorch autocast rewrites dtypes per-op, so the mismatch hides. Detection: dtype audit plus profiler kernel names.
- **Misaligned dims.** An odd hidden size or unpadded vocab quietly falls off the tensor-core fast path. Detection: measured TFLOPS far below roofline prediction for the shape.

## The non-obvious

FLOPs are the wrong mental unit for half of your problems: a GEMM's speed is set by its *shape*, not its FLOP count. Cutting FLOPs in a memory-bound matmul (decode) saves nothing — the weights still get read once per token — while cutting bytes (quantization, batching to fatten the GEMM) is worth exactly what the roofline says it is. Staff-level habit: before optimizing any matmul, classify it — left of the ridge point, optimize bytes; right of it, optimize FLOPs.

## Connections

- [[Concept - Why GPUs for Deep Learning]] — GPUs won because they execute exactly this one operation at extreme throughput; the atom explains the hardware.
- [[Concept - Vector Norms and Distances]] — the dot product is the matmul's inner loop; its accumulation-error behavior is inherited by every GEMM.
- [[Concept - The Roofline Model]] — the formal version of the intensity argument here; ridge point vs GEMM shape predicts achieved throughput.
- [[Concept - Tensor Cores]] — the hardware unit that executes GEMM fragments, and the source of the alignment and accumulate-in-fp32 rules.
- [[Concept - GPU Memory Hierarchy]] — where the "bytes moved" in arithmetic intensity actually come from and why HBM bandwidth caps GEMV.
- [[Deep Dive - FlashAttention]] — attention's two matmuls tiled to keep the score matrix in SRAM; the canonical example of optimizing bytes instead of FLOPs.
- [[Concept - Attention Mechanism]] — the layer that is "two batched matmuls plus a softmax"; its cost model follows directly from this note.
- [[Concept - Scaling Laws]] — built on the 6ND FLOP accounting derived here; compute-optimal training is GEMM arithmetic at planetary scale.
- [[Deep Dive - LoRA]] — the associativity example made into a method: never materialize $UV$, always compute $U(Vx)$.
- [[Concept - Singular Value Decomposition]] — the decomposition that explains what a weight matrix does per direction, and why low-rank chains approximate it.
- [[Concept - Floating Point for Deep Learning]] — the precision formats whose range/precision tradeoffs dictate multiply-vs-accumulate choices.
- [[Gotchas - Numerical Stability]] — the catalog of reduction-error pathologies that fp32 accumulation exists to prevent.

## Sources

- Kaplan et al. (2020) — "Scaling Laws for Neural Language Models" — the C ≈ 6ND FLOP accounting in the appendix.
- Hoffmann et al. (2022) — "Training Compute-Optimal Large Language Models" (Chinchilla) — the budget allocation built on that accounting.
- Chellapilla et al. (2006) — "High Performance Convolutional Neural Networks for Document Processing" — im2col lowering of convolution to GEMM.
- Williams et al. (2009) — "Roofline: An Insightful Visual Performance Model" — the intensity/bandwidth framework used here.
- Hu et al. (2021) — "LoRA: Low-Rank Adaptation of Large Language Models" — the low-rank parenthesization win in production form.
- Chowdhery et al. (2022) — "PaLM" — the 46.2% MFU reference point for large-scale training efficiency.
- Micikevicius et al. (2017) — "Mixed Precision Training" — the low-precision multiply / fp32 accumulate discipline.
