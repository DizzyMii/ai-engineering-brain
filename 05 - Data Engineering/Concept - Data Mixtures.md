---
tags: [concept, domain/data-engineering, level/core]
aliases: [data mix, domain weights, pretraining mixture]
summary: "The per-source sampling weights of a pretraining corpus, and why the mix — not just token count — sets a model's capability profile."
---
# Concept - Data Mixtures

> **One-paragraph hook:** Two corpora with the same token count can produce wildly different models, because where the tokens come from and in what proportion matters as much as how many there are. A data mixture is the set of per-source sampling weights: how much web, code, books, math and multilingual text. It's one of the few pretraining decisions that trades off directly against model capabilities, beyond loss.

## The mechanism

A mixture assigns a sampling weight to each source. That weight, together with the source's raw size, sets how many times each source gets seen relative to a single pass over the whole corpus:

$$
\text{effective epochs}_{\text{domain}} = \frac{\text{weight}_{\text{domain}} \times \text{total tokens}}{|\text{domain}|}
$$

A small, high-quality source like Wikipedia or a curated code corpus gets deliberately upsampled to an effective-epoch count of 2–5x, so the run sees each Wikipedia document several times. The much larger, noisier web crawl is downsampled to well under one full epoch. That's what "the model saw Wikipedia N times" means in practice. Nobody runs literal extra passes over Wikipedia; the sampler just draws from it more often than its raw size would justify.

Mixture design is an allocation problem with tradeoffs, and purity isn't the goal. Two effects dominate:

- **Code helps non-code reasoning.** Adding source code measurably improves entity tracking, structured reasoning and chain-of-thought quality. It started as practitioner folklore and is now measured evidence, one of the more surprising cross-domain transfer effects in pretraining. See [[Concept - Chain-of-Thought and Why It Works]] for the mechanism CoT relies on that code data appears to reinforce.
- **The multilingual tax.** Model capacity is shared across everything it learns, so past a certain point, adding languages trades English (or whichever language dominates) quality for multilingual coverage. This is the "curse of multilinguality." There's no free lunch: every language you add is capacity you didn't spend on depth in the languages you already had.

## In practice

Canonical mixes are public enough to compare. LLaMA-1 (Touvron et al. 2023) used roughly 67% CommonCrawl, 15% C4, 4.5% GitHub, 4.5% Wikipedia, 4.5% Books, 2.5% arXiv and 2% StackExchange. C4 and CommonCrawl overlap heavily in underlying source but both appear, because they went through different pipelines and were treated as distinct signal. GPT-3's mixture upsampled Wikipedia and books by roughly 3.4x relative to their raw share of the pool. The Pile (Gao et al. 2020) was the most hand-crafted: 22 distinct components (books, papers, code, dialogue, legal text and more), each weighted individually instead of lumped into one "web + extras" split.

The mixture isn't constant across training. Most labs run an **annealing** or **cooldown** phase: in roughly the final 10–20% of training, as the learning rate decays (see [[Concept - Learning Rate Schedules for Pretraining]] in the training-at-scale domain), the mixture shifts to upweight the highest-quality, code, math and [[Concept - Synthetic Training Data|synthetic]] data. It's treated as a separate, deliberate late-training intervention, distinct from the base mixture. The intuition is that the model is most receptive to high-signal data right as it converges, so the annealing mix is where labs spend their most expensive tokens.

## Failure modes

The mixture that works depends on model size, and teams that tune once and reuse forever get caught by this. An optimal mix found by ablating a 1B-parameter proxy is often measurably wrong at 70B, because larger models have more capacity to absorb rarer domains without the tradeoffs a small model faces. That transfer failure is what motivates [[Concept - Learned Data Mixing (DoReMi and Mixing Laws)]] as a frontier research direction. Hand-tuning at one scale and hoping it holds at another is a documented source of wasted compute.

A second failure stays invisible until eval time. Over-upsampling a small high-quality domain (too many effective epochs of Wikipedia) can push it past diminishing returns into mild overfitting on that source, while starving the model of the long tail in the larger, noisier domains it's being downsampled against.

## The non-obvious

The multilingual tax and the code-helps-reasoning effect point at the same thing, and it's easy to miss if you think of a mixture as "how much of each language/format": domains interact. Many labs add code specifically because it improves general reasoning benchmarks unrelated to code, not because they want a coding model. That's a transfer effect, not a topical one. I'd compare mixture design to nutrition more than to categorization: you're deciding what cognitive scaffolding each data type builds, and those effects cross domain boundaries in ways the source labels don't show.

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
