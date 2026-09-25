---
tags: [concept, domain/neural-networks, level/surface]
aliases: [loss function, objective function, cost function, criterion, cross-entropy loss, MSE loss]
summary: "The objective a network minimizes and how it shapes gradients: CE vs MSE, label smoothing, reductions, and loss-at-init checks."
---

# Concept - Loss Functions for Neural Networks

> **One-paragraph hook:** Every gradient the network ever sees is the derivative of one scalar, the loss. It's the only channel from the task to the weights, and its *gradient shape* matters more than its value. Two losses that rank the same predictions identically can differ 100× in learning speed: one hands the optimizer a clean error signal, the other multiplies it by a saturating factor that vanishes when the model is most wrong.

## The mechanism

**Classification: cross-entropy.** For a target distribution $y$ (usually one-hot) and predicted probabilities $\hat{y}$ from a [[Concept - Softmax]]:

$$\mathcal{L}_{CE} = -\sum_i y_i \log \hat{y}_i$$

Minimizing it maximizes the log-likelihood of the correct class; the information-theoretic reading (code length under the wrong distribution) is in [[Concept - Entropy and Cross-Entropy]]. Differentiate through the softmax and the gradient with respect to the logits $z$ collapses to

$$\frac{\partial \mathcal{L}_{CE}}{\partial z} = \hat{y} - y$$

the raw prediction error, no extra factors. Confidently wrong gives a gradient magnitude near 1; correct gives near 0. That clean, well-scaled signal going into [[Concept - Backpropagation]] is why softmax+CE dominates classification, and why frameworks fuse them (`F.cross_entropy` = log-softmax + NLL in one numerically stable op).

### Why CE replaced MSE for classification

Squared error through a sigmoid output $\hat{y} = \sigma(z)$ has gradient

$$\frac{\partial}{\partial z}\,\tfrac{1}{2}(\hat{y}-y)^2 = (\hat{y}-y)\,\sigma'(z)$$

and $\sigma'(z) \le 0.25$, decaying to ~0 in the tails. A unit that is *saturated and wrong* ($\hat{y} \approx 0$ when $y = 1$) gets almost no gradient at the moment it needs the most. CE cancels the $\sigma'$ factor analytically, so learning stays fast even from badly wrong starts. The field switched for this mechanical reason, not out of empirical preference.

### Regression: MSE, MAE, Huber

MSE $(\hat{y}-y)^2$ is the maximum-likelihood loss under Gaussian noise. But its gradient grows linearly with the error, so one mislabeled outlier at 100× the typical scale contributes 10,000× the loss and yanks the model. MAE $|\hat{y}-y|$ caps the gradient at ±1. It's robust, but constant-magnitude gradients converge slowly near the optimum, and it's non-smooth at 0. Huber sits between them: quadratic within $\delta$ of the target, linear beyond. It's the standard compromise ($\delta = 1.0$ default). Value heads in RL and scalar [[Concept - Reward Models]] are regression heads, and their outlier behavior is a real training-stability lever.

### Label smoothing

Replace the hard target with $y_\text{smooth} = (1-\varepsilon)\,y + \varepsilon / C$, typically $\varepsilon = 0.1$ (Szegedy et al. 2016). Plain CE is only minimized as the correct logit $\to \infty$, so hard targets push logits to grow without bound. Smoothing gives a finite optimum, improves calibration, and adds a small accuracy bump on ImageNet-scale classification. The catch (Müller et al. 2019) is that it collapses the geometry of the penultimate layer: logit gaps between *incorrect* classes get erased. That measurably hurts when the model is a [[Concept - Knowledge Distillation]] teacher, because inter-class structure is what distillation transfers.

## In practice

| Task | Loss | Notes |
|---|---|---|
| Multi-class classification / next-token prediction | Softmax + CE (fused) | The default; per-token CE *is* LM pretraining |
| Multi-label / binary | BCE-with-logits | Fused sigmoid+CE for the same stability reasons |
| Regression, clean targets | MSE | ML estimate under Gaussian noise |
| Regression, outliers / heavy tails | Huber (or MAE) | Value heads, reward-model heads |
| Distribution matching (distillation, RLHF penalty) | [[Concept - KL Divergence]] | CE minus a constant when the target is fixed |

