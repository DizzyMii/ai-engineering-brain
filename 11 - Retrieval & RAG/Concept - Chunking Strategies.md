---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [document chunking, text splitting]
summary: "How documents get split into retrievable units — the index-time decision that caps retrieval quality before any model choice matters."
---
> **One-paragraph hook:** Before a document can be embedded and searched, it has to be cut into pieces, and that cut is a one-way door: whatever context falls on the wrong side of a chunk boundary is gone from that chunk's embedding forever. Teams routinely spend weeks tuning [[Concept - Embedding Models|embedding models]] and [[Concept - Rerankers|rerankers]] while running a naive fixed-size splitter that quietly caps the recall ceiling everything downstream is fighting against — chunking is the most under-invested, highest-leverage decision in a [[Concept - Retrieval-Augmented Generation|RAG]] pipeline.

## The mechanism

The fundamental tension is size versus context. Small chunks produce precise, focused embeddings — a 100-token chunk about one specific fact has an embedding that represents that fact cleanly — but they fragment context, so a chunk can lose the antecedent, the subject, or the surrounding qualifier a reader would need. Large chunks preserve context but dilute the embedding signal: mean-pooling (the standard pooling strategy for most encoders) averages a longer, more topically diverse sequence into one vector, blurring the specific fact a query is trying to match against everything else in the chunk. Large chunks also run into hard limits — many BERT-based encoders cap at 512 tokens, while newer long-context embedders (Nomic, Jina v3) extend to 8k, but exceeding the model's trained context silently truncates or degrades quality rather than erroring.

There are four broad strategies, in increasing order of sophistication and index-time cost:

- **Fixed-size** — split on a raw token or character count with overlap. Simple, fast, and blind to document structure; the default most tutorials use and the default most production systems should graduate past.
- **Recursive character splitting** — try to split on paragraph breaks first, then line breaks, then sentence boundaries, then words, only falling back to a harder split when a chunk still exceeds the size budget. This respects natural document structure without needing to parse it.
- **Structural** — split along the document's actual structure: Markdown/HTML headers, or a code file's AST (function/class boundaries), so a chunk never crosses a heading or splits a function mid-body.
- **Semantic chunking** — embed individual sentences, measure the cosine distance between consecutive sentence embeddings, and cut where the distance spikes (a "topic boundary" detector). This approach circulated widely through Greg Kamradt's public notebooks and talks rather than a peer-reviewed paper — *folklore, well-tested in practice but not formally benchmarked at the level BM25 or HNSW are.*

```
doc:  [para1][para2][para3][para4][para5]
                     |--- chunk A (overlap) ---|
                              |--- chunk B (overlap) ---|
```

A 10-20% overlap between adjacent chunks avoids severing a thought exactly at a chunk boundary — the price is duplicated storage and duplicate near-identical vectors in the index, which needs handling downstream (deduplication, or accepting slightly redundant results).

## In practice

**Small-to-big / parent-document retrieval** decouples the unit you search from the unit you generate with: embed small, precise child chunks for search precision, but when a child chunk is retrieved, return its larger parent chunk (or the whole section/document) to the generator for context. This gets you the best of both sizes at the cost of tracking a parent-child mapping alongside the index.

**Proposition-based / atomic chunking** (Chen et al. 2023, "Dense X Retrieval") goes further: an LLM decomposes text into standalone factoids — self-contained propositions that don't depend on surrounding sentences to make sense — and each proposition becomes its own indexed unit. This produces the cleanest possible embeddings but costs an LLM call per chunk at index time, a real expense at corpus scale.

The oft-cited default of **256-512 tokens with modest overlap** is a reasonable starting point, not a universal optimum — the right chunk size depends on the corpus (dense legal text vs. sparse chat logs), the embedder's effective context and pooling behavior, and the query type (a fact-lookup query wants small precise chunks; a "summarize this section" query wants larger ones). The only reliable way to pick a size is to sweep a few options against a real eval set (see [[Concept - RAG Evaluation]]) and measure recall@k, not to trust a blog-post default.

