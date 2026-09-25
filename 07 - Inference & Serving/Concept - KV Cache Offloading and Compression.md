---
tags: [concept, domain/inference-serving, level/frontier]
aliases: [KV offloading, StreamingLLM, H2O, SnapKV, KV eviction]
summary: "Tiering KV cache across HBM/CPU/NVMe, or evicting low-value tokens, once context no longer fits in GPU memory."
---
# Concept - KV Cache Offloading and Compression
> **One-paragraph hook:** The [[Concept - KV Cache]] grows linearly with both context length and batch, and eventually it doesn't fit in HBM, however much GQA/MLA or [[Concept - KV Cache Quantization|quantization]] has already saved. At that point there are exactly two moves, and they compose. You can move the bytes somewhere slower and fetch them back on demand (tiering), or decide some tokens' K,V aren't worth keeping and throw them away (eviction/compression). Tiering is lossless and bandwidth-limited; eviction is lossy and quality-limited. Mixing up which failure mode a given technique trades into is the most common mistake in long-context serving.

## The mechanism

**Tiering** moves cold KV blocks down a memory hierarchy (HBM → CPU RAM → local NVMe → a remote store) and prefetches them back before they're needed, overlapping the transfer with compute so decode doesn't stall on it. FlexGen (Sheng et al. 2023) pioneered this for throughput-oriented single-GPU serving. It offloaded weights, KV and activations together so generation on consumer hardware was viable at all. Production systems narrowed this to KV: LMCache, Mooncake's KV store (see [[Concept - Prefill-Decode Disaggregation]]) and vLLM's CPU offload path all move blocks off the hot path once they stop being actively attended to.

Bandwidth decides whether tiering pays off. PCIe 4.0 delivers roughly 32 GB/s; an H100 has ~3 TB/s of HBM bandwidth, close to two orders of magnitude more. Offloading wins only when the offloaded tokens get reused enough to amortize the transfer, or when the workload is throughput-oriented and latency-tolerant instead of interactive. Naively offloading a *live* sequence's near-term KV stalls every decode step on a slow fetch, making a bandwidth-bound workload much slower.

**Eviction** makes the opposite bet. It pays no transfer cost and instead decides up front that some tokens' K,V won't be needed again, then drops them. **StreamingLLM** (Xiao et al. 2023) keeps a handful of leading "attention-sink" tokens (often just four) plus a sliding window of recent tokens, and nothing in between. It exploits a real property of trained attention: softmax has to distribute probability mass across every position, and models learn to dump otherwise-unneeded mass onto the first few tokens, which are always present whatever the content, as a kind of no-op sink. Drop the sinks and the softmax normalization has nowhere to put that mass; attention distributions corrupt and the model degenerates. A rolling window also changes each retained token's *relative* position every step, so StreamingLLM has to reassign [[Concept - Rotary Position Embeddings (RoPE)|RoPE]] angles for the window instead of keeping the original absolute positions. Keeping the original angles is a common, silent bug.

**H2O** (Zhang et al. 2023) adds an importance signal. It tracks each token's accumulated attention score during generation and, whenever the cache exceeds budget, evicts the lowest-scoring tokens (keeping the "heavy hitters"). **SnapKV** (2024) applies the idea to the *prompt*, one-shot, before generation starts. It looks at the attention pattern over a trailing window just before the first generated token and uses it to pick which prompt tokens to keep, shrinking a long prompt's KV footprint before decode begins. Sliding-window attention (as in Mistral) is the architectural version: baked into the model at training time instead of applied post-hoc at serving time.

| Method | What it drops | When applied | Lossy? |
|---|---|---|---|
| Tiering (FlexGen, LMCache, Mooncake, vLLM CPU offload) | Nothing — moves, doesn't drop | On demand, continuously | No |
| StreamingLLM | Everything but sink + window | Continuously as context grows | Yes |
| H2O | Low accumulated-attention-score tokens | Continuously during generation | Yes |
| SnapKV | Low-importance prompt tokens | Once, before generation | Yes |
| Sliding-window attention (Mistral) | Tokens outside the window | Architectural, always-on | Yes, by design |

## In practice

These levers compose. Putting fp8 [[Concept - KV Cache Quantization|KV quantization]] on top of StreamingLLM's sink+window policy stacks a precision cut on a token-count cut, two orthogonal axes of the same memory budget. Under [[Concept - Prefill-Decode Disaggregation]], tiering behaves differently again: KV sent to a decode pool may itself be tiered and not fully resident, which adds a fetch-from-tier delay on top of the pool-to-pool transfer.

