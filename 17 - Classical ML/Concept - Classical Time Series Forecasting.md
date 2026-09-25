---
tags: [concept, domain/classical-ml, level/core]
aliases: [ARIMA, SARIMA, ETS, exponential smoothing, Box-Jenkins]
summary: "ARIMA/ETS and the Box-Jenkins workflow — the statistical forecasting toolkit that gradient boosting on lag features now usually beats."
---

> For a decade the biggest public forecasting competitions were won by careful use of a handful of 1970s-era statistical methods, not by the fanciest model. Then, in 2020, the winner treated forecasting as ordinary tabular regression. Both facts matter more to a working forecaster than any particular architecture.

## The mechanism

**ARIMA(p,d,q)** has three parts: autoregression on $p$ past values, differencing of order $d$ to remove trend and induce stationarity, and a moving-average term over $q$ past forecast errors:

$$\left(1 - \sum_{i=1}^p \phi_i L^i\right)(1-L)^d y_t = \left(1 + \sum_{j=1}^q \theta_j L^j\right)\varepsilon_t$$

where $L$ is the lag operator. The **Box-Jenkins workflow** picks $p$ and $q$ from the autocorrelation function (ACF) and partial autocorrelation function (PACF). A pure AR($p$) process has a PACF that cuts off sharply after lag $p$ and an ACF that decays gradually; a pure MA($q$) process is the mirror image. Seasonal data needs **SARIMA(p,d,q)(P,D,Q)$_s$**, which adds a second set of AR/I/MA terms at the seasonal lag $s$.

Everything here rests on **stationarity**: constant mean, variance and autocorrelation structure over time. Test it with the Augmented Dickey-Fuller test (ADF, null = unit root / non-stationary) and KPSS (null = stationary, deliberately the opposite null, so run both). Induce it by differencing for trend and log/Box-Cox transforms for variance that grows with the level.

**Exponential smoothing (ETS)** is the other classical family, and on real business series it often beats ARIMA. It builds in layers. Simple exponential smoothing ($\hat y_{t+1} = \alpha y_t + (1-\alpha)\hat y_t$) handles a level with no trend. **Holt's method** adds a trend component, and **Holt-Winters** adds multiplicative or additive seasonality on top. All of ETS can be written in state-space form, the same conceptual family as the state-space sequence models that came back decades later in [[Concept - State Space Models and Mamba]]. That's what lets modern implementations (`statsmodels`, R's `forecast::ets`) fit it by maximum likelihood and pick the best variant automatically by AIC.

## In practice

The empirical history is unusually well documented because it played out in public competitions. The **M-competitions** (Makridakis et al., run roughly every 4–6 years since 1982) kept finding that simple statistical methods, and *combinations* of simple methods, beat complex ones. That was a surprising result and the field leaned on it. It held until **M4 (2018)**, won by Slawek Smyl's hybrid ES-RNN: an [[Concept - Recurrent Networks and the LSTM]]-based model that used exponential smoothing for each series' level/trend/seasonality and let the RNN learn cross-series patterns. It wasn't a pure neural model. Then **M5 (2020)**, on hierarchical Walmart retail data, was won outright by [[Concept - Gradient Boosting]] via [[Breakdown - LightGBM]]. That's where gradient boosting overtook pure statistical forecasting as the practical default for large, many-series problems.

The win encodes today's strong baseline: treat forecasting as **tabular regression**. Build lag features ($y_{t-1}, y_{t-7}, y_{t-28}, \ldots$), rolling statistics (mean/std over trailing windows) and calendar/Fourier seasonality features. Then fit one [[Breakdown - LightGBM]] model across *all* series at once so it can share patterns between similar products or stores. ARIMA, fit per series, can't do that by construction. This approach usually beats per-series ARIMA and Prophet on multi-series retail/demand data, and it comes with all the tuning machinery in [[Reference - Gradient Boosting Hyperparameters]].

**Evaluation** should never rest on raw MAE/RMSE alone.

- **MASE** (Mean Absolute Scaled Error) scales error against a naive (last-value or seasonal-naive) forecast's error, giving a scale-free number you can compare across series.
- **sMAPE** is the common symmetric-percentage alternative, with known asymmetry quirks near zero.
- **Pinball/quantile loss** scores probabilistic forecasts at specific quantiles. Or wrap a point forecast model-agnostically in [[Concept - Conformal Prediction]] for a distribution-free interval instead of a parametric one.

The **seasonal-naive baseline** ("this period equals the same period last cycle") is shockingly hard to beat, and you should always report it next to any fancier model. A forecasting result with no naive baseline comparison can't be trusted; it's the same evaluation discipline covered in [[Concept - Statistical Rigor in Model Evaluation]].

## Failure modes

- **Regime change / structural breaks.** A model fit on a stable historical regime degrades silently when the process shifts (a promotion policy change, a demand shock). Track rolling out-of-sample error; a single static backtest won't catch it.
- **Over-differencing.** Differencing more than stationarity needs injects spurious negative autocorrelation and inflates forecast variance. Check ADF/KPSS after each differencing step instead of differencing by reflex.
- **Look-ahead leakage from full-series features.** Normalizing, imputing or computing rolling statistics over the whole series, including points in the future of a given training cutoff, is the single most common bug in ML forecasting pipelines. Every transform has to be strictly causal. [[Concept - Time Series Cross-Validation and Leakage]] covers this discipline.
- **Continuous-demand models on intermittent demand.** Series full of exact zeros (spare parts, low-volume SKUs) break ARIMA/ETS smoothness assumptions. Use Croston's method or its TSB variant, which model demand size and inter-demand interval separately.
- **Trusting in-sample fit.** A model can fit history well and still forecast badly. Always evaluate on a truly held-out future window with the forward-chaining CV from [[Concept - Time Series Cross-Validation and Leakage]], never a random split.

## The non-obvious

The field's competition history is the main evidence base here, more than any single paper. [[Lore - Kaggle and the Reign of Gradient Boosting]] isn't really a separate story from classical forecasting. M5's LightGBM win *is* where the two threads merged, and it's why "add lag features and throw it at a GBDT" became the default even for people who think of themselves as doing "real" statistical forecasting. A corollary, folklore that's weakly sourced but widely repeated: most production forecasting gains come from better features (holidays, promotions, weather, hierarchy structure) and a correct backtest, not from swapping ARIMA for a fancier model family.

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
