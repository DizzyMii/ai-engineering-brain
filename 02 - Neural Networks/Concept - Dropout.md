---
tags: [concept, domain/neural-networks, level/core]
aliases: [inverted dropout, MC-dropout, stochastic depth, DropPath]
summary: "Random unit masking with 1/(1-p) survivor scaling: a cheap ~2^n ensemble; ~0.1 in transformers, 0.0 in large-scale pretraining."
---

# Concept - Dropout
> **One-paragraph hook:** Dropout randomly zeroes units during training and does nothing at inference — three lines of code that act like training an exponential ensemble of subnetworks for free. It carried regularization in deep learning for a decade, then large-scale pretraining quietly turned it off: when you see each token once, the dataset does the regularizing. Knowing *when it's off and why* is now as important as knowing how it works.

## The mechanism

**Inverted dropout**, the modern standard: at train time, sample an elementwise mask $m \sim \mathrm{Bernoulli}(1-p)$ and scale the survivors by $1/(1-p)$ so the expected activation is preserved; at test time, do nothing.

```python
def dropout(x, p, training):
    if not training or p == 0.0:
        return x                      # inference: identity, zero cost
    mask = (torch.rand_like(x) > p).float()
    return x * mask / (1 - p)         # E[output] == x
```

The $1/(1-p)$ is not a nicety — it is the contract that makes train-time and test-time activation statistics match. The original formulation (Srivastava et al. 2014) instead scaled *weights* by $(1-p)$ at test time; inverting moved the cost into training and made inference a clean identity, which is why every framework does it this way now. **Forgetting the survivor scaling is a classic silent bug**: nothing errors, but every activation downstream of the dropout layer is $(1-p)\times$ smaller at inference than the network was trained to expect.

**Why it regularizes — two equivalent readings:**

1. **Ensemble view.** A network with $n$ droppable units defines $\sim 2^n$ weight-sharing subnetworks; each training step samples one and updates the shared weights. Test-time expectation-matching approximates averaging this exponential ensemble (exactly, for a single linear layer; approximately, in depth).
2. **Co-adaptation view.** A unit cannot rely on any specific other unit existing, so features must be individually useful rather than functioning only in fragile conspiracies. Formally, dropout acts as an adaptive noise penalty — for linear models it reduces to an L2-like penalty scaled by feature variance (Wager et al. 2013).

## In practice

- **Rates:** the original MLP-era recipe was $p=0.5$ on hidden layers, $p=0.2$ on inputs. CNNs use 0.1–0.5, though [[Breakdown - Batch Normalization]] displaced much of it in vision. Transformers ship ~0.1 on attention weights and residual-branch outputs — the original [[Deep Dive - The Transformer]] used 0.1 everywhere.
- **Large-model pretraining uses 0.0.** GPT-3-class and LLaMA-class runs train with no dropout: single-epoch training over trillions of tokens means there is no memorization pressure for it to fight, and it costs capacity in an underfitting regime. Dropout returns the moment data gets small again — fine-tuning configs (including LoRA dropout of 0.05–0.1) routinely re-enable it.
- **Train/eval switching:** dropout is one of the two modules (with BatchNorm) whose behavior `model.train()`/`model.eval()` flips — the mechanics and the bugs live in [[Concept - The Training Loop]].
- **Variants that matter:** DropConnect (Wan et al. 2013) masks weights instead of activations. Stochastic depth / DropPath (Huang et al. 2016) drops entire residual branches — making expected depth shallower during training — and is load-bearing for very deep ResNets and for ViT recipes (DeiT-style training uses drop-path ~0.1, often scaled linearly with depth); see [[Concept - Residual Connections]] and [[Concept - Vision Transformers]].

## Failure modes

- **Missing survivor scaling.** Symptom: eval metrics mysteriously worse than train dynamics suggest; activation magnitudes shift between train and eval. Cause: hand-rolled dropout without $1/(1-p)$. Detection: compare per-layer activation statistics in train vs eval mode on the same batch — they should match in expectation. Fix: use the framework op.
- **Dropout active at inference.** Symptom: nondeterministic predictions, degraded and noisy eval metrics. Cause: forgotten `model.eval()`. Detection: run the same input twice — outputs should be bit-identical; this and its siblings are cataloged in [[Gotchas - Training Neural Networks]].
- **The BatchNorm interaction.** Dropout before BatchNorm shifts the activation variance between train (units dropped) and eval (all units present), so BN's running statistics are calibrated for a distribution that no longer exists at eval — a measurable accuracy hit (Li et al. 2019). Fixes: put dropout after all BN layers, or don't mix them. LayerNorm-based transformers sidestep the issue because normalization statistics are computed per-token at both train and eval — see [[Concept - RMSNorm and LayerNorm]].
- **Regularizing before fitting.** Dropout left on while debugging a model that can't yet overfit a single batch masks the real bug. Turn it off first, make the model fit, then re-add.

## The non-obvious

Dropout doubles as a free uncertainty estimator. **MC-dropout** (Gal & Ghahramani 2016): keep dropout *on* at inference and average 20–50 stochastic forward passes — the spread of the predictions approximates Bayesian predictive uncertainty, because dropout training is (under their analysis) approximate variational inference. It's the cheapest uncertainty signal that requires zero changes to training, and it works on any already-trained dropout model. The catch practitioners hit: it's 20–50× inference cost, and on models trained with $p=0$ there is nothing to sample — another way the "pretraining turned dropout off" shift quietly removed a capability.

## Connections

- [[Concept - The Multilayer Perceptron]] — the host architecture dropout was invented for; masking units is masking MLP hidden features.
- [[Concept - Generalization in Deep Learning]] — dropout is an *explicit* regularizer, but the deep story is that implicit optimizer bias often does more of the work; dropout is neither necessary nor sufficient.
- [[Concept - The Training Loop]] — `model.train()`/`model.eval()` exists in large part because of dropout; ordering and mode bugs originate here.
- [[Breakdown - Batch Normalization]] — the other mode-switching layer, and dropout's worst interaction partner via the variance-shift effect.
- [[Concept - RMSNorm and LayerNorm]] — per-token normalization has no train/eval statistic mismatch, which is why transformers escape the dropout-BN pathology.
- [[Gotchas - Training Neural Networks]] — the aggregated catalog where dropout's mode and scaling bugs sit ranked among their peers.
- [[Concept - Residual Connections]] — stochastic depth drops whole residual branches, extending dropout's idea from units to layers.
- [[Concept - Vision Transformers]] — where DropPath is a standard, load-bearing training-recipe ingredient.
- [[Deep Dive - The Transformer]] — defined the ~0.1 attention/residual dropout convention that later large-scale pretraining abandoned.

## Sources

- Hinton et al. (2012) — "Improving neural networks by preventing co-adaptation of feature detectors." The original dropout preprint and the co-adaptation argument.
- Srivastava et al. (2014) — "Dropout: A Simple Way to Prevent Neural Networks from Overfitting." The JMLR paper: ensemble interpretation, rates, test-time scaling.
- Wan et al. (2013) — "Regularization of Neural Networks using DropConnect." The drop-weights variant.
- Wager et al. (2013) — "Dropout Training as Adaptive Regularization." The noise-penalty/L2 correspondence for linear models.
- Huang et al. (2016) — "Deep Networks with Stochastic Depth." Branch-level dropout that unlocked very deep ResNets.
- Gal & Ghahramani (2016) — "Dropout as a Bayesian Approximation." MC-dropout for predictive uncertainty.
- Li et al. (2019) — "Understanding the Disharmony between Dropout and Batch Normalization." The variance-shift mechanism.
