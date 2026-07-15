---
tags: [lore, domain/neural-networks, level/unicorn]
aliases: [Adam vs SGD, adaptive gradient generalization gap, SWATS, marginal value of adaptive methods]
summary: "The decade-long fight over whether adaptive optimizers generalize worse than SGD, and how AdamW plus scale mostly ended it."
---

# Lore - The Adam vs SGD Generalization Wars

> **The fight:** for roughly five years the field believed [[Concept - Adam and AdamW|Adam]] trained faster but *generalized worse* than plain [[Concept - Stochastic Gradient Descent and Momentum|SGD]]. Vision stayed on SGD to keep its ImageNet numbers; NLP shrugged and used Adam anyway. Then AdamW showed a large chunk of the "gap" was a mis-implemented regularizer, and the arrival of transformers everywhere made the argument moot. The residue — a flat-minima intuition and a piece of folklore that "transformers just can't use SGD" — is still load-bearing in how people reason about optimizers today.

## What happened

By 2016 there were two tribes with two optimizers. Computer vision trained ResNets on ImageNet with **SGD + momentum**: learning rate ~0.1, momentum 0.9, weight decay 1e-4, a hand-tuned step-decay schedule. NLP and the brand-new transformer trained with **Adam**. Nobody thought much about it until the numbers started disagreeing.

The opening shot was **Wilson et al. 2017 — "The Marginal Value of Adaptive Gradient Methods in Machine Learning"** (NeurIPS). Its claim was pointed: adaptive methods (Adam, RMSProp, Adagrad) find solutions that *test* worse than SGD, even on problems where they reach a *lower training loss*. On several vision and language tasks, a well-tuned SGD matched or beat a well-tuned Adam on held-out data. The paper's rhetorical weapon was that the adaptive methods looked good only because people compared badly-tuned SGD against out-of-the-box Adam. The practitioner takeaway hardened into dogma: *if you want the best test accuracy, use SGD; Adam is for convenience.*

The fallout was visible on leaderboards. ImageNet state-of-the-art stayed on SGD + momentum for years. It also produced one of the great tell-tale hacks of the era: **SWATS (Keskar & Socher 2017 — "Improving Generalization Performance by Switching from Adam to SGD")**. The recipe is exactly what the name says — start on Adam to get the fast early descent, then *switch to SGD* partway through once a trigger fires, to collect SGD's supposedly-flatter endpoint. People genuinely shipped this. A hybrid optimizer whose entire reason to exist is a belief about generalization is about as clear an artifact of the folklore as you can get.

Meanwhile NLP never joined the war, because SGD simply did not work on transformers. The original transformer (Vaswani et al. 2017) trained with Adam under the "Noam" schedule — linear warmup then inverse-square-root decay — and every descendant (BERT, GPT-2, GPT-3) used Adam or AdamW. Attempts to train a transformer language model with SGD stalled or diverged. So the two camps talked past each other: vision *chose* SGD for the last point of accuracy; NLP *had no choice* but Adam.

**The plot twist was AdamW (Loshchilov & Hutter, arXiv 2017 → ICLR 2019 — "Decoupled Weight Decay Regularization").** Their observation: the "weight decay" everyone ran inside Adam was actually L2 regularization, added as $\lambda\theta$ *to the gradient* — so it flowed through the second-moment EMA and got divided by $\sqrt{\hat v}$. Parameters with a large gradient history received *less* shrinkage, inverting the regularizer's intent and coupling its strength to the loss landscape. Decouple the decay — apply $\lambda\theta$ directly to the weights, outside the adaptive machinery — and much of Adam's reported generalization deficit disappears. A large fraction of "Adam generalizes worse" was really "Adam + L2 is a broken weight-decay implementation." That reframed the entire debate: the confound Wilson et al. hadn't controlled for was the *decay coupling*, not the adaptivity.

Why NLP genuinely needs the adaptive preconditioner became clearer later. Transformer gradients are pathological for a single global step size: token [[Concept - Embeddings as Learned Representations|embeddings]] produce *sparse, heavy-tailed* gradients (a given token appears in a handful of examples per batch); [[Concept - RMSNorm and LayerNorm|LayerNorm]] gains, attention projections, and FFN weights live at wildly different gradient scales; and the loss landscape's condition number is enormous. **Zhang et al. 2020 — "Why are Adaptive Methods Good for Attention Models?"** (NeurIPS) argued the culprit is heavy-tailed gradient noise from class/token imbalance, and showed that *gradient clipping* lets SGD partially close the gap — evidence that the adaptivity was compensating for tail behavior, not magic. **Zhang et al. 2024 — "Why Transformers Need Adam: A Hessian Perspective"** pushed further, attributing it to *block heterogeneity*: the Hessian's spectrum differs sharply across parameter blocks in a transformer, and a single SGD learning rate cannot serve all of them at once, whereas Adam's per-coordinate scaling can.

