---
tags: [checklist, domain/post-training, level/core]
aliases: [preference dataset QA, DPO data checklist, RM data checklist]
summary: "Pre-flight checks for an SFT or preference dataset before launching alignment training: contamination, length bias, provenance, templates."
---

### Provenance & labeling
- [ ] Every preference pair records where it came from (human annotator ID/vendor vs. RLAIF/model-generated), so quality problems can be traced to a source.
- [ ] For human-labeled pairs, inter-annotator agreement is measured on a sampled overlap set. Expect ~65–75% pairwise agreement; anything far outside that band is a labeling-instruction bug, not noise.
- [ ] For [[Concept - Synthetic Training Data]] or RLAIF-labeled pairs, a held-out human-labeled sample is spot-checked against the AI labels to catch systematic labeler bias.

### Content & distinctness
- [ ] Chosen and rejected responses differ after normalization. Drop pairs that are identical or differ only in whitespace/punctuation; they carry zero gradient signal in the [[Concept - Direct Preference Optimization (DPO)]] loss.
- [ ] Pairs with near-zero preference margin (labeler near the decision boundary, or high disagreement in an ensemble [[Concept - Reward Models|reward model]]) are flagged and down-weighted or dropped. They're the noisiest examples in the set.
- [ ] Prompts and responses are checked for leaked system prompts, injected instructions, or boilerplate refusal templates that don't belong in training data.

### Distribution & balance
- [ ] Mean token length of chosen vs. rejected is compared per data source. If chosen is consistently longer, the model learns length as a proxy for quality (see [[Concept - Length Bias in Preference Optimization]]). This is the most common silent bug in preference datasets.
- [ ] Refusal/safety pairs are balanced against helpfulness pairs so the model doesn't learn to over-refuse benign requests.
- [ ] The prompt distribution is compared against the deployment task mix by category/topic clustering. Prompts far off the target distribution burn training budget without moving the metrics that matter.

### Deduplication & contamination
- [ ] Near-duplicate prompts are removed with [[Concept - Deduplication at Scale|MinHash/LSH]] or embedding-similarity clustering. Duplicates overweight those examples in the gradient and cause overfitting.
- [ ] Prompts and responses are checked for n-gram and embedding overlap against every eval set the model will be scored on ([[Concept - Benchmark Contamination]]). Contamination here inflates benchmark numbers silently and permanently, with no training-time sign that anything went wrong.
- [ ] PII is scanned for and scrubbed from prompts and responses before the data enters the training pipeline.

### Formatting
- [ ] The chat template is applied identically to chosen and rejected completions, with correct role and special tokens on both sides. A template that differs by even one token invalidates the pair's log-probability comparison.
- [ ] EOS/eot tokens are present and unmasked in both sequences, so a missing terminator can't corrupt the implicit reward comparison.

## Why these items

- **Length balance leads the distribution checks because it's the hardest bug to see and the easiest to introduce.** Preference data collected from a stronger model (RLAIF, or humans told to prefer "more thorough" answers) is very often longer on the chosen side by construction. Nothing in a DPO or RM run errors out. Loss goes down, reward accuracy goes up, and the deployed model just gets verbose. The mechanism is in [[Concept - Length Bias in Preference Optimization]].
- **Contamination checks exist because eval inflation from preference data is invisible at training time.** A preference set scraped or generated from the same distribution as a benchmark (e.g., paraphrased GSM8K problems) makes the model look better on that benchmark for reasons unrelated to generalization. You only see it later, as an unexplained gap between reported evals and real-world behavior.
- **Near-zero-margin pairs get flagged because they're disproportionately mislabels.** Human labelers agree least, and flip labels most on repeat annotation, where the true preference gap is smallest. Training on those pairs at full weight puts label noise right where the gradient signal is already weakest.
- **Chosen and rejected need identical templates because DPO-family losses compare log-probabilities computed under the same tokenization.** A stray extra BOS token or a different system-prompt slot on one side shifts that sequence's log-probability for reasons unrelated to quality, and corrupts the margin the loss is trying to learn.

## Connections

- [[Concept - Reward Models]] — this checklist is the data-quality gate that Bradley-Terry RM training assumes has already been passed.
- [[Concept - Direct Preference Optimization (DPO)]] — the algorithm most directly harmed by duplicate, identical, or length-biased pairs; several checklist items exist specifically to protect its loss.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the surface-level, down-link prerequisite stage; preference data quality assumes the SFT data hygiene pass already happened.
- [[Concept - Deduplication at Scale]] — the mechanism (MinHash/LSH) behind the dedup checklist item, imported from data engineering (domain 05, cross-domain).
- [[Concept - Benchmark Contamination]] — the general contamination mechanism this checklist applies specifically to preference pairs (domain 13, cross-domain).
- [[Concept - Length Bias in Preference Optimization]] — the unicorn-level deep mechanism behind the checklist's most important single item.
- [[Concept - Synthetic Training Data]] — covers the provenance and quality risks specific to AI-generated (RLAIF) preference data (domain 05, cross-domain).
