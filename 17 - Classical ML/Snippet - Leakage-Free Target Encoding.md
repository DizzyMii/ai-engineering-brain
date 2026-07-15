---
tags: [snippet, domain/classical-ml, level/advanced]
aliases: [target encoding, mean encoding, out-of-fold encoding, OOF encoding, likelihood encoding]
summary: "Out-of-fold, Bayesian-smoothed mean encoding that beats one-hot on trees without leaking the target."
---

# Snippet - Leakage-Free Target Encoding

> **Hook:** Target (mean) encoding replaces a high-cardinality category with the mean of the target for that category — a single dense, ordered numeric column that [[Concept - Gradient Boosting|gradient-boosted trees]] split on far more efficiently than a wide one-hot block. Done naively it is the single most common Kaggle leakage bug: a row's own label bleeds into its own feature and the [[Concept - Statistical Rigor in Model Evaluation|cross-validation]] score becomes a fantasy. This is the out-of-fold, smoothed version that actually generalizes.

The two guards are orthogonal. **Out-of-fold (OOF)** computes each training row's encoding from folds that *exclude* it, so a row can never see its own target. **Bayesian smoothing** shrinks categories seen only a handful of times toward the global mean, so a level with `n=2` rows doesn't get a wildly overconfident encoding. Both are needed; either alone still fails.

```python
"""
Leakage-free target (mean) encoding for a high-cardinality categorical.

What it does:
  Encodes a categorical column by the target mean, computing each TRAIN row's
  value from only the folds that EXCLUDE it (out-of-fold), and shrinking rare
  categories toward the global mean (Bayesian smoothing). Beats one-hot on
  tree models without the target leakage naive target encoding causes.

Dependencies (as of 2026):
  python 3.11, numpy 1.26+, pandas 2.x, scikit-learn 1.4+ (KFold only).

Expected output (seed=0):
  global mean:            ~0.35
  train NaNs after fit:   0
  corr(cat_te, y) train:  ~0.20   # real signal, NOT leakage (~1.0 would be a leak)
  test NaNs (unseen cat): 0
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold


def _smoothed_means(stats: pd.DataFrame, global_mean: float, m: float) -> pd.Series:
    # Bayesian shrinkage: encoded = (n*cat_mean + m*global_mean) / (n + m).
    # m is a pseudo-count of "prior" observations pinned at global_mean, so a
    # level seen n << m times is pulled almost entirely back to global_mean.
    n, s = stats["count"], stats["sum"]
    return (s + m * global_mean) / (n + m)


def fit_target_encoding(train, col, target, m=20.0, n_splits=5, seed=0):
    """Return (oof: Series on train.index, mapping: dict, global_mean: float)."""
    global_mean = float(train[target].mean())
    oof = pd.Series(np.nan, index=train.index, dtype="float64")

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for tr_idx, val_idx in kf.split(train):
        tr = train.iloc[tr_idx]
        # Stats come from the TRAINING folds only; the held-out rows (val_idx)
        # never contribute to their own encoding -> no self-leak.
        stats = tr.groupby(col)[target].agg(["count", "sum"])
        enc = _smoothed_means(stats, global_mean, m)
        mapped = train.iloc[val_idx][col].map(enc)
        oof.iloc[val_idx] = mapped.fillna(global_mean)  # category absent in fold -> prior

    # Inference mapping: fit ONCE on the full training set (maximum signal) and
    # reused for every test row. Unseen test categories fall back to global_mean.
    full_stats = train.groupby(col)[target].agg(["count", "sum"])
    mapping = _smoothed_means(full_stats, global_mean, m).to_dict()
    return oof, mapping, global_mean


def transform_target_encoding(df, col, mapping, global_mean):
    return df[col].map(mapping).fillna(global_mean)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    n = 20_000
    cats = rng.integers(0, 500, size=n)          # 500 levels: high-cardinality
    base = (cats % 7) / 7.0                       # genuine per-category effect
    y = rng.binomial(1, 0.15 + 0.5 * base)        # target depends on category

    df = pd.DataFrame({"cat": cats, "y": y})
    train, test = df.iloc[:15_000].copy(), df.iloc[15_000:].copy()

    oof, mapping, gm = fit_target_encoding(train, "cat", "y", m=20.0, n_splits=5)
    train["cat_te"] = oof
    test["cat_te"] = transform_target_encoding(test, "cat", mapping, gm)

    leak_corr = np.corrcoef(train["cat_te"], train["y"])[0, 1]
    print(f"global mean:            {gm:.4f}")
    print(f"train NaNs after fit:   {train['cat_te'].isna().sum()}")
    print(f"corr(cat_te, y) train:  {leak_corr:.3f}  # signal, not leakage")
    print(f"test NaNs (unseen cat): {test['cat_te'].isna().sum()}")
```

