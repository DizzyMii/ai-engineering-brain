---
tags: [concept, domain/hardware-systems, level/frontier]
aliases: [NVL72, GB200 NVL72, NVLink domain, scale-up domain, rack-scale GPU]
summary: "Extending the NVLink scale-up domain from an 8-GPU node to a 72-GPU rack, moving the bandwidth cliff and rewriting parallelism math."
---
> **One-paragraph hook:** For a decade the unit of "one big GPU" was the 8-GPU node — eight cards fully connected by NVSwitch, and a ~15x bandwidth cliff the moment traffic left the box onto [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)|InfiniBand]]. That cliff, sitting at 8 GPUs, is the single fact that has dictated distributed-training layout since Megatron: keep bandwidth-hungry tensor and expert parallelism *inside* the node, spread everything else across the slow network. Rack-scale systems — NVIDIA's GB200 NVL72 being the canonical 2025 example — move the cliff from 8 GPUs to 72 by extending the NVLink fabric across an entire liquid-cooled rack, presenting all 72 GPUs as one coherent, high-bandwidth memory-and-compute pool. That re-plumbing changes which parallelism strategies are cheap, not just how fast the existing ones run.

## The mechanism

An **NVLink domain** is the set of GPUs that can address each other's HBM directly over NVLink at NVLink speed, routed through NVSwitch silicon, without a single byte touching the scale-out network. Historically this domain *was* the node: 8 H100s on an HGX baseboard, each with ~900 GB/s of NVLink4 (18 links × 50 GB/s), all-to-all through on-board NVSwitches. Beyond 8, you hit the [[Concept - Anatomy of an AI Training Cluster|two-tier network]] — InfiniBand NDR at ~400 Gb/s ≈ 50 GB/s per GPU — an ~18x drop in per-GPU bandwidth the instant you leave the baseboard.

GB200 NVL72 collapses that boundary. Seventy-two Blackwell GPUs (paired with 36 Grace CPUs across 18 compute trays) connect through nine NVLink Switch trays over a copper cable backplane, forming one NVLink domain with **NVLink5 at 1.8 TB/s per GPU** and roughly **130 TB/s of aggregate all-to-all bandwidth** across the rack. Every GPU can read or write every other GPU's HBM at ~1.8 TB/s — two orders of magnitude faster than the InfiniBand that used to separate them.

```
  OLD: the node is the domain (Hopper HGX)          NEW: the rack is the domain (GB200 NVL72)

   ┌───────── 8-GPU NVLink island ─────────┐         ┌────────── 72-GPU NVLink domain ──────────┐
   │  G0 G1 G2 G3 G4 G5 G6 G7               │         │  G0 ... G71  (all-to-all ~130 TB/s agg)   │
   │  all-to-all ~900 GB/s/GPU (NVSwitch)   │         │  ~1.8 TB/s per GPU over NVLink5           │
   └───────────────┬───────────────────────┘         │  ~13.5 TB pooled HBM3e                    │
                   │  cliff: ~50 GB/s/GPU             └───────────────┬──────────────────────────┘
              InfiniBand NDR (18x drop)                               │  cliff now here (moved 8 → 72)
                   │                                             InfiniBand / Ethernet scale-out
              other nodes                                             │
                                                                 other racks
```

Two structural consequences follow.

**Memory pooling.** Because NVLink is load/store-addressable, the 72 GPUs' HBM becomes one fast pool: 72 × 192 GB HBM3e ≈ **13.5 TB** reachable at NVLink bandwidth. A model plus its optimizer state, or an enormous [[Concept - KV Cache]], that would never fit in one GPU's 192 GB and would be crippled by paging over InfiniBand, now spreads across the domain while every shard stays one NVLink hop away. GB200 additionally couples each Grace CPU to its GPUs over NVLink-C2C at 900 GB/s coherent, extending the pool into ~480 GB of LPDDR per superchip for offload.

**The parallelism map is rewritten.** [[Concept - Tensor and Pipeline Parallelism|Tensor parallelism]] all-reduces activations on *every* layer, and [[Concept - Expert Parallelism|expert parallelism]] does an all-to-all dispatch on every MoE layer — both are bandwidth-bound [[Concept - All-Reduce and Collective Operations|collectives]] that were effectively capped at degree 8 because degree 9 meant crossing the cliff. In a 72-GPU domain, TP and EP can span far more GPUs while staying on NVLink, so the optimal (TP, EP, PP, DP) decomposition shifts toward much wider TP/EP and away from the pipeline/data parallelism you previously used to avoid the network. For a large [[Concept - Mixture of Experts Architecture|mixture-of-experts]] model, the all-to-all expert dispatch — the most punishing collective in the stack — becomes an in-domain operation, which is precisely why DeepSeek-V3-style MoE serving benefits so directly from a large scale-up domain.

## In practice

