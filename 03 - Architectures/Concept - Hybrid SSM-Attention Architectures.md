---
tags: [concept, domain/architectures, level/frontier]
aliases: [Jamba, hybrid Mamba-attention, SSM-transformer hybrid, Griffin]
summary: "Interleaving a majority of cheap recurrent/SSM layers with a few full-attention layers to buy exact recall at near-constant KV memory."
---

# Concept - Hybrid SSM-Attention Architectures

> **One-paragraph hook:** A pure [[Concept - State Space Models and Mamba|SSM]] or linear-recurrent model has a fixed-size state, so it can't do exact copy or associative recall, which is what attention is uniquely good at. A pure transformer has exact recall, but its [[Concept - KV Cache|KV cache]] grows linearly with context. The hybrid bet is that these costs are lopsided: attention buys recall nothing else gives you, and you need very *little* of it. Interleave a small fraction of full-attention layers (roughly 5–15%) into an otherwise Mamba/linear-recurrent stack and you get transformer-level quality back at a fraction of the long-context inference memory. This is the dominant design for efficient long-context models as of 2026.

## The mechanism

The motivation is close to a theorem: **attention is required for in-context recall, and a small amount of it suffices.** Jelassi et al. (2024) showed transformers copy and retrieve from context far better than state-space models of equal size. An SSM has to cram the whole prefix into a fixed $d_{state}$-dimensional vector; attention keeps every past token addressable. But recall is *sparse* in the network: only a few layers need to look back. The recipe:

- **Mostly recurrent layers.** Most blocks are a [[Concept - State Space Models and Mamba|selective SSM]] (Mamba/Mamba-2) or a gated [[Concept - Linear Attention|linear-attention]] recurrence. Each keeps only a constant-size state per sequence, so it adds $O(1)$ to the KV cache regardless of context length.
- **A few full-attention layers.** Every $k$-th block is standard [[Concept - Attention Mechanism|scaled dot-product attention]], which restores exact lookup. Only these layers hold a growing cache.
- **Often MoE on top.** The FFN sublayers are frequently sparsified with [[Concept - Mixture of Experts Architecture|mixture-of-experts]] to add capacity without adding active FLOPs. That choice is independent of the sequence mixer.

The savings are arithmetic. With $1$ in $k$ layers as attention, the KV cache shrinks by roughly $k\times$ against a same-depth transformer, and the recurrent layers add a fixed few-MB state whatever the sequence length. At 256k context that decides whether the cache fits on one GPU.

What you get to tune: the attention-to-recurrence ratio; *placement* (early layers only, evenly periodic, or a hand-tuned pattern); full vs. [[Concept - Sparse and Sliding-Window Attention|sliding-window]] attention layers; and whether to add MoE. Placement matters because recall has to come *after* the recurrent layers have done enough local mixing to form keys worth retrieving. Putting all the attention up front tends to underperform periodic interleaving.

```
Jamba block (attention : Mamba ≈ 1 : 7), stacked ×4
┌───────────────────────────────────────────────┐
│  Mamba  Mamba  Mamba  ATTN  Mamba  Mamba  Mamba │  ← only ATTN grows KV cache
│   +MoE          +MoE         +MoE         +MoE  │  ← MoE on a subset of FFNs
└───────────────────────────────────────────────┘
```

## In practice

- **Jamba (Lieber et al., AI21 2024)** is the reference open hybrid: a 52B-total / 12B-active MoE interleaving Mamba, attention and MoE at a **1:7 attention-to-Mamba ratio**. It runs **256k context** with a KV cache small enough to sit alongside the weights on a single 80GB GPU. The paper reports a cache roughly an order of magnitude smaller than a comparable Mixtral-class transformer at long context.
- **Griffin / RecurrentGemma (De et al., DeepMind 2024)** uses a gated linear recurrence (the RG-LRU block) with **local sliding-window attention** in place of Mamba. It matches transformer quality with faster inference and a bounded cache. RecurrentGemma-2B/9B are the open releases.
- **Nemotron-H (NVIDIA 2025)** and **Zamba2 (Zyphra 2024)** are the scale-up data points. Both are built on Mamba-2 blocks with a thin layer of attention (Nemotron-H uses on the order of ~8% attention layers), which supports the emerging **5–15% attention** consensus. [[Reference - Model Genealogy]] shows where they sit in the lineage.

Hybrid vs. pure attention vs. pure SSM is its own note: [[Decision - Choosing a Sequence Mixer]].

## Failure modes

- **Too little attention, silent recall failure.** Push the attention fraction too low and the model looks fine on perplexity and chat, then collapses on long-range exact match: copying a UUID from 40k tokens back, tracking names, structured extraction. Loss won't show it. Needle/multi-key retrieval and code tasks that need verbatim copy will. Test with multi-key associative-recall probes; single-needle passkey tests miss it.
- **Bad placement.** Putting all the attention layers up front starves late-layer retrieval. Periodic placement fixes it, and the right pattern is found empirically per architecture.
- **Immature kernels and serving.** The recurrent layers don't get the [[Deep Dive - FlashAttention|FlashAttention]]/vLLM/SGLang path. Chunked scan kernels, state management and cache handling have seen less production use, and a naive implementation can be *slower* than attention at short context because the scan has poor arithmetic intensity at small batch. Ecosystem risk is frequently what decides it.
- **Two cache types.** The serving stack now handles a growing KV cache (attention layers) and constant recurrent states (SSM layers) with different eviction/paging semantics, which means more places for bugs.

## The non-obvious

The surprise is *how few* attention layers you need. Transformer people assume recall is spread out and expect to keep maybe half the layers as attention. Empirically it's closer to one in ten. Mechanistically, exact retrieval runs on a small number of specialized circuits (the [[Concept - Induction Heads|induction-head]] machinery). Once a couple of layers can form and match those, more attention layers add little for recall and still cost memory. What catches teams out: **you can't certify a hybrid's effective context from perplexity or a single-needle test.** Both saturate long before real multi-hop recall does. Size the attention budget against your hardest retrieval eval, not against loss.

**Open question (frontier, weakly settled):** the best attention ratio and placement are still unsettled, and so is whether hybrids reach *frontier* quality at the very largest scales. Most published hybrids top out below the largest dense/MoE transformers, and nobody knows yet whether that's inherent or just where the compute has gone.

Hybrids also cut against the field's own history. The near-universal convergence on the plain attention+FFN block, told in [[Lore - The Standardization of the Transformer Block]], was never inevitable, and the 2024-era hybrid wave is the first sustained, successful departure from it at scale.

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
