---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [cross-encoder reranking, reranking, re-ranking]
summary: "Cross-encoders re-score first-stage candidates with joint attention, trading throughput for precision bi-encoders can't reach."
---
> **One-paragraph hook:** [[Concept - Semantic Search]] and [[Concept - BM25 and Lexical Retrieval]] are built for recall — cheap enough to sweep millions of documents — which means they're bad at precision. A reranker fixes that by throwing a much more expensive model at a much smaller candidate set: not "find the needles," but "you already found 100 candidates, tell me which one is actually the needle." Adding one is routinely the single highest-ROI change to a mediocre RAG pipeline.

## The mechanism

A bi-encoder (the architecture behind [[Concept - Embedding Models]]) encodes the query and the document *independently* into fixed vectors and compares them with a similarity function — dot product or cosine. This independence is what makes it fast: document embeddings are precomputed once and stored in an index, so at query time you only embed the query and do a nearest-neighbor lookup. But independence is also a ceiling: the model never gets to look at the query and the document *together*, so it can't model fine-grained token-level interactions like "does this specific clause in the document answer this specific sub-question."

A **cross-encoder** removes that ceiling by concatenating query and document into a single input — `[CLS] query [SEP] document [SEP]` — and running it through one transformer. Every query token attends to every document token and vice versa via full self-[[Concept - Attention Mechanism]], and a classification head on top reads out a single relevance score. This joint attention is strictly more expressive than a bi-encoder's independent encoding: the model can match "revenue" in the query against "top-line growth" in the document *in context*, something two separately-pooled vectors structurally cannot represent as precisely.

The cost is unavoidable: because query and document are fused before any computation happens, nothing can be precomputed. Scoring $N$ candidates means $N$ full forward passes through the transformer, at query time, every time. This is why cross-encoders are never used as the first-stage retriever over a full corpus — running a cross-encoder over a million documents per query is a non-starter — and are instead used as a second stage over a small candidate set a cheap retriever already narrowed down.

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

The **retrieve-then-rerank cascade** is the default architecture: a cheap, recall-oriented first stage (BM25, dense, or [[Concept - Hybrid Search and Reciprocal Rank Fusion]]) surfaces 100–1000 candidates, and the reranker cuts that down to the 3–10 chunks that actually go into the generation prompt. The critical constraint to internalize: **the reranker can only reorder what retrieval already found.** If the correct document never made it into the top-1000 from the first stage, no amount of reranking recovers it — reranker quality caps out at first-stage recall, which is why tuning chunking and the first-stage retriever still matters even after you've added a great reranker.

Model landscape (as of 2026): Cohere Rerank v3, BGE-reranker-v2, Jina Reranker, mixedbread's mxbai-rerank, and Voyage Rerank are the common hosted/open options, descending from the MonoT5/monoBERT lineage of cross-encoder rerankers. A separate family, **LLM rerankers** like RankGPT, use a general-purpose LLM to *listwise* rank a candidate set (generate a permutation directly, or via pairwise/sliding-window comparisons) rather than scoring each candidate independently — strong zero-shot performance with no reranker-specific training, at the cost of being slower and more expensive per query; sliding windows are used to handle candidate lists too long for one context.

Latency budget: cross-encoder inference adds tens to low hundreds of milliseconds when batched on GPU, which is why practitioners rerank 50–200 candidates, not thousands — reranking 1000 candidates either blows the latency budget or requires a much bigger GPU fleet, and the marginal value of candidates ranked below ~200 by a decent first-stage retriever is usually small anyway.

Long documents break the naive setup: cross-encoders have the same token-limit constraints as any transformer, so a document longer than the model's max sequence length gets silently truncated — evidence past the truncation point is invisible to the reranker even though it retrieved the right document. The fix is chunk-and-max (score each chunk of the document, keep the max) or a long-context reranker explicitly trained for it.

## Failure modes

- **Reranker can't fix bad recall**: if the first-stage retriever missed the answer entirely, the reranker has nothing to promote. Symptom: adding a reranker doesn't move end-to-end accuracy despite improved nDCG on the candidates that *were* retrieved. Detect by measuring recall@k of the first stage in isolation, per [[Concept - RAG Evaluation]] — this is the two-stage decomposition that localizes whether the bug is retrieval or reranking.
- **Silent truncation on long documents**: a relevant passage sitting past the reranker's max sequence length is invisible to the score, so a document is under-ranked for reasons that have nothing to do with relevance. Detect by checking document lengths against the reranker's context limit before assuming the model is "just wrong."
- **Over-reranking too few or too many candidates**: reranking only the top 10 from first-stage defeats the purpose (you're barely reordering); reranking 2000 blows the latency budget for marginal gain. The 50–200 range is the empirical sweet spot most production systems converge on.
- **Latency surprise under load**: a reranker that looked fine in a demo at low QPS can become the dominant tail-latency contributor once batching saturates GPU throughput — this is a [[Concept - Cost Engineering for LLM Applications]] problem as much as a quality one, and needs to be load-tested, not just accuracy-tested.

## The non-obvious

"Just add a reranker" has become standard advice in RAG circles for a concrete, measurable reason: because bi-encoder retrieval is capped by the information bottleneck of pooling a whole document into one vector, and a cross-encoder's joint attention routinely recovers a large chunk of the relevance signal that pooling destroyed — large nDCG@10 gains are common even with an off-the-shelf reranker and zero tuning. The failure mode practitioners hit is not "does reranking help" (it almost always does) but forgetting that a reranker is a *precision* tool bolted onto whatever *recall* ceiling the first stage already set — teams that see disappointing end-to-end results after adding a reranker are, more often than not, staring at a first-stage recall problem they misdiagnosed as a reranking problem.

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
