---
tags: [lore, domain/data-engineering, level/unicorn]
aliases: [C4 bad words list, LDNOOBW, Colossal Clean Crawled Corpus blocklist, Documenting C4, Dodge 2021]
summary: "How C4's 'bad words' blocklist quietly deleted LGBTQ and dialect content from the corpus behind a generation of models."
---
# Lore - The C4 Blocklist Incident

## What happened

C4 — the Colossal Clean Crawled Corpus — was built by Raffel et al. (2020) to train T5, out of a single April 2019 [[Concept - Common Crawl and Web Data at Scale|Common Crawl]] snapshot. It became one of the most-used open pretraining corpora of its era: ~156 billion tokens of English web text, later folded as a component into other mixes (LLaMA-1 drew 15% of its data from C4). The "Clean" in the name is the whole story here. To produce it, the authors ran a set of [[Concept - Quality Filtering for Pretraining Data|heuristic filters]] (keep lines ending in terminal punctuation, drop short pages, remove `lorem ipsum` and `{` for code) — and one line-item that looked innocuous in the methods section: **any document containing a word on a blocklist was removed entirely.**

The blocklist was the "List of Dirty, Naughty, Obscene, and Otherwise Bad Words" (LDNOOBW), a GitHub list that originated at Shutterstock to filter *autocomplete suggestions* — a context where over-blocking a search box costs nothing. Applied as a document-level pretraining filter, it does something very different: it deletes the whole page if a single listed term appears anywhere in it, with no notion of context, sense, or intent.

In 2021, Dodge et al. published "Documenting Large Webtext Corpora: A Case Study on the Colossal Clean Crawled Corpus" (EMNLP 2021) — a *documentation audit*, reverse-engineering what C4 actually contained and, more pointedly, what it had thrown away. The findings became a landmark:

- The blocklist **disproportionately removed content about LGBTQ+ identities and sexual health**, because identity terms and slang carry sexual senses the list flags out of context (a page discussing gay identity or a clinic's STI information page could contain a listed word and vanish wholesale).
- It **over-removed text in African-American English and Hispanic-aligned English** — dialect features co-occur with flagged slang, so entire registers of real human writing were filtered out at higher rates. This is the corpus-side mirror of Sap et al. (2019), which showed toxicity classifiers flag AAE as "toxic" far more often than Standard American English.
- Meanwhile, **clinical descriptions of sexual violence survived**, because they use clinical vocabulary the blocklist doesn't contain — so the filter removed marginalized *voices* while keeping the *content* it was ostensibly there to guard against.
- Orthogonally, the audit found **entire domains excluded** (some benign), **evaluation-benchmark text present in C4** (a documented contamination finding), and heavy **over-representation of patent and US-government text** — a reminder that "web text" is not a neutral sample of human language.

None of this was malicious. It was a one-line default, inherited from a tool built for a different job, shipped inside a corpus that trained a generation of models before anyone audited what "clean" had actually cost.

## The lesson

The mechanical lesson is precise, and it generalizes past C4: **a lexical blocklist conflates a word with a harm.** "Clean" is operationally defined as "contains none of the list author's tokens," so the corpus inherits the blind spots and cultural assumptions of whoever wrote the list — and does so silently, because a document-level drop leaves no trace in the surviving data. Worse, filtering at *pretraining* time doesn't just remove offensive text; it removes the model's *exposure to entire topics*, and therefore its ability to discuss, recognize, or refuse them later. You cannot post-hoc teach a model to handle LGBTQ health questions gracefully if it never saw the vocabulary during pretraining. This is the same over-filtering / distribution-shift harm catalogued in [[Concept - PII and Toxicity Filtering]]: aggressive cleaning trades diversity and robustness for a superficial safety metric, and the trade is invisible unless you audit the rejected pile.

C4 is now the canonical cautionary tale behind three durable practice changes:

1. **Datasheets and documentation-as-a-deliverable.** A corpus ships with an account of what it includes *and excludes*; the Dodge paper is the reason "just document the dataset" stopped being optional.
2. **Audited classifier/annotator filtering over word blocklists.** Modern pipelines prefer learned quality signals validated by ablation (the FineWeb-Edu approach) to lexical lists — though as [[Reference - Data Filtering Heuristics]] records, classifiers have their *own* narrowing failure mode, so the fix is auditing, not any single method.
3. **Push safety to post-training, not the pretrain corpus.** The field's consensus moved toward filtering lightly at pretrain (to preserve the model's world-knowledge and its ability to recognize harmful content) and handling refusals downstream through [[Concept - Refusal Mechanics]] and alignment, rather than lobotomizing the base corpus. A blocklist can't distinguish a slur from a reclaimed identity term or a clinical fact; a post-trained model, in principle, can.

The meta-lesson for anyone building a corpus: the filter you copied from someone else's repo has *their* assumptions baked in, and at web scale those assumptions become the boundaries of what your model can think about.

## Evidence status

**Verified.** C4, the LDNOOBW blocklist, and the Dodge et al. (2021) audit are all public and reproducible — the paper's analysis was run on a released reconstruction of C4 (`allenai/c4`), the blocklist is a public GitHub repo, and the filtering code is in the T5 release. The disproportionate-removal findings are documented in the paper with examples; the causal claim ("this made the models worse at X") is an inference from the removal statistics rather than a controlled ablation, and is stated as such here. See [[Reference - Where Real AI Knowledge Lives]] for tracking this class of dataset-documentation work.

## Connections
- [[Concept - Quality Filtering for Pretraining Data]] — C4 is the worked example of the heuristic/blocklist filtering paradigm and its distribution-shift failure mode.
- [[Concept - PII and Toxicity Filtering]] — the general safety/diversity tradeoff that the blocklist got catastrophically wrong; AAE over-flagging (Sap et al. 2019) is the shared thread.
- [[Reference - Data Filtering Heuristics]] — the exact C4 rules (terminal-punctuation, `lorem ipsum`, the bad-words list) live here as lookup constants.
- [[Concept - Training Set Decontamination]] — the audit also found benchmark text inside C4, an early documented contamination case.
- [[Concept - Refusal Mechanics]] — the modern alternative: handle harmful content via post-training refusals rather than deleting topics from the pretrain corpus.
- [[Concept - Common Crawl and Web Data at Scale]] — C4 is a single 2019 Common Crawl snapshot run through the filters; the raw material whose long tail the blocklist truncated.
- [[Reference - Where Real AI Knowledge Lives]] — where dataset-documentation audits like this one get surfaced and tracked.

## Sources
- Dodge et al. (2021) — "Documenting Large Webtext Corpora: A Case Study on the Colossal Clean Crawled Corpus" (EMNLP 2021): the audit that exposed the blocklist's disproportionate removals and C4's other biases.
- Raffel et al. (2020) — "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer" (T5): the paper that built C4 and applied the LDNOOBW blocklist.
- Sap et al. (2019) — "The Risk of Racial Bias in Hate Speech Detection": the toxicity-classifier bias against African-American English that the corpus-side finding mirrors.
