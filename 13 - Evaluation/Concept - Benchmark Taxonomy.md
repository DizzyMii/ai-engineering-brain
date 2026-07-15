---
tags: [concept, domain/evaluation, level/surface]
aliases: []
summary: "Benchmarks vary on two independent axes — what capability they measure and how they're scored — and the scoring axis governs reproducibility more."
---
> **One-paragraph hook:** Every LLM benchmark you'll ever cite is a point in a two-dimensional space: what it measures (knowledge, math, code, instruction-following, long-context...) and how it turns a model output into a number (log-likelihood over fixed options, generate-then-parse, execution against tests, a model judge, human preference). Engineers usually argue about the first axis — "is this a good math benchmark?" — when the second axis is the one that actually determines whether the number means anything across two different runs.

## The mechanism

Think of every benchmark as living at the intersection of two orthogonal choices.

**Axis 1 — WHAT is measured (the capability):** knowledge recall, multi-step reasoning, math, code generation, instruction-following, long-context retrieval, multilinguality, safety/refusal behavior, multimodal understanding. This axis is what marketing decks talk about.

**Axis 2 — HOW it is scored (the paradigm):** this is the axis that determines whether a reported score is reproducible, gameable, or comparable across papers.

- **Closed-form log-likelihood.** The model never generates; you compare $P(\text{option} \mid \text{prompt})$ across a fixed set of candidate completions and take the argmax. Cheap, deterministic given a fixed harness, but sensitive to normalization choices (see [[Concept - Answer Scoring and Normalization]]). MMLU and HellaSwag in their canonical form are scored this way.
- **Generation-plus-parse.** The model free-generates; a regex or parser extracts the final answer, which is then checked for exact match. GSM8K, MATH, and AIME work this way — the extraction step is a silent source of both false positives (lucky substring match) and false negatives (correct but differently-formatted answer).
- **Execution-based.** The generated artifact (code, a patch) is actually run against test cases; correctness is unfakeable by surface-form tricks. HumanEval, MBPP, LiveCodeBench, and SWE-bench are execution-graded — see [[Breakdown - MMLU]] for a scored-comparison contrast and [[Breakdown - SWE-bench]] for the execution end of this spectrum. IFEval is a related but distinct case: programmatic checks (e.g., "response must contain exactly 3 bullet points") rather than test execution.
- **Model-judged.** A strong LLM scores or ranks outputs. MT-Bench, AlpacaEval, and Arena-Hard use this paradigm — see [[Concept - LLM-as-Judge]] for the full mechanics.
- **Human-preference.** Crowdsourced pairwise votes aggregated into a rating, as in Chatbot Arena.

Metric families layer on top of the paradigm: accuracy/exact-match and F1 for closed-form and parsed tasks; pass@k for execution-based sampling (see [[Concept - Pass@k and Sampling-Based Evaluation]]); Elo/Bradley-Terry and win-rate for preference paradigms; BLEU/ROUGE, which measure n-gram overlap and are largely dead as generation-quality metrics because they correlate poorly with human judgment on open-ended text.

A score is meaningless without its baselines. MMLU's random baseline is 25% (four options); its reported human-expert baseline is ~89.8%. A model scoring 45% on MMLU is doing almost nothing interesting relative to chance plus partial knowledge; a model scoring 85% is near the ceiling human experts set. Every benchmark carries this identity triplet — random baseline, human baseline, current SOTA — and a bare percentage without it is not evaluable.

## In practice

A practical map, one canonical exemplar per major cell:

| Capability | Scoring paradigm | Exemplar |
|---|---|---|
| Knowledge / reasoning MCQ | log-likelihood | MMLU, GPQA |
| Math | generate + parse | GSM8K, MATH, AIME |
| Code | execution-based pass@k | HumanEval, MBPP, LiveCodeBench, SWE-bench |
| Instruction-following | programmatic checks | IFEval |
| Chat/open-ended quality | LLM-judged | MT-Bench, AlpacaEval, Arena-Hard |
| Chat/open-ended quality | human preference | Chatbot Arena |
| Long-context | generate + parse (retrieval) | RULER, needle-in-a-haystack |
| Multimodal | mixed (MCQ + generation) | MMMU |

The multiple-choice vs. open-generation distinction is not cosmetic. MCQ measures *recognition* — can the model pick the right answer out of a lineup — and is confounded by option position and letter-symbol binding (see [[Concept - Multiple-Choice Symbol Binding and Position Bias]]). Open generation measures *production* — can the model construct the answer from scratch — but then needs either a parser or a judge to score it, each with its own failure modes.

