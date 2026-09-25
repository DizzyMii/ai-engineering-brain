---
tags: [concept, domain/prompting-context, level/core]
aliases: [context caching, cache_control]
summary: "Reusing the KV cache for a repeated prompt prefix skips redundant prefill compute, cutting cached-token cost up to 90%."
---
> **One-paragraph hook:** Any LLM call that shares a prefix with an earlier one (same system prompt, same few-shot block, same long document) pays by default to recompute the same attention keys and values from scratch. Prompt caching stores the computed [[Concept - KV Cache]] for a token prefix, so a later request with that exact prefix skips the expensive prefill and pays only for the new suffix. The shared part of the prompt goes from a recurring per-call compute cost to a near-fixed-cost lookup.

## The mechanism

LLM inference has two phases. Prefill is one forward pass over every prompt token to build its key/value entries. Decode generates output tokens one at a time, attending back over the accumulated KV. Prefill cost grows with input length: for a dense transformer it's roughly $2 \times N \times P$ FLOPs for $N$ prompt tokens and $P$ parameters, all spent before the first output token. Causal attention means the K/V entries for token $i$ depend only on tokens $0..i$, so a byte-identical prefix gives byte-identical KV values on every request. Prompt caching persists the KV cache server-side and matches each incoming prompt against the cached prefix token by token, starting at position 0. For the matched span prefill is skipped entirely, and only the new suffix gets prefilled:

```
Request 1:  [ system prompt ][ few-shot block ][ user turn A ]
             \_______________ written to cache ______________/

Request 2:  [ system prompt ][ few-shot block ][ user turn B ]
             \___ cache HIT: KV reused, skipped ___/^only this new suffix is prefilled
```

That token-level, position-0 matching is also the mechanism's biggest constraint, because matching stops at the first divergence. A timestamp, a request ID, or a JSON object serialized with unstable key order anywhere before the reusable content makes everything after it miss the cache, even when the expensive part (a long system prompt, a big document) is byte-identical to last time. So cache-aware prompts put static content first and volatile content last. That's backwards from how people naturally write prompts: context, then instructions, then the ever-changing user question.

## In practice

Pricing and TTL vary a lot by provider (as of 2026); [[Reference - Prompt Caching Across Providers]] has the full table. Anthropic's model shows the shape of the economics. Explicit `cache_control` breakpoints (up to 4 per request), a 5-minute default TTL with a paid 1-hour option, writes at roughly 1.25x the base input price, reads at roughly 0.1x base (a 90% discount on a hit), and a minimum cacheable prefix of about 1,024 tokens for Sonnet/Opus (~2,048 for Haiku). OpenAI caches automatically with no breakpoint API, above a 1,024-token threshold in 128-token increments, at roughly a 50% read discount with no write premium and a shorter ~5-10 minute idle-eviction window.

The write premium means caching is an investment that needs reuse to pay off, not a free speedup. With Anthropic's numbers, writing a cached prefix costs 1.25x and each later read 0.1x, against 1.0x per call with no caching. For $n$ calls sharing a prefix, caching costs $1.25 + 0.1(n-1)$ (in units of the base price) versus $n$ without it. Solving $1.25 + 0.1(n-1) = n$ puts break-even just above $n \approx 1.3$. A *second* use of the prefix already makes caching cheaper, and by three or four reuses the discount is large. A prefix used exactly once still costs 25% more than not caching. You're betting on reuse within the TTL.

So prompt caching is the natural place for anything static and reused: a long [[Concept - System Prompts]] block, few-shot exemplar sets, RAG document prefixes injected before every query in a session, and multi-turn conversations that re-send the whole transcript each turn. Self-hosted inference servers already do the same thing for free. [[Concept - Automatic Prefix Caching]] in engines like vLLM and SGLang caches shared KV prefixes across concurrent requests as a standard part of serving, built on the same paged-KV memory management as [[Concept - Continuous Batching]]. The mechanism is identical; a managed API just meters and bills it. What a provider's cache keeps once total demand exceeds GPU memory comes down to the tiering and eviction tradeoffs in [[Concept - KV Cache Offloading and Compression]]. Writing a prefix doesn't guarantee it survives. It competes with every other tenant's cache for the same finite HBM.

