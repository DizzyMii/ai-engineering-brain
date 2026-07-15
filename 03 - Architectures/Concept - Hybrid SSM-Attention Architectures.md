---
tags: [concept, domain/architectures, level/frontier]
aliases: [Jamba, hybrid Mamba-attention, SSM-transformer hybrid, Griffin]
summary: "Interleaving a majority of cheap recurrent/SSM layers with a few full-attention layers to buy exact recall at near-constant KV memory."
---

# Concept - Hybrid SSM-Attention Architectures

> **One-paragraph hook:** A pure [[Concept - State Space Models and Mamba|SSM]] or linear-recurrent model has a fixed-size state, so it cannot do exact copy or associative recall — the thing attention is uniquely good at. A pure transformer has exact recall but a [[Concept - KV Cache|KV cache]] that grows linearly with context. The hybrid insight is that these costs are wildly asymmetric: attention buys recall you can't get any other way, but you need very *little* of it. Interleave a small fraction of full-attention layers (roughly 5–15%) into a stack that is otherwise Mamba/linear-recurrent, and you recover transformer-level quality at a fraction of the long-context inference memory. This is the dominant design for efficient long-context models as of 2026.

## The mechanism

The motivation is a clean, near-theorem result: **attention is required for in-context recall, and a small amount of it suffices.** Jelassi et al. (2024) showed transformers copy/retrieve from context far better than state-space models of equal size, because an SSM must cram the entire prefix into a fixed $d_{state}$-dimensional vector, whereas attention keeps every past token addressable. But recall is *sparse* in the network — you don't need every layer to be able to look back, you need a few. So the hybrid recipe is:

- **Majority recurrent layers.** Most blocks are a [[Concept - State Space Models and Mamba|selective SSM]] (Mamba/Mamba-2) or a gated [[Concept - Linear Attention|linear-attention]] recurrence. Each carries only a constant-size state per sequence, so their contribution to the KV cache is $O(1)$ in context length.
- **A sprinkling of full-attention layers.** Every $k$-th block is standard [[Concept - Attention Mechanism|scaled dot-product attention]], restoring exact lookup. These are the *only* layers that hold a growing cache.
- **Often MoE on top.** The FFN sublayers are frequently sparsified with [[Concept - Mixture of Experts Architecture|mixture-of-experts]] to add capacity without adding active FLOPs, orthogonally to the sequence-mixer choice.

The inference win is arithmetic. If only $1$ in $k$ layers is attention, the KV cache shrinks by roughly $k\times$ versus a same-depth transformer, and the recurrent layers add a fixed few-MB state regardless of sequence length. At 256k context this is the difference between a cache that fits on one GPU and one that doesn't.

The **design knobs** are: the attention-to-recurrence ratio; *placement* (early layers only, evenly periodic, or a specific hand-tuned pattern); whether the attention layers are full or [[Concept - Sparse and Sliding-Window Attention|sliding-window]]; and whether to add MoE. Placement matters because recall has to happen *after* the recurrent layers have done enough local mixing to form the keys worth retrieving — pure front-loading tends to underperform periodic interleaving.

```
Jamba block (attention : Mamba ≈ 1 : 7), stacked ×4
┌───────────────────────────────────────────────┐
│  Mamba  Mamba  Mamba  ATTN  Mamba  Mamba  Mamba │  ← only ATTN grows KV cache
│   +MoE          +MoE         +MoE         +MoE  │  ← MoE on a subset of FFNs
└───────────────────────────────────────────────┘
```

## In practice

- **Jamba (Lieber et al., AI21 2024)** is the reference open hybrid: a 52B-total / 12B-active MoE that interleaves Mamba, attention, and MoE at a **1:7 attention-to-Mamba ratio**. It runs **256k context** with a KV cache small enough to fit alongside weights on a single 80GB GPU — the paper reports roughly an order-of-magnitude smaller cache than a comparable Mixtral-class transformer at long context.
- **Griffin / RecurrentGemma (De et al., DeepMind 2024)** pairs a gated linear recurrence (the RG-LRU block) with **local sliding-window attention** instead of Mamba, matching transformer quality with faster inference and a bounded cache. RecurrentGemma-2B/9B are the open releases.
- **Nemotron-H (NVIDIA 2025)** and **Zamba2 (Zyphra 2024)** are the scale-up data points, both built on Mamba-2 blocks with a thin layer of attention (Nemotron-H uses on the order of ~8% attention layers), reinforcing the emerging **5–15% attention** consensus. See [[Reference - Model Genealogy]] for where these sit in the lineage.

