---
tags: [decision, domain/retrieval-rag, level/core]
aliases: [RAG vs long context, retrieval vs context stuffing]
summary: "Default to RAG; reach for raw long-context stuffing only on small, bounded, infrequently-queried corpora — and combine both above that."
---
# Decision - RAG vs Long-Context Windows

> **The decision:** given a corpus and a query workload, should you retrieve relevant passages into a bounded prompt, or stuff the whole corpus into a long-context window and let attention do the work? **Default for the 80% case:** use [[Concept - Retrieval-Augmented Generation]] — most corpora are large, growing, and queried repeatedly enough that retrieval's cost and freshness advantages dominate, and the exceptions (small static corpora, one-off deep reads) are identifiable in advance.

## Decision flow

```mermaid
flowchart TD
    A["Does the full corpus fit under ~200k tokens?"] -->|No| RAG1["Use RAG"]
    A -->|Yes| B{"Query volume against this corpus?"}
    B -->|"Low / one-off read"| LC1["Long-context: raw stuffing is fine"]
    B -->|"High, same corpus repeated"| C{"Is the corpus static or rarely updated?"}
    C -->|"No — frequent updates"| RAG2["Use RAG — reindexing beats re-caching a moving target"]
    C -->|"Yes — static"| D{"Need per-claim attribution / citations?"}
    D -->|"Yes"| RAG3["Use RAG, or retrieve-then-long-context hybrid"]
    D -->|"No"| E["Long-context with prompt caching"]
    RAG1 --> F["Multi-hop / whole-doc reasoning needed? -> retrieve down to ~50k tokens, then long-context read"]
    E --> F
```

## Tradeoff matrix

| Criterion | RAG (retrieve + generate) | Long-context (raw stuffing) | Long-context (prompt-cached) | Hybrid (retrieve-then-stuff) |
|---|---|---|---|---|
| Corpus size ceiling | Effectively unbounded (index scales independently of window) | Bounded by the model's context window (order of 100k–1M+ tokens as of 2026) | Same window ceiling, but repeated reads amortize | Unbounded corpus, bounded window per query |
| Cost per query | Cheap embedding + ANN lookup (sub-cent, single-digit ms) plus generation over a small context | Full prefill cost over every token in the window, every call | Fresh-token cost paid once; cached-token reads priced far below fresh input (order of a 10x discount under schemes like Anthropic prompt caching, roughly similar under Gemini context caching) — *(as of 2026)* | Cheap retrieval cost plus prefill over the retrieved subset (tens of k tokens, not the whole corpus) |
| Latency (prefill) | Low — only retrieved tokens are prefilled | Scales with window size; a 200k-token prefill dominates end-to-end latency | Cache hit skips re-computation of the [[Concept - KV Cache]] for cached tokens, cutting effective prefill | Low-to-moderate — bounded by the retrieved-down size |
| Multi-fact accuracy | Curated evidence avoids diluting the model's attention with irrelevant tokens | Degrades on facts placed mid-window even well inside the nominal window (lost-in-the-middle) | Same degradation profile as raw stuffing — caching is a cost fix, not an accuracy fix | Retrieval curation plus long-context coherence on the retrieved subset |
| Freshness / updates | Reindex changed documents; index and generation stay decoupled | Every update invalidates the whole cached context, forcing a full re-cache | Same re-cache-on-update cost as raw long-context | Reindex changed documents; no context re-cache needed |
| Attribution / citations | Native — you know exactly which chunk supported which claim | Weak — the model must self-report which part of a huge blob it used | Same weakness as raw long-context | Native, inherited from the retrieval step |
| Engineering complexity | Higher: chunking, embedding, index, [[Concept - Rerankers|reranking]] pipeline | Lower: no index to build or maintain | Lower, plus cache-key/session management | Highest: both a retrieval pipeline and a long-context budget to manage |

## The details that flip the decision

- **Multi-hop, whole-document reasoning** where no single chunk contains the answer (e.g. "summarize how this contract's obligations change across all twelve amendments") favors long-context or a retrieve-then-stuff hybrid over naive top-$k$ RAG, because the evidence is distributed rather than localized — the query type, not just corpus size, determines the winner.
- **Regulatory or compliance need for per-claim citation** flips the decision toward RAG even on a corpus small enough to fit in-window, because attribution requires knowing which specific passage backed which specific claim — something raw long-context generation cannot guarantee without an additional extraction step.
- **Spiky, repeated-read access patterns** — the same large document read thousands of times a day (a support macro, a product spec) — is where prompt caching most changes the math: [[Concept - Prompt Caching]] amortizes the fixed prefill cost across all repeated reads, narrowing the cost gap with RAG even at large context sizes. It narrows the gap; it does not eliminate lost-in-the-middle.
- **Continuously growing corpora** (a live ticket system, a document store with daily uploads) favor RAG structurally: reindexing new documents is cheap and incremental, while re-caching an ever-changing long-context blob means the cache invalidates constantly and you're paying fresh-prefill cost on every update anyway.
- **Reasoning-model interaction**: chain-of-thought output tokens compound on top of whatever input tokens were paid for prefill, so stuffing a large window into a reasoning model multiplies rather than adds to the cost delta versus RAG — see [[Concept - Cost Engineering for LLM Applications]] for the full accounting.

The mature 2026 synthesis is not either/or: retrieve down from an unbounded corpus to a bounded budget (order of tens of thousands of tokens) and then hand that curated subset to a long-context model, rather than either pure top-3-chunk RAG or raw whole-corpus stuffing — retrieval feeds the window instead of competing with it.

## Connections

- [[Concept - Retrieval-Augmented Generation]] — the retrieval-side alternative this decision is choosing between; assumes the reader already knows the RAG loop.
- [[Decision - Fine-Tuning vs RAG vs Prompting]] — the adjacent decision on whether to bake knowledge into weights at all, upstream of this retrieve-vs-stuff choice.
- [[Concept - Context Rot]] — the mechanism behind why raw long-context stuffing degrades even within the nominal window, not just beyond it.
- [[Concept - Prompt Caching]] — the specific economics that narrow, but do not close, long-context's cost disadvantage against RAG.
- [[Concept - KV Cache]] — why prefill cost scales with context length in the first place: every token adds an entry to the cache that attention must read.
- [[Concept - Cost Engineering for LLM Applications]] — the general framework for computing the break-even point between these options for a specific workload.
- [[Lore - The RAG Is Dead Debate]] — the recurring folklore claim this decision note is the sober, mechanism-level answer to.

## Sources

- Liu et al. (2023) — Lost in the Middle: How Language Models Use Long Contexts. Established that recall degrades for information placed mid-context even well within the nominal window, the empirical basis for RAG's multi-fact accuracy advantage over raw stuffing.
- Google DeepMind (2024) — Gemini 1.5 Technical Report. The near-perfect single-needle-in-a-haystack results that fueled the "long context replaces RAG" argument this decision weighs against real multi-fact workloads.
