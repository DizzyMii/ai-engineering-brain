---
tags: [concept, domain/neural-networks, level/advanced]
aliases: [generalization puzzle, implicit regularization, flat minima]
summary: "Overparameterized nets can memorize noise yet generalize anyway — flat minima, SGD's implicit bias, and why capacity bounds fail."
---

# Concept - Generalization in Deep Learning

> **One-paragraph hook:** A modern network can memorize its entire training set, and will if you hand it random labels. Classical learning theory says such a model can't generalize. Empirically it does, and it gets better as it gets *bigger*. The answer lies in *which* of the many zero-training-error solutions the optimizer picks, so generalization turns out to be an optimization story: flat minima, gradient noise, norm and margin. That's why batch size, learning rate and optimizer choice double as regularizers.

## The mechanism

**Random labels broke the classical picture.** In "Understanding deep learning requires rethinking generalization" (Zhang et al. 2017), standard architectures (Inception on ImageNet, small CNNs on CIFAR-10) were trained on uniformly random labels and reached ~zero *training* error. Pure memorization, full capacity. The same networks trained on the true labels generalize well. Any capacity measure blind to the data and training procedure (VC dimension, Rademacher complexity of the full class) is vacuous here: the hypothesis class contains the memorizer, yet training on real data reliably doesn't return it. The paper's second result: turning off explicit regularizers (weight decay, dropout, augmentation) degrades test accuracy only modestly. In this regime explicit regularization is neither necessary nor sufficient for generalization.

**The optimizer's implicit bias picks the solution.** [[Concept - Stochastic Gradient Descent and Momentum]] doesn't sample uniformly from the zero-loss set. Its gradient noise (scale ~ LR/batch) makes sharp basins unstable, so the iterate bounces out of narrow minima and settles where the loss is locally flat and the weight norm low. In the cleanest tractable case, gradient descent on logistic regression over separable data provably converges to the max-margin solution with no regularizer in sight (Soudry et al. 2018). Much of deep learning's generalization comes from the optimizer, not the objective.

**Flat vs sharp minima.** The flatness story runs from Hochreiter & Schmidhuber (1997, "Flat Minima") to Keskar et al. (2017). Large-batch training (thousands per step) reduces gradient noise, lands in sharper minima, and pays a test-accuracy gap of a few percent against small-batch SGD at otherwise matched settings. Intuition: a flat minimum's loss barely moves under parameter perturbation, so the train→test shift costs little; a sharp minimum is brittle. The caveat is real. Dinh et al. (2017) showed flatness isn't reparameterization-invariant (you can rescale a ReLU net to make any minimum look sharp without changing its function), so naive sharpness is not a rigorous complexity measure. The link is contested in detail but holds up in practice: [[Concept - Sharpness-Aware Minimization]] optimizes for flatness directly and wins on vision benchmarks, and [[Concept - The Edge of Stability]] shows the learning rate itself pins the curvature the model settles at ($\lambda_{\max} \approx 2/\eta$), which turns LR into a de facto flatness dial.

**Better capacity measures.** Effective capacity isn't parameter count. Norm- and margin-based bounds, e.g. the spectrally-normalized margin bounds of Bartlett et al. (2017), track generalization across models far better than VC-style counting. They measure the function the net learned, not the largest one it could represent, and under that lens bigger models kept well-regularized by training aren't paradoxical.

**The overparameterized regime.** Past the interpolation threshold (model just big enough to fit the training set exactly), test error can *fall again* as parameters grow. That's [[Concept - Double Descent]] (Belkin et al. 2019), and it inverts the classical U-curve: more capacity gives the implicit bias more room to find smooth interpolants. It's the theoretical backdrop for [[Concept - Scaling Laws]]. In the modern regime, bigger models generalize better, predictably.

## In practice

