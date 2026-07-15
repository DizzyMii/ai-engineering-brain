---
tags: [reference, domain/fine-tuning, level/core]
aliases: [PEFT comparison, PEFT matrix, PEFT method table]
summary: "Lookup matrix: PEFT methods by param count, family, mergeability, inference cost, quality vs full FT, and best-fit use case."
---

# Reference - PEFT Method Comparison

## Method matrix

Quality vs full FT is date-stamped to **2024–2026 open-model practice** (Llama/Qwen/Mistral families); it is task-dependent and the row notes say for which tasks. "Mergeable" and latency columns are defined in the footnotes.

| Method | Family¹ | Trainable %² | Mergeable?³ | Extra inference latency⁴ | Quality vs full FT⁵ | Best-fit use case | Key paper |
|---|---|---|---|---|---|---|---|
| LoRA ([[Deep Dive - LoRA]]) | reparam | 0.1–1% | Yes | +0 (after merge) | ~95–99% on instruction/style; lags on code/math | The general default | Hu 2021 |
| QLoRA ([[Concept - QLoRA]]) | reparam + 4-bit NF4 base | 0.1–1% (adapter) | Only after dequantizing base⁶ | +0 after merge; dequant overhead at *train* time | ≈ LoRA | Consumer-GPU FT of large models | Dettmers 2023 |
| DoRA ([[Concept - DoRA]]) | reparam (magnitude + direction) | ~LoRA + <0.01% | Yes | +0 after merge | **>** LoRA, most at low rank (+1–4 pts commonsense) | When the small quality bump is worth extra train cost | Liu 2024 |
| rsLoRA⁷ | reparam (scaling fix) | = LoRA | Yes | +0 | Unlocks high-rank LoRA (r=64–256) | Hard domains at r ≥ 32 | Kalajdzievski 2023 |
| Adapters — Houlsby | additive bottleneck | 0.5–8% | **No** | **+latency (sequential layer)** | Strong NLU, near full FT | Multi-task, latency-tolerant | Houlsby 2019 |
| Adapters — Pfeiffer | additive bottleneck | ~½ Houlsby | **No** | **+latency** | ≈ Houlsby | AdapterHub default | Pfeiffer 2021 |
| IA3 ([[Concept - Adapter Layers]]) | additive rescale | 0.01–0.05% | Foldable into weights⁸ | ~+0 | Strong few-shot (T-Few) | Few-shot, tiny budget | Liu 2022 |
| BitFit | selective (biases only) | ~0.08% | N/A (updates real params) | +0 | Small-model only; weakens at scale | Minimal-budget, small models | Ben-Zaken 2021 |
| Prompt tuning ([[Concept - Prompt Tuning and Prefix Tuning]]) | additive (soft prompt) | <0.1% | **No** | Consumes context window | Matches full FT only >10B | Multi-task serving (swap prompts) | Lester 2021 |
| Prefix tuning ([[Concept - Prompt Tuning and Prefix Tuning]]) | additive (KV prefix) | <0.1% | **No** | Consumes context / KV per layer | **>** prompt tuning; ~full FT (P-tuning v2) | Multi-task NLG | Li & Liang 2021 |
| VeRA | reparam (shared frozen random + tiny scales) | ~1/10 of LoRA | Yes | +0 after merge | ≈ LoRA at far fewer stored params | Many adapters, storage-bound | Kopiczko 2024 |
| (Lo)ReFT ([[Concept - Representation Fine-Tuning (ReFT)]]) | activation intervention | 0.01–0.05% | **No** | Small (runs like an adapter) | ≈ / **>** LoRA on some tasks (10–50× fewer params) | Extreme parameter efficiency | Wu 2024 |

## Family quick-reference

| Family¹ | What it trains | Mergeable? | Canonical members |
|---|---|---|---|
| Reparameterization | Factors of a low-rank weight *update* $\Delta W$ | Yes (fold $\Delta W$ into $W$) | LoRA, QLoRA, DoRA, rsLoRA, VeRA |
| Additive | New modules/vectors inserted into the frozen network | Usually no (sequential) | Adapters, IA3, prompt/prefix tuning |
| Selective | An existing subset of the model's own weights | N/A (already in $W$) | BitFit |
| Intervention | Edits to hidden activations at inference | No | (Lo)ReFT |

