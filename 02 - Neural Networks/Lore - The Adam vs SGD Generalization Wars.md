---
tags: [lore, domain/neural-networks, level/unicorn]
aliases: [Adam vs SGD, adaptive gradient generalization gap, SWATS, marginal value of adaptive methods]
summary: "The decade-long fight over whether adaptive optimizers generalize worse than SGD, and how AdamW plus scale mostly ended it."
---

# Lore - The Adam vs SGD Generalization Wars

> **The fight:** for roughly five years the field believed [[Concept - Adam and AdamW|Adam]] trained faster but *generalized worse* than plain [[Concept - Stochastic Gradient Descent and Momentum|SGD]]. Vision stayed on SGD to protect its ImageNet numbers. NLP shrugged and used Adam anyway. Then AdamW showed that a large chunk of the "gap" was a mis-implemented regularizer, and transformers taking over everything made the argument moot. Two leftovers still shape how people reason about optimizers today: a flat-minima intuition, and the folklore that "transformers just can't use SGD."

## What happened

By 2016 there were two tribes with two optimizers. Computer vision trained ResNets on ImageNet with **SGD + momentum**: learning rate ~0.1, momentum 0.9, weight decay 1e-4, a hand-tuned step-decay schedule. NLP and the brand-new transformer trained with **Adam**. Nobody cared until the numbers started disagreeing.

The opening shot was **Wilson et al. 2017, "The Marginal Value of Adaptive Gradient Methods in Machine Learning"** (NeurIPS). The claim: adaptive methods (Adam, RMSProp, Adagrad) find solutions that *test* worse than SGD, even on problems where they reach a *lower training loss*. On several vision and language tasks, well-tuned SGD matched or beat well-tuned Adam on held-out data. The paper's rhetorical weapon: adaptive methods had only looked good because people compared badly-tuned SGD against out-of-the-box Adam. Practitioners hardened this into dogma: *if you want the best test accuracy, use SGD; Adam is for convenience.*

The fallout showed on leaderboards: ImageNet state of the art stayed on SGD + momentum for years. It also produced one of the era's tell-tale hacks, **SWATS (Keskar & Socher 2017, "Improving Generalization Performance by Switching from Adam to SGD")**. Start on Adam for the fast early descent, then *switch to SGD* partway through when a trigger fires, to collect SGD's supposedly flatter endpoint. People shipped this. A hybrid optimizer that exists only because of a belief about generalization is about as pure an artifact of folklore as you'll find.

NLP never joined the war, because SGD didn't work on transformers. The original transformer (Vaswani et al. 2017) trained with Adam under the "Noam" schedule (linear warmup, then inverse-square-root decay), and every descendant (BERT, GPT-2, GPT-3) used Adam or AdamW. Attempts to train a transformer language model with SGD stalled or diverged. The two camps talked past each other: vision *chose* SGD for the last point of accuracy; NLP *had no choice* but Adam.

**The plot twist was AdamW (Loshchilov & Hutter, arXiv 2017 → ICLR 2019, "Decoupled Weight Decay Regularization").** They noticed that the "weight decay" everyone ran inside Adam was really L2 regularization, added as $\lambda\theta$ *to the gradient*. It therefore flowed through the second-moment EMA and got divided by $\sqrt{\hat v}$. Parameters with a large gradient history got *less* shrinkage, which inverts the regularizer's intent and ties its strength to the loss landscape. Decouple the decay by applying $\lambda\theta$ directly to the weights, outside the adaptive machinery, and much of Adam's reported generalization deficit disappears. A large fraction of "Adam generalizes worse" was "Adam + L2 is a broken weight-decay implementation." That reframed the debate: the confound Wilson et al. hadn't controlled for was the *decay coupling*, not the adaptivity.

