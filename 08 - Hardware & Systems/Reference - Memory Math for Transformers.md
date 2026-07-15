---
tags: [reference, domain/hardware-systems, level/core]
aliases: [transformer memory formula, GPU memory budget, KV cache size formula, AdamW memory formula]
summary: "The byte formulas for transformer parameters, training state, activations, and KV cache — what fits on a GPU, worked for 7B and 70B."
---

# Reference - Memory Math for Transformers

Formula sheet for computing GPU memory before you launch a job — the capacity-planning counterpart to the [[Concept - GPU Memory Hierarchy]] (this tells you what fits; that tells you how fast it moves) and to [[Concept - Model FLOPs Utilization (MFU)]] (memory tells you if the job runs at all, MFU tells you how efficiently it runs once it does). All formulas are per-model unless stated; combine with sharding degree (data/tensor/ZeRO) from the cross-reference table at the bottom.

## Parameter count

$$
P \approx 12 \cdot n_{layers} \cdot d_{model}^2 \;+\; 2 \cdot vocab \cdot d_{model}
$$

The $12 d_{model}^2$ term is one decoder layer: 4$d^2$ for the four attention projections (Q, K, V, O) + 8$d^2$ for a 4×-expansion MLP (up + down projection); the vocab term is input embedding + (if untied) output head.

| Model | $n_{layers}$ | $d_{model}$ | Formula result | Actual (public) |
|---|---|---|---|---|
| ~7B class (e.g. Llama-2-7B) | 32 | 4096 | ~6.4B core + ~0.3B embed ≈ **6.7B** | 6.7B |
| ~70B class (e.g. Llama-2-70B) | 80 | 8192 | ~64.4B core + ~0.5B embed ≈ **65B** | 68.9B¹ |

¹ Gap from GQA (fewer KV-projection params than full MHA) and non-4× SwiGLU MLP ratios in real configs — treat the formula as an order-of-magnitude estimate, not exact.

## Training memory per parameter (mixed-precision AdamW)

| Term | Bytes/param | Notes |
|---|---|---|
| fp16/bf16 weights | 2 | the copy used for forward/backward compute |
| fp32 master weights | 4 | kept for optimizer-step precision |
| Adam momentum ($m$) | 4 | fp32 |
| Adam variance ($v$) | 4 | fp32 |
| Gradient | 2–4 | 2 if kept fp16/bf16, 4 if accumulated in fp32 |
| **Total** | **16–18** | see [[Concept - Mixed Precision Training]] |

$$
\text{Training memory} \approx P \times (16 \text{ to } 18)\text{ bytes}
$$

**Worked example:** a 7B model needs $7\text{B} \times 16\text{–}18 \approx 112\text{–}126$ GB just for parameter state — before activations — which does not fit on a single 80 GB H100 (as of 2026) and forces sharding via [[Concept - Data Parallelism and ZeRO]] or tensor parallelism. A 70B model needs ~1.1–1.3 TB, requiring double-digit GPU counts just to hold state.

## Activation memory

Per Korthikanti et al. (2022, "Reducing Activation Recomputation in Large Transformer Models"), activation memory for one transformer layer without recomputation is approximately:

$$
\text{Activations/layer} \approx s \cdot b \cdot h \cdot \left(34 + \frac{5 \cdot a \cdot s}{h}\right) \text{ bytes}
$$

where $s$ = sequence length, $b$ = batch size, $h$ = hidden dim, $a$ = number of attention heads (bf16 activations, standard attention implementation). This scales **linearly in batch, linearly in hidden size, and roughly quadratically in sequence length** through the attention term — the reason long-context training is activation-memory-dominated. **Activation recomputation** (store only the layer input, recompute the rest in the backward pass) cuts this to roughly $s \cdot b \cdot h \cdot 2$ bytes/layer at the cost of ~30% extra FLOPs — a favorable trade because these ops are memory-bound anyway (see [[Concept - The Memory Wall]]).

