---
tags: [concept, domain/architectures, level/core]
aliases: [position embeddings, positional embeddings, PE]
summary: "The family of techniques for injecting order into permutation-equivariant self-attention: sinusoidal, learned, relative, ALiBi, NoPE, RoPE."
---
> **One-paragraph hook:** Self-attention on its own cannot tell "dog bites man" from "man bites dog" — it's a weighted average over a set, and sets have no order. Every transformer needs some mechanism to inject position, and the twenty years of research condensed into modern LLMs boils down to five real families of solution, of which [[Concept - Rotary Position Embeddings (RoPE)]] is the current default. This note is the map; RoPE gets its own deep treatment.

## The mechanism

Formally: $\text{Attn}(x_1, \ldots, x_n)$ built purely from $Q = xW_Q$, $K = xW_K$, $V = xW_V$ and softmax is *permutation-equivariant* — permute the input tokens and the outputs permute identically, with no signal about which position is which. Position must be injected somewhere: into the input embeddings, into the attention scores, or (as it turns out) obtained for free from the causal mask's asymmetry.

**Absolute sinusoidal** (Vaswani et al. 2017): add a fixed, non-learned vector to each token embedding before layer 1, built from sine/cosine at geometrically spaced frequencies:
$$PE_{(pos, 2i)} = \sin\!\left(\frac{pos}{10000^{2i/d}}\right), \quad PE_{(pos, 2i+1)} = \cos\!\left(\frac{pos}{10000^{2i/d}}\right)$$
No learned parameters, and in principle continuable to any length — in practice extrapolation is poor because the model never trained on those specific phase combinations.

**Learned absolute** (BERT, GPT-2): a trainable embedding table of shape `[max_len, d_model]` added to token embeddings. Simple and effective within range, but hard-capped: there is no row in the table for position `max_len + 1`, full stop.

**Relative position** (Shaw et al. 2018; T5's relative-position bias buckets; Transformer-XL): instead of encoding *where* a token is, bias the attention score for pair $(i,j)$ by a function of $i-j$. This generalizes better to unseen lengths since the model only ever reasons about offsets, not absolute coordinates.

**ALiBi** (Press et al. 2021): no embeddings at all — subtract a linear, head-specific penalty directly from the raw attention scores: $\text{score}_{ij} \mathrel{-}= m_h \cdot (i - j)$ for $i \ge j$, where $m_h$ is a fixed geometrically-spaced slope per head. Zero added parameters, and empirically strong length extrapolation — a model trained at 1k tokens generalizes to several times that. Used in BLOOM and MPT.

**NoPE**: add nothing. Kazemnejad et al. (2023) showed decoder-only causal models can learn position *implicitly* from the causal mask alone and, at smaller scales, extrapolate surprisingly well without any explicit scheme — because the causal mask itself already breaks permutation equivariance (the *set* of tokens visible at position $i$ has size $i$, which is itself positional information).

**RoPE** (own note): rotates $Q$ and $K$ by a position-dependent angle in 2D subspaces so their dot product becomes a function of relative position with no added parameters and no bias table. It won on composability with linear attention and its KV-cache-friendliness, and is the default in essentially every 2024–2026 open-weight LLM.

| Scheme | Params added | Extrapolation | Notes |
|---|---|---|---|
| Sinusoidal absolute | 0 | Poor in practice | Original Transformer, T5 encoder |
| Learned absolute | `max_len × d_model` | Hard cliff at cap | BERT, GPT-2 |
| Relative bias (T5/Shaw) | small bucket table | Better than absolute | T5, Transformer-XL |
| ALiBi | 0 | Strong | BLOOM, MPT |
| NoPE | 0 | Surprisingly good, small scale | Not yet mainstream production |
| RoPE | 0 | Good, extendable (PI/NTK/YaRN) | Dominant modern default |

## In practice

Sinusoidal absolute lived in the original [[Concept - Encoder-Decoder and Decoder-Only Architectures]] Transformer and T5's encoder. Learned absolute powered BERT and GPT-2, both capped at 512/1024 tokens with no graceful way past it — extending context meant retraining the position table from scratch. ALiBi's biggest deployment is BLOOM (176B) and MPT-7B/30B, both explicitly built for extrapolation without fine-tuning. RoPE has been the default since roughly 2022 across the LLaMA/GPT-NeoX/Mistral/Qwen lineage, and its own extension machinery (Position Interpolation, NTK-aware scaling, YaRN — see [[Concept - Context Length Extension]]) is now the standard path to pushing a trained model past its original context length.

## Failure modes

Absolute schemes fail as a hard cliff: perplexity is fine up to `max_len`, then the model either has no embedding row to use (learned) or is evaluating frequency combinations it never saw in training (sinusoidal), and quality falls off a cliff rather than degrading gracefully. Relative and ALiBi-style schemes degrade more gently — perplexity rises smoothly past the trained length rather than exploding. **Detection**: plot perplexity (or task accuracy) against position bucket; a sharp knee exactly at the trained maximum is the signature of absolute-position dependence, while a smooth, gradual rise indicates a relative-style scheme running out of runway rather than breaking outright. This same diagnostic is the starting point for diagnosing [[Concept - Context Rot]] in long-context evaluation.

## The non-obvious

NoPE's success is not magic — it works because the causal mask is *already* an asymmetric structure that leaks position for free (the attended set's cardinality at position $i$ literally encodes $i$). That's a genuinely useful mental model even if you never ship a NoPE model: it explains why decoder-only architectures got away with weaker positional schemes than encoder-only ones ever could, since a bidirectional [[Concept - Attention Mechanism]] stack has no equivalent free signal. Folklore, weakly sourced: despite NoPE "working" in controlled academic settings, essentially no frontier lab ships it as the sole positional signal at 100B+ scale — the risk of a subtle degradation only visible at scale isn't worth the parameter savings, so RoPE (or RoPE plus NoPE-inspired tweaks in a subset of layers) remains the safe default even where NoPE alone would technically suffice.

## Connections

- [[Concept - Rotary Position Embeddings (RoPE)]] — the dominant modern scheme; this note is the map, that one is the deep mechanism.
- [[Concept - Attention Mechanism]] — the permutation-equivariant operation that makes positional encoding mandatory in the first place.
- [[Concept - Context Length Extension]] — the post-hoc methods (PI, NTK, YaRN) that stretch a RoPE model past its trained length.
- [[Deep Dive - The Transformer]] — where positional encoding is injected into the overall forward path.
- [[Concept - Attention Sinks]] — a positional/attention-pattern artifact (fixed attention to early tokens) that interacts with how position is encoded near the sequence start.
- [[Concept - Context Rot]] — the long-context quality degradation whose diagnosis starts with exactly the perplexity-by-position plots described above.
- [[Concept - Vision Transformers]] — a domain where 2D positional encoding (not just 1D sequence position) has its own separate set of design choices.
- [[Concept - Encoder-Decoder and Decoder-Only Architectures]] — the architectural family (decoder-only) whose causal mask is what makes NoPE viable at all.

## Sources
- Vaswani et al. (2017) — "Attention Is All You Need": the original sinusoidal absolute encoding.
- Shaw, Uszkoreit, and Vaswani (2018) — relative position representations in self-attention.
- Raffel et al. (2020) — T5: relative-position bias buckets shared across layers.
- Press, Smith, and Lewis (2021) — ALiBi: linear-bias length extrapolation without added parameters.
- Kazemnejad et al. (2023) — "The Impact of Positional Encoding on Length Generalization": the NoPE finding.
