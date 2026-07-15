---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [HyDE, RAG-Fusion, query rewriting, query expansion, multi-query retrieval, step-back prompting]
summary: "Rewriting or expanding a query before retrieval — HyDE, multi-query, decomposition, step-back — to close the query-document vocabulary gap."
---
> **One-paragraph hook:** A terse user query and a verbose passage that answers it can live surprisingly far apart in embedding space, even when the passage is exactly what the user needs — the vocabulary and register mismatch is real, not a retrieval bug. Query transformation fixes this *before* retrieval ever runs, by rewriting, expanding, decomposing, or routing the query into a form that lands closer to the documents that actually answer it.

## The mechanism

Short keyword-style queries ("colbert storage cost") and long, well-formed passages (a paragraph explaining ColBERT's index size tradeoffs) are asymmetric: they differ in length, register, and vocabulary even when perfectly relevant to each other, and a [[Concept - Semantic Search|bi-encoder]] trained to embed both into one space only partially closes that gap. Query transformation techniques attack the asymmetry directly, each in a different way:

- **HyDE** (Gao et al. 2022, Precise Zero-Shot Dense Retrieval without Relevance Labels): instead of embedding the raw query, ask an LLM to generate a *hypothetical answer* — a fake document that would answer the question — and embed **that**. The hallucinated document is stylistically and lexically similar to real passages (it reads like one), which places it much closer in embedding space to actual answering documents than the terse original query ever was, even though its specific factual content may be wrong. Retrieval only needs the hypothetical document to be topically and stylistically right, not factually right — the embedding never gets compared against ground truth, only against the corpus.
- **Multi-query / RAG-Fusion**: generate $N$ paraphrases of the query, retrieve independently for each, and merge the $N$ result lists with [[Concept - Hybrid Search and Reciprocal Rank Fusion|Reciprocal Rank Fusion]] — $\text{RRF}(d) = \sum_i \frac{1}{k + \text{rank}_i(d)}$. Different phrasings surface different relevant documents that any single phrasing would miss, at the direct cost of $N\times$ the retrieval calls.
- **Decomposition**: split a compound or multi-hop question ("compare X's Q1 revenue to Y's Q1 revenue") into independent sub-queries, retrieve each separately, and pass all the retrieved evidence to the generator together — necessary whenever no single passage in the corpus contains the full answer.
- **Step-back prompting** (Zheng et al. 2023, Take a Step Back): ask a more abstract, general question first ("what factors affect X's overall pricing strategy" before "why did X raise prices in March") to retrieve the underlying principles or background context, then use that alongside the original specific query.
- **Routing**: classify the query first — which index, which tool, or no retrieval at all — before doing anything else. This is the gate that keeps retrieval from firing (and injecting noise) on queries that don't need it, like small talk or pure-reasoning questions.

## In practice

Every transform costs at least one extra LLM call before retrieval even starts, typically adding on the order of 100-500ms of latency; multi-query multiplies the downstream retrieval cost by $N$ (commonly 3-5 paraphrases, rarely more — cost grows linearly while marginal recall gain does not). The standard production pipeline chains transform, retrieval, and post-processing: **transform query → retrieve per variant → RRF-fuse → [[Concept - Rerankers|rerank]]** — the transform widens the net, fusion merges it, and the reranker restores precision. Frameworks like LangChain's `MultiQueryRetriever` and LlamaIndex's query-transform modules implement these patterns directly; routing is usually the cheapest of the five to add and the one with the best cost/benefit ratio, since it is a single classification call, not a retrieval multiplier.

## Failure modes

- **HyDE hallucinating into the wrong domain**: on narrow technical or unfamiliar corpora, the LLM cannot generate a plausible hypothetical document and instead fabricates confidently wrong terminology, which then retrieves documents matching the fabrication rather than the user's actual intent. Symptom: retrieved documents are topically unrelated to the real query despite HyDE "working" on common-knowledge questions. Detect with a domain-specific eval set, not general-purpose benchmarks; fix by grounding the HyDE prompt with domain context or falling back to raw-query retrieval for out-of-domain queries.
- **Multi-query cost blowup**: uncapped $N$ or expensive per-variant embedding calls turn a cheap retrieval into a $N\times$ latency and cost problem for marginal recall gain. Fix by capping $N$ at 3-5 and measuring lift on the eval set before increasing it.
- **Decomposition losing the aggregation step**: sub-queries retrieve fine individually but nothing recombines them coherently for the generator, so the final answer addresses only one sub-question. Fix by explicitly structuring the prompt to require synthesis across all sub-query results, not just concatenation.
- **Routing misclassification**: an overly aggressive router sends everything to retrieval (injecting irrelevant context into simple queries) or nothing (silently dropping grounding on queries that needed it). Detect via a confusion matrix over labeled query types in the eval set, per [[Concept - RAG Evaluation]].

## The non-obvious

HyDE's hallucination is not a bug relative to its purpose — it is the mechanism. The technique works precisely because "plausible but possibly wrong" text still lands in the correct region of embedding space for most fact-lookup queries, since dense embedding similarity tracks topic and register more than truth value. That is also exactly why it decays hardest on narrow technical domains: the model can no longer even fake a stylistically plausible passage, so the hallucination stops being harmless noise and starts actively misdirecting retrieval into a wrong corner of the space.

Measured naively, multi-query lift looks smaller than practitioners expect — because aggregate metrics average over queries that already had high single-phrasing recall, where a second paraphrase adds nothing. The real gain concentrates almost entirely in ambiguous or underspecified queries, so lift has to be measured stratified by query difficulty, not in aggregate, or the technique looks like it isn't paying for its added latency when it actually is, just not uniformly.

## Connections

- [[Concept - Rerankers]] — the precision-restoring stage that follows a transform-and-fuse pipeline; transformation widens recall, reranking narrows it back down.
- [[Concept - Agentic Retrieval]] — the frontier extension where the model decides dynamically *whether* and *how* to transform the query mid-generation, rather than applying a fixed transform upfront.
- [[Deep Dive - RAG Architectures]] — query transformation is the canonical pre-retrieval optimization stage in the advanced-RAG taxonomy.
- [[Concept - Chain-of-Thought and Why It Works]] — step-back prompting and decomposition both borrow the same "reason before acting" mechanism that makes chain-of-thought effective.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — the fusion method that merges multi-query's $N$ result lists into one ranking.
- [[Concept - Semantic Search]] — the retrieval mechanism whose asymmetric-query weakness motivates query transformation in the first place.
- [[Concept - RAG Evaluation]] — the stratified-by-query-type measurement required to see where a transform actually pays off.
- [[Concept - Task Decomposition and Planning]] — the general agentic-planning version of the same decompose-into-subgoals move that query decomposition applies specifically to retrieval.

## Sources

- Gao et al. (2022) — Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE). Generating a hypothetical document to embed instead of the raw query.
- Zheng et al. (2023) — Take a Step Back: Evoking Reasoning via Abstraction in Large Language Models. Step-back prompting for retrieving underlying principles before specifics.
- Cormack, Clarke & Buettcher (2009) — Reciprocal Rank Fusion. The scale-free fusion method RAG-Fusion applies to multi-query result lists.
