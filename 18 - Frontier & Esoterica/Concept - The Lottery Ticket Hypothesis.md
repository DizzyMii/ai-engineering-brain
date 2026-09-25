---
tags: [concept, domain/esoterica, level/core]
aliases: [LTH, winning ticket, Iterative Magnitude Pruning, IMP]
summary: "A dense net's accuracy can be matched by a small subnetwork trained from its own init — most weights exist to make search work, not to fire."
---
> **One-paragraph hook:** Train a dense network, prune 90% of its weights by magnitude, reset the survivors to the exact values they had at initialization (the *same* values, not a fresh draw), and retrain. On MNIST and CIFAR-scale problems this "winning ticket" matches or beats the full network's accuracy in no more training time. The underlying claim is that a dense net's job in training is mostly to let SGD *find* a good sparse subnetwork, and most parameters never need to be useful at inference. It's one of the cleanest existence proofs in the field that overparameterization is a search convenience, not a capacity requirement.

## The mechanism
Frankle & Carbin's 2019 ICLR best paper, "The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks," states it formally. A randomly initialized dense network $f(x;\theta_0)$ contains a subnetwork, defined by a binary mask $m$, such that $f(x; m \odot \theta_0)$ trained in isolation reaches the full network's test accuracy in at most the same number of iterations. The mask is found by **Iterative Magnitude Pruning (IMP)**:

```
θ ← θ0                          # save the initial weights
for round in 1..R:
    train θ to convergence
    m ← mask out the p% smallest-|weight| entries of θ (cumulative)
    θ ← m ⊙ θ0                  # REWIND: reset survivors to θ0, not new values
return (m, θ0)                  # the winning ticket
```

Each round prunes a fraction of the remaining weights (typically 20%) and *rewinds* the survivors to their $\theta_0$ values before retraining. Over several rounds this reaches 80–96% sparsity on MNIST/CIFAR-scale conv nets and small transformers with no accuracy loss against the dense baseline.

The most important result in the paper is what happens without the rewind. Keep the mask $m$, re-randomize the surviving weights, retrain, and the ticket dies: accuracy falls back toward a random-sparse baseline. So the mask alone (a good sparse *architecture*) isn't the ticket. The ticket is the mask **paired with that specific initialization**. You can't split a winning ticket into "good topology" plus "any lucky draw."

Frankle et al.'s 2020 follow-up ("Stabilizing the Lottery Ticket Hypothesis," sometimes called "late rewinding") found that pure IMP from $\theta_0$ fails on harder problems like ResNet-50/ImageNet. Rewinding all the way to step 0 gives unstable, non-reproducible retraining. The fix is to rewind to an early step $k$ (roughly 0.1–7% of total training) in place of step 0, the point where the network has become **stable to SGD noise**: two runs from step $k$ with different data orders end up in the same basin. That stability point is the linear mode connectivity studied in [[Concept - Mode Connectivity and Flat Minima]]. A ticket exists once and only once the weights have entered a basin from which SGD trajectories no longer diverge.

A stranger variant pushes "the mask carries information" further. Zhou et al. and Ramanujan et al.'s 2020 "What's Hidden in a Randomly Weighted Neural Network?" find subnetworks of networks whose weights were **never trained**. Only the binary mask is optimized (a "supermask"), and it already reaches respectable accuracy on ImageNet. The random init, selected correctly, does real computational work before any gradient step touches the weights.

## In practice
IMP as described trains the full dense network to convergence *several times*, once per pruning round. Cheap for a small CIFAR classifier; a non-starter for LLM pretraining, where one dense run already costs the whole compute budget.

Unstructured magnitude pruning also fits production hardware badly. Accelerators get their throughput from dense GEMMs on [[Concept - Tensor Cores]], and a randomly scattered 90%-zero weight matrix gets no speedup unless the sparsity is structured (2:4 sparsity, whole attention heads, whole channels). LTH's unstructured masks generally don't qualify.

So production LLM compression goes another way. One-shot post-training methods like SparseGPT and Wanda prune a pretrained model directly using second-order or activation-based saliency, with no retraining loop. [[Concept - Post-Training Quantization Formats]] covers the sibling family of post-hoc compression that ships in production instead of IMP. [[Concept - Knowledge Distillation]], training a small model to imitate a large one, is the other favored route, and it avoids the mask-search problem by never searching for a mask.

