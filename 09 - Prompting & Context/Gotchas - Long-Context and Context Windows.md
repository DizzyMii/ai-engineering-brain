---
tags: [gotchas, domain/prompting-context, level/advanced]
aliases: []
summary: "Long-context pitfalls: silent truncation, context rot, lost-in-the-middle, NIAH overconfidence, and cost blowups, with fixes."
---
# Gotchas - Long-Context and Context Windows

Big context windows breed false confidence. The pricing page says 200K or 1M tokens, and it's tempting to treat that as a budget you can spend freely. You can't. Each gotcha below is a case where "is the window big enough?" was the wrong question. Roughly ordered by how much production pain they cause.

## 1. Silent truncation eats your system prompt, not your history
**Symptom:** A long chat session slowly loses its persona and rules. The model stops following formatting instructions or safety constraints it obeyed earlier in the same conversation, and the API reports no error.
**Cause:** When accumulated input exceeds the window, some client libraries and naive serving wrappers make room by truncating from the head of the sequence, which is usually where the system prompt lives. It's silent because the client made a length-management decision; the model didn't fail. It faithfully continues the (now system-prompt-less) sequence it was given.
**Fix:** Reserve a fixed token budget for the system prompt and task spec, and truncate only conversation history (oldest turns first, or via [[Concept - Context Compaction]]). Head truncation must never touch the static prefix.
**Detection:** Log every call's token count by segment (system, history, live turn). Alert when the system-prompt segment drops below its expected fixed size.

## 2. The advertised context window is not the effective one
**Symptom:** Quality drops well before the stated max-token limit. A model with a 200K-token window gives noticeably worse answers at 80K tokens than at 8K on the same task shape.
**Cause:** "Context rot" ([[Concept - Context Rot]]; Chroma 2025). Attention is a softmax over all positions, so probability mass thins out as sequence length grows (see [[Concept - Softmax]]), and positional generalization degrades past the length the model was trained or extended on (see [[Concept - Rotary Position Embeddings (RoPE)]]). The nominal window is a serving and architecture spec (what fits in memory, what RoPE scaling was tuned for). It doesn't promise that every position gets used equally well.
**Fix:** Don't plan your context budget up to the maximum window. Measure your task's effective length with a position-swept eval and stay comfortably below where accuracy starts to fall.
**Detection:** Run the same query at several context lengths (2K, 20K, 100K...) with the same signal buried inside and plot accuracy against length. That's a position-controlled eval; a single needle-in-a-haystack pass won't show it.

## 3. Lost in the middle: a buried instruction gets ignored
**Symptom:** A rule or fact in the middle of a long prompt is followed inconsistently. The same content at the very start or very end is followed reliably.
**Cause:** Liu et al. 2023 ("Lost in the Middle") showed QA and retrieval accuracy is U-shaped in the position of the relevant fact within a long context. Primacy and recency dominate, and mid-context information gets used far less whatever the nominal window size.
**Fix:** Put the most critical instruction first AND restate it at the very end, right before the live query.
**Detection:** A position-swept eval that moves the target fact around in an otherwise fixed-length context. Once you plot it, the U-shape is easy to see.

## 4. Passing needle-in-a-haystack does not mean the model can reason over the window
**Symptom:** Your NIAH score is 99%+, you ship a long-context RAG feature on the strength of it, and complaints about missed cross-document facts start coming in.
**Cause:** NIAH tests verbatim retrieval of one lexically distinct sentence, the easiest long-context task there is. Multi-hop reasoning, aggregating across many chunks and synthesizing scattered evidence need a much harder capability that NIAH never tests. A model can ace NIAH and still fail badly at "count how many of these 40 documents mention X" or "reconcile these three conflicting numbers."
**Fix:** Evaluate on tasks that look like the real workload (multi-hop QA, aggregation, cross-reference). Don't trust a public NIAH score.
**Detection:** Keep a small in-house long-context eval shaped like the production task, and re-run it on every model or context-length change.

## 5. Multi-turn drift: one bad early tool result poisons everything after it
**Symptom:** A long agent session or chat degrades over many turns. The model keeps referring back to a fact, tool output or hallucination from early on that was wrong, and builds on it.
**Cause:** Nothing in the architecture forgets. A wrong early observation sits in context with the same nominal standing as everything after it, and later generations condition on it as they would on a correct fact. Errors compound turn over turn instead of fading.
**Fix:** Compact or evict stale and incorrect turns instead of letting the transcript grow without bound (see [[Concept - Context Compaction]]). Pin only the system prompt and task spec permanently.
**Detection:** Spot-check long sessions for a "patient zero" wrong fact and count how many later turns reference it. Error rate rising with turn count is the signature.

## 6. Distractor documents lower accuracy more than they help
**Symptom:** Adding more retrieved passages "to be safe" makes answers worse.
**Cause:** Plausible but irrelevant passages compete for attention mass like real content does. Hard negatives (topically close but wrong) hurt more than random unrelated filler, since the model has a harder time dismissing them.
**Fix:** Rerank and trim to fewer high-signal chunks (see [[Concept - Rerankers]]) instead of stuffing in everything retrieval returned.
**Detection:** Sweep the number of retrieved chunks (k) on an eval set. Accuracy typically peaks and then falls once k passes some task-dependent point.

## 7. Latency and cost grow faster than context length
**Symptom:** Doubling input length more than doubles latency and dollar cost, and it gets worse every turn in a multi-turn chat.
**Cause:** Prefill compute scales with sequence length, and the [[Concept - KV Cache]] grows linearly in memory with it ([[Reference - Memory Math for Transformers]] has the per-token byte cost). In a naive multi-turn loop without caching, the whole growing transcript gets re-prefilled from scratch every turn.
**Fix:** Cache the shared prefix (see [[Concept - Prompt Caching]]) so each turn prefills only the new suffix, and shrink context proactively instead of letting it grow unbounded.
**Detection:** Track prefill time and dollar cost by turn number within a long conversation. An uncached multi-turn chat shows clearly superlinear growth as the transcript gets longer.

## 8. Cache TTL expires between bursty calls, and you silently pay full prefill
**Symptom:** Prompt-cache hit rate collapses in low-traffic periods (nights, weekends) though the prompt content hasn't changed.
**Cause:** Prompt caches have a TTL, roughly 5 minutes by default for Anthropic (see [[Concept - Prompt Caching]]). If the gap between calls sharing a prefix exceeds it, the cache is evicted. The next call pays full prefill and, with explicit-caching providers, the write premium again.
**Fix:** Send keep-alive pings to low-traffic endpoints, or use a longer TTL tier (Anthropic's 1-hour beta) for spiky workloads.
**Detection:** Monitor cache-hit rate by time of day and correlate dips with the gap between consecutive requests to the same endpoint.

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
