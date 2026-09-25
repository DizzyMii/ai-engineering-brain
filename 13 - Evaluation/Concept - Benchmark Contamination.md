---
tags: [concept, domain/evaluation, level/core]
aliases: [test set leakage, data contamination]
summary: "Test data or its near-duplicates leaking into training corpora inflates benchmark scores without real capability, and perfect decontamination is impossible at web scale."
---
> **One-paragraph hook:** a model that scores 95% on GSM8K might be 95% capable at grade-school math. Or it might have seen large fractions of GSM8K (verbatim, paraphrased, or explained in a blog post) somewhere in its pretraining corpus. Benchmark contamination is how that happens. Modern pretraining corpora are scraped from a web that has spent years mirroring, discussing and solving every popular benchmark, so for any widely used public benchmark some contamination is now the default assumption, not an edge case.

## The mechanism

Contamination comes in through several vectors, and each needs a different defense:

- **Direct inclusion.** The benchmark itself, or a full mirror, gets scraped: GitHub repos hosting the dataset, HuggingFace dataset pages, academic PDF hosts. It's the crudest vector and the easiest to detect.
- **Indirect leakage.** Solutions, worked examples or discussions of specific items appear in blog posts, Stack Overflow answers or textbooks that get scraped separately from the benchmark's release. Much harder to catch, because no single source holds the "whole" benchmark.
- **Synthetic-data leakage.** A teacher model that was itself contaminated (or was evaluated directly on the test set during development) generates synthetic training data for a student. The contamination travels one generation away from the original source, which defeats source-level filtering entirely. This ties into [[Concept - Synthetic Training Data]] pipelines, where the provenance of "teacher-generated" examples is rarely audited against benchmark test sets.
- **Outright eval-on-train.** Benchmark items, or close paraphrases, end up in a fine-tuning or RL dataset because whoever built the data mixture didn't cross-check it against held-out evals. [[Concept - Data Mixtures]] covers how mixture composition gets decided (or goes unchecked).

**Canary strings** are the field's main voluntary defense. BIG-bench embeds a unique GUID in each task file so anyone can grep a training corpus (or prompt a trained model) for the canary and get a clean signal of inclusion. It only works as a norm. Benchmark authors rely on labs to respect the canary and exclude tagged content, and nobody outside a lab's data pipeline can enforce that.

**Rephrasing defeats naive decontamination.** Yang et al. (2023), "Rethinking Benchmark and Contamination for Language Models with Rephrased Samples," showed this most clearly. They trained a 13B model on paraphrased and translated versions of test items, with no verbatim overlap, and it reached GPT-4-level scores on the affected benchmark while passing standard n-gram decontamination checks cleanly. That result ended confidence in exact-match decontamination as a sufficient defense.

## In practice

The effects are big enough to flip leaderboard rankings: contamination can add tens of points on an affected benchmark compared with a clean evaluation. The GPT-4 technical report is a notable case of a lab disclosing this directly. It reported contamination findings on several benchmarks and published decontaminated splits next to the raw numbers, closer to best practice than most releases get. It's also why [[Concept - Training Set Decontamination]] is a standard pretraining-pipeline step and not an afterthought: removing benchmark overlap before training is cheaper than detecting and discounting it later. The stakes go beyond leaderboard bragging rights. [[Concept - Scaling Laws]] fits (loss vs. compute) are usually validated against benchmark performance, and contaminated eval points distort the fitted compute-optimal frontier just as they distort one model's headline score.

**Temporal signal** is the strongest circumstantial evidence of contamination across the ecosystem. Models consistently score higher on benchmark problems dated before their training cutoff than on problems dated after, at roughly constant difficulty. LiveCodeBench's date-windowing design (counting only problems released after a model's cutoff) is built on this observation, as are [[Concept - Private and Dynamic Benchmarks]] more generally, where LiveBench and similar live-refreshed sets use the same signal on purpose.

Detection methods, roughly weakest to strongest (full treatment in [[Concept - Membership Inference for Contamination Detection]]):

- **Exact n-gram overlap.** Cheap and catches direct inclusion; paraphrase or translation defeats it trivially.
- **Embedding/paraphrase overlap.** Catches near-duplicates that n-gram matching misses, but it's expensive at corpus scale and still misses heavily restructured leakage.
- **Min-K% probability** (Shi et al. 2023). Flags text where the model's least-likely tokens are suspiciously high-probability, a memorization signature.
- **Guided-prompting completion tests.** Prompt the model with the start of a benchmark item and see whether it completes it verbatim.
- **Oren et al. (2023) exchangeability test.** Checks whether a model's log-probabilities on a benchmark's canonical item ordering are exchangeable with a random ordering. A model trained on that order breaks exchangeability in a statistically detectable way.

