---
tags: [breakdown, domain/architectures, level/advanced]
aliases: [Mixtral, Mixtral-8x7B, Mixtral 8x7B]
summary: "Mistral's top-2-of-8 sparse MoE: 47B total / ~13B active — the canonical open MoE and its misread expert-specialization finding."
---

# Breakdown - Mixtral 8x7B

> Mixtral 8x7B is Mistral AI's sparse [[Concept - Mixture of Experts Architecture|mixture-of-experts]] model, released open-weights under Apache 2.0 in December 2023 (paper: Jiang et al., *Mixtral of Experts*, Jan 2024). It was the first strong, fully-open MoE with a clean published recipe. It made "top-2 of 8" the reference point for open MoE and produced the most-cited (and most-misunderstood) result about what experts specialize in. It reaches Llama-2-70B / GPT-3.5-class quality while activating ~13B parameters per token. *(as of 2026, superseded on the quality frontier but still the canonical teaching example.)*

## The headline numbers

| Property | Value |
|---|---|
| Total parameters | **47B** (not 56B — see math below) |
| Active parameters / token | **~13B** (top-2 of 8 experts) |
| Layers | 32 |
| $d_{model}$ | 4096 |
| Attention | 32 query heads, **8 KV heads** ([[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)|GQA]]), $d_{head}=128$ |
| FFN | SwiGLU, $d_{ff}=14336$, **8 experts/layer**, top-2 |
| Norm / position | pre-norm [[Concept - RMSNorm and LayerNorm|RMSNorm]], [[Concept - Rotary Position Embeddings (RoPE)|RoPE]] ($\theta=10^6$) |
| Vocab / context | 32000 / 32768 |
| License | Apache 2.0 |

## How it works

Mixtral is Mistral 7B's architecture with **only the FFN sublayer swapped for MoE**. Attention stays fully dense. Each block runs standard GQA attention, then sends each token to 2 of 8 expert FFNs:

```
token x  ─►  RMSNorm ─► GQA attention ─► + residual
         ─►  RMSNorm ─► router (Linear 4096→8) ─► softmax
                              │
                     top-2 experts (i, j), renormalize gates
                              │
             g_i·Expert_i(x) + g_j·Expert_j(x)  ─► + residual
```

The router is a per-layer linear gate producing 8 logits. Softmax, take the **top-2**, **renormalize** those two gate weights to sum to 1, and take the weighted sum of the two expert outputs. Each expert is a full SwiGLU FFN (gate/up/down, $4096\times14336$). Everything else (GQA with 8 KV heads, RoPE, pre-norm RMSNorm, no biases) comes verbatim from Mistral 7B. One difference: Mixtral **drops the sliding-window attention** Mistral 7B used and runs full attention over the 32k window.

**The parameter math**, or why "8x7B" = 47B and not 56B: the "8x" multiplies *only the FFN*, not the whole 7B model. Attention, embeddings, norms and the router are shared once.
- Experts: $3 \times 4096 \times 14336 \approx 176\text{M}$ per expert (SwiGLU = 3 matrices) $\times\,8 \times 32 \approx 45.1\text{B}$
- Attention (per layer $\approx 42\text{M}$) $\times\,32 \approx 1.3\text{B}$; embed + unembed $\approx 0.26\text{B}$
- **Total $\approx 47\text{B}$.** Active per token = 2/8 of the experts + all shared params $\approx 13\text{B}$.

The name double-counts the shared components. The "7B" is nominal; there's no real submodel you can extract.

## The clever parts

