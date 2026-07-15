---
tags: [concept, domain/training-at-scale, level/frontier]
aliases: [data-constrained scaling, Muennighoff scaling laws, repeated-data scaling]
summary: "How pretraining loss scales when unique data runs low, and how compute should shift between repeats, params, and synthetic data."
---

# Concept - Data-Constrained Scaling Laws

> **One-paragraph hook:** [[Concept - Scaling Laws|Chinchilla]] assumes you can always get more *unique* tokens for a fixed compute budget — but frontier runs training on 15T+ tokens are running out of clean, unique, high-quality web text. Data-constrained scaling laws answer the practical question this creates: if you have to repeat a fixed pool of $D_C$ unique tokens to hit your target token count, how much is each repeated pass actually worth, and where should the *rest* of your compute go instead?

## The mechanism

Start from the Chinchilla loss model $L(N,D) = E + A/N^\alpha + B/D^\beta$, which implicitly assumes every one of the $D$ tokens seen during training is unique. Muennighoff et al. 2023 ("Scaling Data-Constrained Language Models") ask what happens when a corpus of only $D_C$ unique tokens is repeated $R_D = D/D_C$ times to reach the target token budget $D$. Empirically, training hundreds of runs across varying $(N, D_C, R_D)$, they find each additional epoch over the same data is worth strictly less than a fresh epoch of new data, with the marginal value **decaying as repetition count grows** rather than staying constant — so the naive Chinchilla law, which treats every token as equally informative, systematically overstates the value of a repeated corpus.

They formalize this by replacing the raw token count $D$ in the loss law with an **effective data** term $D_{\text{eff}} = D_C \cdot U(R_D)$, where $U$ is a monotonically increasing but saturating function of the repetition count fit empirically from the sweep — doubling the number of repeats does *not* double the effective data the model benefits from, and past a threshold, additional repeats contribute almost nothing. The practically load-bearing numbers from their fit:

| Repetition regime | Marginal value of an extra epoch |
|---|---|
| Up to ~4 epochs | Nearly as valuable as fresh unique data |
| ~4-16 epochs | Decaying fast, meaningfully less than fresh data |
| Beyond ~16 epochs | Near-worthless — extra repeats barely move the loss |

They extend the same logic to parameters: once you're data-constrained, throwing more parameters $N$ at a fixed, repeated $D_C$ also has diminishing returns, but the *relative* return on more parameters degrades more slowly than the return on more repeats — which is the mechanistic basis for their headline practical guidance: **once you're in the data-constrained regime, extra compute is better spent on parameters than on more repeats past the ~4-epoch mark.**

## In practice

Chinchilla's ~20 tokens/param compute-optimal ratio assumes an infinite unique-data pool; a run at [[Deep Dive - Anatomy of a Pretraining Run|15T+ tokens]] (Llama-3's regime) is already deep into territory where high-quality web text alone can't supply that many unique tokens without heavy filtering losses, which is why frontier labs increasingly report training on a mix of repeated high-quality subsets and freshly generated data.

The practical levers under a fixed data budget, in the order this law recommends reaching for them:
1. **Repeat the existing corpus up to ~4 epochs** — nearly free, per the value curve above.
2. **Blend in [[Concept - Synthetic Training Data]] and code/other domains** ([[Concept - Data Mixtures]]) to genuinely extend the unique-token pool rather than repeating.
3. **Shift additional compute toward more parameters** rather than more repeats once past the ~4-epoch mark, since parameter scaling degrades more gracefully than repeat scaling in the data-constrained regime.
4. **Up-weight the scarcest high-quality data specifically during the LR-decay/annealing phase** of a run, concentrating the highest-value repeats where they move the needle most.

## Failure modes

- **Over-repeating drives memorization and contamination risk.** Past the point where repeats stop adding generalizable signal, the model increasingly just memorizes the repeated text verbatim, raising the odds that [[Concept - Benchmark Contamination|benchmark-adjacent]] passages get memorized rather than the underlying pattern learned.
- **Conflating tokens-seen with unique-tokens-seen.** A run boasting "trained on 15T tokens" can have a much smaller effective unique-token count if a large fraction of the budget is repeats — sizing decisions and reported comparisons need the unique count, not the raw token-seen count.
- **Repetition compounds badly with weak [[Concept - Deduplication at Scale|deduplication]].** If near-duplicate documents already inflate a corpus's effective repetition count before you deliberately repeat it, the true $R_D$ is higher than the nominal one, and the value-decay curve above kicks in earlier than expected.

## The non-obvious

This law is the mechanistic reason the field pivoted hard toward synthetic data generation and aggressive deduplication rather than just scaling up web-crawl volume further — the constraint that's actually binding at the frontier increasingly isn't compute, it's the supply of unique, non-degenerate tokens (see [[Concept - The Data Wall]]). A subtler trap: teams that don't track de-duplicated unique-token counts can misdiagnose a data-repetition ceiling as an optimizer or architecture problem, because the symptom — diminishing loss improvement per additional GPU-hour — looks identical to an ordinary training plateau unless you've explicitly computed $R_D$ for your corpus.

## Connections
- [[Concept - Scaling Laws]] — the compute-optimal law this note extends into the regime where $D$ is capped by unique-data availability rather than compute.
- [[Concept - Data Mixtures]] — the domain-mix decisions that determine how much genuinely unique high-quality data is available before repetition becomes necessary.
- [[Concept - Deduplication at Scale]] — weak dedup silently inflates the effective repetition count, pulling a corpus into the fast-decay regime earlier than its nominal repeat count suggests.
- [[Concept - Synthetic Training Data]] — the primary lever for extending the effective unique-data pool beyond what repetition alone can buy.
- [[Concept - Benchmark Contamination]] — over-repeating training data raises the odds that benchmark-adjacent text gets memorized rather than generalized from.
- [[Deep Dive - Anatomy of a Pretraining Run]] — data-constraint math is one of the direct inputs to a real run's compute-budget sizing decision.
- [[Concept - The Data Wall]] — the trajectory-level framing of the same supply constraint this note derives the loss-function consequences of.
- [[Lore - Books3 and the Shadow Library Reckoning]] — a real-world consequence of labs running low on legitimately available unique text, driving them toward contested data sources.

## Sources
- Muennighoff et al. (2023) — "Scaling Data-Constrained Language Models" — derives the effective-data-with-decay extension to the Chinchilla law and the empirical epoch-value curve.
- Hoffmann et al. (2022) — "Training Compute-Optimal Large Language Models" — the Chinchilla law this note extends into the data-limited regime.
