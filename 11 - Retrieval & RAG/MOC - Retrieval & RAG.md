---
tags: [moc, domain/retrieval-rag, level/surface]
aliases: []
summary: "Map of Retrieval & RAG: embeddings, lexical and hybrid search, vector indexes, rerankers, chunking, and production RAG architecture."
---

# MOC - Retrieval & RAG

This domain owns how a model gets fed facts it wasn't trained on: turning documents into retrievable units, embedding or indexing them, finding the right ones at query time, and assembling them into context an LLM can actually use. It matters because a frozen model's knowledge is fixed at training time and its context window is finite and expensive, so retrieval is the mechanism that supplies fresh, proprietary, or long-tail information without a fine-tune. The notes here run from the surface definition of RAG and semantic search through the core mechanics of embeddings, BM25, chunking, and hybrid fusion, into advanced territory — ANN index internals, rerankers, contextual retrieval, full production architectures — and out to frontier and unicorn material on agentic retrieval, GraphRAG, embedding geometry pathologies, and the perennial "RAG is dead" debate. Retrieval quality is a ceiling on generation quality: a perfect generator fed the wrong context still produces a wrong answer, which is why this domain treats retrieval and generation as separately measurable problems.

## Start here

- **Surface** → [[Concept - Retrieval-Augmented Generation]] — the core idea: augment a frozen LLM with retrieved external context at inference time instead of retraining it.
- **Core** → [[Concept - Embedding Models]] — the dual-encoder machinery that turns text into vectors so relevance becomes geometric proximity, underlying most of the rest of this domain.
- **Advanced** → [[Deep Dive - RAG Architectures]] — the taxonomy of system designs from naive to modular to agentic to graph, and how to pick a point on that spectrum.
- **Frontier** → [[Concept - Agentic Retrieval]] — retrieval driven by the model's own decisions about whether, what, and when to retrieve, instead of a fixed pipeline.
- **Unicorn** → [[Concept - Embedding Space Geometry]] — the geometric pathologies (anisotropy, hubness, dimensional collapse) that silently degrade dense retrieval even when everything looks correct.

## Foundations

- [[Concept - Retrieval-Augmented Generation]] — augmenting a frozen LLM with retrieved external context at inference time to cut hallucination and inject fresh or proprietary knowledge.
- [[Concept - Semantic Search]] — retrieving by geometric proximity in a shared embedding space instead of by keyword overlap, the dense half of modern retrieval.

## Embeddings and representation learning

- [[Concept - Embedding Models]] — dual-encoder transformers trained to map text into a vector space where retrieval relevance becomes geometric proximity.
- [[Concept - Contrastive Learning for Text Embeddings]] — the InfoNCE objective that pulls matching query-document pairs together and pushes everything else apart, making cosine similarity a valid ranking signal.
- [[Concept - Hard Negative Mining]] — selecting semantically-close-but-wrong training negatives to sharpen retrieval embeddings, and the false-negative trap that silently ruins it.
- [[Concept - Matryoshka Representation Learning]] — training embeddings so every leading prefix of the vector is itself valid, giving one model many operating points on cost versus accuracy.
- [[Concept - Embedding Space Geometry]] — the geometric pathologies — anisotropy, hubness, dimensional collapse, cross-model cosine incomparability — that silently degrade dense retrieval.
- [[Concept - Embedding Quantization]] — compressing embedding vectors to int8 or binary for 4-32x cheaper storage and faster search, with a rescore pass that recovers most of the recall.

## Lexical, sparse, and hybrid retrieval

- [[Concept - BM25 and Lexical Retrieval]] — BM25 scores documents by saturating term frequency and weighting by rarity, the decades-old baseline that still wins on exact match.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — fusing lexical and dense retrieval by rank, not score, so exact-match and semantic recall combine without a fragile normalization step.
- [[Snippet - Reciprocal Rank Fusion]] — a complete, runnable Python implementation of RRF for merging BM25 and dense retrieval result lists.
- [[Concept - Learned Sparse Retrieval]] — neural models that emit sparse, vocabulary-indexed weight vectors, serving on ordinary inverted indexes while learning term expansion and semantics.
- [[Concept - Late Interaction and ColBERT]] — token-level multi-vector retrieval scored via MaxSim, sitting between bi-encoders and cross-encoders on the cost/precision curve.

