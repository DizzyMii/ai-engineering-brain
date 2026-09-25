---
tags: [concept, domain/classical-ml, level/unicorn]
aliases: [time series cross-validation, purged k-fold, embargo, walk-forward validation, forward chaining, backtest leakage, CPCV]
summary: "Validating temporal and financial models without leakage: forward-chaining, purging, embargo, and CPCV."
---

# Concept - Time Series Cross-Validation and Leakage

> **Hook:** On temporal and financial data, the ordinary cross-validation you trust everywhere else generates lies. Shuffle-and-split lets the model peek at the future, and the backtest prints a Sharpe ratio that evaporates once real money is on it. This note is the tribal knowledge quants and time-series people learn by losing: the specific leakage traps, and the purging/embargo machinery that stops them. The governing folklore, plainly: **if your backtest looks too good, you have leakage.** Experienced practitioners assume leakage until they've *proven* it isn't there.

## The mechanism

**Random K-fold leaks the future into the past.** Standard [[Concept - Statistical Rigor in Model Evaluation|k-fold CV]] assumes rows are exchangeable, so it happily puts January and March in training and February in validation. The model is now trained on data from *after* the point it predicts. Any temporal autocorrelation becomes a leaked answer, and real series are nothing but autocorrelation. The scores are gorgeous and worthless.

The baseline fix is **forward-chaining** (walk-forward) CV: always train on the past and validate on the future.

```
Fold 1:  train [────]           val [──]
Fold 2:  train [────────]       val [──]
Fold 3:  train [────────────]   val [──]
         time ─────────────────────────────►
```

Train on `[0, t]`, validate on `(t, t+h]`, then roll `t` forward, with either an **expanding** window (keep all history) or a **rolling** one (drop stale history when the process is non-stationary). scikit-learn's `TimeSeriesSplit` is the expanding version. It's necessary but *not sufficient*: it fixes split order and leaves the two subtler leaks below.

**Purged K-fold + embargo** handles labels that span time (López de Prado, *Advances in Financial Machine Learning*, 2018). If the label is a forward return ("did price rise over the next 5 days?"), a training sample's label window can *overlap* the test window even when the feature timestamps don't. Two defenses:

```
                              TEST BLOCK
train ... [t_i feat|─── t_i label window ───] │██████████████│ ......... train
                              PURGE ───────────┘              └─── EMBARGO ───┐
          (drop train samples whose LABEL window                (drop/skip train samples for a
           overlaps the test window)                             gap AFTER the test block; kills
                                                                 leakage via serial correlation)
```

- **Purge:** drop any training sample whose *label* window overlaps the test window. Otherwise that training label was partly set by data inside the test period.
- **Embargo:** after the test block, skip a gap of training samples before resuming. Serial correlation makes the observations *right* after the test set near-copies of it, and without the gap they leak too. Embargo length scales with the label horizon; a few percent of the sample is typical for daily bars.

## In practice

- **Feature look-ahead is the number-one backtest bug, bar none.** Any transform fit over the *whole* series drags the future backwards: a rolling mean with a centered window, target encoding computed on all rows (see [[Snippet - Leakage-Free Target Encoding]]), z-scoring with the full-series mean/std, forward-fill imputation, a StandardScaler `.fit()` on the entire dataset. **Every transform must be causal**: fit on data at or before time `t`, applied at `t`. The tell is a feature whose importance is suspiciously high and whose live performance is suspiciously absent.
- **Group leakage stacks on top of the temporal kind.** The same customer, instrument or event in adjacent train and test periods leaks even with correct time ordering, and so do duplicated rows and near-duplicate events. Split by **group AND time at once**. The same pitfall bites [[Gotchas - Gradient Boosting in Practice|boosted-tree pipelines]] when an ID column silently ties folds together.
- **Overlapping labels break IID and inflate significance.** When labels share time (overlapping return windows), your "N samples" holds far fewer *independent* observations than the count suggests, and every significance test is over-optimistic. Corrections: **sample-uniqueness weighting** (down-weight overlapping labels), the **deflated Sharpe ratio**, and the **Probability of Backtest Overfitting (PBO)**, which accounts for how many strategy variants you tried. That multiple-testing tax is what turns a "3-sigma" alpha into noise.
- **Pipeline order for temporal work:** build the leak-free split *first* (as [[Playbook - Tuning Gradient Boosted Trees|tuning playbooks]] insist), then engineer causal features, then tune. Do it in reverse and no later rigor will save you.

