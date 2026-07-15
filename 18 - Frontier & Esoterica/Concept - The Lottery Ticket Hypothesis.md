---
tags: [concept, domain/esoterica, level/core]
aliases: [LTH, winning ticket, Iterative Magnitude Pruning, IMP]
summary: "A dense net's accuracy can be matched by a small subnetwork trained from its own init — most weights exist to make search work, not to fire."
---
> **One-paragraph hook:** Train a dense network, prune away 90% of its weights by magnitude, reset the survivors to the exact values they had at initialization (not new random values — the *same* values), and retrain. On MNIST and CIFAR-scale problems this "winning ticket" matches or beats the full network's accuracy in no more training time. The claim underneath — that a dense net's job during training is mostly to let SGD *find* a good sparse subnetwork, not to make every parameter useful at inference — is one of the cleanest existence proofs in the field that overparameterization is a search convenience, not a capacity requirement.

## The mechanism
Frankle & Carbin's 2019 ICLR best-paper "The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks" formalizes the claim: a randomly-initialized dense network $f(x;\theta_0)$ contains a subnetwork defined by a binary mask $m$ such that $f(x; m \odot \theta_0)$, trained in isolation, reaches the full network's test accuracy in at most the same number of iterations. The mask isn't guessed — it's found by **Iterative Magnitude Pruning (IMP)**:

```
θ ← θ0                          # save the initial weights
for round in 1..R:
    train θ to convergence
    m ← mask out the p% smallest-|weight| entries of θ (cumulative)
    θ ← m ⊙ θ0                  # REWIND: reset survivors to θ0, not new values
return (m, θ0)                  # the winning ticket
```

Each round prunes a fraction of the remaining weights (typically 20% per round) and *rewinds* the survivors to their value at $\theta_0$ before retraining. Iterated over several rounds this reaches 80–96% sparsity on MNIST/CIFAR-scale conv nets and small transformers with no accuracy loss versus the dense baseline.

The single most important — and non-obvious — result in the paper is what happens if you skip the rewind: keep the same mask $m$ but re-randomize the surviving weights to new values before retraining. The ticket dies. Accuracy collapses back toward a random-sparse baseline. This tells you the "winning ticket" is not a property of the mask alone (a good sparse *architecture*) — it's a property of the mask **paired with that specific initialization**. The mask and the init are coupled; you can't decompose a winning ticket into "good topology" plus "any lucky draw."

Frankle et al.'s 2020 follow-up ("Stabilizing the Lottery Ticket Hypothesis," sometimes called "late rewinding") found that pure IMP-from-$\theta_0$ fails to find tickets on harder problems (ResNet-50/ImageNet): rewinding all the way to step 0 gives unstable, non-reproducible retraining runs. The fix is to rewind to an early step $k$ (roughly 0.1–7% of total training) rather than step 0 — the point at which the network has become **stable to SGD noise**, meaning two runs from step $k$ with different data orders converge to the same basin. This stability point is the exact object studied under [[Concept - Mode Connectivity and Flat Minima]] as linear mode connectivity: a ticket exists once and only once its weights have entered a basin from which SGD trajectories no longer diverge.

A stranger variant sharpens the "mask carries information" claim further. Zhou et al. and Ramanujan et al.'s 2020 "What's Hidden in a Randomly Weighted Neural Network?" show that you can find a subnetwork of a network whose weights were **never trained at all** — only the binary mask is optimized (a "supermask") — that already reaches respectable accuracy on ImageNet. The random init alone, correctly selected, is doing real computational work before a single gradient step touches the weights.

## In practice
IMP as originally described requires training the full dense network to convergence *multiple times* (once per pruning round) — for a small CIFAR classifier that's cheap; for an LLM pretraining run it is a non-starter, since a single dense pretraining run already costs the whole compute budget. Unstructured magnitude pruning is also a poor match for the hardware production systems actually run on: modern accelerators get their throughput from dense GEMMs on [[Concept - Tensor Cores]], and a randomly-scattered 90%-zero weight matrix gets zero speedup unless the sparsity pattern is structured (2:4 sparsity, whole attention heads, whole channels) — LTH's unstructured masks generally don't qualify. This is why production LLM compression takes a completely different path: one-shot, post-training methods like SparseGPT and Wanda prune a pretrained model directly using second-order/activation-based saliency, no retraining loop required, and see [[Concept - Post-Training Quantization Formats]] for the sibling family of post-hoc compression techniques that ship in production instead of IMP. [[Concept - Knowledge Distillation]] is the other production-favored compression route — training a small model to imitate a large one — which sidesteps the mask-search problem entirely by not searching for a mask at all.

Tickets also don't transfer cleanly: a mask found for one dataset or one optimizer configuration is, at best, a partial win when reused for a different task, and structured pruning generally beats unstructured pruning on real end-to-end latency even when unstructured pruning wins on raw parameter count.

## Failure modes
- **Re-initializing survivors kills the ticket.** Symptom: accuracy of the "pruned and retrained" network is no better than a random-sparse-mask baseline. Cause: you dropped the rewind step and randomized the surviving weights. Detection: always run the reinit-control ablation (same mask, fresh random values) before claiming you've found a winning ticket — if reinit does just as well, you haven't found anything interesting, you've found a good architecture that any init can fill.
- **Rewinding to step 0 on a hard problem produces unstable results.** Symptom: retraining runs from the same mask land at noticeably different accuracies across seeds. Cause: the network at step 0 hasn't yet reached the SGD-noise-stable basin. Fix: late rewinding to an early step $k$.
- **Assuming unstructured sparsity buys inference speedup.** Symptom: a model with 90% of weights zeroed runs at the same latency as the dense model. Cause: dense tensor-core kernels don't skip zeros; you need structured sparsity or dedicated sparse kernels to realize any wall-clock gain.
- **IMP compute cost scaling.** Each pruning round is a full retrain; R rounds means R× the training compute of the dense baseline just to find the ticket — the reason IMP stays a research tool rather than a production pipeline at LLM scale.

## The non-obvious
The result that should reorganize how you think about overparameterization is the reinit-kills-it ablation: a winning ticket is not "a good sparse architecture" in the abstract, it is a specific (mask, init) pair discovered by training the dense network as a search procedure. Overparameterization's practical value is less about final-model capacity and more about giving SGD enough candidate subnetworks to search over — [[Concept - Double Descent]]'s finding that the modern deep-learning regime lives comfortably past the interpolation threshold is the complementary observation from a different angle: past that threshold there is so much redundant capacity that many good, sparse, coupled (mask, init) solutions exist for SGD to land on, which is exactly the population IMP is drawing from.

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
