---
tags: [concept, domain/data-engineering, level/core]
aliases: [boilerplate removal, main content extraction, HTML-to-text extraction]
summary: "Turning raw HTML into clean plaintext by stripping nav/ads/footers — a high-leverage, underrated stage in the pretraining pipeline."
---
# Concept - Text Extraction from Web Pages

> **One-paragraph hook:** Most of a crawled HTML page is stuff you don't want to train on: navigation bars, cookie banners, ad slots, related-article widgets and JavaScript, with the actual article buried somewhere in the DOM. Text extraction is the algorithm that digs the article out. Which extractor you use changes downstream model loss more than almost any other single pipeline decision, something the field only fully internalized around 2023.

## The mechanism

An HTML document mixes "boilerplate" (site chrome repeated on every page of a domain: nav menus, footers, sidebars, ads, comment widgets) with "main content" (the actual article, post or page text). A crawler or a naive HTML-stripper sees only tags and can't tell the two apart. Extraction algorithms combine DOM structure (text density per subtree, tag distribution, link density) with heuristics (paragraph length, position in the document, punctuation density) to classify each DOM node as content or chrome, and keep the content.

The dominant open tools, roughly in order of adoption in modern pretraining pipelines:

| Tool | Approach | Notable users |
|---|---|---|
| **trafilatura** (Barbaresi 2021) | DOM tree + text-density heuristics, actively maintained | RefinedWeb, [[Breakdown - FineWeb and FineWeb-Edu]] |
| **resiliparse** | Fast C++-backed extraction, optimized for throughput | Dolma, DCLM |
| **jusText** | Boilerplate detection via block classification | Older CC pipelines |
| **boilerpipe** | Java, shallow-text-features classifier, pre-2015 lineage | Legacy pipelines |
| **readability** (Mozilla's algorithm) | Browser-reader-mode heuristics | Ad hoc extraction |

The choice matters. Swap trafilatura for a weaker extractor on the same crawl and downstream loss and benchmark scores measurably change. A worse extractor either leaks boilerplate into training, diluting signal and teaching the model that "Subscribe to our newsletter" is a common continuation, or strips real content too aggressively and leaves articles as unusable fragments.

## In practice

The formative result: Common Crawl's own pre-extracted **WET** files, the "naive pre-extracted plaintext" shipped with every dump of [[Concept - Common Crawl and Web Data at Scale]], are bad, and re-extracting from raw **WARC** yourself is a major, measurable quality lever. This is arguably RefinedWeb's (Penedo et al. 2023) central finding. Running trafilatura over WARC HTML instead of using CC's WET extraction produced a corpus that outperformed prior CC-derived datasets built on WET, with equal or lower filtering effort downstream. FineWeb took the lesson wholesale. Nobody serious touches WET anymore.

Extraction sits right after raw crawl ingestion and right before [[Concept - Quality Filtering for Pretraining Data]]. A Gopher-style rule about "mean word length" or "symbol-to-word ratio" means nothing on a page still full of `<nav>` markup, so extraction has to be clean before filtering rules make sense. Language ID happens here too: fastText's `lid.176` model routes or drops documents by detected language, and its accuracy depends on extraction. Leave a wall of Spanish-language nav links stitched onto an English article and the detector returns a wrong or low-confidence label, corrupting a decision every downstream heuristic relies on.

Extraction is CPU-bound and embarrassingly parallel: no GPU, no cross-document dependency, trivially sharded across a cluster. At full-dump scale (billions of pages) it still dominates the wall-clock time of the early pipeline stages. [[Playbook - Building a Pretraining Corpus from Common Crawl]] therefore treats it as a distinct, cacheable step. Run it once per dump, write the extracted text to disk, and never re-run it just to tweak a downstream filter threshold.

## Failure modes

Bad extraction doesn't crash. It leaves characteristic fingerprints:

- **Boilerplate leakage.** Menu items, "Related Posts" and cookie-consent text get interleaved with the article body and teach the model spurious continuations.
- **Repeated cross-domain navigation.** Every page on a domain shares the same nav/footer chrome, so an extractor that fails to strip it produces documents that look like near-duplicates even when the articles differ. That can confuse or waste effort in [[Concept - Deduplication at Scale]] if extraction ran too late or too loosely relative to dedup.
- **Mojibake and encoding errors.** Wrong charset detection turns quotes and accented characters into garbage byte sequences. Left unnormalized, these fill the tokenizer's vocabulary with junk tokens (see [[Lore - Glitch Tokens]] for what happens when garbage substrings get their own BPE token and sit untrained in the embedding table).
- **Unclosed tags and malformed HTML.** Real-world HTML is often invalid, and a brittle parser either discards the whole document or extracts from the wrong subtree.
- **JS-rendered content missed entirely.** Crawlers capture the HTML response, not a rendered DOM, so content injected client-side by JavaScript (increasingly common on modern sites) is invisible to extraction however good the algorithm. That's a blind spot built into crawling, not a bug.
- **Structure loss in tables and code.** Extractors tuned for prose flatten tables into text soup and can mangle whitespace in code blocks. Given code's outsized value in the mixture (see [[Concept - Data Mixtures]]), this hurts disproportionately.

## The non-obvious

Extraction gets treated as plumbing, a boring preprocessing step nobody wants to own. In downstream impact it's one of the highest-leverage single decisions in the corpus build, on par with or exceeding many quality-filter choices. RefinedWeb's headline contribution was no novel filter or clever dedup trick. It pointed out that everyone was training on Common Crawl's own low-quality extraction, and that simply re-extracting from WARC beat elaborate downstream filtering applied to WET. Before investing in a fancier filter or classifier, check that your extractor isn't the bottleneck: spot-read 100 random extracted documents for boilerplate before touching anything downstream.

## Connections
- [[Concept - Common Crawl and Web Data at Scale]] — extraction's raw input, and the reason WET-versus-WARC is the first fork in the road.
- [[Concept - Quality Filtering for Pretraining Data]] — the stage extraction directly feeds; heuristic rules are meaningless on unextracted HTML.
- [[Concept - Deduplication at Scale]] — poor extraction produces spurious near-duplicates from shared site chrome, coupling extraction quality to dedup accuracy.
- [[Breakdown - FineWeb and FineWeb-Edu]] — the reference pipeline that validated trafilatura-over-WARC extraction as a measured, ablated win rather than a hunch.
- [[Deep Dive - The Pretraining Data Pipeline]] — extraction's exact position in the full stage graph, right after crawl ingestion and before language ID.
- [[Playbook - Building a Pretraining Corpus from Common Crawl]] — the operational step-by-step where extraction is run once and cached.
- [[Concept - Byte-Pair Encoding]] — extraction artifacts (mojibake, malformed structure) become tokenizer training data, so garbage in extraction becomes garbage tokens.
- [[Lore - Glitch Tokens]] — the downstream, years-later consequence of extraction artifacts surviving into a tokenizer's vocabulary.

## Sources
- Barbaresi (2021) — "Trafilatura: A Web Scraping Library and Command-Line Tool for Text Discovery and Extraction": the DOM+heuristics extractor now standard in open pretraining pipelines.
- Penedo et al. (2023) — "The RefinedWeb Dataset for Falcon LLM": established that re-extracting from WARC with trafilatura beats consuming Common Crawl's own WET files.
- Penedo et al. (2024) — "FineWeb: decanting the web for the finest text data at scale": adopted and validated the WARC re-extraction lesson at 15T-token scale.
