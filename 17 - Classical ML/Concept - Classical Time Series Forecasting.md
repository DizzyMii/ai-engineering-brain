---
tags: [concept, domain/classical-ml, level/core]
aliases: [ARIMA, SARIMA, ETS, exponential smoothing, Box-Jenkins]
summary: "ARIMA/ETS and the Box-Jenkins workflow — the statistical forecasting toolkit that gradient boosting on lag features now usually beats."
---

> For a decade, the biggest public forecasting competitions were won not by the fanciest model but by careful application of a handful of 1970s-era statistical methods — and then, in 2020, by treating forecasting as ordinary tabular regression. Both facts matter more to a working forecaster than any specific architecture.

## The mechanism

**ARIMA(p,d,q)** combines three components: autoregression on $p$ past values, differencing of order $d$ to remove trend and induce stationarity, and a moving-average term over $q$ past forecast errors:

$$\left(1 - \sum_{i=1}^p \phi_i L^i\right)(1-L)^d y_t = \left(1 + \sum_{j=1}^q \theta_j L^j\right)\varepsilon_t$$

where $L$ is the lag operator. The **Box-Jenkins workflow** identifies $p$ and $q$ from the autocorrelation function (ACF) and partial autocorrelation function (PACF): a pure AR($p$) process has a PACF that cuts off sharply after lag $p$ while its ACF decays gradually; a pure MA($q$) process is the mirror image. Seasonal data needs **SARIMA(p,d,q)(P,D,Q)$_s$**, adding a second set of AR/I/MA terms at the seasonal lag $s$.

**Stationarity is the load-bearing assumption** underneath all of this: a stationary series has constant mean, variance, and autocorrelation structure over time. It's tested with the Augmented Dickey-Fuller test (ADF, null = unit root / non-stationary) and KPSS (null = stationary — deliberately the opposite null, run both), and induced by differencing for trend and log/Box-Cox transforms for variance that grows with the level.

**Exponential smoothing (ETS)** is the other classical family, and in practice often beats ARIMA on real business series. It builds up in layers: simple exponential smoothing ($\hat y_{t+1} = \alpha y_t + (1-\alpha)\hat y_t$) handles a level with no trend; **Holt's method** adds a trend component; **Holt-Winters** adds multiplicative or additive seasonality on top of that. All of ETS is expressible in state-space form — the same conceptual family as the state-space sequence models revisited decades later in [[Concept - State Space Models and Mamba]] — which is what lets modern implementations (`statsmodels`, R's `forecast::ets`) fit it by maximum likelihood and select the best variant automatically via AIC.

## In practice

The empirical history here is unusually well-documented because it was fought out in public competitions. The **M-competitions** (Makridakis et al., run roughly every 4–6 years since 1982) repeatedly found that simple statistical methods, and *combinations* of simple methods, beat complex ones — a genuinely surprising, load-bearing result for the field. That held until **M4 (2018)**, won by Slawek Smyl's hybrid ES-RNN — an [[Concept - Recurrent Networks and the LSTM]]-based model that used exponential smoothing to handle each series' level/trend/seasonality and let the RNN learn cross-series patterns, rather than a pure neural model. Then **M5 (2020)**, on hierarchical Walmart retail data, was won outright by [[Concept - Gradient Boosting]] via [[Breakdown - LightGBM]] — the moment gradient boosting overtook pure statistical forecasting as the practical default for large, many-series problems.

That win encodes the modern strong baseline: reframe forecasting as **tabular regression**. Build lag features ($y_{t-1}, y_{t-7}, y_{t-28}, \ldots$), rolling statistics (rolling mean/std over trailing windows), and calendar/Fourier seasonality features, then fit a single [[Breakdown - LightGBM]] model across *all* series at once so it can share patterns across similar products or stores — something ARIMA, fit per-series, structurally cannot do. This usually beats per-series ARIMA and Prophet on multi-series retail/demand data, and it inherits all the tuning machinery from [[Reference - Gradient Boosting Hyperparameters]].

