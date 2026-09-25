---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [contextual embeddings, contextual BM25, Anthropic Contextual Retrieval, late chunking]
summary: "Prepending LLM-generated document context to each chunk before indexing, made viable by prompt caching, to fix the isolated-chunk problem."
---
> **One-paragraph hook:** A chunk that reads "revenue grew 3% over the previous quarter" is useless once it loses which company and which quarter it means, and that information usually sat in a sentence two paragraphs up that [[Concept - Chunking Strategies|chunking]] cut away. Contextual retrieval re-attaches the missing context to every chunk before it's embedded or indexed. A silent ranking failure becomes a fixable index-time cost.

## The mechanism

Chunking is a one-way door. Whatever context falls on the wrong side of a boundary is gone from that chunk's representation, both its embedding vector and its lexical terms. A chunk about "the third amendment" with nothing naming the contract, or a financial figure with no company or quarter, retrieves poorly under both dense and lexical search. The retrieval mechanism works fine; the chunk just no longer contains what a reader (or an embedder) needs to see that it's relevant.

Anthropic's **Contextual Retrieval** (2024) fixes this at index time. For each chunk, give an LLM the *entire source document* plus that chunk and have it write a short (50-100 token) contextual blurb, e.g. "This chunk is from ACME Corp's Q2 2023 10-K filing, in the section discussing overall revenue growth for the quarter." Then **prepend the blurb to the chunk before embedding it and before indexing it into [[Concept - BM25 and Lexical Retrieval|BM25]]**. Both arms improve, dense and BM25. The embedding carries the disambiguating context, and the literal company name and quarter become searchable BM25 terms the raw chunk never had.

The economics make it practical. Done naively, generating context per chunk means resending the whole source document once per chunk: for a document with 200 chunks, that's 200x the document's token count in one indexing pass. **Prompt caching** (Anthropic's prompt caching, Gemini's context caching) closes the gap. The document body is cached once, and each per-chunk call reads that cached prefix at a steep discount over fresh-token pricing, bringing the effective cost to roughly a few dollars per million document tokens processed. So Contextual Retrieval rests on a serving-layer feature more than a modeling insight. It was economically infeasible at corpus scale before extended prompt caching existed and became a standard recommendation once it did.

Anthropic's reported numbers: contextual embeddings alone cut retrieval failure rate by roughly 35%. Adding contextual BM25 brings that to roughly 49%, and adding a [[Concept - Rerankers|reranker]] on top of both brings it to roughly 67%. Each stage (context, hybrid, rerank) compounds with the others instead of replacing them.

**Late chunking** (Jina AI, 2024) gets a similar effect with no extra LLM calls. Embed the *entire* long document once with a long-context encoder, so every token embedding already carries full-document attention context, and *then* mean-pool per chunk boundary from those contextualized token embeddings. The boundary is applied after contextualization, so no chunk's embedding is ever computed in isolation. It's cheaper than the LLM-blurb approach but only fixes the dense arm. Nothing comparable helps BM25, which needs the literal disambiguating tokens physically present in the indexed text. It also requires the document to fit in a long-context embedding model (8k+ tokens) so there's something to attend over.

## In practice

Contextual retrieval earns its index-time LLM cost on high-value corpora (legal contracts, financial filings, technical documentation) where a miss is expensive and the corpus is too large for manual chunk curation. On small or low-stakes corpora the extra indexing cost doesn't pay back. It composes with parent-document/small-to-big chunking and with a full hybrid-search-plus-rerank stack. Anthropic recommends layering all of it, since each stage's measured gain adds on top of the others.

## Failure modes

- **Cache-miss cost blowup.** If a document's chunks aren't processed in sequence within the cache TTL, or documents are reprocessed out of order, the cached prefix never hits and every chunk pays full fresh-token pricing. Symptom: index builds land 5-10x over estimate. Fix: batch all of a document's chunk-context calls together, in order, inside the cache window.
- **Blurb hallucination.** The LLM invents context that isn't in the document (wrong quarter, wrong party to a contract), corrupting both the embedding and the BM25 terms with plausible but false disambiguation. Fix: ground the prompt strictly in the provided document text and spot-check a sample against source.
- **Applying it to already-atomic chunks.** FAQ entries, short structured records, anything already self-contained gains nothing from added context and just pays the LLM cost. Check that the [[Gotchas - RAG Pipelines|isolated-chunk problem]] exists in your corpus before adopting the technique wholesale.
- **Late chunking without a long-context embedder.** Pairing late chunking with a model whose effective context is shorter than your documents defeats the mechanism. The token embeddings never see the parts of the document that would have disambiguated the chunk.

## The non-obvious

For entity- and number-heavy corpora (financial filings, legal contracts, anything built around proper nouns and dates), contextual BM25 usually matters more than contextual embeddings alone. BM25 can only match the literal disambiguating token (the company name, the exact date) if it's in the index. A dense embedder trained on broad web text has often already absorbed some topical context from pretraining and degrades more gracefully. The two arms fail differently and need different fixes, and a team that only patches the embedding side because "we're doing semantic search" leaves roughly half of Anthropic's reported gain on the table.

## Connections

- [[Concept - Chunking Strategies]] — the index-time decision that creates the isolated-chunk problem contextual retrieval exists to patch after the fact.
- [[Concept - Prompt Caching]] — the specific serving-layer economics that turned this from a theoretically-correct but too-expensive idea into a practical default.
- [[Concept - Rerankers]] — the third, compounding stage of Anthropic's stack; contextual embeddings, contextual BM25, and reranking each add independent gain on top of the others.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — contextual BM25 only matters because the lexical arm of hybrid search is still in the pipeline at all.
- [[Concept - Embedding Models]] — contextual retrieval changes what gets fed into the embedder, not the embedder itself.
- [[Deep Dive - RAG Architectures]] — contextual retrieval is a pre-indexing enrichment stage in the broader RAG-architecture taxonomy.
- [[Gotchas - RAG Pipelines]] — chunk-boundary context loss is cataloged there as one of the standard silent retrieval failures.
- [[Concept - Cost Engineering for LLM Applications]] — the index-time LLM cost this technique introduces is a real, budgetable line item, not free.
- [[Concept - Learned Sparse Retrieval]] — SPLADE's term expansion fixes the same underlying vocabulary-mismatch problem contextual BM25 targets, but by learning expansion terms rather than prepending an LLM-written blurb.

## Sources

- Anthropic (2024) — Introducing Contextual Retrieval. Contextual embeddings, contextual BM25, and the measured 35%/49%/67% failure-rate reductions from stacking each stage.
- Jina AI (2024) — Late Chunking in Long-Context Embedding Models. The alternative embed-first, chunk-after mechanism that avoids extra LLM calls.
