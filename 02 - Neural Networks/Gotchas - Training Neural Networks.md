---
tags: [gotchas, domain/neural-networks, level/unicorn]
aliases: [training bugs, silent training failures]
summary: "The catalog of silent training bugs — data, loss, optimizer, precision, and mode — ranked by how much pain they cause."
---
# Gotchas - Training Neural Networks

These are bugs that make a network train wrong without crashing. A crash hands you a stack trace. These let training *run*, draw a plausible loss curve, and cost you a week or a production incident. Worst first. Across the whole list, **pipeline and configuration bugs vastly outnumber modeling bugs**, and almost all of them are silent.

## 1. Forgetting `model.eval()` corrupts your metrics and your production outputs

**Symptom:** validation accuracy is unstable across runs, worse than train "loss" suggests, or production behavior differs from eval. Or the reverse: eval looks *too* good, then production collapses.

**Cause:** `model.train()` vs `model.eval()` flips two things. [[Breakdown - Batch Normalization|BatchNorm]] switches from batch statistics to its EMA running statistics, and Dropout switches from masking-and-rescaling to pass-through. Leave the model in train mode at inference and BatchNorm keeps *updating* its running stats on eval data while Dropout injects noise. Outputs become nondeterministic and depend on batch composition. One forgotten `.eval()` on a serving path is a recurring and expensive production incident.

**Fix:** wrap evaluation in `model.eval()` (and `torch.no_grad()`), then restore `model.train()`. In serving, assert eval mode at load time.

**Detection:** run the same input through twice. Different outputs mean you're in train mode (or have some other nondeterminism source). Check that BatchNorm `num_batches_tracked` stops incrementing during eval.

## 2. Train/test contamination and label leakage

**Symptom:** validation metrics improve suspiciously fast and look great, then the model underperforms badly on fresh data.

**Cause:** the validation set isn't held out. Common forms: dedup run *after* the train/val split, so near-duplicates straddle both; a feature computed from future information or from the label; normalization statistics fit on the full dataset before splitting; or, for LLMs, eval-set text sitting in the pretraining corpus (a [[Concept - Benchmark Contamination|benchmark contamination]] problem in its own right). The model is graded on data it effectively memorized.

**Fix:** split first, then fit, dedup and compute statistics on the training partition only. For pretraining, decontaminate against your eval suites before training, not after.

**Detection:** a val curve that improves faster than plausible is the first tell. Hash-and-compare train vs val examples for exact and near duplicates, and audit every feature for whether it could encode the label or future data.

## 3. Loss-reduction mismatch (`mean` vs `sum` vs per-token)

**Symptom:** loss magnitude jumps when you change batch size or sequence length. A config that trained fine at one batch size diverges or crawls at another; a fine-tune that worked on short examples breaks on long ones.

**Cause:** the reduction silently rescales the effective learning rate. With `sum` reduction the gradient scales with batch size (double the batch → double the gradient → double the effective LR). The subtler killer is the **masked-loss token-count bug** in [[Concept - Supervised Fine-Tuning (SFT)|SFT]]. You mask prompt tokens and average only over completion tokens, but divide by the wrong denominator (all tokens vs valid tokens, or per-example vs per-batch averaging). The loss is miscounted, learning is biased toward long or short sequences, and the LR gets rescaled per batch. Mechanism in [[Concept - Loss Functions for Neural Networks|loss-function reductions]].

**Fix:** pick one reduction convention and hold it constant across batch and sequence changes. For masked loss, divide by the exact count of *unmasked* tokens and be explicit about per-token vs per-example averaging.

**Detection:** loss magnitude shouldn't jump when only batch size changes. Print the token count going into the denominator and confirm it equals the number of unmasked positions.

## 4. Forgetting `zero_grad`: gradients accumulate across steps

**Symptom:** loss stalls, oscillates, or explodes after the first few steps, and gradient norm grows every step.

**Cause:** `loss.backward()` **accumulates** into `.grad` on purpose, so that RNNs and gradient accumulation work. Never zero them and each step adds onto the last, so your effective update is a growing running sum. It's the canonical beginner bug because the API does the surprising-but-correct thing by default.

**Fix:** call `optimizer.zero_grad(set_to_none=True)` before each `backward()`.

**Detection:** log the global gradient norm. If it climbs monotonically from step 1, you're accumulating. In a correct loop it fluctuates within a stable band.

## 5. Silent autograd graph breaks

**Symptom:** a parameter never updates, a loss term has no effect, or backward throws an in-place-modification error only some of the time.

**Cause:** the [[Concept - Backpropagation|autograd graph]] got cut. A stray `.detach()` or `.item()`/`.data` access removes a tensor from the graph, so no gradient flows upstream. An in-place op (`x += ...`, `relu_()`) can overwrite a value backward needs. Reusing a graph across steps without `retain_graph` errors, and retaining it when you didn't mean to leaks memory. Separately, `zero_grad(set_to_none=True)` sets `.grad` to `None` instead of a zero tensor. Cleaner and faster, but code that reads `param.grad` expecting a tensor (custom logging, manual grad surgery) breaks on the `None`.