**Evaluation** should never be raw MAE/RMSE alone. MASE (Mean Absolute Scaled Error) scales the error against a naive (last-value or seasonal-naive) forecast's error, giving a scale-free number comparable across series; sMAPE is the common symmetric-percentage alternative (with known asymmetry quirks near zero); pinball/quantile loss scores probabilistic forecasts at specific quantiles, or a point forecast can be wrapped model-agnostically in [[Concept - Conformal Prediction]] for a distribution-free interval instead of a parametric one. The **seasonal-naive baseline** ("this period equals the same period last cycle") is shockingly hard to beat and must always be reported alongside any fancier model — a forecasting result without a naive baseline comparison is not trustworthy, the same evaluation discipline covered generally in [[Concept - Statistical Rigor in Model Evaluation]].

## Failure modes

- **Regime change / structural breaks** — a model fit on a stable historical regime silently degrades when the underlying process shifts (a promotion policy change, a demand shock); detect via rolling out-of-sample error tracking, not a single static backtest.
- **Over-differencing** — differencing more than needed to achieve stationarity injects spurious negative autocorrelation and inflates forecast variance; detect by checking ADF/KPSS after each differencing step rather than differencing reflexively.
- **Look-ahead leakage from features computed over the full series** — normalizing, imputing, or computing rolling statistics using the entire series, including points that lie in the future relative to a given training cutoff, is the single most common bug in ML-based forecasting pipelines; every transform must be strictly causal. This is exactly the discipline covered in [[Concept - Time Series Cross-Validation and Leakage]].
- **Applying continuous-demand models to intermittent demand** — series with many exact zeros (spare parts, low-volume SKUs) break ARIMA/ETS's smoothness assumptions; use Croston's method or its TSB variant instead, which separately model demand size and inter-demand interval.
- **Trusting in-sample fit** — a model that fits history well can still forecast badly; always evaluate on a genuinely held-out future window via the forward-chaining CV scheme described in [[Concept - Time Series Cross-Validation and Leakage]], never a random split.

## The non-obvious

The field's own competition history is the load-bearing evidence base here, more than any single paper: [[Lore - Kaggle and the Reign of Gradient Boosting]] is not really a separate story from classical time series forecasting — M5's LightGBM win *is* the moment those two threads merged, and it's why "add lag features and throw it at a GBDT" quietly became the default even for practitioners who think of themselves as doing "real" statistical forecasting. The corollary, folklore, weakly sourced but widely repeated among practitioners: most production forecasting improvements come from better features (holidays, promotions, weather, hierarchy structure) and a correct backtest, not from swapping ARIMA for a fancier model family.

## Connections

- [[Concept - Time Series Cross-Validation and Leakage]] — the leakage-safe validation discipline (forward-chaining, purging) every model in this note must be evaluated under.
- [[Concept - Gradient Boosting]] — the mechanism behind the modern "forecasting as tabular regression" baseline that won M5.
- [[Breakdown - LightGBM]] — the concrete system that won the M5 competition and is the default engine for the lag-feature approach.
- [[Concept - Statistical Rigor in Model Evaluation]] — MASE, sMAPE, and naive-baseline comparison are instances of the same evaluation discipline applied specifically to forecasting.
- [[Concept - State Space Models and Mamba]] — ETS's state-space formulation is the classical ancestor of the state-space sequence models now used in deep learning.
- [[Lore - Kaggle and the Reign of Gradient Boosting]] — the competitive-ML history explaining why gradient boosting, not deep learning, became the default forecasting engine at scale.
- [[Reference - Gradient Boosting Hyperparameters]] — the tuning surface for the LightGBM model once forecasting is reframed as regression.
- [[Concept - Conformal Prediction]] — a model-agnostic way to get calibrated prediction intervals around any of these point forecasts, including ARIMA/ETS.
- [[Concept - Recurrent Networks and the LSTM]] — the architecture behind the ES-RNN hybrid that won M4, and the natural down-link into sequence modeling for readers coming from statistics.

## Sources
- Box & Jenkins (1970) — *Time Series Analysis: Forecasting and Control*, the origin of the ARIMA identification methodology.
- Smyl (2020) — "A hybrid method of exponential smoothing and recurrent neural networks for time series forecasting" (*International Journal of Forecasting*), the M4-winning ES-RNN.
- Makridakis, Spiliotis & Assimakopoulos — the M4 (2018) and M5 (2020) competition papers, the empirical record this note leans on.
- Hyndman & Athanasopoulos — *Forecasting: Principles and Practice*, the standard applied reference for ETS, ARIMA, and MASE.
