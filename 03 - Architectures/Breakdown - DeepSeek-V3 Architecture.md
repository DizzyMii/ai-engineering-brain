---
tags: [breakdown, domain/architectures, level/unicorn]
aliases: [DeepSeek-V3, DeepSeek V3, MLA, DeepSeekMoE]
summary: "671B/37B-active MoE that stacked MLA + fine-grained experts + aux-loss-free balancing + MTP + native fp8 to hit a ~$5.6M training bill."
---

# Breakdown - DeepSeek-V3 Architecture

> DeepSeek-V3 (DeepSeek-AI, technical report Dec 2024) is a 671B-parameter sparse [[Concept - Mixture of Experts Architecture|MoE]] language model, open-weights, that reached GPT-4o / Claude-3.5-Sonnet-class quality on many benchmarks while reporting a headline training cost around **$5.6M**. It matters not for any single trick but because it is the 2024–25 **high-water mark of efficient architecture co-design**: MLA + fine-grained MoE + aux-loss-free balancing + [[Concept - Multi-Token Prediction|Multi-Token Prediction]] + native fp8, each chosen to fight a specific cost, composed into one system that ran on export-restricted H800s. It is also the base model behind DeepSeek-R1. *(Numbers as of the Dec-2024 report.)*

## The headline numbers

| Property | Value |
|---|---|
| Total / active params | **671B / 37B** per token |
| Layers | 61 (first 3 dense, rest DeepSeekMoE) |
| $d_{model}$ | 7168 |
| Attention | **MLA**, 128 heads; KV latent $d_c=512$, decoupled RoPE dim 64 |
| MoE | **256 routed experts** (top-8) + **1 shared** per layer; node-limited to ≤4 nodes |
| Training tokens | **14.8T** |
| Compute | **2.788M H800 GPU-hours** (2.664M pretraining) |
| Reported cost | **~$5.576M** (@ assumed $2/H800-hour) |
| Precision | **native fp8** (E4M3) mixed precision |
| Context | 128K (YaRN-extended 4K→32K→128K) |

The cost figure is what shocked the field: a frontier-class model trained for under $6M of GPU time, roughly an order of magnitude below the assumed cost of comparable Western models. (Caveat, well-sourced: this excludes salaries, prior R&D, failed runs, and the cluster's capital cost — it is *marginal compute* only.)

## How it actually works

Standard pre-norm [[Deep Dive - The Transformer|transformer]] backbone, but two sublayers are heavily reworked. Attention is **Multi-head Latent Attention (MLA)**; the FFN (after the first 3 dense layers) is **DeepSeekMoE**.

```
        ┌─────────────── one MoE layer ───────────────┐
x ─► RMSNorm ─► MLA ────────────────────────► + residual
        │   (compress KV→512 latent + 64 RoPE dims,
        │    cache the latent; up-project per head)
x ─► RMSNorm ─► router ─► top-8 of 256 routed experts
        │                 + 1 always-on shared expert  ─► + residual
        └── per-expert bias b_i steers routing (no aux loss)
   [+ sequential MTP module predicts the 2nd-next token]
```

**MLA** ([[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)|the fourth attention variant]]) is the KV-cache play. Instead of caching full per-head K and V, it down-projects them into a shared **~512-dim latent** that is cached per token, and up-projects to per-head K/V at compute time. The subtlety: [[Concept - Rotary Position Embeddings (RoPE)|RoPE]] is position-dependent and **cannot be absorbed** into the low-rank projection, so a small set of **decoupled RoPE dimensions (64 per head)** is carried separately alongside the latent. The cached state per token per layer is thus $512 + 64 = 576$ elements — roughly **1/4 of an equivalent GQA cache** while matching or beating full MHA quality (see [[Concept - KV Cache]]).

**DeepSeekMoE** is fine-grained: **256 small routed experts, top-8**, plus **1 shared expert** that every token always uses. Many-small-experts multiply the combinatorial routing capacity ($\binom{256}{8}$ vs. Mixtral's $\binom{8}{2}$) and let experts specialize far more sharply than [[Breakdown - Mixtral 8x7B|Mixtral's]] coarse 8; the shared expert absorbs common computation so routed experts don't waste capacity relearning it.

## The clever parts

