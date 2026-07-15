---
tags: [concept, domain/data-engineering, level/core]
aliases: [data mix, domain weights, pretraining mixture]
summary: "The per-source sampling weights of a pretraining corpus, and why the mix — not just token count — sets a model's capability profile."
---
# Concept - Data Mixtures

> **One-paragraph hook:** Two corpora can have the same token count and wildly different downstream models, because what matters isn't just how many tokens you train on but where they come from and in what proportion. A data mixture is the set of per-source sampling weights — how much web, code, books, math, and multilingual text — and it's one of the few pretraining decisions that trades off directly against model capabilities, not just loss.

## The mechanism

A mixture assigns a sampling weight to each source, and that weight, combined with the source's raw size, determines how many times each source gets seen relative to a single pass over the whole corpus:

$$
\text{effective epochs}_{\text{domain}} = \frac{\text{weight}_{\text{domain}} \times \text{total tokens}}{|\text{domain}|}
$$

A small, high-quality source like Wikipedia or a curated code corpus is deliberately upsampled — weighted so its effective-epoch count is 2–5x, meaning the training run sees each Wikipedia document multiple times over the course of training — while the much larger, noisier web crawl is downsampled to well under one full epoch. This is the practical mechanism behind "the model saw Wikipedia N times": nobody trains multiple literal passes over just Wikipedia, the sampler just draws from it more often than its raw size alone would justify.

Mixture design is fundamentally a tradeoff allocation problem, not a purity problem. Two effects dominate the tradeoffs:

- **Code helps non-code reasoning.** Adding source code to the mix measurably improves entity tracking, structured reasoning, and chain-of-thought quality — this started as practitioner folklore and has since become measured evidence, one of the more surprising cross-domain transfer effects in pretraining. See [[Concept - Chain-of-Thought and Why It Works]] for the mechanism CoT relies on that code data appears to reinforce.
- **The multilingual tax.** Model capacity is shared across everything it learns, so adding more languages to the mix past a certain point trades English (or whichever language is dominant) quality for multilingual coverage — the "curse of multilinguality." There's no free lunch here; every language you add is language capacity you didn't spend on depth in the languages you already had.

## In practice

Canonical mixes are public enough to compare directly. LLaMA-1 (Touvron et al. 2023) used roughly 67% CommonCrawl, 15% C4, 4.5% GitHub, 4.5% Wikipedia, 4.5% Books, 2.5% arXiv, and 2% StackExchange — note that C4 and CommonCrawl are both present despite heavy overlap in underlying source, because they were processed by different pipelines and treated as distinct signal. GPT-3's mixture upsampled Wikipedia and books by roughly 3.4x relative to their raw share of the pool. The Pile (Gao et al. 2020) took the most hand-crafted approach: 22 distinct components (books, papers, code, dialogue, legal text, and more), each individually weighted rather than treated as one undifferentiated "web + extras" split.

The mixture is not a fixed constant across training — most labs run an **annealing** or **cooldown** phase: during roughly the final 10–20% of training, as the learning rate decays (see [[Concept - Learning Rate Schedules for Pretraining]] in the training-at-scale domain), the mixture shifts to upweight the highest-quality, code, math, and [[Concept - Synthetic Training Data|synthetic]] data. This is distinct from the base mixture and treated as a separate, deliberate late-training intervention — the intuition being that the model is most receptive to high-signal data right as it's converging, and the annealing mix is where labs spend their most expensive tokens.

## Failure modes

The mixture that works is size-dependent, and this is the trap that catches teams who tune once and reuse forever: an optimal mix found by ablating on a 1B-parameter proxy model is often measurably wrong at 70B, because larger models have more capacity to absorb rarer domains without the tradeoffs a small model faces. This transfer failure is exactly what motivates [[Concept - Learned Data Mixing (DoReMi and Mixing Laws)]] as a frontier research direction — hand-tuning at one scale and hoping it holds at another is a documented source of wasted compute.

A second failure mode is invisible until eval time: over-upsampling a small high-quality domain (repeating Wikipedia too many effective epochs) can push that domain past the point of diminishing returns and into mild overfitting on that source specifically, while starving the model of exposure to the long tail of the larger, noisier domains it's being downsampled against.

## The non-obvious

The multilingual tax and the code-helps-reasoning effect point at the same underlying truth that's easy to miss when you think of a mixture as just "how much of each language/format": domains interact. Code isn't in the mix because you want a coding model — many labs add it specifically because it improves general reasoning benchmarks unrelated to code. That's a transfer effect, not a topical one, and it means mixture design is closer to nutrition than to categorization — you're not deciding what topics the model should "know about," you're deciding what cognitive scaffolding different data types build, and those effects cross domain boundaries in ways that aren't obvious from the source labels alone.

## Connections
- [[Concept - Learned Data Mixing (DoReMi and Mixing Laws)]] — the frontier answer to the transfer-failure problem: optimize mixture weights algorithmically instead of hand-tuning and hoping they generalize across scale.
- [[Concept - Scaling Laws]] — mixture weights interact with the token budget Chinchilla-style scaling implies; the right mix at one compute budget isn't guaranteed to be right at another.
- [[Concept - Data Curriculum and Ordering]] — mixtures set the proportions, curriculum sets the order and timing (including the annealing/cooldown phase) in which those proportions are actually presented.
- [[Concept - Synthetic Training Data]] — synthetic tokens are just another source competing for mixture weight, typically upweighted specifically during annealing.
- [[Concept - Quality Filtering for Pretraining Data]] — filtering determines what's even eligible to enter a domain's pool before mixture weighting decides how often it's sampled.
- [[Deep Dive - Anatomy of a Pretraining Run]] — shows where mixture decisions are locked in relative to the rest of a real training run's timeline.
- [[Concept - The Data-Centric View of Model Quality]] — mixture design is a second, independent lever alongside per-document quality filtering under the same data-centric thesis.
- [[Concept - Chain-of-Thought and Why It Works]] — the code-improves-reasoning effect is a concrete, measured instance of a mixture decision changing a capability that has nothing to do with the source's topic label.
- [[Concept - Learning Rate Schedules for Pretraining]] — the annealing/cooldown mixture shift is timed against, and inseparable from, the LR decay schedule it accompanies.

## Sources
- Touvron et al. (2023) — "LLaMA: Open and Efficient Foundation Language Models": published the exact per-source mixture percentages that became a reference point for the field.
- Gao et al. (2020) — "The Pile: An 800GB Dataset of Diverse Text for Language Modeling": the hand-tuned 22-component mixture approach, an early and explicit treatment of mixture design as a first-class decision.
- Xie et al. (2023) — "DoReMi: Optimizing Data Mixtures Speeds Up Language Model Pretraining": the DoReMi result motivating why hand-tuned mixtures don't reliably transfer across scale.
