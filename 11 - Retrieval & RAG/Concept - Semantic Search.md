---
tags: [concept, domain/retrieval-rag, level/surface]
aliases: [dense retrieval, vector search, nearest-neighbor search]
summary: "Retrieving by geometric proximity in a shared embedding space instead of by keyword overlap — the dense half of modern retrieval."
---
> **One-paragraph hook:** Semantic search maps queries and documents into the same vector space and finds relevant results by distance rather than by shared words, so "how do I cancel my subscription" retrieves a document that says "terminating your plan" even though not one token matches. It is the mechanism underneath every embedding-based [[Concept - Retrieval-Augmented Generation]] system, and its entire failure surface — normalization, asymmetry, index approximation — is invisible until it silently costs you recall.

## The mechanism

A query $q$ and a document $d$ are both mapped by an [[Concept - Embedding Models|embedding model]] into the same $d$-dimensional real vector space. Relevance is then approximated by geometric proximity, most commonly **cosine similarity**:

$$\text{sim}(q, d) = \frac{q \cdot d}{\lVert q \rVert \, \lVert d \rVert}$$

which is a normalized dot product — a [[Concept - Matrix Multiplication as the Atom of Deep Learning|matrix multiply]] under the hood — measuring the angle between the two vectors while ignoring their magnitude. If both vectors are pre-normalized to unit length ($\lVert q \rVert = \lVert d \rVert = 1$), cosine similarity and raw dot product become identical, which is why most production embedding models (E5, BGE, OpenAI's text-embedding-3) L2-normalize their outputs and serve indexes tuned for dot product or inner-product distance rather than computing cosine per query — it's the same number, cheaper to compute.

There is a critical asymmetry most engineers miss on first contact: **symmetric** search (query and document are the same kind of text, e.g. semantic textual similarity between two sentences) is a different problem from **asymmetric** search (a short, terse query against a long, verbose passage — the standard RAG shape). Asymmetric retrieval needs the encoder to represent "what a question looks like" differently from "what an answer looks like," which is why models like E5 require literal `"query: "` / `"passage: "` string prefixes before encoding, and BGE uses instruction strings for the same purpose. Encode a query without the prefix and the model treats it like a passage — the geometry is subtly wrong and recall drops with no error, no warning, no stack trace.

For $N$ vectors of dimension $d$, exact brute-force search costs $O(N \cdot d)$ per query — compute the similarity to every vector and sort. This is exact and, on modern hardware, entirely fine up to roughly a million vectors. Past that scale, brute force becomes the latency bottleneck and you need an approximate index — see [[Concept - HNSW]] — which trades a small amount of recall for orders-of-magnitude faster search.

```
def brute_force_search(query_vec, index, k):
    scores = [dot(query_vec, doc_vec) for doc_vec in index]  # O(N*d)
    return top_k(scores, k)  # exact; fine to ~1M vectors, then use ANN
```

## In practice

Semantic search's headline win is closing the **vocabulary gap**: synonyms, paraphrases, and cross-lingual matches that share no tokens still land close together in embedding space, which is exactly where lexical scoring (see [[Concept - BM25 and Lexical Retrieval]]) scores zero. Its headline weakness is the mirror image: exact identifiers, product SKUs, rare proper nouns, and code symbols get blurred into their semantic neighborhood rather than matched precisely — an embedder happily places `ERR_4471` near `ERR_4470`. This complementary failure pattern is the entire justification for [[Concept - Hybrid Search and Reciprocal Rank Fusion]] rather than picking one arm and hoping.

Production systems don't hand-roll brute force at scale; they run one of the systems catalogued in [[Reference - Vector Database Landscape]] (pgvector, Qdrant, Weaviate, Pinecone, and others), each wrapping an ANN index behind a query API with metadata filtering.

The **top-k** choice is a real tuning knob, not an afterthought: too small and you miss evidence the generator needed; too large and you bloat the prompt with marginal or irrelevant passages, which both costs tokens and triggers position-dependent degradation similar in shape to [[Concept - Context Rot]] — the model pays less attention to information buried in the middle of a long stuffed context than to what's near the edges.

## Failure modes

- **Unnormalized dot product leaks document length into relevance**: longer documents tend to have larger-magnitude embeddings (more content summed into the pooled vector), so raw dot product over unnormalized vectors systematically favors long documents regardless of actual relevance. Fix by normalizing, or explicitly using cosine.
- **Silent asymmetric-prefix omission**: forgetting `query:`/`passage:` prefixes (or the model's required instruction format) doesn't error — it just returns worse results, and the drop is easy to misattribute to "the embedding model isn't good enough" rather than a formatting bug. Detect with an A/B recall test on a labeled query set, prefix vs no-prefix.
- **Brute force past ~1M vectors**: latency degrades linearly with corpus size with no warning until p99 latency alarms fire in production; the fix (adopting an ANN index) changes the recall/latency contract and needs its own tuning.
- **Cross-model similarity scores are not comparable**: a cosine of 0.82 from one embedding model and 0.82 from another do not mean the same thing — thresholds and "this is relevant" cutoffs are model-specific and must be recalibrated whenever the embedder changes, a subtlety explored fully in [[Concept - Embedding Space Geometry]].

## The non-obvious

The single most expensive semantic-search bug in production isn't a bad model choice — it's a formatting bug that ships silently. Because asymmetric-prefix omission degrades recall gradually rather than causing an error, teams routinely run for months with meaningfully worse retrieval than their embedding model is capable of, only discovering the gap when someone finally runs a controlled recall comparison. The practical discipline this implies: whenever you change embedding models, re-verify the exact input format the model card specifies (prefix strings, instruction templates, max sequence length) against what your indexing and query code actually sends — don't assume the new model's calling convention matches the old one.

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
