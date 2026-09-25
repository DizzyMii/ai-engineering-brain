---
tags: [concept, domain/data-engineering, level/core]
aliases: [training data copyright, TDM exception, fair use for AI training]
summary: "The legal-technical constraints on what text can be crawled and trained on — fair use, TDM exceptions, licenses, and opt-out signals."
---
# Concept - Copyright and Licensing of Training Data

> "It was on the public internet" is not a legal defense for training on it. Every engineer building a pretraining corpus makes a legal bet on fair use or a text-and-data-mining exception each time they include a crawled document, whether they think about it or not. This note covers the technical-legal mechanics: doctrines, license types, opt-out signals, and how they shape real corpora. It doesn't predict how the lawsuits resolve.

## The mechanism

By default, text on the web is copyrighted the moment it's created, under US law and most international copyright law. There's no "publicly available, therefore free to use" carve-out. Training instead relies on affirmative legal theories that a use is permitted despite the copyright:

- **Fair use (US).** A four-factor balancing test: purpose/transformativeness, nature of the work, amount used, effect on the market. AI labs argue it covers training because the model learns statistical patterns from the work without reproducing it. This is contested, not settled.
- **Text-and-data-mining exceptions (EU).** The EU DSM Directive (Articles 3–4) creates an explicit TDM exception, but Article 4's version lets a rights holder opt out by reserving their rights (technically, via machine-readable signals). That removes the exception's protection for their content.

Neither doctrine has a settled bright line for AI training *(as of 2026)*. Both are being tested in litigation, and each case turns on fact-specific questions (how transformative the specific use is, whether the model can be shown to substitute for the original work in its market) instead of a categorical rule.

**Active litigation shaping practice (as of 2026).** The marquee cases are NYT v. OpenAI (news content, direct-quotation concerns), Authors Guild v. OpenAI (books), Kadrey v. Meta (the [[Lore - Books3 and the Shadow Library Reckoning]] books corpus, discussed below) and Getty v. Stability (images). None has produced a definitive, generally applicable precedent. Labs are building corpora under real legal uncertainty.

## In practice

Industry has split into two tracks that trade against each other: scale and litigate, or license clean and shrink.

**License-clean corpora** give up size and diversity for provenance certainty. The Stack (code, filtered by detected SPDX license to permissive-only), Common Pile and KL3M (public-domain and explicitly licensed sources), PG-19 (Project Gutenberg's public-domain books) and Common Corpus are all smaller pools built so a lab can point to a defensible license chain for every document. The cost is far less raw volume than an unfiltered [[Concept - Common Crawl and Web Data at Scale]] scrape.

**Technical opt-out signals** are how the "TDM exception with opt-out" doctrine gets implemented on the ground. The channels are `robots.txt` (which Common Crawl honors by design, making it the first and oldest), emerging `noai`/TDM-reservation HTTP headers and `ai.txt` files, and more and more per-site blocks of specific crawler user-agents (`GPTBot`, `CCBot`). Together they shrink the crawlable web in real time. Every site that adds one removes itself from future corpora built on respectful crawls, a slow, cumulative supply shock to the field's raw material.

**Code licensing is a separate trap** from prose copyright. GitHub hosts a huge amount of copyleft code (GPL, AGPL) whose licenses impose obligations on derivative works. Train on GitHub indiscriminately and the model may reproduce copyleft snippets verbatim, potentially "contaminating" a user's proprietary codebase with obligations they never agreed to. The Stack handles this by filtering to permissively licensed repositories via detected SPDX identifiers, and offers an "Am I In The Stack" opt-out tool for authors. It's a rare case of a corpus builder building consent infrastructure up front instead of only reacting to takedown demands.

**Compliance obligations are getting concrete.** C2PA content credentials (provenance metadata attached to media), dataset datasheets documenting a corpus's sourcing, and the EU AI Act's training-data-summary obligation (providers must publish a sufficiently detailed summary of the content used to train a model) are moving from best practice to regulatory requirement. [[Reference - AI Copyright Litigation Tracker]] tracks the cases and these obligations as they evolve.

## Failure modes

**Assuming "publicly crawlable" means "licensed."** It's the most common misconception. It's also the assumption that put [[Lore - Books3 and the Shadow Library Reckoning]], a pirated-ebook corpus assembled from a torrent tracker, inside The Pile and, per litigation disclosures, inside models including LLaMA. Once data is in a shipped model's lineage it can't be cleanly removed; the only fix is retraining without it. Part of the reason [[Reference - Model Genealogy]] tracking exists is that questions like "did this model's lineage touch Books3" now carry legal stakes.

**Treating code and prose copyright as one problem.** A pipeline that runs prose-oriented dedup and quality filtering over GitHub data, with no separate license-detection pass, will silently pull in copyleft code next to permissive code. That creates output-contamination risk downstream, and a generic quality filter was never designed to catch it.

**Ignoring opt-out signals because they're inconvenient.** A crawler or corpus builder that ignores `robots.txt`, `ai.txt` or explicit crawler blocks is making a more aggressive legal bet, not a neutral one. Each high-profile scraping controversy has made rights holders quicker to add these signals, which shrinks the honestly crawlable web for everyone who respects them.

## The non-obvious

Legal risk has become a second axis of data curation next to quality. Engineers now pick *which* data to include partly on legal defensibility, independent of its training value, and that is reshaping raw supply. The harder rights holders push opt-out signals and litigation, the more future corpora skew toward whatever is license-clean or opt-in. That isn't necessarily the distribution of text that produced the best models so far.

So [[Concept - Data Mixtures]] decisions increasingly follow from legal risk tolerance as well as measured downstream accuracy. The constraint barely existed in the C4-era (2019-2020) pretraining literature. Now it limits what a frontier lab can even put in its ablation set.

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
