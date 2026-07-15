---
tags: [reference, domain/data-engineering, level/advanced]
aliases: [Gopher rules, C4 rules, MassiveText filters]
summary: "Lookup sheet of the exact filtering rules and thresholds used by C4, Gopher, RefinedWeb, FineWeb, and CCNet — so you don't rederive them mid-pipeline."
---

# Reference - Data Filtering Heuristics

All thresholds below are corpus-specific choices made by their original authors, not universal constants — treat every number as a starting point to ablation-validate against your own data via [[Decision - Choosing a Quality Filtering Strategy]], not a rule to copy blindly. Date-stamped as of 2026; these are the published, citable values.

## C4 (Raffel et al. 2020)

| Rule | Threshold / value | Purpose |
|---|---|---|
| Line terminal punctuation | keep only lines ending in `.`, `!`, `?`, or `"` | drop navigation/menu fragments |
| Minimum document length | drop pages with < 3 sentences | remove stub/boilerplate pages |
| Minimum line length | drop lines < 5 words | remove nav chrome, labels |
| Placeholder text | drop lines containing "lorem ipsum" | remove template placeholder pages |
| Code/markup leakage | drop lines containing `{` | remove embedded JS/CSS |
| Policy boilerplate | drop lines matching cookie/privacy-policy phrasing | remove legal boilerplate |
| Blocklist | drop documents matching a "dirty, naughty, obscene" word list<sup>†</sup> | remove obscene/spam content |
| Span dedup | dedup any repeated 3-sentence span | remove templated repetition |

† See [[Lore - The C4 Blocklist Incident]] — this rule is the canonical cautionary tale for lexical blocklist over-reach, not a rule to reuse as-is.

## Gopher / MassiveText (Rae et al. 2021)

| Rule | Threshold | Purpose |
|---|---|---|
| Word count | 50 – 100,000 words | drop stubs and runaway/junk documents |
| Mean word length | 3 – 10 characters | catch non-natural-language token soup |
| Symbol-to-word ratio | `#` and `...` occurrences < 0.1 | catch markup/list-heavy junk |
| Bullet-initial lines | < 90% of lines | catch list-only/menu pages |
| Ellipsis-terminal lines | < 30% of lines | catch truncated/preview-style content |
| Alphabetic word fraction | ≥ 80% of words contain a letter | catch numeric/symbol spam |
| Stopword presence | ≥ 2 of {the, be, to, of, and, that, have, with} present | catch non-natural-language / keyword-stuffed text |

## RefinedWeb / MacroData Refinement (Penedo et al. 2023)

| Rule | Value | Purpose |
|---|---|---|
| Extraction | `trafilatura` on raw WARC (not WET) | the pipeline's central quality lever — see [[Concept - Text Extraction from Web Pages]] |
| Line filters | drop mostly-digit lines, short lines, policy boilerplate | Gopher-style cleanup, applied post-extraction |
| Dedup | document-level + line-level | remove exact and templated near-duplicates |
| URL blocklist | domain-level adult-content blocklist | remove NSFW sources at the source level |

## FineWeb / FineWeb-Edu (Penedo et al. 2024)

| Rule | Value | Purpose |
|---|---|---|
| Base filters | Gopher-style + custom ablation-discovered filters | validated by training 1.8B models on 350B tokens per variant, not by inspection |
| FineWeb-Edu classifier | Llama-3-70B-Instruct rates educational value 0–5 on ~460k samples, distilled to a linear regression over embeddings | keep documents scoring ≥ 3 |

See [[Breakdown - FineWeb and FineWeb-Edu]] for the full pipeline and the ablation methodology behind these choices.

## CCNet perplexity buckets (Wenzek et al. 2019)

| Step | Value | Purpose |
|---|---|---|
| Reference model | KenLM 5-gram, trained on Wikipedia (per language) | scores fluency against a "clean" reference distribution |
| Bucketing | split corpus into head / middle / tail thirds by per-document perplexity | separates natural language from boilerplate/spam |
| Retention | keep head (and often middle); drop tail | tail = non-natural text |

## Language ID

| Tool | Threshold | Note |
|---|---|---|
| fastText `lid.176` | keep language if `p ≥ 0.65` (typical) | corpus-specific; must run before any of the tables above, since every rule set here is language-tuned |

## Connections
- [[Concept - Quality Filtering for Pretraining Data]] — the mechanism and paradigm-level reasoning behind every rule in these tables; this page deliberately omits the "why," only the numbers.
- [[Concept - Text Extraction from Web Pages]] — the stage that runs before these rules and determines what text they even see; RefinedWeb's extraction row is the clearest example of extraction quality gating filter effectiveness.
- [[Decision - Choosing a Quality Filtering Strategy]] — how to choose which of these rule sets (or paradigms) fits a given compute budget and language coverage.
- [[Breakdown - FineWeb and FineWeb-Edu]] — the full ablation methodology that produced the FineWeb-Edu classifier row above.
- [[Concept - Deduplication at Scale]] — the dedup rules referenced in the C4 and RefinedWeb rows, detailed separately since dedup has its own parameter space (MinHash bands/rows) beyond a simple threshold table.
- [[Lore - The C4 Blocklist Incident]] — the documented failure of the C4 blocklist row above; read before reusing a lexical blocklist in a new pipeline.
- [[Concept - Entropy and Cross-Entropy]] — perplexity, the scoring function behind the CCNet bucket table, is literally cross-entropy under a reference language model.
- [[Concept - Byte-Pair Encoding]] — language ID (the last table) has to run before tokenizer training and before every heuristic above, since both are language-specific.

## Sources
- Raffel et al. (2020) — "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer": the C4 rule table.
- Rae et al. (2021) — "Scaling Language Models: Methods, Analysis & Insights from Training Gopher": the Gopher/MassiveText rule table.
- Penedo et al. (2023) — "The RefinedWeb Dataset for Falcon LLM": the RefinedWeb/MacroData Refinement rule table.
- Penedo et al. (2024) — "FineWeb: decanting the web for the finest text data at scale": the FineWeb/FineWeb-Edu rule table.
- Wenzek et al. (2019) — "CCNet: Extracting High Quality Monolingual Datasets from Web Crawl Data": the perplexity-bucket table.