The practical decision — hybrid vs. pure attention vs. pure SSM — is its own note: [[Decision - Choosing a Sequence Mixer]].

## Failure modes

- **Too little attention, silent recall failure.** Push the attention fraction too low and the model looks fine on perplexity and chat but collapses on long-range exact-match: copying a UUID from 40k tokens back, name-tracking, structured extraction. It won't show up in loss; it shows up on needle/multi-key retrieval and code tasks that require verbatim copy. Detect with multi-key associative-recall probes, not single-needle passkey tests.
- **Bad placement.** Front-loading all attention layers starves late-layer retrieval; the fix is periodic placement, found empirically per-architecture.
- **Kernel and serving immaturity.** The recurrent layers don't ride the [[Deep Dive - FlashAttention|FlashAttention]]/vLLM/SGLang path. Chunked scan kernels, state management, and cache handling are less battle-tested, and a naive implementation can be *slower* than attention at short context because the scan has poor arithmetic intensity at small batch. Ecosystem risk is frequently the deciding factor.
- **Two cache types to manage.** A serving stack now juggles a growing KV cache (attention layers) and constant recurrent states (SSM layers) with different eviction/paging semantics — more surface area for bugs.

## The non-obvious

The counterintuitive part is *how few* attention layers you need. Practitioners coming from transformers assume recall is distributed and expect to keep maybe half the layers as attention; the empirical answer is closer to one in ten. The mechanistic reason is that exact retrieval is implemented by a small number of specialized circuits (the [[Concept - Induction Heads|induction-head]] machinery), and once a couple of layers can form and match those, additional attention layers are largely redundant for recall while remaining expensive for memory. The corollary that bites teams: **you cannot certify a hybrid's effective context from perplexity or a single-needle test** — those saturate long before real multi-hop recall does. Budget attention layers against your hardest retrieval eval, not against loss.

**Open question (frontier, weakly settled):** the optimal attention ratio and placement, and whether hybrids reach *frontier* quality at the very largest scales, remain unsettled — most published hybrids top out below the largest dense/MoE transformers, and it's unclear whether that's fundamental or just where the compute has gone.

Hybrids are also a quiet rebuttal to the field's own history: the near-universal convergence on the plain attention+FFN block chronicled in [[Lore - The Standardization of the Transformer Block]] was never inevitable, and the 2024-era hybrid wave is the first sustained, successful departure from it at scale.

## Connections

- [[Concept - State Space Models and Mamba]] — the recurrent substrate that supplies the cheap majority layers; hybrids exist precisely to patch its recall weakness.
- [[Concept - Linear Attention]] — the other constant-state option (Griffin's RG-LRU, gated linear attention) that hybrids interleave with attention.
- [[Concept - Attention Mechanism]] — the exact-recall layer the hybrid keeps a few of; the thing SSMs cannot replicate.
- [[Concept - Sparse and Sliding-Window Attention]] — the attention layers are often *local*, not full, bounding their cache too.
- [[Concept - KV Cache]] — the cost the hybrid is designed to minimize; only attention layers contribute to it.
- [[Concept - Mixture of Experts Architecture]] — orthogonal sparsity axis routinely stacked on top (Jamba is Mamba + attention + MoE).
- [[Concept - Induction Heads]] — the circuit that implements recall, explaining why so few attention layers suffice.
- [[Decision - Choosing a Sequence Mixer]] — where the hybrid-vs-pure tradeoff is decided against your context and recall requirements.
- [[Reference - Model Genealogy]] — situates Jamba, Griffin, Nemotron-H, Zamba2 in the broader model family tree.
- [[Lore - The Standardization of the Transformer Block]] — the ladder up-link: the history of how the field converged on a pure-attention block, which hybrids are the first successful large-scale departure from.

## Sources
- Lieber et al. (2024) — *Jamba: A Hybrid Transformer-Mamba Language Model.* The canonical open 1:7 attention-to-Mamba + MoE recipe at 256k context.
- Jelassi et al. (2024) — *Repeat After Me: Transformers are Better than State Space Models at Copying.* The recall/copying gap that motivates keeping attention.
- De et al. (2024) — *Griffin: Mixing Gated Linear Recurrences with Local Attention.* Recurrence + sliding-window attention; basis of RecurrentGemma.
- Gu & Dao (2023); Dao & Gu (2024) — Mamba and Mamba-2/SSD, the selective-SSM blocks most hybrids use.
- NVIDIA (2025) — *Nemotron-H*; Zyphra (2024) — *Zamba2.* Scale-up hybrids converging on ~5–15% attention.