1. **MLA — KV compression without losing RoPE.** The decoupled-RoPE split is the crux practitioners miss: you can't rotate a compressed latent because rotation is per-position, so you keep a tiny RoPE-carrying branch un-compressed. This is what makes long-context serving cheap without the quality hit that plagued earlier low-rank-KV attempts.
2. **Aux-loss-free load balancing (Wang et al. 2024).** Every MoE has to stop routing from collapsing onto a few experts. The classic fix is an auxiliary [[Concept - MoE Training and Load Balancing|load-balance loss]] added to the gradient — but that loss fights the language-modeling objective and costs quality. DeepSeek instead adds a **per-expert bias $b_i$** to the routing affinity used for *top-k selection only* (the gate value still uses the unbiased score), and nudges $b_i$ up/down each step based on observed load. Balancing becomes a control loop, not a gradient term — **no quality tax.** A tiny sequence-wise complementary loss remains only as a backstop. This is the single most stealable idea in the model.
3. **Multi-Token Prediction as training signal *and* draft.** A sequential [[Concept - Multi-Token Prediction|MTP]] module predicts the second-next token (auxiliary loss, weight 0.3→0.1), densifying the signal — and at inference doubles as a self-speculative draft with **85–90% acceptance → ~1.8× decode throughput.**
4. **Native fp8 training.** DeepSeek-V3 is the first frontier-scale model trained natively in [[Concept - FP8 Training|fp8]] (E4M3), not just fp8 inference. It works via **fine-grained quantization** — tile-wise ($1\times128$) scaling for activations, block-wise ($128\times128$) for weights — so a single outlier doesn't blow the scale for a whole tensor, plus high-precision accumulation. This roughly halves memory and compute traffic versus bf16 [[Concept - Mixed Precision Training|mixed precision]].
5. **DualPipe + comms co-design.** Custom pipeline scheduling overlaps computation with the all-to-all expert-dispatch communication, engineered around the H800's constrained interconnect. Details in [[Breakdown - DeepSeek-V3 Training]].

## What it got wrong / what's dated

- **The efficiency is hardware-topology-specific.** The fp8 + DualPipe + node-limited-routing stack is co-designed for their exact **H800 cluster** — the H800 is a bandwidth-crippled, export-compliant H100 (reduced NVLink), and much of the cleverness is *working around* that limit. Ported to a different interconnect, the wins shrink or the code doesn't apply.
- **Balancing still isn't free of assumptions.** The bias control loop needs the complementary sequence-wise loss as a safety net; pure bias-only balancing can still drift on pathological data, and the update rate is a tuned knob.
- **Dense first layers and node-limited routing are pragmatic hacks**, not principled — the first 3 layers stay dense because early-layer routing was unstable, and routing is capped to ≤4 nodes to bound comms. Both are concessions to systems reality.
- **Cost number is marginal-only** and gets quoted as total cost, which it is not.

## What to steal

- **MLA** whenever serving is KV-cache-bound and you can afford the up-projection compute — it's the best quality-per-cached-byte attention variant published.
- **Bias-based aux-loss-free balancing** — drop it into any MoE to kill the load-balance-vs-quality tradeoff; nearly free to implement.
- **MTP-as-draft** — pretrain with an MTP module and get ~1.8× decode for free.
- What's *not* portable: assume the fp8/comms co-design needs re-derivation for your hardware.

## Connections

- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — MLA is the headline attention variant; this note is its flagship deployment.
- [[Concept - Mixture of Experts Architecture]] — DeepSeekMoE is fine-grained MoE; read for routing/capacity fundamentals.
- [[Concept - Multi-Token Prediction]] — the MTP module used for both training signal and speculative drafting here.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the decoupled-RoPE trick is what makes MLA's KV compression possible.
- [[Concept - KV Cache]] — MLA's whole purpose is shrinking this to ~1/4 of GQA.
- [[Concept - MoE Training and Load Balancing]] — the aux-loss problem DeepSeek sidesteps with a bias control loop.
- [[Concept - FP8 Training]] — native fp8 with fine-grained tile/block quantization is how the cost number was hit.
- [[Concept - Mixed Precision Training]] — the bf16 baseline fp8 improves on; where loss-scaling and accumulation precision matter.
- [[Breakdown - DeepSeek-V3 Training]] — the systems companion: DualPipe, comms overlap, and the full training recipe.
- [[Breakdown - Mixtral 8x7B]] — the coarse-grained MoE predecessor DeepSeekMoE's fine-grained design improves on.
- [[Concept - GRPO and RL with Verifiable Rewards]] — DeepSeek-V3 is the base model that DeepSeek-R1 post-trained with GRPO.
- [[Deep Dive - The Transformer]] — the backbone MLA and DeepSeekMoE slot into.
- [[Reference - Model Genealogy]] — DeepSeek-V3's place in the MoE lineage and the DeepSeek family.

## Sources
- DeepSeek-AI (2024) — *DeepSeek-V3 Technical Report.* Full architecture, 671B/37B, 14.8T tokens, 2.788M H800-hours, fp8, MLA, MTP.
- DeepSeek-AI (2024) — *DeepSeek-V2.* Origin of MLA and DeepSeekMoE (fine-grained + shared experts).
- Wang et al. (2024) — *Auxiliary-Loss-Free Load Balancing.* The per-expert bias control loop DeepSeek-V3 uses.
- Gloeckle et al. (2024) — *Multi-token Prediction.* The MTP idea the sequential module implements.
