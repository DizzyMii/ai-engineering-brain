---
tags: [concept, domain/architectures, level/core]
aliases: [position embeddings, positional embeddings, PE]
summary: "The family of techniques for injecting order into permutation-equivariant self-attention: sinusoidal, learned, relative, ALiBi, NoPE, RoPE."
---
> **One-paragraph hook:** Self-attention by itself can't tell "dog bites man" from "man bites dog". It's a weighted average over a set, and sets have no order. Every transformer needs some way to inject position, and twenty years of research condensed into modern LLMs comes down to five real families of solution. [[Concept - Rotary Position Embeddings (RoPE)]] is the current default and has its own note; this one is the map.

## The mechanism

Formally, $\text{Attn}(x_1, \ldots, x_n)$ built only from $Q = xW_Q$, $K = xW_K$, $V = xW_V$ and softmax is *permutation-equivariant*. Permute the input tokens and the outputs permute the same way, with no signal about which position is which. Position has to come in somewhere: through the input embeddings, through the attention scores, or (as it turns out) for free from the asymmetry of the causal mask.

**Absolute sinusoidal** (Vaswani et al. 2017) adds a fixed, non-learned vector to each token embedding before layer 1, built from sine/cosine at geometrically spaced frequencies:
$$PE_{(pos, 2i)} = \sin\!\left(\frac{pos}{10000^{2i/d}}\right), \quad PE_{(pos, 2i+1)} = \cos\!\left(\frac{pos}{10000^{2i/d}}\right)$$
It has no learned parameters and could in principle continue to any length. In practice it extrapolates poorly, because the model never trained on those particular phase combinations.

**Learned absolute** (BERT, GPT-2) is a trainable `[max_len, d_model]` embedding table added to token embeddings. Simple and effective within range, but hard-capped: there's no row for position `max_len + 1`, full stop.

**Relative position** (Shaw et al. 2018; T5's relative-position bias buckets; Transformer-XL) skips encoding *where* a token is. It biases the attention score for pair $(i,j)$ by a function of $i-j$. Since the model only ever reasons about offsets, never absolute coordinates, it generalizes better to unseen lengths.

**ALiBi** (Press et al. 2021) uses no embeddings. It subtracts a linear, head-specific penalty straight from the raw attention scores: $\text{score}_{ij} \mathrel{-}= m_h \cdot (i - j)$ for $i \ge j$, where $m_h$ is a fixed, geometrically spaced slope per head. It adds zero parameters and extrapolates well empirically; a model trained at 1k tokens generalizes to several times that. BLOOM and MPT use it.

**NoPE** adds nothing. Kazemnejad et al. (2023) showed that decoder-only causal models can learn position *implicitly* from the causal mask and, at smaller scales, extrapolate surprisingly well with no explicit scheme. The causal mask already breaks permutation equivariance: the *set* of tokens visible at position $i$ has size $i$, and that size is positional information.

**RoPE** (own note) rotates $Q$ and $K$ by a position-dependent angle in 2D subspaces, so their dot product becomes a function of relative position with no added parameters and no bias table. It won on composability with linear attention and on KV-cache friendliness, and it's the default in essentially every 2024–2026 open-weight LLM.

| Scheme | Params added | Extrapolation | Notes |
|---|---|---|---|
| Sinusoidal absolute | 0 | Poor in practice | Original Transformer, T5 encoder |
| Learned absolute | `max_len × d_model` | Hard cliff at cap | BERT, GPT-2 |
| Relative bias (T5/Shaw) | small bucket table | Better than absolute | T5, Transformer-XL |
| ALiBi | 0 | Strong | BLOOM, MPT |
| NoPE | 0 | Surprisingly good, small scale | Not yet mainstream production |
| RoPE | 0 | Good, extendable (PI/NTK/YaRN) | Dominant modern default |

## In practice

Sinusoidal absolute appeared in the original [[Concept - Encoder-Decoder and Decoder-Only Architectures]] Transformer and in T5's encoder. Learned absolute powered BERT and GPT-2, capped at 512/1024 tokens with no graceful way past the cap; more context meant retraining the position table from scratch. ALiBi's biggest deployments are BLOOM (176B) and MPT-7B/30B, both built explicitly to extrapolate without fine-tuning. RoPE has been the default since roughly 2022 across the LLaMA/GPT-NeoX/Mistral/Qwen lineage. Its extension machinery (Position Interpolation, NTK-aware scaling, YaRN; see [[Concept - Context Length Extension]]) is now the standard way to push a trained model past its original context length.

## Failure modes

Absolute schemes fail at a hard cliff. Perplexity is fine up to `max_len`. After that the model either has no embedding row (learned) or is evaluating frequency combinations it never saw in training (sinusoidal), and quality drops sharply instead of degrading gracefully. Relative and ALiBi-style schemes degrade more gently, with perplexity rising smoothly past the trained length.

**Detection**: plot perplexity (or task accuracy) against position bucket. A sharp knee at the trained maximum is the signature of absolute-position dependence. A smooth, gradual rise means a relative-style scheme running out of runway, not breaking outright. The same plot is where diagnosing [[Concept - Context Rot]] in long-context evaluation starts.

## The non-obvious

NoPE isn't magic. It works because the causal mask is *already* asymmetric and leaks position for free: the size of the attended set at position $i$ is literally $i$. That mental model is useful even if you never ship a NoPE model. It explains why decoder-only architectures got away with weaker positional schemes than encoder-only ones could, since a bidirectional [[Concept - Attention Mechanism]] stack has no equivalent free signal.

Folklore, weakly sourced: NoPE "works" in controlled academic settings, yet essentially no frontier lab ships it as the sole positional signal at 100B+ scale. A subtle degradation that only appears at scale isn't worth the parameter savings. So RoPE (or RoPE plus NoPE-inspired tweaks in a subset of layers) stays the safe default, even where NoPE alone would technically suffice.

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