The cleanest confirmation that the split was about *architecture, not modality* came when vision itself switched architectures. The [[Concept - Vision Transformers|Vision Transformer]] (Dosovitskiy et al. 2021) is trained with **AdamW**, not SGD — the moment CNNs gave way to transformers in vision, vision moved to Adam too. The dividing line was never "images vs text"; it was "convolutional inductive bias vs attention's gradient statistics."

Resolution *(as of 2026)*: **AdamW is the universal default for anything transformer-shaped.** SGD + momentum survives in pockets of CNN classification and some fine-tuning regimes where it's cheaper and good enough. The "Adam generalizes worse" claim is now read mostly as a weight-decay artifact. But the war left residue: the flat-minima intuition — that SGD's gradient noise biases it toward flatter, better-generalizing basins (see [[Concept - Generalization in Deep Learning]]) — never fully died. It stopped being *decision-relevant* at [[Concept - Scaling Laws|frontier scale]] only because there you have no alternative to Adam-family preconditioning, so the question quietly retired undecided rather than resolved.

## The lesson

- **Benchmarking an optimizer conflates it with its regularization coupling.** The Wilson et al. result was real *as measured*, but the measurement baked in a broken weight-decay implementation. AdamW didn't refute the experiment; it removed the confound and most of the effect went with it. When an "A is worse than B" result depends on a shared implementation detail, fix the detail before believing the ranking.
- **Whether you *need* an adaptive optimizer is a property of your gradients, not your task.** Sparse, heavy-tailed, block-heterogeneous gradients (embeddings, norm layers, attention) demand per-coordinate scaling; smooth, homogeneous CNN gradients do not. "Vision uses SGD, NLP uses Adam" was a proxy for a gradient-statistics fact, which is why it flipped the instant vision adopted transformers.
- **The reason Adam won at scale isn't generalization at all — it's learning-rate transfer.** Because $\hat m/\sqrt{\hat v} \approx \pm 1$ per coordinate, Adam's update is roughly bounded by $\eta$ regardless of gradient magnitude (smoothed sign descent), so a good LR transfers across model sizes. SGD's step scales with raw gradient magnitude, so its LR does not. At billion-parameter scale, where you cannot afford to re-sweep, that alone settles the choice.

## Evidence status

**Well-sourced.** The papers are real and uncontroversial: Wilson et al. 2017, Keskar & Socher 2017 (SWATS), Loshchilov & Hutter 2019 (AdamW), Zhang et al. 2020 and 2024. The historical pattern — ImageNet SOTA on SGD, transformers/NLP on Adam, ViT on AdamW — is documented in the papers' own training configs.

**Folklore layer, directionally true.** "Transformers just can't use SGD" is what practitioners experienced and is the everyday shorthand, but "can't" is too strong: SGD + clipping narrows the gap (Zhang et al. 2020), and the failure is a matter of degree and tuning cost, not a theorem. Nobody trains a frontier model with SGD because there is no upside, not because it's provably impossible.

**Contested.** The causal story that *flat minima cause better generalization* is load-bearing in the folklore but genuinely unsettled — the flatness–generalization link is measurable-but-slippery (sharpness is reparameterization-dependent), which is exactly why the original war ended in a truce rather than a verdict.

## Connections

- [[Concept - Adam and AdamW]] — the optimizer at the center of the fight; AdamW's decoupled decay is the twist that ended most of it.
- [[Concept - Stochastic Gradient Descent and Momentum]] — the other combatant; its implicit-regularization noise is the source of the flat-minima claim.
- [[Concept - Generalization in Deep Learning]] — the flat-vs-sharp-minima framework the whole argument was really about.
- [[Concept - Embeddings as Learned Representations]] — sparse, heavy-tailed embedding gradients are a core reason transformers need adaptive preconditioning.
- [[Concept - RMSNorm and LayerNorm]] — norm-layer gains contribute to the per-block gradient-scale disparity that defeats a single SGD learning rate.
- [[Concept - Scaling Laws]] — at frontier scale the LR-transfer property of Adam, not generalization, is what makes the choice non-negotiable.
- [[Concept - Vision Transformers]] — vision's switch to AdamW when it adopted attention is the cleanest evidence the split was architectural, not modality-based.

## Sources

- Wilson et al. (2017) — The Marginal Value of Adaptive Gradient Methods in Machine Learning. Opened the debate; claimed SGD generalizes better than adaptive methods.
- Keskar & Socher (2017) — Improving Generalization Performance by Switching from Adam to SGD (SWATS). The shipped hybrid hack encoding the folklore.
- Loshchilov & Hutter (2019) — Decoupled Weight Decay Regularization. Showed much of the gap was a coupled-L2 artifact; introduced AdamW.
- Zhang et al. (2020) — Why are Adaptive Methods Good for Attention Models? Heavy-tailed noise explanation; clipping partially rescues SGD.
- Zhang et al. (2024) — Why Transformers Need Adam: A Hessian Perspective. Block-heterogeneity account of Adam's advantage on transformers.
- Dosovitskiy et al. (2021) — An Image is Worth 16x16 Words (ViT). Vision-on-AdamW; the architectural tell.
