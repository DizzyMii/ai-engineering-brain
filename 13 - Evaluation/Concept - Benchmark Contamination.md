---
tags: [concept, domain/evaluation, level/core]
aliases: [test set leakage, data contamination]
summary: "Test data or its near-duplicates leaking into training corpora inflates benchmark scores without real capability, and perfect decontamination is impossible at web scale."
---
> **One-paragraph hook:** A model that scores 95% on GSM8K might be 95% capable at grade-school math, or it might have seen large fractions of GSM8K — verbatim, paraphrased, or explained in a blog post — somewhere in its pretraining corpus. Benchmark contamination is the specific mechanism by which this happens, and because modern pretraining corpora are scraped from a web that has spent years mirroring, discussing, and solving every popular benchmark, some degree of contamination is now the default assumption for any widely-used public benchmark rather than an edge case.

## The mechanism

Contamination enters through several distinct vectors, and they require different defenses:

- **Direct inclusion.** The benchmark itself, or a full mirror of it, gets scraped — GitHub repos hosting the dataset, HuggingFace dataset pages, academic PDF hosts. This is the crudest and most detectable vector.
- **Indirect leakage.** Solutions, worked examples, or discussions of specific benchmark items appear in blog posts, Stack Overflow answers, or textbooks that get scraped independently of the benchmark's own release. Much harder to catch because no single source contains the "whole" benchmark.
- **Synthetic-data leakage.** A teacher model that was itself contaminated (or was directly evaluated on the test set during development) generates synthetic training data for a student model — the contamination propagates a generation removed from the original source, which defeats source-level filtering entirely. This interacts directly with [[Concept - Synthetic Training Data]] pipelines, where the provenance of "teacher-generated" examples is rarely audited against benchmark test sets.
- **Outright eval-on-train.** The benchmark's items, or close paraphrases, get included in a fine-tuning or RL dataset because whoever built the data mixture didn't cross-check against held-out evals — see [[Concept - Data Mixtures]] for how mixture composition is decided (or fails to be checked).

**Canary strings** are the field's main voluntary defense: BIG-bench embeds a unique GUID string in each task file specifically so anyone can grep a training corpus (or prompt a trained model) for the canary and get a clean signal of inclusion. This only works as a norm — respecting the canary and excluding tagged content is a convention benchmark authors rely on labs to follow, not something enforceable from outside a lab's data pipeline.

**Rephrasing defeats naive decontamination.** Yang et al. (2023), "Rethinking Benchmark and Contamination for Language Models with Rephrased Samples," is the sharpest demonstration of this: they trained a 13B model on paraphrased and translated versions of test items — no verbatim overlap — and the model reached GPT-4-level scores on the affected benchmark while passing standard n-gram-based decontamination checks cleanly. This is the result that killed confidence in exact-match decontamination as a sufficient defense.

## In practice

Effect sizes are large enough to flip leaderboard rankings: contamination can add tens of points on an affected benchmark relative to a genuinely clean evaluation. The GPT-4 technical report is a notable case of a lab disclosing this directly — it reported contamination findings on several benchmarks and published decontaminated splits alongside the raw numbers, which is closer to best practice than most releases manage. This is also why [[Concept - Training Set Decontamination]] is treated as a first-class pretraining-pipeline step rather than an afterthought: cleaning benchmark overlap out of the corpus before training is cheaper than trying to detect and discount it after the fact. It matters beyond leaderboard bragging rights too — [[Concept - Scaling Laws]] fits (loss vs. compute) are usually validated against benchmark performance, and contaminated eval points distort the fitted compute-optimal frontier the same way they distort a single model's headline score.

**Temporal signal** is the most robust circumstantial evidence for contamination at the ecosystem level: models consistently score higher on benchmark problems dated before their training cutoff than on problems dated after it, holding difficulty roughly constant. This observation is the direct basis for LiveCodeBench's date-windowing design — only counting problems released after a model's training cutoff — and for [[Concept - Private and Dynamic Benchmarks]] more generally, where LiveBench and similar live-refreshed sets exploit the same signal deliberately.

Detection methods, roughly weakest to strongest (full treatment in [[Concept - Membership Inference for Contamination Detection]]):

- **Exact n-gram overlap** — cheap, catches direct inclusion, defeated trivially by paraphrase or translation.
- **Embedding/paraphrase overlap** — catches near-duplicates n-gram matching misses, but expensive at corpus scale and still misses heavily-restructured leakage.
- **Min-K% probability** (Shi et al. 2023) — flags text where the model's least-likely tokens are suspiciously high-probability, a signature of memorization.
- **Guided-prompting completion tests** — prompt the model with the start of a benchmark item and see if it completes it verbatim.
- **Oren et al. (2023) exchangeability test** — checks whether a model's log-probabilities on a benchmark's canonical item ordering are exchangeable with a random ordering; a trained-on-order model breaks exchangeability in a statistically detectable way.

## Failure modes

**Symptom:** a model tops a benchmark leaderboard but underperforms noticeably on the same skill in production or on a freshly-constructed variant. **Cause:** the benchmark score was partly memorization, not capability — this is the [[Concept - Goodhart's Law in Model Evaluation]] pattern with contamination as the specific vector. **Detection:** run a rebuilt, non-overlapping version of the benchmark (the GSM1k approach) and compare; a large drop is the signature.

**Symptom:** n-gram-based decontamination reports "clean," but the model still shows suspiciously high scores. **Cause:** rephrasing, translation, or synthetic-data-mediated leakage that n-gram matching cannot see (the Yang et al. 2023 result). **Detection:** embedding-similarity or paraphrase-aware overlap checks, or the temporal-signal test — does score correlate with pre/post training-cutoff dating.

**Symptom:** a benchmark that was clean at release becomes progressively less trustworthy over successive model generations. **Cause:** every model release effectively adds the benchmark's items (and by now, likely blog-post discussions of them) further into the shared web corpus that subsequent models train on — contamination compounds across the ecosystem over time even without any single lab acting in bad faith. **Detection:** compare a fixed model's score on the original benchmark against a freshly-rebuilt version at increasing time offsets from the benchmark's release date.

## The non-obvious

Perfect decontamination is not achievable at web scale, and treating it as an achievable engineering target rather than a risk-management problem leads teams to over-trust a "we ran decontamination" checkbox. The durable defenses are structural, not exhaustive-filtering: release-date discipline (only trust scores on problems dated after the model's training cutoff), respecting and checking canary strings, and shifting weight toward private or live/dynamic benchmarks (see [[Concept - Private and Dynamic Benchmarks]]) precisely because they sidestep the detection problem rather than trying to solve it. Corpus-level deduplication (see [[Concept - Deduplication at Scale]], owned by domain 05) reduces near-duplicate contamination but does not touch indirect or synthetic-mediated leakage at all — dedup and decontamination are related but non-overlapping defenses, and having one does not imply the other.

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
