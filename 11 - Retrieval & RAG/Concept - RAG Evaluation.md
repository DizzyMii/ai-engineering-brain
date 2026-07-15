---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [RAG Eval, retrieval evaluation, RAGAS]
summary: "RAG must be scored as two separate measurement problems — retrieval and generation — or a bad retriever and a bad generator become indistinguishable."
---
> **One-paragraph hook:** Ship a [[Concept - Retrieval-Augmented Generation]] system without an eval harness and you are debugging by vibes: when the answer is wrong you cannot tell whether the retriever missed the right passage or the generator ignored a passage it was handed. RAG evaluation is the discipline that scores retrieval and generation as two separate measurement problems and only then recombines them — the two-stage decomposition is what turns "the bot said something dumb" into an actionable bug report pointing at a specific pipeline stage.

## The mechanism

A RAG pipeline has two distinct failure surfaces — retrieval and generation — that produce the exact same visible symptom: a wrong final answer. A perfect generator fed garbage context looks identical, from the outside, to a bad generator fed perfect context. **You cannot localize a failure from the final answer alone**; you need per-stage metrics computed against a labeled golden set.

**Retrieval metrics** ask: did the right evidence surface, and where?
- **recall@k**: did at least one gold-relevant chunk appear in the top-$k$ retrieved results, averaged over queries. The blunt, most-cited number.
- **MRR (Mean Reciprocal Rank)**: $\text{MRR} = \frac{1}{|Q|}\sum_{q} \frac{1}{\text{rank}_q}$ where $\text{rank}_q$ is the position of the first relevant chunk for query $q$ — penalizes burying the answer even if it's technically in the top-$k$.
- **nDCG@k**: a graded, position-discounted metric, $\text{DCG@k} = \sum_{i=1}^{k} \frac{2^{\text{rel}_i}-1}{\log_2(i+1)}$, normalized by the ideal ordering's DCG (IDCG) to get nDCG $\in [0,1]$. Unlike recall@k it rewards putting the *most* relevant chunk first, not just anywhere in the top-$k$ — the metric of choice once you have graded (not just binary) relevance labels.
- **hit-rate**: the simplest binary recall variant, useful as a sanity check.
- **Context precision/recall**: when you lack hand labels, an LLM judge scores whether each retrieved chunk is relevant and whether all relevant chunks were retrieved — a judged proxy for recall@k/precision@k, with all the caveats of [[Concept - LLM-as-Judge]].

**Generation metrics** ask: given the context that was actually retrieved, is the answer any good?
- **Faithfulness / groundedness**: decompose the answer into atomic claims and check each is entailed by the retrieved context — the direct hallucination catch. An answer can be fluent, relevant, and completely unfaithful to what was actually retrieved.
- **Answer relevancy**: does the answer address the question asked (measured, in RAGAS, by generating several questions *from* the answer and checking their embedding similarity back to the original query).
- **Context utilization**: whether the generator actually used the relevant chunks it was given, as opposed to ignoring them in favor of parametric memory.

RAGAS (Es et al. 2023) operationalizes faithfulness, answer relevancy, and context precision/recall as LLM-judged scores on a 0–1 scale, and is the framework most teams reach for first because it needs no gold labels beyond a question set.

## In practice

Building the golden set comes first, not last: 50–200 hand-labeled query → relevant-chunk pairs, drawn from real or realistic queries, is the common starting size — small enough to label by hand, large enough to catch systematic regressions. Synthetic QA generation (have an LLM write questions from your chunks) bootstraps coverage fast but has a well-known failure pattern: it tends to produce too-easy questions that echo the source chunk's exact vocabulary, and risks **answer leakage** where the "gold" answer is trivially copy-pasted rather than requiring real retrieval — synthetic sets systematically overestimate real-world recall unless adversarially filtered, the same leakage failure mode that [[Concept - Training Set Decontamination]] exists to catch on the pretraining side.

Beyond static recall numbers, RAG-specific robustness tests catch failure modes plain recall@k misses entirely:
- **Needle-in-a-haystack**: can retrieval find one specific fact buried in a large corpus at all.
- **Position-bias sweeps**: does answer quality change when the same gold chunk is moved from position 1 to position 5 in the context.
- **The distractor test**: does injecting one irrelevant-but-plausible chunk flip an otherwise-correct answer — a direct probe of generation robustness, independent of retrieval quality.

