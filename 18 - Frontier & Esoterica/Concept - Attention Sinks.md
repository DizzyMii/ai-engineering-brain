---
tags: [concept, domain/esoterica, level/advanced]
aliases: [attention sink, sink tokens, StreamingLLM sinks]
summary: "Attention heads dump 30-80% of their mass on token 0 regardless of content — softmax's escape valve, and the key to streaming inference."
---
> **One-paragraph hook:** Log the attention weights of any decoder-only LLM on a long prompt and you'll see what looks like a bug. Many heads put 30–80% of their attention mass on the first token (usually BOS), whatever that token is and whatever the query is about. That's the **attention sink**. Once you see why softmax forces it to exist, it stops looking like an artifact. It's the trick that lets you serve arbitrarily long streaming conversations on a fixed-size KV cache.

## The mechanism
[[Concept - Softmax]] makes attention weights over the visible keys sum to exactly 1, so a head has no way to say "attend to nothing." When a query doesn't need anything in the current context (common on filler tokens, punctuation, or early in a sequence before there's anything to look up), the probability mass still has to land somewhere. The first token is the obvious place. Under the causal mask every later query can see it, and since it never changes with the rest of the sequence, its key vector is stable across contexts. The network can learn to park "no-op" attention there without corrupting the values it does care about.

Formally, for query $q_i$ over keys $k_0 \ldots k_i$, $\alpha_{ij} = \mathrm{softmax}(q_i \cdot k_j / \sqrt{d})_j$. If none of $k_1 \ldots k_i$ scores well against $k_0$, normalization pushes $\alpha_{i0}$ up anyway. A head with nowhere useful to look ends up on position 0 by construction, with no learned relevance involved.

Xiao et al. 2023, "Efficient Streaming Language Models with Attention Sinks" (StreamingLLM), made this a serving technique. A plain sliding-window [[Concept - KV Cache]] evicts the oldest tokens as new ones arrive. StreamingLLM instead keeps the KV of the **first ~4 tokens permanently resident** as a fixed "sink cache," next to a sliding window of recent tokens:

```
KV cache layout under StreamingLLM:
[ sink: tokens 0-3 (never evicted) ][ ...evicted middle... ][ sliding window: last N tokens ]
```

Perplexity stays flat over 4M+ tokens of streamed generation. The ablation that matters: evict the sink tokens along with everything else and perplexity explodes as soon as the window first slides past position 0. It's a cliff, with no gradual slope before it. The heads that were dumping mass into the sink lose their target, softmax spreads that mass over whatever tokens remain, and attention gets corrupted everywhere.

The sink comes from softmax itself, and nothing about position 0's meaning is required, so you can also train one in on purpose. Give the model a dedicated content-free sink token from the start, or add a per-head learnable "sink logit" that sits in the softmax denominator but is never a value the model reads. Same idea: a place for the head to dump nothing. It's related to [[Snippet - Softmax-Off-By-One (Quiet Attention)]], which adds a constant to the softmax denominator so a head can output near-zero total attention.

Sink positions also line up with hidden-state dimensions of enormous magnitude (see [[Concept - Massive Activations and Outlier Features]]). These are one mechanism seen two ways. The network built itself a fixed, high-magnitude, always-attended bias channel; in the attention weights you call it a "sink," in the residual-stream activations an "outlier."

ViTs show the same thing. Darcet et al. 2024, "Vision Transformers Need Registers," found that ViTs repurpose a handful of low-information patch tokens as high-norm dumping grounds during training. Same softmax need for a no-op destination, in an architecture with no fixed "token 0." Their fix is explicit register tokens added up front, which cleans up the feature maps and takes the artifact tokens out of the meaningful patch grid.

## In practice
Any streaming or long-context stack that evicts from the [[Concept - KV Cache]] has to special-case the sink. Plain recency eviction ("drop the oldest entries first") will eventually drop it and tank quality, as the StreamingLLM ablation shows. Stacks supporting [[Concept - RoPE Extrapolation and Context Extension]] have a second way to break it: methods that rescale or reinterpret early positional encodings can shift the sink token's positional signature, so the mechanism fails from the position side even if the KV entry is never evicted. And a [[Concept - Post-Training Quantization Formats]] pipeline that quantizes activations or KV entries uniformly, without excluding the sink's outlier channels, puts its largest error right where the model is most sensitive.

## Failure modes
- **Sliding-window KV cache with no sink exemption.** Perplexity is fine until the window first slides past position 0, then spikes catastrophically. Heads that dumped mass into the sink have no valid target left. Fix: pin the first few tokens' KV entries permanently, as StreamingLLM does.
- **Uniform quantization over the sink's outlier channels.** Quality drops sharply on long sequences but not short ones. To detect it, compare per-token quantization error: the sink token and its outlier dims show error orders of magnitude above the rest. Fix: mixed-precision or protected-channel schemes that carve those dimensions out.
- **Context extension that perturbs early-position encodings.** Long-context quality regresses after a RoPE rescaling method while short-context quality is unaffected. The sink's positional signature is no longer the stable anchor the model learned.
- **Attention entropy collapse near sink-dependent heads.** A head that loses its sink and has to over-concentrate elsewhere is a special case of the instability covered in [[Concept - Attention Entropy Collapse]].

## The non-obvious
Don't treat the sink as wasted compute to optimize away. It behaves like a bias term the network needs, because softmax can't express "attend to nothing." Two consequences people get backwards. Eviction or compression heuristics that rank the earliest tokens as least valuable (they're the stalest) are fighting a mechanism they don't know about. And since the sink and the massive-activation outlier are one object measured by two instruments (attention weights vs. residual-stream magnitude), a fix aimed at one alone, say quantizing the outliers away without protecting the matching attention pattern, tends to move the failure somewhere else instead of removing it.

## Connections
- [[Concept - Massive Activations and Outlier Features]] — the sink and the outlier activation are two views of one implicit-bias mechanism; fixes that ignore one while patching the other tend to fail.
- [[Snippet - Softmax-Off-By-One (Quiet Attention)]] — a direct engineering response to the same root cause: giving softmax a legitimate way to express "attend to nothing" instead of forcing the mass onto a real token.
- [[Concept - KV Cache]] — the sink is precisely the exception that eviction and compression policies for the cache must carve out to avoid catastrophic quality loss.
- [[Concept - Attention Mechanism]] — the sink is a direct, unavoidable consequence of the softmax normalization inside standard scaled dot-product attention.
- [[Concept - Softmax]] — the root cause: a normalization that must sum to 1 has no way to express "attend to nothing," so it needs somewhere stable to dump unwanted mass.
- [[Concept - Post-Training Quantization Formats]] — quantization schemes that don't protect the sink token and its outlier channels see disproportionate quality loss there.
- [[Concept - RoPE Extrapolation and Context Extension]] — extension methods that alter early positional encodings can make the sink drift, breaking streaming inference that depends on it staying fixed.
- [[Concept - Attention Entropy Collapse]] — heads destabilized by losing their sink target are a specific instance of the broader entropy-collapse failure mode tracked there.

## Sources
- Xiao, Tian, Chen, Han & Lewis (2023) — "Efficient Streaming Language Models with Attention Sinks." Introduces the sink-cache-plus-sliding-window StreamingLLM technique and the eviction ablation showing perplexity explodes without it.
- Darcet, Oquab, Mairal & Bojanowski (2024) — "Vision Transformers Need Registers." Documents the same softmax-driven high-norm-artifact-token phenomenon in ViTs and fixes it with explicit register tokens.
