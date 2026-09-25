---
tags: [concept, domain/prompting-context, level/advanced]
aliases: [context degradation, effective context length]
summary: "Model quality decays as input length grows, well before the advertised window limit — the window is a spec, not a usable-capacity promise."
---
> **One-paragraph hook:** A 1M-token context window is a marketing number. It doesn't guarantee performance. Give a model ten times more tokens and accuracy on the same task measurably drops, even when all the right information is technically present. The field now calls this context rot. Every serving engineer hits it eventually: a RAG pipeline that worked well with 3 retrieved chunks gets worse when someone "helpfully" bumps it to 20. More context adds to the denominator, and it usually adds little signal.

## The mechanism

A transformer's attention is a [[Concept - Softmax]] over every position in the context. For query $q$ at the current step, the weight on key $k_i$ is

$$a_i = \frac{\exp(q \cdot k_i / \sqrt{d})}{\sum_{j=1}^{N} \exp(q \cdot k_j / \sqrt{d})}$$

As $N$ grows, the denominator sums over more terms. Unless the logits are sharply peaked on the relevant tokens, probability mass spreads thinner across a bigger competing set. And the competitors usually aren't inert filler. They're *plausible*: topically related passages, near-duplicate facts. They pull weight away from the signal.

That's the root of **lost-in-the-middle**. Liu et al. (2023), *"Lost in the Middle: How Language Models Use Long Contexts,"* found that accuracy on multi-document QA and key-value retrieval is U-shaped in the position of the relevant fact. Performance peaks when the answer sits at the very start or very end of the context and drops substantially when it's buried in the middle. In some configurations it fell below a closed-book (no-context-at-all) baseline. The model can see the middle tokens fine. It just weights them badly against everything else competing for attention mass.

Two more effects stack on top. Positional generalization degrades past the length the model was trained on: [[Concept - Rotary Position Embeddings (RoPE)]] encodes position via rotation frequencies tuned to a training-length distribution, and extrapolating far past it produces attention patterns the model never learned to read. YaRN and NTK-aware scaling exist as patches for this. Then there are [[Concept - Attention Sinks]]. Early tokens (often BOS) soak up a large share of attention mass as a sort of "no-op" release valve, and in long contexts that interacts with dilution to squeeze what's left for the tokens that matter.

## In practice

Chroma's 2025 technical report, *"Context Rot: How Increasing Input Tokens Impacts LLM Performance,"* tested roughly 18 models on simple tasks. Performance decayed smoothly as input length grew, well inside the advertised window. The term "context rot" comes from this report, and it generalizes Lost in the Middle's position-specific result into a length-dependent one. The upshot (as of 2026): don't assume a model advertising a 1M-token window (Gemini 1.5/2.x-class, Llama 4 Scout) can *use* anywhere near that much context reliably for tasks that need synthesis across the full span.

Needle-in-a-haystack (NIAH) benchmarks are the classic trap. Passing NIAH proves the model can retrieve one verbatim fact planted in filler. It says nothing about multi-hop reasoning or aggregating scattered facts, and that's what most real long-context work (agent transcripts, multi-document synthesis, codebase-wide questions) needs. A model can ace NIAH at 1M tokens and still fail badly when asked to combine five facts spread across the same window.

One mitigation is position-aware prompt construction. Put the critical instruction at the start of the context **and** restate it at the end, so it lands on both peaks of the U-curve.

## Failure modes

- **Silent mid-context recall failure.** A fact in the middle of a long prompt gets ignored or misattributed, and nothing errors. Detection: run a position-controlled eval. Sweep a known ground-truth fact across positions and plot accuracy against position. A flat high line means you're fine; a dip in the middle is the U-curve tax.
- **Distractor-induced collapse.** Plausible-but-irrelevant retrieved passages lower accuracy. *Hard negatives* (topically close, superficially similar) hurt more than random filler because they compete in the same representational neighborhood as the true answer. Detection: A/B the query with and without the marginal retrieved documents. If accuracy drops when you add "helpful" context, you've found it.
- **NIAH false confidence.** You ship a long-context feature validated only on needle tests and find out in production that multi-hop questions fail. Detection: eval on aggregation and multi-hop tasks that look like the real workload, in addition to single-fact retrieval.
- **Compounding cost and latency.** Prefill is $O(N)$ compute and the [[Concept - KV Cache]] grows $O(N)$ in memory. So the "just add more context" habit that hurts quality also raises latency and cost at the same time.

## The non-obvious

The lesson people resist longest: adding *more relevant-looking* context can make answers *worse*, and slower too. It's tempting to treat retrieval recall as free ("if in doubt, include the chunk"). With distractor sensitivity, a topically adjacent but unnecessary document degrades the answer to the question you cared about. That inverts the naive RAG intuition. Retrieval should curate the smallest high-signal set that answers the question, and maximizing recall into the window works against that. So [[Concept - Rerankers]] and aggressive [[Concept - Context Compaction]] are quality levers as much as cost savers.

## Connections
- [[Concept - Rotary Position Embeddings (RoPE)]] — the positional-encoding mechanism whose extrapolation limits set a hard ceiling on effective context independent of the advertised window.
- [[Concept - Attention Sinks]] — the sink dynamic that competes with genuine signal for attention mass as context length grows.
- [[Concept - Softmax]] — the normalization at the mathematical root of why more competing tokens means diluted mass on any one of them.
- [[Concept - Rerankers]] — the standard mitigation: shrink the context to high-signal documents before it ever reaches the model.
- [[Concept - Context Compaction]] — the complementary mitigation for long-running sessions: actively compress or evict rather than let context grow unbounded.
- [[Concept - Context Engineering]] — the broader discipline this note is a failure-mode chapter of: context rot is the reason curation, not maximization, is the right default.
- [[Gotchas - Long-Context and Context Windows]] — the aggregated pitfall list (silent truncation, cache TTL, multi-turn drift) that context rot sits alongside in production.
- [[Concept - KV Cache]] — the memory structure whose linear growth makes long-context both a quality problem (this note) and a cost/latency problem simultaneously.

## Sources
- Liu et al. (2023) — "Lost in the Middle: How Language Models Use Long Contexts." Established the U-shaped position bias in long-context QA and retrieval.
- Chroma (2025) — "Context Rot: How Increasing Input Tokens Impacts LLM Performance." Multi-model empirical study showing smooth performance decay with input length, the origin of the term.
- Xiao et al. (2023) — "Efficient Streaming Language Models with Attention Sinks" (StreamingLLM). Identified the attention-sink phenomenon that interacts with long-context degradation.
