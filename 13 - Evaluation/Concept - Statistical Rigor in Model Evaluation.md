---
tags: [concept, domain/evaluation, level/advanced]
aliases: [confidence intervals for evals, paired significance testing, eval statistics]
summary: "Treat a benchmark score as a random variable with a confidence interval, not a fixed fact — most reported model-vs-model gaps are inside the noise."
---

> **One-paragraph hook:** A benchmark accuracy is a sample statistic. It was measured on a finite set of items, with a finite number of decoding seeds, under one prompt template, and each of those adds variance. The most common statistical sin in the field is reporting a bare percentage, declaring that model A beats model B on a fraction-of-a-point gap, and never asking whether the gap is distinguishable from noise.

## The mechanism

**Confidence intervals for a proportion.** Accuracy on $n$ items with observed accuracy $\hat p$ is a binomial proportion. The naive Wald interval $\hat p \pm 1.96\sqrt{\hat p(1-\hat p)/n}$ is known to under-cover near $p=0$, $p=1$, and at moderate $n$, so use the Wilson score interval or the exact Clopper-Pearson interval. As a rule of thumb, the width of a 95% CI around $p=0.5$ on $n$ items is about

$$1.96\sqrt{\frac{p(1-p)}{n}} \approx \frac{1}{\sqrt{n}}$$

At $n=1000$ that's roughly $\pm 3.1$ points. A "58% vs 55%" headline on a 1000-item benchmark is often not distinguishable from noise once you draw the interval.

**Small benchmarks have brutal arithmetic.** GPQA-Diamond has on the order of 198 items. AIME has roughly 30 problems per year. On a 30-item benchmark one question is worth 3.3 percentage points, so most AIME deltas in launch blog posts are smaller than a single flipped answer. They aren't statistically meaningful without a much larger item pool or aggregation across many AIME years.

**Paired testing is the free lunch people skip.** When both models answer the *same* items, their per-item correctness is correlated. Comparing two independent marginal confidence intervals throws that correlation away. Two overlapping marginal CIs do **not** imply a non-significant difference: the paired difference can be significant even when the marginals overlap widely. The right tools use the pairing directly. McNemar's test works on the $2\times2$ table of discordant pairs (items where one model got it right and the other didn't),

$$\chi^2 = \frac{(b-c)^2}{b+c}$$

where $b$ and $c$ count "A right, B wrong" and "A wrong, B right." The paired bootstrap ([[Snippet - Paired Bootstrap for Model Comparison]]) resamples item indices with replacement and recomputes the accuracy *difference* each time, building an empirical distribution of the delta. Permutation tests randomly relabel which model "owns" each item's score under the null of no difference. All three have far more power than an unpaired two-sample test on the same data, because they cancel the shared item-level variance instead of adding it to both arms.

**Variance beyond sampling noise.** Item sampling is only one source. Prompt template wording, few-shot exemplar choice and ordering ([[Concept - Prompt Format Sensitivity in Evaluation]]), decoding seed and, when an [[Concept - LLM-as-Judge]] is involved, the judge model itself all add variance a naive binomial CI never captures. Miller's 2024 "Adding Error Bars to Evals" argues for reporting variance across seeds and formats as well as items, because a model 2 points ahead under one prompt template can be 2 points behind under a semantically equivalent one.

**Multiple comparisons.** An $N$-model leaderboard is $N$ simultaneous hypothesis tests against whichever model is on top. Run that many comparisons uncorrected and some model is guaranteed to "win" by chance, even if all are identical in true capability. Bonferroni (divide the significance threshold by the number of comparisons) or a false-discovery-rate procedure (Benjamini-Hochberg) is the minimum before crowning a winner.

**Non-independence within a benchmark.** MMLU is 57 subjects with wildly uneven item counts and within-subject correlation ([[Breakdown - MMLU]]), and many benchmarks group several questions under a shared passage or document. Treating each item as an i.i.d. Bernoulli draw when items cluster breaks the independence assumption behind the simple binomial CI and understates the true variance. The fix is a hierarchical or cluster bootstrap that resamples subjects or documents instead of items.

## In practice

