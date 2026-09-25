---
tags: [concept, domain/neural-networks, level/core]
aliases: [inverted dropout, MC-dropout, stochastic depth, DropPath]
summary: "Random unit masking with 1/(1-p) survivor scaling: a cheap ~2^n ensemble; ~0.1 in transformers, 0.0 in large-scale pretraining."
---

# Concept - Dropout
> **One-paragraph hook:** Dropout randomly zeroes units during training and does nothing at inference. Three lines of code buy you an exponential ensemble of subnetworks for free. It carried regularization in deep learning for a decade, then large-scale pretraining turned it off: when you see each token once, the dataset does the regularizing. Knowing *when it's off and why* now matters as much as knowing how it works.

## The mechanism

Inverted dropout is the modern standard. At train time, sample an elementwise mask $m \sim \mathrm{Bernoulli}(1-p)$ and scale the survivors by $1/(1-p)$ so the expected activation is preserved. At test time, do nothing.

```python
def dropout(x, p, training):
    if not training or p == 0.0:
        return x                      # inference: identity, zero cost
    mask = (torch.rand_like(x) > p).float()
    return x * mask / (1 - p)         # E[output] == x
```

The $1/(1-p)$ is the contract that makes train-time and test-time activation statistics match. The original formulation (Srivastava et al. 2014) scaled *weights* by $(1-p)$ at test time instead; inverting moved the cost into training and made inference an identity, so every framework does it this way now. **Forgetting the survivor scaling is a classic silent bug**: nothing errors, but every activation downstream of the dropout layer is $(1-p)\times$ smaller at inference than the network was trained to expect.

Two equivalent readings of why it regularizes:

1. **Ensemble view.** A network with $n$ droppable units defines $\sim 2^n$ weight-sharing subnetworks. Each training step samples one and updates the shared weights. Test-time expectation-matching approximates averaging this exponential ensemble (exactly for a single linear layer, approximately in depth).
2. **Co-adaptation view.** A unit can't count on any specific other unit existing, so each feature has to be useful on its own, outside fragile conspiracies. Formally, dropout acts as an adaptive noise penalty; for linear models it reduces to an L2-like penalty scaled by feature variance (Wager et al. 2013).

## In practice

- **Rates:** the original MLP-era recipe was $p=0.5$ on hidden layers and $p=0.2$ on inputs. CNNs use 0.1–0.5, though [[Breakdown - Batch Normalization]] displaced much of it in vision. Transformers ship ~0.1 on attention weights and residual-branch outputs; the original [[Deep Dive - The Transformer]] used 0.1 everywhere.
- **Large-model pretraining uses 0.0.** GPT-3-class and LLaMA-class runs train with no dropout. Single-epoch training over trillions of tokens leaves no memorization pressure to fight, and in an underfitting regime it just costs capacity. Once data gets small again it comes back: fine-tuning configs (including LoRA dropout of 0.05–0.1) routinely re-enable it.
- **Train/eval switching:** dropout is one of the two modules (with BatchNorm) whose behavior `model.train()`/`model.eval()` flips. The mechanics and the bugs are in [[Concept - The Training Loop]].
- **Variants worth knowing:** DropConnect (Wan et al. 2013) masks weights instead of activations. Stochastic depth / DropPath (Huang et al. 2016) drops entire residual branches, which makes expected depth shallower during training. Very deep ResNets and ViT recipes depend on it (DeiT-style training uses drop-path ~0.1, often scaled linearly with depth); see [[Concept - Residual Connections]] and [[Concept - Vision Transformers]].

## Failure modes

- **Missing survivor scaling.** Symptom: eval metrics worse than train dynamics suggest; activation magnitudes shift between train and eval. Cause: hand-rolled dropout without $1/(1-p)$. Detection: compare per-layer activation statistics in train vs eval mode on the same batch; they should match in expectation. Fix: use the framework op.
- **Dropout active at inference.** Symptom: nondeterministic predictions, degraded and noisy eval metrics. Cause: forgotten `model.eval()`. Detection: run the same input twice and the outputs should be bit-identical. This one and its siblings are cataloged in [[Gotchas - Training Neural Networks]].
- **The BatchNorm interaction.** Dropout before BatchNorm shifts the activation variance between train (units dropped) and eval (all units present). BN's running statistics are then calibrated for a distribution that doesn't exist at eval, a measurable accuracy hit (Li et al. 2019). Fixes: put dropout after all BN layers, or don't mix them. LayerNorm-based transformers avoid the issue because normalization statistics are computed per-token at both train and eval (see [[Concept - RMSNorm and LayerNorm]]).
- **Regularizing before fitting.** Leaving dropout on while debugging a model that can't yet overfit a single batch hides the real bug. Turn it off, get the model to fit, then add it back.

## The non-obvious

Dropout doubles as a free uncertainty estimator. With **MC-dropout** (Gal & Ghahramani 2016) you keep dropout *on* at inference and average 20–50 stochastic forward passes. The spread of the predictions approximates Bayesian predictive uncertainty, because dropout training is (under their analysis) approximate variational inference. It's the cheapest uncertainty signal that needs zero changes to training, and it works on any already-trained dropout model. The catch: it costs 20–50× inference, and a model trained with $p=0$ has nothing to sample. So when pretraining turned dropout off, this capability went with it.

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
