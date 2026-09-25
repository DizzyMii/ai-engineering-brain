---
tags: [lore, domain/data-engineering, level/unicorn]
aliases: [Books3, Bibliotik, The Pile books component, shadow library corpus]
summary: "The ~197k-book pirated corpus that trained early open LLMs, its DMCA takedown, and the copyright reckoning it forced."
---
# Lore - Books3 and the Shadow Library Reckoning

## What happened

Books3 was a pile of pirated ebooks: roughly **196,640 books, ~37 GiB of plaintext**, assembled by Shawn Presser in 2020 by scraping a torrent from **Bibliotik**, a private, invite-only ebook piracy tracker. Presser released it openly ("suffice it to say, this is all of bibliotik"), and it went into **The Pile** (Gao et al. 2020), EleutherAI's 825 GiB open pretraining corpus. The name is literal. The Pile already had *Books1* (public-domain Project Gutenberg text) and *Books2*. Books3 was the third and by far the largest books slice, and the only one sourced from a piracy tracker.

Why books at all, when the web is effectively infinite? Per token, **books are the most valuable part of a pretraining corpus.** They're long-form, professionally edited and coherent over tens of thousands of tokens, so they teach what web text teaches worst: sustained argument, narrative structure, long-range consistency. That's why a 37 GiB pile of pirated books was worth including in an 825 GiB corpus, and why so many models reached for it. It's the concrete face of the shortage in [[Concept - The Data Wall]]. High-quality long-form text is scarce, and the shadow libraries were where it sat, unlicensed.

**Who trained on it.** The Pile, and so the open models trained directly on it: **GPT-J, GPT-NeoX-20B, and Pythia** (all EleutherAI). Per later litigation disclosures, **Meta's LLaMA** and **BloombergGPT** also used Books3 (BloombergGPT's paper lists The Pile among its public data). Around 2020–2022, Books3 was a near-default ingredient in open and semi-open LLMs, because it was openly downloadable and nobody had forced the question of where it came from. [[Reference - Model Genealogy]] now tracks which model lineages touched it, since the answer carries legal weight.

**The takedown.** In 2023 the Danish anti-piracy group **Rights Alliance** issued DMCA notices. Books3 was pulled from its main hosts, The Eye and HuggingFace, and The Pile's official distribution dropped the books component. In the same window, journalist **Alex Reisner (*The Atlantic*)** published a searchable index of Books3 so authors could look up their own pirated work in the corpus that trained the models. Overnight, tens of thousands of writers could see it for themselves, and Books3 became a public cause.

**The litigation.** Books3 is named directly in **Kadrey v. Meta** (plaintiffs including Richard Kadrey and Sarah Silverman) and in Authors Guild suits. Discovery in Kadrey surfaced **internal Meta deliberations about knowingly using Books3**, a rare documented look at a lab weighing pirated data against legal risk and going ahead. The doctrine lives in [[Concept - Copyright and Licensing of Training Data]]: "it was publicly downloadable" is not "it was licensed," and Books3 is the case that showed the distinction has teeth.

## The lesson

Books3 forced the field to accept three things it had been avoiding.

1. **Provenance isn't a formality.** Once pirated data is in a shipped model's lineage, you can't cleanly remove it. The only remedy is retraining without it, at full cost. Cheap to include, ruinously expensive to un-include: so provenance now gets decided *upstream*, at corpus-assembly time, instead of litigated downstream.
2. **The most valuable data is also the most dangerous.** Books are worth so much per token because they're professionally authored, in-copyright works, and that same property makes them the riskiest data to scrape. You don't get long-form quality without copyright exposure.
3. **The reckoning reshaped supply.** Books3's fall set off explicit **license-clean corpus** efforts (Common Pile, KL3M, Common Corpus) that trade size for defensible provenance. It sped up **direct licensing deals**, with labs paying publishers and archives for books instead of scraping them. It also raised the value of [[Concept - Synthetic Training Data|synthetic]] long-form generation as a partial substitute for scraped books, and of pre-2023 archival text generally (the [[Concept - Common Crawl and Web Data at Scale|web crawl]] can't supply what books do).

The doctrinal aftershock came in 2025. In **Bartz v. Anthropic** (Judge William Alsup, N.D. Cal.), court records showed Anthropic had itself downloaded Books3 (in 2021) among other pirated sources before switching to purchased-and-scanned books. The June 2025 ruling drew a sharp line: training on *legally acquired* books is fair use, but *downloading from pirate libraries* is infringement regardless of the eventual use. The piracy exposure drove a reported **~$1.5 billion settlement** (roughly $3,000 per work) later that year. Kadrey v. Meta got a more mixed 2025 ruling, which turned on the plaintiffs failing to show market harm and did not hold the piracy acceptable. The doctrine itself belongs in [[Concept - Copyright and Licensing of Training Data]] and is tracked live in [[Reference - AI Copyright Litigation Tracker]]. For the lore, what matters is that Books3 dragged the whole question into court and made "where did your books come from" a board-level risk.

## Evidence status

**Verified** for the provenance (Presser's own release, Bibliotik origin, The Pile datasheet), the 2023 takedown (Rights Alliance notices, host removals), and the existence and naming of the pleadings (Kadrey, Authors Guild, Bartz). **Well-sourced** for per-model usage drawn from court filings and papers (LLaMA, BloombergGPT, Anthropic's Books3 download), though some usage detail remains **contested or sealed**, and exact per-model book counts vary by filing. The ~$1.5B Anthropic settlement figure is as reported in 2025 coverage of the case. Book count (~196,640) and size (~37 GiB) are the widely cited figures from the corpus's own release and The Pile documentation. [[Reference - Where Real AI Knowledge Lives]] covers following this thread as filings unseal.

## Connections
- [[Concept - Copyright and Licensing of Training Data]] — the doctrine home; Books3 is its litigated worked example of "downloadable ≠ licensed."
- [[Concept - Common Crawl and Web Data at Scale]] — the web can't supply long-form coherence, which is exactly the gap books fill and why the piracy was tempting.
- [[Reference - Model Genealogy]] — tracks which model lineages (GPT-J, NeoX, Pythia, LLaMA, BloombergGPT) touched Books3, now a provenance question with legal stakes.
- [[Lore - The OPT-175B Logbook]] — the sibling open-model war story; both are primary-source windows into how large corpora and runs actually got built.
- [[Concept - Synthetic Training Data]] — one go-forward substitute for scraped books: generate long-form text rather than pirate it.
- [[Concept - The Data Wall]] — books are the scarce premium tokens the field is running short of, which is the pressure that made shadow libraries attractive.
- [[Reference - AI Copyright Litigation Tracker]] — the live record of Kadrey, Authors Guild, and Bartz v. Anthropic and their evolving outcomes.
- [[Reference - Where Real AI Knowledge Lives]] — where these provenance and litigation threads get surfaced as filings unseal.

## Sources
- Gao et al. (2020) — "The Pile: An 800GB Dataset of Diverse Text for Language Modeling": documents Books3 as a component, including its size and provenance.
- Presser, S. (2020) — the public release of Books3 ("all of bibliotik"), the artifact's origin.
- Reisner, A. (2023, *The Atlantic*) — "Revealed: The Authors Whose Pirated Books Are Powering Generative AI": the searchable Books3 index that made the corpus a public cause.
- Bartz v. Anthropic, N.D. Cal. (Judge Alsup, 2025) — the ruling distinguishing lawful acquisition from pirate-library downloading, and the reported ~$1.5B settlement.
