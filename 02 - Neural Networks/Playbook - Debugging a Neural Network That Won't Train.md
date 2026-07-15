---
tags: [playbook, domain/neural-networks, level/advanced]
aliases: []
summary: "Ordered diagnostic procedure for a neural net that won't train: loss-at-init, overfit-a-batch, LR sweep, gradient audit."
---

# Playbook - Debugging a Neural Network That Won't Train

> **Goal:** find why a network refuses to learn — flat loss, NaN loss, or loss that falls but plateaus above chance — via a fixed diagnostic order that isolates data bugs, optimization bugs, and modeling bugs from each other, distilled from Karpathy's "Recipe for Training Neural Networks" and lab practice. **When to run this:** the first time a new model or training script won't converge, or any time a previously-working run breaks after a change. **Prerequisites:** a runnable training loop (see [[Snippet - A Minimal Training Loop in PyTorch]]), per-step logging of loss and gradient norms, and the discipline to change one variable at a time.

## Steps

1. **Verify loss at initialization.** Action: run one forward pass on a freshly initialized model, before any optimizer step, and print the loss. Expected observation: for $C$-class classification with cross-entropy, loss $\approx \ln(C)$ — e.g. $\ln(1000) \approx 6.91$ for ImageNet, $\ln(50257) \approx 10.82$ for GPT-2's vocabulary (see [[Concept - Loss Functions for Neural Networks]]). What deviation means: a loss far from $\ln(C)$ at random init signals a label-indexing bug, a logit/target shape mismatch, or a wrong loss reduction — fix this before touching the model, since every later step assumes the loss function itself is wired correctly.

2. **Overfit a single batch to ~0 loss.** Action: take one small batch (8–32 examples), disable all regularization, and train on just that batch for a few hundred steps. Expected observation: loss should crash toward 0 — a model with enough capacity can always memorize a small fixed batch. What deviation means: if you cannot drive loss to ~0 here, the bug is in the model or the optimization loop, not in data volume or regularization strength — don't touch either of those until this step passes.

3. **Inspect the actual decoded tensors entering the loss.** Action: pull one batch from the real dataloader mid-training and decode it back to human-readable form (detokenize text, un-normalize images); manually check inputs against targets. Expected observation: inputs and labels line up exactly as intended. What deviation means: an off-by-one label shift, a preprocessing bug, or a tokenization mismatch — in practice most "the model is broken" reports are pipeline bugs, and this step catches them before you burn a session on the architecture.

4. **Run a learning-rate sweep (the LR range test).** Action: disable any LR schedule, then run short training stints at LRs spaced on a log scale (e.g. 1e-5, 1e-4, 1e-3, 1e-2, 1e-1), following Smith (2015)'s range-test methodology referenced in [[Concept - Stochastic Gradient Descent and Momentum]]. Expected observation: a band of LRs where loss decreases smoothly; loss diverges to NaN above it and crawls or plateaus below it. What deviation means: NaN at every LR, even tiny ones, points away from LR and toward numerical issues (fp16 overflow, bad init, a `log(0)`); a flat loss at every LR points to a disconnected computational graph rather than a step-size problem.

5. **Turn off dropout, weight decay, and data augmentation.** Action: zero every regularizer and re-run steps 2–4. Expected observation: the model should fit more easily, not less — regularization should only ever make training *harder* to overfit and *easier* to generalize. What deviation means: if disabling regularization doesn't isolate the bug, it isn't regularization-related; re-add each regularizer one at a time once the model demonstrably can learn, watching for a misconfigured one (e.g. a dropout rate still active at eval time via a train/eval mode bug — see [[Concept - The Training Loop]]).

6. **Audit per-layer gradient norms, dead-unit fraction, and mode/zero_grad correctness.** Action: log the L2 norm of every layer's gradient each step, count the fraction of post-ReLU activations at exactly zero, and confirm `zero_grad()` runs before every `backward()` and that `model.train()`/`model.eval()` are set correctly around the loop. Expected observation: grad norms roughly consistent in order of magnitude across depth; dead-unit fraction well under 90% per layer. What deviation means: grad norms shrinking by orders of magnitude with depth signal [[Concept - Vanishing and Exploding Gradients]]; a layer with >90% dead ReLUs signals too-high LR or bad init killing that layer permanently; a grad norm that grows every step with no drops points to a missing `zero_grad()`.

## Verification

The playbook has succeeded once both hold: (a) step 2's single-batch overfit reaches ~0 loss, and (b) with the full dataset and normal regularization restored, training loss falls in the first few hundred steps below the step-1 loss-at-init baseline and keeps trending down with no NaNs or gradient-norm blowups. If both hold, any remaining problem is a generalization, data-quality, or hyperparameter-tuning problem — not a "the model won't train" problem — and belongs to a different investigation.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| Loss is NaN from step 1 | LR too high, `eps` too small under fp16, or overflow in a hand-rolled softmax/log | Lower LR 10x; use a numerically stable loss (see [[Concept - Softmax]]'s stable formulation) |
| Loss is flat / never moves | LR far too low, or the graph is disconnected (`.detach()`, wrong `requires_grad`, frozen params) | Re-run step 4's LR sweep; grep for `.detach()` and `torch.no_grad()` misuse |
| Loss falls, then spikes or explodes mid-run | Unclipped gradient spike, often near the LR-warmup boundary | Add or lower `clip_grad_norm_` (folklore default max_norm ≈ 1.0); see [[Gotchas - Training Neural Networks]] |
| Train loss looks perfect, val loss is bad or noisy | `model.eval()` never called (BatchNorm running stats or Dropout still active), or genuine overfitting | Check train/eval toggling first — it's cheaper to rule out than real overfitting |
| Single-batch overfit never reaches ~0 loss | Optimization or architecture is fundamentally broken (dead layer, wrong loss, disconnected graph) | Re-check step 1 and step 3 before anything else — don't add data or regularization |
| Grad norms fine, loss fine, but final accuracy still bad | Not a "won't train" problem — likely data quality, model capacity, or an eval bug | Exit this playbook; this is a modeling/evaluation problem, not an optimization one |

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
