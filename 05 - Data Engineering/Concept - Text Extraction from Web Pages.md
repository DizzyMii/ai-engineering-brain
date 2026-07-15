---
tags: [concept, domain/data-engineering, level/core]
aliases: [boilerplate removal, main content extraction, HTML-to-text extraction]
summary: "Turning raw HTML into clean plaintext by stripping nav/ads/footers — a high-leverage, underrated stage in the pretraining pipeline."
---
# Concept - Text Extraction from Web Pages

> **One-paragraph hook:** A crawled HTML page is mostly not the thing you want to train on — it's navigation bars, cookie banners, ad slots, related-article widgets, and JavaScript, with the actual article buried somewhere in the DOM. Text extraction is the algorithm that finds the signal in that noise, and which extractor you use changes downstream model loss more than almost any other single pipeline decision — a fact the field only fully internalized around 2023.

## The mechanism

The problem is structural: an HTML document mixes "boilerplate" (site chrome that repeats across every page on a domain — nav menus, footers, sidebars, ads, comment widgets) with "main content" (the actual article, post, or page text). A crawler and a naive HTML-stripper can't tell these apart — they just see tags. Extraction algorithms use a mix of DOM structure (text density per subtree, tag distribution, link density) and heuristics (paragraph length, position in document, punctuation density) to classify each DOM node as content or chrome and keep only the former.

The dominant open tools, roughly in order of adoption in modern pretraining pipelines:

| Tool | Approach | Notable users |
|---|---|---|
| **trafilatura** (Barbaresi 2021) | DOM tree + text-density heuristics, actively maintained | RefinedWeb, [[Breakdown - FineWeb and FineWeb-Edu]] |
| **resiliparse** | Fast C++-backed extraction, optimized for throughput | Dolma, DCLM |
| **jusText** | Boilerplate detection via block classification | Older CC pipelines |
| **boilerpipe** | Java, shallow-text-features classifier, pre-2015 lineage | Legacy pipelines |
| **readability** (Mozilla's algorithm) | Browser-reader-mode heuristics | Ad hoc extraction |

Extractor choice is not a wash — swapping trafilatura for a weaker extractor on the same crawl measurably changes downstream loss and benchmark scores, because a worse extractor either leaks boilerplate into training (diluting signal, teaching the model that "Subscribe to our newsletter" is a common continuation) or over-aggressively strips real content (truncating articles into unusable fragments).

## In practice

The formative result here is that Common Crawl's own pre-extracted **WET** files — the "naive pre-extracted plaintext" shipped alongside every dump of [[Concept - Common Crawl and Web Data at Scale]] — are bad, and re-extracting from raw **WARC** yourself is a major, measurable quality lever. RefinedWeb (Penedo et al. 2023) built this into arguably its central finding: running trafilatura over WARC HTML instead of consuming CC's own WET extraction produced a corpus that outperformed prior CC-derived datasets built on WET, at equal or lower filtering effort downstream. FineWeb inherited this lesson wholesale — nobody serious touches WET anymore.

Extraction sits immediately downstream of raw crawl ingestion and immediately upstream of [[Concept - Quality Filtering for Pretraining Data]]: you can't apply a Gopher-style heuristic rule about "mean word length" or "symbol-to-word ratio" to a page still full of `<nav>` markup, so extraction has to be clean before filtering rules are even meaningful. Language ID lives right here too — fastText's `lid.176` model routes or drops documents by detected language, and extraction quality feeds directly into LID accuracy: a page whose extractor leaves a wall of Spanish-language nav links stitched onto an English article will confuse the language detector into a wrong or low-confidence label, corrupting a decision that every downstream heuristic depends on.

Cost-wise, extraction is CPU-bound and embarrassingly parallel — no GPU, no cross-document dependency, trivially shardable across a cluster — but at full-dump scale (billions of pages) it still dominates the wall-clock time of the early pipeline stages, which is why [[Playbook - Building a Pretraining Corpus from Common Crawl]] treats it as a distinct, cacheable step: run it once per dump, write the extracted text to disk, and never re-run it just to tweak a downstream filter threshold.

## Failure modes

Bad extraction leaves characteristic fingerprints, not crashes:

- **Boilerplate leakage** — menu items, "Related Posts," and cookie-consent text interleaved into article body text, teaching the model spurious continuations.
- **Repeated cross-domain navigation** — because every page on a domain shares the same nav/footer chrome, an extractor that fails to strip it produces documents that look like near-duplicates of each other even though the actual article content differs, which can confuse or waste effort in [[Concept - Deduplication at Scale]] if extraction ran too late or too loosely relative to dedup.
- **Mojibake and encoding errors** — wrong charset detection turns quotes and accented characters into garbage byte sequences; left unnormalized, this pollutes the tokenizer's vocabulary with junk tokens (see [[Lore - Glitch Tokens]] for what happens when garbage substrings get their own BPE token and sit un-trained in the embedding table).
- **Unclosed tags and malformed HTML** — real-world HTML is often invalid, and a brittle parser either throws away the whole document or extracts from the wrong subtree.
- **JS-rendered content missed entirely** — crawlers capture the HTML response, not a rendered DOM, so any content injected client-side by JavaScript (increasingly common on modern sites) is invisible to extraction no matter how good the algorithm is — a structural blind spot, not a bug.
- **Structure loss in tables and code** — extractors optimized for prose flatten tables into unreadable text soup and can mangle code blocks' whitespace, which matters disproportionately given code's outsized value in the mixture (see [[Concept - Data Mixtures]]).

## The non-obvious

Extraction is treated as pipeline plumbing — a boring preprocessing step nobody wants to own — when it is in fact one of the highest-leverage single decisions in the whole corpus build, on par with or exceeding many quality-filter choices in downstream impact. RefinedWeb's headline contribution to the field wasn't a novel filter or a clever dedup trick; it was pointing out that everyone was quietly training on Common Crawl's own low-quality extraction and that simply re-extracting from WARC beat elaborate downstream filtering applied to WET. The lesson generalizes: before investing in a fancier filter or classifier, verify your extractor isn't the actual bottleneck — spot-read 100 random extracted documents for boilerplate before touching anything downstream.

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
