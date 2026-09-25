---
tags: [concept, domain/training-at-scale, level/frontier]
aliases: [data-constrained scaling, Muennighoff scaling laws, repeated-data scaling]
summary: "How pretraining loss scales when unique data runs low, and how compute should shift between repeats, params, and synthetic data."
---

# Concept - Data-Constrained Scaling Laws

> **One-paragraph hook:** [[Concept - Scaling Laws|Chinchilla]] assumes you can always get more *unique* tokens for a fixed compute budget. Frontier runs training on 15T+ tokens are running out of clean, unique, high-quality web text. Data-constrained scaling laws answer the question that follows: if you must repeat a fixed pool of $D_C$ unique tokens to reach your target token count, what is each repeated pass worth, and where should the *rest* of your compute go?

## The mechanism

Start from the Chinchilla loss model $L(N,D) = E + A/N^\alpha + B/D^\beta$, which implicitly assumes all $D$ training tokens are unique. Muennighoff et al. 2023 ("Scaling Data-Constrained Language Models") ask what happens when a corpus of only $D_C$ unique tokens is repeated $R_D = D/D_C$ times to reach the target budget $D$. Across hundreds of runs varying $(N, D_C, R_D)$, they find each extra epoch over the same data is worth strictly less than a fresh epoch of new data, and the marginal value **decays as repetition count grows** instead of holding constant. The naive Chinchilla law treats every token as equally informative, so it systematically overstates what a repeated corpus is worth.

Their fix replaces the raw token count $D$ in the loss law with an **effective data** term $D_{\text{eff}} = D_C \cdot U(R_D)$. $U$ is a monotonically increasing, saturating function of repetition count, fit empirically from the sweep. Doubling the repeats does *not* double the effective data, and past a threshold more repeats contribute almost nothing. The numbers from their fit that matter in practice:

| Repetition regime | Marginal value of an extra epoch |
|---|---|
| Up to ~4 epochs | Nearly as valuable as fresh unique data |
| ~4-16 epochs | Decaying fast, meaningfully less than fresh data |
| Beyond ~16 epochs | Near-worthless — extra repeats barely move the loss |

The same logic extends to parameters. Once you're data-constrained, adding parameters $N$ against a fixed, repeated $D_C$ also has diminishing returns, but the *relative* return on parameters degrades more slowly than the return on repeats. That's the basis for their headline guidance: **once you're in the data-constrained regime, extra compute is better spent on parameters than on more repeats past the ~4-epoch mark.**

## In practice

Chinchilla's ~20 tokens/param compute-optimal ratio assumes an infinite unique-data pool. A run at [[Deep Dive - Anatomy of a Pretraining Run|15T+ tokens]] (Llama-3's regime) is already well past what high-quality web text alone can supply in unique tokens without heavy filtering losses. Hence frontier labs increasingly report training on a mix of repeated high-quality subsets and freshly generated data.

Under a fixed data budget, the law suggests reaching for these levers in order:
1. **Repeat the existing corpus up to ~4 epochs.** Nearly free, per the value curve above.
2. **Blend in [[Concept - Synthetic Training Data]] and code/other domains** ([[Concept - Data Mixtures]]) to extend the unique-token pool instead of repeating.
3. **Put additional compute into more parameters** once past the ~4-epoch mark, since parameter scaling degrades more gracefully than repeat scaling in the data-constrained regime.
4. **Up-weight the scarcest high-quality data during the LR-decay/annealing phase** of a run, so the highest-value repeats land where they help most.

## Failure modes

- **Over-repeating drives memorization and contamination risk.** Once repeats stop adding generalizable signal, the model increasingly memorizes the repeated text verbatim. That raises the odds that [[Concept - Benchmark Contamination|benchmark-adjacent]] passages get memorized instead of the underlying pattern being learned.
- **Conflating tokens-seen with unique-tokens-seen.** A run "trained on 15T tokens" can have a much smaller effective unique-token count if much of the budget is repeats. Sizing decisions and reported comparisons need the unique count.
- **Repetition compounds badly with weak [[Concept - Deduplication at Scale|deduplication]].** If near-duplicates already inflate a corpus's effective repetition count before you deliberately repeat it, the true $R_D$ is higher than the nominal one and the value decay above kicks in earlier than expected.

## The non-obvious

This law explains why the field pivoted hard toward synthetic data generation and aggressive deduplication instead of just scaling web-crawl volume further. At the frontier, the limit is increasingly the supply of unique, non-degenerate tokens, not compute (see [[Concept - The Data Wall]]). A subtler trap: teams that don't track deduplicated unique-token counts can mistake a data-repetition ceiling for an optimizer or architecture problem. The symptom, diminishing loss improvement per additional GPU-hour, looks identical to an ordinary training plateau unless you've computed $R_D$ for your corpus.

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
