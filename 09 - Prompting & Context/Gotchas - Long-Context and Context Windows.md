---
tags: [gotchas, domain/prompting-context, level/advanced]
aliases: []
summary: "Long-context pitfalls: silent truncation, context rot, lost-in-the-middle, NIAH overconfidence, and cost blowups, with fixes."
---
# Gotchas - Long-Context and Context Windows

Large context windows invite a false sense of security: the number on the pricing page says 200K or 1M tokens, so it's tempting to treat that as a budget you can spend freely. It isn't. Every one of these gotchas is a way that "the window is big enough" turns out to be the wrong question. Ordered roughly by how much production pain they cause.

## 1. Silent truncation eats your system prompt, not your history
**Symptom:** A long-running chat session gradually loses its persona and rules — the model stops following formatting instructions or safety constraints it obeyed earlier in the same conversation — with no error from the API.
**Cause:** When the accumulated input exceeds the context window, some client libraries and naive serving wrappers truncate from the head of the sequence to make room, and the head is usually where the system prompt lives. The truncation is silent because it's a length-management decision inside the client, not a model failure — the model faithfully continues whatever (now system-prompt-less) sequence it was actually given.
**Fix:** Reserve a fixed token budget for the system prompt and task spec, and truncate only conversation history (oldest turns first, or via [[Concept - Context Compaction]]) — never let head-truncation touch the static prefix.
**Detection:** Log the token count of every call broken down by segment (system, history, live turn); alert when the system-prompt segment's token count drops below its expected fixed size.

## 2. The advertised context window is not the effective one
**Symptom:** Quality degrades well before the stated max-token limit — a 200K-token-window model gives noticeably worse answers at 80K tokens than at 8K, on the identical task shape.
**Cause:** "Context rot" ([[Concept - Context Rot]]; Chroma 2025) — attention is a softmax over all positions, so probability mass dilutes as sequence length grows (see [[Concept - Softmax]]), and positional generalization degrades past the length a model was actually trained or extended on (see [[Concept - Rotary Position Embeddings (RoPE)]]). The nominal window is a serving and architecture spec — what fits in memory, what RoPE scaling was tuned for — not a promise that every position is used equally well.
**Fix:** Don't provision context budget up to the maximum window; measure your own task's effective length with a position-swept eval and budget comfortably below the point where accuracy starts declining.
**Detection:** Run the same query at multiple context lengths (2K, 20K, 100K...) with the same signal buried inside, and plot accuracy against length — a position-controlled eval, not a single needle-in-a-haystack pass.

## 3. Lost-in-the-middle: a buried instruction gets ignored
**Symptom:** A rule or fact placed in the middle of a long prompt is followed inconsistently, while the same content at the very start or very end is followed reliably.
**Cause:** Liu et al. 2023 ("Lost in the Middle") showed QA and retrieval accuracy is U-shaped in the position of the relevant fact within a long context — primacy and recency dominate, and mid-context information is used far less regardless of nominal window size.
**Fix:** Put the most critical instruction first in the prompt AND restate it again at the very end, right before the live query.
**Detection:** A position-swept eval that varies where the target fact sits in an otherwise fixed-length context; the U-shape is easy to see once you plot it.

## 4. Needle-in-a-haystack passing does not mean the model can reason over the window
**Symptom:** Your NIAH eval score is 99%+, you ship a long-context RAG feature on the strength of it, and production complaints roll in about missed cross-document facts.
**Cause:** NIAH tests verbatim retrieval of one lexically distinct sentence — the easiest possible long-context task. Multi-hop reasoning, aggregation across many chunks, and synthesizing scattered evidence exercise a materially harder capability that NIAH never probes; a model can ace NIAH and still fail badly at "count how many of these 40 documents mention X" or "reconcile these three conflicting numbers."
**Fix:** Evaluate with tasks representative of the real workload — multi-hop QA, aggregation, cross-reference — rather than trusting a public NIAH score.
**Detection:** Maintain a small in-house long-context eval that mirrors the actual production task shape, and re-run it on every model or context-length change.

