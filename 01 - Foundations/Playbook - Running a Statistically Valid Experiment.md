---
tags: [playbook, domain/foundations, level/advanced]
aliases: [experiment design, statistical power analysis, A/B testing statistics, valid model comparison]
summary: "End-to-end procedure for a sound experiment: pre-register, power, pick the right test, don't peek, correct multiplicity, report effect size + CI."
---

# Playbook - Running a Statistically Valid Experiment

> **Goal:** Turn "model B looks better" into a defensible claim with a stated effect size, confidence interval, and false-positive control — not a number you talked yourself into.
> **When to run this:** Any comparison whose outcome will move a decision — an A/B test, a fine-tune vs baseline eval, a kernel that "seems faster," a prompt change you want to ship.
> **Prerequisites:** You can state one primary metric, you can generate independent (or paired) measurements, and you understand what a p-value is and is not — see [[Concept - Hypothesis Testing and p-values]].

The default failure of engineering experiments is not bad math; it is *degrees of freedom*. Every unregistered choice — which metric, which slice, when to stop — is a lottery ticket for a false positive. This playbook removes those tickets in order.

## Steps

**1. Pre-register the hypothesis, primary metric, and decision rule — before touching data.**
Write, in one place: the single primary metric, the direction and minimum effect size that would change your decision (the *minimum detectable effect*, MDE), the test you will run, and the alpha. Freeze it.
→ *Expected:* A one-paragraph analysis plan you could hand to a skeptic.
→ *Deviation:* If you find yourself choosing the metric *after* seeing results, you are in Gelman & Loken's "garden of forking paths" (2013) — every fork silently multiplies your false-positive rate. A pre-registered plan is the single strongest guard against it, and against the broader pathology Ioannidis (2005) named in "Why Most Published Research Findings Are False."

**2. Do a power analysis and size the experiment.**
Estimate the metric's variance $\sigma^2$ (from a pilot or historical runs) and your MDE $\delta$. For comparing two means at power $1-\beta \approx 0.8$, two-sided $\alpha=0.05$:

$$ n \approx \frac{2\,(z_{1-\alpha/2} + z_{1-\beta})^2\,\sigma^2}{\delta^2} = \frac{2\,(1.96 + 0.84)^2\,\sigma^2}{\delta^2} \approx \frac{15.7\,\sigma^2}{\delta^2}\ \text{per arm.}$$

→ *Expected:* A concrete N per arm. Sample size scales as $\sigma^2/\delta^2$ — halving the effect you want to detect quadruples the cost.
→ *Deviation:* If N is infeasible, **do not shrink the experiment — shrink the variance.** Pair or block: score both systems on the *identical* items and test the per-item differences. Pairing cancels item-difficulty variance, which usually dominates, and can cut required N by 10–100×. This is the highest-leverage move in the whole playbook and the one people skip.

**3. Choose the test to match the data structure — not out of habit.**

| Situation | Test | Why |
|---|---|---|
| Paired continuous scores (same items, both systems) | Paired $t$ or Wilcoxon signed-rank | Pairing removes item variance; Wilcoxon if non-normal/outliers |
| Paired win/loss (same items, binary better/worse) | McNemar (1947) | Uses only the discordant pairs, which carry the signal |
| Arbitrary or non-normal metric (BLEU, pass@k, p95 latency) | Bootstrap CI (Efron 1979) | No distributional assumption; resample the *pairs* |
| Small N, need an exact null | Permutation test | Exact under exchangeability; no asymptotics |

→ *Expected:* A named test whose assumptions you can defend out loud.
→ *Deviation:* Using an unpaired test on paired data throws away your best variance reduction; using a $t$-test on a heavy-tailed metric (latency, token counts) gives a CI that lies.

**4. Run to the pre-registered N — do not peek and stop.**
Fix N in advance, or if you must monitor live, use an *always-valid* method (alpha-spending / sequential confidence sequences).
→ *Expected:* You compute significance once, at the planned stopping point.
→ *Deviation:* Naive repeated interim looks inflate the false-positive rate far above your nominal $\alpha$ — checking a 0.05 test daily for two weeks yields a true FPR around 0.2–0.3. "It looked significant so we stopped" *invalidates the p-value.* This is the single most common sin in production A/B testing; it is exactly why platforms like Optimizely shipped sequential ("always-valid") statistics — the classic fixed-horizon test is wrong the moment a human watches the dashboard.

