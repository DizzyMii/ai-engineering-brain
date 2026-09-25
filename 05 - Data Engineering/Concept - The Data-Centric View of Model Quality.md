---
tags: [concept, domain/data-engineering, level/surface]
aliases: [data-centric AI, data-centric pretraining]
summary: "The ~2020-2024 thesis that data curation, not architecture, explains most of the quality gap between models at fixed compute."
---
# Concept - The Data-Centric View of Model Quality

> **One-paragraph hook:** Ask why one 7B model beats another 7B model trained on the same compute budget, and by 2024 the honest answer was almost never "better architecture." It was "better data." The data-centric view is the field's collective conclusion that once you fix the decoder-only transformer and the compute budget implied by [[Concept - Scaling Laws]], the pretraining corpus is the dominant lever on model quality. It's also the one lever frontier labs don't publish.

## The mechanism

The argument has three legs.

Compute-optimality comes first. Chinchilla (Hoffmann et al. 2022) found that compute-optimal training wants roughly 20 tokens per parameter, so every frontier run is data-hungry by construction. You can't make up for weak per-token signal with more parameters, because the compute-optimal parameter count is itself a function of the token budget. Low-quality tokens put a floor under your loss no matter how you spend the parameter budget.

Then there's measured effect size. FineWeb's ablation method (Penedo et al. 2024) made this quantifiable: train an identical 1.8B model on 350B tokens of each candidate dataset, hold everything else fixed, and compare on a curated high-signal eval suite. Under that protocol, curation choices alone move downstream accuracy by 5–15 points at fixed compute. Most architecture ablations at that scale produce a smaller swing.

The third leg is an existence proof that data substitutes for scale. Phi-1 (Gunasekar et al. 2023, "Textbooks Are All You Need," see [[Breakdown - The Phi Models and Textbook-Quality Data]]) trained a 1.3B model on roughly 7B tokens of curated and [[Concept - Synthetic Training Data|synthetic]] "textbook-quality" data and beat models an order of magnitude larger on code benchmarks. That only makes sense if quality-per-token, not parameter count, was the limit.

DCLM (Li et al. 2024) turned this into a proper benchmark. It fixes the model architecture and the raw candidate pool and scores only the filtering pipeline. Under DCLM's protocol a better curation pipeline beat the prior open state of the art by a wide margin, isolating data as the experimental variable the way a benchmark should.

## In practice

"Garbage in, garbage out" is now a number. A typical modern pipeline discards 90–99% of raw [[Concept - Common Crawl and Web Data at Scale|Common Crawl]] tokens through [[Concept - Quality Filtering for Pretraining Data|quality filtering]] and dedup and keeps the useful few percent. Teams now tune and ablate that survival rate instead of treating it as a side effect of cleaning.

The competitive implication matters more if you read model announcements. Architectures have converged (essentially everyone runs a decoder-only transformer with minor variants) and show up in papers within weeks of release. Data pipelines don't. Labs disclose token counts and vague source categories but almost never the filtering thresholds, classifier training sets or mixture weights. As of 2026, the undocumented data pipeline is one of the few durable moats a frontier lab has, because it's the lever that measurably matters and nobody open-sources it in full.

## Failure modes

The data-centric view is easy to over-apply. "More filtering is always better" is false. In [[Lore - The C4 Blocklist Incident]], an aggressive filter silently deleted whole demographics' text from a corpus that trained a generation of models. Quality filters are trained against some notion of "quality" (often "looks like Wikipedia") that encodes its own bias, so chasing eval gains with ever-harsher filtering can narrow the model's world without anyone noticing.

The other trap is misattribution. A team sees a competitor's model beat theirs at similar scale and assumes a secret architecture trick. The FineWeb/DCLM evidence says a better-curated corpus is the far likelier explanation, and hunting for architecture explanations of data-driven gaps wastes research cycles.

## The non-obvious

The naive intuition says bigger, more diverse raw data is strictly better. FineWeb's own ablations found the opposite: a smaller, more aggressively curated subset (FineWeb-Edu) beat the larger unfiltered pool on knowledge benchmarks. Quality-per-token, not token count, is what moves eval numbers. So a public claim like "we trained on X trillion tokens" is close to meaningless without the survival rate and filtering criteria behind it. Two "15T-token" corpora built with different filters are different products.

## Connections
- [[Concept - Scaling Laws]] — Chinchilla's tokens-per-parameter result is the mathematical premise that makes per-token data quality binding in the first place.
- [[Breakdown - FineWeb and FineWeb-Edu]] — the canonical ablation-driven demonstration that curation choices move eval numbers by double digits at fixed compute.
- [[Concept - Quality Filtering for Pretraining Data]] — the mechanism-level note on how "quality" actually gets operationalized into filters.
- [[Concept - Synthetic Training Data]] — the most aggressive form of data-centric intervention: don't just filter what exists, generate better tokens outright.
- [[Breakdown - The Phi Models and Textbook-Quality Data]] — the existence proof that a small model on curated+synthetic data beats far larger models trained on raw web text.
- [[Deep Dive - Anatomy of a Pretraining Run]] — shows where data-curation decisions actually plug into a real training run's timeline and budget.
- [[Concept - Data Mixtures]] — the data-centric view isn't just about filtering quality, it's also about the proportions of domains you mix, which is its own lever.
- [[Concept - The Open vs Closed Model Divide]] — since architecture is public and data pipelines aren't, the data-centric moat is a direct driver of why closed labs stay ahead even when their published techniques are replicated.
- [[Concept - Common Crawl and Web Data at Scale]] — it is the raw material whose curated survival rate is the concrete thing the data-centric thesis is arguing you should optimize.
- [[Lore - The C4 Blocklist Incident]] — the cautionary case where chasing "quality" through aggressive filtering did measurable harm, proof the data-centric view isn't a free lunch.

## Sources
- Hoffmann et al. (2022) — "Training Compute-Optimal Large Language Models" (Chinchilla): established the ~20 tokens/parameter compute-optimal ratio that makes per-token data quality a binding constraint.
- Penedo et al. (2024) — "FineWeb: decanting the web for the finest text data at scale": the ablation methodology that turned "data quality matters" into a measured 5–15 point effect.
- Gunasekar et al. (2023) — "Textbooks Are All You Need": Phi-1's existence proof that curated+synthetic data lets a small model beat 10x-larger ones on code.
- Li et al. (2024) — "DataComp-LM: In search of the next generation of training sets for language models" (DCLM): a standardized benchmark that isolates data curation as the experimental variable.
