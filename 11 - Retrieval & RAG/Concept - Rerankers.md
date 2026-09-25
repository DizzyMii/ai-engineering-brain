---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [cross-encoder reranking, reranking, re-ranking]
summary: "Cross-encoders re-score first-stage candidates with joint attention, trading throughput for precision bi-encoders can't reach."
---
> **One-paragraph hook:** [[Concept - Semantic Search]] and [[Concept - BM25 and Lexical Retrieval]] are built for recall, cheap enough to sweep millions of documents, and that makes them bad at precision. A reranker fixes this by putting a much more expensive model on a much smaller candidate set. The question changes from "find the needles" to "you found 100 candidates, which one is the needle?" Adding one is routinely the highest-ROI change you can make to a mediocre RAG pipeline.

## The mechanism

A bi-encoder (the architecture behind [[Concept - Embedding Models]]) encodes query and document *independently* into fixed vectors and compares them with dot product or cosine. Independence is what makes it fast. Document embeddings are precomputed once and indexed, so at query time you embed the query and do a nearest-neighbor lookup. It's also a ceiling. The model never sees query and document *together*, so it can't model fine-grained token interactions like "does this clause in the document answer this sub-question?"

A **cross-encoder** removes the ceiling. It concatenates query and document into one input, `[CLS] query [SEP] document [SEP]`, and runs it through a single transformer. Every query token attends to every document token and back through full self-[[Concept - Attention Mechanism]], and a classification head reads out one relevance score. Joint attention is strictly more expressive than independent encoding: the model can match "revenue" in the query to "top-line growth" in the document *in context*, which two separately pooled vectors can't represent as precisely.

The cost can't be avoided. Query and document are fused before any computation, so nothing can be precomputed, and scoring $N$ candidates takes $N$ full forward passes at query time, every time. Running a cross-encoder over a million documents per query is a non-starter, so they never serve as the first-stage retriever over a full corpus. They're a second stage over a small candidate set a cheap retriever already narrowed.

```
first-stage retrieval (bi-encoder / BM25 / hybrid)
        corpus (millions)  →  top 100–1000 candidates
                                        │
                                        ▼
                          cross-encoder reranker
                    scores EACH (query, candidate) pair
                    with full joint attention, one pass each
                                        │
                                        ▼
                              top 3–10 → into prompt
```

## In practice

The **retrieve-then-rerank cascade** is the default. A cheap, recall-oriented first stage (BM25, dense, or [[Concept - Hybrid Search and Reciprocal Rank Fusion]]) surfaces 100–1000 candidates, and the reranker cuts them to the 3–10 chunks that go into the generation prompt. The constraint to internalize: **the reranker can only reorder what retrieval already found.** If the right document never made the first stage's top-1000, no reranking brings it back. Reranker quality is capped by first-stage recall, so chunking and the first-stage retriever still need tuning after you add a great reranker.

Models (as of 2026): Cohere Rerank v3, BGE-reranker-v2, Jina Reranker, mixedbread's mxbai-rerank and Voyage Rerank are the common hosted/open options, descended from the MonoT5/monoBERT cross-encoder lineage. **LLM rerankers** such as RankGPT are a separate family. A general-purpose LLM ranks the candidate set *listwise* (generating a permutation directly, or through pairwise/sliding-window comparisons) instead of scoring each candidate on its own. They give strong zero-shot performance with no reranker-specific training, and cost more time and money per query. Sliding windows handle candidate lists too long for one context.

Latency: batched on GPU, cross-encoder inference adds tens to low hundreds of milliseconds. That's why people rerank 50–200 candidates and not thousands. Reranking 1000 either blows the latency budget or needs a much bigger GPU fleet, and candidates a decent first stage ranks below ~200 usually add little anyway.

Long documents break the naive setup. Cross-encoders have the same token limits as any transformer, so a document longer than the model's max sequence length gets silently truncated, and evidence past the cut is invisible to the reranker even though retrieval found the right document. Use chunk-and-max (score each chunk, keep the max) or a long-context reranker trained for it.

## Failure modes

- **A reranker can't fix bad recall.** If the first stage missed the answer, the reranker has nothing to promote. Symptom: end-to-end accuracy doesn't move, though nDCG improves on the candidates that *were* retrieved. Measure first-stage recall@k on its own, per [[Concept - RAG Evaluation]]; that two-stage split tells you whether the bug is in retrieval or reranking.
- **Silent truncation on long documents.** A relevant passage past the reranker's max sequence length never reaches the score, so the document is under-ranked for reasons unrelated to relevance. Check document lengths against the reranker's context limit before deciding the model is "just wrong."
- **Reranking too few or too many candidates.** Reranking only the first stage's top 10 barely reorders anything. Reranking 2000 blows the latency budget for marginal gain. Most production systems converge on the 50–200 range empirically.
- **Latency surprise under load.** A reranker that looked fine in a low-QPS demo can dominate tail latency once batching saturates GPU throughput. That makes it a [[Concept - Cost Engineering for LLM Applications]] problem as well as a quality one. Load-test it, don't just accuracy-test it.

## The non-obvious

"Just add a reranker" became standard RAG advice for a measurable reason. Bi-encoder retrieval is capped by the bottleneck of pooling a whole document into one vector, and a cross-encoder's joint attention routinely recovers much of the relevance signal pooling threw away. Large nDCG@10 gains are common even from an off-the-shelf reranker with zero tuning. Whether reranking helps is rarely the issue (it almost always does). The mistake is forgetting that a reranker is a *precision* tool sitting on whatever *recall* ceiling the first stage set. Teams disappointed by end-to-end results after adding one are, more often than not, looking at a first-stage recall problem they misread as a reranking problem.

## Connections

- [[Concept - Late Interaction and ColBERT]] — the middle ground between bi-encoder and cross-encoder: token-level scoring that's cheaper than a full cross-encoder but richer than single-vector similarity.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — the first-stage candidate generator whose output the reranker re-scores; recall here caps reranker quality.
- [[Concept - Semantic Search]] — the down-link prerequisite: understand bi-encoder independent encoding to see exactly what joint attention adds.
- [[Concept - RAG Evaluation]] — nDCG@10 and the two-stage retrieval/generation decomposition are how reranker gains actually get measured.
- [[Concept - Attention Mechanism]] — the mechanism a cross-encoder uses internally to fuse query and document representations.
- [[Concept - Cost Engineering for LLM Applications]] — reranker latency and GPU cost are a real production line item, not free precision.
- [[Deep Dive - RAG Architectures]] — reranking is a standard post-retrieval optimization stage in the advanced-RAG taxonomy.
- [[Concept - Hard Negative Mining]] — cross-encoder rerankers are the standard teacher model for distilling hard-negative labels into faster bi-encoder embeddings.

## Sources

- Nogueira & Cho (2019) — Passage Re-ranking with BERT (monoBERT). Established the cross-encoder retrieve-then-rerank cascade as the standard pattern.
- Nogueira et al. (2020) — Document Ranking with a Pretrained Sequence-to-Sequence Model (monoT5). The T5-based reranking lineage several current commercial rerankers descend from.