A defensible number comes from this workflow: (1) report $n$ and the exact scoring method with every accuracy figure; (2) compute a Wilson or Clopper-Pearson CI, not Wald; (3) when comparing two models on the same items, use a paired test (McNemar or paired bootstrap), never two independent CIs; (4) with more than two models, apply a multiple-comparison correction before naming a winner; (5) if the benchmark clusters (subjects, documents, templates), resample in a cluster-aware way; (6) if other variance sources are in play (prompt format, seed, judge model), report a range across them instead of a point estimate. [[Reference - LLM Benchmark Landscape]] and [[Checklist - Trusting a Benchmark Number]] turn a version of this into a checklist for reading other people's numbers as well as producing your own.

## Failure modes

- **Bare accuracy, no CI, no n.** A leaderboard cell with one decimal number and no interval is unfalsifiable. You can't tell whether the ranking is real.
- **Comparing marginal CIs instead of pairing.** Concluding "not significant" because two independent CIs overlap, when a paired test on the same items would show a real difference. This error is common enough to check for by default.
- **AIME/GPQA-Diamond-sized deltas treated as meaningful.** A 2-point gap on a 30-item benchmark is one flipped answer. Report it that way, or aggregate across years or repeats before trusting it.
- **Leaderboard hillclimbing under multiple comparisons.** Submitting variants until one clears the top score, without correcting for the number of attempts, is p-hacking under another name. [[Concept - Goodhart's Law in Model Evaluation]] covers the wider dynamic.
- **Ignoring format/seed variance.** Publishing one run's number as the model's fixed property, when a different prompt template or seed would move it several points ([[Concept - Prompt Format Sensitivity in Evaluation]]).

## The non-obvious

Pairing is the highest-value fix in this area because it costs nothing: no new data, only correct use of what you have. Two models on the same 1000-item benchmark can have marginal 95% CIs that overlap by several points while the *paired* difference is significant at p < 0.01. The marginals hide that both models are right or wrong on the *same* items in a highly correlated way, so the true comparison has far less noise than either marginal suggests. Most public comparisons skip this. They compute two independent-looking CIs and eyeball the overlap, which is the weaker test and gives systematically less powerful (sometimes wrong-signed) conclusions about which model is better.

## Connections
- [[Snippet - Paired Bootstrap for Model Comparison]] — the runnable implementation of the paired-testing machinery described here.
- [[Reference - LLM Benchmark Landscape]] — applies this note's CI and sample-size reasoning across the actual major benchmarks (AIME's tiny n, MMLU's clustering).
- [[Concept - Human Evaluation Methodology]] — inter-annotator agreement and study-power questions in human eval are the same statistical-rigor discipline applied to a different data-generating process.
- [[Concept - Entropy and Cross-Entropy]] — the loss/likelihood quantities underlying log-likelihood scoring methods this note's CIs are often computed over.
- [[Checklist - Trusting a Benchmark Number]] — operationalizes this note's principles as a pre-flight check for consuming a published score.
- [[Concept - KL Divergence]] — the same information-theoretic toolbox (Foundations domain) that underlies calibration and distributional-shift diagnostics referenced when judge or template variance is suspected.
- [[Concept - Hypothesis Testing and p-values]] — the foundational significance-testing framework (Foundations domain) this note specializes to the paired, benchmark-comparison setting.
- [[Concept - Meta-Evaluation of LLM Judges]] — validating a judge's agreement with humans is itself a statistical-rigor problem: correlation coefficients and agreement rates need the same CI discipline.
- [[Concept - Conformal Prediction]] — a Classical ML technique (domain 17) for distribution-free prediction intervals, the natural extension of this note's CI reasoning beyond simple binomial proportions.

## Sources
- Miller, E. (2024) — "Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations." Argues for reporting variance across seeds/prompts, not just item-sampling CIs.
- Wilson, E. B. (1927) — "Probable Inference, the Law of Succession, and Statistical Inference." Source of the Wilson score interval, the standard correction to the Wald interval for binomial proportions.
- McNemar, Q. (1947) — "Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages." The closed-form paired significance test for binary same-item comparisons.
- Dror, R. et al. (2018) — "The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing." Surveys paired bootstrap and permutation testing for NLP model comparison.
