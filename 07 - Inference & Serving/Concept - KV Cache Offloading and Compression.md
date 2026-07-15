---
tags: [concept, domain/inference-serving, level/frontier]
aliases: [KV offloading, StreamingLLM, H2O, SnapKV, KV eviction]
summary: "Tiering KV cache across HBM/CPU/NVMe, or evicting low-value tokens, once context no longer fits in GPU memory."
---
# Concept - KV Cache Offloading and Compression
> **One-paragraph hook:** The [[Concept - KV Cache]] grows linearly with both context length and batch, and eventually it simply doesn't fit in HBM — no matter how much has already been saved with GQA/MLA or [[Concept - KV Cache Quantization|quantization]]. From there there are exactly two moves, and they compose: move the bytes somewhere slower and fetch them back on demand (tiering), or decide some tokens' K,V simply aren't worth keeping and throw them away (eviction/compression). One is lossless and bandwidth-limited; the other is lossy and quality-limited — conflating which failure mode a given technique trades into is the most common mistake in long-context serving.

## The mechanism

**Tiering** moves cold KV blocks down a memory hierarchy — HBM → CPU RAM → local NVMe → a remote store — and prefetches them back ahead of when they're needed, overlapping the transfer against compute so decode doesn't stall waiting on it. FlexGen (Sheng et al. 2023) pioneered this for throughput-oriented single-GPU serving, offloading weights, KV, and activations together to make generation on consumer hardware viable at all. Production systems that followed narrowed the idea to KV specifically: LMCache, Mooncake's KV store (see [[Concept - Prefill-Decode Disaggregation]]), and vLLM's CPU offload path all move blocks off the hot path once they stop being actively attended to.

The bandwidth math is what gates whether tiering pays off at all: PCIe 4.0 delivers roughly 32 GB/s, against an H100's ~3 TB/s of HBM bandwidth — close to two orders of magnitude slower. Offloading only wins when the offloaded tokens are reused enough to amortize that transfer, or the workload is throughput-oriented and latency-tolerant rather than interactive; naive offload of a *live* sequence's near-term KV stalls every decode step on a slow fetch, turning a bandwidth-bound workload into a much slower one.

**Eviction** takes the opposite bet: rather than pay any transfer cost, decide up front that some tokens' K,V simply won't be needed again and drop them. **StreamingLLM** (Xiao et al. 2023) keeps a handful of leading "attention-sink" tokens (often just four) plus a sliding window of recent tokens, and nothing in between. The mechanism this exploits is a real property of trained attention: softmax must distribute probability mass across every position, and models learn to dump otherwise-unneeded mass onto the first few tokens — which are always present regardless of content — as a kind of no-op sink. Drop those sink tokens and the softmax normalization has nowhere to put that mass; attention distributions corrupt and the model degenerates. Because a rolling window changes each retained token's *relative* position every step, StreamingLLM must reassign [[Concept - Rotary Position Embeddings (RoPE)|RoPE]] angles for the window rather than keep original absolute positions — preserving original angles across a shifted window is a common, silent implementation bug.

**H2O** (Zhang et al. 2023) generalizes eviction with an importance signal: track each token's accumulated attention score across generation and evict the lowest "heavy hitters" once the cache exceeds budget, continuously, as generation proceeds. **SnapKV** (2024) applies the same idea to the *prompt* specifically, one-shot, before generation starts — it observes the attention pattern over a trailing window just before the first generated token and uses it to decide which prompt tokens are worth keeping, compressing a long prompt's KV footprint before decode even begins. Sliding-window attention (as in Mistral) is the architectural version of the same idea — baked into the model at training time rather than applied post-hoc at serving time.

| Method | What it drops | When applied | Lossy? |
|---|---|---|---|
| Tiering (FlexGen, LMCache, Mooncake, vLLM CPU offload) | Nothing — moves, doesn't drop | On demand, continuously | No |
| StreamingLLM | Everything but sink + window | Continuously as context grows | Yes |
| H2O | Low accumulated-attention-score tokens | Continuously during generation | Yes |
| SnapKV | Low-importance prompt tokens | Once, before generation | Yes |
| Sliding-window attention (Mistral) | Tokens outside the window | Architectural, always-on | Yes, by design |

## In practice

These levers compose rather than compete. Layering fp8 [[Concept - KV Cache Quantization|KV quantization]] on top of StreamingLLM's sink+window policy stacks a precision cut on top of a token-count cut — two orthogonal axes of the same memory budget. Under [[Concept - Prefill-Decode Disaggregation]], tiering interacts differently again: KV transferred to a decode pool may itself already be tiered rather than fully resident, adding a fetch-from-tier delay on top of the pool-to-pool transfer.

## Failure modes

- **Silent long-range retrieval loss.** Eviction is lossy by construction — a fact planted early in a long document becomes unrecoverable once its tokens are dropped — and perplexity often looks fine while needle-in-haystack-style retrieval quietly fails. Detection requires an explicit long-context retrieval eval, not perplexity; the same lesson [[Gotchas - Quantization Quality Loss|quantization's proxy-metric trap]] teaches on a different axis.
- **PCIe becomes the decode bottleneck under offload.** If fetched blocks aren't prefetched ahead of when they're needed, a decode step can stall on a PCIe round trip; against an H100 baseline of roughly 42 ms/token, an unhidden fetch is enough to double or triple effective decode latency.
- **Per-head vs. global token budgets change which method wins.** Evicting the same token index uniformly across all attention heads is simpler to implement but discards more information than a per-head budget, since different heads attend to different tokens as "important" — comparing two eviction methods without matching budget granularity isn't a fair comparison.
- **Eviction and tiering both fragment the underlying block allocator.** Continuously evicting individual tokens (H2O) or shuttling blocks between tiers (FlexGen-style offload) leaves the paged KV allocator's free list riddled with non-contiguous holes — the same production pathology chronicled in [[Lore - The KV Cache Fragmentation Crisis]]. Watch fragmentation ratio, not just aggregate free-byte count, or a cache that looks like it has room can still fail to satisfy a new allocation.

## The non-obvious

Attention sinks aren't a bug being worked around — they're an emergent property of how softmax attention gets trained, and StreamingLLM's real contribution was diagnostic as much as technical: explaining *why* keeping a specific handful of early tokens fixes what naive context truncation breaks. Every early "just drop old tokens" long-context hack that degenerated silently was running into this same phenomenon without a name for it.

The tiering-vs-eviction choice is really a decision about which failure mode you're willing to accept: tiering trades latency for correctness (slow but right), eviction trades correctness for latency (fast but occasionally wrong). Mature serving stacks increasingly run both as layered filters rather than picking one — eviction as the aggressive first cut for the easy majority of low-value tokens, tiering as the overflow valve for whatever eviction wasn't confident enough to drop outright.

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