**Check loss at init first.** With random init and $C$ balanced classes, predictions are ~uniform, so CE $\approx \ln(C)$ at step 0: $\ln(1000) \approx 6.9$ for ImageNet, $\ln(50257) \approx 10.82$ for GPT-2's vocab. Do this *before* touching the model (step 1 of [[Playbook - Debugging a Neural Network That Won't Train]]). Too high means an init or logit-scale bug. Too low means label leakage or a degenerate batch. Sitting at $\ln(C)$ and never moving means a disconnected graph.

**Reduction is a hidden learning-rate knob.** `mean` vs `sum` vs per-token reduction rescales the gradient by batch size or sequence length, so the effective LR changes silently whenever either one does. The classic case is the SFT masked-loss token-count bug: dividing summed loss by *all* tokens instead of *unmasked* tokens shrinks gradients in proportion to how much of each sequence is masked. Mechanics in [[Concept - Loss Masking and Sequence Packing]]; it's also listed in [[Gotchas - Training Neural Networks]].

## Failure modes

- **Wrong loss at init.** Symptom: step-0 CE far from $\ln(C)$. Cause: label off-by-one, logits passed through an extra softmax (double-softmax), or wrong reduction. Fix before any architecture work.
- **Hand-rolled `log(softmax(x))`.** NaNs when a probability underflows to 0. Use the fused CE / log-sum-exp path.
- **Saturated sigmoid + MSE.** Loss stuck high, gradients ~0 despite gross errors. To detect, plot gradient norm vs error; it's flat where it should be large. Switch to CE/BCE-with-logits.
- **Reduction mismatch across code paths.** Loss magnitude jumps when batch size or sequence length changes, so cross-run comparisons are meaningless. Vary batch size 2× and confirm per-example loss doesn't move.
- **Label smoothing where structure matters.** Calibration improves, but distillation from the smoothed teacher regresses. Compare student quality from smoothed vs unsmoothed teachers.

## The non-obvious

You can't pick the loss and the optimizer separately. Reduction, masking and target smoothing all multiply into the gradient the same way a learning-rate change does, except *silently* and sometimes *per-example*. If a run behaves differently after a "harmless" data or batching change, audit the loss's denominator first. In practice more "optimizer mysteries" trace to the loss reduction than to the optimizer.

## Connections

- [[Concept - Softmax]] — the output map CE is fused with; the pair's clean $\hat{y}-y$ gradient is the whole reason for the pairing.
- [[Concept - Entropy and Cross-Entropy]] — the information-theoretic ground truth beneath the CE formula (down to why it's measured in nats).
- [[Concept - KL Divergence]] — CE's sibling: identical gradients when the target is fixed, and the loss of choice when matching soft distributions.
- [[Concept - Backpropagation]] — the loss's gradient is the seed value the entire backward pass propagates; loss shape = gradient shape everywhere.
- [[Concept - Reward Models]] — scalar reward/value heads are regression heads, where the MSE/Huber outlier tradeoff has training-stability consequences.
- [[Concept - Knowledge Distillation]] — soft-target CE/KL against a teacher; the Müller et al. label-smoothing caveat lives at this seam.
- [[Concept - Loss Masking and Sequence Packing]] — where the per-token reduction and token-count denominators become real SFT bugs.
- [[Gotchas - Training Neural Networks]] — the aggregated catalog where the reduction and masking pathologies from this note recur as war stories.
- [[Playbook - Debugging a Neural Network That Won't Train]] — operationalizes loss-at-init and the other checks here into a diagnostic procedure.

## Sources

- Szegedy et al. (2016) — Rethinking the Inception Architecture for Computer Vision. Introduced label smoothing ($\varepsilon = 0.1$).
- Müller et al. (2019) — When Does Label Smoothing Help? Showed it improves calibration but erases inter-class structure and hurts distillation teachers.
- Huber (1964) — Robust Estimation of a Location Parameter. The original robust loss interpolating MSE and MAE.
- Goodfellow, Bengio & Courville (2016) — *Deep Learning*, ch. 6. The standard treatment of why CE's gradient beats MSE's through saturating outputs.
