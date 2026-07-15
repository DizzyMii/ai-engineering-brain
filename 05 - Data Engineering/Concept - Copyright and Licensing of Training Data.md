---
tags: [concept, domain/data-engineering, level/core]
aliases: [training data copyright, TDM exception, fair use for AI training]
summary: "The legal-technical constraints on what text can be crawled and trained on — fair use, TDM exceptions, licenses, and opt-out signals."
---
# Concept - Copyright and Licensing of Training Data

> **One-paragraph hook:** "It was on the public internet" is not a legal defense for training on it, and every engineer building a pretraining corpus is, whether they think about it or not, making a legal bet on fair use or a text-and-data-mining exception every time they include a crawled document. This note is the technical-legal mechanics — doctrines, license types, opt-out signals, and how real corpora are shaped by them — not a prediction of how the lawsuits resolve.

## The mechanism

Text on the web is copyrighted the moment it's created, by default, under both US and most international copyright law — there is no "publicly available, therefore free to use" carve-out. Training relies instead on affirmative legal theories that a use is permitted despite the underlying copyright:

- **Fair use (US)** — a four-factor balancing test (purpose/transformativeness, nature of the work, amount used, effect on the market) that AI labs argue covers training because the model doesn't reproduce the work, it learns statistical patterns from it. This is contested, not settled.
- **Text-and-data-mining exceptions (EU)** — the EU DSM Directive (Articles 3–4) creates an explicit TDM exception, but Article 4's exception is opt-out-able: a rights holder can reserve their rights (technically, via machine-readable signals), which removes the exception's protection for that content.

Neither doctrine has a settled bright line for AI training specifically as of 2026 — both are being actively tested in litigation, and the outcome in any given case turns on fact-specific questions (transformativeness of the specific use, whether the model can be shown to cause market substitution for the original work) rather than a categorical rule.

**Active litigation shaping practice (as of 2026)**: NYT v. OpenAI (news content, direct-quotation concerns), Authors Guild v. OpenAI (books), Kadrey v. Meta (the [[Lore - Books3 and the Shadow Library Reckoning]] books corpus, discussed below), and Getty v. Stability (images) are the marquee cases; none has produced a definitive, generally-applicable precedent, and labs are building corpora under genuine legal uncertainty rather than settled rules.

## In practice

The industry response to this uncertainty splits into two tracks that trade against each other: scale-and-litigate versus license-clean-and-shrink.

