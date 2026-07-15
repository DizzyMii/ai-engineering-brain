---
tags: [reference, domain/training-at-scale, level/unicorn]
aliases: [pretraining hyperparameters, LLM training config, hyperparameter table, betas weight decay warmup]
summary: "Sourced hyperparameters of real frontier pretraining runs, surfacing folklore constants like beta2=0.95, wd=0.1, and grad clip 1.0."
---

# Reference - LLM Pretraining Hyperparameters

*Values as of 2026. Each row is sourced below. Cells marked `n/d` were not disclosed; `*` = approximate/partially disclosed; footnote markers explain non-obvious cells. Published numbers dominate; folklore is called out in its own section.*

## Optimizer, LR, and schedule

| Model | Peak LR | Min LR | Warmup | Global batch (tokens)¹ | β1 | β2 | ε | wd | grad clip |
|---|---|---|---|---|---|---|---|---|---|
| GPT-3 175B | 6e-5 | 6e-6 | 375M tok | 3.2M ² | 0.9 | 0.95 | 1e-8 | 0.1 | 1.0 |
| Gopher 280B | 4e-5* | ~4e-6 | 1.5k steps | 3M→6M ² | 0.9 | n/d | n/d | n/d | 1.0 |
| Chinchilla 70B | ~1e-4* | ~1e-5 | ~500 steps* | 1.5M→3M ² | 0.9 | n/d | n/d | n/d | n/d |
| PaLM 540B | 1e-2 ³ | — ³ | 10k steps ³ | 1M→2M→4M ² | 0.9 | 1−k⁻·⁸ ⁴ | n/d | lr² ⁴ | 1.0 |
| OPT-175B | 1.2e-4 | 1.2e-5 | 2k steps | 2M | 0.9 | 0.95 | 1e-8 | 0.1 | 1.0→0.3 ⁵ |
| Llama-1 65B | 1.5e-4 | 1.5e-5 | 2k steps | 4M | 0.9 | 0.95 | 1e-5 ⁶ | 0.1 | 1.0 |
| Llama-2 70B | 1.5e-4 | 1.5e-5 | 2k steps | 4M | 0.9 | 0.95 | 1e-5 ⁶ | 0.1 | 1.0 |
| Llama-3 405B | 8e-5* | n/d | 8k steps* | 4M→8M→16M ²* | 0.9 | 0.95 | 1e-8 | 0.1 | 1.0 |
| Llama-3 8B | 3e-4* | n/d | ~8k steps* | 4M→ ... ²* | 0.9 | 0.95 | 1e-8 | 0.1 | 1.0 |
| DeepSeek-V3 | 2.2e-4 | 7.3e-6 ⁷ | 2k steps | ~62.9M ²⁷ | 0.9 | 0.95 | 1e-8 | 0.1 | 1.0 |

*LR shape: GPT-3, Gopher, Chinchilla, OPT, Llama-1/2/3 use cosine decay to ~10% of peak over the token budget; PaLM uses constant-then-inverse-sqrt; DeepSeek-V3 uses a multi-stage constant/cosine schedule (WSD-flavored). See [[Concept - Learning Rate Schedules for Pretraining]].*

## Scale, data, precision, tokenizer

| Model | Params | Tokens | tokens/param | Precision | Optimizer | Vocab |
|---|---|---|---|---|---|---|
| GPT-3 175B | 175B | 300B | 1.7 | fp16 | Adam | 50,257 |
| Gopher 280B | 280B | 300B | 1.07 | bf16 | Adam | 32,000 |
| Chinchilla 70B | 70B | 1.4T | 20 | bf16 | AdamW | 32,000 |
| PaLM 540B | 540B | 780B | 1.44 | bf16 | Adafactor ⁴ | 256,000 |
| OPT-175B | 175B | 180B | 1.03 | fp16 | AdamW | 50,272 |
| Llama-1 65B | 65B | 1.4T | 21.5 | bf16 | AdamW | 32,000 |
| Llama-2 70B | 70B | 2.0T | 28.6 | bf16 | AdamW | 32,000 |
| Llama-3 405B | 405B | 15.6T | 38.5 | bf16 | AdamW | 128,256 |
| Llama-3 8B | 8B | 15T | 1,875 | bf16 | AdamW | 128,256 |
| DeepSeek-V3 | 671B (37B act) | 14.8T | 22 total / 400 active ⁸ | fp8 ⁹ | AdamW | 128,815 |

## Folklore constants (the near-universal defaults)

These are the values that show up run after run, mostly unexplained in the papers, and are the practical defaults for a new dense run — the reasoning is owned by [[Concept - AdamW at Scale]]:

- **β2 = 0.95**, not Adam's 0.999 — a faster second-moment estimate tracks gradient-variance jumps and cuts spike sensitivity (GPT-3, OPT, Llama-1/2/3, DeepSeek-V3).
- **β1 = 0.9** — essentially never changed.
- **weight decay = 0.1** (decoupled/AdamW), **excluded from 1D params** — norms, biases, and often embeddings get no decay. Rarely written down; nearly always done.
- **global-norm gradient clip = 1.0** — tightened to 0.3–0.5 only during an instability ([[Concept - Training Stability and Loss Spikes]]).
- **warmup ≈ 0.1–2% of steps** (commonly ~2000 steps); **min LR = 10% of peak**, not 0, so a checkpoint can be continued.
- **z-loss coefficient ≈ 1e-4** on the output softmax where used (PaLM); router z-loss ≈ 1e-3 for MoE — see [[Concept - z-loss and Logit Soft-Capping]].
- **ε = 1e-8** standard; **Llama used 1e-5** ⁶, a rare deliberate outlier.

