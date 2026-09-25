---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [HyDE, RAG-Fusion, query rewriting, query expansion, multi-query retrieval, step-back prompting]
summary: "Rewriting or expanding a query before retrieval — HyDE, multi-query, decomposition, step-back — to close the query-document vocabulary gap."
---
> **One-paragraph hook:** A terse user query and a verbose passage that answers it can sit surprisingly far apart in embedding space, even when the passage is exactly what the user needs. The vocabulary and register mismatch is real; it isn't a retrieval bug. Query transformation fixes it *before* retrieval runs by rewriting, expanding, decomposing or routing the query into a form that lands closer to the documents that answer it.

## The mechanism

Short keyword queries ("colbert storage cost") and long, well-formed passages (a paragraph on ColBERT's index-size tradeoffs) are asymmetric. They differ in length, register and vocabulary even when perfectly relevant to each other, and a [[Concept - Semantic Search|bi-encoder]] trained to embed both into one space only partly closes the gap. Each transformation technique attacks the asymmetry differently:

- **HyDE** (Gao et al. 2022, Precise Zero-Shot Dense Retrieval without Relevance Labels). Don't embed the raw query. Ask an LLM for a *hypothetical answer*, a fake document that would answer the question, and embed **that**. The fake reads like a real passage, stylistically and lexically, so it lands much closer in embedding space to actual answering documents than the terse query did, even if its facts are wrong. Retrieval only needs the hypothetical document to be right in topic and style. The embedding is compared against the corpus, never against ground truth.
- **Multi-query / RAG-Fusion.** Generate $N$ paraphrases of the query, retrieve for each independently, and merge the $N$ result lists with [[Concept - Hybrid Search and Reciprocal Rank Fusion|Reciprocal Rank Fusion]]: $\text{RRF}(d) = \sum_i \frac{1}{k + \text{rank}_i(d)}$. Different phrasings surface relevant documents a single phrasing would miss, at a direct cost of $N\times$ the retrieval calls.
- **Decomposition.** Split a compound or multi-hop question ("compare X's Q1 revenue to Y's Q1 revenue") into independent sub-queries, retrieve each separately, and hand all the evidence to the generator together. You need this whenever no single passage in the corpus holds the full answer.
- **Step-back prompting** (Zheng et al. 2023, Take a Step Back). Ask a more abstract question first ("what factors affect X's overall pricing strategy" before "why did X raise prices in March") to retrieve the underlying principles or background, then use that alongside the original query.
- **Routing.** Classify the query first (which index, which tool, or no retrieval at all) before anything else. This gate keeps retrieval from firing, and injecting noise, on queries that don't need it, like small talk or pure-reasoning questions.

## In practice

Every transform costs at least one extra LLM call before retrieval starts, typically adding on the order of 100-500ms. Multi-query multiplies downstream retrieval cost by $N$, commonly 3-5 paraphrases and rarely more, since cost grows linearly and marginal recall gain doesn't. The standard production chain is **transform query → retrieve per variant → RRF-fuse → [[Concept - Rerankers|rerank]]**: the transform widens the net, fusion merges it, the reranker restores precision. LangChain's `MultiQueryRetriever` and LlamaIndex's query-transform modules implement these patterns directly. Routing is usually the cheapest of the five to add and has the best cost/benefit, because it's a single classification call and doesn't multiply retrieval.

## Failure modes

- **HyDE hallucinating into the wrong domain.** On narrow technical or unfamiliar corpora the LLM can't produce a plausible hypothetical document and makes up confidently wrong terminology, which then retrieves documents matching the fabrication instead of the user's intent. Symptom: retrieved documents are topically unrelated to the real query, though HyDE "works" on common-knowledge questions. Detect with a domain-specific eval set, not general benchmarks. Fix by grounding the HyDE prompt in domain context or falling back to raw-query retrieval for out-of-domain queries.
- **Multi-query cost blowup.** Uncapped $N$ or expensive per-variant embedding calls turn cheap retrieval into an $N\times$ latency and cost problem for marginal recall. Cap $N$ at 3-5 and measure lift on the eval set before raising it.
- **Decomposition drops the aggregation step.** Sub-queries retrieve fine individually, but nothing recombines them coherently for the generator, so the final answer covers only one sub-question. Structure the prompt to require synthesis across all sub-query results; concatenation isn't enough.
- **Routing misclassification.** An over-eager router sends everything to retrieval (irrelevant context on simple queries) or nothing (silently dropping grounding where it was needed). Detect with a confusion matrix over labeled query types in the eval set, per [[Concept - RAG Evaluation]].

## The non-obvious

For HyDE's purpose, the hallucination *is* the mechanism. It works because "plausible but possibly wrong" text still lands in the right region of embedding space for most fact-lookup queries: dense similarity tracks topic and register more than truth. It's also why HyDE decays hardest on narrow technical domains. Once the model can't even fake a stylistically plausible passage, the hallucination stops being harmless noise and starts steering retrieval into the wrong corner of the space.

Measured naively, multi-query lift looks smaller than practitioners expect. Aggregate metrics average over queries that already had high single-phrasing recall, where a second paraphrase adds nothing. The real gain sits almost entirely in ambiguous or underspecified queries. Measure lift stratified by query difficulty, or the technique will look like it isn't paying for its latency when it is, just unevenly.

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