Why NLP needs the adaptive preconditioner became clear later. Transformer gradients are pathological for a single global step size. Token [[Concept - Embeddings as Learned Representations|embeddings]] produce *sparse, heavy-tailed* gradients (a given token appears in a handful of examples per batch). [[Concept - RMSNorm and LayerNorm|LayerNorm]] gains, attention projections and FFN weights sit at wildly different gradient scales. And the loss landscape's condition number is enormous. **Zhang et al. 2020, "Why are Adaptive Methods Good for Attention Models?"** (NeurIPS) blamed heavy-tailed gradient noise from class/token imbalance and showed that *gradient clipping* lets SGD partially close the gap. So adaptivity was compensating for tail behavior; there was nothing magic about it. **Zhang et al. 2024, "Why Transformers Need Adam: A Hessian Perspective"** went further and pointed to *block heterogeneity*. The Hessian's spectrum differs sharply across a transformer's parameter blocks, and one SGD learning rate can't serve all of them at once. Adam's per-coordinate scaling can.

The cleanest confirmation that the split was about *architecture, not modality* came when vision changed architectures. The [[Concept - Vision Transformers|Vision Transformer]] (Dosovitskiy et al. 2021) trains with **AdamW**. When transformers replaced CNNs, vision moved to Adam too. The dividing line was "convolutional inductive bias vs attention's gradient statistics," and images vs text had nothing to do with it.

Resolution *(as of 2026)*: **AdamW is the universal default for anything transformer-shaped.** SGD + momentum survives in pockets of CNN classification and some fine-tuning regimes where it's cheaper and good enough. The "Adam generalizes worse" claim is now read mostly as a weight-decay artifact. The flat-minima intuition, though, never fully died: the idea that SGD's gradient noise pushes it toward flatter, better-generalizing basins (see [[Concept - Generalization in Deep Learning]]). It stopped mattering for decisions at [[Concept - Scaling Laws|frontier scale]] only because there's no alternative to Adam-family preconditioning there. The question retired undecided.

## The lesson

- **Benchmarking an optimizer conflates it with its regularization coupling.** The Wilson et al. result was real *as measured*, but the measurement baked in a broken weight-decay implementation. AdamW didn't refute the experiment. It removed the confound, and most of the effect went too. When an "A is worse than B" result depends on a shared implementation detail, fix the detail before you believe the ranking.
- **Whether you *need* an adaptive optimizer depends on your gradients, not your task.** Sparse, heavy-tailed, block-heterogeneous gradients (embeddings, norm layers, attention) demand per-coordinate scaling. Smooth, homogeneous CNN gradients don't. "Vision uses SGD, NLP uses Adam" was a proxy for a fact about gradient statistics, so it flipped the moment vision adopted transformers.
- **Adam won at scale because of learning-rate transfer.** Generalization had nothing to do with it. Since $\hat m/\sqrt{\hat v} \approx \pm 1$ per coordinate, Adam's update is roughly bounded by $\eta$ whatever the gradient magnitude (smoothed sign descent), so a good LR transfers across model sizes. SGD's step scales with raw gradient magnitude, so its LR doesn't. At billion-parameter scale, where you can't afford to re-sweep, that alone settles it.

## Evidence status

**Well-sourced.** The papers are real and uncontroversial: Wilson et al. 2017, Keskar & Socher 2017 (SWATS), Loshchilov & Hutter 2019 (AdamW), Zhang et al. 2020 and 2024. The historical pattern (ImageNet SOTA on SGD, transformers/NLP on Adam, ViT on AdamW) is documented in the papers' own training configs.

**Folklore layer, directionally true.** "Transformers just can't use SGD" matches what practitioners experienced and is the everyday shorthand, but "can't" is too strong. SGD + clipping narrows the gap (Zhang et al. 2020), and the failure is a matter of degree and tuning cost. It isn't a theorem. Nobody trains a frontier model with SGD because there's no upside, not because it's provably impossible.

**Contested.** The folklore leans hard on the causal story that *flat minima cause better generalization*, and that story is unsettled. The flatness–generalization link is measurable but slippery (sharpness depends on reparameterization), which is why the original war ended in a truce and not a verdict.

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