## Trends across the rows

- **Overtraining (tokens/param) exploded**: Chinchilla-optimal ≈ 20 → Llama-3 8B ≈ 1,875, a deliberate trade of extra training cost for a smaller, cheaper-to-serve model ([[Concept - Scaling Laws]]).
- **Precision migrated fp16 → bf16 → fp8**: GPT-3/OPT (fp16, loss-scale battles) → Gopher onward (bf16) → DeepSeek-V3 (first production fp8), tracked in [[Concept - Mixed Precision Training]].
- **Batch-size ramping is standard**: GPT-3 went 32k → 3.2M tokens, DeepSeek-V3 ramped to ~63M — exploiting the growing critical batch ([[Concept - Critical Batch Size]]).
- **Optimizer**: AdamW dominates; PaLM's Adafactor and the newer Muon/Shampoo experiments ([[Concept - muP and Hyperparameter Transfer]] covers how HPs transfer across scale) are the exceptions, not the rule.

## Footnotes

1. **Global batch in tokens** = (sequences per step) × (sequence length). Papers report sequences; converted here at each run's context length (2048 for GPT-3/OPT-era, 4096 for Llama-2/3 and DeepSeek-V3).
2. **`a→b` = batch-size warmup**: the batch is ramped from `a` to `b` early in training; the value shown is the terminal steady batch.
3. **PaLM LR**: constant 1e-2 for the first 10k steps, then decays as 1/√(step); there is no fixed minimum.
4. **PaLM used Adafactor** (without factorization), with β1 = 0.9 and second-moment decay 1 − k⁻·⁸, and **weight decay = lr²** (coupled to the current LR). The β2 = 0.95 folklore applies to the AdamW runs, not PaLM.
5. **OPT-175B** lowered global-norm clip from 1.0 to 0.3 during instability episodes (see the logbook).
6. **Llama** used AdamW **ε = 1e-5**, unusually large versus the standard 1e-8 — a rare published deviation.
7. **DeepSeek-V3** LR is multi-stage: constant 2.2e-4, then cosine decay, then constant 2.2e-5, then a 7.3e-6 tail; batch ramped 3,072 → 15,360 sequences (× 4,096 = ~62.9M tokens).
8. **MoE tokens/param** is ambiguous: 14.8T / 671B total ≈ 22; 14.8T / 37B active ≈ 400. Report both.
9. **fp8** = mixed fp8 with per-tile/per-block scaling and fp32 accumulation; sensitive layers stay bf16/fp32 ([[Concept - FP8 Training]]).

## Connections
- [[Concept - AdamW at Scale]] — the reasoning behind the β2=0.95 / wd=0.1 / clip=1.0 folklore surfaced in this table.
- [[Concept - Learning Rate Schedules for Pretraining]] — the schedule shapes (cosine, inverse-sqrt, WSD) the LR columns imply.
- [[Concept - Scaling Laws]] — explains the tokens/param column and the Chinchilla-to-overtraining trend across rows.
- [[Concept - Mixed Precision Training]] — the precision column's fp16→bf16→fp8 migration and why each row chose what it did.
- [[Concept - muP and Hyperparameter Transfer]] — how these LRs/betas can be tuned on a small proxy and transferred, cutting the search this table samples.
- [[Reference - Model Genealogy]] — the lineage of the models tabulated here (who descended from whom); cross-domain lookup companion.
- [[Reference - Memory Math for Transformers]] — pair the param/precision columns with per-tensor memory to size a run's HBM footprint.
- [[Concept - Critical Batch Size]] — the theory behind the batch-size-ramp column and why late training tolerates larger batches.
- [[Concept - FP8 Training]] — the fp8 precision cell (DeepSeek-V3) and the per-block-scaling recipe behind it.
- [[Concept - Training Stability and Loss Spikes]] — why the grad-clip and z-loss folklore constants exist; the table's defaults are its scar tissue.
- [[Concept - z-loss and Logit Soft-Capping]] — the ~1e-4 z-loss constant surfaced in the folklore section, and its mechanism.

## Sources
- Brown et al. (2020) — "Language Models are Few-Shot Learners" (GPT-3) — LR-by-size table, β2=0.95, 32k→3.2M batch ramp, cosine-to-10%.
- Rae et al. (2021) — "Scaling Language Models: Methods, Analysis & Insights from Training Gopher" — the 280B undertrained baseline; LR and batch ramp.
- Hoffmann et al. (2022) — "Training Compute-Optimal Large Language Models" (Chinchilla) — the 20-tokens/param compute-optimal point.
- Chowdhery et al. (2022) — "PaLM" — Adafactor, 1e-2 constant-then-inverse-sqrt LR, z-loss 1e-4, wd=lr².
- Zhang et al. (2022) — "OPT: Open Pre-trained Transformer Language Models" — AdamW (0.9,0.95), the clip 1.0→0.3 instability fix.
- Touvron et al. (2023a,b) — "LLaMA" and "Llama 2" — AdamW ε=1e-5, LR by size, 4M-token batch, cosine-to-10%.
- Llama Team / Dubey et al. (2024) — "The Llama 3 Herd of Models" — 15T-token overtraining, 405B config, batch ramping.
- DeepSeek-AI (2024) — "DeepSeek-V3 Technical Report" — multi-stage LR, fp8, 671B/37B MoE, ~63M-token terminal batch.
- Loshchilov & Hutter (2017) — "Decoupled Weight Regularization" — the AdamW decay convention (wd=0.1) that most rows adopt.
