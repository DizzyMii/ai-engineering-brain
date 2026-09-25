---
tags: [concept, domain/data-engineering, level/frontier]
aliases: [DoReMi, data mixing laws, RegMix]
summary: "Replacing hand-tuned pretraining mixture weights with optimized ones - DoReMi's minimax reweighting or fitted mixing laws - and why they often fail to transfer to scale."
---

> **One-paragraph hook:** [[Concept - Data Mixtures]] covers what a mixture *is*. This note is about how to stop guessing its weights by hand. DoReMi and data mixing laws both try to turn "how much web vs. code vs. books" from an art practiced by senior researchers into an optimization problem you solve at small scale and transfer up. Both work well enough to be interesting and unreliably enough that most frontier labs still keep a human in the loop.

## The mechanism

**DoReMi** (Xie et al. 2023) frames mixture selection as **distributionally robust optimization**. Train a small *reference* model on a baseline mixture to get a per-domain loss target $\ell_i^{ref}$. Then train a small *proxy* model whose sampling weights $\alpha$ are updated online toward the domains where the proxy is currently doing worst relative to that reference, using a Group-DRO-style multiplicative-weights update:

$$\alpha_i \leftarrow \alpha_i \cdot \exp\!\big(\eta \,(\ell_i(\theta_{proxy}) - \ell_i^{ref})\big), \qquad \alpha \leftarrow \alpha / \|\alpha\|_1$$

The objective is **minimax**: it minimizes *worst-case* excess loss across domains instead of average loss. So the resulting weights frequently **down-weight the largest domain** (raw web) and **up-weight domains an average-loss objective would underserve**, the small, high-value ones that get drowned out under naive proportional sampling. The optimized $\alpha$ from the small proxy run then becomes the mixture for the full-scale run.

**Data Mixing Laws** (Ye et al. 2024) are more empirical. Fit a predictive function relating loss to mixture proportions $r$,

$$L(r) \approx c + \sum_i k_i \, e^{-t_i r_i}$$

by training a handful of small models on different mixtures and regressing loss against proportion. Once fit, the law *predicts* the loss of any untested mixture, ideally including the optimal one, without training it. Mixture search becomes optimization over a cheap fitted surface instead of a search over expensive training runs. **RegMix** and related proxy-model methods have the same shape: train many tiny models on randomly sampled mixtures, regress downstream loss on composition, extrapolate the optimum. They cost less than DoReMi's online reweighting loop.

## In practice

On The Pile, DoReMi reached the reference model's baseline perplexity roughly **2.6x faster** in training steps and improved average downstream accuracy over the hand-tuned baseline mixture. That's a real result on a real benchmark suite. Mixing laws appeal because they decouple "how many mixtures do I need to try" from "how many do I need to train at full scale": fit the curve on cheap small runs and read off a prediction. It's the same idea as using [[Concept - Scaling Laws]] to predict large-model loss from small-model trends without repeatedly training the large model.

## Failure modes

The big caveat for all of these methods is **the transfer problem**. Mixtures optimized on a small proxy with a modest token budget don't reliably transfer to a much larger model trained on a much larger budget. DoReMi's own gains are sensitive to the reference model and to how finely domains are split (coarse vs. fine-grained definitions give different optimized weights for the "same" data). Several replication attempts have reported weak or even negative transfer at scale. This is contested and only weakly sourced in public writeups (folklore, weakly sourced: practitioners report DoReMi-style weights occasionally underperforming a simple hand-tuned mixture once scaled up, though clean published negative results are rarer than the positive ones). The failure to watch for in practice is trusting a proxy-optimized mixture blind at full scale, with no ablation checkpoint partway through the real run.

## The non-obvious

For all the machinery, **most frontier labs as of 2026 still hand-tune and ablate mixtures**. They treat DoReMi-style and mixing-law outputs as a *prior* to consult, not a final answer, with the same scale-transfer skepticism that governs [[Concept - Data Curriculum and Ordering]]. What I find interesting about DoReMi is less the better weights and more that a minimax objective disagrees with proportional-to-size sampling by design. It will deliberately starve your biggest domain if the model already finds that domain easy, which is a different lens on mixture design from an engineer eyeballing token counts.

## Connections
- [[Concept - Data Mixtures]] — the base concept this note automates; learned mixing replaces hand-tuned weights with an optimization procedure.
- [[Concept - Scaling Laws]] — mixing laws borrow the same "fit small, predict large" methodology, and inherit the same extrapolation risk.
- [[Concept - KL Divergence]] — DoReMi's reweighting is a distributionally-robust variant of minimizing worst-case divergence from a reference loss distribution across domains.
- [[Concept - Data Curriculum and Ordering]] — a sibling frontier problem (order and repetition) with the identical small-scale-doesn't-transfer failure mode.
- [[Deep Dive - The Pretraining Data Pipeline]] — mixture weighting is one stage in that pipeline, applied just before the final shuffle.
- [[Concept - The Data-Centric View of Model Quality]] — learned mixing is one concrete instance of the broader thesis that curation, not architecture, is the quality lever.
- [[Concept - Data-Constrained Scaling Laws]] — the token-budget-limited regime in which choosing the right mixture (and repetition schedule) matters most.
- [[Gotchas - Pretraining Data Pipelines]] — where the transfer-problem failure mode shows up operationally: a mixture that looked great on a proxy, degrading results at full scale.

## Sources
- Xie et al. (2023) — DoReMi: Optimizing Data Mixtures Speeds Up Language Model Pretraining. Introduced the minimax/Group-DRO reweighting algorithm and the 2.6x convergence-speed result on The Pile.
- Ye et al. (2024) — Data Mixing Laws: Optimizing Data Mixtures by Predicting Language Modeling Performance. Introduced the fitted exponential functional form relating mixture proportion to loss.
