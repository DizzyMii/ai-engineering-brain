---
tags: [concept, domain/esoterica, level/frontier]
aliases: [LMC, linear mode connectivity, flat vs sharp minima]
summary: "Why independent SGD solutions are connected by low-loss paths, and why flat minima generalize better — the geometry behind model merging."
---
> **One-paragraph hook:** The textbook loss landscape is a scatter of isolated valleys, one per local minimum found by a different training run. Empirically, distinct SGD solutions are connected by simple low-loss paths, and flatter solutions generalize better than sharp ones. That geometry is why weight averaging, Model Soups, and merging fine-tunes with SLERP or TIES work instead of producing garbage, and why sharpness-aware training and lottery-ticket rewinding behave the way they do.

## The mechanism
Loss-landscape geometry ties together several of this domain's strangest results. [[Concept - Double Descent]]'s non-monotone test-error curve and [[Concept - Grokking]]'s delayed generalization are both, at bottom, about which basin gradient descent lands in and how that basin's shape changes with capacity or training time.

Garipov et al. 2018 ("Loss Surfaces, Mode Connectivity, and Fast Ensembling") took two independently trained SGD solutions, assumed to sit in separate basins behind a high-loss barrier, and found them connected by simple curves (Bezier or piecewise-linear) of near-constant *low* loss. The straight line between them is high-loss; a slightly bent path isn't. The landscape is far more connected than a straight-line barrier suggests.

### Linear mode connectivity
Frankle et al. 2020 sharpened this. Two networks are linearly mode connected (LMC) if the *straight-line* interpolation between their weights stays low-loss, no clever curve needed. Two networks trained from the *same* initialization with a different data order or seed become LMC only after a short early "burn-in": the network first has to become stable to SGD noise. That same stability point is what makes [[Concept - The Lottery Ticket Hypothesis]]'s late-rewinding trick work. Rewinding a ticket mask to init fails on harder tasks, but rewinding to an early step (0.1–7% of training), around where LMC starts, succeeds.

### Permutation symmetry and Git Re-Basin
Networks trained from *different* initializations normally have a high loss barrier between them. Permutation symmetry explains it: you can permute a layer's hidden units without changing the function, so two networks solving the same problem can hold their features in unrelated orders. Permute one network's units to line up with the other's and the interpolation barrier largely disappears ("LMC modulo permutation," Ainsworth et al. 2022). The implication is striking: once you quotient out the relabeling symmetry, there may be essentially one big basin in place of many small ones.

### Flatness and generalization
Hochreiter & Schmidhuber (1997) argued on minimum-description-length grounds that flat minima, where loss stays low under weight perturbation, generalize better than sharp ones because a flat solution takes fewer bits to specify. Keskar et al. (2016) gave the empirical result everyone cites: large-batch settings in [[Concept - The Training Loop]] tend to converge to sharper minima that generalize worse than the flatter ones small-batch SGD finds. That ties a training hyperparameter straight to landscape geometry, and it's the same optimizer-generalization tension recorded as folklore in [[Lore - The Adam vs SGD Generalization Wars]].

[[Concept - Sharpness-Aware Minimization]] (Foret et al. 2020) turns the flatness argument into an objective. Minimize the worst-case loss in an $\epsilon$-neighborhood in place of $L(w)$,
$$\min_w \max_{\|\epsilon\| \le \rho} L(w + \epsilon)$$
approximated by one ascent step (find the worst-case perturbation) and then a descent step at that perturbed point. It roughly doubles per-step cost but reliably improves generalization. Variants (ASAM, GSAM) adapt the neighborhood shape and matter most for ViT training.

## In practice
A cluster of production techniques rests on this geometry. Weight averaging along one trajectory (SWA, EMA checkpoints) works because checkpoints close in time are trivially mode-connected. Model Soups (Wortsman et al. 2022) average several independently fine-tuned checkpoints of the *same* pretrained model and beat any single member for free, which only works because fine-tunes of a shared base stay in one basin. Merging differently fine-tuned models (SLERP, TIES, DARE) is one step further along the same continuum, and whether it succeeds is a direct readout of how mode-connected the source checkpoints are. When they aren't connected at all (different architectures, or bases too dissimilar to interpolate), [[Concept - Knowledge Distillation]] is the fallback route to a single compact model, at the price of a full training run.

