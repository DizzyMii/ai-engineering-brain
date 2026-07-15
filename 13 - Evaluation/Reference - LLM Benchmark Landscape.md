---
tags: [reference, domain/evaluation, level/core]
aliases: [benchmark cheat sheet, eval benchmark table]
summary: "Comparison matrix of major LLM benchmarks: capability, format, size, baselines, 2026 saturation status, and headline flaws."
---

# Reference - LLM Benchmark Landscape

Numbers below are approximate and move with every frontier release — treat everything as *(as of 2026)* and re-verify before quoting in a launch deck. Rows are grouped by the capability axis; the format/scoring column is the axis that actually determines whether two numbers are comparable — see [[Concept - Benchmark Taxonomy]] for why. Before trusting any single cell, run it through [[Checklist - Trusting a Benchmark Number]].

## Knowledge / reasoning

| Benchmark | Format / scoring | Size | Random baseline | Human baseline | SOTA & saturation (2026) | Headline flaw |
|---|---|---|---|---|---|---|
| MMLU | Log-likelihood MCQ, 4 options | 57 subjects, ~14k test items | 25% | ~89.8% (domain experts) | ~86–90%, plateaued since ~2024 | ~6.5% of questions mis-labeled overall, some subjects (e.g. virology) >50% wrong — see [[Breakdown - MMLU]] |
| MMLU-Pro | Log-likelihood MCQ, 10 options, harder distractors | Subset of MMLU-derived questions, re-curated | ~10% | Not separately re-normed | Below MMLU's plateau — headroom restored by construction | Newer, less independently audited than MMLU itself |
| MMLU-Redux | Log-likelihood MCQ | Re-annotated sample of MMLU | 25% | — | Tracks MMLU minus the label-error tax | Only covers a re-annotated subset, not the full 14k |
| GPQA-Diamond | Log-likelihood / generate MCQ, 4 options | ~198 items | 25% | Domain PhDs materially above non-expert skilled googlers | Frontier models well below domain-expert ceiling, closing over 2024–2026 | Tiny n → wide confidence intervals on any reported delta — see [[Concept - Statistical Rigor in Model Evaluation]] |
| Humanity's Last Exam | Mixed MCQ + generation, expert-authored | Thousands of items across many disciplines | Near 0% by design | Expert-level per item | Deliberately far below saturation at launch (2025) | Built explicitly to outlast the saturation problem, so "SOTA" is a moving, low number by design |
| ARC-Challenge | Log-likelihood MCQ, 4 options | ~2.5k grade-school science questions | 25% | High | Saturated for frontier models | Easy relative to modern frontier capability; low discriminative power today |
| HellaSwag | Log-likelihood MCQ, sentence completion | ~10k test items | 25% | High | ~95%+ for frontier models | Label noise in the distractor set inflates the effective ceiling |
| BIG-Bench-Hard (BBH) | Mixed, generate + parse | 23 hard BIG-bench tasks | Task-dependent | Task-dependent | Uneven — some tasks saturated, some not | Aggregation across heterogeneous tasks hides which specific skill moved |
| MuSR | Generate + parse, multi-step reasoning | Hundreds of long-form reasoning items | Low | High | Not saturated | Long-context length makes cost per item high relative to MCQ benchmarks |
| TruthfulQA | Generate + parse or judged | ~800 questions | Low | High | Frontier models still trip on it | Rewards evasive non-answers as "truthful," conflating truthfulness with refusal |

## Math

| Benchmark | Format / scoring | Size | SOTA & saturation (2026) | Headline flaw |
|---|---|---|---|---|
| GSM8K | Generate + parse, exact-match final number | ~1.3k test items | Saturated, ~95%+ since 2024 | On the web since 2021 — presumptively contaminated (see [[Concept - Benchmark Contamination]]) |
| MATH | Generate + parse, symbolic equivalence check | ~5k competition problems | High but not fully saturated | Equivalence checking has false negatives (unsimplified forms) and false positives (lucky substrings) |
| AIME | Generate + parse, exact numeric answer | ~30 items/year | High variance run to run | One question is ~3.3% of the score — most reported AIME gaps between models are not statistically significant |
| GSM-Symbolic | Generate + parse, procedurally varied | Templated variants of GSM8K-style problems | Accuracy drops and variance rises vs. static GSM8K on the same underlying problem | Isolates whether a model learned the *structure* or memorized surface forms |
| GSM1k | Generate + parse, freshly authored | ~1k new grade-school problems | 8–13% drop vs. GSM8K for several model families | The direct contamination-quantification instrument for GSM8K |

## Code

| Benchmark | Format / scoring | Size | SOTA & saturation (2026) | Headline flaw |
|---|---|---|---|---|
| HumanEval | Execution-based pass@k | 164 hand-written problems | Saturated | On the web for years — heavily contaminated; also small enough that a handful of items dominate the score |
| MBPP | Execution-based pass@k | ~1k crowd-written problems | High, approaching saturation | Simpler tasks than HumanEval; ceiling effects similar |
| LiveCodeBench | Execution-based pass@k, date-windowed | Rolling window of post-cutoff problems | Not saturated by construction | Only as fresh as its problem-sourcing cadence |
| BigCodeBench | Execution-based, function-call-heavy tasks | ~1.1k tasks | Meaningfully below HumanEval-style scores | Tests library/API use, not just algorithmic code — harder to compare across papers |
| SWE-bench / SWE-bench Verified | Execution-based, fail-to-pass + pass-to-pass tests | 2,294 original / 500 Verified (human-filtered) | ~2% (2023) → 60–70%+ on Verified (2025–26) | Measures scaffold+model system, not the base model alone — see [[Breakdown - SWE-bench]] |

