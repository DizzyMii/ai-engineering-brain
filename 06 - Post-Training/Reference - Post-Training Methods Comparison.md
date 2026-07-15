---
tags: [reference, domain/post-training, level/core]
aliases: [post-training algorithm comparison, alignment method comparison, DPO vs PPO vs GRPO]
summary: "Lookup matrix across SFT, RLHF-PPO, DPO family, GRPO, and rejection sampling: data type, resident models, cost, stability, defaults."
---

## Method comparison matrix

| Method | Data type | Needs RM? | Needs ref model? | Policy | Models resident¹ | Relative compute² | Stability | Typical defaults | Canonical user |
|---|---|---|---|---|---|---|---|---|---|
| [[Concept - Supervised Fine-Tuning (SFT)]] | Demonstrations | No | No | Offline | 1 | 1x (baseline) | High | LR 1e-5–2e-5, 1–3 epochs | InstructGPT stage 1, Llama-3 |
| RLHF-PPO ([[Deep Dive - RLHF End to End]]) | Pairwise prefs → RM | Yes | Yes (+ value) | On-policy | 4 (policy, ref, RM, value) | ~4–10x SFT | Lowest | KL target ~6–10 nats, adaptive β | InstructGPT, Anthropic HH |
| [[Concept - Direct Preference Optimization (DPO)]] | Pairwise prefs | No | Yes | Offline | 2 (policy, ref) | ~1–1.5x SFT | High | β ≈ 0.1 (0.01–0.5) | Zephyr, Tulu 2 |
| IPO ([[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]]) | Pairwise prefs | No | Yes | Offline | 2 | ~DPO | High — fixes DPO's margin-to-infinity overfit | τ (target margin) | Near-deterministic preference sets |
| KTO ([[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]]) | Unpaired binary (good/bad) | No | Yes | Offline | 2 | ~DPO | Medium-high | separate desirable/undesirable weights | Production thumbs-up/down logs |
| ORPO ([[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]]) | Pairwise prefs | No | **No** | Offline, single-stage | 1 | ~SFT (cheapest pref method) | Medium | λ ≈ 0.1–1.0 | Memory-constrained fine-tunes |
| SimPO ([[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]]) | Pairwise prefs | No | **No** | Offline | 1 | ~SFT | Medium-high | β ≈ 2–2.5, γ/β ≈ 0.3–0.5 | Length-bias-sensitive deployments |
| [[Concept - GRPO and RL with Verifiable Rewards]] | Verifiable reward or RM | Optional | Yes (small/0 β) | On-policy | 2–3 (policy, ref, [RM]) | ~2–4x SFT (no value model) | Medium — better than PPO, still on-policy variance | group size G = 8–64 | DeepSeek-R1, DeepSeekMath |
| [[Concept - Rejection Sampling and Expert Iteration]] | RM- or verifier-scored samples | Yes/verifier | No | Iterative offline | 1 (+ scorer) | ~k× generation + 1× SFT | High — parallel, no RL loop | k = 8–128 | Llama-2/3, STaR |

## Core formulas

| Method | Objective |
|---|---|
| Reward model (Bradley-Terry) | $\mathcal{L} = -\log\sigma(r(x,y_w) - r(x,y_l))$ |
| RLHF reward (per-token) | $r_t = -\beta \cdot \log(\pi_\theta/\pi_{ref})_t$ (+ RM scalar at final token) |
| DPO | $\mathcal{L} = -\log\sigma\!\big(\beta[\log\tfrac{\pi_\theta(y_w\|x)}{\pi_{ref}(y_w\|x)} - \log\tfrac{\pi_\theta(y_l\|x)}{\pi_{ref}(y_l\|x)}]\big)$ |
| GRPO advantage | $A_i = \dfrac{r_i - \text{mean}(r)}{\text{std}(r)}$, broadcast to every token of completion $i$ |

## Footnotes

1. **Models resident** = distinct full-size model copies held in accelerator memory simultaneously during the training step (policy, frozen reference, reward model, value/critic). This is the dominant driver of the "relative compute" column — see [[Reference - Memory Math for Transformers]] for the byte-level accounting per model.
2. **Relative compute** is a rough wall-clock multiplier over an equivalent SFT run on the same data volume; it excludes the one-time cost of RM training and is sensitive to rollout/generation efficiency (a slow sampler inflates PPO/GRPO disproportionately). Figures as of 2026 — treat as order-of-magnitude, not benchmark numbers.
3. Reference-free methods (ORPO, SimPO) drop the KL anchor entirely, which is why they save a resident model but lose the built-in overoptimization brake that DPO, IPO, KTO, and GRPO retain via the reference model.

## Connections

- [[Concept - Direct Preference Optimization (DPO)]] — the row every other offline method in this table is defined as a variant of.
- [[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]] — the mechanism detail (loss derivations) behind the IPO/KTO/ORPO/SimPO rows.
- [[Concept - GRPO and RL with Verifiable Rewards]] — the on-policy, no-value-model row; this table's numbers on group size and resident models come from its mechanism.
- [[Deep Dive - RLHF End to End]] — the full four-model PPO pipeline this table compresses into one row.
- [[Concept - PPO for Language Models]] — the RL algorithm underlying the RLHF-PPO row's clipping and stability numbers.
- [[Decision - Choosing a Preference Optimization Algorithm]] — turns this comparison matrix into an actual choice given data and compute constraints.
- [[Reference - Memory Math for Transformers]] — the per-model byte accounting that explains why "models resident" drives cost (domain 08, cross-domain).
- [[Reference - PEFT Method Comparison]] — the analogous comparison matrix one layer over, for parameter-efficiency instead of preference-optimization axis (domain 12, cross-domain).
- [[Concept - The Post-Training Pipeline]] — the surface-level map showing where each method in this table sits in the end-to-end stack.