**5. Correct for multiplicity.**
If you test many metrics, slices, or model variants, adjust. Bonferroni (divide $\alpha$ by the number of tests) is strict and controls family-wise error; Benjamini-Hochberg (1995) controls the false discovery rate and is far more powerful when you have many tests.
→ *Expected:* Adjusted thresholds recorded alongside raw p-values.
→ *Deviation:* An uncorrected sweep of 20 metrics at $\alpha=0.05$ expects ~1 spurious "win" by construction. The dashboard with 40 green cells has ~2 lies in it.

**6. Report the effect size with a confidence interval — not just the p-value.**
State: effect size, its (1−α) CI, N, the test, and its assumptions. A p-value alone is uninterpretable; the CI carries the magnitude *and* the uncertainty.
→ *Expected:* "B beats A by 1.8 points (95% CI [0.4, 3.2]), paired bootstrap, n=2,000."
→ *Deviation:* Reporting only "p<0.05" hides that the effect might be 0.4 points — statistically real, practically irrelevant.

## Verification

- **Reproduce on a fresh seed/split.** A real effect survives reseeding; a result that flips sign across seeds *is* the noise you were supposed to measure.
- **Sanity-check the CI width against N.** A CI width wildly inconsistent with $\sigma/\sqrt{n}$ means a variance mis-estimate or a broken pairing.
- **Run a negative control.** Compare a system to *itself* (two seeds of A). It should show no significant difference; if it does, your pipeline is leaking or your test's assumptions are violated.
- **A/A test the harness** before trusting any A/B number.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Significant but tiny effect | Overpowered; N so large every trivial gap "wins" | Report effect size + CI; decide against the MDE, not against zero |
| Wide CI spanning zero | Underpowered / high variance | Not "no difference" — inconclusive. Pair/block (Step 2) and add data |
| Result flips across seeds | You measured noise; item variance not controlled | Switch to a paired design; increase N |
| Won "after we kept checking" | Optional-stopping inflation (Step 4) | Discard; rerun with fixed N or a sequential test |
| One of 30 metrics is significant | Multiplicity (Step 5) | Apply Benjamini-Hochberg; treat unadjusted hits as hypotheses, not findings |
| "Significant" but the CI barely clears zero and N is small | Winner's curse / Type M error (Gelman & Carlin 2014) | Underpowered wins overestimate the effect; replicate before believing the magnitude |

For LLM- and benchmark-specific versions of these traps — judge variance, contamination, per-example scoring — cross over to the evaluation domain via the Connections below.

## Connections

- [[Concept - Hypothesis Testing and p-values]] — the definitions this playbook operationalizes; read it first for what a p-value, CI, and power actually mean.
- [[Concept - Statistical Rigor in Model Evaluation]] — the same discipline applied specifically to model benchmarks; where variance comes from judges, sampling, and prompt format.
- [[Deep Dive - Designing an Eval Harness]] — where you *implement* pairing, seeds, and bootstrap CIs so that "run without peeking" is enforced by the tooling, not willpower.
- [[Snippet - Paired Bootstrap for Model Comparison]] — the exact resampling code for Step 3's bootstrap-CI branch; the tool this playbook keeps pointing at.
- [[Concept - LLM-as-Judge]] — a judge is a noisy, biased measurement instrument; its variance and drift are why you must pair and power your comparisons.
- [[Concept - Benchmark Contamination]] — a confound that makes an "effect" real in your data and fake in the world; pre-registration does not save you from a poisoned test set.
- [[Lore - Benchmark Scandals]] — the field's cautionary tales of p-hacking, contamination, and forking-path reporting; the deep end of what this playbook prevents.
- [[Decision - Deep Learning vs Gradient Boosting for Tabular Data]] — a decision that lives or dies on a *valid* comparison; the classic arena where an unpaired, uncorrected sweep declares a false winner.

## Sources

- Gelman & Loken (2013) — "The garden of forking paths." Names why analysis flexibility inflates false positives even without intentional p-hacking.
- Ioannidis (2005) — "Why Most Published Research Findings Are False." The base-rate argument for pre-registration and power.
- Benjamini & Hochberg (1995) — "Controlling the False Discovery Rate." The multiplicity correction to reach for when tests are many.
- Efron (1979) — "Bootstrap Methods." The distribution-free CI for arbitrary metrics; Koehn (2004) applied bootstrap resampling to MT eval significance.
- McNemar (1947) — the paired binary test for win/loss comparisons.
- Gelman & Carlin (2014) — Type S (sign) and Type M (magnitude) errors; why underpowered "wins" exaggerate.
