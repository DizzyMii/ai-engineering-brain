---
tags: [concept, domain/esoterica, level/advanced]
aliases: [attention sink, sink tokens, StreamingLLM sinks]
summary: "Attention heads dump 30-80% of their mass on token 0 regardless of content — softmax's escape valve, and the key to streaming inference."
---
> **One-paragraph hook:** Hook a logging callback into any decoder-only LLM's attention weights and profile a long prompt, and you'll see something that looks like a bug but isn't: a large fraction of heads route 30–80% of their attention mass onto the very first token — usually BOS — no matter what that token is or what the query is actually about. This is the **attention sink**, and once you understand why softmax forces it to exist, it stops looking like an artifact and starts looking like the load-bearing trick behind serving arbitrarily long streaming conversations on a fixed-size KV cache.

## The mechanism
[[Concept - Softmax]] guarantees attention weights over the visible key set sum to exactly 1 — there is no way for a head to output "attend to nothing." When a head's query doesn't semantically need any of the current context (a common situation on filler tokens, punctuation, or early in a sequence before there's anything useful to look up), softmax still has to place that probability mass *somewhere*. The first token is the natural resting place: under the causal mask it is visible from every later position (every query can see it), and because it never changes with the rest of the sequence, its key vector is stable across contexts — a fixed, always-available, low-information target the network can learn to route "no-op" attention onto without corrupting the value it actually cares about.

Formally, for query $q_i$ over keys $k_0 \ldots k_i$, $\alpha_{ij} = \mathrm{softmax}(q_i \cdot k_j / \sqrt{d})_j$. If none of $k_1 \ldots k_i$ scores highly relative to $k_0$, the normalization forces $\alpha_{i0}$ up regardless — a head with nowhere useful to look ends up looking at position 0 by construction, not by learned relevance.

Xiao et al. 2023, "Efficient Streaming Language Models with Attention Sinks" (StreamingLLM), turned this observation into a serving technique. Instead of a plain sliding-window [[Concept - KV Cache]] that evicts the oldest tokens as new ones arrive, they keep the KV of the **first ~4 tokens permanently resident** as a fixed "sink cache," alongside a sliding window of the most recent tokens:

```
KV cache layout under StreamingLLM:
[ sink: tokens 0-3 (never evicted) ][ ...evicted middle... ][ sliding window: last N tokens ]
```

This holds perplexity flat over 4M+ tokens of streamed generation. The critical ablation is what happens if you evict the sink tokens along with everything else in a naive sliding window: perplexity explodes almost immediately once the window first slides past position 0 — not a gradual degradation, a cliff. The heads that were dumping mass into the sink have nowhere left to put it, and the softmax normalization forces that mass onto whatever tokens remain, corrupting attention everywhere.

Because the sink is a structural property of softmax rather than a property of position-0's semantics specifically, you can also train it in deliberately: give the model a dedicated, content-free sink token from the start, or add a per-head learnable "sink logit" that participates in the softmax denominator without ever being a value the model reads from — a trained version of the same "give the head somewhere to dump nothing" idea, related to the [[Snippet - Softmax-Off-By-One (Quiet Attention)]] technique of adding a constant to the softmax denominator so a head can output near-zero total attention.

Attention sinks are tightly coupled to a second phenomenon: the sink positions coincide with hidden-state dimensions carrying enormous magnitude — see [[Concept - Massive Activations and Outlier Features]]. These aren't two separate curiosities; they're two observable faces of the same mechanism — the network built itself a fixed, high-magnitude, always-attended bias channel, and depending on whether you're looking at the attention weights or the residual-stream activations, you call it a "sink" or an "outlier."

There's a vision analogue: Darcet et al. 2024, "Vision Transformers Need Registers," found that ViTs spontaneously repurpose a handful of low-information patch tokens as high-norm dumping grounds during training — the same softmax-driven need for a no-op destination, but in an architecture with no fixed "token 0." Their fix is to give the model explicit, purpose-built register tokens up front, cleaning up the feature maps and removing the artifact tokens from the meaningful patch grid entirely.

## In practice
Production streaming and long-context serving stacks that manage the [[Concept - KV Cache]] with eviction policies must special-case the sink: a naive recency-based eviction heuristic ("drop the oldest KV entries first") will eventually drop the sink and tank quality, exactly as StreamingLLM's ablation shows. Systems that support [[Concept - RoPE Extrapolation and Context Extension]] have a second failure surface here — extension methods that rescale or reinterpret early positional encodings can make the sink token's positional signature drift, which breaks the mechanism from the position-embedding side even if the KV entry itself is never evicted. And any [[Concept - Post-Training Quantization Formats]] pipeline that quantizes activations or KV entries uniformly, without excluding the sink token's outlier channels, will blow up quantization error exactly where the model is most sensitive to it.

## Failure modes
- **Sliding-window KV cache with no sink exemption.** Symptom: perplexity is fine until the window first slides past position 0, then spikes catastrophically. Cause: heads that relied on dumping mass into the sink have no valid target left. Fix: pin the first few tokens' KV entries permanently, per StreamingLLM.
- **Uniform quantization touching the sink's outlier channels.** Symptom: quality degrades sharply on long sequences specifically, not on short ones. Detection: compare per-token quantization error; the sink token and its outlier dims will show error orders of magnitude above the rest. Fix: mixed-precision or protected-channel quantization schemes that carve out the sink/outlier dimensions.
- **Context-extension methods that perturb early-position encodings.** Symptom: long-context quality regresses after applying a RoPE rescaling method, even though short-context quality is unaffected. Cause: the sink token's positional signature is no longer the stable anchor the model learned to rely on.
- **Attention entropy collapse near sink-dependent heads.** A head that loses access to its sink and is forced to over-concentrate elsewhere in the sequence is a special case of the broader instability tracked under [[Concept - Attention Entropy Collapse]].

## The non-obvious
The sink is not a wasted computation to be optimized away — it's closer to a bias term the network needs, structurally, because softmax cannot express "attend to nothing." This reframes two things practitioners often get backwards: first, "smart" eviction or compression heuristics that treat the earliest tokens as the least valuable (because they're stalest) are optimizing against a mechanism they don't know exists; second, the sink and the massive-activation outlier are the same underlying object seen from two different instruments (attention weights vs. residual-stream magnitude), so any fix that addresses one in isolation — quantizing outliers away, say, without also protecting the corresponding attention pattern — tends to just move the failure rather than remove it.

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
