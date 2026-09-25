---
tags: [concept, domain/data-engineering, level/core]
aliases: [decontamination, benchmark decontamination, contamination removal]
summary: "Stripping evaluation benchmarks out of pretraining corpora via n-gram/substring overlap removal — imperfect by construction."
---
# Concept - Training Set Decontamination

> **One-paragraph hook:** Every benchmark you evaluate a model on (MMLU, GSM8K, HumanEval) has its questions and answers published somewhere on the open web, so a web-scale pretraining corpus is contaminated with eval data by default, not by accident. Decontamination is the targeted dedup pass that tries to strip that overlap out before training. Knowing how it works, and where it can't work by design, is what separates trusting a benchmark number from knowing when not to.

## The mechanism

Contamination comes in through a boring channel you can't avoid. Benchmark authors publish their test sets on GitHub, HuggingFace dataset pages and arXiv, and others write blog posts explaining the benchmark and Kaggle notebooks solving it. A general-purpose crawl like [[Concept - Common Crawl and Web Data at Scale]] can't tell "a benchmark's canonical test item" from any other web page. By the time a corpus reaches trillions of tokens, it holds verbatim or near-verbatim copies of most popular benchmarks' items somewhere in the pile, entirely incidentally.

Mechanically, decontamination is a targeted variant of [[Concept - Deduplication at Scale]]. Instead of comparing training documents against each other, you compare every training document against every item in every benchmark you plan to evaluate on, and remove (or truncate around) any document that overlaps too much.

```
for doc in training_corpus:
    doc_ngrams = ngram_set(doc, n)
    for benchmark_item in eval_sets:
        if overlap(doc_ngrams, ngram_set(benchmark_item, n)) > threshold:
            flag_or_remove(doc)
            break
```

Two overlap definitions dominate in practice:
- **n-gram overlap.** GPT-3 (Brown et al. 2020) used 13-gram overlap: if a 13-token window of a training document matches a 13-token window of a benchmark item, the document is flagged.
- **substring overlap.** Later pipelines (Llama, GPT-4-era reports) use roughly 50-character exact substring matches. These are cheaper to compute at trillion-token scale and catch near-identical copy-paste contamination directly.

Both are essentially a specialized dedup pass with the benchmark set on one side of the comparison. The MinHash/suffix-array machinery that finds duplicates within a corpus can be pointed at "corpus vs. benchmark" instead of "corpus vs. itself."

## In practice

The famous proof that decontamination fails even at the labs that invented it is the **GPT-3 contamination bug** (Brown et al. 2020, section 4). OpenAI meant to filter 13-gram overlaps against its benchmark suite before training, but a bug in the dedup logic let contamination through. Retraining would have thrown away an enormous sunk cost, so they analyzed the impact post hoc, benchmark by benchmark, and published which scores were likely inflated. It was one of the field's first documented "we shipped it contaminated, here's our best estimate of the damage" admissions, and it set the norm that followed. Contamination is now treated as effectively unavoidable at scale, and the expected practice is disclosure, not perfection. Modern model reports (Llama, GPT-4-class releases) routinely publish per-benchmark contamination-overlap statistics instead of claiming zero contamination.

The **canary string** is a complementary detection method. Benchmark authors (e.g., BIG-bench) embed a unique GUID in their dataset files so that any pipeline scanning for that literal string can tell, after the fact, whether the benchmark was ingested into a corpus. Dataset authors get a lightweight audit trail that doesn't depend on whatever decontamination the corpus builder ran.

Order matters. Decontamination runs *after* the bulk of filtering and dedup ([[Deep Dive - The Pretraining Data Pipeline]]). It's benchmark-specific and comparatively expensive per document, and you want it working on the corpus as close to final shape as possible so nothing downstream reintroduces contamination. [[Concept - Synthetic Training Data]] generated from a contaminated teacher, for instance, can silently bring back benchmark answers a web-side decontamination pass never sees.

## Failure modes

**Paraphrase and translation blindness.** n-gram and substring matching work on exact text. They catch verbatim copies and miss a benchmark question that's been paraphrased, translated, reformatted into a different template, or embedded in a blog post discussing the answer in prose. Embedding-based semantic overlap detection catches more of this, but it's far more expensive at corpus scale and prone to false positives (flagging distinct documents that happen to discuss similar topics).

**Blind to future benchmarks.** You can only strip what you know to check against at build time. A corpus crawled and decontaminated in 2025 against the 2025 set of benchmarks is by definition not decontaminated against anything released in 2026. A corpus already baked into trained weights can't be fixed retroactively. Benchmark authors therefore increasingly treat "was this released after the model's data cutoff" as central evidence in [[Concept - Benchmark Contamination]] analysis.

**Over-aggressive removal deletes legitimate text.** A short, generic 13-gram or 50-character substring can match both a benchmark item and a huge amount of ordinary web prose by coincidence: a common idiom, a standard code snippet, a frequently quoted sentence. Set the overlap threshold too loose and you delete real, useful, uncontaminated documents because they share a common phrase with a benchmark. It's the false-positive side of the precision/recall tradeoff behind every filtering stage in the pipeline. For the operational symptom of the opposite error, see [[Gotchas - Pretraining Data Pipelines]]: suspiciously high benchmark scores mean decontamination under-removed, not that the model got smarter.

## The non-obvious

Decontamination is a dedup problem in a different hat, but "just run MinHash again" undersells how much its quality depends on the *tokenization granularity* of the overlap check. n-gram matching runs over whatever units the pipeline picks: words, characters, or [[Concept - Byte-Pair Encoding]] tokens. Coarser units miss contamination that finer ones would catch, and finer units throw more false positives from short common sequences. No threshold is both complete and precise. Every published decontamination method is a specific, disclosed compromise on that tradeoff, and model reports increasingly publish their overlap definition and threshold next to their contamination statistics instead of a bare "we decontaminated."

## Connections
- [[Concept - Benchmark Contamination]] — the evaluation-side twin of this note: how contamination is *detected and reported* once it's already in a trained model, versus how it's *removed* before training.
- [[Concept - Deduplication at Scale]] — decontamination is mechanically a specialized dedup pass with the benchmark set as one side of the comparison.
- [[Concept - Statistical Rigor in Model Evaluation]] — a benchmark score's validity as a statistic depends on the eval set being unseen; decontamination is the upstream precondition that rigor assumes.
- [[Deep Dive - The Pretraining Data Pipeline]] — decontamination's position late in the stage graph, after filtering and dedup, before mixture assembly.
- [[Gotchas - Pretraining Data Pipelines]] — "benchmark scores suspiciously high" as the field-observed symptom of a decontamination failure.
- [[Concept - Synthetic Training Data]] — a teacher model that memorized a benchmark can reintroduce its answers through generated data, a contamination channel web-side decontamination never sees.
- [[Concept - Common Crawl and Web Data at Scale]] — the reason contamination is the default state of any web corpus: benchmarks get crawled like everything else.
- [[Concept - Byte-Pair Encoding]] — the tokenization granularity that n-gram overlap checks are actually computed over, setting the precision/recall tradeoff of the whole method.

## Sources
- Brown et al. (2020) — "Language Models are Few-Shot Learners" (GPT-3), section 4: the original documented contamination bug and the post hoc impact analysis that set the field's disclosure norm.
- BIG-bench collaboration (2022) — "Beyond the Imitation Game": introduced canary-string self-tagging so dataset authors can audit for ingestion independent of any given lab's decontamination process.