## KV cache

$$
\text{KV cache bytes} = 2 \cdot n_{layers} \cdot n_{kv\_heads} \cdot d_{head} \cdot seq \cdot batch \cdot bytes_{elem}
$$

The leading 2 is for K and V. $n_{kv\_heads}$ is the lever [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] pulls: full MHA sets $n_{kv\_heads} = n_{heads}$; GQA/MQA shrink it independently of the query head count.

**Worked example** (32 layers, $d_{head}=128$, seq=4096, batch=1, fp16):
- Full MHA, 32 KV heads: $2 \times 32 \times 32 \times 128 \times 4096 \times 2 \text{ bytes} \approx 2.0$ GiB per sequence.
- GQA, 8 KV heads (4× fewer): **≈ 0.5 GiB per sequence** — a 4× cut for the same quality-relevant query head count. Full mechanics in [[Concept - KV Cache]].

## Inference weight memory by dtype

| Dtype | Bytes/param | 7B model | 70B model |
|---|---|---|---|
| fp16/bf16 | 2 | 14 GB | 140 GB |
| fp8 | 1 | 7 GB | 70 GB |
| int4 | 0.5 | 3.5 GB | 35 GB |

Add KV cache (above) and a **~1.1–1.2× runtime overhead** (CUDA graphs, workspace buffers, fragmentation) for the real deployable footprint. See [[Concept - Post-Training Quantization Formats]] for what each dtype costs in quality.

## Quick-fit heuristics

- **"params × 2" bytes** ≈ fp16 inference weight memory (before KV cache).
- **"params × ~18" bytes** ≈ mixed-precision AdamW training memory, unsharded.
- Recompute-vs-store: recomputation buys you a ~5–10× activation memory cut for ~30% more FLOPs — nearly always worth it when activations, not compute, are the binding constraint.

## Sharding cross-reference (approximate; see [[Concept - Data Parallelism and ZeRO]] for exact mechanics)

| Memory term | ZeRO-1 | ZeRO-2 | ZeRO-3 / FSDP | + Tensor-parallel degree $T$ |
|---|---|---|---|---|
| Optimizer state (master, $m$, $v$) | ÷N | ÷N | ÷N | also ÷$T$ |
| Gradients | full | ÷N | ÷N | also ÷$T$ |
| Weights | full | full | ÷N | also ÷$T$ |
| Activations | full (unless recomputed) | full | full | roughly ÷$T$ |

($N$ = data-parallel world size.) This is why a memory budget for a large run always has to specify *which* sharding degree divides *which* term — quoting "GB per GPU" without the parallelism config is meaningless.

## Connections

- [[Concept - GPU Memory Hierarchy]] — the physical HBM capacity (80/141/192 GB across H100/H200/B200) these formulas are budgeting against.
- [[Concept - Model FLOPs Utilization (MFU)]] — the compute-side counterpart; memory math tells you what fits, MFU tells you how fast it runs once it does.
- [[Concept - KV Cache]] — the full mechanics and paging behavior behind the KV cache formula above.
- [[Concept - Data Parallelism and ZeRO]] — how the sharding cross-reference table is actually implemented.
- [[Concept - Mixed Precision Training]] — the source of the 16–18 bytes/param training figure.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — the architectural choice that sets $n_{kv\_heads}$ in the KV cache formula.
- [[Concept - Post-Training Quantization Formats]] — what fp8/int4 weight compression costs in accuracy, not just bytes.
- [[Concept - The Memory Wall]] — why activation recomputation is a favorable trade even though it adds FLOPs.

## Sources

- Korthikanti et al. (2022) — "Reducing Activation Recomputation in Large Transformer Models" — the activation memory formula and selective-recomputation tradeoff.
- Rajbhandari et al. (2020) — "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models" — the optimizer/gradient/weight sharding stages referenced in the cross-reference table.
