---
tags: [concept, domain/data-engineering, level/core]
aliases: [synthetic data, synthetic pretraining data, model-generated data]
summary: "Generating pretraining/mid-training tokens with models instead of harvesting them, and when synthetic tokens help versus hurt."
---
# Concept - Synthetic Training Data

> **One-paragraph hook:** Synthetic training data means using a model, usually a stronger one, to produce the tokens you train the next model on instead of scraping them off the web. Done carelessly, it launders a teacher's mistakes permanently into a student's weights. Done well (Phi, Cosmopedia, WRAP), it's the highest-leverage tool a data team has, because you set style, difficulty and coverage directly instead of hoping the web happens to contain what you need.

## The mechanism

There are four families of synthetic data generation, and which one you're running changes what can go wrong:

1. **Distillation from a stronger teacher.** Prompt a larger model to write training examples (Phi's textbook generation, Cosmopedia's synthetic textbooks). The student inherits the teacher's knowledge and its errors alike. Mechanically this overlaps with [[Concept - Knowledge Distillation]], but at pretraining-corpus scale instead of logit matching.
2. **Rephrasing real web text into a cleaner style.** WRAP (Maini et al. 2024, "Rephrasing the Web") takes real [[Concept - Common Crawl and Web Data at Scale|Common Crawl]] documents and has a model rewrite them "in Wikipedia style" or "in QA style." The facts are real; only the surface form changes.
3. **Task-conditioned generation.** The self-instruct lineage: a model generates instruction/response pairs from seed tasks. This matters more for [[Concept - Supervised Fine-Tuning (SFT)]] than for pretraining, but the generation mechanics are the same.
4. **Format transformation.** Turning raw prose into structured QA pairs or other formats a model learns from more directly.

Whether the result helps depends less on generation mechanics than on two conditions: diversity and verifiability. Diversity is where most runs fail. Naive sampling from one teacher with a fixed prompt collapses to a narrow output distribution: predictable phrasing, repeated examples, thin topic coverage. Cosmopedia handled this with explicit diversity engineering, crossing tens of thousands of topic seeds with hundreds of audience and style variations. A single "generate more textbooks" prompt would never produce that coverage on its own.

Verifiability is the second condition, and it's why synthetic pretraining works best in checkable domains. Phi-1 filtered its synthetic code by executing it against test cases, so a document survived only if its code ran and passed. When you can generate-then-verify, the training signal is provably correct, a stronger guarantee than any classifier-based filter (see [[Concept - Quality Filtering for Pretraining Data]]) can give. Code and math dominate the synthetic-data success stories for this reason: execution or proof can check correctness, and nothing can check prose "quality" that way.

## In practice

WRAP has the cleanest quantified result. Rephrasing C4 into cleaner styles gave roughly a 3x pretraining speedup and lower perplexity across 21 domains versus training on the raw web text. No new facts went in. The gain comes from style normalization plus an implicit dedup effect: rephrasing collapses many near-identical noisy phrasings of a fact into one clean canonical phrasing. That's a data-efficiency win, and it injects no knowledge.

Phi (see [[Breakdown - The Phi Models and Textbook-Quality Data]]) showed how far the distillation family can go. A 1.3B model trained on ~7B curated+synthetic tokens beat models 10x its size on code benchmarks. It's the strongest existence proof in the field that synthetic data, done right, substitutes for raw scale.

Synthetic data is now a standard ingredient in [[Concept - Data Mixtures]]. It's typically upweighted during the annealing/cooldown phase near the end of training, alongside code and math, because it packs a lot of learnable signal per token.

## Failure modes

Two risks dominate. The first is hallucination laundering. If the teacher confidently states something false, the student learns it as ground truth and can't tell it apart from a verified fact. Synthetic data has no independent error correction unless you build it in (execution, proof-checking, cross-model consistency checks).

The second is silent benchmark contamination. A teacher that memorized eval items during its own training can reproduce them in paraphrased form. That contaminates the student's corpus in a way plain n-gram [[Concept - Training Set Decontamination]] against the original benchmark text won't catch, since the phrasing has changed.

Legal exposure belongs on this list too, not in a footnote. Synthetic generation sidesteps copyright on the source text you'd otherwise have scraped, but it inherits the teacher model's terms of service (OpenAI's ToS, for instance, forbids using its outputs to train a competing model). Provenance and watermark leakage from teacher to student is a live, unresolved concern as of 2026.

## The non-obvious

People who haven't run this pipeline expect the problem to be obviously fake, low-quality text. It isn't. Modern teachers write fluent, plausible text, and a naive quality filter waves it straight through. The risk is distributional: unfiltered single-teacher synthetic data is dangerously narrow and confidently wrong in ways inspection won't reveal. Train the next generation's teacher on this generation's synthetic output without enough real data mixed in and you get [[Concept - Model Collapse from Synthetic Data]]. Diversity engineering and generate-then-verify are the two things separating "quality substitutes for scale" from "garbage compounding," so don't treat them as polish.

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
