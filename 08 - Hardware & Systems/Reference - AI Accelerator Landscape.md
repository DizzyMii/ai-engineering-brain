---
tags: [reference, domain/hardware-systems, level/core]
aliases: [AI chip landscape, accelerator comparison, GPU vs TPU vs ASIC]
summary: "Date-stamped 2026 spec comparison of NVIDIA GPUs, Google TPUs, AMD MI300, AWS Trainium/Inferentia, and inference ASICs."
---

# Reference - AI Accelerator Landscape

Peak figures are vendor-quoted dense tensor-core numbers unless noted. They're ceilings. Real workloads get 30-60% of peak as [[Concept - Model FLOPs Utilization (MFU)]]. [[Decision - Selecting GPUs for Training and Inference]] turns this table into a buy/rent decision, and the linked Breakdown notes have the architecture behind each row.

## Training-class accelerators: NVIDIA and Google (as of 2026)

| Chip (gen, year) | Peak BF16 TFLOP/s[^1] | Peak FP8/lower TFLOP/s | HBM capacity | HBM bandwidth | Interconnect BW | TDP | Availability |
|---|---|---|---|---|---|---|---|
| A100 (Ampere, 2020) | 312 | INT8: 624 TOPS | 80 GB HBM2e | 2.0 TB/s | NVLink3, ~600 GB/s | 400W | GA, legacy/cost-optimized |
| H100 (Hopper, 2022) | 989 | 1979 (FP8) | 80 GB HBM3 | 3.35 TB/s | NVLink4, ~900 GB/s | 700W | GA, mainstream training/inference |
| H200 (Hopper refresh, 2024) | 989 (same compute die) | 1979 (FP8) | 141 GB HBM3e | 4.8 TB/s | NVLink4, ~900 GB/s | ~700W | GA, memory-bound serving/long-context |
| B200 / GB200 (Blackwell, 2025) | ~2.2x H100 effective training throughput (vendor claim); adds FP4 | FP4 microscaling (MXFP4/NVFP4) | 192 GB HBM3e | ~8 TB/s | NVLink5; GB200 NVL72 rack domain ~130 TB/s | ~1000W (B200 SXM) | Ramping through 2026, allocation-constrained |
| TPU v4 (2021) | ~275/chip | — | 32 GB HBM2 | vendor-quoted | ICI 3D torus, pod = 4096 chips | vendor-quoted | GA, still widely used internally at Google |
| TPU v5p (2023) | higher than v4 (Google spec sheet) | — | ~95 GB HBM2e | ~2.8 TB/s (Google-quoted) | ICI mesh | vendor-quoted | GA, frontier-scale training pods, GCP-only |
| TPU v6 / Trillium (2024) | Google's highest perf/chip TPU to date (company-claimed ~4.7x v5e per chip) | — | smaller per-chip HBM, large pod scale | vendor-quoted | ICI + optical circuit switch (OCS) | vendor-quoted | GA 2024-2025, GCP-only |

[[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]] covers what changed from Hopper to Blackwell (TMA, wgmma, dual-die packaging). [[Breakdown - The Google TPU]] covers the ICI torus, the XLA compile-first model and the OCS reconfiguration behind the TPU rows. Both families get their FLOPs from dedicated matrix units, but different ones: NVIDIA's [[Concept - Tensor Cores]] are warp-collective MMA instructions, while the TPU's [[Concept - Systolic Arrays]] are a fixed 2D MAC grid the operands flow through. That's the biggest architectural split in the table.

## AMD and AWS

| Chip (year) | Peak FLOPs | Memory | Notes |
|---|---|---|---|
| AMD MI300X (2023) | ~1.3 PFLOP/s BF16 dense (AMD-quoted) | 192 GB HBM3 @ ~5.3 TB/s | Largest HBM capacity of any datacenter accelerator at launch; against CUDA, the practical limiter is the ROCm software stack, not the silicon |
| AMD MI325X / MI355 (2024-2025) | successors to MI300X | higher HBM3e capacity/bandwidth | Doubling down on memory capacity over peak FLOPs |
| AWS Trainium2 (2024) | vendor-quoted, not independently benchmarked | vertically integrated with Trn2 UltraServer clusters | Cheaper $/token claim holds only inside AWS; Neuron compiler is materially less mature than CUDA/XLA; underpins Anthropic's "Project Rainier" buildout (announced 2024, hundreds of thousands of chips) |
| AWS Inferentia2 | inference-optimized | — | Cost-optimized `inf2.*` instances for standard (non-frontier) inference workloads |

## Inference specialists: memory-architecture bets, not general accelerators

