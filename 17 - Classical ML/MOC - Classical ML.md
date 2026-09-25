---
tags: [moc, domain/classical-ml, level/surface]
aliases: []
summary: "Map of Classical ML: tree ensembles, gradient boosting, calibration, imbalance, time series, and classical text/causal methods."
---

# MOC - Classical ML

This domain covers the non-neural machine learning toolkit that still runs most production tabular systems. That means decision trees and their ensembles (bagging, gradient boosting), the classical text representations (TF-IDF, word2vec) that came before transformer embeddings, statistical time series forecasting, and the evaluation disciplines every model needs to be trustworthy in production, neural or not: calibration, imbalanced-class handling, leakage-safe cross-validation, conformal prediction. Deep learning didn't replace these methods on structured data. Gradient-boosted trees (XGBoost, LightGBM) are still the default for anything under roughly a million rows, Kaggle spent a decade proving it empirically, and TabPFN (2023-2026) is the first serious neural challenger. The notes go from the mechanics of a single decision tree, through the additive-ensemble math of gradient boosting, into production concerns like hyperparameter tuning, target-encoding leakage and calibration drift, and out to in-context tabular transformers and distribution-free conformal guarantees. Come here when the problem is structured data, a small-to-mid-size dataset, or a baseline that has to be beaten before anyone gets to use the fancier model.

## Start here

- **Surface** → [[Concept - Decision Trees]]: recursive axis-aligned partitioning that greedily maximizes impurity decrease; the base learner every ensemble in this domain builds on.
- **Core** → [[Concept - Gradient Boosting]]: an additive ensemble fit by gradient descent in function space, correcting residual errors one shallow tree at a time.
- **Advanced** → [[Breakdown - XGBoost]]: the regularized, distributed, sparsity-aware systems paper that made gradient boosting the Kaggle default for a decade.
- **Frontier** → [[Breakdown - TabPFN]]: the transformer that classifies tabular data by in-context learning in one forward pass, the first credible neural challenger to GBTs.
- **Unicorn** → [[Lore - Kaggle and the Reign of Gradient Boosting]]: what Kaggle grandmasters learned about CV discipline and leak-hunting years before papers caught up.

## Trees and ensembles: the tabular baseline

- [[Concept - Decision Trees]] — recursive axis-aligned partitioning that greedily maximizes impurity decrease; the high-variance learner every tree ensemble is built from.
- [[Concept - Bagging and Random Forests]] — variance reduction by averaging decorrelated trees trained on bootstrap resamples and random feature subsets.
- [[Concept - Gradient Boosting]] — an additive ensemble fit by gradient descent in function space, correcting residual errors with shallow trees.

## Gradient boosting in production

- [[Breakdown - XGBoost]] — Chen & Guestrin's 2016 systems paper that made gradient boosting a regularized, distributed, sparsity-aware library and the Kaggle default for a decade.
- [[Breakdown - LightGBM]] — Microsoft's histogram-based GBDT (Ke et al. 2017), which used GOSS and EFB to out-train XGBoost on large data and won the M5 forecasting competition.
- [[Reference - Gradient Boosting Hyperparameters]] — cross-library map of the same tuning knobs in XGBoost, LightGBM and CatBoost: names, ranges, defaults, and what each controls.
- [[Playbook - Tuning Gradient Boosted Trees]] — the ordered, leak-checked procedure for taking XGBoost/LightGBM/CatBoost from baseline to squeezed final model without fooling yourself.
- [[Gotchas - Gradient Boosting in Practice]] — the leakage, overfit and calibration traps that make boosted-tree pipelines ace the notebook and fail in production.
- [[Snippet - Leakage-Free Target Encoding]] — out-of-fold, Bayesian-smoothed mean encoding that beats one-hot on trees without leaking the target.
- [[Decision - Deep Learning vs Gradient Boosting for Tabular Data]] — under ~1M rows, gradient-boosted trees beat deep nets on accuracy, speed and tuning cost; the default, with named exceptions.
- [[Breakdown - TabPFN]] — the transformer that classifies tabular data by in-context learning in one forward pass, no per-dataset training.

## Calibration, imbalance, and uncertainty

- [[Concept - Probability Calibration]] — making a classifier's scores mean P(y=1|score=p)=p, and the Platt/isotonic/temperature methods that enforce it after the fact.
- [[Concept - Learning from Imbalanced Data]] — why accuracy and ROC-AUC lie under class imbalance, the threshold, cost-weighting and resampling fixes, and the leakage trap that ruins them.
- [[Concept - Conformal Prediction]] — distribution-free prediction sets with finite-sample coverage that wrap any trained model.

## Time series

- [[Concept - Classical Time Series Forecasting]] — ARIMA/ETS and the Box-Jenkins workflow, the statistical forecasting toolkit that gradient boosting on lag features now usually beats.
- [[Concept - Time Series Cross-Validation and Leakage]] — validating temporal and financial models without leakage: forward-chaining, purging, embargo, and CPCV.

## Text representation and embeddings

- [[Concept - TF-IDF and the Bag of Words]] — sparse count-based text representation weighting terms by frequency and rarity; still a near-free, strong baseline for classification and retrieval.
- [[Concept - Word2Vec and the Embedding Lineage]] — how word2vec turned words into dense trainable vectors, why that's secretly matrix factorization, and what it seeded in every embedding since.

## Unsupervised learning and causal inference

- [[Concept - Clustering and Dimensionality Reduction]] — the core unsupervised toolkit for grouping and projecting unlabeled data, and how each method can silently mislead you.
- [[Concept - Causal Inference Basics]] — estimating what an intervention causes, beyond what correlates with it, when you can't randomize, and why predictive ML alone can't do this.

## Lore: what Kaggle taught before the papers caught up

- [[Lore - Kaggle and the Reign of Gradient Boosting]] — how gradient-boosted trees conquered Kaggle and codified CV discipline, stacking and leak-hunting years before papers validated them.

## Adjacent domains

- [[MOC - Evaluation]] — the calibration, imbalanced-class and leakage-safe validation discipline taught here on tabular models is the same one that domain applies to LLM evals.
- [[MOC - Retrieval & RAG]] — TF-IDF and word2vec are the direct ancestors of the dense embeddings that domain's retrieval stack depends on.
- [[MOC - Data Engineering]] — leakage-free target encoding and time series CV are the tabular mirror of the contamination and dedup problems that domain solves for pretraining corpora.
