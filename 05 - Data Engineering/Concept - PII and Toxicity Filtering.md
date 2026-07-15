---
tags: [concept, domain/data-engineering, level/advanced]
aliases: [PII scrubbing, PII redaction, toxicity filtering, NSFW filtering]
summary: "Detecting and redacting personal data, secrets, and toxic content from pretraining corpora, and the safety/diversity tradeoff filtering creates."
---

# Concept - PII and Toxicity Filtering

> **One-paragraph hook:** Common Crawl contains real emails, phone numbers, leaked API keys, and doxxed personal information, alongside genuinely toxic and NSFW content — and a model trained on it will happily reproduce any of it verbatim if asked the right way. This stage of the [[Deep Dive - The Pretraining Data Pipeline]] is where labs decide what to strip before it becomes weights, and it's one of the few filtering decisions where the naive "remove more" answer is demonstrably wrong: over-filtering doesn't just narrow the corpus, it can make the resulting model *worse* at the exact safety behavior it was meant to protect.

## The mechanism

PII detection layers three techniques. **Regex** catches structurally regular PII — email addresses, phone numbers, social security numbers, credit card numbers, IP addresses — cheaply and with high precision on well-formed instances. **NER (named entity recognition)** catches names and addresses, which don't follow a fixed pattern and need a model, not a pattern match, to identify. **Entropy- and regex-based secret scanning**, in the style of tools like detect-secrets and TruffleHog, catches API keys and credentials by combining a pattern match (known key-format prefixes) with a high-entropy check on the surrounding string, since a real secret looks statistically different from an English sentence. Code-focused corpora take this furthest: the BigCode project's [[Concept - Copyright and Licensing of Training Data|license-filtered]] pipeline behind StarCoder ran this full stack over source code specifically and redacted detected PII to sentinel placeholders like `<EMAIL>` and `<KEY>`.

That last detail — redaction to a placeholder rather than deleting the whole document — is a real design tradeoff. **Redaction preserves the document's training signal** (the surrounding code or prose stays intact, useful for learning structure and syntax) but introduces its own failure mode: the sentinel tokens themselves become learnable patterns, and a model can memorize and later emit `<EMAIL>` or `<KEY>` verbatim as an artifact of training, not as an actual leak, which nonetheless looks alarming in production output. **Removing the whole document avoids that artifact but loses all the surrounding training signal**, which matters at scale when the flagged content is a small fraction of an otherwise-useful document.

Toxicity and NSFW filtering uses the same classifier-driven pattern as [[Concept - Quality Filtering for Pretraining Data|quality filtering]] generally: Perspective-API-style toxicity classifiers, fastText toxic-content classifiers, and perplexity scoring against a toxic-content reference corpus with a KenLM model. C4's approach (Raffel et al. 2020) combined a domain-level blocklist with a lexical "bad words" list — a design whose consequences are the subject of [[Lore - The C4 Blocklist Incident]].

## In practice

Cost is a real constraint: running a classifier pass over trillions of tokens is expensive, so production pipelines distill lightweight classifiers (a linear head over embeddings, or a small fastText model) rather than run a heavyweight model over every token, and some pipelines sample rather than exhaustively score.

There's also a legal driver pushing this stage earlier in the pipeline rather than later. GDPR's right-to-erasure is, in practice, close to impossible to satisfy once a datum has been trained into model weights — there is no clean way to "delete" one person's data from a converged neural network the way you'd delete a database row. That practical impossibility is exactly why labs push PII filtering upstream, into the data pipeline, rather than treating it as a post-hoc model-editing problem. Extraction attacks make the stakes concrete: Carlini et al. (2021), "Extracting Training Data from Large Language Models," demonstrated that unfiltered PII present in training data is recoverable from a trained model via targeted prompting — this stage isn't theoretical hygiene, it closes a real, demonstrated attack surface. Note that this is the pretrain-time complement to [[Concept - PII Redaction and Data Retention]], which handles PII in production logs and inference traffic rather than in training corpora.

## Failure modes

