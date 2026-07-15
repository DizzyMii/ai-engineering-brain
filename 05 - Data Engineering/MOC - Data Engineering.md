---
tags: [moc, domain/data-engineering, level/surface]
aliases: []
summary: "Map of Data Engineering: sourcing, filtering, dedup, mixtures, synthetic data, and decontamination for pretraining corpora."
---
# MOC - Data Engineering

This domain covers the pipeline that turns the raw, messy internet into the tokens a model actually trains on: where the text comes from (Common Crawl, licensed corpora, synthetic generation), what gets thrown out (quality filters, PII/toxicity scrubbing, deduplication, benchmark decontamination), and how the surviving tokens get weighted, ordered, and shipped into a run (data mixtures, curricula, sharding). It matters because the post-2020 data-centric thesis holds that at fixed compute, corpus quality — not architecture — explains most of the gap between models, and because every filtering choice is also a values choice: C4's blocklist deleted LGBTQ content, Books3's shadow-library corpus triggered the industry's copyright reckoning. The notes here span from what Common Crawl actually is up through the frontier question of whether recursive training on synthetic data quietly collapses a model's tails, and whether learned mixture weights even transfer across scale. Treat this domain as upstream of [[MOC - Training at Scale]] (what the run is fed) and as asking the same quality questions [[MOC - Post-Training]] asks about SFT/preference data, just earlier and at far larger scale.

**Start here, by level:**
- **Surface:** [[Concept - The Data-Centric View of Model Quality]] — the ~2020-2024 thesis that data curation, not architecture, explains most of the quality gap between models at fixed compute; the reason this domain exists.
- **Core:** [[Concept - Quality Filtering for Pretraining Data]] — the pipeline stage that decides which crawled documents survive: heuristic rules, perplexity scoring, classifier/LLM-annotator filters.
- **Advanced:** [[Deep Dive - The Pretraining Data Pipeline]] — the end-to-end system, every stage in the order it must run, from raw WARC dumps to a tokenized, sharded corpus.
- **Frontier:** [[Concept - Model Collapse from Synthetic Data]] — recursive training on model output narrows the learned distribution and kills the tails, but only under replace, not accumulate.
- **Unicorn:** [[Lore - The C4 Blocklist Incident]] — how a "bad words" blocklist quietly deleted LGBTQ and dialect content from the corpus behind a generation of models.

## Sourcing and extracting raw text

- [[Concept - Common Crawl and Web Data at Scale]] — the nonprofit monthly web crawl (WARC/WET/WAT dumps on S3) that underlies nearly every open pretraining corpus.
- [[Concept - Text Extraction from Web Pages]] — turning raw HTML into clean plaintext by stripping nav/ads/footers, a high-leverage, underrated pipeline stage.
- [[Concept - Copyright and Licensing of Training Data]] — the legal-technical constraints on what text can be crawled and trained on: fair use, TDM exceptions, licenses, opt-out signals.
- [[Playbook - Building a Pretraining Corpus from Common Crawl]] — the end-to-end procedure: fetch WARC dumps, extract, filter, dedup, decontaminate, mix, and shard a corpus.

## Quality filtering and safety scrubbing

- [[Concept - The Data-Centric View of Model Quality]] — the ~2020-2024 thesis that data curation, not architecture, explains most of the quality gap between models at fixed compute.
- [[Concept - Quality Filtering for Pretraining Data]] — heuristic rules, perplexity scoring, and classifier/LLM-annotator filters, and what each stage is actually deciding.
- [[Concept - PII and Toxicity Filtering]] — detecting and redacting personal data, secrets, and toxic content, and the safety/diversity tradeoff filtering creates.
- [[Reference - Data Filtering Heuristics]] — the exact rules and thresholds used by C4, Gopher, RefinedWeb, FineWeb, and CCNet, so you don't rederive them mid-pipeline.
- [[Decision - Choosing a Quality Filtering Strategy]] — when to use heuristic, perplexity, classifier, or LLM-annotator filtering, and the default recipe.

## Deduplication and decontamination

- [[Concept - Deduplication at Scale]] — removing exact and near-duplicate text at web scale with hashing, suffix arrays, and MinHash-LSH; granularity is the real knob.
- [[Concept - Semantic Deduplication]] — deduplicating by embedding-space meaning instead of lexical overlap, catching paraphrases MinHash cannot see.
- [[Snippet - MinHash LSH Deduplication]] — a runnable MinHash + LSH banding pipeline: shingling, signatures, and union-find clustering.
- [[Concept - Training Set Decontamination]] — stripping evaluation benchmarks out of pretraining corpora via n-gram/substring overlap removal, imperfect by construction.

## Mixtures, curriculum, and synthetic data

- [[Concept - Data Mixtures]] — the per-source sampling weights of a corpus, and why the mix, not just token count, sets a model's capability profile.
- [[Concept - Learned Data Mixing (DoReMi and Mixing Laws)]] — replacing hand-tuned mixture weights with optimized ones, and why they often fail to transfer to scale.
- [[Concept - Data Curriculum and Ordering]] — whether the order and repetition schedule of tokens, not just the mixture, measurably changes convergence and final quality.
- [[Concept - Synthetic Training Data]] — generating pretraining/mid-training tokens with models instead of harvesting them, and when synthetic tokens help versus hurt.
- [[Concept - Model Collapse from Synthetic Data]] — recursive training on model output narrows the learned distribution and kills the tails, but only under replace, not accumulate.

## Systems, case studies, and pitfalls

- [[Deep Dive - The Pretraining Data Pipeline]] — the end-to-end system that turns raw Common Crawl dumps into a tokenized, shuffled, sharded training corpus.
- [[Breakdown - FineWeb and FineWeb-Edu]] — how Hugging Face built the 15T-token FineWeb corpus and its ablation-validated FineWeb-Edu educational subset.
- [[Breakdown - The Phi Models and Textbook-Quality Data]] — how Microsoft's Phi models used curated and synthetic textbook-quality data to make small models punch above their size.
- [[Gotchas - Pretraining Data Pipelines]] — the bugs and silent quality killers of web-scale corpus building: contamination, verbatim memorization, shuffle NaNs, filter narrowing.

## Lore: when data decisions became incidents

- [[Lore - The C4 Blocklist Incident]] — how C4's "bad words" blocklist quietly deleted LGBTQ and dialect content from the corpus behind a generation of models.
- [[Lore - Books3 and the Shadow Library Reckoning]] — the ~197k-book pirated corpus that trained early open LLMs, its DMCA takedown, and the copyright reckoning it forced.

## Adjacent domains

- [[MOC - Training at Scale]] — this domain answers what the training run is fed; that domain answers what happens once those tokens start flowing through the model.
- [[MOC - Post-Training]] — the same quality-filtering, deduplication, and decontamination questions recur for SFT and preference data, just downstream and at far smaller scale.
- [[MOC - Evaluation]] — benchmark contamination handled here is the flip side of eval integrity there; a leaked test set quietly undermines both.
