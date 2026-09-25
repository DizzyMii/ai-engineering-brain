---
tags: [reference, domain/fine-tuning, level/core]
aliases: [LoRA hyperparameters, fine-tuning defaults, SFT hyperparameters]
summary: "Typical LoRA/QLoRA/full-FT hyperparameters: LR, epochs, rank, alpha, warmup, schedule, batch, precision, with rationale."
---

# Reference - Fine-Tuning Hyperparameters

## Core knobs

Defaults for instruction/behavior [[Concept - Supervised Fine-Tuning (SFT)|SFT]]-style fine-tuning, date-stamped to **2024–2026 Llama / Qwen / Mistral-family practice**. "7B SFT" is the reference full-FT column; scale LR down for larger bases.

| Knob | LoRA ([[Deep Dive - LoRA]]) | QLoRA ([[Concept - QLoRA]]) | Full FT (7B SFT) | One-line rationale |
|---|---|---|---|---|
| Learning rate | 1e-4 – 3e-4 | ~2e-4 | 1e-5 – 2e-5 | LoRA wants ~10× full-FT LR: only $A,B$ train, and $\alpha/r$ folds into the effective step¹ |
| Epochs | 1–3 | 1–3 | 1–3 | >3 overfits small sets fast; large datasets often run a single epoch |
| Rank $r$ | 8–64 (16 default) | 8–64 (16 default) | — | Raise for hard domains, **with** rsLoRA scaling² |
| $\alpha$ (lora_alpha) | $2r$ or $r$ | $2r$ (=32 at r=16) | — | $\alpha/r$ is the update scale, not a free knob² |
| LoRA dropout | 0.05–0.1 | 0.05–0.1 | resid. dropout 0–0.1 | Light regularization on small data; 0 for large data |
| Weight decay | 0 (on adapters) | 0 | 0.0–0.1 | Decay on the zero-init $B$ is near-meaningless; apply to full weights only |
| Effective batch | 16–128 | 16–128 | 16–128+ | Via gradient accumulation; **LR scales with effective batch**³ |
| Warmup | 3–10% of steps (~100) | 3–10% (~100) | 3–10% | Stabilizes the early, high-variance steps |
| LR schedule | cosine or linear → ~0 or ~10% of peak | same | cosine → ~10% | Cosine decay is the default; linear is fine for short runs |
| Target modules | all linear⁴ | all linear⁴ | all weights | Coverage beats rank; $q,v$-only underfits |
| Precision | bf16 compute | NF4 base + bf16 compute + double-quant⁵ | bf16 + fp32 master | See [[Concept - Mixed Precision Training]] |
| Grad checkpointing | on (memory) | on (required with paged optim) | on for large seq | Trades ~30% compute for large activation-memory savings |

## Rank / alpha reference

| $r$ | $\alpha$ ($=2r$) | Standard scale $\alpha/r$ | rsLoRA scale $\alpha/\sqrt r$ | When to use |
|---|---|---|---|---|
| 8 | 16 | 2.0 | 5.66 | Style/tone/format; light adaptation |
| 16 | 32 | 2.0 | 8.0 | The common default; most instruction FT |
| 32 | 64 | 2.0 | 11.3 | Larger behavior shifts; enable rsLoRA at/above here² |
| 64 | 128 | 2.0 | 16.0 | Hard domains (code/math); **rsLoRA on or it plateaus** |
| 256 | 512 | 2.0 | 32.0 | Only worthwhile with rsLoRA; approaching full-FT capacity |

Holding $\alpha=2r$ pins the *standard* scale at 2.0 across all ranks, which is the whole point of the $2r$ convention. Under rsLoRA the effective scale $\alpha/\sqrt r$ rises with rank instead. That's intended: it's what keeps the update magnitude rank-invariant. See [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]].

## QLoRA-specific config

