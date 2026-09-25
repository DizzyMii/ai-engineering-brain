---
tags: [concept, domain/retrieval-rag, level/surface]
aliases: [dense retrieval, vector search, nearest-neighbor search]
summary: "Retrieving by geometric proximity in a shared embedding space instead of by keyword overlap — the dense half of modern retrieval."
---
> **One-paragraph hook:** Semantic search maps queries and documents into one vector space and finds relevant results by distance, not shared words. "How do I cancel my subscription" retrieves a document that says "terminating your plan" though not one token matches. It's the mechanism under every embedding-based [[Concept - Retrieval-Augmented Generation]] system, and its whole failure surface (normalization, asymmetry, index approximation) stays invisible until it has cost you recall.

## The mechanism

An [[Concept - Embedding Models|embedding model]] maps a query $q$ and a document $d$ into the same $d$-dimensional real vector space. Relevance is then approximated by geometric proximity, most commonly **cosine similarity**:

$$\text{sim}(q, d) = \frac{q \cdot d}{\lVert q \rVert \, \lVert d \rVert}$$

That's a normalized dot product (a [[Concept - Matrix Multiplication as the Atom of Deep Learning|matrix multiply]] under the hood) measuring the angle between the vectors and ignoring magnitude. If both are pre-normalized to unit length ($\lVert q \rVert = \lVert d \rVert = 1$), cosine similarity and raw dot product are identical. So most production embedding models (E5, BGE, OpenAI's text-embedding-3) L2-normalize their outputs and serve indexes tuned for dot product or inner-product distance. Same number, cheaper than computing cosine per query.

Most engineers miss an asymmetry on first contact. **Symmetric** search (query and document are the same kind of text, as in semantic similarity between two sentences) is a different problem from **asymmetric** search (a short, terse query against a long, verbose passage, the standard RAG shape). Asymmetric retrieval needs the encoder to represent "what a question looks like" differently from "what an answer looks like." That's why E5 requires literal `"query: "` / `"passage: "` prefixes before encoding and BGE uses instruction strings for the same purpose. Encode a query without the prefix and the model treats it as a passage. The geometry is subtly off and recall drops with no error, no warning, no stack trace.

For $N$ vectors of dimension $d$, exact brute-force search costs $O(N \cdot d)$ per query: compute similarity to every vector and sort. It's exact, and on modern hardware fine up to roughly a million vectors. Past that, brute force becomes the latency bottleneck and you need an approximate index such as [[Concept - HNSW]], which gives up a little recall for search that's orders of magnitude faster.

```
def brute_force_search(query_vec, index, k):
    scores = [dot(query_vec, doc_vec) for doc_vec in index]  # O(N*d)
    return top_k(scores, k)  # exact; fine to ~1M vectors, then use ANN
```

## In practice

Semantic search's big win is closing the **vocabulary gap**. Synonyms, paraphrases and cross-lingual matches that share no tokens still land close together in embedding space, where lexical scoring (see [[Concept - BM25 and Lexical Retrieval]]) gives zero. Its big weakness is the mirror image. Exact identifiers, product SKUs, rare proper nouns and code symbols get blurred into their semantic neighborhood instead of matched precisely; an embedder happily puts `ERR_4471` next to `ERR_4470`. These complementary failures are the whole case for [[Concept - Hybrid Search and Reciprocal Rank Fusion]] over picking one arm and hoping.

At scale, production systems don't hand-roll brute force. They run one of the systems in [[Reference - Vector Database Landscape]] (pgvector, Qdrant, Weaviate, Pinecone and others), each wrapping an ANN index behind a query API with metadata filtering.

**Top-k** is a real tuning knob. Too small and you miss evidence the generator needed. Too large and you bloat the prompt with marginal or irrelevant passages, which costs tokens and triggers position-dependent degradation shaped like [[Concept - Context Rot]]: the model attends less to information buried in the middle of a long stuffed context than to what's near the edges.

## Failure modes

- **Unnormalized dot product leaks document length into relevance.** Longer documents tend to have larger-magnitude embeddings (more content summed into the pooled vector), so raw dot product over unnormalized vectors systematically favors long documents whatever their relevance. Normalize, or use cosine explicitly.
- **Silent asymmetric-prefix omission.** Forgetting `query:`/`passage:` prefixes (or the model's required instruction format) throws no error. Results just get worse, and the drop is easy to blame on "the embedding model isn't good enough" instead of a formatting bug. Detect with an A/B recall test on a labeled query set, prefix vs. no prefix.
- **Brute force past ~1M vectors.** Latency grows linearly with corpus size with no warning until p99 alarms fire in production. The fix, an ANN index, changes the recall/latency contract and needs its own tuning.
- **Similarity scores don't compare across models.** A cosine of 0.82 from one embedding model and 0.82 from another mean different things. Thresholds and "this is relevant" cutoffs are model-specific and need recalibrating whenever the embedder changes; [[Concept - Embedding Space Geometry]] covers this fully.

## The non-obvious

The most expensive semantic-search bug in production is a formatting bug that ships silently, not a bad model choice. Prefix omission degrades recall gradually and never errors, so teams routinely run for months with meaningfully worse retrieval than their embedding model can deliver, and find out only when someone runs a controlled recall comparison. Whenever you change embedding models, re-check the exact input format the model card specifies (prefix strings, instruction templates, max sequence length) against what your indexing and query code sends. Don't assume the new model's calling convention matches the old one.

## Connections

- [[Concept - Embedding Models]] — the component that produces the vectors this note's distance math operates on.
- [[Concept - HNSW]] — the dominant approximate index that makes semantic search fast past brute-force scale.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — combines semantic search with lexical retrieval to cover both of their complementary blind spots.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — cosine/dot-product similarity is literally a matmul, and its cost scaling follows the same rules.
- [[Concept - Retrieval-Augmented Generation]] — the primary consumer of semantic search results.
- [[Reference - Vector Database Landscape]] — where semantic search actually runs in production, with index and filtering tradeoffs.
- [[Concept - BM25 and Lexical Retrieval]] — the lexical retrieval mode whose failure cases are semantic search's strengths, and vice versa.
- [[Concept - Context Rot]] — explains why an oversized top-k doesn't just cost tokens but can actively hurt answer quality.
- [[Concept - Embedding Space Geometry]] — why raw similarity scores don't transfer across models or domains.

## Sources

- Karpukhin et al. (2020) — Dense Passage Retrieval for Open-Domain Question Answering. Established dual-encoder dense retrieval as competitive with and complementary to lexical search, the foundation modern semantic search builds on.