Tables, code, and long named entities are where naive splitters break in a way that's easy to miss in a demo and painful in production: a table split from its header row leaves every retrieved row uninterpretable (no column labels), and a function split from its signature leaves the body ungrounded. This is exactly the failure structural chunking exists to prevent, and it's the canonical example teams cite when debugging "why does the model give a wrong answer even though the right row is clearly in the corpus" — the row was retrieved, but its header wasn't.

## Failure modes

- **Chunk-boundary amputation**: a table row without its header, a code function without its signature, a clause without its governing sentence — the retrieved text is technically present but uninterpretable in isolation. Fix with structural chunking or parent-document retrieval; detect by manually inspecting a sample of retrieved chunks for self-containedness, not just checking whether the right document was retrieved.
- **Oversized chunks dilute the embedding signal**: a chunk that spans three unrelated topics produces a mean-pooled vector that resembles none of them well, so a targeted query on any one topic scores it lower than a smaller, focused chunk would — measured as depressed recall@k on multi-topic source documents.
- **Undersized chunks fragment meaning**: pronouns, headers, and qualifiers that live outside the chunk boundary make the chunk's embedding and its content ambiguous or misleading on its own — the same root problem [[Concept - Contextual Retrieval]] exists specifically to patch by re-injecting document-level context per chunk.
- **Chunk size tuned once on a demo corpus and never revisited**: production corpora evolve (new document types, longer documents, more tables) and a chunking strategy that scored well on the original eval set silently degrades as the corpus mix shifts — re-run the eval sweep when the corpus composition changes materially.

## The non-obvious

Chunking is the retrieval-quality lever teams reach for last, when it should usually be reached for first. It's easy to underweight because it doesn't look like a "model choice" — there's no leaderboard, no MTEB score, nothing to swap in a config file and A/B test with one line changed — so it gets a naive fixed-size default and never revisited while all the tuning effort goes into the embedder and the [[Deep Dive - RAG Architectures|architecture]]. In practice, moving from a naive fixed-size splitter to a structural or semantic chunker on a real corpus routinely recovers more recall than swapping to a better embedding model, because a well-formed chunk is retrievable by *any* reasonable embedder, while a badly-formed chunk (header-less table row, decapitated function) is unretrievable by all of them regardless of model quality.

## Connections

- [[Concept - Contextual Retrieval]] — patches the context-fragmentation failure by prepending document-level context to each chunk rather than relying on chunk boundaries alone.
- [[Concept - Embedding Models]] — the chunk size decision is bounded by, and interacts with, the embedder's max sequence length and pooling behavior.
- [[Concept - Rerankers]] — a reranker can fix a noisy top-k but cannot recover information that a bad chunk boundary already discarded.
- [[Concept - Retrieval-Augmented Generation]] — chunking is the index-time decision every RAG pipeline's retrieval quality is ultimately bounded by.
- [[Concept - Byte-Pair Encoding]] — chunk size is measured in tokens, and tokenizer behavior (how a BPE vocabulary splits your specific text) determines what "512 tokens" actually covers.
- [[Deep Dive - RAG Architectures]] — chunking is the first step of the index-time pipeline every RAG architecture variant builds on top of.
- [[Gotchas - RAG Pipelines]] — chunk-boundary amputation and oversized-chunk dilution are catalogued there alongside the rest of the pipeline's failure surface.
- [[Concept - RAG Evaluation]] — the only reliable method for choosing a chunk size and strategy is measuring recall@k against a golden set, not guessing.
- [[Concept - Semantic Search]] — the retrieval mechanism whose precision is directly gated by how well-formed the indexed chunks are.
- [[Concept - Text Extraction from Web Pages]] — chunking operates on whatever text extraction already produced, so extraction artifacts (broken tables, lost structure) become chunking problems downstream.
- [[Playbook - Building a Production RAG System]] — walks through picking and validating a chunking strategy as an early, load-bearing step in the build order.

## Sources

- Chen et al. (2023) — Dense X Retrieval: What Retrieval Granularity Should We Use? Introduces proposition-based (atomic factoid) chunking and shows granularity materially changes retrieval quality.
- folklore, weakly sourced: Greg Kamradt's semantic chunking method (embed sentences, split at cosine-distance breakpoints) circulated through public notebooks and talks rather than a peer-reviewed paper, but is widely implemented (e.g. in LangChain's semantic chunker).