## 5. Multi-turn drift: one early bad tool result poisons everything downstream
**Symptom:** A long agent session or chat degrades over many turns — the model keeps referencing a fact, tool output, or hallucination from early in the conversation that was already wrong, and compounds it.
**Cause:** Nothing in the architecture forgets; a wrong early observation sits in context with equal nominal standing to everything that follows, and subsequent generations condition on it just as they would on a correct fact, so errors compound turn over turn rather than decaying.
**Fix:** Compact or evict stale/incorrect turns rather than letting the transcript grow unbounded (see [[Concept - Context Compaction]]), and pin only the system prompt and task spec as permanently retained.
**Detection:** Spot-check long sessions for a "patient zero" wrong fact and trace how many later turns reference it; a rising error rate correlated with turn count is the signature.

## 6. Distractor documents lower accuracy more than they help
**Symptom:** Adding more retrieved passages "to be safe" makes answers worse, not better.
**Cause:** Plausible-but-irrelevant passages compete for attention mass the same as real content does; hard negatives — topically close but wrong — hurt more than random unrelated filler because they're harder for the model to discount outright.
**Fix:** Rerank and trim to fewer high-signal chunks (see [[Concept - Rerankers]]) instead of stuffing in everything retrieval returned.
**Detection:** Sweep the number of retrieved chunks (k) on an eval set — accuracy typically peaks and then declines as k grows past some task-dependent point.

## 7. Latency and cost blow up faster than context length grows
**Symptom:** Doubling input length more than doubles latency and dollar cost, and it gets progressively worse per turn in a multi-turn chat.
**Cause:** Prefill compute scales with sequence length and the [[Concept - KV Cache]] grows linearly in memory with it (see [[Reference - Memory Math for Transformers]] for the per-token byte cost); in a naive multi-turn loop without caching, the entire growing transcript gets re-prefilled from scratch on every single turn.
**Fix:** Cache the shared prefix (see [[Concept - Prompt Caching]]) so only the new suffix is prefilled each turn, and shrink context proactively rather than letting it grow unbounded.
**Detection:** Track prefill time and dollar cost per turn number within a long conversation — an uncached multi-turn chat shows visibly superlinear growth as the transcript lengthens.

## 8. Cache TTL expires between bursty calls, silently paying full prefill
**Symptom:** Prompt-cache hit rate craters during low-traffic periods (nights, weekends) even though the prompt content itself hasn't changed at all.
**Cause:** Prompt caches carry a TTL — Anthropic's default is roughly 5 minutes (see [[Concept - Prompt Caching]]) — and if the gap between calls sharing a prefix exceeds it, the cache is evicted; the next call pays full prefill and, for explicit-caching providers, the write premium again.
**Fix:** Use keep-alive pings against low-traffic endpoints, or opt into a longer TTL tier (Anthropic's 1-hour beta) for spiky workloads.
**Detection:** Monitor cache-hit rate by time-of-day and correlate dips against the gap duration between consecutive requests to the same endpoint.

## Connections
- [[Concept - Context Rot]] — the underlying mechanism most of these gotchas are surface symptoms of.
- [[Concept - Rerankers]] — the concrete fix for distractor degradation.
- [[Concept - KV Cache]] — the memory structure whose linear growth drives the latency/cost gotcha.
- [[Reference - Memory Math for Transformers]] — the actual per-token byte formulas behind the cost blowup.
- [[Concept - Prompt Caching]] — the mitigation for both the cost-blowup gotcha and the TTL gotcha itself.
- [[Concept - Context Compaction]] — the structural fix for multi-turn drift and unbounded transcript growth.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the positional mechanism whose extrapolation limits set where effective length actually starts breaking down.
- [[Concept - Softmax]] — the normalization at the heart of attention whose probability mass dilutes as sequence length grows, the root cause of gotcha #2.

## Sources
- Liu et al. (2023) — "Lost in the Middle: How Language Models Use Long Contexts": the U-shaped position-accuracy curve underlying gotcha #3.
- Chroma (2025) — "Context Rot" technical report: the effective-vs-nominal context length benchmark underlying gotcha #2.
- Anthropic and OpenAI provider documentation (as of 2026) — prompt-caching TTL and pricing specifics underlying gotcha #8.
