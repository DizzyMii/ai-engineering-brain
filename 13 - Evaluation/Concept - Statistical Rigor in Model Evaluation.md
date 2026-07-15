---
tags: [concept, domain/evaluation, level/advanced]
aliases: [confidence intervals for evals, paired significance testing, eval statistics]
summary: "Treat a benchmark score as a random variable with a confidence interval, not a fixed fact — most reported model-vs-model gaps are inside the noise."
---

> **One-paragraph hook:** A benchmark accuracy is a sample statistic, not a Platonic property of the model — it was measured on a finite set of items, with a finite number of decoding seeds, under one prompt template, and every one of those is a source of variance. The single most common statistical sin in the field is reporting a bare percentage, declaring model A beats model B on a fraction-of-a-point gap, and never asking whether that gap is distinguishable from noise.

## The mechanism

**Confidence intervals for a proportion.** Benchmark accuracy on $n$ items with observed accuracy $\hat p$ is a binomial proportion, and the naive Wald interval $\hat p \pm 1.96\sqrt{\hat p(1-\hat p)/n}$ is known to under-cover near $p=0$, $p=1$, and at moderate $n$ — practitioners should use the Wilson score interval or the exact Clopper-Pearson interval instead. As a rule of thumb, the width of a 95% CI around $p=0.5$ on $n$ items is about

$$1.96\sqrt{\frac{p(1-p)}{n}} \approx \frac{1}{\sqrt{n}}$$

which at $n=1000$ is roughly $\pm 3.1$ points. That means a "58% vs 55%" headline result on a 1000-item benchmark is often not distinguishable from noise once you draw the interval.

**Small benchmarks have brutal arithmetic.** GPQA-Diamond has on the order of 198 items; AIME has roughly 30 problems per year. On a 30-item benchmark, a single question is worth 3.3 percentage points — meaning most AIME score deltas reported between models in launch blog posts are smaller than what one flipped answer would produce, and are not statistically meaningful without a much larger item pool or aggregation across many AIME years.

**Paired testing is the free lunch practitioners skip.** When both models answer the *same* items, their per-item correctness is correlated, and comparing two independent marginal confidence intervals throws that correlation away — two overlapping marginal CIs do **not** imply the difference between them is non-significant, because the paired difference can still be significant even when both marginals overlap widely. The right tools exploit the pairing directly: McNemar's test operates on the $2\times2$ table of discordant pairs (items where exactly one model got it right),

$$\chi^2 = \frac{(b-c)^2}{b+c}$$

where $b$ and $c$ are the counts of "A right, B wrong" and "A wrong, B right" respectively; the paired bootstrap (see [[Snippet - Paired Bootstrap for Model Comparison]]) resamples item indices with replacement and recomputes the accuracy *difference* each time, building an empirical distribution of the delta directly; and permutation tests randomly relabel which model "owns" each item's score under the null of no difference. All three have dramatically more statistical power than an unpaired two-sample test on the same data, because they cancel the shared, item-level variance instead of adding it to both arms.

**Variance beyond sampling noise.** Item-sampling variance is only one source of noise. Prompt template wording, few-shot exemplar choice and ordering (see [[Concept - Prompt Format Sensitivity in Evaluation]]), decoding seed, and — when an [[Concept - LLM-as-Judge]] is involved — the judge model itself, all inject additional variance that a naive binomial CI never captures. Miller's 2024 "Adding Error Bars to Evals" argues for reporting variance across seeds and formats, not just across items, because a model that looks 2 points ahead under one prompt template can look 2 points behind under a semantically-equivalent one.

**Multiple comparisons.** An $N$-model leaderboard is $N$ simultaneous hypothesis tests against whichever model currently sits on top, and running that many comparisons without correction guarantees some model "wins" by chance alone even if all models are identical in true capability. Bonferroni correction (divide your significance threshold by the number of comparisons) or a false-discovery-rate procedure (Benjamini-Hochberg) is the minimum discipline before crowning a leaderboard winner.

**Non-independence within a benchmark.** MMLU is 57 subjects with wildly uneven item counts and within-subject correlation (see [[Breakdown - MMLU]]); many benchmarks group multiple questions under a shared passage or document. Treating every item as an i.i.d. Bernoulli draw when items cluster by subject or document violates the independence assumption behind the simple binomial CI and understates the true variance — a hierarchical or cluster bootstrap (resample at the subject/document level, not the item level) is the correct fix.

## In practice

The workflow that actually produces a defensible number: (1) report $n$ and the exact scoring method alongside every accuracy figure; (2) compute a Wilson or Clopper-Pearson CI, not Wald; (3) if comparing two models on the same item set, use a paired test (McNemar or paired bootstrap), never two independent CIs; (4) if the comparison spans more than two models, apply a multiple-comparison correction before naming a winner; (5) if the benchmark has known clustering (subjects, documents, templates), use a cluster-aware resampling scheme; (6) if variance sources beyond item sampling are in play (prompt format, seed, judge model), report a range across those axes, not a single point estimate. [[Reference - LLM Benchmark Landscape]] and [[Checklist - Trusting a Benchmark Number]] operationalize a version of this checklist for consuming other people's numbers, not just producing your own.

## Failure modes

- **Bare accuracy, no CI, no n.** A leaderboard cell with a single decimal number and no interval is unfalsifiable — you cannot tell if the ranking is real.
- **Comparing marginal CIs instead of pairing.** Concluding "not significant" because two independent CIs overlap, when a paired test on the same items would show the difference is real — this specific error is common enough that it deserves to be checked by default.
- **AIME/GPQA-Diamond-sized deltas treated as meaningful.** A 2-point gap on a 30-item benchmark is one flipped answer; report it as such or aggregate across years/repeats before trusting it.
- **Leaderboard hillclimbing under multiple comparisons.** Repeatedly submitting variants until one clears the current top score, without correcting for the number of attempts, is p-hacking with a different name — see [[Concept - Goodhart's Law in Model Evaluation]] for the broader dynamic this feeds.
- **Ignoring format/seed variance.** Publishing a single run's number as if it were the model's fixed property, when re-running with a different prompt template or seed would move it several points (see [[Concept - Prompt Format Sensitivity in Evaluation]]).

## The non-obvious

The paired-vs-unpaired distinction is the highest-leverage fix in this whole area because it's free — it requires no new data, only using the data you already have correctly. Two models evaluated on the same 1000-item benchmark generate two accuracy numbers whose marginal 95% CIs can easily overlap by several points while the *paired* difference between them is significant at p < 0.01, because the overlap in the marginals hides the fact that both models are right or wrong on the *same* items in a highly correlated way — the true comparison has far less noise than either marginal alone suggests. Most public model comparisons never exploit this, computing two independent-looking CIs and eyeballing overlap, which is the statistically weaker test available and produces systematically less powerful (and sometimes wrong-signed) conclusions about which model is actually better.

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