## Why it's written this way

1. **The OOF split is the leakage guard.** If you fit `groupby(col)[target].mean()` on the whole training set and map it back, every row's encoding contains that row's own `y`. On a category with one row, the encoding *is* the label — `corr(cat_te, y)` shoots to ~1.0 and the model learns to read the answer off the feature. Encoding each fold from the *other* folds severs that path. This is why `oof.iloc[val_idx]` is assigned from `enc` built on `tr_idx` only.

2. **The smoothing prior is the variance guard.** `(n*cat_mean + m*global_mean)/(n+m)` is a conjugate-style shrinkage (Micci-Barreca 2001). Without it, a level seen 3 times with all-positive labels encodes to 1.0 and the tree treats a noise spike as certainty. `m≈20` means "trust the category once you've seen it far more than 20 times, otherwise trust the base rate." Tune `m` to the noise level, not the cardinality.

3. **Fit and transform are deliberately separate objects.** Training rows get the *OOF* encoding; test/inference rows get a *single* mapping fit on the full training set. Mixing these — using the full-train mapping on train rows too — quietly reintroduces the leak on the training split. The returned `mapping` dict is a fitted artifact you serialize and ship; it is the only thing that touches production, which mirrors how the encoder must actually run.

4. **`fillna(global_mean)` handles the unseen-category case naive code crashes on.** A category present at serve time but absent from training maps to `NaN`; falling back to the prior is the correct, calibrated default. This is not defensive padding — high-cardinality columns (user IDs, ZIP codes, SKUs) reliably surface novel levels in production.

**The non-obvious trap this snippet does *not* fully solve:** OOF encoding protects *within* the training set, but when you wrap the whole pipeline in an outer CV loop for model selection, the encoder must be **re-fit inside each outer fold**. Fit it once on all data and the outer validation fold's targets have leaked into the encoding of every outer training fold. The rule generalizes: any statistic learned from the target (encodings, priors, normalization by target-correlated quantities) is a model parameter and must live inside the resampling boundary. See [[Concept - Time Series Cross-Validation and Leakage]] for the temporal analogue.

**A different answer to the same problem:** CatBoost's *ordered target statistics* dispense with folds entirely — it draws a random permutation of the rows and encodes each row using only the targets of rows that precede it (an expanding-window mean), which is leakage-free online and avoids the fold-count/variance tradeoff. Same disease, different cure; worth knowing when you reach for [[Breakdown - LightGBM|a boosting library]] and want native categorical handling.

## Connections
- [[Concept - Gradient Boosting]] — target encoding exists mainly to feed dense ordered features to boosted trees; it is the encoding of choice over one-hot for high cardinality.
- [[Gotchas - Gradient Boosting in Practice]] — this snippet is the concrete fix for the "target leakage from features" gotcha catalogued there.
- [[Breakdown - LightGBM]] — its native categorical splits and CatBoost's ordered target statistics are the built-in alternatives to hand-rolled encoding.
- [[Concept - Statistical Rigor in Model Evaluation]] — the whole point is that the CV number stays honest; a leaked encoding is the fastest way to inflate it.
- [[Concept - Learning from Imbalanced Data]] — smoothing strength interacts with class imbalance; rare-positive categories are exactly where naive encoding overfits hardest.
- [[Concept - Training Set Decontamination]] — the same principle at corpus scale: any information that crosses the train/eval boundary silently inflates measured performance.
- [[Concept - Time Series Cross-Validation and Leakage]] — the deeper, temporal form of the same rule: statistics learned from the target must never see the future or the held-out split.

## Sources
- Micci-Barreca, D. (2001) — *A Preprocessing Scheme for High-Cardinality Categorical Attributes in Classification and Prediction Problems.* The original smoothed empirical-Bayes target encoding.
- Prokhorenkova et al. (2018) — *CatBoost: unbiased boosting with categorical features.* Introduces ordered target statistics, the permutation-based leakage-free alternative referenced in the comments.
