---
tags: [breakdown, domain/architectures, level/unicorn]
aliases: [DeepSeek-V3, DeepSeek V3, MLA, DeepSeekMoE]
summary: "671B/37B-active MoE that stacked MLA + fine-grained experts + aux-loss-free balancing + MTP + native fp8 to hit a ~$5.6M training bill."
---

# Breakdown - DeepSeek-V3 Architecture

> DeepSeek-V3 (DeepSeek-AI, technical report Dec 2024) is a 671B-parameter open-weights sparse [[Concept - Mixture of Experts Architecture|MoE]] language model. It reached GPT-4o / Claude-3.5-Sonnet-class quality on many benchmarks at a reported headline training cost around **$5.6M**. No single trick explains it. It's the 2024–25 **high-water mark of efficient architecture co-design**: MLA, fine-grained MoE, aux-loss-free balancing, [[Concept - Multi-Token Prediction|Multi-Token Prediction]] and native fp8, each aimed at a specific cost, composed into one system on export-restricted H800s. It's also the base model behind DeepSeek-R1. *(Numbers as of the Dec-2024 report.)*

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

The cost figure shocked the field: a frontier-class model for under $6M of GPU time, roughly an order of magnitude below the assumed cost of comparable Western models. Well-sourced caveat: it excludes salaries, prior R&D, failed runs and the cluster's capital cost. It's *marginal compute* only.

## How it works

The backbone is a standard pre-norm [[Deep Dive - The Transformer|transformer]] with two sublayers heavily reworked. Attention is **Multi-head Latent Attention (MLA)**, and the FFN (after the first 3 dense layers) is **DeepSeekMoE**.

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

**MLA** ([[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)|the fourth attention variant]]) goes after the KV cache. It down-projects K and V into a shared **~512-dim latent**, caches that per token, and up-projects to per-head K/V at compute time. The catch is [[Concept - Rotary Position Embeddings (RoPE)|RoPE]]: it's position-dependent and **cannot be absorbed** into the low-rank projection, so a small set of **decoupled RoPE dimensions (64 per head)** rides alongside the latent. Cached state per token per layer comes to $512 + 64 = 576$ elements, roughly **1/4 of an equivalent GQA cache**, while matching or beating full MHA quality (see [[Concept - KV Cache]]).

**DeepSeekMoE** is fine-grained: **256 small routed experts, top-8**, plus **1 shared expert** every token always uses. Lots of small experts multiply combinatorial routing capacity ($\binom{256}{8}$ vs. Mixtral's $\binom{8}{2}$) and let experts specialize far more sharply than [[Breakdown - Mixtral 8x7B|Mixtral's]] coarse 8. The shared expert takes the common computation so routed experts don't spend capacity relearning it.

## The clever parts

1. **MLA keeps RoPE while compressing KV.** The decoupled-RoPE split is the part practitioners miss. Rotation is per-position, so you can't rotate a compressed latent; you keep a tiny RoPE-carrying branch uncompressed. That makes long-context serving cheap without the quality hit earlier low-rank-KV attempts took.
2. **Aux-loss-free load balancing (Wang et al. 2024).** Every MoE has to keep routing from collapsing onto a few experts. The classic fix adds an auxiliary [[Concept - MoE Training and Load Balancing|load-balance loss]] to the gradient, but that loss fights the language-modeling objective and costs quality. DeepSeek adds a **per-expert bias $b_i$** to the routing affinity used for *top-k selection only* (the gate value still uses the unbiased score) and nudges $b_i$ up or down each step based on observed load. Balancing becomes a control loop with **no quality tax.** A tiny sequence-wise complementary loss stays on as a backstop. It's the single most stealable idea in the model.
3. **MTP as both training signal and draft.** A sequential [[Concept - Multi-Token Prediction|MTP]] module predicts the second-next token (auxiliary loss, weight 0.3→0.1), which densifies the signal. At inference it doubles as a self-speculative draft with **85–90% acceptance → ~1.8× decode throughput.**
4. **Native fp8 training.** DeepSeek-V3 is the first frontier-scale model trained natively in [[Concept - FP8 Training|fp8]] (E4M3), as opposed to only fp8 inference. The trick is **fine-grained quantization**: tile-wise ($1\times128$) scaling for activations and block-wise ($128\times128$) for weights, so one outlier can't blow the scale for a whole tensor, plus high-precision accumulation. That roughly halves memory and compute traffic against bf16 [[Concept - Mixed Precision Training|mixed precision]].
5. **DualPipe and comms co-design.** Custom pipeline scheduling overlaps compute with the all-to-all expert-dispatch traffic, engineered around the H800's constrained interconnect. Details in [[Breakdown - DeepSeek-V3 Training]].

## What it got wrong / what's dated

- **The efficiency is tied to their hardware topology.** The fp8 + DualPipe + node-limited-routing stack is co-designed for their exact **H800 cluster**. The H800 is a bandwidth-crippled, export-compliant H100 (reduced NVLink), and much of the cleverness is *working around* that limit. On a different interconnect the wins shrink or the code doesn't apply.
- **Balancing still rests on assumptions.** The bias loop needs the sequence-wise loss as a safety net, pure bias-only balancing can still drift on pathological data, and the update rate is a tuned knob.
- **Dense first layers and node-limited routing are pragmatic hacks.** The first 3 layers stay dense because early-layer routing was unstable, and routing is capped at ≤4 nodes to bound comms. Both are concessions to systems reality.
- **The cost number is marginal-only** and gets quoted as total cost, which it isn't.

## What to steal

- **MLA** when serving is KV-cache-bound and you can afford the up-projection compute: the best quality-per-cached-byte attention variant published.
- **Bias-based aux-loss-free balancing.** Drop it into any MoE to kill the load-balance-vs-quality tradeoff; it's nearly free to implement.
- **MTP-as-draft.** Pretrain with an MTP module and get ~1.8× decode for free.
- What doesn't port: assume the fp8/comms co-design has to be re-derived for your hardware.

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