| Setting | Value | Why |
|---|---|---|
| Quant type | NF4 | Information-optimal 4-bit for near-normal weights (Dettmers 2023) |
| Compute dtype | bfloat16 | Storage dtype ≠ compute dtype; dequant to bf16 per matmul |
| Double quantization | on | Quantizes the block scale constants too; ~0.37 bits/param saved |
| Optimizer | paged_adamw_8bit | Pages optimizer state to CPU on memory spikes; prevents OOM on long sequences |
| LR | 2e-4 | Community-converged QLoRA default |

## Memory sizing anchors

- Optimizer + gradient + master state ≈ **16 bytes per trainable parameter** under [[Concept - Adam and AdamW|AdamW]] mixed precision. This is the term PEFT collapses. Full derivation: [[Reference - Memory Math for Transformers]].
- Full FT of 7B in bf16 ≈ 14 GB weights + 14 GB grads + ~56 GB fp32 master+moments ≈ **~84 GB** → needs an 80 GB A100 with offload or multi-GPU.
- QLoRA 7B (4-bit base ≈ 3.5–4 GB + bf16 adapter state) **fits in <16 GB** on one consumer card, the democratization result.

## Footnotes

1. **LoRA LR ~10× full-FT.** Only the small $A,B$ factors are optimized, and the $\alpha/r$ scaling multiplies with the LR, so part of the "10×" *is* the scaling factor, not the optimizer. Fix the scaling regime first, then sweep LR (see footnote 2).
2. **Rank/alpha scaling caveat.** By default $\Delta W = (\alpha/r)BA$, and the branch magnitude decays $\propto 1/\sqrt r$, so naively raising $r$ collapses the effective LR and quality plateaus. Use `use_rslora=True` (scaling $\alpha/\sqrt r$) at $r \ge 32$. Copying an $\alpha$ from a config with a different $r$ silently retunes your effective LR. Full mechanism: [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]].
3. **LR–batch coupling.** A larger effective batch reduces gradient noise. The rough heuristic is to scale LR linearly with batch (or by $\sqrt{\cdot}$ for adaptive optimizers). Effective batch = micro-batch × grad-accum × data-parallel world size.
4. **all-linear targets:** `q,k,v,o` plus MLP `gate,up,down`. If you added special tokens or resized embeddings, also put `embed_tokens` and `lm_head` in `modules_to_save`, or the new tokens emit garbage.
5. **Precision.** Keep norm layers and the softmax in fp32 under mixed precision to avoid NaNs. QLoRA stores 4-bit but computes in bf16.

## Connections
- [[Deep Dive - LoRA]] — defines $r$, $\alpha$, target modules, and the $\Delta W = (\alpha/r)BA$ these values parameterize.
- [[Concept - QLoRA]] — the source of the NF4 / double-quant / paged-optimizer settings above.
- [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] — why the rank/alpha table has a scaling caveat and when to flip `use_rslora`.
- [[Playbook - Preparing a Fine-Tuning Dataset]] — the upstream data work these knobs assume is already done (sizing, format, replay).
- [[Concept - Supervised Fine-Tuning (SFT)]] — the objective these defaults target; other objectives (DPO/GRPO) use different LRs.
- [[Concept - Adam and AdamW]] — the optimizer whose LR and per-parameter state these tables are set against.
- [[Concept - Mixed Precision Training]] — the bf16/fp32 regime behind the precision row.
- [[Reference - Memory Math for Transformers]] — the formulas behind the 16-bytes/param and ~84 GB anchors.

## Sources
- Hu et al. 2021 — "LoRA." Rank/alpha/target-module semantics.
- Dettmers et al. 2023 — "QLoRA." NF4, double quantization, paged optimizers, the <16 GB result.
- Kalajdzievski 2023 — "A Rank Stabilization Scaling Factor for Fine-Tuning with LoRA." The $\alpha/\sqrt r$ scaling behind footnote 2.
- Biderman et al. 2024 — "LoRA Learns Less and Forgets Less." Evidence for all-linear coverage and the rank-vs-domain guidance.
