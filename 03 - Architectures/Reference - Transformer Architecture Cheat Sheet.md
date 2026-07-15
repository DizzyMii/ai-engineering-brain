---
tags: [reference, domain/architectures, level/core]
aliases: []
summary: "Parameter and FLOP formulas plus a side-by-side config table for GPT-2 through DeepSeek-V3, date-stamped 2026."
---

# Reference - Transformer Architecture Cheat Sheet

*Parameter-count and FLOP formulas for [[Deep Dive - The Transformer]]'s block structure, plus a side-by-side dimension table for real models. Numbers date-stamped (as of 2026); full training-memory accounting (activations, optimizer state, KV cache) lives in [[Reference - Memory Math for Transformers]], not here.*

## Table 1 — parameter formulas per block

| Component | Formula | Notes |
|---|---|---|
| Attention (MHA) | $4 d_{model}^2$ | $W_Q, W_K, W_V, W_O$, each $d_{model}\times d_{model}$ |
| Attention (GQA, $n_{kv}$ KV heads) | $2d_{model}^2 + 2 d_{model}(n_{kv}\, d_{head})$ | $W_Q,W_O$ stay full-size; $W_K,W_V$ shrink by $n_{kv}/n_{heads}$ — mechanism in [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] |
| Attention (MLA) | $\approx d_{model}\cdot d_{latent}$ + small decoupled-RoPE terms | $d_{latent}\approx512$ in DeepSeek-V2/V3; roughly 1/4 the KV footprint of GQA at matched or better quality |
| FFN (vanilla, ReLU/GELU) | $2 d_{ff}\, d_{model}$ | $W_1$ ($d_{model}\to d_{ff}$), $W_2$ ($d_{ff}\to d_{model}$) |
| FFN (GLU: SwiGLU/GeGLU) | $3 d_{ff}\, d_{model}$ | adds a gate matrix — see [[Concept - Feed-Forward Networks and GLU Variants]] |
| Norms | $\approx 4 d_{model}$ | negligible; two RMSNorm/LayerNorm weight vectors per block |
| Embedding | $vocab \cdot d_{model}$ | usually weight-tied to the unembedding (Press & Wolf 2017) — count once, not twice |

Total params for a dense, pre-norm, MHA model with $d_{ff}=4d_{model}$:

$$N \approx n_{layers}\cdot 12\, d_{model}^2 + vocab\cdot d_{model}$$

The $12d^2$ splits as $4d^2$ attention $+\ 8d^2$ FFN. GQA/MLA shrink the attention term; a GLU FFN at the standard $d_{ff}\approx(8/3)d_{model}$ rescale keeps the FFN term close to $8d^2$ despite the extra matrix. [[Concept - Mixture of Experts Architecture|MoE]] multiplies the FFN term by the expert count for *total* params but not *active* params — that decoupling is the whole point of sparse routing.

## Table 2 — FLOPs conventions

| Pass | FLOPs / token | Basis |
|---|---|---|
| Forward | $\approx 2N$ | 2 FLOPs (multiply + add) per parameter touched once |
| Forward + backward (training) | $\approx 6N$ | backward costs ~2x forward; Kaplan et al. 2020, refined by Hoffmann et al. 2022 ("Chinchilla") |
| Full training run | $C \approx 6ND$ | $D$ = training tokens; the identity [[Concept - Scaling Laws]] is built on |
| Attention term alone | $O(N_{seq}^2\cdot d)$ | quadratic in sequence length, independent of model depth |
| FFN term alone | $O(N_{seq}\cdot d^2)$ | linear in sequence length |

At typical pretraining sequence lengths (2k–8k) the FFN term dominates total FLOPs; past roughly $N_{seq}\sim d$ tokens the quadratic attention term overtakes it — the crossover that motivates [[Concept - Sparse and Sliding-Window Attention]] and every long-context serving optimization.

## Table 3 — model configuration comparison (as of 2026)

Lineage and licensing detail for each row lives in [[Reference - Model Genealogy]]; this table is dimensions only.

