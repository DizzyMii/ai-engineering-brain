---
tags: [lore, domain/architectures, level/unicorn]
aliases: [transformer block evolution, LLaMA-standard block, how the transformer block converged]
summary: "How the 2017 Vaswani block became the 2024 LLaMA-standard decoder: pre-norm RMSNorm, RoPE, SwiGLU, GQA — and why each stuck."
---

# Lore - The Standardization of the Transformer Block

## What happened

If you download almost any open-weights LLM released in 2024–2025 and open the block definition, you see the same seven or eight decisions: **decoder-only, pre-norm, RMSNorm, RoPE, SwiGLU FFN at ~8/3·4·d, no bias terms, GQA.** It looks like a law of nature. It is not. It is the accreted residue of about seven years of swaps, each made by a specific person for a specific reason, several of which stuck for reasons closer to social physics than to proven superiority. Here is the sequence.

**The original (Vaswani et al. 2017, *Attention Is All You Need*).** The ancestral block, laid out in the [[Deep Dive - The Transformer]], is almost unrecognizable to a modern eye: an **encoder–decoder**, **post-norm** LayerNorm (`x = LayerNorm(x + Sublayer(x))`), **sinusoidal absolute** positional encodings added to the embeddings, a **ReLU** FFN at `4·d_model`, multi-head attention **with bias terms**, and dropout everywhere. It was designed for machine translation, and every one of those choices was later overturned.

**The decoder-only turn (GPT → GPT-2, Radford et al. 2018–2019).** OpenAI threw away the encoder and the cross-attention, keeping only the causal decoder — the architecture split explained in [[Concept - Encoder-Decoder and Decoder-Only Architectures]]. GPT-2 also quietly moved the **LayerNorm to the input of each sublayer (pre-norm)** and added a final norm before the output. This was the first load-bearing swap: pre-norm builds a clean additive gradient highway through the residual, so the model trains stably at depth without the delicate warmup post-norm demands. The mechanism and its residual-growth side effect are the subject of [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]]. Xiong et al. (2020) later gave the theory (pre-norm bounds gradient magnitude at initialization), but the practice was already universal by then — the labs had voted with their training runs.

**Noam Shazeer's outsized fingerprints.** A remarkable fraction of the modern block traces to a handful of papers by one author. **Multi-query attention** (Shazeer 2019, *Fast Transformer Decoding* — a single-author, four-page paper) collapsed the K/V heads to one to shrink the decode-time cache, seeding the whole MHA→MQA→GQA→MLA lineage now catalogued in [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]]. **GLU variants** (Shazeer 2020, *GLU Variants Improve Transformer*) gated the FFN — **SwiGLU** — for a consistent perplexity win, the sublayer now standard per [[Concept - Feed-Forward Networks and GLU Variants]]. That paper ends with the now-legendary line attributing the gains to "divine benevolence," a rare moment of honesty that the mechanism was not understood. And **RMSNorm** (Zhang & Sennrich 2019) dropped LayerNorm's mean-centering and bias for a cheaper scale-only normalizer — see [[Concept - RMSNorm and LayerNorm]] — which spread because it was ~10–20% cheaper per norm at no measured quality cost.

**The positional swap (RoFormer, Su et al. 2021).** **RoPE** replaced learned/sinusoidal absolute encodings by rotating Q and K by a position-dependent angle so the attention dot product depends only on *relative* position — the mechanism in [[Concept - Rotary Position Embeddings (RoPE)]]. It competed head-to-head with **ALiBi** (Press et al. 2021), which biased scores by a linear function of distance and had cleaner extrapolation. ALiBi won BLOOM and MPT; RoPE won essentially everyone else. The honest reading (folklore, weakly sourced): RoPE did not clearly *beat* ALiBi on merits — it won on **ecosystem momentum** once LLaMA shipped it, kernels optimized for it, and context-extension tricks (PI, NTK, YaRN) were all built on its frequency structure.

**LLaMA crystallizes the consensus (Touvron et al. 2023).** Meta's LLaMA 1 assembled the pieces into what is now *the* reference block: **pre-norm RMSNorm + RoPE + SwiGLU (with `d_ff ≈ 8/3 · 4 · d_model` to hold the parameter count constant against the extra gate matrix) + no bias terms.** LLaMA 2 added **GQA** (Ainslie et al. 2023) at the 34B/70B scale. Because the weights were open and the recipe was legible, nearly everyone copied it wholesale — Mistral, Qwen, Yi, and dozens more. The [[Reference - Model Genealogy]] is, from 2023 on, largely a family tree of LLaMA-block descendants. This is the moment the block *standardized*: not because it was proven optimal, but because a good-enough, fully-open reference removed the incentive to re-derive it.