| System | Architecture | On-chip/on-die memory | Niche |
|---|---|---|---|
| Groq LPU | SRAM-only, deterministic single-core-per-chip dataflow, **no HBM/DRAM at all** | ~230 MB SRAM/chip | Extreme low-latency, jitter-free decode; a model that doesn't fit in one chip's tiny SRAM needs a chain of dozens to hundreds of chips, trading capacity for determinism |
| Cerebras WSE-3 | Wafer-scale engine: one reticle-busting silicon wafer instead of diced chips, ~900k cores | ~44 GB on-die SRAM | Models that fit on-wafer need zero inter-chip network hops; training and inference at extreme single-device scale |
| SambaNova SN40L | Reconfigurable Dataflow Unit (RDU), three-tier memory (SRAM + HBM + DDR) | large effective pool via the DDR tier | Pins huge (MoE) models across a cheap DDR tier instead of scaling pure HBM capacity |

## What the numbers hide

These are the columns vendors put on a slide, and optimizing for them alone is a mistake. [[Decision - Selecting GPUs for Training and Inference]] explains why memory bandwidth and capacity usually run out before peak FLOPs do. A chip with more FLOP/s than you can feed just idles, and that idle time is the [[Concept - Model FLOPs Utilization (MFU)]] gap.

The bigger point is that **software and ecosystem maturity separate these chips more than silicon does.** AMD's MI300X has more HBM than an H100 and competitive quoted FLOPs, and still loses design wins to CUDA's kernel libraries, framework support and institutional habit. [[Concept - The CUDA Moat]] is the name for that. Google's TPU line has been architecturally excellent for a decade and is still GCP-only. AWS Trainium2 is cheap and vertically integrated, but its compiler stack is years behind NVIDIA's. None of this appears in a TFLOP/s column. See also [[Reference - Where Real AI Knowledge Lives]]: chip specs are cheap to publish and expensive to verify, and the know-how for *actually getting* the quoted peak out of a real training or serving workload lives with practitioners, not in datasheets.

Buying the wrong row also hits the balance sheet. Accelerators depreciate on a useful-life assumption (typically 3-6 years), and that assumption is under debate as generations go obsolete faster than the accounting expects. See [[Concept - GPU Depreciation and Compute Capex Accounting]].

## Connections
- [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]] — full architectural detail behind the H100/H200/B200 rows.
- [[Breakdown - The Google TPU]] — full architectural detail behind the TPU rows, including the ICI mesh and XLA compilation model.
- [[Concept - Systolic Arrays]] — the general compute primitive (weight-stationary MAC grid) behind every TPU and most inference ASICs in this table.
- [[Concept - Tensor Cores]] — the competing compute primitive (warp-collective MMA) that gives NVIDIA GPUs their FLOPs.
- [[Decision - Selecting GPUs for Training and Inference]] — turns these raw specs into an actual purchase/rental decision.
- [[Concept - Model FLOPs Utilization (MFU)]] — why the peak numbers in this table overstate delivered performance.
- [[Reference - Where Real AI Knowledge Lives]] — where the practitioner knowledge that separates a datasheet from a working deployment actually lives (cross-domain: ecosystem & history).
- [[Concept - The CUDA Moat]] — the software/ecosystem gap that is the real explanation for why this table isn't decided by FLOPs alone (cross-domain: ecosystem & history).
- [[Concept - GPU Depreciation and Compute Capex Accounting]] — the financial half of "which chip should we buy" that this table only informs the technical half of (cross-domain: AI economics).

## Sources
- NVIDIA — Ampere, Hopper, and Blackwell Architecture Whitepapers (2020, 2022, 2024) — A100/H100/H200/B200 compute, memory, and interconnect specs.
- Google Cloud — TPU v4, v5p, and Trillium (v6) documentation and spec sheets (2021-2024) — per-chip FLOPs, memory, and ICI topology.
- AMD — MI300X datasheet and Instinct architecture briefings (2023) — HBM3 capacity/bandwidth and quoted FLOPs.
- AWS — Trainium2/Neuron and Inferentia2 announcements (2024) — vertically-integrated accelerator positioning; Anthropic "Project Rainier" partnership announcement (2024).
- Groq, Cerebras, SambaNova — public architecture briefings (LPU SRAM-only design; WSE-3 wafer-scale specs; SN40L RDU three-tier memory) — 2023-2024.

[^1]: "Peak BF16 TFLOP/s" is the dense tensor-core number at boost clocks. Several vendors also publish a 2x "sparse" figure that assumes 2:4 structured sparsity, which production models rarely achieve. Compare on the dense figure.
