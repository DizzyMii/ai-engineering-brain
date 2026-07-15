---
tags: [concept, domain/data-engineering, level/core]
aliases: [synthetic data, synthetic pretraining data, model-generated data]
summary: "Generating pretraining/mid-training tokens with models instead of harvesting them, and when synthetic tokens help versus hurt."
---
# Concept - Synthetic Training Data

> **One-paragraph hook:** Synthetic training data means using a model — usually a stronger one — to produce the tokens you train the next model on, instead of scraping them off the web. Done carelessly it's a way to launder a teacher's mistakes into a permanent part of a student's weights; done well (Phi, Cosmopedia, WRAP) it's the highest-leverage lever a data team has, because you control style, difficulty, and coverage directly instead of hoping the web happens to contain what you need.

## The mechanism

Synthetic data generation splits into four families, and knowing which one you're running changes what can go wrong:

1. **Distillation from a stronger teacher** — prompt a larger model to produce training examples (Phi's textbook generation, Cosmopedia's synthetic textbooks). The student inherits the teacher's knowledge and its errors alike; this overlaps mechanically with [[Concept - Knowledge Distillation]] but at the pretraining-corpus scale rather than the logit-matching scale.
2. **Rephrasing real web text into a cleaner style** — WRAP (Maini et al. 2024, "Rephrasing the Web") takes real [[Concept - Common Crawl and Web Data at Scale|Common Crawl]] documents and has a model rewrite them "in Wikipedia style" or "in QA style." The facts are real; only the surface form changes.
3. **Task-conditioned generation** — the self-instruct lineage, where a model generates instruction/response pairs from seed tasks. More central to [[Concept - Supervised Fine-Tuning (SFT)]] than pretraining, but the same generation mechanics apply.
4. **Format transformation** — turning raw prose into structured QA pairs or other formats that are easier for a model to learn from directly.

The generation mechanics matter less than the two conditions that determine whether the result helps: diversity and verifiability. Diversity is the primary failure axis — naive sampling from a single teacher with a fixed prompt collapses to a narrow output distribution (predictable phrasing, repeated examples, narrow topic coverage). Cosmopedia's answer was explicit diversity engineering: tens of thousands of topic seeds crossed with hundreds of audience and style variations, forcing coverage that a single "generate more textbooks" prompt would never produce on its own.

Verifiability is the second axis, and it's why synthetic pretraining works best in checkable domains. Phi-1 filtered its synthetic code by actually executing it against test cases — a document only survives if the code it contains runs and passes. Where you can generate-then-verify, you get a training signal that's provably correct, which is a stronger quality guarantee than any classifier-based filter (see [[Concept - Quality Filtering for Pretraining Data]]) can offer. This is the mechanical reason code and math dominate the synthetic-data success stories: correctness is checkable by execution or proof, prose "quality" is not.

## In practice

WRAP is the cleanest quantified result: rephrasing C4 into cleaner styles gave roughly a 3x pretraining speedup and lower perplexity across 21 domains compared to training on the raw web text directly. The mechanism isn't new facts — it's style normalization plus an implicit dedup effect (rephrasing collapses many near-identical noisy phrasings of the same fact into one clean canonical phrasing), which is a data-efficiency win, not a knowledge-injection win.

At the frontier, Phi (see [[Breakdown - The Phi Models and Textbook-Quality Data]]) showed the ceiling of the distillation family: a 1.3B model trained on ~7B curated+synthetic tokens beat models 10x its size on code benchmarks. That's the strongest existence proof in the field that synthetic data, done right, substitutes for raw scale.

Synthetic data is now a standard ingredient in [[Concept - Data Mixtures]], typically upweighted during the annealing/cooldown phase near the end of training alongside code and math, precisely because it's dense in learnable signal per token.

## Failure modes

Two risks dominate. First, hallucination laundering: if the teacher model confidently states something false, the student learns it as ground truth with no way to distinguish it from a verified fact — synthetic data has no independent error-correction mechanism unless you build one in (execution, proof-checking, cross-model consistency checks). Second, silent benchmark contamination: if the teacher memorized eval items during its own training, its synthetic output can reproduce them in paraphrased form, contaminating the student's corpus in a way that plain n-gram [[Concept - Training Set Decontamination]] against the original benchmark text won't catch, because the phrasing has changed.

There's also a legal dimension worth flagging as a failure mode rather than an afterthought: synthetic generation sidesteps copyright on the source text you'd otherwise have scraped, but it inherits the teacher model's terms of service — OpenAI's ToS, for instance, forbids using its outputs to train a competing model — and provenance/watermark leakage from teacher to student is a live, unresolved concern as of 2026.

## The non-obvious

The thing that surprises people who haven't run this pipeline: the failure mode to worry about isn't "the synthetic data is obviously fake and low-quality" — modern teacher models produce fluent, plausible-looking text, so a naive quality filter waves it straight through. The actual risk is distributional: unfiltered, single-teacher synthetic data is dangerously narrow and confidently wrong in ways that are hard to detect by inspection, which is exactly the setup that produces [[Concept - Model Collapse from Synthetic Data]] if you then train the next generation's teacher on this generation's synthetic output without mixing in enough real data. Diversity engineering and generate-then-verify aren't optional polish — they're the two things standing between "quality substitutes for scale" and "garbage compounding."

## Connections
- [[Concept - Knowledge Distillation]] — the logit/response-matching mechanism that synthetic-data generation from a teacher model is a corpus-scale application of.
- [[Breakdown - The Phi Models and Textbook-Quality Data]] — the reference case study for the whole distillation family, including the diversity-engineering trick.
- [[Concept - Model Collapse from Synthetic Data]] — the frontier failure mode that occurs specifically when synthetic data replaces rather than supplements real data across generations.
- [[Concept - Data Mixtures]] — synthetic tokens are one more source that has to be weighted into the mixture, typically upweighted during annealing.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the task-conditioned generation family (self-instruct) is more central to SFT data construction than to pretraining.
- [[Concept - Training Set Decontamination]] — a teacher that memorized benchmarks can leak them into synthetic output in paraphrased form that standard decontamination misses.
- [[Concept - Quality Filtering for Pretraining Data]] — generate-then-verify is a stronger filter than any classifier when the domain is checkable.
- [[Concept - Scaling Laws]] — synthetic data's whole value proposition is raising quality-per-token, which is the exact lever Chinchilla-style compute-optimal training is bottlenecked on.
- [[Concept - Common Crawl and Web Data at Scale]] — rephrasing families like WRAP operate directly on real web text pulled from Common Crawl, making the two techniques complementary rather than competing.

## Sources
- Gunasekar et al. (2023) — "Textbooks Are All You Need": Phi-1's demonstration that curated+synthetic data lets a 1.3B model beat 10x-larger models on code.
- Maini et al. (2024) — "Rephrasing the Web: A Recipe for Compute and Data-Efficient Language Modeling" (WRAP): rephrasing C4 gave ~3x pretraining speedup and lower perplexity across 21 domains.
- Ben Allal et al. (2024) — Cosmopedia (Hugging Face technical report/blog): the diversity-engineering recipe of topic/audience/style seed crossing to avoid teacher-output collapse.
