---
tags: [reference, domain/hardware-systems, level/core]
aliases: [transformer memory formula, GPU memory budget, KV cache size formula, AdamW memory formula]
summary: "The byte formulas for transformer parameters, training state, activations, and KV cache — what fits on a GPU, worked for 7B and 70B."
---

# Reference - Memory Math for Transformers

Formulas for working out GPU memory before you launch a job. This note says what fits; [[Concept - GPU Memory Hierarchy]] says how fast it moves. Memory decides whether the job runs at all, and [[Concept - Model FLOPs Utilization (MFU)]] decides how efficiently it runs once it does. Formulas are per-model unless stated. Divide by the sharding degree (data/tensor/ZeRO) using the table at the bottom.

## Parameter count

$$
P \approx 12 \cdot n_{layers} \cdot d_{model}^2 \;+\; 2 \cdot vocab \cdot d_{model}
$$

The $12 d_{model}^2$ term is one decoder layer: 4$d^2$ for the four attention projections (Q, K, V, O) plus 8$d^2$ for a 4×-expansion MLP (up and down projection). The vocab term is the input embedding plus the output head if it's untied.

| Model | $n_{layers}$ | $d_{model}$ | Formula result | Actual (public) |
|---|---|---|---|---|
| ~7B class (e.g. Llama-2-7B) | 32 | 4096 | ~6.4B core + ~0.3B embed ≈ **6.7B** | 6.7B |
| ~70B class (e.g. Llama-2-70B) | 80 | 8192 | ~64.4B core + ~0.5B embed ≈ **65B** | 68.9B¹ |

¹ The gap comes from GQA (fewer KV-projection params than full MHA) and non-4× SwiGLU MLP ratios in real configs. Treat the formula as an order-of-magnitude estimate.

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

Worked example: a 7B model needs $7\text{B} \times 16\text{–}18 \approx 112\text{–}126$ GB for parameter state alone, before activations. That doesn't fit on one 80 GB H100 (as of 2026), so you have to shard with [[Concept - Data Parallelism and ZeRO]] or tensor parallelism. A 70B model needs ~1.1–1.3 TB, which takes double-digit GPU counts just to hold state.

## Activation memory

From Korthikanti et al. (2022, "Reducing Activation Recomputation in Large Transformer Models"), activation memory for one transformer layer without recomputation is approximately:

$$
\text{Activations/layer} \approx s \cdot b \cdot h \cdot \left(34 + \frac{5 \cdot a \cdot s}{h}\right) \text{ bytes}
$$

where $s$ = sequence length, $b$ = batch size, $h$ = hidden dim, $a$ = number of attention heads (bf16 activations, standard attention). It grows **linearly in batch and hidden size and roughly quadratically in sequence length** through the attention term, so activations dominate memory in long-context training. **Activation recomputation** stores only the layer input and recomputes the rest in the backward pass. That cuts it to roughly $s \cdot b \cdot h \cdot 2$ bytes/layer for ~30% extra FLOPs, a good trade since these ops are memory-bound anyway (see [[Concept - The Memory Wall]]).

## KV cache

$$
\text{KV cache bytes} = 2 \cdot n_{layers} \cdot n_{kv\_heads} \cdot d_{head} \cdot seq \cdot batch \cdot bytes_{elem}
$$

The leading 2 covers K and V. [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] is about $n_{kv\_heads}$: full MHA sets $n_{kv\_heads} = n_{heads}$, and GQA/MQA shrink it without touching the query head count.

Worked example (32 layers, $d_{head}=128$, seq=4096, batch=1, fp16):
- Full MHA, 32 KV heads: $2 \times 32 \times 32 \times 128 \times 4096 \times 2 \text{ bytes} \approx 2.0$ GiB per sequence.
- GQA, 8 KV heads (4× fewer): **≈ 0.5 GiB per sequence**. A 4× cut with the same query head count, which is what matters for quality. Full mechanics in [[Concept - KV Cache]].

## Inference weight memory by dtype

| Dtype | Bytes/param | 7B model | 70B model |
|---|---|---|---|
| fp16/bf16 | 2 | 14 GB | 140 GB |
| fp8 | 1 | 7 GB | 70 GB |
| int4 | 0.5 | 3.5 GB | 35 GB |

For the real deployed footprint, add KV cache (above) and **~1.1–1.2× runtime overhead** (CUDA graphs, workspace buffers, fragmentation). [[Concept - Post-Training Quantization Formats]] covers what each dtype costs in quality.

## Quick-fit heuristics

- **"params × 2" bytes** ≈ fp16 inference weight memory (before KV cache).
- **"params × ~18" bytes** ≈ mixed-precision AdamW training memory, unsharded.
- Recompute vs. store: recomputation buys a ~5–10× activation memory cut for ~30% more FLOPs. Nearly always worth it when activations are the limit and compute isn't.

## Sharding cross-reference (approximate; see [[Concept - Data Parallelism and ZeRO]] for exact mechanics)

| Memory term | ZeRO-1 | ZeRO-2 | ZeRO-3 / FSDP | + Tensor-parallel degree $T$ |
|---|---|---|---|---|
| Optimizer state (master, $m$, $v$) | ÷N | ÷N | ÷N | also ÷$T$ |
| Gradients | full | ÷N | ÷N | also ÷$T$ |
| Weights | full | full | ÷N | also ÷$T$ |
| Activations | full (unless recomputed) | full | full | roughly ÷$T$ |

($N$ = data-parallel world size.) A memory budget for a large run has to say *which* sharding degree divides *which* term. "GB per GPU" without the parallelism config means nothing.

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
