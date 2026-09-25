---
tags: [snippet, domain/evaluation, level/advanced]
aliases: [paired bootstrap, McNemar's test]
summary: "Runnable paired bootstrap and McNemar's test to decide whether one model actually beats another on the same benchmark items."
---
# Snippet - Paired Bootstrap for Model Comparison

> **What it does:** Takes two boolean per-item correctness arrays for models A and B, scored on the *same* benchmark items, and returns a bootstrap confidence interval on the accuracy difference plus the closed-form McNemar's test. Both are standard paired alternatives to comparing two independent marginal confidence intervals, which is the wrong tool here (see [[Concept - Statistical Rigor in Model Evaluation]]).
> **Dependencies:** numpy >= 1.20, Python 3.9+. A pure-Python fallback without numpy is a simple rewrite of the resampling loop with `random.choices`, left out for clarity.
> **Expected output:** with the worked example at the bottom (seed=42), something close to `delta (A - B) = 0.0XXX`, `95% CI = [lo, hi]`, `P(A > B) = 0.9XX`, `McNemar b=.., c=.., chi2=.., p=0.0XXX`. Exact digits depend on the RNG draw, but the sign and rough magnitude are stable across reruns because the seed is fixed.

```python
"""
Paired bootstrap and McNemar's test for comparing two models on the SAME
benchmark items. Both are paired tests: they exploit the fact that A and B
were scored on identical items, so their per-item correctness is correlated,
rather than treating the two accuracy numbers as independent samples.
"""

import numpy as np


def paired_bootstrap(correct_a: np.ndarray, correct_b: np.ndarray,
                      n_resamples: int = 10_000, seed: int = 0):
    """
    correct_a, correct_b: 1-D boolean (or 0/1) arrays, same length,
                           SAME item order — item i must be the same
                           benchmark question in both arrays.
    Returns (observed_delta, ci_lo, ci_hi, p_a_greater).
    """
    assert correct_a.shape == correct_b.shape, "must be scored on identical items"
    n = correct_a.shape[0]
    rng = np.random.default_rng(seed)

    observed_delta = correct_a.mean() - correct_b.mean()

    # Resample ITEM INDICES, not A and B separately — this is what keeps
    # the pairing (and therefore the correlation) intact. See "Why it's
    # written this way" below.
    idx = rng.integers(0, n, size=(n_resamples, n))
    deltas = correct_a[idx].mean(axis=1) - correct_b[idx].mean(axis=1)

    ci_lo, ci_hi = np.percentile(deltas, [2.5, 97.5])   # percentile bootstrap
    p_a_greater = float((deltas > 0).mean())
    return observed_delta, ci_lo, ci_hi, p_a_greater


def mcnemar(correct_a: np.ndarray, correct_b: np.ndarray):
    """
    Closed-form paired significance test on the discordant-pairs count.
    b = items A got right and B got wrong; c = items A got wrong and B got right.
    Concordant items (both right or both wrong) carry no information about
    which model is better and are correctly excluded from the statistic.
    Uses the continuity-corrected chi-square form for b + c >= 25, and an
    exact binomial test below that (the chi-square approximation is
    unreliable on the small discordant counts typical of a ~200-item
    benchmark like GPQA-Diamond).
    """
    b = int(np.sum(correct_a & ~correct_b))
    c = int(np.sum(~correct_a & correct_b))

    if b + c < 25:
        from math import comb
        n, k = b + c, min(b, c)
        p = min(1.0, 2 * sum(comb(n, i) * 0.5 ** n for i in range(0, k + 1)))
        stat = None
    else:
        stat = (abs(b - c) - 1) ** 2 / (b + c)
        from math import erf, sqrt
        p = 1 - erf(sqrt(stat / 2))   # chi2(1) survival via the normal relation
    return b, c, stat, p


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    n_items = 500
    correct_a = rng.random(n_items) < 0.62                      # model A: ~62% accuracy
    raw_b = rng.random(n_items) < 0.60                           # model B: ~60% accuracy
    # correlate B with A on 70% of items to mimic two real models answering
    # the same benchmark (they agree on "easy" items and disagree on hard ones)
    correct_b = np.where(rng.random(n_items) < 0.7, correct_a, raw_b)

    delta, lo, hi, p_a = paired_bootstrap(correct_a, correct_b)
    b, c, stat, p_mcnemar = mcnemar(correct_a, correct_b)

    print(f"delta (A - B)            = {delta:.4f}")
    print(f"95% CI (percentile)      = [{lo:.4f}, {hi:.4f}]")
    print(f"P(A > B) over resamples  = {p_a:.3f}")
    print(f"McNemar b={b}, c={c}, chi2={stat}, p={p_mcnemar:.4f}")
```

## Why it's written this way

- **Resampling item indices, instead of resampling A and B independently, is the whole point.** Bootstrap `correct_a` and `correct_b` separately and you get two independent-sample confidence intervals, the weaker tool this snippet replaces. Indexing both arrays with one shared resampled index array keeps the item-level correlation between the two models' scores, and that correlation is where a paired comparison gets its power.
- **The main lesson is in the comment, not the code:** overlapping marginal confidence intervals do **not** imply a non-significant difference. Each model can have a wide individual accuracy CI, overlapping the other's, while the *paired* difference is significant, because both marginals carry noise the paired test cancels. It's the most common statistical error in casual model-vs-model comparisons, and it comes from using the right data the wrong way.
- **McNemar falls back to an exact binomial below b+c=25.** The chi-square approximation's accuracy depends on the discordant-pair count, not total items. A 1000-item benchmark where the models agree on 950 items still has only ~50 discordant pairs, and small benchmarks like AIME or GPQA-Diamond can land well under the point where the closed form is trustworthy.
- **Percentile bootstrap is used over BCa (bias-corrected and accelerated) for transparency, not because it's always better.** Percentile intervals can be biased when the delta's resampling distribution is skewed, which is more likely at small n. Flag it instead of trusting it silently, and use BCa (`scipy.stats.bootstrap(..., method="BCa")`) on small or skewed benchmarks. Both functions also assume item-level independence. For a benchmark with real cluster structure (MMLU's 57 subjects, or any multi-question-per-passage set), resample clusters instead of items or the interval will come out too narrow.

## Connections

- [[Concept - Statistical Rigor in Model Evaluation]] — the conceptual case for paired testing and confidence intervals this snippet is the runnable implementation of.
- [[Concept - Human Evaluation Methodology]] — the same paired-comparison logic applies when the "correctness" array comes from human pairwise preference votes instead of an automatic verifier.
- [[Reference - LLM Benchmark Landscape]] — supplies the item counts (AIME ~30, GPQA-Diamond ~198) that determine whether McNemar's exact-binomial fallback triggers on a given benchmark.
- [[Checklist - Trusting a Benchmark Number]] — this snippet is the concrete tool behind that checklist's "was a paired test used" item.
- [[Concept - Hypothesis Testing and p-values]] — the foundational null-hypothesis-testing framework (Foundations domain) both functions here specialize to the paired, same-item comparison case.
- [[Playbook - Evaluating a Fine-Tune]] — the practical use case: deciding whether a fine-tune actually beat its base model rather than winning on noise (Fine-Tuning domain).
- [[Concept - Conformal Prediction]] — a distribution-free alternative (Classical ML domain, frontier) for quantifying prediction uncertainty, contrasted here with resampling-based CIs on an accuracy delta.

## Sources

- Efron, B. & Tibshirani, R. (1993) — "An Introduction to the Bootstrap." The foundational resampling methodology this snippet implements directly.
- McNemar, Q. (1947) — "Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages." The closed-form paired significance test for binary same-item comparisons.
- Dror, R. et al. (2018) — "The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing." Surveys paired bootstrap and permutation testing for exactly this NLP model-comparison setting.
- Miller, E. (2024) — "Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations." The practitioner-facing case for reporting paired uncertainty rather than bare deltas.
