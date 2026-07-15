---
tags: [concept, domain/data-engineering, level/frontier]
aliases: [curriculum learning, data ordering, annealing, cooldown]
summary: "Whether the order and repetition schedule of pretraining tokens - not just the mixture - measurably changes convergence and final quality."
---

> **One-paragraph hook:** [[Concept - Data Mixtures]] answers *what proportion* of each domain a model sees; curriculum and ordering asks *in what sequence* and *how many times*. The default answer — a single global i.i.d. shuffle over one epoch — is what almost every large run actually does, but two real deviations from that default are load-bearing in production pipelines: end-of-run quality annealing, and controlled multi-epoch repetition. Everything fancier (easy-to-hard curricula, domain-phased training) has weaker, scale-fragile evidence.

## The mechanism

The null hypothesis is that order shouldn't matter: stochastic gradient descent over a fixed dataset converges to roughly the same place regardless of presentation order, as long as the sampling is unbiased. This is why the default in nearly every large pretraining run is a **global seeded shuffle** — mix every domain together, shuffle once across the whole token pool, and stream it. It's simple, reproducible, and hard to get wrong.

Curriculum learning claims you can beat that default by controlling *when* the model sees what: easy examples before hard ones, short sequences before long, low-quality-but-abundant data before high-quality-but-scarce data. The intuition borrows from human pedagogy and from smaller-scale supervised-learning results. At LLM pretraining scale the evidence is mixed and mostly comes from small ablations (sub-billion to low-billion parameter models); gains that show up at 1B parameters frequently vanish or reverse at 70B, so most frontier labs treat curriculum as unproven and keep shuffling.

One curriculum effect **does** replicate robustly: **quality annealing**, also called **cooldown**. During the final ~10–20% of training tokens, as the learning-rate schedule decays toward its minimum, labs upweight the highest-quality, synthetic, code, and math data in the mix — a distinct, second mixture layered on top of the base mixture used for the bulk of training. This has been reported across MiniCPM, OLMo, Llama-3's published training recipe, and DeepSeek's pipeline. The mechanism is plausible: late in training, with a small learning rate, gradient steps make small, precise updates to the loss landscape, and spending those precise updates on the cleanest signal available yields a better final checkpoint than spending them on average-quality web text.

The second robust effect is **multi-epoch repetition**. Muennighoff et al. (2023, "Scaling Data-Constrained Language Models") measured what happens when you're token-constrained and must repeat data rather than acquire more: up to roughly **4 epochs** of repeated data perform nearly as well as fresh unique tokens at the same total count; returns decay steadily beyond that, and by roughly **16+ epochs** additional repetition adds essentially nothing over just stopping training earlier. This turns "how many times can I see this document" into a first-class curriculum decision, not an accident of how the token budget happened to land.

## In practice

Repetition value is coupled to [[Concept - Deduplication at Scale]]: the entire point of tolerating up to ~4 epochs is that you're repeating *clean, deduplicated* data — repeating junk just wastes the budget faster, since duplicate-heavy corpora already over-represent low-information text before you multiply it further. A practical annealing recipe looks like: train the bulk of the run on the base [[Concept - Data Mixtures]] with a standard LR schedule, then in the final phase swap in a mixture upweighted toward instruction-adjacent, code, math, and synthetic tokens ([[Concept - Synthetic Training Data]]) while the LR decays to its floor — this is now a fairly standard component of frontier recipes rather than a research curiosity.

Domain phasing — front-loading broad web data and shifting to specialized domains later — is a related idea but interacts dangerously with catastrophic forgetting in a base model still under active pretraining: late-stage narrow data can quietly erase capabilities the model built earlier in training, the same mechanism that shows up as [[Concept - Catastrophic Forgetting]] during fine-tuning, just inside a single pretraining run instead of across a train/fine-tune boundary.

## Failure modes

The most common failure is treating curriculum results from a small ablation as production-ready: an ordering strategy validated on a 1B-parameter, tens-of-billions-of-tokens run has no guarantee of transferring to a 70B-parameter, multi-trillion-token run — the same transfer problem that plagues [[Concept - Learned Data Mixing (DoReMi and Mixing Laws)]]. A second failure is over-aggressive domain phasing that erases earlier-learned capabilities via catastrophic forgetting, showing up as regressions on capabilities the model appeared to have mid-run. A third is repeating data past the point of value — pushing epochs into the 16+ range on the (false) assumption that more passes always help, when [[Deep Dive - Anatomy of a Pretraining Run]] would show the loss curve flattening while wall-clock cost keeps climbing. Detection for all three is the same: track downstream eval curves at multiple checkpoints during training, not just at the end, and compare against a shuffled-baseline run whenever budget allows.

## The non-obvious

There is no scaling-law-grade theory of optimal data ordering — unlike token-budget scaling ([[Concept - Scaling Laws]]) or even mixture optimization, ordering research hasn't converged on a predictive functional form, which is why annealing and bounded repetition are adopted as *empirically validated heuristics* rather than derived results. The practitioner lesson: curriculum claims that look clean in a paper at small scale should be treated as a hypothesis to ablate at your target scale, not a recipe to import directly — the same caution [[Gotchas - Pretraining Data Pipelines]] applies to filtering thresholds applies here to ordering schedules.

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