## Failure modes
Sharpness depends on parameterization. It isn't a property of the minimum alone. Dinh et al. (2017) showed you can rescale a network's weights (using ReLU's positive homogeneity, for instance) so a flat minimum looks arbitrarily sharp in the new coordinates while computing the same function. A claim that "flatness predicts generalization" needs a scale-invariant flatness measure (e.g., relative to weight norm), or it's measuring the parameterization instead of the geometry.

Permutation alignment is also uneven across architectures. It's cleanest for MLPs and CNNs, where "permute the hidden units" is a well-posed matching problem. Attention layers are murkier: permutation symmetry interacts with head structure and positional information in ways that are less cleanly solved.

## The non-obvious
Lottery-ticket rewinding, model merging and grokking's delayed generalization all sit on the *same* landscape geometry. In the Omnigrok framing, [[Concept - Grokking]]'s late generalization is the optimizer eventually moving from a memorizing region of weight-norm space into a lower-norm, flatter, generalizing one, driven by the same pressure toward flat, low-norm solutions that [[Concept - Adam and AdamW]]'s decoupled weight decay applies in ordinary training. Treat all three as observations of how connected and how flat the basin a run lands in is, and Model Soups working stops being surprising. Why overparameterized nets generalize at all is still unsolved. Flat-minima and mode-connectivity arguments are leading partial answers, not a proof, and the question is listed as open in [[Reference - Open Problems in LLM Engineering]].

## Connections
- [[Concept - The Lottery Ticket Hypothesis]] — late rewinding succeeds exactly at the stability point where linear mode connectivity kicks in; the two phenomena share a mechanism.
- [[Concept - Double Descent]] — both describe non-monotone or unintuitive geometry of the loss/generalization surface as capacity or training time increases.
- [[Concept - Knowledge Distillation]] — an alternative route to a merged small model that doesn't rely on mode connectivity, useful when source checkpoints aren't in the same basin.
- [[Concept - Adam and AdamW]] — the optimizer whose implicit bias, interacting with weight decay, shapes which basin and how flat a minimum training converges to.
- [[Concept - The Training Loop]] — batch size and learning rate schedule choices made here are exactly the levers Keskar et al. tie to sharp-vs-flat minima.
- [[Concept - Grokking]] — Omnigrok's account of grokking as motion toward a flatter, lower-norm basin is a direct application of this note's geometry.
- [[Reference - Open Problems in LLM Engineering]] — why overparameterized nets generalize at all remains unsolved; flat-minima and mode-connectivity arguments are leading partial answers, not a settled theory.
- [[Concept - Sharpness-Aware Minimization]] — the training-time technique that directly operationalizes the flat-minima generalization argument.
- [[Lore - The Adam vs SGD Generalization Wars]] — the long-running practitioner argument over which optimizer's implicit bias finds better-generalizing minima, the folklore-level version of this note's mechanism.

## Sources
- Garipov et al. (2018) — Loss Surfaces, Mode Connectivity, and Fast Ensembling of DNNs. Shows low-loss curves connect independent SGD solutions.
- Frankle et al. (2020) — Linear Mode Connectivity and the Lottery Ticket Hypothesis. Defines LMC and ties it to lottery-ticket rewinding.
- Ainsworth et al. (2022) — Git Re-Basin: Merging Models modulo Permutation Symmetries. Permutation alignment removes the interpolation barrier between independent runs.
- Keskar et al. (2016) — On Large-Batch Training for Deep Learning: Generalization Gap and Sharp Minima. Ties batch size to sharpness empirically.
- Foret et al. (2020) — Sharpness-Aware Minimization for Efficiently Improving Generalization. The SAM training objective.
- Wortsman et al. (2022) — Model Soups: Averaging Weights of Multiple Fine-Tuned Models Improves Accuracy Without Increasing Inference Time.
