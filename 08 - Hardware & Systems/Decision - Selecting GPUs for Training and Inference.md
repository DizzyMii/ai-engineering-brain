---
tags: [decision, domain/hardware-systems, level/advanced]
aliases: []
summary: "How to pick an accelerator by capacity fit, then compute- vs memory-bound profile, then latency/throughput SLO, then $/hr — not by peak TFLOPs."
---

> **The decision in one sentence:** pick the accelerator that first *fits* your model at the precision and batch size you need, then match its bandwidth/FLOPs profile to whether your workload is compute- or memory-bound — peak TFLOPs is the last column you should look at, not the first.
> **Default answer for the 80% case (as of 2026):** H100 (or H200 where HBM capacity is the constraint) rented on-demand from a major cloud, tensor-parallel within a node if training beyond ~70B params, single-GPU or small tensor-parallel group for serving.

## Decision flow

```mermaid
flowchart TD
    A[Start: pick an accelerator] --> B{Does model + optimizer/KV state fit\nin HBM at target batch/precision?}
    B -- No --> B1[Shard across more GPUs, pick a higher-HBM SKU,\nor quantize weights/KV — see Reference - Memory Math for Transformers]
    B1 --> C
    B -- Yes --> C{Training or inference?}
    C -- Training --> D{Scale beyond one node (>8 GPUs)?}
    D -- Yes --> D1[Interconnect dominates: H100/H200/B200\nwith NVLink+InfiniBand, not raw FLOPs]
    D -- No --> D2[A100/H100 single node;\nA100 still fine below ~70B params]
    C -- Inference --> E{Latency-critical (interactive)\nor throughput-critical (batch)?}
    E -- Latency --> E1[Bandwidth + low-latency SKU:\nH100, or Groq LPU for extreme decode latency]
    E -- Throughput --> E2[Maximize batch: H100/L40S/consumer fleet,\ncost-per-token wins over per-request latency]
    D1 --> F{Rent from cloud or buy capex?}
    D2 --> F
    E1 --> F
    E2 --> F
    F -- "Expected utilization < ~50-70%, or short/bursty need" --> F1[Cloud on-demand or spot]
    F -- "Sustained utilization > ~70%, long horizon" --> F2[Owned capex]
```

## Tradeoff matrix

*(all figures as of 2026; cloud pricing moves fast and should be re-checked at decision time)*

| Option | Peak BF16 TFLOP/s | HBM capacity | HBM bandwidth | Interconnect | ~Cloud $/hr | Best fit |
|---|---|---|---|---|---|---|
| A100 | ~312 | 80 GB | ~2 TB/s | NVLink3 | lowest of the datacenter tier | Training/inference below ~70B; legacy fleets |
| H100 | ~989 | 80 GB | ~3.35 TB/s | NVLink4, ~900 GB/s | ~$2-4/hr on-demand | Default choice — training and latency-sensitive serving |
| H200 | ~989 (same compute as H100) | 141 GB HBM3e | ~4.8 TB/s | NVLink4 | premium over H100 | When KV cache / model capacity, not FLOPs, is the binding constraint |
| B200/GB200 | FP4-class, ~2.2x H100 training throughput | 192 GB HBM3e | ~8 TB/s | NVLink5, rack-scale (NVL72) | premium, limited availability | Frontier-scale training; where rack-scale NVLink domain matters |
| AMD MI300X | competitive FLOPs on paper | 192 GB HBM3 | high | Infinity Fabric | often cheaper | Capacity-bound inference, if the ROCm software gap is acceptable |
| Consumer RTX 4090 | high dense FLOPs, no tensor-core datacenter features | 24 GB GDDR6X | ~1 TB/s | none (PCIe only, no NVLink) | none — capex only | Single-GPU fine-tune/inference; never multi-node training |
| Groq LPU | N/A (SRAM-only, deterministic) | tiny (on-chip SRAM) | N/A | proprietary | premium per-token | Ultra-low-latency single-stream decode |

## The details that flip the decision

**The FLOPs trap.** Buying peak [[Concept - Model FLOPs Utilization (MFU)|FLOPs]] you cannot feed is the most common expensive mistake. A B200 bought for its FP4 peak but run on a workload that's memory-bound (most decode, most norm/softmax-heavy work) never approaches that peak — see [[Concept - The Roofline Model]] for why arithmetic intensity, not sticker-FLOPs, determines what you actually get. Check whether your workload's arithmetic intensity clears the ridge point *before* paying a FLOPs premium.

