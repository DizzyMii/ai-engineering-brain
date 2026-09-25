---
tags: [concept, domain/hardware-systems, level/advanced]
aliases: [systolic array, MXU, weight-stationary dataflow]
summary: "The 2D grid-of-MACs dataflow behind TPUs: operands pulse through cell-to-cell, reusing each SRAM read across a whole row without a register file."
---

# Concept - Systolic Arrays

> **One-paragraph hook:** A GPU tensor core reads operand fragments from a register file on every MMA instruction. A systolic array reads a value from SRAM *once* and lets it pass through dozens or hundreds of multiply-accumulate cells as it physically pulses across the chip, with no instruction fetch and no register-file access per MAC. Google built the TPU's matrix unit as a systolic array instead of a GPU-style SIMT core because of that choice, and it's why the two designs differ on perf/watt more than on raw peak FLOPs.

## The mechanism

A systolic array is a rigid $N \times N$ grid of processing elements (PEs), each doing one multiply-accumulate per cycle. Operands enter at the edges and *march* through in lockstep, one cell-to-cell hop per cycle. The name (H.T. Kung and Charles Leiserson, 1978/1982, first proposed for VLSI matrix computation) is an analogy to a heartbeat pumping blood through tissue. TPU v1's MXU was a $256 \times 256$ grid, 65,536 MAC units in one systolic array (Jouppi et al., 2017).

The efficient dataflow is **weight-stationary**. Weights are loaded into the PE grid once and stay put for the whole matmul. Activations stream in from one edge, partial sums accumulate as they cross the array, and results stream out the far edge. Each weight is read from SRAM once and reused for every activation that flows past it, so that read is amortized over the whole streamed dimension of the input with zero extra memory traffic per MAC. Compare a GPU tensor core running `mma.sync`. Every warp-collective MMA instruction still goes through instruction fetch/decode and pulls operand fragments from the register file (see [[Concept - Tensor Cores]]). That's fast but costs something. A systolic array has no instruction stream inside it, only a fixed spatial dataflow, so that per-instruction overhead disappears.

```
Weight-stationary systolic array (4x4, weights preloaded):

        a_in →  [w00]→[w01]→[w02]→[w03]
                  ↓      ↓      ↓      ↓
        a_in →  [w10]→[w11]→[w12]→[w13]
                  ↓      ↓      ↓      ↓
        a_in →  [w20]→[w21]→[w22]→[w23]
                  ↓      ↓      ↓      ↓
        a_in →  [w30]→[w31]→[w32]→[w33]
                  ↓      ↓      ↓      ↓
                 psum   psum   psum   psum  → out

Activations enter from the left, weights are stationary in each PE,
partial sums accumulate downward and exit the bottom edge.
```

For the workload it fits, large regular dense matmul, this buys extreme FLOP/byte and FLOP/watt. The grid is a fixed physical structure, though. Every matmul pays a **pipeline fill/drain cost** of roughly $O(N)$ cycles at the start and end, the time for the first and last operands to cross the array, outside the steady-state throughput. With inner dimension $K \gg N$ that overhead amortizes to nothing. On small or oddly shaped matmuls it can dominate. Dimensions that don't divide evenly into the array's fixed tile size (128×128 or 256×256, depending on generation) get zero-padded to the next multiple. That's the **padding tax**: real PE-cycles spent multiplying zeros.

Weight-stationary is one point in a design space. **Output-stationary** designs hold partial sums fixed in each PE while both operands stream through. **Row-stationary** (Eyeriss; Chen, Emer, and Sze, 2016) picks which operand to hold fixed per layer, to minimize whichever memory traffic dominates for that convolution shape. Deciding what stays stationary means deciding which operand's reuse matters most for the target workload.

## In practice

