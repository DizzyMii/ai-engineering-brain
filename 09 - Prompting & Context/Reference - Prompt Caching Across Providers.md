---
tags: [reference, domain/prompting-context, level/core]
aliases: []
summary: "Date-stamped comparison of prompt-caching TTL, minimum prefix, and pricing across Anthropic, OpenAI, Gemini, and DeepSeek."
---
*(as of 2026 — caching terms and prices move quickly; verify against current provider docs before using these numbers in a cost model. See [[Concept - Prompt Caching]] for the mechanism and break-even math behind these columns.)*

## Comparison table

| Provider | Mode | Min cacheable prefix | Write multiplier¹ | Read multiplier¹ | TTL / eviction | Breakpoints | Notes |
|---|---|---|---|---|---|---|---|
| Anthropic (Claude) | Explicit (`cache_control`) | ~1,024 tokens (Sonnet/Opus); ~2,048 (Haiku) | ~1.25x | ~0.1x | 5 min default; 1 hr option (paid) | Up to 4 per request | Caller decides exactly what's cached; scoped per-org². |
| OpenAI (GPT) | Automatic | ≥1,024 tokens, then 128-token steps | 1.0x (no premium) | ~0.5x | ~5-10 min idle eviction | N/A (automatic) | Keyed on exact prefix + org; no manual breakpoint API. |
| Google Gemini | Implicit (automatic) + explicit context caching | Implicit: model-dependent; explicit: ~4,096+ tokens | Explicit: billed per token-hour of storage³ | Reduced per-token rate on hit | Explicit: caller-set TTL at creation; implicit: not caller-controlled | Explicit: user-managed cache object | Two distinct mechanisms with different billing models, not one feature. |
| DeepSeek | Automatic, disk-backed | Not a fixed floor — disk KV cache | 1.0x (no premium) | ~0.1x on a context hit | Not TTL-bound in the usual sense — disk-backed persistence | N/A (automatic) | Distinctive disk-backed design — a real production instance of the tiering strategies covered in [[Concept - KV Cache Offloading and Compression]]; unusually cheap and durable on hits. |

¹ Multipliers apply to the input-token price only; the uncached suffix of every request still bills at the full base input rate.
² "Read"/cache-hit pricing covers only the matched cached prefix. Caches are per-org and, in practice, per-region — never shared across accounts, and not guaranteed to be shared across a provider's own data centers.
³ Gemini's explicit context caching bills separately for cache *storage* (per token-hour) on top of the discounted per-token rate on a hit — a different cost model from the write-premium-on-first-use approach Anthropic and DeepSeek use.

## Connections
- [[Concept - Prompt Caching]] — the mechanism and break-even economics this table is a quick-reference companion to.
- [[Concept - KV Cache]] — what is actually being persisted and reused under every row of this table.
- [[Concept - Cost Engineering for LLM Applications]] — use this table directly when modeling per-request cost for a multi-provider or provider-switching deployment.
- [[Concept - Semantic Caching]] — a complementary caching layer (fuzzy response reuse) that composes with, rather than replaces, the exact-prefix caching in this table.
- [[Concept - Prompt Engineering]] — the prefix-design discipline (static-first ordering) that determines whether any row of this table actually pays off in practice.
- [[Concept - Automatic Prefix Caching]] — the unbilled, self-hosted equivalent of the "automatic" rows above, available in open-source serving engines.
- [[Concept - KV Cache Offloading and Compression]] — the deeper mechanism behind DeepSeek's disk-backed cache row above: tiering the KV cache down to NVMe instead of holding it all in HBM.
