---
tags: [concept, domain/inference-serving, level/core]
aliases: [APC, prefix caching, prefix reuse]
summary: "Reusing already-computed KV blocks across requests that share a leading prefix, so shared system prompts and chat history skip prefill entirely."
---
# Concept - Automatic Prefix Caching
> **One-paragraph hook:** Most production prompts aren't unique — they share a system prompt, a few-shot block, or a multi-turn chat history that gets re-sent every turn. Automatic prefix caching (APC) recognizes when a new request's leading tokens match [[Concept - KV Cache]] blocks already computed for an earlier request and points at them instead of recomputing prefill, turning a repeated 2,000-token system prompt from tens of milliseconds of compute into a cache lookup.

## The mechanism
The KV cache is stored in fixed-size blocks (the same blocking [[Concept - PagedAttention]] uses for memory management). Automatic prefix caching hashes each block by its token content *and* the hash of every preceding block in the sequence, so the hash is really a hash of "this exact prefix up to and including this block." When a new request arrives, the engine walks its prompt block-by-block and checks each hash against a cache index: on a hit, it points the new request's block table at the existing physical KV blocks (the same copy-on-write sharing mechanism PagedAttention uses for beam search) instead of running prefill compute for that span. Only the un-cached suffix — typically the last few blocks, wherever the new request's content actually diverges — needs a real forward pass.

vLLM's automatic prefix caching implements this hash-per-block scheme directly. SGLang's RadixAttention (Zheng et al. 2024) generalizes it: instead of a flat hash table, it maintains a **radix tree** over all live KV in the engine, where tree edges are shared token sequences and any two requests that diverge partway through a prompt automatically share the common prefix path and only branch at the point of divergence, with LRU eviction over tree leaves when memory is tight. The practical difference is scope — vLLM's block hashing is optimized for exact prefix matches against a cache; RadixAttention treats prefix-sharing as a first-class scheduling signal across arbitrary concurrent requests, not just a static, pre-declared system prompt.

```
Radix tree over three live requests sharing a system prompt + partial history:

root
 └─ "SYSTEM_PROMPT..." (shared KV, refcount=3)
     ├─ "...user turn 1: hi"           (req A diverges here)
     ├─ "...user turn 1: help me code" (req B diverges here)
     └─ "...user turn 1: help me code" ─ "...turn 2: fix this bug" (req C, shares B's turn 1)
```

## In practice
The biggest wins come from workload shapes where a large fraction of prompt tokens are structurally repeated: a shared system prompt across every user, few-shot exemplar blocks, multi-turn chat where each turn re-sends the full history, and agent loops that replay a growing transcript on every step (see [[Deep Dive - The Agent Loop]]). These workloads routinely see **70-95% of prompt tokens land as cache hits**, which is why prefix caching is close to a free win for chat and agent products specifically — it directly attacks the TTFT and compute cost of exactly the traffic pattern those products generate.

Correctness is strict: matching is on exact token IDs, not semantic similarity, so a single differing token — a timestamp, a user ID, a random nonce — inserted near the *front* of the prompt busts the cache for every block downstream of it, even if the rest of the prompt is identical. The practitioner fix is prompt-template discipline: put anything variable (user ID, current date, session state) at the *end* of the prompt, after the stable system/instruction block, so the cache-relevant prefix stays constant across requests. Caching only ever touches the prompt side — it has no effect on sampled output, so it's a pure latency/cost optimization with zero correctness risk to generation itself, as long as the underlying prompt hashing is correct.

## Failure modes
**Cache thrash:** a workload with many distinct, low-reuse prefixes (or one where prompts vary early rather than late) churns the radix tree or hash table constantly, and the hit rate collapses toward zero while still paying the bookkeeping overhead — detectable by monitoring cache hit rate alongside TTFT; a hit rate that doesn't match the expected structural overlap of the traffic is the signal to check prompt templates.

**Stale reuse:** if a system prompt or template is edited without bumping whatever key scopes the cache, old and new requests can silently share KV computed under the old prompt — the fix is to key the cache (or force invalidation) on a template version, not just raw token content, when templates are hot-swapped in production.

**Privacy and cross-tenant leakage:** a naive global cache shared across tenants can leak the *existence* of another user's prompt through timing — a cache hit is measurably faster than a miss, so an attacker probing prefixes can infer whether a specific prefix (e.g., another user's private document) was recently processed by someone else. Production multi-tenant systems scope the cache per API key or per tenant rather than sharing one global pool, trading away some of the cross-user reuse for isolation.

## The non-obvious
The failure mode practitioners hit first in production isn't thrash or leakage, it's the "one token at the front" bug: teams template their prompts with the variable content (a request ID, a timestamp for logging) prepended for readability, then can't understand why their prefix cache hit rate is near zero despite a mostly-static system prompt — the fix is almost always reordering the template, not tuning the cache. The second non-obvious point is that automatic prefix caching and [[Concept - Continuous Batching]] compound: a cached prefix means the "prefill" for a newly admitted request is nearly instant, which removes much of the interference [[Concept - Chunked Prefill]] was built to solve in the first place — a well-cached agent workload can run smoothly with a smaller prefill token budget than an uncached one would need.

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