**Decode is memory-bandwidth-bound, not compute-bound.** For inference, HBM bandwidth and capacity (for weights plus [[Concept - KV Cache]]) dominate the decode-phase cost far more than peak FLOPs — a GPU with mediocre FLOPs but excellent bandwidth beats a FLOPs monster at serving throughput. This is why the inference branch of the decision flow above routes on bandwidth-class hardware, and why cost per token, not raw hardware cost, is the metric that should decide — see [[Concept - Cost Engineering for LLM Applications]].

**Capacity gates everything.** If the model plus optimizer state (training) or weights plus KV cache (inference) doesn't fit in HBM at your target batch and precision, no amount of compute matters until you've solved the fit problem — shard, quantize, or upgrade to a higher-capacity SKU. Run the numbers with [[Reference - Memory Math for Transformers]] before shopping for hardware, not after.

**Interconnect beats FLOPs at scale.** Past roughly one node (8 GPUs), training throughput is usually gated by how fast gradients synchronize, not by any single GPU's peak FLOPs — the [[Concept - GPU Interconnects (NVLink, InfiniBand, RoCE)|NVLink-vs-InfiniBand bandwidth cliff]] (an order of magnitude drop leaving the node) makes topology and interconnect generation a first-order purchasing decision, not an afterthought.

**Cloud vs owned is a utilization bet.** H100 on-demand rental runs roughly $2-4/hr (2026); owned capex only wins once sustained utilization clears roughly 50-70%, because idle owned hardware is pure sunk cost while idle rented hardware simply isn't rented. Spot/preemptible instances cut price further but add real risk to long, uninterruptible training runs — checkpoint discipline becomes load-bearing, not optional, when using them.

**Consumer cards are a different product, not a cheaper H100.** No NVLink (PCIe-only inter-GPU bandwidth), no ECC memory, and capped HBM (24 GB on a 4090) rule consumer cards out for multi-node training and for any workload where a bit-flip is unacceptable. They're genuinely fine for single-GPU fine-tuning or low-stakes inference — but note the datacenter driver licensing caveat: NVIDIA's consumer driver EULA restricts datacenter deployment of GeForce cards, which matters if you're building a commercial serving fleet rather than a personal workstation.

**Concrete scenario picks (2026):**
- **7B model inference, low request volume:** single L40S or even a consumer 4090 — capacity and bandwidth easily cover a 7B model's weights plus modest KV cache.
- **70B model serving at scale:** tensor-parallel H100 group (typically 2-4 GPUs) inside one NVLink domain; H200 if KV cache pressure from long contexts pushes you over 80 GB.
- **100B+ pretraining:** H100/H200/B200 cluster with full NVLink+InfiniBand fabric, thousands of GPUs — at this scale, [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]]'s rack-scale NVLink domain (GB200 NVL72) becomes a first-order consideration, not a footnote.
- **GCP-committed workloads at very large training scale:** [[Breakdown - The Google TPU]] is a legitimate alternative to the whole flow above, but only inside Google Cloud — its exclusion from most of this decision's scope is a platform-lock-in tradeoff, not a performance one.

## Connections
- [[Reference - AI Accelerator Landscape]] — the raw spec tables this decision's tradeoff matrix is condensed from; consult it for chips beyond the shortlist here (MI300X, Trainium2, inference specialists).
- [[Reference - Memory Math for Transformers]] — the formulas that answer the decision flow's first gate ("does it fit?") before any hardware comparison is meaningful.
- [[Concept - The Roofline Model]] — the theory behind the FLOPs trap: why peak TFLOPs is the wrong first metric for most real workloads.
- [[Concept - Model FLOPs Utilization (MFU)]] — the metric that tells you, after purchase, whether you're actually getting the FLOPs you paid for.
- [[Breakdown - The NVIDIA Datacenter GPU (Hopper and Blackwell)]] — the detailed architecture behind the H100/H200/B200 rows in the tradeoff matrix.
- [[Breakdown - The Google TPU]] — the platform-locked alternative that this decision mostly excludes by scope, and why.
- [[Concept - Cost Engineering for LLM Applications]] — turns the $/hr hardware numbers here into the $/token economics that actually drive a serving deployment's P&L.
- [[Concept - KV Cache]] — the inference-side memory term that, alongside weights, decides whether decode is even feasible on a given SKU.

## Sources
- NVIDIA datacenter GPU datasheets (H100, H200, B200) — the peak-FLOP, HBM capacity, and bandwidth figures in the tradeoff matrix.
- folklore, weakly sourced: the "~50-70% utilization breakeven" for owned-vs-rented capex is widely cited by infrastructure teams as a rule of thumb; it depends heavily on negotiated cloud discount rates and depreciation schedules, so treat it as a starting estimate, not a formula.
