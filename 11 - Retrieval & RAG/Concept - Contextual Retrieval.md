---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [contextual embeddings, contextual BM25, Anthropic Contextual Retrieval, late chunking]
summary: "Prepending LLM-generated document context to each chunk before indexing, made viable by prompt caching, to fix the isolated-chunk problem."
---
> **One-paragraph hook:** A chunk that reads "revenue grew 3% over the previous quarter" is useless the moment it loses which company and which quarter it's talking about — and that information usually lived in a sentence two paragraphs earlier that [[Concept - Chunking Strategies|chunking]] cut away. Contextual retrieval re-attaches that missing context to every chunk, before it ever gets embedded or indexed, turning a silent ranking failure into a fixable index-time cost.

## The mechanism

Chunking is a one-way door: whatever context falls on the wrong side of a chunk boundary is gone from that chunk's representation, both its embedding vector and its lexical terms. A chunk about "the third amendment" with no antecedent naming the contract, or a financial figure with no company or quarter attached, retrieves poorly under both dense and lexical search — not because the retrieval mechanism is broken, but because the chunk itself no longer contains what a reader (or an embedder) needs to know it's relevant.

Anthropic's **Contextual Retrieval** (2024) fixes this at index time: for every chunk, feed the *entire source document* plus that specific chunk to an LLM, and have it generate a short (50-100 token) contextual blurb — e.g. "This chunk is from ACME Corp's Q2 2023 10-K filing, in the section discussing overall revenue growth for the quarter" — then **prepend that blurb to the chunk before both embedding it and indexing it into [[Concept - BM25 and Lexical Retrieval|BM25]]**. Both retrieval arms get fixed, not just the semantic one: the embedding now carries the disambiguating context, and the literal company name and quarter now exist as searchable BM25 terms that the raw chunk never had.

The economics are what make this practical rather than merely correct. Naively, generating context for every chunk means resending the entire source document to the LLM once per chunk — for a document with 200 chunks, that is 200x the document's token count in a single indexing pass. **Prompt caching** (Anthropic's prompt caching, Gemini's context caching) is what closes that gap: the document body is cached once, and every subsequent per-chunk context-generation call reads that cached prefix at a steep discount over fresh-token pricing, bringing the effective cost down to roughly the order of a few dollars per million document tokens processed. Contextual Retrieval is downstream of a serving-layer feature, not a modeling insight — it was economically infeasible at corpus scale before extended prompt caching existed, and became a standard recommendation once it did.

Anthropic's own reported numbers: contextual embeddings alone cut retrieval failure rate by roughly 35%; adding contextual BM25 on top brings that to roughly 49%; adding a [[Concept - Rerankers|reranker]] on top of both brings it to roughly 67% — each stage of the stack (context, hybrid, rerank) compounding rather than substituting for the others.

An alternative mechanism, **late chunking** (Jina AI, 2024), gets a similar effect without any extra LLM calls: embed the *entire* long document once with a long-context encoder (so every token's embedding already carries full-document attention context), and only *then* mean-pool per chunk boundary from those already-contextualized token embeddings. The chunk boundary is applied after contextualization instead of before it, so no chunk's embedding is ever computed in isolation. It is cheaper than the LLM-blurb approach but only fixes the dense arm — there is no analogue that helps BM25, since BM25 needs the literal disambiguating tokens physically present in the indexed text, and only requires the document to fit a genuinely long-context embedding model (8k+ tokens) to have anything to attend over.

## In practice

Contextual retrieval is worth the index-time LLM cost on high-value corpora — legal contracts, financial filings, technical documentation — where a retrieval miss is expensive and the corpus is large enough that manual chunk curation isn't feasible, but not worth it on small or low-stakes corpora where the extra indexing cost isn't repaid. It composes naturally with parent-document/small-to-big chunking and with a full hybrid-search-plus-rerank stack — Anthropic's own recommendation is to layer all of it, since each stage's gain is measured as additive on top of the others, not as alternatives.

## Failure modes

- **Cache-miss cost blowup**: if chunks for the same document aren't processed sequentially and within the cache TTL, or documents are reprocessed out of order, the cache prefix never hits and every chunk pays full fresh-token pricing. Symptom: index-build costs land 5-10x over the estimate. Fix by batching all of a document's chunk-context calls together, in order, inside the cache window.
- **Blurb hallucination**: the LLM invents context not actually present in the document (wrong quarter, wrong party to a contract), silently corrupting both the embedding and the BM25 terms with plausible-looking but false disambiguation. Fix by grounding the context-generation prompt strictly to the provided document text and spot-checking a sample against source.
- **Applying it to already-atomic chunks**: FAQ entries, short structured records, or anything that's already self-contained gains nothing from added context and just pays the LLM cost for no recall improvement — check whether the [[Gotchas - RAG Pipelines|isolated-chunk problem]] actually exists in this corpus before adopting the technique wholesale.
- **Late chunking without a genuinely long-context embedder**: choosing late chunking as the cheaper alternative but pairing it with a model whose effective context is shorter than the documents being processed defeats the entire mechanism — the token embeddings never actually see the parts of the document that would have disambiguated the chunk.

## The non-obvious

Contextual BM25 usually matters more in practice than contextual embeddings alone for entity- and number-heavy corpora — financial filings, legal contracts, anything organized around proper nouns and dates — precisely because BM25 needs the literal disambiguating token (the company name, the exact date) present in the index to ever match it, while a dense embedder trained on broad web text has often already partially absorbed some topical context from pretraining and degrades more gracefully. The two retrieval arms fail differently, so they need to be fixed differently, and a team that only patches the embedding side because "we're doing semantic search" is leaving roughly half of Anthropic's reported gain on the table.

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