Frameworks in this space — RAGAS, TruLens, ARES (Saad-Falcon et al. 2023), DeepEval — all converge on the same shape (LLM-judged faithfulness/relevancy plus retrieval metrics) and all inherit LLM-as-judge cost and bias caveats: judge models have length bias, position bias, and self-preference, and running a judge over every eval query at every iteration is itself a real line item worth putting through the same discipline as [[Concept - Cost Engineering for LLM Applications]].

## Failure modes

- **Component vs end-to-end divergence**: nDCG gains from adding a [[Concept - Rerankers|reranker]] do not always move final answer quality — if the generator only attends to the first 1–2 chunks regardless of what's retrieved, improving rank 3–10 is invisible downstream. Symptom: retrieval metrics improve in an ablation but the production answer-quality dashboard is flat. Fix: always measure both, and treat a retrieval-only win as provisional until end-to-end faithfulness confirms it.
- **Golden-set rot from re-chunking**: labels are query → gold-chunk-ID pairs; if [[Concept - Chunking Strategies|chunking]] boundaries change (different chunk size, different splitter), the old chunk IDs no longer exist and the golden set silently stops validating anything. Detect by version-pinning the golden set to a chunking scheme and re-labeling on any pipeline change to indexing.
- **Synthetic-set optimism**: an eval set built entirely from LLM-generated questions plateaus at unrealistically high scores because the questions were generated *from* the same text they're meant to retrieve, inflating apparent recall. Detect by periodically sampling real production queries and comparing their score distribution to the synthetic set's.
- **Small-sample noise mistaken for signal**: a nDCG delta of 0.02 across a 50-query golden set is frequently not statistically distinguishable from noise; see [[Concept - Statistical Rigor in Model Evaluation]] before shipping a change on the strength of a small eval-set improvement.

## The non-obvious

The most common mismeasurement in RAG shops isn't a metric bug, it's an organizational one: teams tune retrieval against nDCG@10 in isolation, ship the reranker that improves it, and never verify the improvement moved the metric that actually matters — end-to-end faithfulness or human-judged answer correctness. A reranker can raise nDCG@10 by double digits and leave faithfulness completely flat, because the generator was already ignoring context past position 3. The fix isn't a better retrieval metric; it's refusing to treat retrieval-stage and generation-stage evaluation as substitutable, ever.

## Connections

- [[Concept - LLM-as-Judge]] — RAGAS's faithfulness and relevancy scores are themselves LLM judgments and inherit judge bias, cost, and calibration problems wholesale.
- [[Concept - Statistical Rigor in Model Evaluation]] — a golden set of 50–200 queries needs significance testing before a metric delta is trusted as a real improvement.
- [[Deep Dive - Designing an Eval Harness]] — the general grading/logging/regression infrastructure a RAG eval suite is built on top of.
- [[Concept - Rerankers]] — reranker-driven retrieval gains are the textbook case where component and end-to-end evaluation diverge.
- [[Gotchas - RAG Pipelines]] — most named RAG failure modes are only visible in production because a retrieval or generation eval caught them first.
- [[Concept - Chunking Strategies]] — golden query-to-chunk labels are only valid until the chunking scheme changes; re-chunking silently invalidates the eval set.
- [[Deep Dive - RAG Architectures]] — different architecture tiers (agentic, graph) need eval axes beyond simple top-k recall.
- [[Concept - Retrieval-Augmented Generation]] — the system this note exists to measure.
- [[Concept - Training Set Decontamination]] — synthetic golden-set answer leakage is the same underlying failure mode (Data Engineering domain) as pretraining-set contamination, just at eval-set-construction time instead of pretraining time.
- [[Concept - Cost Engineering for LLM Applications]] — LLM-as-judge scoring is a recurring per-query cost line item (Production & Ops domain) that has to be budgeted like any other inference cost.

## Sources

- Es et al. (2023) — RAGAS: Automated Evaluation of Retrieval Augmented Generation. Defines faithfulness, answer relevancy, and context precision/recall as LLM-judged metrics without requiring gold labels.
- Saad-Falcon et al. (2023) — ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. Trains lightweight classifiers on LLM-judge labels to cut per-query judging cost at scale.
