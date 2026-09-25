---
tags: [moc, domain/foundations, level/surface]
aliases: []
summary: "Map of the math substrate under every model: linear algebra, probability, statistics, optimization geometry, floating-point numerics."
---

# MOC - Foundations

This domain owns the math and numerics the rest of the vault builds on: the linear algebra that turns a forward pass into a chain of GEMMs, the probability and information theory behind every loss function, the statistics that separate a real result from noise, and the floating-point arithmetic the hardware actually runs. Failures here are silent and expensive. An ill-conditioned matrix, a KL estimator with the wrong sign convention, or an fp16 gradient that flushes to zero shows up three domains downstream as mysterious training instability, with no error at the source. Other domains take these mechanisms as given. Here you learn why they hold, what their assumptions cost, and how they break.

## Start here

- **Surface** → [[Concept - Vector Norms and Distances]] — the measuring sticks (Lp norms, cosine similarity, spectral norm) that every other note in this vault assumes you know.
- **Core** → [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — every dense layer, attention op and convolution lowers to GEMM, so this is the cost model for the rest of AI engineering.
- **Advanced** → [[Concept - The Condition Number]] — one number that sets both how much a linear solve amplifies numerical error and how fast gradient descent converges.
- **Frontier** → [[Concept - The Hessian Spectrum in Deep Learning]] — the active-research view of the loss surface: a near-zero eigenvalue bulk plus a few outliers that your learning rate ends up obeying.
- **Unicorn** → [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — the war story behind today's mixed-precision training recipe.

## Linear algebra

- [[Concept - Vector Norms and Distances]] — Lp and matrix norms and the distances built from them: what each measures, where it's used, and how each misleads.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — 2mnk FLOPs and arithmetic intensity: the arithmetic behind deep learning's compute cost model.
- [[Concept - Singular Value Decomposition]] — every matrix is rotation → axis scaling → rotation; the scaling factors explain PCA, spectral norms, low-rank compression, and LoRA.
- [[Concept - The Condition Number]] — how much a linear solve amplifies numerical error, and why it also predicts gradient descent's convergence rate.
- [[Decision - Choosing a Matrix Factorization]] — Cholesky for SPD solves, LU for general square, QR for least squares, SVD for rank/stability; never form an explicit inverse.

## Probability and information theory

- [[Concept - Entropy and Cross-Entropy]] — entropy is optimal code length; cross-entropy = entropy + KL is the language-model loss; perplexity and bits-per-byte are its exchange rates.
- [[Concept - KL Divergence]] — the asymmetric gap between distributions: forward KL covers modes (MLE), reverse KL seeks them (RLHF), and estimating it well is subtle.
- [[Concept - Maximum Likelihood Estimation]] — every standard loss is a negative log-likelihood under an assumed noise model; choosing the loss is choosing that assumption.

## Statistics and experimentation

- [[Concept - Hypothesis Testing and p-values]] — how to tell if an observed difference is real or noise, and the ways p-values get misread in eval and A/B work.
- [[Playbook - Running a Statistically Valid Experiment]] — pre-register, power the test, pick the right statistic, don't peek, correct for multiplicity, report effect size and CI.

## Optimization geometry

- [[Concept - Convexity and the Loss Landscape]] — why non-convex deep learning losses are reliably trainable: saddle-point geometry, SGD noise, and mode connectivity between minima.
- [[Concept - The Hessian Spectrum in Deep Learning]] — a near-zero eigenvalue bulk plus a few outliers, and why λ_max is set by your learning rate rather than the reverse.

## High-dimensional geometry

- [[Concept - The Geometry of High-Dimensional Spaces]] — distances concentrate, random vectors go near-orthogonal, and volume flees to the shell: why 3D intuition dies above d~100.

## Floating point and numerical computation

- [[Concept - Floating Point for Deep Learning]] — how IEEE-754 formats trade exponent range against mantissa precision, and why bf16's fp32-range exponent won deep learning training.
- [[Reference - Floating Point Formats]] — lookup table of bit layout, dynamic range, precision, and memory cost for every floating-point format used in modern deep learning.
- [[Breakdown - bfloat16]] — reverse-engineering Google's 16-bit brain float: 8 exponent / 7 mantissa bits, why range beat precision, and how it killed loss scaling.
- [[Concept - Subnormal Numbers and Gradual Underflow]] — the IEEE-754 arcana that bites DL: subnormals, the flush-to-zero cliff, signed zero, and NaN semantics that can stall training without an error.
- [[Snippet - The Log-Sum-Exp Trick]] — compute log-sum-exp, log-softmax, and cross-entropy from logits without overflow: subtract the max, stay in log-space.
- [[Gotchas - Numerical Stability]] — how floating-point arithmetic corrupts a run without warning (overflow, cancellation, log(0), flushed gradients) and how to catch each early.
- [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — how fp16's 5-bit exponent nearly killed low-precision training, the loss-scaling hack that saved it, and the bf16 ending.
- [[Lore - The Nondeterminism of Floating-Point Reductions]] — identical code on identical hardware doesn't reproduce bit-for-bit, because parallel float reductions sum in scheduler-dependent order.

## Adjacent domains

- [[MOC - Neural Networks]] — backprop, the training loop, and every optimizer and normalization layer are this domain's calculus, linear algebra, and numerics put to work.
- [[MOC - Training at Scale]] — the floating-point formats and numerical-stability failure modes here become distributed-training decisions (loss scaling, reduction order, mixed precision) at scale.
- [[MOC - Evaluation]] — hypothesis testing and experiment design here are the statistical discipline that keeps eval and benchmark claims honest.
- [[MOC - Classical ML]] — MLE and SVD/PCA here are the estimation and dimensionality-reduction machinery classical models are built on.
