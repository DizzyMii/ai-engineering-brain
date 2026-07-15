---
tags: [concept, domain/agents, level/advanced]
aliases: [agent memory, long-term memory for agents, MemGPT-style memory]
summary: "How agents persist state past the context window: episodic/semantic/procedural stores, scored retrieval, and the hard write-policy problem."
---
> **One-paragraph hook:** An agent's context window is a whiteboard that gets erased every session; memory is the filing cabinet next to it. The interesting engineering isn't the filing cabinet itself — it's deciding what goes in it, how it's indexed, and how a stale or contradictory page gets pulled back out three weeks later and presented as current fact.

## The mechanism

Agent memory splits along two axes. The first is duration: **short-term/working memory** is just the context window — whatever tokens are currently loaded — and it vanishes when the session ends or the window fills. **Long-term memory** is an external store that survives across sessions and must be explicitly written to and retrieved from. The second axis is content type, borrowed from cognitive-science taxonomy: **episodic** memory (specific past interactions — "the user asked about X on Tuesday"), **semantic** memory (facts about the world or the user, stripped of when/where they were learned), and **procedural** memory (learned skills or how-to knowledge — "the deploy script needs `--force` on this repo").

Two systems define the mechanism in practice. **Generative Agents** (Park et al. 2023) introduced the *memory stream*: every observation is stored as a timestamped natural-language entry, and retrieval scores candidates on three signals combined into one number:

$$\text{score} = \alpha_{\text{recency}} \cdot \text{recency} + \alpha_{\text{importance}} \cdot \text{importance} + \alpha_{\text{relevance}} \cdot \text{relevance}$$

where recency is an exponential decay over hours since last access, importance is a 1–10 "poignancy" score the LLM itself assigns at write time, and relevance is cosine similarity between the query embedding and the memory's embedding (the same machinery as [[Concept - Embedding Models]] and [[Concept - HNSW]] for the index). The paper also runs periodic *reflection*: every so often the agent generates higher-level insights by summarizing clusters of recent memories, producing a synthesized memory that itself becomes retrievable — a crude form of consolidation.

**MemGPT**, later productized as Letta (Packer et al. 2023), takes an OS-inspired framing instead: the model has a small, fixed *main context* (like RAM) and unbounded *external context* — recall storage and archival storage (like disk). The model doesn't passively receive retrieved memories; it actively pages data in and out by calling functions (`core_memory_append`, `archival_memory_search`, `conversation_search`) exposed as tools, the same interface described in [[Concept - Tool Use and Function Calling]]. This is a genuinely different design axis: Generative Agents' retrieval is a fixed pipeline the harness runs every turn, while MemGPT's is a decision the model itself makes.

## In practice

Retrieval of memories reuses RAG infrastructure wholesale — an embedding index, approximate nearest-neighbor search, sometimes a reranking pass (link [[Concept - Rerankers]]) — but the query is agent-generated rather than user-typed, which changes its statistics: it tends to be more templated, more repetitive across turns, and easier to cache. For systems that need the retrieval step itself to be adaptive rather than a fixed top-k call, this converges with [[Concept - Agentic Retrieval]] — the memory lookup becomes another tool the agent decides when and how to invoke, rather than something injected unconditionally every turn.

The harder problem in production is almost never retrieval — it's the **write policy**. Deciding what's worth storing, deduplicating near-identical entries, and reconciling contradictions (the user's stated preference changed; which version is current?) is unsolved in general. Teams that embed every tool call and every message verbatim end up with a store where cosine similarity retrieves plausible-sounding but low-signal noise, because the store was never curated for retrievability in the first place.

## Failure modes

**Memory bloat**: unbounded write policies grow the store faster than any query needs, degrading both retrieval precision (more near-duplicate distractors) and cost (larger index, more embedding calls). Detection: track store growth rate against distinct-fact growth rate — if the ratio diverges, you're storing redundancy, not information.

**Stale or contradictory memories surfacing**: without an invalidation mechanism, an old fact ("user is on the free tier") outranks a newer one on relevance and gets served as current. Detection: memories with no expiry/supersession field and no write-time conflict check are a smell; symptom is the agent confidently asserting something the user just corrected.

**Retrieval misses on paraphrase**: embedding similarity is lexically fuzzy but not perfect — a memory phrased as "deploys fail on Fridays" may not surface for the query "why did the release break," because the surface forms diverge more than the embedding model's training distribution anticipated. This is the same brittleness embedding-based retrieval has everywhere, just harder to notice because the agent silently proceeds without the fact instead of erroring.

**Over-aggressive pruning/compaction erasing still-relevant facts**: summarization used to control store size can throw away a low-salience-looking detail that turns out to matter three sessions later — there's no way to know in advance which details will matter.

## The non-obvious

The write problem is harder than the read problem, and most teams build the read side first because it looks like the RAG problem they already know how to solve. In practice, the failure you'll spend the most time debugging is not "retrieval didn't find the right memory" but "the store is full of memories nobody should have written" — restating the same fact five ways, storing transient scratch reasoning as if it were durable knowledge, or never reconciling a correction against the original claim. A curated, deduplicated, explicitly-typed (episodic/semantic/procedural) store with a small number of high-value entries beats an "embed everything" store an order of magnitude larger, every time you actually measure end-task quality rather than recall@k in isolation.

It's also worth being precise about the boundary with [[Concept - Context Engineering for Agents]]: memory is the durable external store that survives across runs; context engineering is the separate discipline of managing what's currently loaded into the window *within* a run (compaction, offload, cache-friendly ordering). A system can have excellent memory and terrible context engineering, or vice versa — they fail independently and get debugged with different tools.

## Connections
- [[Concept - Tool Use and Function Calling]] — MemGPT-style memory is implemented as the model calling paging functions, reusing the tool-call interface for a self-editing store.
- [[Concept - Context Engineering for Agents]] — the sibling discipline: memory is the durable store, context engineering is what's loaded into the window right now; both fail independently.
- [[Concept - Embedding Models]] — the retrieval half of memory reuses embedding-based similarity search wholesale.
- [[Concept - HNSW]] — the approximate-nearest-neighbor index that makes memory retrieval fast at scale.
- [[Concept - Rerankers]] — an optional precision pass on top of raw embedding retrieval when memory recall is noisy.
- [[Deep Dive - The Agent Loop]] — memory is read and written at specific points in this loop; get the timing wrong and you either miss context or double-write.
- [[Deep Dive - RAG Architectures]] — the infrastructure agent memory borrows almost entirely, just with an agent-generated query instead of a user one.
- [[Concept - Context Rot]] — the failure mode memory is partly designed to route around: don't keep everything in-window, page it out and retrieve on demand.
- [[Concept - Prompt Caching]] — memory writes and retrievals that touch the transcript prefix can bust the cache if not appended carefully.
- [[Concept - Agentic Retrieval]] — the frontier version of memory lookup: the agent decides when and how to query its own store rather than a fixed retrieval pipeline running every turn.

## Sources
- Park et al. (2023) — "Generative Agents: Interactive Simulacra of Human Behavior." Introduces the recency/importance/relevance memory stream and periodic reflection.
- Packer et al. (2023) — "MemGPT: Towards LLMs as Operating Systems." OS-inspired virtual context management with model-driven paging via function calls; productized as Letta.
