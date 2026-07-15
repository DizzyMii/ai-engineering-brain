---
tags: [concept, domain/data-engineering, level/frontier]
aliases: [DoReMi, data mixing laws, RegMix]
summary: "Replacing hand-tuned pretraining mixture weights with optimized ones - DoReMi's minimax reweighting or fitted mixing laws - and why they often fail to transfer to scale."
---

> **One-paragraph hook:** [[Concept - Data Mixtures]] describes what a mixture *is*; this note is about how to stop guessing its weights by hand. DoReMi and data mixing laws both try to turn "how much web vs. code vs. books" from an art practiced by senior researchers into an optimization problem you can solve at small scale and transfer up — and both work well enough to be interesting, and unreliably enough that most frontier labs still keep a human in the loop.

## The mechanism

**DoReMi** (Xie et al. 2023) frames mixture selection as **distributionally robust optimization**. Train a small *reference* model on some baseline mixture to get a per-domain loss target $\ell_i^{ref}$. Then train a small *proxy* model whose data-sampling weights $\alpha$ are updated online to chase the domains where the proxy is currently doing worst relative to that reference — a Group-DRO-style multiplicative-weights update:

$$\alpha_i \leftarrow \alpha_i \cdot \exp\!\big(\eta \,(\ell_i(\theta_{proxy}) - \ell_i^{ref})\big), \qquad \alpha \leftarrow \alpha / \|\alpha\|_1$$

This is a **minimax** objective: it minimizes the *worst-case* excess loss across domains rather than the average loss, which is why the resulting weights frequently **down-weight the largest domain** (raw web) and **up-weight domains where a plain average-loss objective would underserve them** — small, high-value domains that get drowned out under naive proportional sampling. The optimized $\alpha$ from the small proxy run is then transferred as the mixture for the full-scale training run.

**Data Mixing Laws** (Ye et al. 2024) take a different, more empirical route: fit a predictive function relating loss to mixture proportions $r$,

$$L(r) \approx c + \sum_i k_i \, e^{-t_i r_i}$$

by training a handful of small models on different mixtures and regressing loss against proportion. Once fit, the law lets you *predict* the loss of an arbitrary untested mixture — including, ideally, the optimal one — without training it, turning mixture search into optimization over a cheaply-fitted surface instead of a search over expensive training runs. **RegMix** and related proxy-model methods follow the same shape: train many tiny models on randomly sampled mixtures, regress downstream loss on mixture composition, and extrapolate the optimum, at lower cost than DoReMi's online reweighting loop.

## In practice

On The Pile, DoReMi reached the reference model's baseline perplexity roughly **2.6x faster** in training steps and improved average downstream accuracy versus the hand-tuned baseline mixture — a real result on a real benchmark suite, not a toy demonstration. The mixing-laws approach is attractive precisely because it decouples "how many mixtures do I need to try" from "how many of them do I need to train at full scale" — you fit the curve on cheap small runs and read off a prediction, similar in spirit to how [[Concept - Scaling Laws]] let you predict large-model loss from small-model trends without training the large model repeatedly.

## Failure modes

The load-bearing caveat for all of these methods is **the transfer problem**: mixtures optimized on a small proxy model and a modest token budget do not reliably transfer to a much larger model trained on a much larger token budget. DoReMi's own reported gains are sensitive to the choice of reference model and to how finely domains are split (coarse vs. fine-grained domain definitions give different optimized weights for the "same" data). Several replication attempts have reported weak or even negative transfer at scale — this is contested and only weakly sourced in public writeups (folklore, weakly sourced: practitioners report DoReMi-style weights occasionally underperforming a simple hand-tuned mixture once scaled up, though clean published negative results are rarer than the positive ones). The practical failure mode to watch for is trusting a proxy-optimized mixture blind at full scale without an ablation checkpoint partway through the real run.

## The non-obvious

Despite the machinery, **most frontier labs as of 2026 still hand-tune and ablate mixtures**, treating DoReMi-style and mixing-law outputs as a *prior* to consult rather than a final answer to trust — the same scale-transfer skepticism that governs [[Concept - Data Curriculum and Ordering]] decisions. The interesting part of DoReMi isn't "the optimizer found better weights," it's that a minimax objective structurally *disagrees* with naive proportional-to-size sampling by design — it will deliberately starve your biggest domain if that domain is already easy for the model, which is a genuinely different lens on mixture design than an engineer eyeballing token counts.

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
