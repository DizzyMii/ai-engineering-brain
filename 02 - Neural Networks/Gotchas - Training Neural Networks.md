---
tags: [gotchas, domain/neural-networks, level/unicorn]
aliases: [training bugs, silent training failures]
summary: "The catalog of silent training bugs — data, loss, optimizer, precision, and mode — ranked by how much pain they cause."
---
# Gotchas - Training Neural Networks

The bugs that make a network train wrong rather than crash. Crashes are easy — they hand you a stack trace. These are the ones that let training *run*, produce a plausible loss curve, and quietly cost you a week or a production incident. Ordered by how much pain they cause, worst first. The through-line: **pipeline and configuration bugs vastly outnumber modeling bugs**, and almost all of them are silent.

## 1. Forgetting `model.eval()` corrupts your metrics and your production outputs

**Symptom:** validation accuracy is unstable across runs, worse than train "loss" suggests, or the model behaves differently in production than it did at eval. Sometimes the opposite — eval looks *too* good, then production collapses.

**Cause:** `model.train()` vs `model.eval()` flips two things. [[Breakdown - Batch Normalization|BatchNorm]] switches from batch statistics to its EMA running statistics, and Dropout switches from masking-and-rescaling to pass-through. Left in train mode at inference, BatchNorm keeps *updating* its running stats on eval data and Dropout injects noise; the model's outputs become nondeterministic and dependent on batch composition. A single forgotten `.eval()` on a serving path is a recurring, genuinely expensive production incident.

**Fix:** wrap evaluation in `model.eval()` (and `torch.no_grad()`), and restore `model.train()` after. In serving, assert eval mode at load time.

**Detection:** run the same input through the model twice — if the outputs differ, you are in train mode (or have another nondeterminism source). Check that BatchNorm `num_batches_tracked` stops incrementing during eval.

## 2. Train/test contamination and label leakage

**Symptom:** validation metrics improve suspiciously fast and look great; the model then underperforms badly on genuinely fresh data.

**Cause:** the validation set is not actually held out. Common forms: deduplication run *after* the train/val split so near-duplicates straddle both; a feature computed using information from the future or the label; normalization statistics fit on the full dataset before splitting; or, for LLMs, eval-set text present in the pretraining corpus (a [[Concept - Benchmark Contamination|benchmark contamination]] problem in its own right). The model is being graded on data it effectively memorized.

**Fix:** split first, then do every fitting/dedup/statistic step using only the training partition. For pretraining, run decontamination against your eval suites before training, not after.

**Detection:** a val curve that improves faster than plausible is the first tell. Concretely, hash-and-compare train vs val examples for exact and near duplicates; audit every feature for whether it could encode the label or future data.

## 3. Loss-reduction mismatch (`mean` vs `sum` vs per-token)

**Symptom:** loss magnitude jumps when you change batch size or sequence length; a config that trained fine at one batch size diverges or crawls at another; a fine-tune that worked on short examples breaks on long ones.

**Cause:** the reduction silently rescales the effective learning rate. `sum` reduction makes the gradient scale with batch size (double the batch → double the gradient → double the effective LR). The subtler killer is the **masked-loss token-count bug** in [[Concept - Supervised Fine-Tuning (SFT)|SFT]]: when you mask prompt tokens and average only over completion tokens, dividing by the wrong denominator (all tokens vs valid tokens, or per-example vs per-batch averaging) miscounts the loss, which biases learning toward long or short sequences and rescales the LR per batch. See [[Concept - Loss Functions for Neural Networks|loss-function reductions]] for the mechanism.

**Fix:** fix a reduction convention and keep it constant across batch/sequence changes; for masked loss, divide by the exact count of *unmasked* tokens, and be explicit about per-token vs per-example averaging.

**Detection:** the loss magnitude should not jump when only the batch size changes. Print the token count entering the denominator and confirm it equals the number of unmasked positions.

## 4. Forgetting `zero_grad` — gradients accumulate across steps

**Symptom:** loss stalls, oscillates, or explodes after the first few steps; gradient norm grows every step.

**Cause:** `loss.backward()` **accumulates** into `.grad` by design — this is deliberate, so RNNs and gradient accumulation work. If you never zero the gradients, each step adds to the previous step's gradient, so your effective update is a growing running sum. It is the canonical beginner bug precisely because the API does the surprising-but-correct thing by default.

