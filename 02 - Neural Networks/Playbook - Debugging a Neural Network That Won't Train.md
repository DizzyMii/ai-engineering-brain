---
tags: [playbook, domain/neural-networks, level/advanced]
aliases: []
summary: "Ordered diagnostic procedure for a neural net that won't train: loss-at-init, overfit-a-batch, LR sweep, gradient audit."
---

# Playbook - Debugging a Neural Network That Won't Train

> **Goal:** find out why a network won't learn (flat loss, NaN loss, or loss that falls but plateaus above chance) by running diagnostics in a fixed order that separates data bugs, optimization bugs and modeling bugs. Distilled from Karpathy's "Recipe for Training Neural Networks" and lab practice.
> **When to run this:** the first time a new model or training script won't converge, or when a previously working run breaks after a change.
> **Prerequisites:** a runnable training loop (see [[Snippet - A Minimal Training Loop in PyTorch]]), per-step logging of loss and gradient norms, and the discipline to change one variable at a time.

## Steps

**1. Check the loss at initialization.** Run one forward pass on a freshly initialized model, before any optimizer step, and print the loss. For $C$-class classification with cross-entropy you should see loss $\approx \ln(C)$: $\ln(1000) \approx 6.91$ for ImageNet, $\ln(50257) \approx 10.82$ for GPT-2's vocabulary (see [[Concept - Loss Functions for Neural Networks]]). A loss far from $\ln(C)$ at random init means a label-indexing bug, a logit/target shape mismatch, or the wrong loss reduction. Fix it before touching the model. Every later step assumes the loss function is wired correctly.

**2. Overfit a single batch to ~0 loss.** Take one small batch (8–32 examples), disable all regularization, and train on it alone for a few hundred steps. Loss should crash toward 0, because a model with enough capacity can always memorize a small fixed batch. If it won't go to ~0, the bug is in the model or the optimization loop. Leave data volume and regularization strength alone until this passes.

**3. Decode the tensors that actually reach the loss.** Pull one batch from the real dataloader mid-training, decode it back to readable form (detokenize text, un-normalize images), and check inputs against targets by hand. A mismatch means an off-by-one label shift, a preprocessing bug or a tokenization mismatch. In practice most "the model is broken" reports are pipeline bugs, and this step catches them before you burn a session on the architecture.

**4. Run a learning-rate sweep (the LR range test).** Turn off any LR schedule. Run short training stints at LRs spaced on a log scale (e.g. 1e-5, 1e-4, 1e-3, 1e-2, 1e-1), following Smith (2015)'s range-test method as referenced in [[Concept - Stochastic Gradient Descent and Momentum]]. You want a band where loss decreases smoothly, with divergence to NaN above it and crawling or plateauing below. NaN at every LR, even tiny ones, points to numerics (fp16 overflow, bad init, a `log(0)`), not the LR. Flat loss at every LR points to a disconnected computational graph, not a step-size problem.

**5. Turn off dropout, weight decay and data augmentation.** Zero every regularizer and re-run steps 2–4. The model should fit more easily, not less: regularization should only ever make training *harder* to overfit and *easier* to generalize. If disabling it doesn't isolate the bug, it isn't regularization-related. Once the model demonstrably learns, add regularizers back one at a time and watch for a misconfigured one, e.g. dropout still active at eval time because of a train/eval mode bug (see [[Concept - The Training Loop]]).

**6. Audit per-layer gradient norms, dead units, and mode/zero_grad handling.** Log the L2 norm of every layer's gradient each step, count the fraction of post-ReLU activations at exactly zero, and confirm `zero_grad()` runs before every `backward()` and `model.train()`/`model.eval()` are set correctly around the loop. Healthy: grad norms roughly the same order of magnitude across depth, dead-unit fraction well under 90% per layer. Norms shrinking by orders of magnitude with depth mean [[Concept - Vanishing and Exploding Gradients]]. A layer with >90% dead ReLUs means too-high LR or bad init has killed that layer permanently. A grad norm that grows every step with no drops means a missing `zero_grad()`.

## Verification

You're done when both hold: (a) step 2's single-batch overfit reaches ~0 loss, and (b) with the full dataset and normal regularization restored, training loss drops below the step-1 loss-at-init baseline in the first few hundred steps and keeps trending down with no NaNs or gradient-norm blowups. Anything still wrong after that is a generalization, data-quality or hyperparameter-tuning problem, and belongs to a different investigation.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| Loss is NaN from step 1 | LR too high, `eps` too small under fp16, or overflow in a hand-rolled softmax/log | Lower LR 10x; use a numerically stable loss (see [[Concept - Softmax]]'s stable formulation) |
| Loss is flat / never moves | LR far too low, or the graph is disconnected (`.detach()`, wrong `requires_grad`, frozen params) | Re-run step 4's LR sweep; grep for `.detach()` and `torch.no_grad()` misuse |
| Loss falls, then spikes or explodes mid-run | Unclipped gradient spike, often near the LR-warmup boundary | Add or lower `clip_grad_norm_` (folklore default max_norm ≈ 1.0); see [[Gotchas - Training Neural Networks]] |
| Train loss looks perfect, val loss is bad or noisy | `model.eval()` never called (BatchNorm running stats or Dropout still active), or real overfitting | Check train/eval toggling first; it's cheaper to rule out than real overfitting |
| Single-batch overfit never reaches ~0 loss | Optimization or architecture is broken at the root (dead layer, wrong loss, disconnected graph) | Re-check step 1 and step 3 before anything else; don't add data or regularization |
| Grad norms fine, loss fine, but final accuracy still bad | Not a "won't train" problem: likely data quality, model capacity, or an eval bug | Exit this playbook; this is a modeling/evaluation problem, not an optimization one |

## Connections

- [[Concept - The Training Loop]] — the ordered skeleton (forward → loss → backward → clip → step → zero_grad) this playbook assumes is correctly implemented; the down-stack prerequisite.
- [[Concept - Loss Functions for Neural Networks]] — owns the loss-at-init diagnostic ($\ln C$) that step 1 depends on.
- [[Snippet - A Minimal Training Loop in PyTorch]] — a working reference loop to diff a broken one against.
- [[Concept - Vanishing and Exploding Gradients]] — the mechanism behind the per-layer gradient-norm audit in step 6.
- [[Concept - Adam and AdamW]] — the optimizer whose LR sweep in step 4 behaves differently (smoothed sign descent) than SGD's does.
- [[Gotchas - Training Neural Networks]] — the aggregated pitfall catalog this playbook's branch table cross-references for deeper symptom/cause/fix detail.
- [[Playbook - Debugging a Diverging Training Run]] — the at-scale analog: once a run trains locally but diverges under distributed or large-batch conditions.
- [[Gotchas - Numerical Stability]] — the numerical root causes (`log(0)`, fp16 overflow, catastrophic cancellation) behind step 4's "NaN at every LR" branch.

## Sources

- Karpathy, A. (2019) — "A Recipe for Training Neural Networks" (blog post). The step-ordered diagnostic methodology — overfit-a-batch, verify loss at init, disable regularization first — this playbook is distilled from.
- Smith, L. (2015) — Cyclical Learning Rates for Training Neural Networks. The LR range-test method used in step 4.
