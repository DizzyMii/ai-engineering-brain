---
tags: [playbook, domain/retrieval-rag, level/advanced]
aliases: []
summary: "A production RAG pipeline, end to end: build the eval set first, then ingest, chunk, embed, index, retrieve, rerank, and generate."
---

# Playbook - Building a Production RAG System

> **Goal:** stand up a [[Concept - Retrieval-Augmented Generation|RAG]] pipeline, from raw document corpus to monitored production endpoint, whose retrieval quality is measured instead of assumed. **When to run this:** a corpus needs to ground LLM answers and the team is past the demo/notebook stage. **Prerequisites:** a representative document sample, a rough idea of the real query distribution, and willingness to build an eval set before writing pipeline code. Skipping that is the most common way production RAG projects go sideways.

## Steps

1. **Build the eval set before any pipeline code.**
   Action: hand-label 50-200 real (query, relevant-chunk, ideal-answer) triples from actual or realistic user queries, covering the query types you expect (fact lookup, multi-hop, out-of-scope).
   Expected observation: a versioned golden set that every later decision (chunk size, embedder, k, reranker) gets measured against.
   What deviation means: if you're tuning on vibes from a handful of demo queries, nothing else in this playbook can be falsified. Stop and build the set first, per [[Concept - RAG Evaluation]].

2. **Ingest and chunk.**
   Action: pick a chunking strategy per document type: structural (headers/AST) for markdown and code, recursive-character for prose, semantic chunking where topic shifts matter. Start at 256-512 tokens with roughly 15% overlap, and treat tables and code as special cases.
   Expected observation: a manual spot-check of 20-30 chunks shows each is self-contained and readable without its neighbors.
   What deviation means: a chunk missing its header, subject or antecedent is a chunking problem. Fix it here, per [[Concept - Chunking Strategies]]; nothing later in the pipeline can recover information a bad boundary threw away.