- **Batch size is a regularization knob.** Scaling batch up without compensating (LR scaling + warmup, per Goyal et al. 2017) costs test accuracy via the sharp-minima route. If you must run huge batches, expect to retune the LR schedule and possibly add explicit flatness pressure (SAM).
- **LLM pretraining barely uses explicit regularizers.** [[Concept - Dropout]] is typically 0.0, and weight decay ~0.1 serves optimization as much as regularization. With single-epoch training over trillions of tokens, the classical overfitting regime (many passes over small data) never arrives. Data scale *is* the regularizer.
- **Optimizer choice leaks into generalization.** The decade of vision folklore that Adam generalizes worse than SGD (mostly a decoupled-weight-decay artifact, partly real flat-minima effect) is chronicled in [[Lore - The Adam vs SGD Generalization Wars]].
- **Diagnostics:** track the train–val gap over the whole run, not only at the end. A model that fits train fast while val lags may still end up generalizing well (see grokking below). A val curve that *worsens* while train improves in a multi-epoch setting is the classical signal to add data or regularization.

## Failure modes

- **Memorization of duplicates and outliers:** even a well-generalizing LLM memorizes text it saw many times. Deduplication is a generalization intervention as well as a data-hygiene one.
- **Grokking:** train accuracy hits 100% while validation sits at chance for thousands of steps, then generalization arrives suddenly ([[Concept - Grokking]]). Early-stop on val at step 10k and you'd conclude the model "memorized"; patience and weight decay were what was missing.
- **Large-batch degradation:** test accuracy silently drops after a batch increase made for throughput. Detection: A/B the batch change at matched compute and tuned LR before blaming the gap on anything else.
- **IID overconfidence:** everything above is about generalization to the *same distribution*. A clean val score says nothing about shift. The val set describes the past, not the deployment.

## The non-obvious

When a deep model overfits, reaching for dropout or weight decay is usually the *lowest*-leverage response. Zhang et al.'s ablations showed explicit regularizers contribute marginally. The implicit bias of training (LR schedule, batch size, gradient noise, early stopping) and above all data quantity and quality do most of the work. Practitioners learn the ordering the hard way: fix the data, then the optimization recipe, then explicit regularizers. It also clears up a newcomer puzzle. Models with 100× more parameters than training examples that generalize fine aren't violating theory. They show that the relevant "capacity" is a property of the training *trajectory*, not the architecture diagram. The geometry agrees: distinct SGD solutions are typically connected by low-loss curves ([[Concept - Mode Connectivity and Flat Minima]]), so training explores a broad, flat, connected basin instead of isolated needle minima.

## Connections

- [[Concept - Stochastic Gradient Descent and Momentum]] — the source of the gradient noise whose implicit bias does most of the regularizing.
- [[Concept - Dropout]] — the canonical explicit regularizer, and Exhibit A for "helpful but neither necessary nor sufficient."
- [[Concept - Double Descent]] — the overparameterized regime where more parameters reduce test error past the interpolation threshold.
- [[Concept - Grokking]] — the extreme case of delayed generalization: memorization first, understanding thousands of steps later.
- [[Concept - Scaling Laws]] — the empirical face of modern generalization: predictable test-loss improvements with scale.
- [[Concept - Sharpness-Aware Minimization]] — the method that turns the flat-minima hypothesis into an explicit training objective.
- [[Concept - The Edge of Stability]] — the mechanism coupling learning rate to curvature, making LR an implicit flatness control.
- [[Concept - Mode Connectivity and Flat Minima]] — the loss-landscape geometry (connected low-loss basins) underpinning the flatness picture.
- [[Lore - The Adam vs SGD Generalization Wars]] — the decade-long practitioner fight over optimizer-dependent generalization and its AdamW resolution.

## Sources

- Zhang et al. (2017) — Understanding deep learning requires rethinking generalization. Random-label memorization; explicit regularizers ablated.
- Keskar et al. (2017) — On Large-Batch Training for Deep Learning. The large-batch/sharp-minima generalization gap.
- Hochreiter & Schmidhuber (1997) — Flat Minima. The original flatness-generalization argument.
- Dinh et al. (2017) — Sharp Minima Can Generalize For Deep Nets. The reparameterization critique of naive sharpness.
- Bartlett et al. (2017) — Spectrally-normalized margin bounds for neural networks. Norm/margin capacity that actually correlates.
- Soudry et al. (2018) — The Implicit Bias of Gradient Descent on Separable Data. Provable max-margin selection with no regularizer.
- Belkin et al. (2019) — Reconciling modern machine-learning practice and the classical bias–variance trade-off. Double descent.
- Goyal et al. (2017) — Accurate, Large Minibatch SGD. The LR-scaling + warmup recipe that closes most of the large-batch gap.
