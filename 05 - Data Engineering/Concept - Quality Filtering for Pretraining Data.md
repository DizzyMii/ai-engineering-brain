---
tags: [concept, domain/data-engineering, level/core]
aliases: [data filtering, corpus filtering, quality classifiers]
summary: "The pipeline stage that decides which crawled documents survive: heuristic rules, perplexity scoring, and classifier/LLM-annotator filters."
---
# Concept - Quality Filtering for Pretraining Data

> **One-paragraph hook:** After [[Concept - Text Extraction from Web Pages]] turns HTML into plaintext, most of that plaintext is still garbage — SEO spam, auto-generated boilerplate, keyword-stuffed listicles, and gibberish. Quality filtering is the stage that decides which documents survive, and it is arguably the single highest-leverage lever in pretraining: the difference between a mediocre and a frontier corpus is not more data, it's a better filter deciding what to throw away.

## The mechanism

Quality filtering sits in a fixed position in the [[Deep Dive - The Pretraining Data Pipeline]]: after language ID (filters are language-specific — a Gopher rule tuned on English breaks on Chinese) and *before* the expensive stages, ideally after [[Concept - Deduplication at Scale]] removes exact and near-duplicate documents so you don't waste classifier compute scoring the same page ten times.

```mermaid
flowchart LR
    A[Extracted text] --> B[Language ID]
    B --> C[Heuristic rules]
    C --> D[Dedup]
    D --> E[Perplexity / classifier / LLM-annotator]
    E --> F[Surviving corpus]
```

Three paradigms, increasing in cost and semantic depth:

**1. Heuristic (rule-based) filters.** Cheap structural checks that catch boilerplate, spam, and non-natural text without ever reading for meaning: minimum/maximum document length, mean word length between roughly 3 and 10 characters, symbol-to-word ratio under 0.1, fraction of lines ending in terminal punctuation, presence of common stopwords, bullet/ellipsis ratios. C4 (Raffel et al. 2020) and Gopher/MassiveText (Rae et al. 2021) are the canonical rule sets — see [[Reference - Data Filtering Heuristics]] for the exact constants. These are essentially free per document and run first.

**2. Perplexity-based filters.** Score each document with a small n-gram language model — CCNet (Wenzek et al. 2019) trains a KenLM 5-gram model on Wikipedia — and bucket documents into head/middle/tail thirds by per-token perplexity:

$$\text{PPL}(x) = \exp\left(-\frac{1}{N}\sum_{i=1}^{N} \log p(w_i \mid w_{<i})\right)$$

Low perplexity relative to a "clean" reference (Wikipedia) means the text looks like fluent natural language; high perplexity flags boilerplate, keyword salad, and non-natural text. This is cheap, needs no labels, and is language-agnostic as long as you have per-language reference text — which is why it scales to CCNet's 100+ languages.

**3. Classifier / LLM-annotator filters.** Train a fast classifier — GPT-3 (Brown et al. 2020) used a linear classifier over curated positives (Wikipedia, WebText-like references) versus random Common Crawl negatives, then kept documents probabilistically via a Pareto-distribution threshold rather than a hard cutoff, preserving some tail diversity. FineWeb-Edu (Penedo et al. 2024, see [[Breakdown - FineWeb and FineWeb-Edu]]) goes further: prompt Llama-3-70B-Instruct to rate ~460k samples for "educational value" on a 0–5 scale, then distill those ratings into a cheap linear classifier over embeddings so it can be applied at trillion-token scale. Keep documents scoring ≥3.

## In practice

Order matters and is not arbitrary: language ID must run first because every downstream rule is language-specific; heuristics run before the expensive classifier because they're nearly free and remove the easy 50%+ of junk cheaply; dedup should run before quality scoring so you don't pay classifier cost N times for N copies of the same page. Skipping this ordering is a common and expensive mistake in first-pass pipelines.

Expect brutal survival rates. A raw Common Crawl dump loses the overwhelming majority of its documents to filtering plus dedup combined — typical open pipelines keep on the order of 1–15% of input as final tokens (RefinedWeb kept roughly 11%). A survival rate above ~50% after the full stack usually means your filters are too weak; well under ~0.5% usually means they're too aggressive and you're throwing away usable text along with the garbage.

