---
tags: [reference, domain/ecosystem-history, level/advanced]
aliases: [GPU market, AI chip market, AI accelerator market, compute supply chain]
summary: "Market structure of AI compute as of 2026: NVIDIA's share, the TSMC/HBM supply chain, export controls, and the challengers."
---

# Reference - The AI Hardware Market

## NVIDIA datacenter GPU lineage

| Chip | Launch | Memory | Approx. street price (as of 2026) | Note |
|---|---|---|---|---|
| A100 | 2020 | 40/80GB HBM2e | ~$10-15k (now secondary market) | The workhorse that trained GPT-3-era and OPT-175B-era models |
| H100 | 2022 | 80GB HBM3 | ~$25-40k | The current large-scale training default; the chip export controls target |
| H200 | 2024 | 141GB HBM3e | Premium over H100 | Memory-bandwidth bump aimed at inference and larger KV caches |
| GH200 (Grace Hopper Superchip) | 2023-24 | Combined CPU+GPU with NVLink-C2C | Sold as modules/systems, not per-chip | Unified CPU-GPU memory; targets large-model inference |
| B200 / GB200 (Blackwell) | 2024-25 | Larger HBM3e pools, NVL72 rack-scale | System-level pricing (racks, not chips) | The generation that moved unit economics from "GPU" to "rack" |

NVIDIA holds roughly **80-90% of the AI training accelerator market** (as of 2026) and its datacenter segment has been the single largest driver of the company's revenue growth since 2023 — the market's center of gravity sits entirely in this one product line.

## The real bottleneck: packaging and memory, not transistors

| Chokepoint | Who controls it | Why it gates supply |
|---|---|---|
| Advanced packaging (CoWoS) | TSMC | Stacking compute die + HBM stacks requires CoWoS capacity that scales much slower than wafer starts; TSMC's CoWoS lines, not its 4nm/3nm fabs, have been the binding constraint on GPU shipments |
| Leading-edge logic | TSMC (4nm/3nm nodes for Hopper/Blackwell) | Single-source; Samsung and Intel Foundry trail on yield for these nodes |
| HBM (High-Bandwidth Memory) | SK Hynix (leading), Samsung, Micron | HBM3E capacity is the other gating resource — every AI accelerator (NVIDIA, AMD, TPU, Trainium) competes for the same three suppliers' output |

The practical consequence: NVIDIA can design a faster chip faster than the supply chain can package and memory-stack it. Lead times for large training clusters have historically run 6-12+ months, driven by CoWoS and HBM allocation rather than chip fabrication.

## Export controls

| Rule | Date | Effect |
|---|---|---|
| Initial US export control rule | Oct 2022 | Banned direct sale of top-tier accelerators (A100, H100-class) to China above defined performance-density thresholds |
| Tightened rule | Oct 2023 | Closed the loophole that let throttled parts squeak under the original thresholds; tightened the performance-density formula |
| China-specific throttled SKUs | Ongoing | A800/H800 (reduced NVLink interconnect bandwidth vs. A100/H100), H20 (reduced compute, higher memory bandwidth) — NVIDIA's compliant-but-degraded China lineup, periodically revised or banned outright as rules tighten further |
| Grey market | Ongoing | Smuggling and third-country reshipment of controlled chips persists despite enforcement; a standing cat-and-mouse dynamic, not a solved problem |

[[Breakdown - DeepSeek]] trained its early models on H800s specifically because that was the highest-tier chip legally available in China at the time — the export-controlled hardware constraint is a first-order fact of that story, not a footnote.

## Challengers and why they lag

| Challenger | Approach | Where it's stuck |
|---|---|---|
| AMD MI300X / MI325 | Direct NVIDIA competitor, strong raw specs | ROCm's software gap — see [[Concept - The CUDA Moat]] — not silicon |
| Intel Gaudi | Direct competitor | Weak ecosystem pull, repeated roadmap resets |
| Cerebras | Wafer-scale single chip (avoids interconnect entirely) | Niche use cases; software targeting is narrow |
| Groq (LPU) | Deterministic, ultra-low-latency inference chip | Attacks inference only, not training |
| SambaNova | Reconfigurable dataflow architecture | Also inference-first; small deployed base |
| Tenstorrent | Open, RISC-V-adjacent architecture (Jim Keller) | Early-stage; software stack still maturing |

Note the pattern: every merchant-silicon challenger that has gained real traction (Groq, SambaNova, Cerebras) attacks **inference**, not training — because the CUDA moat is shallowest there (see [[Concept - The CUDA Moat]]).

## Hyperscaler in-house silicon — the real threat

| Chip | Owner | Status |
|---|---|---|
| TPU v5 / v6 (Trillium) | Google DeepMind / Google Cloud | Trains and serves Gemini internally; the only in-house silicon with a full non-CUDA software stack (JAX/XLA) proven at frontier scale |
| Trainium / Inferentia | Amazon | Used for internal workloads and offered on AWS as a cheaper alternative to NVIDIA instances |
| Maia | Microsoft | Targets Azure's own inference/training workloads |
| MTIA | Meta | Internal recommendation and inference workloads, expanding scope |

Vertical integration — owning silicon, compiler, and the model workload end to end — is the only strategy so far that has actually routed production frontier training around CUDA (see [[Concept - The CUDA Moat]] for why JAX+XLA-on-TPU is the proof that the moat is porous when one company owns the whole stack).

## The neocloud tier

CoreWeave, Lambda, Crusoe, and Nebius finance and operate GPU-as-a-service fleets, competing for NVIDIA allocation rather than trying to unseat NVIDIA. On-demand H100 pricing has run roughly **$2-8/hour** depending on spot vs. reserved commitment and provider, with the acute 2023 shortage pricing easing considerably by 2025 as Blackwell supply ramped and hyperscaler capex diversified.

## Power as the new binding constraint

By 2025-2026 the conversation shifted from "how many GPUs can you get" to "how many gigawatts can you interconnect to the grid." Frontier training clusters are increasingly quoted in **megawatts** rather than chip counts, and grid interconnect queues — not chip allocation — have become the long pole for new datacenter buildouts. See [[Concept - Cost Engineering for LLM Applications]] for where this shows up on the inference-cost side.

*Date-stamp aggressively: pricing, export-control specifics, and the challenger roster all churn quarterly. Treat every number above as "as of 2026" unless it's a fixed historical launch date.*

## Connections
- [[Concept - The CUDA Moat]] — the market-share numbers here are the effect; the CUDA moat is the software mechanism that sustains them.
- [[Reference - The AI Lab Landscape]] — compute access is a first-order determinant of which labs can compete at the frontier at all.
- [[Breakdown - DeepSeek]] — the concrete case study of a lab training a frontier model under export-control-constrained hardware.
- [[Concept - GPU Memory Hierarchy]] — the HBM figures in this market note (capacity, bandwidth) are the same numbers that drive on-chip memory-hierarchy engineering.
- [[Concept - Tensor Cores]] — the compute throughput this market prices per chip is delivered by tensor cores, not general-purpose CUDA cores.
- [[Concept - Cost Engineering for LLM Applications]] — hardware market prices are the raw input to per-token inference cost modeling.

## Sources
- US Bureau of Industry and Security (BIS) — Export Administration Regulations updates, October 2022 and October 2023 rules on advanced computing items to China.
- NVIDIA — quarterly datacenter segment revenue disclosures (investor relations filings).
- TSMC — CoWoS advanced-packaging capacity commentary in quarterly earnings calls.
