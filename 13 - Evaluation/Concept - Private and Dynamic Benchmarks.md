---
tags: [concept, domain/evaluation, level/frontier]
aliases: [live benchmarks, held-out benchmarks, dynamic benchmarks, contamination-resistant evaluation]
summary: "Contamination-resistant evaluation via private holdouts, date-windowing, procedural generation, and adversarial-in-the-loop benchmarks."
---
> **One-paragraph hook:** By 2026 every static, public benchmark is on a clock. The day it ships it starts leaking into the next model's pretraining corpus, and within a generation or two the score measures exposure instead of capability. The response is a family of designs that make test data hard to memorize: kept private, refreshed faster than models train, generated fresh per evaluation, or written to beat the current frontier. That's the "eval crisis" answer. If you can't reliably detect that a benchmark has leaked, build one that can't leak.

## The mechanism

A static benchmark is a fixed set of question–answer pairs, and any fixed text eventually gets scraped, mirrored, discussed and solved on the open web through the vectors catalogued in [[Concept - Benchmark Contamination]]. After that the score decouples from the capability it stood in for: [[Concept - Goodhart's Law in Model Evaluation]], with contamination as the vector. There are four families of defense, and each removes a different degree of freedom that memorization relies on.

**1. Private holdouts.** Test items never leave the host's servers. You submit a model or an API endpoint and get back an aggregate score. Scale AI's SEAL leaderboards, the protected portions of GPQA, and ARC-AGI's private evaluation set (the one the ARC Prize is scored on) all work this way. Memorization is off the table because the text is never published. You pay in reproducibility and trust: you can't audit the items or re-run the eval, and you have to trust the host isn't leaking or mis-scoring.

**2. Live / date-windowed.** Keep publishing, but only count items that postdate a model's training cutoff. LiveBench (White et al. 2024) refreshes its question pool monthly from recent arXiv papers, news and competition problems. LiveCodeBench (Jain et al. 2024) stamps each coding problem with its release date and lets you window the leaderboard to "problems released after model X's cutoff." The evidence that this matters comes from LiveCodeBench itself: the *same model* scores measurably lower on post-cutoff problems than on pre-cutoff ones of matched difficulty. That's a direct, in-the-wild contamination signal, not an inferred one. The cost is cross-time comparability, since a score on July's questions isn't strictly comparable to one on January's.

**3. Procedural / templated generation.** Store *generators* instead of questions. GSM-Symbolic (Mirzadeh et al. 2024, Apple) re-instantiates GSM8K problems by swapping names, entities and numeric values through symbolic templates, giving an unbounded stream of unseen variants. What made it famous: frontier models showed a mean accuracy drop and, more tellingly, *high variance across variants of the same problem*. Changing only a name or a number moved the score, which is evidence of pattern-matching on surface form. GSM1k (Zhang et al. 2024) is the manual version, with humans rebuilding grade-school problems from scratch in the GSM8K style. The risk is narrowness. A template only generates the distribution its authors thought to encode.

**4. Adversarial-in-the-loop.** Put a human writer against the current model and keep only the examples that fool it. DynaBench (Kiela et al. 2021) and Adversarial NLI (Nie et al. 2020) did this, regenerating the benchmark continuously to stay *ahead* of the models, so it can't saturate. The cost is that difficulty is defined relative to one model generation, so the set drifts.

A crowdsourced Elo leaderboard like [[Breakdown - Chatbot Arena]] sits slightly apart. It's effectively a living benchmark: prompts come from real users in real time and are never published as a fixed set. You get fresh and private for free, and pay with an uncontrolled prompt distribution.

| Family | Example | Memorization channel closed by | You pay in |
|---|---|---|---|
| Private holdout | SEAL, GPQA protected, ARC-AGI private | Never publishing the items | Reproducibility, host trust |
| Live / date-windowed | LiveBench, LiveCodeBench | Only scoring post-cutoff items | Cross-time comparability |
| Procedural / templated | GSM-Symbolic, GSM1k | Generating fresh variants | Narrowness of the template |
| Adversarial-in-the-loop | DynaBench, ANLI | Regenerating to beat the frontier | Difficulty is model-relative |

## In practice

Pick the family by the failure you most need to prevent. If you're worried about one model's headline number being memorized, date-windowing is the cheapest honest fix and needs no new host infrastructure. It uses the same temporal signal as membership-based detection ([[Concept - Membership Inference for Contamination Detection]]), but proactively instead of forensically. For a competitive leaderboard where labs have an incentive to overfit, a private holdout with API-only submission is the only thing that survives adversarial pressure, and you accept becoming a trusted third party. To probe reasoning robustness, procedural generation is the sharpest tool, because variance across variants is itself the finding.

[[Reference - LLM Benchmark Landscape]] shows which mainstream benchmarks already have live or private variants (LiveCodeBench for HumanEval-style coding, GPQA for MMLU-style knowledge), so you can swap in a contamination-resistant equivalent instead of defending a saturated public set. Dynamic benchmarks exist because the classic static ones hit [[Concept - Benchmark Saturation]] and lost their headroom; the design is a response to that curve flattening.

## Failure modes

**Symptom:** a private-holdout leaderboard shows a suspicious ordering nobody can reproduce or contest. **Cause:** you moved the trust problem without solving it. The host controls scoring, subset selection and disclosure, and there's no external audit path. **Detection:** ask for a public *sample* of retired items and a documented scoring harness, and cross-check against a reproducible public benchmark for the same capability. The governance critiques of private multi-variant testing ([[Lore - Benchmark Scandals]]) are this failure in public.

**Symptom:** a templated benchmark shows near-flat scores across variants and everyone calls the model "robust." **Cause:** the template's degrees of freedom are too shallow. Swapping surface tokens without changing reasoning structure tests memorization of *form*. **Detection:** vary structural depth (number of reasoning steps, distractor count) as well as names and numbers, and watch whether variance appears.

**Symptom:** a live benchmark's monthly scores wander and you can't tell improvement from drift in question difficulty. **Cause:** the item distribution changed under you, so month-over-month deltas mix model change with benchmark change. **Detection:** carry a small anchor set of fixed items across refreshes to calibrate difficulty drift, and report per-refresh confidence intervals.

## The non-obvious

*Contamination resistance and reproducibility pull against each other, and you can't maximize both.* A perfectly reproducible benchmark is a fixed, published set, which is what gets contaminated. A perfectly leak-proof one is private or freshly generated, which is what you can't audit or re-run. Every design here buys resistance with some reproducibility, trust or comparability. Ignore that and you end up over-trusting a "private, so it must be clean" leaderboard that is really just unauditable.

The mature move is to run both: a reproducible public set for apples-to-apples engineering deltas, and a contamination-resistant set as a reality check on whether those deltas are capability or exposure. It's the same measurement-artifact caution as in [[Concept - The Emergent Abilities Debate]], where apparent jumps turned out to come from how the thing was measured. None of this replaces corpus-side hygiene either. [[Concept - Training Set Decontamination]] on the training pipeline is complementary: a dynamic benchmark protects *your* score today and does nothing to keep tomorrow's public benchmark out of tomorrow's pretraining run.

## Connections

- [[Concept - Benchmark Contamination]] — the phenomenon these designs are built to defeat; this note is the structural answer to that note's detection problem.
- [[Concept - Goodhart's Law in Model Evaluation]] — the general proxy-decoupling dynamic; dynamic benchmarks are an attempt to keep the measure coupled to the target under optimization pressure.
- [[Breakdown - Chatbot Arena]] — a crowdsourced Elo board that is effectively a living benchmark because its prompt stream is fresh and private.
- [[Concept - Membership Inference for Contamination Detection]] — the forensic alternative; date-windowing uses the same temporal signal proactively instead of trying to detect leakage after the fact.
- [[Reference - LLM Benchmark Landscape]] — the lookup for which mainstream benchmarks already have contamination-resistant live or private variants.
- [[Concept - The Emergent Abilities Debate]] — the cross-domain lesson that measured capability is often a measurement artifact, which is why a reality-check benchmark matters.
- [[Concept - Benchmark Saturation]] — the trajectory-level force (domain 24) that makes static benchmarks lose their headroom and forces the move to dynamic designs.
- [[Concept - Training Set Decontamination]] — the complementary corpus-side defense (domain 05); dynamic benchmarks and pipeline decontamination protect different things and neither substitutes for the other.
- [[Lore - Benchmark Scandals]] — the concrete incidents (GSM1k drops, private-testing governance disputes) where these mechanisms and their failure modes became public stories.

## Sources
- White et al. (2024) — LiveBench: A Challenging, Contamination-Free LLM Benchmark. Monthly-refreshed live evaluation.
- Jain et al. (2024) — LiveCodeBench: Holistic and Contamination-Free Evaluation of LLMs for Code. Date-windowing and the post-cutoff score-drop signal.
- Mirzadeh et al. (2024) — GSM-Symbolic: Understanding the Limitations of Mathematical Reasoning in LLMs. Templated variant generation and variance-across-variants as a robustness probe.
- Zhang et al. (2024) — A Careful Examination of LLM Performance on Grade School Arithmetic (GSM1k). Manually rebuilt fresh problems; quantifies overfit.
- Kiela et al. (2021) — Dynabench: Rethinking Benchmarking in NLP. Adversarial human-in-the-loop benchmark construction.
- Nie et al. (2020) — Adversarial NLI: A New Benchmark for Natural Language Understanding. Iterated adversarial data collection against current models.
- Chollet et al. (ARC-AGI, private-set design) and Scale AI SEAL — API-only private-holdout leaderboards.