**License-clean corpora** deliberately sacrifice size and diversity for provenance certainty: The Stack (code, filtered by detected SPDX license to permissive-only), Common Pile and KL3M (assembled from public-domain and explicitly-licensed sources), PG-19 (Project Gutenberg's public-domain books), and Common Corpus are all smaller, cleaner-provenance pools built specifically so a lab can point to a defensible license chain for every document, at the cost of far less raw volume than an unfiltered [[Concept - Common Crawl and Web Data at Scale]] scrape.

**Technical opt-out signals** are the mechanism by which the "TDM exception with opt-out" doctrine actually gets implemented on the ground: `robots.txt` (which Common Crawl honors by design, making it the first and oldest opt-out channel), emerging `noai`/TDM-reservation HTTP headers and `ai.txt` files, and increasingly common per-site blocks of specific crawler user-agents (`GPTBot`, `CCBot`) are all shrinking the crawlable web in real time — every site that adds one of these signals removes itself from future training corpora built on respectful crawls, which is a slow, cumulative supply shock to the field's raw material.

**Code licensing is its own trap**, distinct from prose copyright: GitHub hosts an enormous amount of copyleft-licensed code (GPL, AGPL) whose licenses impose obligations on derivative works, so training indiscriminately on GitHub risks a model that reproduces copyleft-licensed snippets verbatim in its output, potentially "contaminating" a user's proprietary codebase with copyleft obligations they never agreed to. The Stack addresses this directly by filtering to permissively-licensed repositories via detected SPDX identifiers and by offering an "Am I In The Stack" opt-out tool for authors — a rare example of a corpus builder proactively engineering consent infrastructure rather than only reacting to takedown demands.

**Compliance obligations are becoming concrete, not aspirational.** C2PA content credentials (provenance metadata attached to media), dataset datasheets documenting a corpus's sourcing, and the EU AI Act's training-data-summary obligation (requiring providers to publish a sufficiently detailed summary of the content used to train a model) are shifting from best-practice to regulatory requirement — see [[Reference - AI Copyright Litigation Tracker]] for how the litigation landscape and these obligations are tracked as they evolve.

## Failure modes

**Assuming "publicly crawlable" equals "licensed."** This is the single most common misconception, and it's the exact assumption that put [[Lore - Books3 and the Shadow Library Reckoning]] — a pirated-ebook corpus assembled from a torrent tracker — inside The Pile and, per litigation disclosures, inside models including LLaMA. Once training data enters a shipped model's lineage, it can't be cleanly removed; the only fix is retraining without it, and [[Reference - Model Genealogy]] tracking exists in part because provenance questions like "did this model's lineage touch Books3" now have real legal stakes.

**Treating code and prose copyright as the same problem.** A pipeline that runs prose-oriented dedup and quality filtering on GitHub data without a separate license-detection pass will silently pull in copyleft code alongside permissive code, creating downstream output-contamination risk that a generic quality filter was never designed to catch.

**Ignoring opt-out signals because they're inconvenient.** Crawlers and corpus builders that don't respect `robots.txt`, `ai.txt`, or explicit crawler blocks are making the legal bet more aggressive, not neutral — and every high-profile scraping controversy has made rights holders faster to add these signals, shrinking the honestly-crawlable web for everyone who does respect them.

## The non-obvious

The field's response to legal risk has quietly become a second axis of data curation, running alongside quality: engineers now choose *which* data to include partly on legal-defensibility grounds independent of the data's actual training value, and this is reshaping the raw supply — the more aggressively rights holders deploy opt-out signals and pursue litigation, the more the field's future corpora skew toward whatever remains license-clean or opt-in, which is not necessarily the same distribution of text that produced the best-performing models to date. In other words: [[Concept - Data Mixtures]] decisions are increasingly downstream of legal risk tolerance, not just measured downstream accuracy — a constraint that didn't meaningfully exist in the C4-era (2019-2020) pretraining literature and now shapes what a frontier lab can even put in its ablation set.

## Connections
- [[Lore - Books3 and the Shadow Library Reckoning]] — the concrete, litigated case study of what happens when "it was on the internet" turns out to mean "it was pirated."
- [[Concept - Common Crawl and Web Data at Scale]] — `robots.txt` compliance is Common Crawl's own opt-out mechanism, making it the practical front line of the TDM-exception debate.
- [[Concept - Synthetic Training Data]] — generating synthetic data sidesteps source-text copyright but inherits the teacher model's own terms of service, which is its own live legal question.
- [[Reference - Model Genealogy]] — provenance tracking that now carries legal weight: which corpora, and by extension which licensing risk, a given model's lineage actually touched.
- [[Concept - PII and Toxicity Filtering]] — a parallel legal driver (GDPR right-to-erasure) that pushes filtering upstream for the same practical reason copyright risk does: you cannot cleanly un-train a shipped model.
- [[Deep Dive - The Pretraining Data Pipeline]] — where license filtering and opt-out signal checks actually get inserted as pipeline stages, alongside quality and PII filtering.
- [[Reference - AI Copyright Litigation Tracker]] — the live-updated record of the specific cases (NYT, Authors Guild, Kadrey, Getty) whose outcomes will retroactively validate or invalidate current data-sourcing practice.
- [[Reference - Open Weights Licensing]] — the mirror-image question once a model is trained: what license the resulting weights carry, which is partly constrained by what licenses went into the training data.

## Sources
- EU Directive 2019/790 (DSM Directive), Articles 3–4 — the statutory text-and-data-mining exception and its rights-holder opt-out mechanism underpinning EU training practice.
- Kadrey v. Meta Platforms, N.D. Cal. — ongoing litigation whose discovery record surfaced internal deliberations about training on the Books3 corpus.
- The Stack (Kocetkov et al. 2022, BigCode) — the SPDX-license-filtered code corpus and its author opt-out tooling, the reference example of licensing-aware corpus construction.
