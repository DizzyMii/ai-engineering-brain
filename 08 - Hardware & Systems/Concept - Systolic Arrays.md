---
tags: [concept, domain/hardware-systems, level/advanced]
aliases: [systolic array, MXU, weight-stationary dataflow]
summary: "The 2D grid-of-MACs dataflow behind TPUs: operands pulse through cell-to-cell, reusing each SRAM read across a whole row without a register file."
---

# Concept - Systolic Arrays

> **One-paragraph hook:** A GPU tensor core reads operand fragments from a register file on every MMA instruction; a systolic array reads a value from SRAM *once* and lets it echo through dozens or hundreds of multiply-accumulate cells as it physically pulses across the chip — no instruction fetch, no register-file access, per MAC. That single architectural choice is why Google built the TPU's matrix unit as a systolic array instead of a GPU-style SIMT core, and why perf/watt, not raw peak FLOPs, is the axis on which the two designs actually differ.

## The mechanism

A systolic array is a rigid $N \times N$ grid of processing elements (PEs), each capable of one multiply-accumulate per cycle. Operands are fed in from the array's edges and *march* through it in lockstep, one cell-to-cell hop per cycle — the "systolic" name (H.T. Kung and Charles Leiserson, 1978/1982, originally proposed for VLSI matrix computation) is a direct analogy to a heartbeat pumping data through tissue. TPU v1's MXU was a $256 \times 256$ grid — 65,536 MAC units in a single systolic array (Jouppi et al., 2017).

The dataflow that makes this efficient is **weight-stationary**: weights are loaded into the PE grid once and held fixed for the duration of a matmul; activations stream in from one edge, partial sums accumulate as they flow across the array, and results stream out the far edge. Each weight, once loaded, is read from SRAM exactly once and then reused for every activation value that flows past it — the SRAM read is amortized over the entire streamed dimension of the input, with zero additional memory-system traffic per MAC. Contrast this with a GPU tensor core executing `mma.sync`: every warp-collective MMA instruction still goes through instruction fetch/decode and pulls operand fragments from the register file (see [[Concept - Tensor Cores]]), which is fast but not free — a systolic array eliminates that per-instruction overhead entirely because there is no instruction stream inside the array, only a fixed spatial dataflow.

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

This buys extreme FLOP/byte and FLOP/watt for the workload it fits: large, regular dense matmul. But the grid is a fixed physical structure, and every matmul pays a **pipeline fill/drain cost** of roughly $O(N)$ cycles at the start and end — the time for the first/last operand to traverse the array — before/after the steady-state throughput kicks in. For a matmul with inner dimension $K \gg N$, this overhead amortizes to nothing; for small or irregularly-shaped matmuls it can dominate. Dimensions that don't divide evenly into the array's fixed tile size (128×128 or 256×256, depending on generation) must be zero-padded up to the next multiple — the **padding tax** — wasting real PE-cycles computing against zeros.

Weight-stationary is one point in a design space. **Output-stationary** designs hold partial sums fixed in each PE while both operands stream through; **row-stationary** (Eyeriss — Chen, Emer, and Sze, 2016) chooses the operand to hold fixed adaptively per layer to minimize whichever memory traffic dominates for that specific convolution shape. The choice of "what stays stationary" is really a choice about which operand's reuse matters most for the target workload.

## In practice

TPU generations scale this primitive up: v1 used a single 256×256 MXU; later generations use smaller (128×128) MXUs, multiple per core, trading a bit of per-matmul steady-state efficiency for more flexibility in how work is scheduled across them (see [[Breakdown - The Google TPU]]). The efficiency case is strongest for large, dense, regularly-shaped GEMMs and convolutions — exactly what a dense transformer's feed-forward and attention-projection matmuls look like at scale — and weakest for anything irregular: [[Concept - Mixture of Experts Architecture|MoE]] routing sends different token counts to different experts every batch, meaning the matmul shape at each expert is dynamic and rarely lines up with the array's fixed tile size; ragged, variable-length attention has the same problem. A GPU's SIMT model plus flexible tensor cores pays a per-instruction overhead the systolic array avoids, but in exchange handles exactly this irregularity without a padding tax — see [[Reference - AI Accelerator Landscape]] for how this tradeoff plays out across the current accelerator lineup.

## Failure modes

**Padding tax:** matmul dimensions not aligned to the MXU's tile size are zero-padded up to the next multiple; a matmul with $K=200$ against a 256-wide array wastes 22% of every PE-cycle on padding. Detection: XLA/TPU compiler padding warnings and MXU-utilization telemetry well below 100% on shapes that "should" be efficient.

**Pipeline bubble on small matmuls:** fill/drain overhead of $O(N)$ cycles dominates when the matmul's contraction dimension $K$ is comparable to or smaller than the array size — small-batch inference or small per-expert matmuls in MoE both trigger this.

**Rigidity under dynamic/irregular workloads:** the array has no mechanism analogous to a GPU's per-thread branch or variable-length loop; anything requiring data-dependent control flow or ragged shapes (MoE dispatch, variable-length sequences) either serializes into many small, poorly-utilized matmuls or requires host/compiler-side padding and bucketing to force regularity.

## The non-obvious

The efficiency story is usually told as "more MACs per chip," but GPUs also pack enormous MAC counts into their tensor cores — H100's tensor cores alone deliver ~989 BF16 TFLOP/s. The real differentiator a systolic array buys isn't MAC count, it's the *elimination of per-instruction overhead*: no register-file read, no instruction dispatch, per multiply-accumulate, because the array has no instruction stream at all — just a fixed spatial pipeline. That's why the systolic design wins on FLOP/watt specifically, not FLOP/s, and why the accelerator wars are fundamentally fought on the perf/watt line even when marketing emphasizes peak TFLOPs.

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