**Fix:** keep the loss on the graph (no `.detach()`/`.item()` on anything you backprop through), avoid in-place ops on tensors autograd needs, and set `retain_graph` deliberately. Guard any code that inspects `.grad` against `None`.

**Detection:** after `backward()`, assert that the parameters you expect to train have non-`None`, non-zero `.grad`. A parameter whose gradient is always `None` is disconnected from the loss.

## 6. NaN loss

**Symptom:** loss becomes `NaN` or `Inf`, usually abruptly, and never recovers.

**Cause:** several, roughly by frequency: `log(0)` or `log` of a negative in a hand-rolled loss; `exp`/[[Concept - Softmax|softmax]] overflow under fp16 (max representable ~65504, so an unclipped logit around 12+ overflows `exp`); learning rate or Adam `eps` too high; bad init producing exploding activations; division by a near-zero denominator. Low precision turns "large" into `Inf` far sooner than fp32 does. Those failure modes are catalogued under [[Concept - Floating Point for Deep Learning|floating point for deep learning]].

**Fix:** use the numerically stable fused softmax+cross-entropy (never `log(softmax(...))`), keep the loss and reductions in fp32 even under mixed precision, clip gradients, lower the LR, sanity-check init.

**Detection:** `assert torch.isfinite(loss)` every step and checkpoint just before the first non-finite value. Check loss at init: for $C$ balanced classes it should be $\approx \ln(C)$ (e.g. $\ln(50257)\approx 10.82$ for a GPT-2 vocab). A value far off means a label, logit or reduction bug exists before any NaN shows up.

## 7. Regularizing before the model can fit

**Symptom:** the model won't reach low training loss even on a tiny dataset, and you burn days on architecture and optimizer while the actual bug sits elsewhere.

**Cause:** dropout, weight decay and data augmentation are all on while you're still trying to establish that the model *can* learn. Regularization suppresses fitting by design, so it masks whatever bug (disconnected graph, wrong LR, data bug) keeps the model from overfitting a single batch. You can't diagnose an underfitting model through a layer of anti-overfitting machinery.

**Fix:** turn off dropout, weight decay and augmentation. Overfit a single batch to ~0 loss, then turn regularization back on. This is step two of the [[Playbook - Debugging a Neural Network That Won't Train|won't-train playbook]].

**Detection:** if the model can't drive one fixed batch to near-zero loss with regularization off, the bug is in the model, optimization or graph, not in generalization. Stop tuning regularizers.

## 8. The meta-gotcha: you're debugging the model and the bug is in the data

**Symptom:** the model "just won't learn" or learns something wrong, with no obvious cause, and resists every architecture and optimizer change.

**Cause:** the tensors entering the loss aren't what you think. An off-by-one label shift, a tokenization mismatch, transposed image channels, a padding token counted as a real target, inputs and labels misaligned by a dataloader `collate` bug. These outnumber modeling bugs by a wide margin, and none of them show up in the loss curve.

**Fix:** decode and eyeball the actual inputs and targets at the loss boundary for a handful of real batches: render the image, detokenize the text, print the label.

**Detection:** until you've looked at the literal decoded tensors going into the loss, you haven't ruled out the most likely bug. Do this *before* touching the [[Concept - The Training Loop|training loop]], the optimizer, or the architecture.

## Connections

- [[Concept - The Training Loop]] — where most of these bugs physically live; the loop's ordering hazards (zero_grad, clip-before-step, train/eval) are half this list.
- [[Playbook - Debugging a Neural Network That Won't Train]] — the ordered procedure (loss-at-init → overfit a batch → LR sweep) that surfaces these gotchas systematically.
- [[Concept - Loss Functions for Neural Networks]] — the reduction and label-target mechanics behind the loss-reduction and NaN gotchas.
- [[Breakdown - Batch Normalization]] — the train/eval statistics discrepancy that makes the forgotten-`.eval()` bug so damaging.
- [[Concept - Backpropagation]] — the autograd graph whose silent severing (detach, in-place, graph reuse) zeroes gradients without erroring.
- [[Concept - Softmax]] — the fp16 `exp` overflow in softmax is one of the most common NaN sources; the stable max-subtracted form is the fix.
- [[Concept - Floating Point for Deep Learning]] — why fp16 overflow in `exp`/softmax and underflow in reductions produce NaNs (cross-domain: foundations).
- [[Concept - Supervised Fine-Tuning (SFT)]] — the masked-loss token-count bug that miscounts valid tokens and silently rescales the LR (cross-domain: post-training).
- [[Concept - Benchmark Contamination]] — the LLM-scale form of train/test leakage: eval text present in the pretraining corpus (cross-domain: evaluation).

## Sources

- Karpathy (2019) — "A Recipe for Training Neural Networks." The source for overfit-a-batch, loss-at-init, and "look at your data" as the first moves; most of this catalog is its failure modes made concrete.
- PyTorch autograd and `optimizer.zero_grad` documentation — the accumulate-by-design semantics and `set_to_none` behavior behind gotchas 4 and 5.
- Li, Chen, Hu, Yang (2019) — "Understanding the Disharmony between Dropout and Batch Normalization by Variance Shift." Mechanism behind the train/eval statistics gotcha when the two are combined.