## Failure modes

- **Silent long-range retrieval loss.** Eviction is lossy by construction. A fact planted early in a long document is unrecoverable once its tokens are dropped, and perplexity often looks fine while needle-in-haystack-style retrieval fails. Only an explicit long-context retrieval eval catches it. [[Gotchas - Quantization Quality Loss|Quantization's proxy-metric trap]] teaches the same lesson on a different axis.
- **PCIe becomes the decode bottleneck under offload.** If fetched blocks aren't prefetched ahead of use, a decode step can stall on a PCIe round trip. Against an H100 baseline of roughly 42 ms/token, an unhidden fetch is enough to double or triple effective decode latency.
- **Per-head vs. global token budgets change which method wins.** Evicting the same token index across all attention heads is simpler to implement but discards more information than a per-head budget, since different heads treat different tokens as "important." Comparing two eviction methods at different budget granularity isn't a fair comparison.
- **Eviction and tiering both fragment the block allocator.** Continuously evicting individual tokens (H2O) or shuttling blocks between tiers (FlexGen-style offload) leaves the paged KV allocator's free list full of non-contiguous holes, the same production pathology chronicled in [[Lore - The KV Cache Fragmentation Crisis]]. Watch the fragmentation ratio as well as the aggregate free-byte count, or a cache that looks like it has room can still fail a new allocation.

## The non-obvious

Attention sinks aren't a bug to work around. They emerge from how softmax attention gets trained, and StreamingLLM's contribution was as much diagnostic as technical: it explained *why* keeping a specific handful of early tokens fixes what naive context truncation breaks. Every early "just drop old tokens" hack that degenerated silently was hitting this without a name for it.

Choosing between tiering and eviction means choosing which failure mode you'll accept. Tiering trades latency for correctness (slow but right). Eviction trades correctness for latency (fast but occasionally wrong). Mature serving stacks increasingly run both as layered filters: eviction as the aggressive first cut for the easy majority of low-value tokens, tiering as the overflow valve for whatever eviction wasn't confident enough to drop.

## Connections
- [[Concept - KV Cache]] — the base data structure and memory formula this note manages once it stops fitting in HBM.
- [[Concept - KV Cache Quantization]] — the orthogonal, composable lever (fewer bytes per token) versus this note's levers (fewer tokens kept, or bytes moved elsewhere).
- [[Concept - Attention Sinks]] — cross-domain (18): the softmax-normalization phenomenon that makes StreamingLLM's sink-token retention necessary rather than an arbitrary heuristic.
- [[Concept - Prefill-Decode Disaggregation]] — the sibling frontier technique that also moves KV cache across a network link, but once per request rather than continuously as a standing capacity strategy.
- [[Concept - Automatic Prefix Caching]] — a cache-hit-driven reason to *keep* KV around across requests, in direct tension with eviction's bias toward dropping it; the two policies must be tuned together, not independently.
- [[Concept - GPU Memory Hierarchy]] — cross-domain (08): the HBM/PCIe/NVMe bandwidth ladder this note's tiering strategy climbs down.
- [[Concept - Rotary Position Embeddings (RoPE)]] — cross-domain (03): sliding-window eviction must reassign relative positions for the retained window, a RoPE-specific implementation detail that's easy to get wrong.
- [[Concept - Attention Mechanism]] — the softmax normalization property underlying why attention sinks exist and why naive truncation breaks the model.
- [[Lore - The KV Cache Fragmentation Crisis]] — the production war story behind why continuous eviction/tiering churn on the paged KV allocator is a known failure class, not a hypothetical.

## Sources
- Xiao et al. (2023) — *Efficient Streaming Language Models with Attention Sinks* (StreamingLLM). Identifies the attention-sink phenomenon and the sink+window eviction policy.
- Zhang et al. (2023) — *H2O: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models*. Accumulated-attention-score eviction during generation.
- Sheng et al. (2023) — *FlexGen: High-Throughput Generative Inference of Large Language Models with a Single GPU*. Pioneers HBM/CPU/NVMe tiering for throughput-oriented serving.
- Li et al. (2024) — *SnapKV: LLM Knows What You Are Looking For Before Generation*. Compresses prompt KV using the attention pattern from a trailing observation window.
