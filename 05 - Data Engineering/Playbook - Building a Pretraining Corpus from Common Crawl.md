---
tags: [playbook, domain/data-engineering, level/advanced]
aliases: []
summary: "End-to-end procedure: fetch WARC dumps, extract, filter, dedup, decontaminate, mix, and shard a Common Crawl corpus for pretraining."
---

> **Goal:** Turn raw [[Concept - Common Crawl and Web Data at Scale]] dumps into a clean, deduplicated, decontaminated, tokenized, sharded corpus ready to feed a training job.
> **When to run this:** Before any from-scratch pretraining run or major continued-pretraining refresh that uses web data as a primary source.
> **Prerequisites:** S3 read access to `s3://commoncrawl/`, a distributed cluster (Spark/Ray/SLURM) with multi-thousand CPU-hours free, a chosen tokenizer, and a frozen list of eval benchmarks to decontaminate against.

```
WARC dumps ──▶ extract ──▶ LID ──▶ filter ──▶ dedup + decontam ──▶ mix + shuffle ──▶ tokenize ──▶ shard
 (~90 TiB)     (CPU-bound)                    (1–15% survives)                                    (GPU-ready)
```

This is the operational trace through [[Deep Dive - The Pretraining Data Pipeline]]. Each step links to the concept note that explains *why* it works that way. Get the ordering wrong (score before dedup, mix before decontaminate) and you either waste compute or ship a contaminated corpus.

## Steps

**1. Fetch.** Pull the selected dumps from `s3://commoncrawl/` as raw **WARC** files, never WET. Expect roughly 90–100 TiB compressed per monthly dump (250+ TiB uncompressed). *Expected observation:* your object listing shows `.warc.gz` segments, not `.wet.gz`. *Deviation:* if a source only offers WET, you've given up control of extraction quality without noticing. WET is Common Crawl's naive pre-extracted plaintext and still carries boilerplate.

**2. Extract.** Run [[Concept - Text Extraction from Web Pages]] over every WARC record with trafilatura or resiliparse, orchestrated by DataTrove or Dolma. *Expected observation:* spot-read 100 random extracted docs. They should read as continuous article prose. *Deviation:* menu items, cookie banners or "Subscribe now" fragments in the text mean the extractor or its config is wrong. Per RefinedWeb's central finding, this is the highest-leverage step to get right.

**3. Language ID.** Route or drop documents with fastText `lid.176`, typically keeping English at a probability threshold around p ≥ 0.65. *Expected observation:* the language histogram roughly matches your target distribution. English will dominate, since Common Crawl is ~44% English documents. *Deviation:* a flat or noisy histogram usually means extraction artifacts (mojibake, truncated text) are corrupting the LID signal, not that LID is broken.

**4. Filter.** Apply heuristic rules first (Gopher/C4-style word count, mean word length, symbol-to-word ratio and terminal-punctuation checks; see [[Reference - Data Filtering Heuristics]]), then run a quality classifier or LLM-annotator on the survivors, per [[Concept - Quality Filtering for Pretraining Data]]. *Expected observation:* 1–15% of input tokens survive. *Deviation:* survival above ~50% means your filters are too weak and junk is getting through. Below ~0.5% you're over-filtering and narrowing the distribution. Validate the choice against [[Decision - Choosing a Quality Filtering Strategy]]; a filter's internal precision won't tell you this.

**5. Dedup + decontaminate.** Run MinHash-LSH per [[Concept - Deduplication at Scale]] (typically `num_perm=128`, similarity threshold ≈0.8) with text-dedup or DataTrove, **within each dump, not globally**. Cross-dump dedup has been shown to strip high-quality repeated content. Then run [[Concept - Training Set Decontamination]]: strip any document with n-gram (e.g. 13-gram) or substring overlap against your eval sets. That amounts to targeted dedup against [[Concept - Benchmark Contamination]]. *Expected observation:* the duplicate rate drops sharply and a per-benchmark overlap report shows ~0% overlap. *Deviation:* nonzero overlap on a benchmark you didn't decontaminate against means you're blind to it. The step only catches benchmarks known at crawl time, never those released later.

