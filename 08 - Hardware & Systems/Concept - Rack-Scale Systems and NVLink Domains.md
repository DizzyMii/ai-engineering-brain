---
tags: [concept, domain/hardware-systems, level/frontier]
aliases: [NVL72, GB200 NVL72, NVLink domain, scale-up domain, rack-scale GPU]
summary: "Extending the NVLink scale-up domain from an 8-GPU node to a 72-GPU rack, moving the bandwidth cliff and rewriting parallelism math."
---
> **One-paragraph hook:** For a decade the unit of "one big GPU" was the 8-GPU node: eight cards fully connected by NVSwitch, and a ~15x bandwidth cliff as soon as traffic left the box for [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)|InfiniBand]]. That cliff at 8 GPUs has dictated distributed-training layout since Megatron. Keep bandwidth-hungry tensor and expert parallelism *inside* the node and spread everything else over the slow network. Rack-scale systems, with NVIDIA's GB200 NVL72 as the canonical 2025 example, move the cliff from 8 GPUs to 72 by running the NVLink fabric across a whole liquid-cooled rack, so all 72 GPUs look like one coherent, high-bandwidth pool. That changes which parallelism strategies are cheap, not only how fast the old ones run.

## The mechanism

An **NVLink domain** is the set of GPUs that can address each other's HBM directly over NVLink at NVLink speed, through NVSwitch silicon, without a byte touching the scale-out network. Historically the domain *was* the node: 8 H100s on an HGX baseboard, each with ~900 GB/s of NVLink4 (18 links × 50 GB/s), all-to-all through on-board NVSwitches. Past 8 you hit the [[Concept - Anatomy of an AI Training Cluster|two-tier network]], InfiniBand NDR at ~400 Gb/s ≈ 50 GB/s per GPU, an ~18x drop in per-GPU bandwidth the moment you leave the baseboard.

GB200 NVL72 removes that boundary. Seventy-two Blackwell GPUs (with 36 Grace CPUs across 18 compute trays) connect through nine NVLink Switch trays over a copper cable backplane into one NVLink domain, with **NVLink5 at 1.8 TB/s per GPU** and roughly **130 TB/s of aggregate all-to-all bandwidth** across the rack. Any GPU can read or write any other GPU's HBM at ~1.8 TB/s, two orders of magnitude faster than the InfiniBand that used to sit between them.

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

Two consequences follow.

**Memory pooling.** NVLink is load/store-addressable, so the 72 GPUs' HBM becomes one fast pool: 72 × 192 GB HBM3e ≈ **13.5 TB** reachable at NVLink bandwidth. A model plus optimizer state, or a huge [[Concept - KV Cache]], too big for one GPU's 192 GB and hopeless to page over InfiniBand, now spreads across the domain with every shard one NVLink hop away. GB200 also couples each Grace CPU to its GPUs over coherent NVLink-C2C at 900 GB/s, extending the pool into ~480 GB of LPDDR per superchip for offload.

**The parallelism map gets redrawn.** [[Concept - Tensor and Pipeline Parallelism|Tensor parallelism]] all-reduces activations on *every* layer, and [[Concept - Expert Parallelism|expert parallelism]] runs an all-to-all dispatch on every MoE layer. Both are bandwidth-bound [[Concept - All-Reduce and Collective Operations|collectives]], and both were effectively capped at degree 8 because degree 9 meant crossing the cliff. In a 72-GPU domain TP and EP can span far more GPUs on NVLink, so the best (TP, EP, PP, DP) decomposition shifts toward much wider TP/EP and away from the pipeline/data parallelism you used to dodge the network. For a large [[Concept - Mixture of Experts Architecture|mixture-of-experts]] model, all-to-all expert dispatch, the most punishing collective in the stack, becomes an in-domain operation. That's why DeepSeek-V3-style MoE serving gains so much from a large scale-up domain.

## In practice

- **Silicon:** GB200 NVL72 = 72 B200 GPUs + 36 Grace CPUs, ~130 TB/s NVLink domain, ~13.5 TB HBM3e, ~1.4 EFLOP FP4 inference (vendor sparse-peak; halve for dense), liquid-cooled, ~120 kW/rack.
- **"One big GPU"** is marketing that's also literally true at the programming-model level: NCCL and the frameworks see one NVLink domain and place collectives accordingly. The NVLink Switch System on DGX H100 SuperPOD (up to 256 GPUs in one NVLink4 domain) came first, but NVL72 is the first mainstream rack-as-accelerator.
- **Serving win:** for a 671B-param MoE, wide EP inside the domain plus [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)|Blackwell's]] FP4 turns a decode that used to be bound by multi-node communication into an in-rack operation, and tokens/sec/GPU rises materially.

## Failure modes

- **Power and cooling are what actually block it.** ~120 kW/rack is far past what air cooling can move. Direct-to-chip liquid cooling is mandatory, and many datacenters can't supply that power and cooling density, so facilities gate allocation more than silicon does. A half-populated rack loses the domain-scale benefit entirely.
- **Blast radius.** The failure domain is now a whole rack. One NVLink switch fault, one leaking cold plate, or one GPU falling off the bus (see [[Gotchas - Hardware Failures at Scale]]) can degrade or drop 72 GPUs at once. A much bigger unit of loss than a node, which forces topology-aware scheduling and fast checkpoint/restart.
- **Straggler amplification.** With 72 GPUs tied together by NVLink collectives, one thermally throttled or silicon-lottery-slow card ([[Concept - GPU Clocks, Power, and Thermal Throttling]]) stalls the whole domain's collectives instead of one node's.
- **Under-using the domain.** If TP=8 already saturated the old node for your model, porting it to NVL72 without widening TP/EP leaves most of the 130 TB/s idle. You only get the win after re-planning the parallelism strategy around the bigger domain.

## The non-obvious

The headline is "bigger and faster." What matters is that **a discrete bandwidth cliff moved, and distributed-systems design is dictated by cliffs more than by average bandwidth.** Every parallelism-placement heuristic in the field (TP inside the node, EP inside the node, DP across the network) worked around a cliff at 8. Move it to 72 and several of those heuristics invert instead of merely relaxing.

The competitive corollary: the accelerator wars are turning into *scale-up fabric* wars. Google's TPU pods (ICI torus + optical circuit switch) have offered large coherent domains for years, and AMD and partners with UALink, plus the Ethernet-based Ultra Ethernet effort, are all trying to own the domain boundary. The chip's FLOPs matter less than how many chips you can wire into one NVLink-equivalent pool, because that caps how cheaply you run tensor and expert parallelism, the collectives that bound frontier training and MoE serving.

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
