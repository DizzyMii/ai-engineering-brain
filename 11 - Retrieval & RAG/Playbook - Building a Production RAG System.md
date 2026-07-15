---
tags: [playbook, domain/retrieval-rag, level/advanced]
aliases: []
summary: "A production RAG pipeline, end to end: build the eval set first, then ingest, chunk, embed, index, retrieve, rerank, and generate."
---

# Playbook - Building a Production RAG System

> **Goal:** stand up a [[Concept - Retrieval-Augmented Generation|RAG]] pipeline whose retrieval quality is measured, not assumed, from a raw document corpus through to a monitored production endpoint. **When to run this:** any time a corpus needs to ground LLM answers and the team is past the demo/notebook stage. **Prerequisites:** a representative document sample, a rough sense of the real query distribution, and the willingness to build an eval set before writing pipeline code — skipping this step is the single most common way production RAG projects go sideways.

## Steps

1. **Build the eval set first — before any pipeline code.**
   Action: hand-label 50-200 real (query, relevant-chunk, ideal-answer) triples drawn from actual or realistic user queries, covering the query types you expect (fact lookup, multi-hop, out-of-scope).
   Expected observation: a versioned golden set that every later decision — chunk size, embedder choice, k, reranker — gets measured against.
   What deviation means: if you're tuning "on vibes" from a handful of demo queries, every subsequent step in this playbook is unfalsifiable — stop and build the set first, per [[Concept - RAG Evaluation]].

2. **Ingest and chunk.**
   Action: pick a chunking strategy by document type — structural (headers/AST) for markdown and code, recursive-character for prose, semantic chunking where topic shifts matter — starting at 256-512 tokens with roughly 15% overlap; handle tables and code as special cases, not as prose.
   Expected observation: a manual spot-check of 20-30 chunks shows each one is self-contained and interpretable without its neighbors.
   What deviation means: a chunk missing its header, subject, or antecedent is a chunking-strategy problem, not a downstream retrieval or generation problem — fix it here, per [[Concept - Chunking Strategies]], since nothing later in the pipeline can recover information a bad boundary already discarded.

3. **Embed.**
   Action: choose an [[Concept - Embedding Models|embedding model]] using MTEB as a starting filter, then confirm the pick against your own eval set (MTEB rank does not equal your-domain performance); respect the model's max sequence length and query/passage instruction prefixes; batch-embed the corpus.
   Expected observation: recall@10 on the eval set clears a sanity threshold (context-dependent, but well below 0.5 signals a real problem) before moving on.
   What deviation means: recall stuck near-random after embedding almost always means an omitted instruction prefix (a single top production bug) or a domain-mismatched model, not a chunking or index problem — verify the prefix first.

4. **Index.**
   Action: default to hybrid indexing — dense ([[Concept - HNSW]] or equivalent) plus [[Concept - BM25 and Lexical Retrieval|BM25]] — and choose the vector store by filtering requirements and expected scale, not by leaderboard popularity, per [[Reference - Vector Database Landscape]].
   Expected observation: both arms return sane top-k results independently on a handful of manual test queries before you wire them together.
   What deviation means: if the lexical arm returns nothing on obviously keyword-matchable queries, the inverted index build failed silently — verify it in isolation before blaming fusion.

5. **Retrieve, fuse, and rerank.**
   Action: retrieve top-100 from each arm, fuse with [[Concept - Hybrid Search and Reciprocal Rank Fusion|Reciprocal Rank Fusion]], then re-score the fused top-N with a cross-encoder [[Concept - Rerankers|reranker]] down to the 3-5 chunks that go into the generation prompt.
   Expected observation: recall@10 on the eval set is at or above roughly 0.7-0.8 (corpus-dependent, but treat materially lower as a signal, not a target to accept).
   What deviation means: low recall here traces back to chunking or the embedder, not the reranker — a reranker can only reorder candidates that first-stage retrieval already surfaced; re-run the eval per stage (retrieval alone vs. reranked) to localize which one is actually failing.

6. **Generate.**
   Action: write a grounding prompt that instructs the model to answer only from the provided context, cite which chunk supports each claim, and explicitly abstain ("I don't have enough information") when the retrieved context doesn't cover the question; use structured output for citations if downstream systems consume them.
   Expected observation: on eval-set questions with no good answer in the corpus, the model abstains rather than confabulating from its parametric prior.
   What deviation means: confident wrong answers on unanswerable questions mean the grounding instruction is too weak or absent — this is a prompt problem, not a retrieval problem, and it will not be fixed by improving retrieval further.

7. **Evaluate end to end, then iterate the weakest stage.**
   Action: score retrieval (recall@k, nDCG@k, MRR) and generation (faithfulness/groundedness, answer relevancy — e.g. via RAGAS-style LLM-judge metrics) separately on the golden set, per [[Concept - RAG Evaluation]]; fix whichever stage scores worst, then re-measure.
   Expected observation: retrieval and generation scores move independently as you change different pipeline stages — confirming the two-stage decomposition is actually isolating failures.
   What deviation means: if a reranker upgrade moves nDCG but not final answer quality, the generator is ignoring the extra context (a prompt/generation problem) even though retrieval "improved" — always check both metrics, never one alone.

8. **Ship monitoring, then keep the eval set alive.**
   Action: log every production query alongside its retrieved chunks and generated answer as structured traces (see [[Concept - LLM Observability and Tracing]]); track the no-context-found rate and low-faithfulness-score rate as ongoing metrics; periodically sample production failures back into the golden set.
   Expected observation: the no-context and low-faithfulness rates are visible on a dashboard, not discovered from user complaints.
   What deviation means: a rising no-context rate over time usually means the corpus has drifted (new document types, new query patterns) faster than the index or eval set has been updated — treat it as a scheduled maintenance signal, not a one-time launch task.

## Verification

Re-run the full golden set end to end after every pipeline change and diff both the retrieval metrics (recall@k, nDCG@k) and the generation metrics (faithfulness, answer relevancy) against the previous run — a change that improves one and silently regresses the other is common (a bigger k raises recall but can lower faithfulness by injecting distractors) and only shows up if both are tracked together, not separately.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Retrieval recall@k is low from the start | Bad chunk boundaries or wrong embedder for the domain | Go back to Step 2/3 — inspect chunks manually, verify instruction prefixes, check embedder against your eval set, not MTEB rank |
| Recall@k is good but final answers are still wrong | Generator ignoring retrieved context, or lost-in-the-middle position bias | Reorder retrieved chunks (best evidence first or last), tighten the grounding prompt, reduce k, per [[Gotchas - RAG Pipelines]] |
| Confident wrong answers on questions the corpus doesn't cover | Missing or weak abstain instruction | Add explicit cite-or-abstain instructions in Step 6 and add unanswerable questions to the eval set |
| Reranker improves nDCG but not end-to-end accuracy | First-stage recall is the actual ceiling, not reranking | Measure retrieval and generation separately (Step 7); the reranker cannot fix a document that never made the shortlist |
| Index quality degrades weeks after launch | Stale embeddings on updated documents, or accumulating delete tombstones | Reindex changed documents and monitor deleted-ratio, per [[Reference - Vector Database Landscape]] |
| Everything looked fine in the demo but breaks on real traffic | The eval set was small, hand-picked, or never adversarial | Expand the golden set with real production failures (Step 8) and add distractor/robustness tests |

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