FineWeb-Edu's classifier moves the needle in a measurable way: filtering the same raw pool down to documents scoring ≥3 produced 5–7 point jumps on knowledge benchmarks like MMLU and ARC versus the unfiltered or lightly-heuristic-filtered baseline at matched token count — a concrete illustration of [[Concept - The Data-Centric View of Model Quality]]'s claim that curation moves downstream accuracy more than architecture does at fixed compute.

## Failure modes

**Over-filtering induces distribution shift.** Every filter is a value judgment about what "good" text looks like, and aggressive filtering doesn't just remove junk — it narrows the corpus toward whatever the filter's positives looked like. The canonical cautionary tale is [[Lore - The C4 Blocklist Incident]]: a lexical "bad words" blocklist, applied to build C4, disproportionately deleted LGBTQ+ content, discussion of sexual health, and text in African-American-aligned English, while unrelated harmful content survived because it didn't contain listed words.

**Classifiers learn surface features, not quality.** A classifier trained with Wikipedia-like positives learns to detect formality and topic, not truth or reasoning depth — code, poetry, dialogue, and dialect-marked text score low not because they're bad but because they don't look like the reference class. This is a real form of the same proxy-vs-target gap that shows up in reward modeling.

**Scoring before dedup wastes compute and biases thresholds.** If ten near-identical copies of a viral spam page enter the classifier pass, you pay for all ten scores, and if that page happens to score well, its weight in the "survivors" pool is inflated tenfold.

## The non-obvious

The field's best evidence against trusting a filter's internal precision is DCLM (Li et al. 2024, see [[Decision - Choosing a Quality Filtering Strategy]]): it fixes the model architecture and the raw candidate pool and treats the filtering pipeline as the only variable, which is the only way to know a filter change actually helped rather than just feeling principled. FineWeb's own methodology follows the same discipline — every filtering choice was validated by training a 1.8B model on 350B tokens and comparing against a fixed eval suite, not by trusting the filter's precision on a held-out sample of its own training distribution. If you can't point to an ablation that trained a model with and without your filter, you don't actually know whether it helped.

## Connections
- [[Reference - Data Filtering Heuristics]] — the exact rule constants (Gopher, C4, RefinedWeb) this note deliberately leaves out to stay a mechanism note, not a lookup sheet.
- [[Decision - Choosing a Quality Filtering Strategy]] — how to pick among the three paradigms for a given compute budget and language set.
- [[Concept - Entropy and Cross-Entropy]] — perplexity-based filtering is literally cross-entropy under a reference language model; the filter *is* an entropy measurement.
- [[Breakdown - FineWeb and FineWeb-Edu]] — the reference example of an LLM-annotator filter taken to production scale with a published ablation harness.
- [[Concept - Deduplication at Scale]] — the pipeline-ordering partner: dedup should generally run before the expensive classifier pass.
- [[Lore - The C4 Blocklist Incident]] — the canonical failure mode of a filter encoding its author's blind spots as "clean."
- [[Concept - Common Crawl and Web Data at Scale]] — the raw material every quality filter operates on; filtering exists because Common Crawl is mostly not usable as-is.
- [[Concept - LLM-as-Judge]] — the FineWeb-Edu annotator is structurally the same move as LLM-as-judge evaluation: use a strong model's judgment as a cheap, distillable label source.

## Sources
- Raffel et al. (2020) — "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer": the C4 heuristic filter set.
- Rae et al. (2021) — "Scaling Language Models: Methods, Analysis & Insights from Training Gopher": the MassiveText heuristic rule set, more extensive than C4's.
- Wenzek et al. (2019) — "CCNet: Extracting High Quality Monolingual Datasets from Web Crawl Data": KenLM perplexity-bucket filtering, scaling to 100+ languages.
- Brown et al. (2020) — "Language Models are Few-Shot Learners" (GPT-3): the classifier + Pareto-threshold quality filter used for GPT-3's training corpus.
- Penedo et al. (2024) — "FineWeb: decanting the web for the finest text data at scale": the LLM-annotator-distilled classifier behind FineWeb-Edu.
- Li et al. (2024) — "DataComp-LM: In search of the next generation of training sets for language models": a standardized benchmark isolating filtering pipelines as the sole variable.
