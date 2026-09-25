---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [RAG Eval, retrieval evaluation, RAGAS]
summary: "RAG must be scored as two separate measurement problems — retrieval and generation — or a bad retriever and a bad generator become indistinguishable."
---
> **One-paragraph hook:** Ship a [[Concept - Retrieval-Augmented Generation]] system without an eval harness and you're debugging by vibes. When the answer is wrong you can't tell whether the retriever missed the right passage or the generator ignored one it was handed. RAG evaluation scores retrieval and generation as two separate measurement problems and only then recombines them. That split turns "the bot said something dumb" into a bug report pointing at a specific pipeline stage.

## The mechanism

A RAG pipeline has two failure surfaces, retrieval and generation, and both produce the same visible symptom: a wrong final answer. From outside, a perfect generator fed garbage context looks just like a bad generator fed perfect context. **You can't localize a failure from the final answer alone.** You need per-stage metrics against a labeled golden set.

**Retrieval metrics** ask whether the right evidence surfaced, and where.
- **recall@k**: did at least one gold-relevant chunk appear in the top-$k$, averaged over queries. The blunt, most-cited number.
- **MRR (Mean Reciprocal Rank)**: $\text{MRR} = \frac{1}{|Q|}\sum_{q} \frac{1}{\text{rank}_q}$, where $\text{rank}_q$ is the position of the first relevant chunk for query $q$. It penalizes burying the answer even inside the top-$k$.
- **nDCG@k**: a graded, position-discounted metric, $\text{DCG@k} = \sum_{i=1}^{k} \frac{2^{\text{rel}_i}-1}{\log_2(i+1)}$, normalized by the ideal ordering's DCG (IDCG) to give nDCG $\in [0,1]$. It rewards putting the *most* relevant chunk first, where recall@k only asks that it appear somewhere in the top-$k$. Use it once you have graded (not just binary) relevance labels.
- **hit-rate**: the simplest binary recall variant, good as a sanity check.
- **Context precision/recall**: without hand labels, an LLM judge scores whether each retrieved chunk is relevant and whether all relevant chunks came back. It's a judged proxy for recall@k/precision@k, with all the caveats of [[Concept - LLM-as-Judge]].

**Generation metrics** ask whether the answer is any good given the context that was actually retrieved.
- **Faithfulness / groundedness**: break the answer into atomic claims and check that the retrieved context entails each one. This is the direct hallucination catch. An answer can be fluent and relevant and still completely unfaithful to what was retrieved.
- **Answer relevancy**: does the answer address the question? RAGAS measures it by generating several questions *from* the answer and checking their embedding similarity to the original query.
- **Context utilization**: did the generator use the relevant chunks it got, or ignore them in favor of parametric memory?

RAGAS (Es et al. 2023) turns faithfulness, answer relevancy and context precision/recall into LLM-judged scores on a 0–1 scale. Most teams reach for it first because it needs no gold labels beyond a question set.

## In practice

Build the golden set first. 50–200 hand-labeled query → relevant-chunk pairs, drawn from real or realistic queries, is the common starting size: small enough to label by hand, big enough to catch systematic regressions. Synthetic QA generation (an LLM writes questions from your chunks) bootstraps coverage fast but fails in a well-known way. It tends to produce too-easy questions that echo the source chunk's exact wording, and it risks **answer leakage**, where the "gold" answer is copy-pasted and needs no real retrieval. Unless adversarially filtered, synthetic sets systematically overestimate real-world recall. It's the same leakage failure [[Concept - Training Set Decontamination]] exists to catch on the pretraining side.

RAG-specific robustness tests catch failures that plain recall@k misses:
- **Needle-in-a-haystack**: can retrieval find one specific fact buried in a large corpus at all?
- **Position-bias sweeps**: does answer quality change when the same gold chunk moves from position 1 to position 5 in the context?
- **The distractor test**: does adding one irrelevant but plausible chunk flip an otherwise correct answer? This probes generation robustness directly, independent of retrieval.

The frameworks (RAGAS, TruLens, ARES (Saad-Falcon et al. 2023), DeepEval) all converge on the same shape, LLM-judged faithfulness/relevancy plus retrieval metrics, and all inherit LLM-as-judge cost and bias. Judge models have length bias, position bias and self-preference. Running a judge over every eval query on every iteration is a real line item too, and deserves the same scrutiny as anything in [[Concept - Cost Engineering for LLM Applications]].

## Failure modes

- **Component and end-to-end results diverge.** nDCG gains from adding a [[Concept - Rerankers|reranker]] don't always move final answer quality. If the generator only attends to the first 1–2 chunks whatever is retrieved, improving ranks 3–10 is invisible downstream. Symptom: retrieval metrics improve in an ablation while the production answer-quality dashboard stays flat. Fix: measure both, and treat a retrieval-only win as provisional until end-to-end faithfulness confirms it.
- **Golden-set rot from re-chunking.** Labels are query → gold-chunk-ID pairs. Change the [[Concept - Chunking Strategies|chunking]] boundaries (chunk size, splitter) and the old chunk IDs no longer exist, so the golden set silently stops validating anything. Version-pin the golden set to a chunking scheme and re-label on any indexing change.
- **Synthetic-set optimism.** An eval set built entirely from LLM-generated questions plateaus at unrealistically high scores, because the questions came *from* the text they're supposed to retrieve. Periodically sample real production queries and compare their score distribution with the synthetic set's.
- **Small-sample noise mistaken for signal.** An nDCG delta of 0.02 on a 50-query golden set is frequently indistinguishable from noise. Read [[Concept - Statistical Rigor in Model Evaluation]] before shipping on a small eval-set improvement.

## The non-obvious

The most common mismeasurement in RAG shops is organizational, not a metric bug. Teams tune retrieval against nDCG@10 in isolation, ship the reranker that improves it, and never check that the improvement moved the metric that matters: end-to-end faithfulness or human-judged answer correctness. A reranker can raise nDCG@10 by double digits and leave faithfulness flat, because the generator was already ignoring context past position 3. A better retrieval metric won't fix that. Never treat retrieval-stage and generation-stage evaluation as substitutes for each other.

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