## Instruction-following / chat quality

| Benchmark | Format / scoring | Size | SOTA & saturation (2026) | Headline flaw |
|---|---|---|---|---|
| IFEval | Programmatic instruction checks | Several hundred prompts with verifiable constraints | High for frontier instruction-tuned models | Only catches constraints expressible as a program; says nothing about substantive quality |
| MT-Bench | LLM-judged, multi-turn | 80 questions, 8 categories | Near-ceiling for frontier judges/models | Small, single-judge-model dependent, superseded in difficulty by Arena-Hard |
| AlpacaEval 2.0 | LLM-judged, length-controlled win-rate | Several hundred instructions | Not a fixed ceiling — win-rate is relative to a baseline model | Raw (non-length-controlled) version was gamed by verbosity before the LC fix shipped |
| Arena-Hard-Auto | LLM-judged, pairwise vs. baseline | ~500 curated hard prompts | More separable than MT-Bench, not saturated | Still inherits whatever biases the underlying judge model has — see [[Concept - LLM-as-Judge]] |
| Chatbot Arena | Crowd pairwise votes, Bradley-Terry Elo | >2–3M votes accumulated by 2024–25 | Living benchmark, no fixed ceiling | Style/length confound and governance disputes — see [[Breakdown - Chatbot Arena]] |

## Long-context / multimodal

| Benchmark | Format / scoring | Size | SOTA & saturation (2026) | Headline flaw |
|---|---|---|---|---|
| RULER | Generate + parse, synthetic long-context tasks | Configurable context lengths, commonly tested to 128k+ | Frontier models degrade well before their advertised max context | "Advertised context length" and "usable context length" diverge — RULER exists to expose the gap |
| Needle-in-a-haystack | Generate + parse, retrieval probe | Configurable | Largely solved for simple single-needle retrieval at frontier | Easy variants are saturated; multi-needle and reasoning-over-retrieved-facts variants are not |
| MMMU | Mixed MCQ + generation, multimodal | Roughly 11.5k college-level questions across ~30 subjects | Below human-expert level | Combines multiple modalities and question types into one blended score, obscuring which modality is weak |

## Footnotes

- **Random / human baselines** are not cosmetic — a bare percentage without them is not evaluable; see [[Concept - Benchmark Taxonomy]].
- **HellaSwag** and **ARC-Challenge** label noise means neither benchmark's ceiling is 100% even in principle.
- **TruthfulQA** conflates "truthful" with "unhelpfully evasive" — a model that refuses to answer scores well without being useful.
- **GSM8K** and **HumanEval** are both saturated *and* contaminated — a high score on either is now closer to a floor check than a differentiator.
- **AIME**'s ~30 items/year means single-question granularity (~3.3%) — always report the item count alongside any AIME percentage.

## Connections

- [[Concept - Benchmark Taxonomy]] — the two-axis (what/how) framework this table's rows and columns are organized around; read that first to interpret any cell here.
- [[Breakdown - MMLU]] — full reverse-engineering of the MMLU row: construction, scoring-implementation variance, and the label-error findings behind its "headline flaw" cell.
- [[Breakdown - SWE-bench]] — full construction, subset history, and score trajectory behind the SWE-bench row (owned by domain 20, the applied-software case study of this benchmark).
- [[Breakdown - Chatbot Arena]] — full rating mechanics, style-control fix, and governance controversy behind the Chatbot Arena row.
- [[Concept - Statistical Rigor in Model Evaluation]] — why a single cell in this table is a random variable, not a fixed number, and how to compare two rows without fooling yourself.
- [[Reference - Model Genealogy]] — the companion lookup for which specific model checkpoint produced a given SOTA number, cross-referenced against this table.
- [[Concept - Benchmark Contamination]] — the mechanism behind the "presumptively contaminated" and "contamination exposure" flags attached to long-public rows like GSM8K and HumanEval.
- [[Concept - LLM-as-Judge]] — the scoring mechanism behind every row in the instruction/chat section, and the biases that complicate reading those cells at face value.
- [[Checklist - Trusting a Benchmark Number]] — the pre-flight discipline to run against any single cell in this table before it goes into a decision document.

## Sources
- Hendrycks et al. (2021) — Measuring Massive Multitask Language Understanding. Defines MMLU, its baselines, and subject taxonomy.
- Chen et al. (2021) — Evaluating Large Language Models Trained on Code (Codex/HumanEval). Defines HumanEval and the pass@k estimator.
- Jimenez et al. (2023) — SWE-bench: Can Language Models Resolve Real-World GitHub Issues? Defines the SWE-bench construction and grading.
- Zheng et al. (2023) — Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. Defines MT-Bench and the Arena judge methodology.
- Rein et al. (2023) — GPQA: A Graduate-Level Google-Proof Q&A Benchmark. Defines GPQA and its expert/non-expert baseline gap.