- **Silicon:** GB200 NVL72 = 72 B200 GPUs + 36 Grace CPUs, ~130 TB/s NVLink domain, ~13.5 TB HBM3e, ~1.4 EFLOP FP4 inference (vendor sparse-peak; halve for dense), liquid-cooled, ~120 kW/rack.
- **The "one big GPU" framing** is marketing that is also literally true at the programming model: NCCL and the frameworks see a single NVLink domain and place collectives accordingly. The precursor was the NVLink Switch System on DGX H100 SuperPOD (up to 256 GPUs in one NVLink4 domain), but NVL72 is the first mainstream rack-as-accelerator.
- **Serving win:** for a 671B-param MoE, wide EP inside the domain plus [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)|Blackwell's]] FP4 turns a formerly multi-node-communication-bound decode into an in-rack operation, materially lifting tokens/sec/GPU.

## Failure modes

- **Power and cooling as the real blocker.** ~120 kW/rack is far past what air cooling moves; direct-to-chip liquid cooling is mandatory, and many datacenters cannot supply the power/cooling density, so allocation is gated by facilities, not silicon. A half-populated rack loses the domain-scale benefit entirely.
- **Blast radius.** The failure domain is now a whole rack. One NVLink switch fault, one leaking cold plate, or one GPU falling off the bus (see [[Gotchas - Hardware Failures at Scale]]) can degrade or drop 72 GPUs at once — a much larger unit of loss than a single node, forcing topology-aware scheduling and fast checkpoint/restart.
- **Straggler amplification.** With 72 GPUs bound tightly by NVLink collectives, one thermally throttled or silicon-lottery-slow card ([[Concept - GPU Clocks, Power, and Thermal Throttling]]) stalls the whole domain's collectives, not just its node's.
- **Under-utilizing the domain.** If your model is small enough that TP=8 already saturated the old node, naively porting it to NVL72 without widening TP/EP leaves most of the 130 TB/s idle — the win is only realized when the parallelism strategy is re-planned around the larger domain.

## The non-obvious

The headline is "bigger and faster," but the load-bearing change is that **a discrete bandwidth cliff moved, and cliffs — not average bandwidths — are what dictate distributed-systems design.** Every parallelism-placement heuristic in the field (TP-inside-node, EP-inside-node, DP-across-network) was a workaround for the cliff being at 8. Move it to 72 and those heuristics don't merely relax — several invert. The corollary is competitive: the accelerator wars are quietly becoming *scale-up fabric* wars. Google's TPU pods (ICI torus + optical circuit switch) have offered large coherent domains for years; AMD and partners pushing UALink, and Ethernet-based Ultra Ethernet, are all attempts to own the domain boundary. The chip's FLOPs matter less than how many of them you can wire into one NVLink-equivalent pool, because that number sets the ceiling on how cheaply you can run tensor and expert parallelism — the collectives that actually bound frontier training and MoE serving.

## Connections
- [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)]] — NVLink/NVSwitch is the fabric a scale-up domain is built from; this note is that concept scaled to a rack.
- [[Concept - Anatomy of an AI Training Cluster]] — the node→rack→pod hierarchy and the two-tier network whose inner tier NVL72 enlarges (down-link, surface).
- [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]] — the B200/GB200 silicon and NVLink5 details this domain is made of.
- [[Concept - Tensor and Pipeline Parallelism]] — the bandwidth-hungry strategy whose optimal degree the larger domain raises (domain 04, cross-domain).
- [[Concept - Expert Parallelism]] — MoE's all-to-all dispatch becomes an in-domain collective when the domain grows to 72 (domain 04, cross-domain).
- [[Concept - Mixture of Experts Architecture]] — the architecture that most benefits, because expert dispatch is its dominant communication cost (domain 03, cross-domain).
- [[Concept - All-Reduce and Collective Operations]] — the collectives that run over the domain and whose cost model the widened bandwidth changes.
- [[Concept - KV Cache]] — the huge memory object that pooled HBM lets you spread across the domain without paging (domain 07, cross-domain).
- [[Gotchas - Hardware Failures at Scale]] — a whole NVLink domain as the new, larger failure blast radius (up-link, unicorn).
- [[Concept - GPU Clocks, Power, and Thermal Throttling]] — ~120 kW/rack power density and the throttling-straggler risk that tight domains amplify (up-link, unicorn).

## Sources
- NVIDIA (2024) — "GB200 NVL72" product and Blackwell architecture briefs (GTC 2024) — NVLink5 bandwidth, 72-GPU domain, ~130 TB/s aggregate, rack power/cooling figures.
- NVIDIA Hopper Architecture Whitepaper (2022) — NVLink4 900 GB/s and the NVLink Switch System (256-GPU domain) that preceded the rack-scale turn.
- DeepSeek-AI (2024) — "DeepSeek-V3 Technical Report" — a large MoE whose expert-parallel dispatch is the workload rack-scale domains most directly cheapen.