1. **Sparsity decouples capacity from compute.** Mixtral has the *parameter budget* of a 47B model and the *active FLOPs* of a ~13B one. At fixed inference compute it beats any 13B dense model, because the extra 34B of resident experts add capacity the router can dial in per token. That's the whole value proposition of MoE (see [[Decision - Dense vs Mixture-of-Experts]]).
2. **Clean top-2 renormalized routing.** Top-2 (vs. Switch Transformer's top-1) gives each token a small ensemble and a smoother loss surface. Renormalizing the two gates keeps output scale stable whatever the raw softmax mass. It's the simplest recipe that works, and that's why it became the reference.
3. **The expert-specialization finding, and how people misread it.** The paper's most-cited result is *negative*: experts **do not specialize by topic or domain.** Routing shows mild **syntactic/positional** structure. Consecutive tokens frequently go to the same expert, and code/whitespace tokens cluster, but there's no "biology expert" or "Python expert." Load is fairly uniform across the 8. Practitioners routinely misremember this as "experts specialize"; the paper found the opposite, and that's why interpretable expert routing is still an open problem.
4. **Inheritance discipline.** Mistral reused a known-good dense recipe (GQA, SwiGLU, RoPE, RMSNorm) and changed one sublayer. Cheap to build, easy to trust.

## What it got wrong / what's dated

- **Coarse-grained experts leave specialization on the table.** 8 big experts with top-2 is a blunt instrument. [[Breakdown - DeepSeek-V3 Architecture|DeepSeek's]] fine-grained design (256 small experts, top-8, plus an always-on shared expert) specializes far better and gets more out of the same active-FLOP budget. Mixtral's recipe now reads as first-generation.
- **Serving is memory-bound like a big dense model.** All **47B stay resident** even though only 13B is active, so a single request pays the memory-bandwidth cost of a large model for the compute of a small one. Sparsity only pays off with enough batch to keep experts busy (see [[Concept - MoE Inference and Expert Parallelism]] and [[Concept - Cost Engineering for LLM Applications]]).
- **Batch-dependent outputs.** Which tokens share a batch changes expert load and, under capacity limits, which tokens get dropped. It's a nondeterminism source that surprises teams (see [[Gotchas - Mixture of Experts]]).

## What to steal

- The **top-2 renormalized routing recipe** transfers directly and is a fine default for a first MoE.
- **MoE only the FFN.** Keep attention dense and sparsify the part holding two-thirds of the parameters ([[Concept - Feed-Forward Networks and GLU Variants|the FFN]]). Nearly every MoE since does this.
- The **expert-parallel serving mindset**: plan for all-experts-resident memory and large-batch throughput from day one. MoE is a throughput architecture, not a single-user-latency one.
- Don't copy the coarse 8-expert granularity blind. Go fine-grained + shared-expert if specialization and efficiency matter.

## Connections

- [[Concept - Mixture of Experts Architecture]] — the general mechanism Mixtral instantiates; read it first for routing/capacity theory.
- [[Breakdown - DeepSeek-V3 Architecture]] — the next-generation MoE that supersedes Mixtral's coarse recipe with fine-grained + shared experts.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — Mixtral's attention is GQA (8 KV heads), inherited from Mistral 7B.
- [[Concept - Rotary Position Embeddings (RoPE)]] — position scheme, with $\theta$ raised to $10^6$.
- [[Concept - Feed-Forward Networks and GLU Variants]] — each expert is a SwiGLU FFN; the sublayer MoE replaces.
- [[Concept - RMSNorm and LayerNorm]] — pre-norm RMSNorm, the block-norm choice inherited wholesale.
- [[Decision - Dense vs Mixture-of-Experts]] — Mixtral is the canonical data point for when sparse beats dense.
- [[Concept - MoE Inference and Expert Parallelism]] — why all-resident memory and batch profile dominate MoE serving cost.
- [[Concept - Cost Engineering for LLM Applications]] — the "47B-resident, 13B-compute" tradeoff in dollar terms.
- [[Concept - Tensor and Pipeline Parallelism]] — how the experts get sharded across GPUs at train and serve time.
- [[Gotchas - Mixture of Experts]] — the batch-dependence, token-dropping, and routing pitfalls Mixtral exhibits.
- [[Reference - Model Genealogy]] — Mixtral's place in the Mistral lineage and the open-MoE family tree.

## Sources
- Jiang et al. (2024) — *Mixtral of Experts.* Config, top-2-of-8 routing, and the "experts don't specialize by topic" finding.
- Jiang et al. (2023) — *Mistral 7B.* The dense base whose GQA/SwiGLU/RoPE/RMSNorm recipe Mixtral inherits.
- Fedus et al. (2021) — *Switch Transformer.* The top-1 predecessor Mixtral's top-2 routing contrasts with.
