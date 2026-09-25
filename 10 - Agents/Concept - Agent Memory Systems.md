---
tags: [concept, domain/agents, level/advanced]
aliases: [agent memory, long-term memory for agents, MemGPT-style memory]
summary: "How agents persist state past the context window: episodic/semantic/procedural stores, scored retrieval, and the hard write-policy problem."
---
> **One-paragraph hook:** An agent's context window is a whiteboard wiped every session; memory is the filing cabinet beside it. The cabinet itself is the easy part. The engineering is in deciding what goes in, how it's indexed, and how a stale or contradictory page gets pulled out three weeks later and presented as current fact.

## The mechanism

Agent memory splits along two axes. The first is duration. **Short-term/working memory** is the context window, whatever tokens are loaded right now, and it's gone when the session ends or the window fills. **Long-term memory** is an external store that survives across sessions and has to be written to and read from explicitly. The second axis is content type, borrowed from cognitive science: **episodic** memory (specific past interactions, "the user asked about X on Tuesday"), **semantic** memory (facts about the world or the user, without when or where they were learned) and **procedural** memory (skills and how-to knowledge, "the deploy script needs `--force` on this repo").

Two systems define how it works in practice. **Generative Agents** (Park et al. 2023) introduced the *memory stream*. Every observation is stored as a timestamped natural-language entry, and retrieval combines three signals into one score:

$$\text{score} = \alpha_{\text{recency}} \cdot \text{recency} + \alpha_{\text{importance}} \cdot \text{importance} + \alpha_{\text{relevance}} \cdot \text{relevance}$$

Recency is an exponential decay over hours since last access. Importance is a 1–10 "poignancy" score the LLM itself assigns at write time. Relevance is cosine similarity between the query embedding and the memory's embedding (the same machinery as [[Concept - Embedding Models]], with [[Concept - HNSW]] for the index). The paper also runs periodic *reflection*: every so often the agent summarizes clusters of recent memories into higher-level insights, and those synthesized memories become retrievable too. It's a crude form of consolidation.

**MemGPT**, later productized as Letta (Packer et al. 2023), borrows from operating systems instead. The model has a small, fixed *main context* (like RAM) and unbounded *external context*, recall storage and archival storage (like disk). The model doesn't passively receive retrieved memories. It pages data in and out itself by calling functions (`core_memory_append`, `archival_memory_search`, `conversation_search`) exposed as tools, the same interface as in [[Concept - Tool Use and Function Calling]]. That's a different design axis: in Generative Agents retrieval is a fixed pipeline the harness runs every turn, and in MemGPT it's a decision the model makes.

## In practice

Memory retrieval reuses RAG infrastructure wholesale: an embedding index, approximate nearest-neighbor search, sometimes a reranking pass ([[Concept - Rerankers]]). The query comes from the agent instead of a user, though, and that changes its statistics. It tends to be more templated, repeats more across turns, and caches more easily. When the retrieval step itself needs to be adaptive instead of a fixed top-k call, this merges with [[Concept - Agentic Retrieval]]: memory lookup becomes another tool the agent decides when and how to use, where the simpler design injects it unconditionally every turn.

In production the harder problem is almost never retrieval. It's the **write policy**. Deciding what's worth storing, deduplicating near-identical entries, and reconciling contradictions (the user's stated preference changed, so which version is current?) is unsolved in general. Teams that embed every tool call and message verbatim end up with a store where cosine similarity pulls up plausible but low-signal noise, because nobody ever curated the store for retrievability.

## Failure modes

**Memory bloat.** Unbounded write policies grow the store faster than any query needs. Retrieval precision drops (more near-duplicate distractors) and cost rises (bigger index, more embedding calls). Detection: compare store growth rate with distinct-fact growth rate. If they diverge, you're storing redundancy.

**Stale or contradictory memories surfacing.** Without invalidation, an old fact ("user is on the free tier") outranks a newer one on relevance and gets served as current. Detection: memories with no expiry or supersession field and no write-time conflict check are a smell. The symptom is the agent confidently asserting something the user just corrected.

**Retrieval misses on paraphrase.** Embedding similarity tolerates wording changes, but not perfectly. A memory phrased "deploys fail on Fridays" may not come up for "why did the release break", because the surface forms diverge more than the embedding model's training distribution anticipated. Embedding retrieval is this brittle everywhere; it's just harder to spot here because the agent carries on silently without the fact instead of erroring.

**Over-aggressive pruning or compaction erasing facts that still matter.** Summarization used to keep the store small can drop a detail that looked unimportant and turns out to matter three sessions later. You can't know in advance which details those will be.

## The non-obvious

Writing is harder than reading, and most teams build the read side first because it looks like the RAG problem they already know. The failure you'll spend the most time debugging is "the store is full of memories nobody should have written", not "retrieval didn't find the right memory": the same fact stored five ways, transient scratch reasoning saved as durable knowledge, a correction never reconciled against the original claim. A curated, deduplicated store with explicit types (episodic/semantic/procedural) and a small number of high-value entries beats an embed-everything store an order of magnitude larger, every time you measure end-task quality instead of recall@k in isolation.

Be precise about the boundary with [[Concept - Context Engineering for Agents]]. Memory is the durable external store that survives across runs. Context engineering manages what's loaded into the window *within* a run (compaction, offload, cache-friendly ordering). A system can have excellent memory and terrible context engineering or the reverse. They fail independently and you debug them with different tools.

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
