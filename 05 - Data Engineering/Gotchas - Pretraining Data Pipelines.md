---
tags: [gotchas, domain/data-engineering, level/unicorn]
aliases: [data pipeline bugs, corpus build failures, pretraining data gotchas]
summary: "The bugs and silent quality killers of web-scale corpus building — contamination, verbatim memorization, shuffle NaNs, filter narrowing."
---
# Gotchas - Pretraining Data Pipelines

None of these show up until *after* you've committed real compute. A bad corpus doesn't throw at build time; it produces a worse model, an embarrassing eval number, or a legal problem weeks later. The common rule: measure the *downstream* effect, not the intermediate metric the stage optimizes. [[Deep Dive - The Pretraining Data Pipeline]] covers how the stages compose, [[Playbook - Building a Pretraining Corpus from Common Crawl]] has the do-it-right ordering, and [[Lore - The OPT-175B Logbook]] is the canonical war story for how real this pain is. Ordered by how much it hurts.

## 1. Benchmark scores come back suspiciously high

**Symptom:** your model posts MMLU / GSM8K / HumanEval numbers above your architecture's plausible range, or improves on a benchmark you didn't target. **Cause:** contamination leaked in. Either you ran [[Concept - Training Set Decontamination|decontamination]] only against benchmarks you knew about at crawl time, or the contamination is paraphrased/translated/reformatted and slipped past exact n-gram matching. Benchmark items live on GitHub, HuggingFace and blogs, so *every* web crawl is contaminated by default. **Fix:** decontaminate with n-gram *and* semantic (embedding) overlap against every eval set, and hold out benchmarks released *after* your crawl date as a clean control. A post-hoc "we'll just analyze the impact" is the GPT-3 admission all over again (Brown et al. 2020 §4 shipped with a known dedup bug instead of retraining). **Detection:** a per-benchmark overlap report at build time, plus the held-out-post-crawl gap. Great pre-crawl scores next to normal post-crawl ones: you're contaminated. [[Concept - Benchmark Contamination]] explains why this is unwinnable in the general case.

## 2. The model emits training text verbatim

**Symptom:** given a document prefix, the model completes it word-for-word, or it regurgitates copyrighted passages and PII. **Cause:** [[Concept - Deduplication at Scale|deduplication]] was too loose or exact-only, so templated near-duplicates survived and got memorized through repetition. Lee et al. (2021, "Deduplicating Training Data Makes Language Models Better") showed near-dedup cuts verbatim emission by roughly **10x**. **Fix:** combine suffix-array exact-substring dedup (drop repeated spans ≥ ~50 tokens) with fuzzy MinHash-LSH (num_perm=128, Jaccard threshold ~0.8). Repeat clean data on purpose; don't let junk repeat by accident. **Detection:** Carlini-style extraction. Prompt with held-out document prefixes and measure the verbatim continuation rate (Carlini et al. 2021 showed unfiltered training data is recoverable from weights). Make it a release gate.

## 3. A quality filter silently narrowed the corpus

**Symptom:** the model is weaker on code, dialects or niche topics than the ablation predicted, and you can't find a bug. **Cause:** the [[Concept - Quality Filtering for Pretraining Data|quality classifier]] learned surface features of its positive set. Train it with only Wikipedia/OpenWebText as positives and it learns *formality and topic*, then drops code, lists, poetry and minority dialects. That's the same distribution-narrowing behind [[Lore - The C4 Blocklist Incident]]. A high internal precision score tells you nothing: the filter is precise about the wrong target. **Fix:** validate every filter with held-out **ablation** (train a small model on the filtered vs unfiltered variant and compare downstream), never internal precision. Hand-audit a random sample of *rejected* documents. **Detection:** look at the rejected pile and compare the language/topic histogram before and after. A filter that drops 40% of your code is obvious if you look and invisible if you trust the AUC.

## 4. Loss NaNs or spikes in the first few hundred steps

**Symptom:** training diverges almost immediately, or loss oscillates violently early. **Cause:** usually data ordering, not the optimizer: unshuffled shards with one domain clustered at the start, a corrupt/truncated shard, or a single pathological repeated document (a 50MB log file, a page of repeated characters). The optimizer side is in [[Concept - Training Stability and Loss Spikes]]; rule out data first, it's cheaper. **Fix:** global seeded shuffle *after* mixture weighting, per-document length caps, and shard checksums written at build time. **Detection:** plot loss against data-order/step index. A spike that recurs at a fixed data offset points straight at a bad shard or an unshuffled block. A decode-roundtrip on a random shard catches corruption before you touch a GPU.

## 5. Global deduplication made the model worse