## Failure modes

- **Cache-busting from nondeterministic prefix content.** A timestamp, UUID or unstable JSON key order anywhere before the reusable block invalidates the cache for everything after it, and cost silently goes back to full price with no error. Detection: watch cache-hit token counts in the API response (Anthropic reports `cache_creation_input_tokens` and `cache_read_input_tokens` separately) and alert if the read/write ratio collapses.
- **TTL expiry between bursty calls.** With a 5-minute default TTL, any longer gap between calls on the same session silently pays full prefill again, unless you send keep-alive requests or buy a longer TTL tier.
- **Too many breakpoints.** Providers that need explicit `cache_control` markers cap how many one request can set (4 for Anthropic). Content past the cap gets no cache boundary of its own and may not cache as intended.
- **Paying for writes nobody reads.** Caching single-use content (a one-off document, a unique per-user prompt with no repeat traffic) is a plain net loss. You pay the write premium and no reads amortize it.

## The non-obvious

Almost everyone misses the write premium on first read. Turning on prompt caching is a bet that a prefix gets reused enough within the TTL to earn back the 1.25x write cost. Blanket-enabling `cache_control` on every request without checking reuse can *raise* spend. Measure prefix reuse rate before you flip the switch.

The second trap is regional. Caches are scoped per org and, in practice, per region. They're never shared across accounts and aren't guaranteed to be shared across a provider's own data centers. A multi-region deployment that round-robins requests across regions can defeat its own cache purely through routing, paying full prefill on every call despite byte-identical prefixes. You won't see it unless you track cache-hit rate per region.

## Connections
- [[Concept - KV Cache]] — the exact data structure prompt caching persists and reuses across requests.
- [[Concept - Continuous Batching]] — the serving-layer infrastructure that prefix caching is typically built alongside in production engines.
- [[Concept - Cost Engineering for LLM Applications]] — prompt caching is one of the highest-leverage cost levers available, but only when reuse patterns justify the write premium.
- [[Concept - Semantic Caching]] — the fuzzy-match sibling technique: semantic caching reuses whole responses for similar-but-not-identical queries, where prompt caching requires an exact token prefix.
- [[Reference - Prompt Caching Across Providers]] — the full provider-by-provider pricing and TTL comparison this note's economics are drawn from.
- [[Concept - Context Engineering]] — cache-friendly prefix ordering (static-first, dynamic-last) is one of the concrete curation levers that discipline requires.
- [[Concept - System Prompts]] — the single most common thing worth caching, since it is identical across nearly every call.
- [[Concept - Prompt Engineering]] — prompt caching is a pure cost/latency optimization layered on top of a prompt's content, not a change to what the prompt says.
- [[Concept - Automatic Prefix Caching]] — the self-hosted, unbilled analog of the same mechanism inside open-source inference engines.
- [[Concept - KV Cache Offloading and Compression]] — the deeper mechanism deciding which cached prefixes actually survive once aggregate demand exceeds available HBM, one level below the provider-facing pricing/TTL abstraction this note covers.

## Sources
- Kwon et al. (2023) — "Efficient Memory Management for Large Language Model Serving with PagedAttention" (the vLLM paper). Introduces the paged KV-cache memory management that automatic prefix caching is built on.
- Anthropic (2024-2026) — Prompt caching API documentation. Primary source for `cache_control` breakpoints, TTL tiers, and the 1.25x/0.1x write/read multipliers.
- OpenAI (2024-2026) — Prompt caching platform documentation. Primary source for the automatic-caching threshold and discount structure.