## Memory rule of thumb

- Trainable-parameter memory ≈ **16 bytes/param** under [[Concept - Adam and AdamW|AdamW]] mixed precision (bf16 weight+grad + fp32 master + 2× fp32 moments); this is the term PEFT shrinks. Frozen base weights are unchanged. Full formulas: [[Reference - Memory Math for Transformers]].
- Example: rank-16 LoRA on all linear layers of a 7B model ≈ **40M trainable params (~0.6%)** → a few hundred MB of optimizer state, versus ~84 GB for full FT of the same model.
- QLoRA's saving is on the **frozen base** (4-bit NF4 ≈ 0.5 GB/B-param) not the adapter; the adapter memory equals plain LoRA's.

## Footnotes

1. **Family** — additive / selective / reparameterization taxonomy (Ding et al. 2022), the organizing frame of [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]]; "intervention" added for ReFT, which edits activations rather than weights.
2. **Trainable %** — fraction of base parameters that receive gradients; drives optimizer/gradient memory, not forward-pass FLOPs. Ranges are for 7B-class models with all-linear targeting where applicable.
3. **Mergeable** — whether the learned update can be algebraically folded back into the base weights so that inference runs the *original* graph with *zero* added cost. Mergeability, more than quality, is why the reparameterization family won large-scale LLM serving; the serving-side payoff is owned by [[Concept - Continuous Batching]] and multi-adapter serving in domain 07.
4. **Extra inference latency** — cost paid *per token at serving time* relative to the base model. "Sequential layer" means the module sits in the forward path and cannot be removed; "consumes context window" means soft-prompt/prefix tokens occupy positions that would otherwise hold input.
5. **Quality vs full FT** — relative task quality *(as of 2024–2026 open-model practice)*; highly task-dependent. All reparameterization methods track full FT closely on instruction/style and lag on large-distribution-shift domains (code, math) — mechanism in [[Concept - Why LoRA Underperforms Full Fine-Tuning]].
6. **QLoRA merge** — merging an adapter into a still-4-bit base loses accuracy; dequantize the base to fp16 first, then merge (see [[Concept - QLoRA]]).
7. **rsLoRA** — not a separate parameterization but a scaling correction to LoRA ($\alpha/\sqrt r$ instead of $\alpha/r$); see [[Reference - Fine-Tuning Hyperparameters]] and the [[Concept - rsLoRA and the Rank-Alpha Scaling Trap|scaling trap]].
8. **IA3 foldable** — the learned element-wise rescaling vectors multiply keys/values/FFN activations and can be absorbed into adjacent weight matrices, so IA3 adds no residual inference cost despite being in the additive family.

## Connections
- [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] — the parent concept whose three-family taxonomy this matrix instantiates row by row.
- [[Deep Dive - LoRA]] — the reparameterization method every other row is measured against.
- [[Concept - QLoRA]] — the 4-bit-base row; where the "mergeable only after dequant" footnote comes from.
- [[Concept - DoRA]] — the row that beats LoRA at equal params, especially at low rank.
- [[Concept - Adapter Layers]] — the additive lineage (Houlsby/Pfeiffer/IA3/BitFit) and why sequential adapters add latency.
- [[Concept - Prompt Tuning and Prefix Tuning]] — the soft-prompt rows and their context-window cost.
- [[Concept - Representation Fine-Tuning (ReFT)]] — the activation-intervention row with 10–50× fewer params than LoRA.
- [[Concept - Continuous Batching]] — the serving mechanism whose economics make "mergeable / no added latency" matter.
- [[Reference - Memory Math for Transformers]] — the byte-per-parameter formulas behind the memory rule of thumb.

## Sources
- Ding et al. 2022 — "Delta Tuning." The family taxonomy used in the quick-reference table.
- Hu et al. 2021 (LoRA); Dettmers et al. 2023 (QLoRA); Liu et al. 2024 (DoRA); Kalajdzievski 2023 (rsLoRA); Houlsby et al. 2019 / Pfeiffer et al. 2021 (adapters); Liu et al. 2022 (IA3, T-Few); Ben-Zaken et al. 2021 (BitFit); Lester et al. 2021 (prompt tuning); Li & Liang 2021 (prefix tuning); Kopiczko et al. 2024 (VeRA); Wu et al. 2024 (ReFT).