**Redaction placeholders get memorized and emitted verbatim.** If the sentinel pattern is too regular (always exactly `<EMAIL>`, appearing at a predictable rate), the model can learn to reproduce it as a generic pattern completion rather than treating it as "personal data was here" — a subtler failure than leaking a real email, but one that erodes trust in the redaction pipeline's stated guarantee. Detection: probe the model for spontaneous placeholder-token emission and check whether it's correlated with the training distribution's redaction rate.

**Over-broad blocklists erase dialects and minority topics rather than harm.** A lexical "bad words" list conflates a *word* with *harm*, deleting documents that merely discuss a topic using flagged vocabulary. Sap et al. (2019), "The Risk of Racial Bias in Hate Speech Detection," found toxicity classifiers systematically over-flag African-American English as toxic relative to matched content in other dialects — meaning naive toxicity filtering doesn't just remove toxic content, it removes dialect-marked and topically sensitive content (LGBTQ+ discussion, sexual health information) at a disproportionate rate. This is the same mechanism documented concretely in [[Lore - The C4 Blocklist Incident]].

**The safety-diversity tradeoff cuts against the intuitive fix.** Filtering toxicity out of pretraining data does reduce a model's propensity to generate toxic content spontaneously — but it also removes the model's exposure to what toxic content looks like, which measurably degrades its ability to *recognize and refuse* toxic requests at inference time, since refusal requires the model to have a representation of the thing it's refusing. This is why many labs, as of 2026, filter only lightly at pretrain time and push the actual safety behavior to post-training via targeted [[Concept - Refusal Mechanics|refusal training]] rather than trying to scrub the base corpus clean.

## The non-obvious

The safety-diversity tradeoff above is the counterintuitive core of this whole note: aggressively cleaning toxicity out of the *pretraining* corpus is not obviously the safest choice, because a model that has never seen toxic content in any form has a weaker internal representation of what it's supposed to refuse, not a stronger one. The practitioner lesson that emerged from watching this play out (the C4 blocklist being the clearest public case study) is that lexical filtering at the data layer and behavioral safety at the post-training layer are different tools solving different problems, and using the data-layer tool to solve the post-training problem produces a model that's simultaneously less capable and not meaningfully safer.

## Connections
- [[Concept - Copyright and Licensing of Training Data]] — the sibling data-cleanliness concern; PII filtering and licensing filtering both push compliance work upstream into the pipeline rather than treating it as a post-hoc problem.
- [[Lore - The C4 Blocklist Incident]] — the canonical documented case of a toxicity/PII-adjacent blocklist causing exactly the dialect-erasure failure mode described above.
- [[Concept - Quality Filtering for Pretraining Data]] — shares the same classifier-based detection architecture (train a cheap model to flag documents) applied to a different target property.
- [[Concept - Refusal Mechanics]] — the post-training mechanism labs increasingly rely on instead of aggressive pretrain-time toxicity scrubbing, per the safety-diversity tradeoff above.
- [[Deep Dive - The Pretraining Data Pipeline]] — places this stage in the full pipeline graph, interleaved with quality filtering and dedup.
- [[Concept - Training Set Decontamination]] — a structurally similar targeted-removal operation, applied against eval benchmarks instead of PII/toxic content.
- [[Concept - PII Redaction and Data Retention]] — the production-side counterpart: this note covers PII in training data, that note covers PII in logs and inference traffic.
- [[Gotchas - Pretraining Data Pipelines]] — documents "PII placeholder tokens emitted" as a real production incident, not just a theoretical risk.

## Sources
- Carlini et al. (2021) — "Extracting Training Data from Large Language Models": demonstrated that unfiltered PII in training data is recoverable from a trained model via targeted extraction attacks.
- Sap et al. (2019) — "The Risk of Racial Bias in Hate Speech Detection": showed toxicity classifiers over-flag African-American English, the mechanism behind dialect-erasure in naive toxicity filtering.
- Raffel et al. (2020) — "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer": C4's domain blocklist and "bad words" list, the filtering design examined in [[Lore - The C4 Blocklist Incident]].
- Li et al. (2023) — "StarCoder: may the source be with you!": the BigCode PII-redaction pipeline that pioneered sentinel-token replacement (`<EMAIL>`, `<KEY>`) for code corpora.