**6. Assemble.** Apply your chosen [[Concept - Data Mixtures]] weights, run a global seeded shuffle across the mixed pool, tokenize with [[Concept - Byte-Pair Encoding]], pack sequences to the training `seq_len` with document separators, and write memory-mapped shards (Megatron `.bin`/`.idx`, WebDataset tar, or Mosaic MDS). *Expected observation:* token count matches the mixture's target budget, shard checksums are clean, and decoding a random sample reproduces the source text exactly. *Deviation:* a mismatched token count means a mixture-weighting bug. A failed decode-roundtrip means the tokenizer/vocab differs between build time and training time. Catch it before you touch [[Deep Dive - Anatomy of a Pretraining Run]] and commit GPU-hours.

## Verification

Before handing the corpus to a training job, confirm: (1) final token count matches the planned budget, (2) shards pass checksums and a load-and-decode smoke test on a handful of random shards, (3) the per-benchmark contamination report is clean, and (4) the survival-rate and language-histogram checks from steps 3–4 still hold on the assembled corpus, not just per dump. Reproducibility check: you should be able to re-derive the whole run from a pinned manifest of tool versions, filter configs and the shuffle RNG seed. If you can't, what you have is a one-off artifact, not a corpus.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Loss NaNs or spikes very early in training | Unshuffled shards (one domain/dump clustered together), a corrupt or truncated shard, or a single pathological repeated document | Re-run the global seeded shuffle, add shard checksums, cap per-document length; see [[Gotchas - Pretraining Data Pipelines]] |
| Model emits verbatim training text under prefix prompting | Dedup threshold too loose, or exact-dedup only with no fuzzy pass | Tighten MinHash threshold and add substring dedup; re-run step 5 |
| Benchmark scores are suspiciously high right after launch | Decontamination only ran against known benchmarks, or missed paraphrase/translation-level contamination | Expand the eval set list, add semantic decontam, hold out any benchmark released after the crawl date |
| Extracted text is full of menu spam / truncated articles | Wrong extractor or misconfigured extraction rules in step 2 | Swap extractor (trafilatura vs resiliparse) and re-spot-check 100 docs before re-running the full dump |
| Corpus can't be reproduced from the manifest | Tool versions, filter configs, or RNG seed weren't pinned | Version and hash the full pipeline (Dolma/DataTrove manifest); never let a dependency bump silently change extraction |

## Connections
- [[Deep Dive - The Pretraining Data Pipeline]] — this playbook is the operational trace through that pipeline's stage graph.
- [[Concept - Common Crawl and Web Data at Scale]] — the raw material step 1 fetches, with its coverage biases and access mechanics.
- [[Concept - Text Extraction from Web Pages]] — step 2's mechanism; extractor choice is the highest-leverage lever in the whole procedure.
- [[Concept - Deduplication at Scale]] — step 5's algorithm and the per-dump-vs-global tradeoff.
- [[Concept - Training Set Decontamination]] — step 5's eval-leakage defense and its inherent blind spots.
- [[Concept - Benchmark Contamination]] — the evaluation-side twin of decontamination; a leaked benchmark corrupts both the corpus and every score reported against it.
- [[Concept - Data Mixtures]] — step 6's weighting scheme, decided before the final shuffle.
- [[Concept - Byte-Pair Encoding]] — the tokenizer that turns the assembled corpus into training-ready IDs.
- [[Deep Dive - Anatomy of a Pretraining Run]] — what consumes this corpus once shards are verified; a bad handoff here burns GPU-hours downstream.
- [[Gotchas - Pretraining Data Pipelines]] — the aggregated failure modes this playbook's verification steps are designed to catch early.

## Sources
- Raffel et al. (2020) — Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer (C4). Introduced the heuristic filtering baseline this playbook's step 4 builds on.
- Penedo et al. (2023) — The RefinedWeb Dataset for Falcon LLM. Established that re-extraction from WARC (step 2) is a bigger quality lever than filtering alone.
- Penedo et al. (2024) — The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale. Source of the per-dump-dedup finding used in step 5 and the ablation-driven validation approach used in step 4's verification.
- Brown et al. (2020) — Language Models are Few-Shot Learners (GPT-3), Section 4. Documents the consequence of a dedup/decontamination bug shipping uncaught — the cautionary case behind this playbook's step 5 verification.