3. **Embed.**
   Action: shortlist an [[Concept - Embedding Models|embedding model]] with MTEB, then confirm it on your own eval set (MTEB rank isn't your-domain performance). Respect the model's max sequence length and its query/passage instruction prefixes. Batch-embed the corpus.
   Expected observation: recall@10 on the eval set clears a sanity threshold before you move on. The threshold depends on context, but well below 0.5 means something is wrong.
   What deviation means: near-random recall after embedding almost always means an omitted instruction prefix (one of the top production bugs) or a domain-mismatched model. Check the prefix first, before suspecting chunking or the index.

4. **Index.**
   Action: default to hybrid indexing, dense ([[Concept - HNSW]] or equivalent) plus [[Concept - BM25 and Lexical Retrieval|BM25]]. Pick the vector store by filtering needs and expected scale, not leaderboard popularity, per [[Reference - Vector Database Landscape]].
   Expected observation: on a handful of manual test queries, each arm returns sane top-k results on its own before you wire them together.
   What deviation means: if the lexical arm returns nothing on obviously keyword-matchable queries, the inverted index build failed silently. Test it in isolation before blaming fusion.

5. **Retrieve, fuse, and rerank.**
   Action: take top-100 from each arm, fuse with [[Concept - Hybrid Search and Reciprocal Rank Fusion|Reciprocal Rank Fusion]], then re-score the fused top-N with a cross-encoder [[Concept - Rerankers|reranker]] down to the 3-5 chunks that go into the generation prompt.
   Expected observation: recall@10 on the eval set at or above roughly 0.7-0.8. It's corpus-dependent, but treat materially lower as a warning, not a number to accept.
   What deviation means: low recall here comes from chunking or the embedder. A reranker can only reorder candidates first-stage retrieval already surfaced. Run the eval per stage (retrieval alone vs. reranked) to find which one is failing.

6. **Generate.**
   Action: write a grounding prompt that tells the model to answer only from the provided context, cite the chunk behind each claim, and abstain ("I don't have enough information") when the context doesn't cover the question. Use structured output for citations if downstream systems consume them.
   Expected observation: on eval questions with no good answer in the corpus, the model abstains instead of confabulating from its parametric prior.
   What deviation means: confident wrong answers on unanswerable questions mean the grounding instruction is too weak or missing. That's a prompt problem, and better retrieval won't fix it.

7. **Evaluate end to end, then iterate the weakest stage.**
   Action: score retrieval (recall@k, nDCG@k, MRR) and generation (faithfulness/groundedness, answer relevancy, e.g. via RAGAS-style LLM-judge metrics) separately on the golden set, per [[Concept - RAG Evaluation]]. Fix the worst-scoring stage, then re-measure.
   Expected observation: retrieval and generation scores move independently as you change different stages, which confirms the two-stage split is isolating failures.
   What deviation means: if a reranker upgrade moves nDCG but not final answer quality, the generator is ignoring the extra context (a prompt/generation problem) even though retrieval "improved." Check both metrics, never one alone.

8. **Ship monitoring, then keep the eval set alive.**
   Action: log every production query with its retrieved chunks and generated answer as structured traces (see [[Concept - LLM Observability and Tracing]]). Track the no-context-found rate and the low-faithfulness rate as ongoing metrics. Periodically sample production failures back into the golden set.
   Expected observation: the no-context and low-faithfulness rates are on a dashboard, not discovered from user complaints.
   What deviation means: a no-context rate that rises over time usually means the corpus has drifted (new document types, new query patterns) faster than the index or eval set was updated. Treat it as a scheduled maintenance signal; it isn't a one-time launch task.

## Verification

After every pipeline change, re-run the full golden set end to end and diff both retrieval metrics (recall@k, nDCG@k) and generation metrics (faithfulness, answer relevancy) against the previous run. Improving one while silently regressing the other is common: a bigger k raises recall but can lower faithfulness by injecting distractors. You only see it if you track both together.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Retrieval recall@k is low from the start | Bad chunk boundaries or wrong embedder for the domain | Back to Step 2/3: inspect chunks by hand, verify instruction prefixes, check the embedder on your eval set instead of MTEB rank |
| Recall@k is good but final answers are still wrong | Generator ignoring retrieved context, or lost-in-the-middle position bias | Reorder retrieved chunks (best evidence first or last), tighten the grounding prompt, reduce k, per [[Gotchas - RAG Pipelines]] |
| Confident wrong answers on questions the corpus doesn't cover | Missing or weak abstain instruction | Add explicit cite-or-abstain instructions in Step 6 and put unanswerable questions in the eval set |
| Reranker improves nDCG but not end-to-end accuracy | First-stage recall is the ceiling | Measure retrieval and generation separately (Step 7); the reranker can't fix a document that never made the shortlist |
| Index quality degrades weeks after launch | Stale embeddings on updated documents, or piling-up delete tombstones | Reindex changed documents and monitor deleted-ratio, per [[Reference - Vector Database Landscape]] |
| Fine in the demo, breaks on real traffic | The eval set was small, hand-picked, or never adversarial | Grow the golden set with real production failures (Step 8) and add distractor/robustness tests |

## Connections

- [[Concept - Chunking Strategies]] — Step 2's decision is the single highest-leverage lever in the whole pipeline; nothing downstream recovers a bad chunk boundary.
- [[Concept - Embedding Models]] — Step 3's model choice, including the instruction-prefix pitfall that silently halves recall if missed.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — the fusion method that combines the dense and lexical arms built in Step 4 and retrieved in Step 5.
- [[Concept - Rerankers]] — the precision stage in Step 5 that can only ever reorder what first-stage retrieval already surfaced.
- [[Concept - RAG Evaluation]] — the metrics and two-stage decomposition methodology that Steps 1 and 7 both depend on.
- [[Reference - Vector Database Landscape]] — the comparison matrix for picking the store in Step 4 by filtering needs and scale, not by popularity.
- [[Concept - LLM Observability and Tracing]] — what Step 8's logging needs to grow into once this system leaves prototype status.
- [[Gotchas - RAG Pipelines]] — the catalog of failure modes this playbook's steps are built to defend against, cross-referenced in the "when it goes wrong" table.
- [[Playbook - Reliable Structured Output]] — the sibling procedure for Step 6 when the generation target is structured citations or a JSON shape rather than free text.
- [[Concept - Agentic Retrieval]] — the natural next step once this static pipeline is solid and query complexity justifies letting the model control retrieval dynamically.

## Sources

- Anthropic (2024) — Introducing Contextual Retrieval. The measured, stacked gains from contextual embeddings, contextual BM25, and reranking that motivate treating retrieval quality as additive across pipeline stages.
- Es et al. (2023) — RAGAS: Automated Evaluation of Retrieval Augmented Generation. The faithfulness/answer-relevancy LLM-judge framework underlying Step 7's generation metrics.