## Chunking and vector indexing

- [[Concept - Chunking Strategies]] — how documents get split into retrievable units, the index-time decision that caps retrieval quality before any model choice matters.
- [[Concept - HNSW]] — the layered proximity-graph ANN index that turns nearest-neighbor search into O(log N) greedy hops, the default in-memory vector index.
- [[Concept - IVF and Product Quantization]] — cluster-and-compress ANN: IVF prunes the search to nearby cells, PQ shrinks each vector to a handful of bytes, FAISS's billion-scale workhorse.
- [[Breakdown - DiskANN]] — Microsoft's SSD-resident ANN index (the Vamana graph) that serves billion-scale nearest-neighbor search from disk on a single node.
- [[Reference - Vector Database Landscape]] — comparison matrix of production vector search systems by index type, filtering strategy, hybrid support, and hosting model.
- [[Gotchas - Vector Index Tuning]] — production ANN failures: filtered-search disconnection, recall cliffs, delete rot, metric mismatch, memory blowup, and benchmark lies.

## Query transformation, reranking, and context prep

- [[Concept - Query Transformation for Retrieval]] — rewriting or expanding a query before retrieval — HyDE, multi-query, decomposition, step-back — to close the query-document vocabulary gap.
- [[Concept - Rerankers]] — cross-encoders re-score first-stage candidates with joint attention, trading throughput for precision bi-encoders can't reach.
- [[Concept - Contextual Retrieval]] — prepending LLM-generated document context to each chunk before indexing, made viable by prompt caching, to fix the isolated-chunk problem.
- [[Concept - Agentic Retrieval]] — retrieval driven by the model's own decisions — whether, what, and when to retrieve, and whether results suffice — instead of a fixed pipeline.

## RAG system architecture

- [[Deep Dive - RAG Architectures]] — the taxonomy of RAG system designs from naive to advanced to modular to agentic to graph, and how to pick the right point on that spectrum.
- [[Playbook - Building a Production RAG System]] — a production RAG pipeline end to end: build the eval set first, then ingest, chunk, embed, index, retrieve, rerank, and generate.
- [[Breakdown - Microsoft GraphRAG]] — an LLM-extracted knowledge graph plus hierarchical community summaries, built to answer global, corpus-wide questions.
- [[Gotchas - RAG Pipelines]] — aggregated RAG pipeline failure modes from ingestion to generation, ordered by pain, each with symptom, cause, fix, and detection.
- [[Decision - RAG vs Long-Context Windows]] — default to RAG; reach for raw long-context stuffing only on small, bounded, infrequently-queried corpora, and combine both above that.

## Evaluation and debate

- [[Concept - RAG Evaluation]] — RAG must be scored as two separate measurement problems, retrieval and generation, or a bad retriever and a bad generator become indistinguishable.
- [[Lore - The RAG Is Dead Debate]] — every context-window jump revives "RAG is dead"; why the claim is both right and wrong, and why retrieval ends up feeding the window anyway.

## Adjacent domains

- [[MOC - Agents]] — agentic retrieval and tool-based search are the same problem viewed from opposite domains; multi-step retrieval is a special case of the agent loop.
- [[MOC - Prompting & Context]] — retrieved chunks land in the context window, so chunking, formatting, and context rot decisions here are downstream of that domain's rules.
- [[MOC - Fine-Tuning]] — RAG and fine-tuning both fight the frozen-knowledge problem; the fine-tuning domain's decision notes cover when to fine-tune instead of, or alongside, retrieval.
- [[MOC - Evaluation]] — general eval methodology (judges, statistical rigor) that RAG Evaluation's two-part retrieval/generation scoring builds on top of.
