---
tags: [lore, domain/data-engineering, level/unicorn]
aliases: [C4 bad words list, LDNOOBW, Colossal Clean Crawled Corpus blocklist, Documenting C4, Dodge 2021]
summary: "How C4's 'bad words' blocklist quietly deleted LGBTQ and dialect content from the corpus behind a generation of models."
---
# Lore - The C4 Blocklist Incident

## What happened

Raffel et al. (2020) built C4, the Colossal Clean Crawled Corpus, to train T5. It came from a single April 2019 [[Concept - Common Crawl and Web Data at Scale|Common Crawl]] snapshot and became one of the most-used open pretraining corpora of its era: ~156 billion tokens of English web text, later folded into other mixes as a component (LLaMA-1 drew 15% of its data from C4). The story is in the word "Clean". The authors ran a set of [[Concept - Quality Filtering for Pretraining Data|heuristic filters]]: keep lines ending in terminal punctuation, drop short pages, remove `lorem ipsum` and `{` for code. One line-item in the methods section looked harmless: **any document containing a word on a blocklist was removed entirely.**

That blocklist was the "List of Dirty, Naughty, Obscene, and Otherwise Bad Words" (LDNOOBW), a GitHub list that started at Shutterstock for filtering *autocomplete suggestions*. Over-blocking a search box costs nothing. Used as a document-level pretraining filter, the same list deletes a whole page if one listed term appears anywhere in it, with no notion of context, sense or intent.

In 2021 Dodge et al. published "Documenting Large Webtext Corpora: A Case Study on the Colossal Clean Crawled Corpus" (EMNLP 2021). It was a *documentation audit* that reverse-engineered what C4 contained and, more pointedly, what it had thrown away. The findings became a landmark:

- The blocklist **disproportionately removed content about LGBTQ+ identities and sexual health**. Identity terms and slang carry sexual senses the list flags out of context, so a page discussing gay identity or a clinic's STI information page could contain a listed word and vanish wholesale.
- It **over-removed text in African-American English and Hispanic-aligned English**. Dialect features co-occur with flagged slang, so entire registers of real human writing were filtered out at higher rates. This mirrors, on the corpus side, Sap et al. (2019), which showed toxicity classifiers flag AAE as "toxic" far more often than Standard American English.
- **Clinical descriptions of sexual violence survived**, because the blocklist doesn't contain clinical vocabulary. The filter removed marginalized *voices* and kept the *content* it was ostensibly there to guard against.
- Separately, the audit found **entire domains excluded** (some benign), **evaluation-benchmark text present in C4** (a documented contamination finding), and heavy **over-representation of patent and US-government text**. "Web text" is not a neutral sample of human language.

None of this was malicious. A one-line default, inherited from a tool built for a different job, shipped inside a corpus that trained a generation of models before anyone audited what "clean" had cost.

## The lesson

The mechanical lesson generalizes past C4: **a lexical blocklist conflates a word with a harm.** "Clean" means "contains none of the list author's tokens," so the corpus inherits the blind spots and cultural assumptions of whoever wrote the list. It does so silently, since a document-level drop leaves no trace in the surviving data. Filtering at *pretraining* time also removes the model's *exposure to entire topics*, and with it the ability to discuss, recognize or refuse them later. You can't post-hoc teach a model to handle LGBTQ health questions well if it never saw the vocabulary during pretraining. [[Concept - PII and Toxicity Filtering]] catalogues the same over-filtering / distribution-shift harm: aggressive cleaning trades diversity and robustness for a superficial safety metric, and you only see the trade if you audit the rejected pile.

C4 is now the standard cautionary tale behind three lasting changes in practice:

1. **Datasheets and documentation as a deliverable.** A corpus ships with an account of what it includes *and excludes*. The Dodge paper is why "just document the dataset" stopped being optional.
2. **Audited classifier/annotator filtering over word blocklists.** Modern pipelines prefer learned quality signals validated by ablation (the FineWeb-Edu approach) to lexical lists. As [[Reference - Data Filtering Heuristics]] records, classifiers have their *own* narrowing failure mode, so the fix is auditing, whatever the method.
3. **Push safety to post-training, not the pretrain corpus.** Consensus moved toward filtering lightly at pretrain, which preserves the model's world-knowledge and its ability to recognize harmful content, and handling refusals downstream through [[Concept - Refusal Mechanics]] and alignment instead of lobotomizing the base corpus. A blocklist can't tell a slur from a reclaimed identity term or a clinical fact. A post-trained model, in principle, can.

For anyone building a corpus: the filter you copied from someone else's repo has *their* assumptions baked in, and at web scale those assumptions become the boundaries of what your model can think about.

## Evidence status

**Verified.** C4, the LDNOOBW blocklist and the Dodge et al. (2021) audit are all public and reproducible. The paper's analysis ran on a released reconstruction of C4 (`allenai/c4`), the blocklist is a public GitHub repo, and the filtering code is in the T5 release. The paper documents the disproportionate-removal findings with examples. The causal claim ("this made the models worse at X") is an inference from the removal statistics, not a controlled ablation, and is stated as such here. See [[Reference - Where Real AI Knowledge Lives]] for tracking this class of dataset-documentation work.

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
