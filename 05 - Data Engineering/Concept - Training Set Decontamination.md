---
tags: [concept, domain/data-engineering, level/core]
aliases: [decontamination, benchmark decontamination, contamination removal]
summary: "Stripping evaluation benchmarks out of pretraining corpora via n-gram/substring overlap removal — imperfect by construction."
---
# Concept - Training Set Decontamination

> **One-paragraph hook:** Every benchmark you evaluate a model on — MMLU, GSM8K, HumanEval — has its questions and answers published somewhere on the open web, which means a web-scale pretraining corpus is contaminated with eval data by default, not by accident. Decontamination is the targeted dedup pass that tries to strip that overlap out before training, and understanding both how it works and where it structurally fails is the difference between trusting a benchmark number and knowing when not to.

## The mechanism

Contamination enters through an unglamorous, unavoidable channel: benchmark authors publish their test sets — on GitHub, HuggingFace dataset pages, arXiv papers, blog posts explaining the benchmark, and Kaggle notebooks solving it — and a general-purpose web crawl like [[Concept - Common Crawl and Web Data at Scale]] has no way to distinguish "a benchmark's canonical test item" from "any other web page." By the time a corpus reaches trillions of tokens, it contains verbatim or near-verbatim copies of most popular benchmarks' items somewhere in the pile, entirely incidentally.

Decontamination is mechanically a targeted variant of [[Concept - Deduplication at Scale]]: instead of comparing training documents against each other, you compare every training document against every item in every benchmark you plan to evaluate on, and remove (or truncate around) any training document that overlaps too much.

```
for doc in training_corpus:
    doc_ngrams = ngram_set(doc, n)
    for benchmark_item in eval_sets:
        if overlap(doc_ngrams, ngram_set(benchmark_item, n)) > threshold:
            flag_or_remove(doc)
            break
```

Two overlap definitions dominate in practice:
- **n-gram overlap** — GPT-3 (Brown et al. 2020) used 13-gram overlap: if a 13-token window of a training document matches a 13-token window of a benchmark item, the document is flagged.
- **substring overlap** — later pipelines (Llama, GPT-4-era reports) use roughly 50-character exact substring matches, which is cheaper to compute at trillion-token scale and catches near-identical copy-paste contamination directly.

Both are essentially a specialized [[Concept - Deduplication at Scale]] pass with the benchmark set standing in as one side of the comparison — the same MinHash/suffix-array machinery that finds document duplicates within a corpus can be pointed at "corpus vs. benchmark" instead of "corpus vs. itself."

## In practice

The now-famous illustration that decontamination is fallible even for the labs that invented the practice is the **GPT-3 contamination bug** (Brown et al. 2020, section 4): OpenAI intended to filter 13-gram overlaps against their benchmark suite before training, but a bug in the dedup logic let contamination through anyway. Rather than retrain — an enormous sunk cost to discard — they analyzed the impact post hoc, benchmark by benchmark, and published which scores were likely inflated. It stands as one of the field's first documented "we shipped it contaminated, here's our best estimate of the damage" admissions, and it set the norm that followed: contamination is now treated as effectively unavoidable at scale, and disclosure — not perfection — is the expected practice. Modern model reports (Llama, GPT-4-class releases) routinely publish per-benchmark contamination-overlap statistics rather than claiming zero contamination.

A complementary detection mechanism is the **canary string**: benchmark authors (e.g., BIG-bench) embed a unique GUID inside their dataset files specifically so that any pipeline scanning for that literal string can detect — after the fact — whether a given benchmark was ingested into a corpus, giving dataset authors a lightweight audit trail independent of whatever decontamination the corpus builder ran.

Order matters operationally: decontamination runs *after* the bulk of filtering and dedup ([[Deep Dive - The Pretraining Data Pipeline]]) because it's benchmark-specific and comparatively expensive per-document, and because you want it to operate on the corpus as close to its final shape as possible so nothing reintroduces contamination downstream (for instance, [[Concept - Synthetic Training Data]] generated from a contaminated teacher model can silently reintroduce benchmark answers that a web-side decontamination pass never sees).

## Failure modes

**Paraphrase and translation blindness.** n-gram and substring matching are exact-text methods — they catch verbatim copies but miss a benchmark question that's been paraphrased, translated into another language, reformatted into a different template, or embedded inside a blog post discussing the answer in prose. Embedding-based semantic overlap detection catches more of this class but is far more expensive to run at corpus scale and is prone to false positives (flagging genuinely distinct documents that happen to discuss similar topics).

**Blind to future benchmarks.** Decontamination can only strip what you know to check against at build time. A corpus crawled and decontaminated in 2025 against the 2025 benchmark landscape is by definition not decontaminated against any benchmark released in 2026 — there is no way to retroactively fix a corpus that's already baked into trained weights, which is why benchmark authors increasingly treat "was this released after the model's data cutoff" as load-bearing evidence in [[Concept - Benchmark Contamination]] analysis.

**Over-aggressive removal deletes legitimate text.** A short, generic 13-gram or 50-character substring can coincidentally match both a benchmark item and a huge amount of ordinary web prose (a common idiom, a standard code snippet, a frequently-quoted sentence). Tuning the overlap threshold too loose deletes real, useful, non-contaminated documents purely because they share a common phrase with a benchmark — the false-positive side of the same precision/recall tradeoff that governs every filtering stage in the pipeline (see [[Gotchas - Pretraining Data Pipelines]] for the operational symptom: benchmark scores that look suspiciously high are the tell that decontamination under-removed, not that the model got smarter).

## The non-obvious

Decontamination is fundamentally a dedup problem wearing a different hat, but treating it as "just run MinHash again" undersells how much decontamination quality depends on the *tokenization granularity* of the overlap check: n-gram matching operates over whatever units the pipeline chooses — words, characters, or [[Concept - Byte-Pair Encoding]] tokens — and a coarser granularity misses contamination that a finer one would catch, while a finer granularity produces more false positives from short common sequences. There is no threshold that is simultaneously complete and precise; every published decontamination methodology is a specific, disclosed compromise on that tradeoff, which is exactly why model reports increasingly publish their exact overlap definition and threshold alongside their contamination statistics rather than a bare "we decontaminated" claim.

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