## Failure modes

**Symptom:** a model tops a benchmark leaderboard but noticeably underperforms on the same skill in production or on a freshly built variant. **Cause:** the score was partly memorization. This is the [[Concept - Goodhart's Law in Model Evaluation]] pattern, with contamination as the vector. **Detection:** run a rebuilt, non-overlapping version of the benchmark (the GSM1k approach) and compare. A large drop is the signature.

**Symptom:** n-gram decontamination reports "clean," and the model's scores are still suspiciously high. **Cause:** rephrasing, translation or synthetic-data-mediated leakage that n-gram matching can't see (the Yang et al. 2023 result). **Detection:** embedding-similarity or paraphrase-aware overlap checks, or the temporal-signal test: does score track pre/post training-cutoff dating?

**Symptom:** a benchmark that was clean at release gets less trustworthy with each model generation. **Cause:** every model release pushes the benchmark's items (and by now, probably blog-post discussions of them) further into the shared web corpus the next models train on. Contamination compounds across the ecosystem over time even if no single lab acts in bad faith. **Detection:** compare a fixed model's score on the original benchmark with a freshly rebuilt version at increasing time offsets from the release date.

## The non-obvious

Perfect decontamination isn't achievable at web scale. Treating it as an engineering target, when it's a risk-management problem, leads teams to over-trust a "we ran decontamination" checkbox. The durable defenses are structural, not exhaustive filtering: release-date discipline (only trust scores on problems dated after the model's training cutoff), respecting and checking canary strings, and shifting weight toward private or live/dynamic benchmarks (see [[Concept - Private and Dynamic Benchmarks]]), which sidestep the detection problem instead of trying to solve it. Corpus-level deduplication ([[Concept - Deduplication at Scale]], owned by domain 05) reduces near-duplicate contamination but doesn't touch indirect or synthetic-mediated leakage. Dedup and decontamination are related defenses that don't overlap, and having one doesn't give you the other.

## Connections

- [[Concept - Membership Inference for Contamination Detection]] — the detection algorithms in depth, including the current reliability critique of whether they actually work.
- [[Concept - Deduplication at Scale]] — the corpus-hygiene mechanics (owned by domain 05) that reduce near-duplicate contamination at the source.
- [[Concept - Private and Dynamic Benchmarks]] — the structural defense: benchmarks designed so contamination is impossible or self-revealing rather than merely checked-for.
- [[Concept - Synthetic Training Data]] — synthetic-data pipelines are a contamination vector one generation removed from the original leak, and provenance auditing rarely covers them.
- [[Concept - Data Mixtures]] — mixture composition decisions are where eval-set leakage into training data actually gets introduced or caught.
- [[Concept - Training Set Decontamination]] — the pretraining-pipeline-side defense (owned by domain 05) that this note's "detection preview" complements.
- [[Concept - Scaling Laws]] — compute-optimal fits are validated against benchmark scores, so contamination distorts the fitted frontier, not just a single leaderboard cell.
- [[Lore - Benchmark Scandals]] — the concrete incidents (GSM1k, the Open LLM Leaderboard discrepancy) where contamination or its absence became a public story.
- [[Concept - Goodhart's Law in Model Evaluation]] — contamination is the data-time instance of the general proxy-decoupling mechanism this note is scoped to preview, not re-derive.

## Sources
- Yang et al. (2023) — Rethinking Benchmark and Contamination for Language Models with Rephrased Samples. Shows paraphrase-based contamination defeats n-gram decontamination.
- Zhang et al. (2024) — A Careful Examination of Large Language Model Performance on Grade School Arithmetic (GSM1k). Rebuilds GSM8K fresh; quantifies the contamination-linked score gap.
- Shi et al. (2023) — Detecting Pretraining Data from Large Language Models (Min-K% Prob). A leading membership-inference detection method.
- Oren et al. (2023) — Proving Test Set Contamination in Black-Box Language Models. The exchangeability-test detection approach.
- OpenAI (2023) — GPT-4 Technical Report. Discloses contamination findings and reports decontaminated benchmark splits.
