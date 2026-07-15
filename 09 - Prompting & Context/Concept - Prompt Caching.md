---
tags: [concept, domain/prompting-context, level/core]
aliases: [context caching, cache_control]
summary: "Reusing the KV cache for a repeated prompt prefix skips redundant prefill compute, cutting cached-token cost up to 90%."
---
> **One-paragraph hook:** Every LLM call that shares a prefix with a prior call — the same system prompt, the same few-shot block, the same long document — is, by default, paying to recompute the same attention keys and values from scratch. Prompt caching stores the computed [[Concept - KV Cache]] for a token prefix so a later request sharing that exact prefix skips the expensive prefill and pays only for the new suffix, turning a recurring per-call compute cost into a near-fixed-cost lookup for the shared part of the prompt.

## The mechanism

LLM inference splits into a prefill phase — one forward pass across every prompt token to build that token's key/value entries — and a decode phase that generates output tokens one at a time, attending back over the accumulated KV. Prefill cost scales with input length: for a dense transformer it is roughly $2 \times N \times P$ FLOPs for $N$ prompt tokens and $P$ parameters, spent before a single output token is produced. Because causal attention means the K/V entries for token $i$ depend only on tokens $0..i$, a byte-identical prefix produces byte-identical KV values on every request. Prompt caching exploits this by persisting the KV cache server-side and matching an incoming prompt against the cached prefix token-by-token, starting at position 0. On a match, prefill for the matched span is skipped entirely and only the new suffix is prefilled:

```
Request 1:  [ system prompt ][ few-shot block ][ user turn A ]
             \_______________ written to cache ______________/

Request 2:  [ system prompt ][ few-shot block ][ user turn B ]
             \___ cache HIT: KV reused, skipped ___/^only this new suffix is prefilled
```

That token-level, position-0 matching is also the mechanism's sharpest constraint: matching stops at the first point of divergence. If a timestamp, a request ID, or a JSON object serialized with unstable key order sits anywhere before the reusable content, everything after that point misses the cache — even if the expensive part of the prompt (a long system prompt, a big document) is byte-identical to the last call. This is why cache-aware prompt design puts static content first and volatile content last, the opposite of how prompts are naturally written (context, then instructions, then the ever-changing user question).

## In practice

Pricing and TTL vary sharply by provider (as of 2026) — see [[Reference - Prompt Caching Across Providers]] for the full table — but Anthropic's model illustrates the shape of the economics: explicit `cache_control` breakpoints (up to 4 per request), a 5-minute default TTL with a 1-hour paid option, a write cost of roughly 1.25x the base input token price, and a read cost of roughly 0.1x base (a 90% discount on a cache hit), with a minimum cacheable prefix around 1,024 tokens for Sonnet/Opus (~2,048 for Haiku). OpenAI instead caches automatically, with no explicit breakpoint API, above a 1,024-token threshold in 128-token increments, at roughly a 50% read discount and no write premium, with a shorter ~5-10 minute idle-eviction window.

The write premium changes the economics from "caching is free speedup" to "caching is an investment that needs reuse to pay off." Using Anthropic's numbers: writing a cached prefix costs 1.25x and each subsequent read costs 0.1x, versus 1.0x per call with no caching at all. For $n$ calls sharing a prefix, total cost with caching is $1.25 + 0.1(n-1)$ (in units of the base price) versus $n$ without caching. Solving $1.25 + 0.1(n-1) = n$ gives a break-even just above $n \approx 1.3$ — meaning a *second* use of the same prefix already makes caching cheaper, and by three or four reuses the discount is substantial. A prefix used exactly once, however, still costs 25% more than not caching it at all: caching is a bet on reuse within the TTL, not an unconditional win.

This makes prompt caching the natural home for anything static and reused: a long [[Concept - System Prompts]] block, few-shot exemplar sets, RAG document prefixes injected before every query in a session, and multi-turn conversations where each new turn re-sends the whole transcript. It is also the billed, provider-side counterpart to what self-hosted inference servers already do for free: [[Concept - Automatic Prefix Caching]] in engines like vLLM and SGLang caches shared KV prefixes across concurrent requests as a standard part of the serving stack, built on the same paged-KV memory management that underlies [[Concept - Continuous Batching]] — the mechanism is identical; the difference is that a managed API meters and bills it explicitly. What a provider's cache actually retains once aggregate demand exceeds GPU memory is governed by the same tiering and eviction tradeoffs covered in [[Concept - KV Cache Offloading and Compression]] — a cached prefix isn't guaranteed to survive indefinitely just because it was written; it competes with every other tenant's cache for the same finite HBM.

## Failure modes

- **Cache-busting via nondeterministic prefix content.** A timestamp, a UUID, or unstable JSON key ordering anywhere before the reusable block invalidates the cache for everything downstream, and cost silently reverts to full price with no error thrown. Detection: monitor cache-hit token counts in the API response (Anthropic reports `cache_creation_input_tokens` and `cache_read_input_tokens` separately) and alert if the read/write ratio collapses.
- **TTL expiry between bursty calls.** A 5-minute default TTL means any gap longer than that between calls on the same session silently pays full prefill again, unless you send keep-alive requests or opt into a longer TTL tier.
- **Exceeding the breakpoint count.** Providers requiring explicit `cache_control` markers cap how many breakpoints a single request can set (4 for Anthropic); content beyond that cap doesn't get its own cache boundary and may not cache as intended.
- **Paying writes that are never read.** Enabling caching on genuinely single-use content — a one-off document, a unique per-user prompt with no repeat traffic — is a straightforward net loss: the write premium is paid and no reads amortize it.

## The non-obvious

The write premium is the detail almost everyone misses on first read: enabling prompt caching is not a free toggle, it is a bet that a given prefix will be reused enough times within the TTL to earn back the 1.25x write cost. Blanket-enabling `cache_control` on every request without checking actual reuse patterns can *increase* spend rather than reduce it — the right diagnostic is measuring prefix reuse rate before flipping the switch, not after.

A second trap is regional: caches are scoped per-org and, in practice, per-region — they are never shared across accounts and are not guaranteed to be shared across a provider's own data centers. A multi-region deployment that load-balances requests round-robin across regions can defeat its own cache purely through routing, paying full prefill on every call despite sending byte-identical prefixes, with the failure invisible unless cache-hit rate is tracked per region.

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
