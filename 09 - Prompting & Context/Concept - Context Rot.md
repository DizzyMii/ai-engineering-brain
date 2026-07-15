---
tags: [concept, domain/prompting-context, level/advanced]
aliases: [context degradation, effective context length]
summary: "Model quality decays as input length grows, well before the advertised window limit — the window is a spec, not a usable-capacity promise."
---
> **One-paragraph hook:** A 1M-token context window is a marketing number, not a performance guarantee. Feed a model ten times more tokens and, even with all the "right" information technically present, accuracy on the same task measurably drops — a phenomenon the field now calls context rot. Every serving engineer eventually hits this: a RAG pipeline that worked great with 3 retrieved chunks quietly gets worse when someone "helpfully" bumps it to 20, because more context is not more signal — it's more denominator.

## The mechanism

A transformer's attention is a [[Concept - Softmax]] over every position in the context: for query $q$ at the current step, the weight on key $k_i$ is

$$a_i = \frac{\exp(q \cdot k_i / \sqrt{d})}{\sum_{j=1}^{N} \exp(q \cdot k_j / \sqrt{d})}$$

As $N$ grows, the denominator sums over more terms. If the logits aren't sufficiently peaked toward the truly relevant tokens, probability mass gets spread thinner across a larger competing set — and unlike a clean uniform dilution, the competitors are often *plausible* (topically related passages, near-duplicate facts), so they actively pull weight away from the signal rather than just sitting inert. This is the mechanistic root of **lost-in-the-middle**: Liu et al. (2023), *"Lost in the Middle: How Language Models Use Long Contexts,"* found that accuracy on multi-document QA and key-value retrieval is U-shaped in the position of the relevant fact — performance is highest when the answer sits at the very start or very end of the context and drops substantially when it's buried in the middle, in some configurations falling below a closed-book (no-context-at-all) baseline. The model isn't failing to "see" the middle tokens; it's failing to weight them correctly against everything else competing for attention mass.

Two more mechanisms compound this. First, positional generalization degrades past the length a model was actually trained on: [[Concept - Rotary Position Embeddings (RoPE)]] encodes position via rotation frequencies tuned to a training-length distribution, and extrapolating far beyond it produces attention patterns the model never learned to interpret (the reason methods like YaRN and NTK-aware scaling exist as patches). Second, [[Concept - Attention Sinks]] — the empirical finding that early tokens (often the BOS token) absorb a disproportionate, load-bearing share of attention mass as a kind of "no-op" release valve — interact with dilution in long contexts, further squeezing what's left for genuinely relevant tokens.

## In practice

Chroma's 2025 technical report, *"Context Rot: How Increasing Input Tokens Impacts LLM Performance,"* tested roughly 18 models on simple tasks and found smooth performance decay as input length grew, well inside the advertised window — this is where the term "context rot" comes from, and it generalizes the position-specific finding of Lost in the Middle into a broader length-dependent one. The practical upshot (as of 2026): a model advertising a 1M-token window (Gemini 1.5/2.x-class, Llama 4 Scout) should not be assumed to *use* anywhere near that much context reliably for tasks requiring synthesis across the full span.

Needle-in-a-haystack (NIAH) benchmarks are the classic trap here: passing NIAH only proves the model can retrieve one verbatim fact planted in a sea of filler — it says nothing about multi-hop reasoning or aggregation across scattered facts, which is what most real long-context workloads (agent transcripts, multi-document synthesis, codebase-wide questions) actually demand. A model can ace NIAH at 1M tokens and still fail badly on a task requiring it to combine five facts spread across that same window. Mitigate with position-aware prompt construction: put the critical instruction at the very start of the context **and** restate it at the end, exploiting the primacy-and-recency peaks of the U-curve directly rather than hoping the middle holds.

## Failure modes

- **Silent mid-context recall failure.** A fact placed in the middle of a long prompt gets ignored or misattributed with no error signal. Detection: run a position-controlled eval — sweep the position of a known ground-truth fact across the context and plot accuracy vs. position; a flat high line means you're fine, a dip in the middle means you're paying the U-curve tax.
- **Distractor-induced collapse.** Adding plausible-but-irrelevant retrieved passages lowers accuracy, and *hard negatives* (topically close, superficially similar) hurt more than random filler text because they compete directly in the same representational neighborhood as the true answer. Detection: A/B the same query with and without the marginal retrieved documents; if accuracy drops when you add "helpful" context, you've found this failure mode.
- **NIAH false confidence.** Shipping a long-context feature validated only on needle tests, then discovering in production that multi-hop questions fail. Detection: evaluate with aggregation/multi-hop tasks representative of the real workload, not just single-fact retrieval.
- **Compounding cost and latency.** Longer context isn't just a quality tax — prefill is $O(N)$ compute and the [[Concept - KV Cache]] grows $O(N)$ in memory, so the same "just add more context" instinct that degrades quality also degrades latency and cost simultaneously.

## The non-obvious

The counterintuitive lesson practitioners resist the longest: adding *more relevant-looking* context can make outputs *worse*, not just slower. It's tempting to treat retrieval recall as an unqualified good — "if in doubt, include the chunk" — but distractor sensitivity means a topically-adjacent-but-unnecessary document actively degrades the answer to the question that mattered. This flips the naive RAG intuition: the goal of retrieval isn't maximizing recall into the context window, it's curating the smallest high-signal set that answers the question, which is why [[Concept - Rerankers]] and aggressive [[Concept - Context Compaction]] are quality levers, not just cost-saving afterthoughts.

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
