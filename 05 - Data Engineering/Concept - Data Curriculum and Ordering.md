---
tags: [concept, domain/data-engineering, level/frontier]
aliases: [curriculum learning, data ordering, annealing, cooldown]
summary: "Whether the order and repetition schedule of pretraining tokens - not just the mixture - measurably changes convergence and final quality."
---

> **One-paragraph hook:** [[Concept - Data Mixtures]] answers *what proportion* of each domain a model sees. Curriculum and ordering asks *in what sequence* and *how many times*. Almost every large run does the default: one global i.i.d. shuffle over one epoch. Two deviations from it matter in production pipelines: end-of-run quality annealing, and controlled multi-epoch repetition. Anything fancier (easy-to-hard curricula, domain-phased training) has weaker evidence that doesn't hold up well across scale.

## The mechanism

The null hypothesis is that order shouldn't matter. SGD over a fixed dataset converges to roughly the same place whatever the presentation order, as long as sampling is unbiased. So nearly every large pretraining run defaults to a **global seeded shuffle**: mix every domain together, shuffle once across the whole token pool, stream it. Simple, reproducible, hard to get wrong.

Curriculum learning claims you can beat that by controlling *when* the model sees what: easy examples before hard, short sequences before long, abundant low-quality data before scarce high-quality data. The intuition comes from human pedagogy and smaller-scale supervised learning. At LLM pretraining scale the evidence is mixed and mostly from small ablations (sub-billion to low-billion parameters). Gains that show up at 1B parameters frequently vanish or reverse at 70B, so most frontier labs treat curriculum as unproven and keep shuffling.

One curriculum effect **does** replicate robustly: **quality annealing**, also called **cooldown**. In the final ~10–20% of training tokens, while the learning-rate schedule decays toward its minimum, labs upweight the highest-quality, synthetic, code and math data. It's a second mixture layered on top of the base mixture used for the bulk of training. MiniCPM, OLMo, Llama-3's published training recipe and DeepSeek's pipeline all report it. The mechanism is plausible: late in training, with a small learning rate, each gradient step makes a small, precise update, and spending those updates on the cleanest signal available gives a better final checkpoint than spending them on average web text.

The second robust effect is **multi-epoch repetition**. Muennighoff et al. (2023, "Scaling Data-Constrained Language Models") measured what happens when you're token-constrained and have to repeat data instead of acquiring more. Up to roughly **4 epochs** of repeated data perform nearly as well as fresh unique tokens at the same total count. Returns decay steadily after that, and by roughly **16+ epochs** more repetition adds essentially nothing over stopping training earlier. So "how many times can I see this document" becomes a deliberate curriculum decision, not an accident of where the token budget happened to land.

## In practice

Repetition value depends on [[Concept - Deduplication at Scale]]. Tolerating up to ~4 epochs only makes sense if the data you're repeating is *clean and deduplicated*. Repeating junk burns the budget faster, because duplicate-heavy corpora already over-represent low-information text before you multiply it.

A practical annealing recipe: train the bulk of the run on the base [[Concept - Data Mixtures]] with a standard LR schedule. In the final phase, swap in a mixture upweighted toward instruction-adjacent, code, math and synthetic tokens ([[Concept - Synthetic Training Data]]) while the LR decays to its floor. This is now a fairly standard part of frontier recipes, no longer a research curiosity.

Domain phasing (broad web data first, specialized domains later) is related but risky in a base model still under active pretraining. Late-stage narrow data can erase capabilities the model built earlier. It's the same mechanism as [[Concept - Catastrophic Forgetting]] during fine-tuning, just inside a single pretraining run instead of across a train/fine-tune boundary.

## Failure modes

The most common failure is treating a small-ablation curriculum result as production-ready. An ordering strategy validated on a 1B-parameter, tens-of-billions-of-tokens run has no guarantee of transferring to a 70B-parameter, multi-trillion-token run. [[Concept - Learned Data Mixing (DoReMi and Mixing Laws)]] has the same transfer problem.

Second: over-aggressive domain phasing that erases earlier capabilities through catastrophic forgetting, which shows up as regressions on things the model appeared to have mid-run.

Third: repeating data past the point of value, pushing into the 16+ epoch range on the (false) assumption that more passes always help. [[Deep Dive - Anatomy of a Pretraining Run]] would show the loss curve flattening while wall-clock cost keeps climbing.

Detection is the same for all three. Track downstream eval curves at several checkpoints during training, not only at the end, and compare against a shuffled-baseline run whenever budget allows.

## The non-obvious

There's no scaling-law-grade theory of optimal data ordering. Token-budget scaling ([[Concept - Scaling Laws]]) and even mixture optimization have predictive functional forms; ordering research hasn't converged on one. Annealing and bounded repetition are adopted as *empirically validated heuristics*, not derived results. My takeaway: a curriculum claim that looks clean in a small-scale paper is a hypothesis to ablate at your target scale, not a recipe to import. [[Gotchas - Pretraining Data Pipelines]] applies the same caution to filtering thresholds.

## Connections
- [[Concept - Data Mixtures]] — mixtures set the *what*; curriculum and ordering set the *when* and *how many times* on top of that mixture.
- [[Concept - Learned Data Mixing (DoReMi and Mixing Laws)]] — shares the same scale-transfer failure mode: small-proxy results don't reliably predict large-run behavior.
- [[Concept - Scaling Laws]] — the token-budget backdrop that repetition and annealing decisions are made against.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where annealing/cooldown phases and epoch-repetition budgets actually get scheduled inside a real run.
- [[Concept - Deduplication at Scale]] — repetition is only cheap on deduplicated data; repeating a dirty corpus compounds its duplication problem.
- [[Concept - Synthetic Training Data]] — one of the standard ingredients upweighted during the annealing/cooldown phase.
- [[Concept - Catastrophic Forgetting]] — the mechanism by which late-stage domain phasing can erase earlier-learned capabilities.
- [[Gotchas - Pretraining Data Pipelines]] — the aggregated pitfalls, including data-order-linked loss spikes, that ordering decisions can trigger.
- [[Concept - Learning Rate Schedules for Pretraining]] — annealing/cooldown is defined jointly with the LR decay schedule, not independently of it.

## Sources
- Muennighoff et al. (2023) — Scaling Data-Constrained Language Models. Established the ~4-epoch near-parity and ~16+-epoch diminishing-returns findings for repeated pretraining data.
