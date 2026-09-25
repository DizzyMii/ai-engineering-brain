---
tags: [concept, domain/data-engineering, level/surface]
aliases: [CC, common crawl corpus]
summary: "The nonprofit monthly web crawl (WARC/WET/WAT dumps on S3) that underlies nearly every open pretraining corpus."
---
# Concept - Common Crawl and Web Data at Scale

> Common Crawl (CC) is a nonprofit crawler that has scraped the web roughly monthly since 2008 and dumped the result, free, on S3. You've probably never opened one of its files, but if you've trained on C4, RefinedWeb, RedPajama, Dolma or [[Breakdown - FineWeb and FineWeb-Edu]], you trained on its descendants. CC is the raw ore under nearly every open pretraining corpus, and its shape (what it captured, what it missed, how it's structured) explains half the weird biases in web-trained models.

## The mechanism

Each snapshot ships as three parallel file types, and it matters which one you touch:

- **WARC**: the raw HTTP response, full headers plus the original HTML byte-for-byte. This is the ground truth.
- **WET**: plaintext from a simple HTML-stripping pass. It has no notion of "main content," so navigation menus, cookie banners and footer boilerplate stay in.
- **WAT**: metadata (outbound links, response headers, detected content type) without the HTML body.

Dumps come out roughly monthly. The cadence has varied; by 2026 there are 100+ cumulative dumps going back to 2013 in the modern WARC-tracked era, plus earlier archives to 2008. A dump is on the order of 2.5–4 billion pages and roughly 90–100 TiB of compressed WARC (250+ TiB uncompressed). Access is free via `s3://commoncrawl/`, and a CDX index lets you query captures by domain/URL without downloading the whole dump. Processing one dump end to end (fetch, decompress, extract, filter) is a distributed job costing thousands of CPU-hours. Nobody does it on a laptop.

CC is not a snapshot of "the whole web." Each crawl is seeded from the previous crawl's link graph plus submitted sitemaps, and samples a few percent of the indexed web per dump. It also respects `robots.txt`. Paywalled sites, sites that block `CCBot`, and a growing number of sites with AI-specific opt-out signals are simply absent. They aren't filtered out later; they were never captured.

## In practice

CC dominates open pretraining because it's the only web-scale corpus that can be openly redistributed. Most commercial search indices are proprietary. Every major open corpus derives from CC. C4 (Raffel et al. 2020) filtered one dump's WET files. [[Concept - Text Extraction from Web Pages]]-driven pipelines like RefinedWeb re-extract from WARC directly. RedPajama, Dolma and FineWeb all combine multiple CC dumps with other sources.

Consumers almost universally skip WET and re-extract from WARC themselves, because WET's naive extraction leaves boilerplate in the training signal. The extraction note goes deeper; "download WET and go" is the rookie path.

Cross-dump deduplication is the consumer's problem. Successive monthly dumps re-crawl huge swaths of the same URLs, so concatenating N dumps gives you nowhere near N times the unique content. [[Concept - Deduplication at Scale]] covers why FineWeb deduped per dump instead of globally.

## Failure modes

CC's coverage is biased, and the biases propagate straight into any model trained on it:

- **Language skew.** Roughly 44% of documents are English. The long tail of low-resource languages is severely underrepresented relative to global speaker populations.
- **Popularity skew.** The crawl frontier favors high-PageRank domains, so obscure-but-legitimate sites are underrepresented compared with well-linked ones.
- **Access skew.** Because CC honors `robots.txt`, paywalled news, many forums and a growing set of AI-blocking sites are invisible to it and to every model trained downstream. [[Concept - Copyright and Licensing of Training Data]] covers this gap further.
- **Format skew.** CC only captures what a crawler can fetch and render at capture time. JS-rendered content that needs execution is frequently missed entirely.

None of this crashes anything. You get a model that's oddly confident about English Wikipedia-adjacent topics and oddly bad at anything behind a login wall or in an underrepresented language, and you only find out if you go looking.

## The non-obvious

The trap is thinking CC = the web. CC is a sample of a sample. It takes a fraction of the indexed web per dump, indexing already favors well-linked pages, and the crawl frontier is seeded from prior crawls. Whatever CC missed in year one it will likely keep missing, since there's no link path in from the parts of the web it never saw. Read any CC-derived corpus's "diversity" claims with that lineage in mind. It's diverse relative to what a link-graph crawler from a fixed seed set can reach, not relative to the web as a whole.

## Connections
- [[Deep Dive - The Pretraining Data Pipeline]] — CC is stage zero of the pipeline this note orchestrates; everything downstream assumes CC's WARC/WET/WAT shape.
- [[Concept - Text Extraction from Web Pages]] — the decision to re-extract from WARC instead of using WET is the single highest-leverage choice made right after ingesting a CC dump.
- [[Concept - Deduplication at Scale]] — cross-dump redundancy from CC's monthly re-crawling is exactly what dedup exists to remove.
- [[Concept - Byte-Pair Encoding]] — CC's language and format skew directly shapes what a tokenizer trained on the resulting corpus learns to represent efficiently.
- [[Reference - Where Real AI Knowledge Lives]] — CC's own documentation and blog are a primary source most engineers never read despite depending on it daily.
- [[Concept - Copyright and Licensing of Training Data]] — `robots.txt` compliance is CC's technical opt-out mechanism, sitting at the center of the legal debate over what's fair to crawl.
- [[Breakdown - FineWeb and FineWeb-Edu]] — the reference example of a modern corpus built from 96 CC dumps end to end.
- [[Playbook - Building a Pretraining Corpus from Common Crawl]] — the operational procedure for turning a CC dump into a training-ready corpus.

## Sources
- Raffel et al. (2020) — "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer" (C4/T5 paper): one of the first widely-used pipelines built directly on a single Common Crawl WET dump.
- Penedo et al. (2023) — "The RefinedWeb Dataset for Falcon LLM": showed that re-extracting from CC's raw WARC beats using CC's own WET extraction, reshaping how the field consumes CC.
- Penedo et al. (2024) — "FineWeb: decanting the web for the finest text data at scale": built a 15T-token corpus from 96 CC dumps with a fully published, ablation-validated pipeline.