| Model (year) | $d_{model}$ | layers | heads | KV heads | $d_{head}$ | $d_{ff}$ | vocab | activation | norm | positional | context | params (total/active) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-2 XL (2019) | 1,600 | 48 | 25 | 25 (MHA) | 64 | 6,400 | 50,257 | GELU | LayerNorm, pre-norm | learned absolute | 1,024 | 1.5B / 1.5B |
| GPT-3 175B (2020) | 12,288 | 96 | 96 | 96 (MHA) | 128 | 49,152 | 50,257 | GELU | LayerNorm, pre-norm | learned absolute | 2,048 | 175B / 175B |
| LLaMA-2 7B (2023) | 4,096 | 32 | 32 | 32 (MHA) | 128 | 11,008 | 32,000 | SwiGLU | RMSNorm, pre-norm | RoPE ($\theta$=10,000) | 4,096 | 7B / 7B |
| LLaMA-2 70B (2023) | 8,192 | 80 | 64 | 8 (GQA) | 128 | 28,672 | 32,000 | SwiGLU | RMSNorm, pre-norm | RoPE ($\theta$=10,000) | 4,096 | 70B / 70B |
| Mistral 7B (2023) | 4,096 | 32 | 32 | 8 (GQA) | 128 | 14,336 | 32,000 | SwiGLU | RMSNorm, pre-norm | RoPE + sliding window 4,096 | 8,192 | 7B / 7B |
| Mixtral 8x7B (2023) | 4,096 | 32 | 32 | 8 (GQA) | 128 | 14,336 ×8 experts | 32,000 | SwiGLU | RMSNorm, pre-norm | RoPE + SWA | 32,768 | 47B / 13B |
| LLaMA-3 70B (2024) | 8,192 | 80 | 64 | 8 (GQA) | 128 | 28,672 | 128,256 | SwiGLU | RMSNorm, pre-norm | RoPE ($\theta$=500,000) | 8,192 (base) | 70B / 70B |
| DeepSeek-V3 (2024) | ~7,168 | 61 | 128 | MLA ($d_{latent}\approx512$) | 128 | ~2,048/expert × 256 + 1 shared | 129,280 | SwiGLU | RMSNorm, pre-norm | RoPE, decoupled dims=64 | 128K | 671B / 37B |
| Qwen2.5 72B (2024) | 8,192 | 80 | 64 | 8 (GQA) | 128 | ~29,568 | 151,936 | SwiGLU | RMSNorm, pre-norm | RoPE ($\theta$=1,000,000) | 131,072 (YaRN) | 72B / 72B |
| Gemma 2 9B (2024) | 3,584 | 42 | 16 | 8 (GQA) | 256 | 14,336 | 256,000 | GeGLU | RMSNorm, sandwich | RoPE | 8,192 | 9B / 9B |

## Conventions worth knowing

- **`head_dim` is folklore-driven, not derived.** 64 and 128 are essentially the only two values any real model uses (GPT-3's 96×128 vs. LLaMA's 32×128) — there's no theoretical result pinning this, it's a convention that stuck because it plays well with tensor-core tile sizes.
- **$d_{ff}$ gets rounded to a hardware-friendly multiple** after the $4d$ or $(8/3)d$ rescale, which is why table entries like 11,008 and 14,336 look arbitrary rather than exact multiples of $d_{model}$.
- **Vocab size has crept up an order of magnitude in five years**: 32k ([[Concept - Byte-Pair Encoding|LLaMA-2's BPE]] tokenizer, English-centric) → 128k (LLaMA-3, more languages + code) → 150k–256k (Qwen2.5, Gemma 2 — heavier multilingual coverage). This directly inflates both the embedding parameter count and the final-layer logit FLOP cost.
- **"Total vs. active" only diverges for MoE rows** (Mixtral, DeepSeek-V3); every dense row has total = active by definition, which is the entire framing of [[Decision - Dense vs Mixture-of-Experts]].

## Connections
- [[Deep Dive - The Transformer]] — the block structure these formulas are counting; read that first if the $12d^2$ derivation is unfamiliar.
- [[Reference - Memory Math for Transformers]] — takes these parameter counts further into training and serving memory (optimizer state, activations, KV cache).
- [[Concept - Scaling Laws]] — what the $C\approx 6ND$ FLOPs identity is *for*: picking model size vs. token count at a fixed compute budget.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — the mechanism behind the GQA/MLA rows in Table 1 and the KV-head column in Table 3.
- [[Concept - Feed-Forward Networks and GLU Variants]] — the mechanism and the $(8/3)d$ rescale behind the GLU FFN row.
- [[Concept - Mixture of Experts Architecture]] — the total-vs-active decoupling behind the Mixtral and DeepSeek-V3 rows.
- [[Concept - Sparse and Sliding-Window Attention]] — where the FLOPs crossover in Table 2 pushes practitioners once sequence length dominates.
- [[Reference - Model Genealogy]] — where these specific models sit in the broader lineage and licensing picture (cross-domain: ecosystem & history).
- [[Concept - Byte-Pair Encoding]] — the tokenizer choices behind each row's vocab size and its downstream cost (cross-domain: training at scale).

## Sources
- Kaplan et al. (2020) — "Scaling Laws for Neural Language Models." Origin of the $\approx 6N$ per-token training FLOPs approximation.
- Hoffmann et al. (2022) — "Training Compute-Optimal Large Language Models" (Chinchilla). Refines the FLOPs-vs-tokens-vs-params accounting used in Table 2.
- Press & Wolf (2017) — "Using the Output Embedding to Improve Language Models." The input/output weight-tying convention assumed in the parameter formulas.
- Touvron et al. (2023) — "LLaMA 2: Open Foundation and Fine-Tuned Chat Models." Source of the LLaMA-2 config numbers.