Tickets don't transfer cleanly either. A mask found for one dataset or optimizer configuration is at best a partial win on another task. And structured pruning generally beats unstructured on real end-to-end latency, even where unstructured wins on raw parameter count.

## Failure modes
- **Re-initializing survivors kills the ticket.** The pruned-and-retrained network does no better than a random-sparse-mask baseline, because the rewind was dropped and the surviving weights randomized. Always run the reinit control (same mask, fresh random values) before claiming a winning ticket. If reinit does just as well, you've found a good architecture that any init can fill, which is much less interesting.
- **Rewinding to step 0 on a hard problem gives unstable results.** Retraining from the same mask lands at noticeably different accuracies across seeds, since the network at step 0 hasn't reached the SGD-noise-stable basin yet. Fix: late rewinding to an early step $k$.
- **Expecting unstructured sparsity to speed up inference.** A model with 90% of weights zeroed runs at the dense model's latency. Dense tensor-core kernels don't skip zeros; you need structured sparsity or dedicated sparse kernels for any wall-clock gain.
- **IMP compute cost.** Each pruning round is a full retrain, so R rounds cost R× the dense baseline's training compute just to find the ticket. That's why IMP stays a research tool and never became a production pipeline at LLM scale.

## The non-obvious
The reinit ablation is the result that should change how you think about overparameterization. A winning ticket is a specific (mask, init) pair that training the dense network uncovers, with training acting as a search procedure. It isn't a good sparse architecture in the abstract. Overparameterization's practical value lies less in final-model capacity than in giving SGD enough candidate subnetworks to search. [[Concept - Double Descent]] shows the same thing from another angle: the modern deep-learning regime sits well past the interpolation threshold, where redundant capacity is so plentiful that many good, sparse, coupled (mask, init) solutions exist for SGD to land on. That's the population IMP draws from.

## Connections
- [[Concept - Double Descent]] — both describe why the overparameterized regime works: double descent shows extra capacity smooths the loss landscape past the interpolation threshold, LTH shows most of that extra capacity was never needed at inference, only for the search.
- [[Concept - Mode Connectivity and Flat Minima]] — late rewinding's "stable to SGD noise" point is the same linear-mode-connectivity stability boundary studied there; the two lines of work independently found the same phase transition in training.
- [[Concept - Post-Training Quantization Formats]] — the production-shipping sibling of LTH's goal (smaller, faster models), achieved by one-shot post-training pruning/quantization instead of iterative retrain-and-rewind.
- [[Concept - Backpropagation]] — IMP is nothing but repeated applications of ordinary backprop-trained rounds with a pruning-and-rewind step interleaved; the mechanism doing all the "search" is standard gradient descent.
- [[Concept - Tensor Cores]] — the hardware reason unstructured winning tickets rarely translate into inference speedups: dense GEMM kernels don't skip zeroed weights.
- [[Concept - Knowledge Distillation]] — the alternative, more production-viable compression philosophy: teach a small model to imitate, rather than search a big model for a small model already inside it.
- [[Reference - Open Problems in LLM Engineering]] — LTH is one of the few concrete partial answers to "why do overparameterized networks generalize at all," an entry in that open-problems catalog.
- [[Concept - The Multilayer Perceptron]] — the dense layer LTH prunes down to a sparse subnetwork; the hypothesis is fundamentally about how much of that dense capacity is load-bearing at inference.

## Sources
- Frankle & Carbin (2019) — "The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks." ICLR best paper; introduces IMP and the winning-ticket claim.
- Frankle, Dziugaite, Roy & Carbin (2020) — "Linear Mode Connectivity and the Lottery Ticket Hypothesis" (the "Stabilizing the LTH" work). Introduces late rewinding and ties ticket stability to SGD-noise stability.
- Zhou, Lan, Liu & Yosinski (2019) and Ramanujan et al. (2020) — "What's Hidden in a Randomly Weighted Neural Network?" Supermasks: high accuracy from mask selection alone, no weight training.
