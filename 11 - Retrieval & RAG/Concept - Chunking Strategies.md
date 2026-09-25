---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [document chunking, text splitting]
summary: "How documents get split into retrievable units — the index-time decision that caps retrieval quality before any model choice matters."
---
> **One-paragraph hook:** Before a document can be embedded and searched it has to be cut into pieces, and that cut is a one-way door. Whatever context lands on the wrong side of a chunk boundary is gone from that chunk's embedding for good. Teams routinely spend weeks tuning [[Concept - Embedding Models|embedding models]] and [[Concept - Rerankers|rerankers]] on top of a naive fixed-size splitter that caps the recall everything downstream is fighting for. Chunking is the most under-invested and highest-payoff decision in a [[Concept - Retrieval-Augmented Generation|RAG]] pipeline.

## The mechanism

The basic tension is size versus context. Small chunks give precise, focused embeddings: a 100-token chunk about one fact has an embedding that represents that fact cleanly. But they fragment context, and a chunk can lose the antecedent, the subject, or the qualifier a reader would need. Large chunks keep context but dilute the embedding. Mean-pooling (the standard for most encoders) averages a longer, more topically mixed sequence into one vector, blurring the fact a query is trying to match with everything else in the chunk. Large chunks also hit hard limits. Many BERT-based encoders cap at 512 tokens, and newer long-context embedders (Nomic, Jina v3) go to 8k, but going past the model's trained context silently truncates or degrades quality with no error.

Four broad strategies, from cheapest to most sophisticated at index time:

- **Fixed-size.** Split on a raw token or character count, with overlap. Simple, fast, blind to document structure. Most tutorials default to it, and most production systems should move past it.
- **Recursive character splitting.** Try paragraph breaks first, then line breaks, then sentence boundaries, then words, falling back to a harder split only when a chunk is still over budget. It respects natural structure without parsing it.
- **Structural.** Split along the document's real structure (Markdown/HTML headers, or a code file's AST at function/class boundaries), so a chunk never crosses a heading or cuts a function mid-body.
- **Semantic chunking.** Embed each sentence, measure cosine distance between consecutive sentence embeddings, and cut where the distance spikes (a "topic boundary" detector). It spread through Greg Kamradt's public notebooks and talks, not a peer-reviewed paper: *folklore, well-tested in practice but not formally benchmarked at the level BM25 or HNSW are.*

```
doc:  [para1][para2][para3][para4][para5]
                     |--- chunk A (overlap) ---|
                              |--- chunk B (overlap) ---|
```

A 10-20% overlap between adjacent chunks keeps a thought from being cut right at a boundary. You pay in duplicated storage and near-identical vectors in the index, which need handling downstream (deduplication, or accepting slightly redundant results).

## In practice

**Small-to-big / parent-document retrieval** separates the unit you search from the unit you generate with. Embed small, precise child chunks for search; when a child is retrieved, hand its larger parent chunk (or the whole section/document) to the generator. You get the benefits of both sizes and pay by tracking a parent-child mapping next to the index.

**Proposition-based / atomic chunking** (Chen et al. 2023, "Dense X Retrieval") goes further. An LLM breaks text into standalone factoids, self-contained propositions that make sense without surrounding sentences, and each proposition is indexed on its own. The embeddings are as clean as they get, but it costs an LLM call per chunk at index time, which adds up at corpus scale.

The oft-cited default of **256-512 tokens with modest overlap** is a reasonable starting point, not a universal optimum. The right size depends on the corpus (dense legal text vs. sparse chat logs), the embedder's effective context and pooling, and the query type: a fact lookup wants small precise chunks, "summarize this section" wants bigger ones. The only reliable way to choose is to sweep a few sizes against a real eval set (see [[Concept - RAG Evaluation]]) and measure recall@k. Don't trust a blog-post default.

Tables, code and long named entities are where naive splitters break, easy to miss in a demo and painful in production. A table split from its header row leaves every retrieved row uninterpretable (no column labels). A function split from its signature leaves the body ungrounded. Structural chunking exists to prevent this, and it's the standard example when teams debug "why is the answer wrong when the right row is clearly in the corpus?" The row was retrieved. Its header wasn't.

## Failure modes

- **Chunk-boundary amputation.** A table row without its header, a function without its signature, a clause without its governing sentence: the text is retrieved but can't be interpreted on its own. Fix with structural chunking or parent-document retrieval. Detect by inspecting a sample of retrieved chunks for self-containedness; checking that the right document came back isn't enough.
- **Oversized chunks dilute the embedding.** A chunk spanning three unrelated topics yields a mean-pooled vector that resembles none of them well, so a targeted query on any one topic scores it below a smaller, focused chunk. It shows up as depressed recall@k on multi-topic source documents.
- **Undersized chunks fragment meaning.** Pronouns, headers and qualifiers outside the boundary leave the chunk's embedding and content ambiguous or misleading on their own. [[Concept - Contextual Retrieval]] exists to patch this by re-injecting document-level context into each chunk.
- **Chunk size tuned once on a demo corpus and never revisited.** Production corpora change (new document types, longer documents, more tables), and a strategy that scored well on the original eval set degrades silently as the mix shifts. Re-run the sweep when corpus composition changes materially.

## The non-obvious

Teams reach for chunking last when it should usually come first. It's easy to underweight because it doesn't look like a "model choice": no leaderboard, no MTEB score, nothing to swap in a config file and A/B with a one-line change. So it gets a naive fixed-size default that's never revisited, while the tuning effort goes into the embedder and the [[Deep Dive - RAG Architectures|architecture]]. In practice, moving from a naive fixed-size splitter to a structural or semantic chunker on a real corpus routinely recovers more recall than switching to a better embedding model. A well-formed chunk is retrievable by *any* reasonable embedder. A badly formed one (header-less table row, decapitated function) is unretrievable by all of them.

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