**Fix:** call `optimizer.zero_grad(set_to_none=True)` before each `backward()`.

**Detection:** log the global gradient norm; if it climbs monotonically from step 1, you are accumulating. In a correct loop it fluctuates around a stable band.

## 5. Silent autograd graph breaks

**Symptom:** a parameter never updates; a loss term has no effect; or the backward pass throws an in-place-modification error only sometimes.

**Cause:** the [[Concept - Backpropagation|autograd graph]] got severed. A stray `.detach()` or `.item()`/`.data` access cuts a tensor out of the graph so no gradient flows upstream. An in-place op (`x += ...`, `relu_()`) can overwrite a value needed for the backward pass. Reusing a graph across steps without `retain_graph` errors; retaining it when you did not mean to leaks memory. Separately, `zero_grad(set_to_none=True)` sets `.grad` to `None` rather than a zero tensor — cleaner and faster, but code that reads `param.grad` expecting a tensor (custom logging, manual grad surgery) breaks on the `None`.

**Fix:** keep the loss on the graph (no `.detach()`/`.item()` on anything you backprop through); avoid in-place ops on tensors that autograd needs; be deliberate about `retain_graph`. Guard any code that inspects `.grad` against `None`.

**Detection:** after `backward()`, assert the parameters you expect to train have non-`None`, non-zero `.grad`. A parameter with a permanently `None` gradient is disconnected from the loss.

## 6. NaN loss

**Symptom:** loss becomes `NaN` or `Inf`, usually abruptly, and never recovers.

**Cause:** several, roughly in order of frequency — `log(0)` or `log` of a negative in a hand-rolled loss; overflow in `exp`/[[Concept - Softmax|softmax]] under fp16 (max representable ~65504, so an unclipped logit around 12+ overflows `exp`); learning rate or Adam `eps` too high; bad init producing exploding activations; or a division by a near-zero denominator. Low-precision arithmetic turns "large" into `Inf` far sooner than fp32 — the failure modes catalogued under [[Concept - Floating Point for Deep Learning|floating point for deep learning]].

**Fix:** use the numerically stable, fused softmax+cross-entropy (never `log(softmax(...))`); keep the loss and reductions in fp32 even under mixed precision; clip gradients; lower the LR; sanity-check init.

**Detection:** `assert torch.isfinite(loss)` every step and checkpoint just before the first non-finite value. Check loss-at-init: for $C$ balanced classes it should be $\approx \ln(C)$ (e.g. $\ln(50257)\approx 10.82$ for a GPT-2 vocab); a value far off means a label/logit/reduction bug is already present before any NaN.

## 7. Regularizing before the model can fit

**Symptom:** the model won't reach low training loss even on a tiny dataset; you spend days on architecture and optimizer while the real bug hides.

**Cause:** dropout, weight decay, and data augmentation are all turned on while you are still trying to establish that the model *can* learn at all. Regularization suppresses fitting by design, so it masks whichever real bug (disconnected graph, wrong LR, data bug) is preventing the model from overfitting a single batch. You cannot diagnose an under-fitting model through a layer of anti-overfitting machinery.

**Fix:** turn off dropout, weight decay, and augmentation; overfit a single batch to ~0 loss first; only then re-enable regularization. This is step two of the [[Playbook - Debugging a Neural Network That Won't Train|won't-train playbook]].

**Detection:** if the model cannot drive a single fixed batch to near-zero loss with regularization off, the bug is in the model/optimization/graph, not in generalization — stop tuning regularizers.

## 8. The meta-gotcha: you are debugging the model when the bug is in the data

**Symptom:** a mysterious "the model just won't learn / learns something wrong" with no obvious cause, resisting every architectural and optimizer change.

**Cause:** the exact tensors entering the loss are not what you think they are — an off-by-one label shift, a tokenization mismatch, transposed image channels, a padding token counted as a real target, inputs and labels misaligned by a dataloader `collate` bug. These outnumber genuine modeling bugs by a wide margin, and none of them are visible from the loss curve.

**Fix:** decode and eyeball the actual inputs and targets at the loss boundary — render the image, detokenize the text, print the label — for a handful of real batches.

**Detection:** if you have not looked at the literal decoded tensors going into the loss, you have not yet ruled out the most likely bug. Do this *before* touching the [[Concept - The Training Loop|training loop]], the optimizer, or the architecture.

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
