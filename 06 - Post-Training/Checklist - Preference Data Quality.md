---
tags: [checklist, domain/post-training, level/core]
aliases: [preference dataset QA, DPO data checklist, RM data checklist]
summary: "Pre-flight checks for an SFT or preference dataset before launching alignment training: contamination, length bias, provenance, templates."
---

### Provenance & labeling
- [ ] Every preference pair records its origin (human annotator ID/vendor vs. RLAIF/model-generated) so quality can be traced back to a source.
- [ ] Inter-annotator agreement is measured on a sampled overlap set for human-labeled pairs (expect ~65–75% pairwise agreement — treat anything far outside this band as a labeling-instruction bug, not noise).
- [ ] For [[Concept - Synthetic Training Data]] or RLAIF-labeled pairs, a held-out human-labeled sample is spot-checked against the AI labels to catch systematic labeler bias.

### Content & distinctness
- [ ] Chosen and rejected responses are byte-different after normalization (drop pairs identical or differing only by whitespace/punctuation — they carry zero gradient signal in the [[Concept - Direct Preference Optimization (DPO)]] loss).
- [ ] Pairs with near-zero preference margin (labeler was near the decision boundary, or an ensemble [[Concept - Reward Models|reward model]] shows high disagreement) are flagged and down-weighted or dropped — these are the noisiest examples in the set.
- [ ] Prompts and responses are checked for leaked system prompts, injected instructions, or boilerplate refusal templates that shouldn't be present in training data.

### Distribution & balance
- [ ] Mean token length of chosen vs. rejected responses is compared per data source; a systematic gap (chosen consistently longer) means the model will learn length as a proxy for quality rather than quality itself — see [[Concept - Length Bias in Preference Optimization]]. This is the single most common silent bug in preference datasets.
- [ ] Refusal/safety pairs are balanced against helpfulness pairs so the resulting model does not learn to over-refuse benign requests.
- [ ] The prompt distribution is checked against the deployment task mix (by category/topic clustering); prompts far off the target distribution waste training budget without moving the metrics that matter.

### Deduplication & contamination
- [ ] Near-duplicate prompts are removed via [[Concept - Deduplication at Scale|MinHash/LSH]] or embedding-similarity clustering; duplicated prompts overweight those examples in the gradient and cause overfitting.
- [ ] Prompts and responses are checked for n-gram and embedding overlap against every eval set the model will be scored on — see [[Concept - Benchmark Contamination]]. Contamination here silently and permanently inflates benchmark numbers with no training-time signal that anything went wrong.
- [ ] PII is scanned and scrubbed from both prompts and responses before the data enters the training pipeline.

### Formatting
- [ ] The chat template is applied identically to chosen and rejected completions, with correct role tokens and special tokens on both sides — a template that differs even by one token invalidates the pair's log-probability comparison.
- [ ] EOS/eot tokens are present and unmasked in both chosen and rejected sequences so the implicit reward comparison isn't corrupted by a missing terminator.

## Why these items

- **Length balance is listed first among distribution checks because it is the hardest bug to see and the easiest to introduce.** Preference data collected from a stronger model (RLAIF, or humans instructed to prefer "more thorough" answers) is very often longer on the chosen side by construction. Nothing in a DPO or RM training run errors out on this — loss goes down, reward accuracy goes up, and the deployed model just gets verbose. This is the mechanism documented in [[Concept - Length Bias in Preference Optimization]].
- **Contamination checks exist because eval inflation from preference data is invisible at training time.** A preference dataset scraped or generated from the same distribution as a benchmark (e.g., paraphrased GSM8K problems) will make the model look better on that benchmark for reasons that have nothing to do with generalization — the failure only shows up as a mysterious gap between reported eval numbers and real-world behavior.
- **Near-zero-margin pairs are flagged rather than silently kept because they are disproportionately mislabels.** Human labelers agree least (and flip labels most under repeat annotation) exactly where the true preference gap is smallest; training on these pairs at full weight injects label noise precisely where the gradient signal is weakest anyway.
- **Template identity between chosen and rejected matters because DPO-family losses compare log-probabilities computed under the same tokenization.** A stray extra BOS token or a different system-prompt slot on one side of the pair shifts that sequence's log-probability for reasons unrelated to quality, corrupting the margin the loss is trying to learn.

## Connections

- [[Concept - Reward Models]] — this checklist is the data-quality gate that Bradley-Terry RM training assumes has already been passed.
- [[Concept - Direct Preference Optimization (DPO)]] — the algorithm most directly harmed by duplicate, identical, or length-biased pairs; several checklist items exist specifically to protect its loss.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the surface-level, down-link prerequisite stage; preference data quality assumes the SFT data hygiene pass already happened.
- [[Concept - Deduplication at Scale]] — the mechanism (MinHash/LSH) behind the dedup checklist item, imported from data engineering (domain 05, cross-domain).
- [[Concept - Benchmark Contamination]] — the general contamination mechanism this checklist applies specifically to preference pairs (domain 13, cross-domain).
- [[Concept - Length Bias in Preference Optimization]] — the unicorn-level deep mechanism behind the checklist's most important single item.
- [[Concept - Synthetic Training Data]] — covers the provenance and quality risks specific to AI-generated (RLAIF) preference data (domain 05, cross-domain).