TPU generations scale this primitive up. v1 used one 256×256 MXU; later generations use several smaller (128×128) MXUs per core, giving up a little per-matmul steady-state efficiency for more flexibility in scheduling work across them (see [[Breakdown - The Google TPU]]). The case is strongest for large, dense, regularly shaped GEMMs and convolutions, which is what a dense transformer's feed-forward and attention-projection matmuls look like at scale. It's weakest for anything irregular. [[Concept - Mixture of Experts Architecture|MoE]] routing sends different token counts to different experts every batch, so each expert's matmul shape is dynamic and rarely lines up with the fixed tile size. Ragged, variable-length attention has the same problem. A GPU's SIMT model with flexible tensor cores pays the per-instruction overhead the systolic array avoids, and in return handles this irregularity without a padding tax. [[Reference - AI Accelerator Landscape]] shows how the trade plays out across the current accelerator lineup.

## Failure modes

**Padding tax.** Matmul dimensions not aligned to the MXU tile size are zero-padded to the next multiple. A matmul with $K=200$ on a 256-wide array wastes 22% of every PE-cycle on padding. Detection: XLA/TPU compiler padding warnings, and MXU utilization well below 100% on shapes that "should" be efficient.

**Pipeline bubble on small matmuls.** Fill/drain overhead of $O(N)$ cycles dominates when the contraction dimension $K$ is about the array size or smaller. Small-batch inference and small per-expert matmuls in MoE both hit this.

**Rigidity under dynamic, irregular workloads.** The array has nothing like a GPU's per-thread branch or variable-length loop. Anything needing data-dependent control flow or ragged shapes (MoE dispatch, variable-length sequences) either breaks into many small, poorly utilized matmuls or needs host/compiler-side padding and bucketing to force regularity.

## The non-obvious

People usually explain the efficiency as "more MACs per chip," but GPUs pack enormous MAC counts into their tensor cores too; H100's tensor cores alone deliver ~989 BF16 TFLOP/s. What a systolic array buys is *no per-instruction overhead*: no register-file read and no instruction dispatch per multiply-accumulate, because there's no instruction stream at all, just a fixed spatial pipeline. So the systolic design wins on FLOP/watt specifically, not FLOP/s, and the accelerator wars are fought on perf/watt even when the marketing talks about peak TFLOPs.

## Connections
- [[Concept - Tensor Cores]] — the GPU's answer to the same problem (dense matmul throughput), solved with flexible per-instruction MMA units instead of a fixed spatial pipeline.
- [[Breakdown - The Google TPU]] — the full system this primitive powers, including how the MXU sits inside the memory model and ICI interconnect.
- [[Reference - AI Accelerator Landscape]] — where systolic-array TPUs sit relative to GPUs and other ASICs on the FLOP/watt and flexibility axes.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the workload (dense GEMM) that systolic arrays are purpose-built to execute at near-peak efficiency.
- [[Concept - The Roofline Model]] — the same arithmetic-intensity reasoning applies inside a systolic array: it is efficient precisely because weight reuse across the row keeps effective intensity high without touching SRAM again.
- [[Concept - GPU Memory Hierarchy]] — contrast case: a GPU stages operands through registers/shared memory/L2/HBM explicitly, where a systolic array reuses a value implicitly via spatial dataflow instead of an explicit cache hierarchy.
- [[Concept - Mixture of Experts Architecture]] — the canonical workload that breaks the systolic array's efficiency assumptions, since expert routing produces irregular, dynamically-shaped matmuls.
- [[Reference - The AI Hardware Market]] — the broader competitive and economic context in which specialized systolic accelerators compete against general-purpose GPUs.
- [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]] — traces how NVIDIA's tensor cores have evolved generation over generation, the direct comparison point for the TPU's fixed MXU design.

## Sources
- Kung, H.T. and Leiserson, C.E. (1978/1982) — "Systolic Arrays for VLSI" — the original systolic-array architecture, proposed for matrix and signal-processing computation in custom VLSI.
- Jouppi, N. et al. (2017) — "In-Datacenter Performance Analysis of a Tensor Processing Unit" (ISCA) — the TPU v1 paper describing the 256×256 systolic MXU and its weight-stationary dataflow.
- Chen, Y.-H., Emer, J., Sze, V. (2016) — "Eyeriss: A Spatial Architecture for Energy-Efficient Dataflow for Convolutional Neural Networks" (ISCA) — the row-stationary dataflow alternative and the general design-space framing of stationary-operand choice.