**Symptom:** you deduped harder (cross-dump global MinHash) and downstream accuracy *dropped*. **Cause:** the FineWeb finding. Global cross-dump [[Concept - Deduplication at Scale|dedup]] disproportionately removes *high-quality* content duplicated across many dumps (it got re-crawled because it's good) and up-weights unique low-quality text. The dup rate went down and quality went down with it. **Fix:** dedup *per dump/shard*, not globally across the whole corpus. **Detection:** measure the *downstream* effect of dedup granularity via ablation, not the duplicate rate. The stage's own metric (fewer dups) is anticorrelated with the one you care about.

## 6. The corpus can't be reproduced

**Symptom:** you rebuild "the same" corpus months later and get materially different data and a different model. **Cause:** filter configs, tool versions and RNG seeds weren't pinned. A `trafilatura` version bump silently changes extraction, a different fastText model version relabels languages, an unseeded shuffle reorders everything. **Fix:** version and hash the *entire* pipeline, with pinned tool versions, filter configs and seeds captured in a manifest (the Dolma toolkit and DataTrove exist for this). The corpus recipe is code; give it a lockfile. **Detection:** rebuild a single shard from the manifest and diff it against the committed artifact. No hash match means your pipeline isn't pinned.

## 7. Mojibake and encoding garbage in the tokens

**Symptom:** the vocabulary and training text contain `Ã©`, `â€™`, replacement characters and other encoding sludge, and downstream you get [[Lore - Glitch Tokens|glitch tokens]] on the rare byte sequences. **Cause:** wrong charset detection at [[Concept - Text Extraction from Web Pages|extraction]] time. A page declared one encoding, served another, and the extractor believed the declaration. **Fix:** normalize with `ftfy` (fixes-text-for-you) after extraction and enforce UTF-8. **Detection:** scan the corpus for the U+FFFD replacement character (`�`) rate and the non-UTF-8 byte fraction. A spike in either flags a charset bug before those bytes become permanent under-trained vocabulary entries.

## 8. The model emits `<EMAIL>` and other PII placeholders

**Symptom:** the model generates literal redaction sentinels like `<EMAIL>`, `<KEY>`, `<PHONE>` in normal output. **Cause:** [[Concept - PII and Toxicity Filtering|PII redaction]] replaced real PII with a fixed, regular placeholder token that shows up often enough to be memorized as ordinary vocabulary. **Fix:** randomize or rate-limit redaction sentinels instead of using one high-frequency token, and consider dropping the highest-frequency cases outright. **Detection:** probe the trained model for placeholder emission on neutral prompts and count sentinel frequency in the corpus. If `<EMAIL>` appears millions of times, it *will* surface.

## Connections
- [[Deep Dive - The Pretraining Data Pipeline]] — the system these failures live inside; each gotcha maps to one stage's silent failure.
- [[Concept - Deduplication at Scale]] — source of gotchas #2, #5: dedup too loose feeds memorization, too global strips quality.
- [[Concept - Training Set Decontamination]] — gotcha #1: decontamination against known-only benchmarks leaves you blind to everything released after your crawl.
- [[Concept - Quality Filtering for Pretraining Data]] — gotcha #3: a classifier optimizing internal precision can narrow the distribution invisibly.
- [[Concept - PII and Toxicity Filtering]] — gotcha #8: over-regular redaction sentinels get memorized and emitted.
- [[Concept - Training Stability and Loss Spikes]] — gotcha #4's optimizer-side counterpart; rule out the data cause first because it's cheaper.
- [[Concept - Benchmark Contamination]] — the eval-side view of gotcha #1; why high scores are guilty until proven clean.
- [[Concept - Text Extraction from Web Pages]] — the stage where charset misdetection (gotcha #7) is introduced before it becomes permanent vocabulary.
- [[Lore - The C4 Blocklist Incident]] — the canonical instance of gotcha #3: a filter that silently deleted whole topics and dialects from the corpus.
- [[Lore - Glitch Tokens]] — where the encoding garbage of gotcha #7 ends up: under-trained tokens that trigger pathological behavior.
- [[Playbook - Building a Pretraining Corpus from Common Crawl]] — the ordered procedure whose verification steps exist to catch exactly these failures early.
- [[Lore - The OPT-175B Logbook]] — the primary-source war story of how much of a large run's pain is data- and infrastructure-shaped, not model-shaped.

## Sources
- Lee et al. (2021) — "Deduplicating Training Data Makes Language Models Better": ~10x reduction in verbatim memorization from near-dedup.
- Carlini et al. (2021) — "Extracting Training Data from Large Language Models": the extraction attack behind the detection method for #2.
- Brown et al. (2020) — GPT-3 paper §4: the documented decontamination bug shipped rather than retrained — the canonical "we shipped it contaminated" admission.
- Penedo et al. (2024) — FineWeb: the per-dump vs global dedup finding behind #5.
