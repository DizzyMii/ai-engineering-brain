---
tags: [concept, domain/inference-serving, level/core]
aliases: [APC, prefix caching, prefix reuse]
summary: "Reusing already-computed KV blocks across requests that share a leading prefix, so shared system prompts and chat history skip prefill entirely."
---
# Concept - Automatic Prefix Caching
> **One-paragraph hook:** Most production prompts repeat something: a system prompt, a few-shot block, or a multi-turn chat history that gets re-sent every turn. Automatic prefix caching (APC) spots when a new request's leading tokens match [[Concept - KV Cache]] blocks already computed for an earlier request and points at those blocks instead of recomputing prefill. A repeated 2,000-token system prompt goes from tens of milliseconds of compute to a cache lookup.

## The mechanism
The KV cache lives in fixed-size blocks, the same blocking [[Concept - PagedAttention]] uses for memory management. APC hashes each block by its token content *and* the hash of every preceding block, so each hash really identifies "this exact prefix up to and including this block." When a request arrives, the engine walks its prompt block by block and looks each hash up in a cache index. On a hit, it points the new request's block table at the existing physical KV blocks (the copy-on-write sharing PagedAttention uses for beam search) and skips prefill compute for that span. Only the un-cached suffix needs a real forward pass. That's typically the last few blocks, wherever the new request's content actually diverges.

vLLM's automatic prefix caching implements this hash-per-block scheme directly. SGLang's RadixAttention (Zheng et al. 2024) generalizes it with a **radix tree** over all live KV in the engine in place of a flat hash table. Tree edges are shared token sequences. Two requests that diverge partway through a prompt share the common path and branch only where they differ, and LRU eviction over tree leaves kicks in when memory is tight. The difference is scope. vLLM's block hashing is tuned for exact prefix matches against a cache, while RadixAttention uses prefix sharing as a scheduling signal across arbitrary concurrent requests, including prefixes nobody declared up front as a static system prompt.

```
Radix tree over three live requests sharing a system prompt + partial history:

root
 └─ "SYSTEM_PROMPT..." (shared KV, refcount=3)
     ├─ "...user turn 1: hi"           (req A diverges here)
     ├─ "...user turn 1: help me code" (req B diverges here)
     └─ "...user turn 1: help me code" ─ "...turn 2: fix this bug" (req C, shares B's turn 1)
```

## In practice
The biggest wins come where a large share of prompt tokens repeat by construction: a system prompt shared by every user, few-shot exemplar blocks, multi-turn chat that re-sends the full history each turn, and agent loops that replay a growing transcript on every step (see [[Deep Dive - The Agent Loop]]). These workloads routinely see **70-95% of prompt tokens land as cache hits**. For chat and agent products, prefix caching is close to a free win, since it cuts TTFT and compute cost on the traffic pattern those products generate.

Matching is strict. It runs on exact token IDs, with no semantic similarity, so one differing token near the *front* of the prompt (a timestamp, a user ID, a random nonce) busts the cache for every block after it, even if the rest is identical. The fix is template discipline: put anything variable (user ID, current date, session state) at the *end*, after the stable system/instruction block, so the cacheable prefix stays constant across requests. Caching only touches the prompt side and has no effect on sampled output. It's a pure latency/cost optimization with zero correctness risk to generation, as long as the prompt hashing itself is correct.

## Failure modes
**Cache thrash:** with many distinct, low-reuse prefixes, or prompts that vary early instead of late, the radix tree or hash table churns constantly. Hit rate collapses toward zero and you still pay the bookkeeping overhead. Watch cache hit rate alongside TTFT. If the hit rate doesn't match the structural overlap you expect in the traffic, check the prompt templates.

**Stale reuse:** edit a system prompt or template without bumping whatever key scopes the cache, and old and new requests can silently share KV computed under the old prompt. When templates are hot-swapped in production, key the cache (or force invalidation) on a template version as well as raw token content.

**Privacy and cross-tenant leakage:** a naive global cache shared across tenants leaks the *existence* of another user's prompt through timing. A hit is measurably faster than a miss, so an attacker probing prefixes can infer whether a specific prefix (say, another user's private document) was recently processed by someone else. Production multi-tenant systems scope the cache per API key or per tenant instead of one global pool, giving up some cross-user reuse for isolation.

## The non-obvious
The failure practitioners hit first in production is neither thrash nor leakage. It's the "one token at the front" bug. Teams prepend variable content (a request ID, a timestamp for logging) to the template for readability, then can't work out why the hit rate is near zero despite a mostly static system prompt. The fix is almost always reordering the template, not tuning the cache.

Second, automatic prefix caching and [[Concept - Continuous Batching]] compound. With a cached prefix, prefill for a newly admitted request is nearly instant, which removes much of the interference [[Concept - Chunked Prefill]] was built to solve. A well-cached agent workload can run smoothly on a smaller prefill token budget than an uncached one would need.

## Connections
- [[Concept - KV Cache]] — the underlying structure being reused; prefix caching is a policy layered on top of it, not a separate cache.
- [[Concept - PagedAttention]] — supplies the block-based layout and copy-on-write sharing that make pointing multiple requests at the same physical KV blocks possible.
- [[Concept - Prompt Caching]] — the API-level, pricing-facing view of this same mechanism as exposed by hosted providers; this note is the serving-engine internals underneath it.
- [[Breakdown - vLLM]] — implements automatic prefix caching via per-block hashing.
- [[Breakdown - SGLang and RadixAttention]] — implements the radix-tree generalization that shares arbitrary common prefixes across concurrent requests.
- [[Deep Dive - The Agent Loop]] — the workload shape (growing, replayed transcript) that benefits most from prefix caching, since each step re-sends nearly the same history.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — prefix caching is one of the direct levers on TTFT and cost per token that this note quantifies.
- [[Concept - The Inference Request Lifecycle]] — the prefill stage this technique is specifically designed to skip; read that note first for the baseline request path.
- [[Concept - Continuous Batching]] — a well-cached prefix shrinks the prefill work a newly admitted request needs, reducing the interference continuous batching has to schedule around.
- [[Concept - Chunked Prefill]] — prefix caching reduces how much of a new request's prompt actually needs a chunked prefill budget in the first place.

## Sources
- Zheng et al. (2024) — *SGLang: Efficient Execution of Structured Language Model Programs*. Introduced RadixAttention, the radix-tree generalization of automatic prefix caching with LRU eviction over shared KV.
- Kwon et al. (2023) — *Efficient Memory Management for Large Language Model Serving with PagedAttention* (SOSP). Established the block-based, copy-on-write KV layout that block-hash prefix caching builds on.
