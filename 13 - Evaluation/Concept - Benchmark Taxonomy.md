---
tags: [concept, domain/evaluation, level/surface]
aliases: []
summary: "Benchmarks vary on two independent axes — what capability they measure and how they're scored — and the scoring axis governs reproducibility more."
---
> **One-paragraph hook:** every LLM benchmark you'll cite is a point in a two-dimensional space. One axis is what it measures (knowledge, math, code, instruction-following, long-context...). The other is how it turns a model output into a number (log-likelihood over fixed options, generate-then-parse, execution against tests, a model judge, human preference). Engineers usually argue about the first axis ("is this a good math benchmark?"), but the second decides whether the number means anything across two different runs.

## The mechanism

Every benchmark sits where two independent choices meet.

**Axis 1: WHAT is measured (the capability).** Knowledge recall, multi-step reasoning, math, code generation, instruction-following, long-context retrieval, multilinguality, safety/refusal behavior, multimodal understanding. Marketing decks talk about this axis.

**Axis 2: HOW it is scored (the paradigm).** This axis decides whether a reported score is reproducible, gameable, or comparable across papers.

- **Closed-form log-likelihood.** The model never generates. You compare $P(\text{option} \mid \text{prompt})$ across a fixed set of candidate completions and take the argmax. It's cheap and deterministic given a fixed harness, but sensitive to normalization choices (see [[Concept - Answer Scoring and Normalization]]). MMLU and HellaSwag in their canonical form are scored this way.
- **Generation-plus-parse.** The model generates freely; a regex or parser extracts the final answer, which is checked for exact match. GSM8K, MATH, and AIME work this way. The extraction step silently produces both false positives (a lucky substring match) and false negatives (a correct answer formatted differently).
- **Execution-based.** The generated artifact (code, a patch) is run against test cases, and surface-form tricks can't fake correctness. HumanEval, MBPP, LiveCodeBench and SWE-bench are execution-graded; see [[Breakdown - MMLU]] for a scored-comparison contrast and [[Breakdown - SWE-bench]] for the execution end of the spectrum. IFEval is related but different: programmatic checks (e.g., "response must contain exactly 3 bullet points") instead of test execution.
- **Model-judged.** A strong LLM scores or ranks outputs. MT-Bench, AlpacaEval and Arena-Hard work this way; full mechanics in [[Concept - LLM-as-Judge]].
- **Human-preference.** Crowdsourced pairwise votes aggregated into a rating, as in Chatbot Arena.

Metric families sit on top of the paradigm: accuracy/exact-match and F1 for closed-form and parsed tasks; pass@k for execution-based sampling (see [[Concept - Pass@k and Sampling-Based Evaluation]]); Elo/Bradley-Terry and win-rate for preference paradigms. BLEU/ROUGE measure n-gram overlap and are largely dead as generation-quality metrics, because they correlate poorly with human judgment on open-ended text.

A score means nothing without its baselines. MMLU's random baseline is 25% (four options) and its reported human-expert baseline is ~89.8%. A model at 45% on MMLU is doing almost nothing interesting beyond chance plus partial knowledge; one at 85% is near the ceiling human experts set. Every benchmark has this identity triplet (random baseline, human baseline, current SOTA), and a bare percentage without it can't be evaluated.

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

The multiple-choice vs. open-generation split matters. MCQ measures *recognition* (can the model pick the right answer out of a lineup?) and is confounded by option position and letter-symbol binding (see [[Concept - Multiple-Choice Symbol Binding and Position Bias]]). Open generation measures *production* (can the model build the answer from scratch?), but it then needs a parser or a judge to score it, and each has its own failure modes.

A third axis matters more and more (as of 2026): static-public vs. contamination-prone vs. live/private. A benchmark that has sat on GitHub since 2021 (GSM8K, HumanEval) is presumed partly memorized by any model trained on a broad web crawl; see [[Concept - Benchmark Contamination]]. That has pushed the field toward held-out and rotating designs ([[Concept - Private and Dynamic Benchmarks]]).

## Failure modes

Benchmarks have a lifecycle, and treating a benchmark's number as timeless is the most common evaluation mistake. GLUE saturated and was replaced by SuperGLUE, which then saturated too. GSM8K sat above 95% for frontier models by 2024. A benchmark that separates a near-0% random baseline from human performance in the 90s stops separating GPT-4-class from Claude-class models once everyone clears 95%. MMLU plateaued around 88-90% for frontier models by 2024, which is why MMLU-Pro (harder distractors, 10 options), GPQA (graduate-level, harder to guess) and Humanity's Last Exam (deliberately far above current ceilings) exist. They replace a saturated instrument instead of patching it.

Symptom of a saturated benchmark: the ranking of top models stops correlating with any other capability signal, and the gaps shrink to within noise ([[Concept - Statistical Rigor in Model Evaluation]] covers telling a real gap from noise). Detection: track frontier models' scores over time. If every new frontier release lands within 2 points of the last, the benchmark is giving you near-zero information.

Reading Axis 1 without Axis 2 ("this is a reasoning benchmark, so a high score means good reasoning") ignores that a log-likelihood-scored MCQ reasoning benchmark can be gamed by option-position priors unrelated to reasoning.

## The non-obvious

The scoring paradigm predicts reproducibility better than the topic does. Two labs running the same model on the same MCQ dataset can get materially different numbers from harness choices alone (chat template or not, 0-shot vs 5-shot, log-likelihood of the letter token vs. the full answer text). It's well documented for MMLU across HELM, lm-eval-harness and the original release code. An execution-based benchmark like HumanEval is close to harness-invariant, because the verifier is a real test suite and not a scoring convention. For a go/no-go decision, prefer execution-based over log-likelihood-based benchmarks, whatever the topic match with your use case. The paradigm's reproducibility often decides whether the number will replicate.

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