## Failure modes

- **The backtest that's too good.** Sharpe > 3 in-sample, flat live. The cause is almost always feature look-ahead or overlapping-label leakage. Detect it with **adversarial validation**: train a classifier to tell train rows from test rows. If it succeeds easily, the splits are distinguishable and probably leaking, and any feature it leans on is a leak suspect.
- **Silent non-stationarity.** Even *perfectly* clean forward-chaining overestimates future performance when the data-generating process changes regime. A model validated on 2015–2019 and deployed into a 2020 regime break gets no protection from CV alone. It's the same distribution-shift wall that voids [[Concept - Conformal Prediction|conformal coverage guarantees]]. Track realized out-of-sample performance against the backtest distribution over time (see [[Concept - Production Monitoring and Drift Detection|drift detection]]).
- **Single-number fragility.** One backtest path is one draw from a distribution you never see. **Combinatorial Purged Cross-Validation (CPCV)** splits the timeline into `N` blocks, trains and tests over the $\binom{N}{k}$ combinations of held-out blocks (each purged and embargoed), and returns a **distribution of Sharpe ratios** across many paths in place of one fragile point estimate. A strategy that looks great on one path and awful on the median was overfit to that path.

## The non-obvious

The deepest trap is **cognitive, not statistical**. Leakage doesn't show up as a bug. It shows up as *success*. Every other bug makes your numbers worse; leakage makes them better, so your incentives work against catching it. That inversion is why the discipline codifies distrust: "trust your CV, not the leaderboard" from [[Lore - Kaggle and the Reign of Gradient Boosting|competitive ML]], "assume leakage until proven otherwise" from quant finance.

The second point: **leakage belongs to the pipeline, not the model.** Swap XGBoost for a neural net and the leaked backtest stays beautiful, because the future came in through the *data*. It's the temporal cousin of [[Concept - Benchmark Contamination|benchmark contamination]] (test data bleeding into training), and one instinct catches both. When a result is surprisingly good, the first hypothesis should be "where did the answer leak in?", not "great model." The people who survive reach for that hypothesis *first* and have made purge, embargo, causal features and CPCV routine, so a leak can't slip in unnoticed. The leakage you didn't hunt for is the leakage you shipped.

## Connections
- [[Concept - Classical Time Series Forecasting]] — the models being validated here; forward-chaining and causal features are the safe way to backtest ARIMA/ETS/LightGBM forecasters.
- [[Gotchas - Gradient Boosting in Practice]] — target-encoding and future-information leakage are the same bug in the boosted-tree setting; this note is its temporal generalization.
- [[Concept - Statistical Rigor in Model Evaluation]] — overlapping labels, multiple testing, and the deflated Sharpe ratio are why naive significance is inflated on time series.
- [[Concept - Benchmark Contamination]] — the LLM-era cousin: test data leaking into training inflates scores the same way look-ahead inflates backtests.
- [[Concept - Learning from Imbalanced Data]] — rare-event temporal targets combine both traps; resampling must also respect the time boundary.
- [[Concept - Conformal Prediction]] — non-exchangeability under regime change breaks conformal coverage exactly as it breaks naive CV; the failure has one root.
- [[Playbook - Tuning Gradient Boosted Trees]] — its first step is "build a leak-free CV scheme before touching hyperparameters"; this note is the deep version of that step for temporal data.
- [[Snippet - Leakage-Free Target Encoding]] — the concrete causal-transform fix: a statistic learned from the target that must not see the held-out split, the row-level analogue of look-ahead leakage.
- [[Concept - Production Monitoring and Drift Detection]] — the live-side check that catches the regime change even a perfect backtest can't anticipate.
- [[Lore - Kaggle and the Reign of Gradient Boosting]] — where "trust your CV, not the leaderboard" and adversarial validation were codified as folklore before the literature caught up.

## Sources
- López de Prado, M. (2018) — *Advances in Financial Machine Learning.* The canonical treatment of purged K-fold, embargo, sample uniqueness, PBO, and CPCV.
- Bailey, Borwein, López de Prado & Zhu (2014) — *Pseudo-Mathematics and Financial Charlatanism / The Deflated Sharpe Ratio.* Multiple-testing and backtest-overfitting corrections.
- scikit-learn — `TimeSeriesSplit` documentation. The expanding-window forward-chaining reference implementation.