An increasingly load-bearing third axis (as of 2026) is static-public vs. contamination-prone vs. live/private. A benchmark that has been on GitHub since 2021 (GSM8K, HumanEval) is presumptively partly memorized by any model trained on a broad web crawl; see [[Concept - Benchmark Contamination]]. This has pushed the field toward held-out and rotating designs — see [[Concept - Private and Dynamic Benchmarks]].

## Failure modes

Benchmarks have a lifecycle, and treating a benchmark's number as timeless is the single most common evaluation mistake. GLUE saturated and was replaced by SuperGLUE, which itself saturated. GSM8K sat above 95% for frontier models by 2024 — a benchmark that discriminates between a random baseline of near-0% and human performance in the 90s is not discriminating between GPT-4-class and Claude-class models once everyone clears 95%. MMLU plateaued around 88-90% for frontier models by 2024, which is why MMLU-Pro (harder distractors, 10 options), GPQA (graduate-level, harder to guess), and Humanity's Last Exam (deliberately far above current ceilings) exist — they replace a saturated instrument rather than patch it.

Symptom of a saturated benchmark: the ranking of top models on it stops correlating with any other capability signal, and gaps between models shrink to within noise (see [[Concept - Statistical Rigor in Model Evaluation]] for how to tell a real gap from noise). Detection: track the score distribution of frontier models over time — a benchmark where every new frontier release scores within 2 points of the last is providing near-zero information.

Reading Axis 1 in isolation without Axis 2 — assuming "this is a reasoning benchmark, so a high score means good reasoning" — ignores that a log-likelihood-scored MCQ reasoning benchmark can be gamed by option-position priors that have nothing to do with reasoning.

## The non-obvious

The scoring paradigm predicts reproducibility better than the topic does. Two labs benchmarking the same model on the same MCQ dataset can get materially different numbers purely from harness choices (chat template applied or not, 0-shot vs 5-shot, log-likelihood of the letter token vs. the full answer text) — this is well documented for MMLU across HELM, lm-eval-harness, and the original release code. Meanwhile an execution-based benchmark like HumanEval is close to harness-invariant because the verifier is a real test suite, not a scoring convention. When picking a benchmark to trust for a go/no-go decision, prefer execution-based over log-likelihood-based, independent of how well the topic matches your use case — the paradigm's reproducibility is often the dominant factor in whether the number will replicate.

## Connections

- [[Reference - LLM Benchmark Landscape]] — the lookup table this taxonomy organizes; go there for the actual rows (size, baselines, saturation status, flaws).
- [[Breakdown - MMLU]] — the canonical worked example of a log-likelihood-scored knowledge benchmark and everything that goes wrong with that paradigm.
- [[Breakdown - SWE-bench]] — the canonical worked example of the execution-based scoring paradigm at the opposite end of the reproducibility spectrum from MMLU.
- [[Concept - LLM-as-Judge]] — the mechanics behind the model-judged scoring paradigm this taxonomy only previews.
- [[Concept - Answer Scoring and Normalization]] — the arcana of how "closed-form log-likelihood" actually turns into a number, which is where most cross-harness discrepancies originate.
- [[Concept - Multiple-Choice Symbol Binding and Position Bias]] — the specific confound behind the MCQ-vs-generation distinction this note flags.
- [[Concept - Statistical Rigor in Model Evaluation]] — a taxonomy cell tells you what's being measured; this tells you whether the measured gap is real.
- [[Concept - The Emergent Abilities Debate]] — capability-axis benchmarks are exactly where claimed "emergence" often turns out to be a metric-choice artifact rather than a real phase transition.
- [[Deep Dive - The Agent Loop]] — agent and tool-use evaluation is a distinct, higher-order capability axis this taxonomy deliberately excludes (owned by domain 10).
- [[Deep Dive - RAG Architectures]] — retrieval-augmented evaluation is likewise a separate axis with its own scoring paradigms (owned by domain 11).
- [[Concept - Benchmark Contamination]] — the static-public-vs-live axis exists largely because contamination erodes the static-public cell over time.
- [[Concept - Pass@k and Sampling-Based Evaluation]] — the metric family that goes with the execution-based scoring paradigm.

## Sources
- Hendrycks et al. (2021) — Measuring Massive Multitask Language Understanding. Defines MMLU and its random/human baselines.
- Wang et al. (2019) — SuperGLUE. The canonical example of a benchmark built to replace a saturated predecessor (GLUE).
- Rein et al. (2023) — GPQA: A Graduate-Level Google-Proof Q&A Benchmark. A knowledge/reasoning MCQ benchmark designed to resist the saturation MMLU suffered.