**The counter-current (Gemma 2, 2024).** Then Google's Gemma 2 report quietly re-added ideas the field had pronounced dead: a **sandwich/post-norm hybrid** (norm before *and* after each sublayer), **logit soft-capping** (`cap · tanh(logits/cap)` on both attention and final logits), and **interleaved local/global attention**. Each was a stability or efficiency play, and each said, in effect: the standard is a local optimum, not a global one. The block is not finished converging — it just looks finished if you only read the LLaMA branch.

## The lesson

Architecture standardization is a **social and infrastructural process at least as much as a scientific one.** Three mechanisms did the work:

1. **The winning variant is the one with the best-supported reference implementation, not always the best variant.** RoPE over ALiBi, SwiGLU over GeGLU, GQA as the default — in each case the "winner" had a marginal or contested quality edge but a decisive ecosystem edge (open weights, fused kernels, downstream tooling). Once [[Deep Dive - FlashAttention]]-class kernels and vLLM/SGLang serving assumed RoPE + GQA, the cost of deviating rose and the standard locked in.
2. **Legibility compounds.** A recipe you can read off a weights file and reproduce in an afternoon gets copied a thousand times; a better recipe buried in a closed model gets copied zero times. LLaMA's openness, more than its quality, is why its block is the standard.
3. **"Settled" is a snapshot, not an endpoint.** Gemma 2 reviving post-norm and soft-capping shows the design space is still live; the convergence you see is survivorship bias over the branch everyone forked.

The practical takeaway for anyone porting or modifying models: treat every "standard" component as a swappable decision with a paper behind it, because someone will swap it back — and when they do (a Gemma soft-cap, a decoupled-RoPE MLA dim), your reference-matching will break exactly where the standard bent.

## Evidence status

- **Well-sourced (papers + model cards):** the *sequence* of changes and each component's origin — Vaswani 2017, GPT-2, Shazeer 2019/2020, Zhang & Sennrich 2019, RoFormer 2021, ALiBi 2021, LLaMA 2023, GQA 2023, Gemma 2 2024. These dates and attributions are solid.
- **Well-sourced folklore:** Shazeer's "divine benevolence" line (verbatim in the GLU Variants paper) and the general pattern that these swaps were empirical-first, theory-later.
- **Weakly-sourced folklore (labeled as such above):** the *why-each-stuck* attribution — specifically that RoPE and the LLaMA block won on ecosystem lock-in rather than proven superiority. This is the consensus reading among practitioners and is consistent with the timeline, but it is an interpretation, not a controlled result. No one ran the counterfactual where ALiBi shipped in LLaMA instead.

## Connections

- [[Deep Dive - The Transformer]] — the block whose evolution this narrates; read it for the mechanism, read this for the history.
- [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] — the pre-norm swap and Gemma 2's post-norm revival, the most consequential norm decisions in the story.
- [[Concept - Feed-Forward Networks and GLU Variants]] — the SwiGLU chapter and the 8/3 rescale that LLaMA standardized.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the positional swap that beat ALiBi on momentum; the mechanism behind the winner.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — the MQA→GQA lineage Shazeer started and LLaMA 2 mainstreamed.
- [[Concept - RMSNorm and LayerNorm]] — the norm that displaced LayerNorm on cost, a quiet but universal swap.
- [[Reference - Model Genealogy]] — from 2023 on, largely the family tree of LLaMA-block descendants this note explains.
- [[Concept - Encoder-Decoder and Decoder-Only Architectures]] — the decoder-only turn that opened the standardization story; where the encoder went.
- [[Deep Dive - FlashAttention]] — the kernel ecosystem whose optimization for RoPE + GQA is a concrete mechanism of the lock-in this note argues drove standardization.
- [[Lore - The OPT-175B Logbook]] — the cross-domain companion war story: what building one of these blocks at scale actually feels like from inside the run.

## Sources

- Vaswani et al. (2017) — *Attention Is All You Need.* The ancestral post-norm encoder–decoder block.
- Radford et al. (2019) — *Language Models are Unsupervised Multitask Learners* (GPT-2). The decoder-only + pre-norm turn.
- Shazeer (2019) — *Fast Transformer Decoding: One Write-Head is All You Need.* MQA, the KV-sharing lineage.
- Shazeer (2020) — *GLU Variants Improve Transformer.* SwiGLU, and the "divine benevolence" line.
- Zhang & Sennrich (2019) — *Root Mean Square Layer Normalization.* RMSNorm.
- Su et al. (2021) — *RoFormer: Enhanced Transformer with Rotary Position Embedding.* RoPE.
- Press et al. (2021) — *Train Short, Test Long: Attention with Linear Biases* (ALiBi). The road not taken.
- Touvron et al. (2023) — *LLaMA.* The recipe that crystallized the standard; Ainslie et al. (2023) *GQA* for the LLaMA-2 addition.
- Gemma Team (2024) — *Gemma 2 Technical Report.* Post-norm hybrid, logit soft-capping, local/global interleave — the counter-current.
