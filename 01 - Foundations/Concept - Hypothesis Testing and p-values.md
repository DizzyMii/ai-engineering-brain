---
tags: [concept, domain/foundations, level/core]
aliases: [NHST, null-hypothesis significance testing, significance testing, p-value]
summary: "How to tell if an observed difference is real or noise, and the exact ways p-values get misread in eval and A/B work."
---

# Concept - Hypothesis Testing and p-values

> **One-paragraph hook:** Every "model B beats model A" claim in an eval report rests on hypothesis testing, and a large fraction of those claims are backed by a badly misread number. A p-value tells you how surprising your data would be *if there were no real difference* — nothing about whether the difference exists, how large it is, or whether it will replicate. Get this wrong at scale and you ship a "win" that was noise, or worse, kill a real improvement because an underpowered eval couldn't see it.

## The mechanism

Null-hypothesis significance testing (NHST) starts from a null hypothesis $H_0$ (e.g. "model A and model B have identical accuracy on the population these prompts are drawn from") and a test statistic $T$ computed from the observed data. Under $H_0$, $T$ has a known or simulable distribution. The p-value is:

$$p = P(T \text{ at least as extreme as observed} \mid H_0 \text{ true})$$

This is a tail probability computed under an assumption you are trying to falsify — it is **not** $P(H_0 \mid \text{data})$, which would require a prior and belongs to Bayesian inference, a different framework entirely.

Two error types define the rest of the machinery. Type I error ($\alpha$) is rejecting $H_0$ when it's actually true — a false positive, fixed in advance by convention at 0.05. Type II error ($\beta$) is failing to reject $H_0$ when it's false — a miss. Power is $1-\beta$: your probability of detecting a real effect of a given size. Power, $\alpha$, sample size $N$, and effect size $\delta$ trade against each other roughly as:

$$N \sim \frac{(z_\alpha + z_\beta)^2 \, \sigma^2}{\delta^2}$$

Required $N$ scales with variance over *squared* effect size — halving the effect you need to detect quadruples the sample required. This single formula explains why a 300-prompt eval set reliably fails to distinguish two models that differ by half a point of accuracy, no matter how carefully it's built.

A $(1-\alpha)$ confidence interval (CI) is exactly the set of null values you would *fail* to reject at level $\alpha$. Its correct reading is coverage over repeated experiments ("if I ran this procedure many times, 95% of the intervals it produces would contain the true value"), not "there is a 95% probability the true value lies in this specific interval" — the true value is fixed, the interval is the random object.

## In practice

Test choice follows from data structure. When the same items are scored by both systems, **pair them**: a paired t-test or Wilcoxon signed-rank test cancels the item-to-item difficulty variance and is dramatically more powerful than an unpaired test on the identical data, because pairing removes the largest variance component (prompt difficulty) that otherwise swamps a small model-to-model delta. For paired win/loss outcomes, McNemar's test is the direct tool. For an arbitrary or non-normal metric, bootstrap the CI by resampling items with replacement and recomputing the statistic thousands of times. For an exact null under exchangeability, run a permutation test: shuffle the system labels, recompute the statistic, and see where the observed value falls in that empirical null distribution — no distributional assumption required.

Running many comparisons compounds the risk. Testing 20 metrics at $\alpha = 0.05$ expects roughly one spurious "significant" result by chance alone. Bonferroni correction divides $\alpha$ by the number of tests (simple, conservative, controls family-wise error). Benjamini-Hochberg (1995) instead controls the false discovery rate — the expected fraction of false positives among rejections — which is less conservative and the better default when screening many candidate changes (e.g. sweeping ablations). Neither rescues a run from p-hacking: trying metrics, cutoffs, and subgroups until something clears 0.05 (the "garden of forking paths") inflates the true false-positive rate far above the nominal $\alpha$, even when only a single test is ultimately reported.

## Failure modes

The three canonical misreadings of a p-value drive most bad conclusions in practice: it is not the probability the null is true, not the effect size, and not the probability the result replicates. Treating $p = 0.03$ as "97% chance this improvement is real" is a category error that shows up constantly in eval writeups.

A subtler failure is the **winner's curse** (Type M / magnitude error, Gelman & Carlin 2014): under low power, only inflated estimates clear the significance threshold, so a "significant" result from an underpowered run systematically *overestimates* the true effect. This is the mechanism behind the familiar pattern of a fine-tune that "beats baseline by 4 points" on a 200-example eval, then shows a 0.5-point gap (or none) on the full held-out set.

Peeking at results as they accumulate and stopping once significance is hit invalidates the reported p-value, because the effective number of "looks" isn't accounted for by a fixed-$N$ test — sequential monitoring needs alpha-spending or always-valid CIs, not ad hoc early stopping.

## The non-obvious

Statistical significance is not practical significance. With enough $N$, a genuinely trivial 0.03% metric shift becomes $p < 0.001$ — the test is doing exactly what it's built to do (detect that the true mean isn't precisely zero), which is a different question from "does this matter for users." Always report an effect size with a confidence interval alongside the p-value; a lone p-value is close to unactionable. [[Playbook - Running a Statistically Valid Experiment]] operationalizes this discipline end to end, from pre-registration through reporting.

## Connections

- [[Playbook - Running a Statistically Valid Experiment]] — the full procedure (pre-registration, power analysis, test selection, multiplicity correction) that turns this note's theory into a repeatable process.
- [[Concept - Maximum Likelihood Estimation]] — the estimation principle underlying most test statistics and the losses being compared in a model A/B.
- [[Concept - Statistical Rigor in Model Evaluation]] — applies this exact machinery specifically to LLM eval-harness comparisons and leaderboard claims.
- [[Deep Dive - Designing an Eval Harness]] — where paired testing and multiple-comparison correction get built into the harness rather than bolted on after.
- [[Concept - LLM-as-Judge]] — judge scores are noisy measurements that need this same significance discipline before "wins more often" is trustworthy.
- [[Concept - Benchmark Contamination]] — a confound that can invalidate a test's premise (samples no longer independent of training) before the p-value even means anything.
- [[Concept - The Emergent Abilities Debate]] — a case study in how metric choice and underpowered sampling near a threshold can manufacture the appearance of a discontinuous effect.
- [[Concept - Causal Inference Basics]] — a hypothesis test tells you a difference is unlikely to be noise; causal inference is the separate machinery for whether the treatment caused it.

## Sources

- Neyman, J. & Pearson, E. (1933) — *On the Problem of the Most Efficient Tests of Statistical Hypotheses.* Founding paper for the $\alpha$/$\beta$, Type I/Type II framework this note is built on.
- Benjamini, Y. & Hochberg, Y. (1995) — *Controlling the False Discovery Rate.* The FDR procedure now standard for correcting many simultaneous comparisons.
- Gelman, A. & Carlin, J. (2014) — *Beyond Power Calculations: Assessing Type S (Sign) and Type M (Magnitude) Errors.* Source of the winner's-curse / Type M error framing used above.
