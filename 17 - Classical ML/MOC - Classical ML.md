---
tags: [moc, domain/classical-ml, level/surface]
aliases: []
summary: "Map of Classical ML: tree ensembles, gradient boosting, calibration, imbalance, time series, and classical text/causal methods."
---

# MOC - Classical ML

This domain owns the non-neural machine learning toolkit that still runs the majority of production tabular systems: decision trees and their ensembles (bagging, gradient boosting), the classical text representations (TF-IDF, word2vec) that predate transformer embeddings, statistical time series forecasting, and the evaluation disciplines — calibration, imbalanced-class handling, leakage-safe cross-validation, conformal prediction — that any model, neural or not, needs to be trustworthy in production. It matters because deep learning did not replace these methods on structured data: gradient-boosted trees (XGBoost, LightGBM) remain the default for anything under roughly a million rows, Kaggle spent a decade proving it empirically, and 2023-2026's TabPFN is the first serious neural challenger. The notes here run from the surface mechanics of a single decision tree, through the core additive-ensemble math of gradient boosting, into advanced production concerns — hyperparameter tuning, target-encoding leakage, calibration drift — and out to the frontier of in-context tabular transformers and distribution-free conformal guarantees. Read this domain whenever the problem is structured data, a small-to-mid-size dataset, or a baseline that needs to beat a fancier model before anyone gets to use the fancier model.

## Start here

- **Surface** → [[Concept - Decision Trees]] — recursive axis-aligned partitioning that greedily maximizes impurity decrease; the atomic learner every ensemble in this domain builds on.
- **Core** → [[Concept - Gradient Boosting]] — fitting an additive ensemble by gradient descent in function space, sequentially correcting residual errors with shallow trees.
- **Advanced** → [[Breakdown - XGBoost]] — the regularized, distributed, sparsity-aware systems paper that turned gradient boosting into the Kaggle default for a decade.
- **Frontier** → [[Breakdown - TabPFN]] — the transformer that classifies tabular data by in-context learning in one forward pass, the first credible neural challenger to GBTs.
- **Unicorn** → [[Lore - Kaggle and the Reign of Gradient Boosting]] — the tribal knowledge Kaggle grandmasters learned about CV discipline and leak-hunting years before papers caught up.

## Trees and ensembles: the tabular baseline

- [[Concept - Decision Trees]] — recursive axis-aligned partitioning that greedily maximizes impurity decrease; the atomic, high-variance learner every tree ensemble is built from.
- [[Concept - Bagging and Random Forests]] — variance reduction by averaging decorrelated trees trained on bootstrap resamples and random feature subsets.
- [[Concept - Gradient Boosting]] — fitting an additive ensemble by gradient descent in function space, sequentially correcting residual errors with shallow trees.

## Gradient boosting in production

- [[Breakdown - XGBoost]] — Chen & Guestrin's 2016 systems paper that turned gradient boosting into a regularized, distributed, sparsity-aware library and the Kaggle default for a decade.
- [[Breakdown - LightGBM]] — Microsoft's histogram-based GBDT (Ke et al. 2017), which used GOSS and EFB to out-train XGBoost on large data and won the M5 forecasting competition.
- [[Reference - Gradient Boosting Hyperparameters]] — cross-library map of the same tuning knob across XGBoost, LightGBM, and CatBoost: names, ranges, defaults, and what each controls.
- [[Playbook - Tuning Gradient Boosted Trees]] — the ordered, leak-checked procedure for tuning XGBoost/LightGBM/CatBoost from a baseline to a squeezed final model without fooling yourself.
- [[Gotchas - Gradient Boosting in Practice]] — the leakage, overfit, and calibration traps that make gradient-boosted-tree pipelines ace the notebook and fail in production.
- [[Snippet - Leakage-Free Target Encoding]] — out-of-fold, Bayesian-smoothed mean encoding that beats one-hot on trees without leaking the target.
- [[Decision - Deep Learning vs Gradient Boosting for Tabular Data]] — for tabular data under ~1M rows, gradient-boosted trees beat deep nets on accuracy, speed, and tuning cost — the default, with named exceptions.
- [[Breakdown - TabPFN]] — the transformer that classifies tabular data by in-context learning in one forward pass, no per-dataset training.

## Calibration, imbalance, and uncertainty

- [[Concept - Probability Calibration]] — making a classifier's scores mean P(y=1|score=p)=p, and the Platt/isotonic/temperature methods that enforce it after the fact.
- [[Concept - Learning from Imbalanced Data]] — why accuracy and ROC-AUC lie under class imbalance, and the threshold, cost-weighting, and resampling fixes — with the leakage trap that ruins them.
- [[Concept - Conformal Prediction]] — distribution-free prediction sets with finite-sample coverage that wrap any trained model.

## Time series

- [[Concept - Classical Time Series Forecasting]] — ARIMA/ETS and the Box-Jenkins workflow, the statistical forecasting toolkit that gradient boosting on lag features now usually beats.
- [[Concept - Time Series Cross-Validation and Leakage]] — validating temporal and financial models without leakage: forward-chaining, purging, embargo, and CPCV.

## Text representation and embeddings

- [[Concept - TF-IDF and the Bag of Words]] — sparse count-based text representation weighting terms by frequency and rarity; still a near-free, strong baseline for classification and retrieval.
- [[Concept - Word2Vec and the Embedding Lineage]] — how word2vec turned words into dense trainable vectors, why that's secretly matrix factorization, and what it seeded in every embedding since.

## Unsupervised learning and causal inference

- [[Concept - Clustering and Dimensionality Reduction]] — the core unsupervised toolkit for grouping and projecting unlabeled data, and the specific ways each method silently misleads you.
- [[Concept - Causal Inference Basics]] — estimating what an intervention causes, not just what correlates with it, when you cannot randomize — and why predictive ML alone can't do this.

## Lore: what Kaggle taught before the papers caught up

- [[Lore - Kaggle and the Reign of Gradient Boosting]] — how gradient-boosted trees conquered Kaggle and codified CV discipline, stacking, and leak-hunting years before papers validated them.

## Adjacent domains

- [[MOC - Evaluation]] — the calibration, imbalanced-class, and leakage-safe validation discipline this domain teaches on tabular models is the same discipline that domain applies to LLM evals.
- [[MOC - Retrieval & RAG]] — TF-IDF and word2vec are the direct ancestors of the dense embeddings that domain's retrieval stack depends on.
- [[MOC - Data Engineering]] — leakage-free target encoding and time series CV here are the tabular-data mirror of the contamination and dedup problems that domain solves for pretraining corpora.
