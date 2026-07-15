---
tags: [concept, domain/neural-networks, level/core]
aliases: [train loop, optimization loop, training step]
summary: "The canonical forward-loss-backward-clip-step-zero cycle, its ordering hazards, and effective batch size — where most 'model' bugs live."
---

# Concept - The Training Loop

> **One-paragraph hook:** Everything in deep learning ultimately executes as one small loop: forward, loss, backward, clip, step, zero. The loop looks too simple to get wrong, which is exactly why it is where most "model" bugs actually live — nearly every line has an ordering hazard whose violation produces no error, no warning, and a silently degraded or diverging run. A practitioner who can recite *why* each line sits where it does can diagnose the majority of training failures without ever opening the model code.

## The mechanism

The five-line core, in the only correct order:

```python
for x, y in loader:
    opt.zero_grad(set_to_none=True)   # 1. clear stale gradients
    loss = loss_fn(model(x), y)       # 2. forward + loss
    loss.backward()                   # 3. backward: ACCUMULATES into .grad
    clip_grad_norm_(model.parameters(), max_norm=1.0)   # 4. after backward, before step
    opt.step()                        # 5. apply update
    sched.step()                      # 6. scheduler AFTER optimizer (PyTorch >= 1.1)
```

**Why `zero_grad` exists at all:** [[Concept - Backpropagation]] accumulates adjoints into `.grad` with `+=` by design — originally for RNN graphs with shared weights, now load-bearing for gradient accumulation. Forget it and each step sums *all previous* gradients: the effective gradient (and its norm) grows every step, loss stalls or explodes. This is the #1 beginner bug, and it earns the top slot in [[Gotchas - Training Neural Networks]]. `set_to_none=True` (the default since PyTorch 2.0) frees the grad tensors instead of writing zeros — a memory and bandwidth win — but changes `None`-vs-`0` semantics that code inspecting `.grad` directly can depend on.

**Epochs, steps, and effective batch.** One *step* = one optimizer update; one *epoch* = one pass over the data. The quantity optimization actually cares about is the **effective batch size**:

$$B_\text{eff} = B_\text{micro} \times N_\text{accum} \times W_\text{data-parallel}$$

[[Concept - Gradient Accumulation and Microbatching]] runs steps 2-3 $N_\text{accum}$ times before one `step()` — exploiting backward's accumulate semantics — trading wall-clock steps for lower peak activation memory at a fixed $B_\text{eff}$ (each `loss` must be divided by $N_\text{accum}$ or you've multiplied the LR). Where that memory actually goes is quantified in [[Reference - Memory Math for Transformers]].

**Clipping.** Global-norm gradient clipping rescales the whole gradient vector if $\|g\|_2 >$ `max_norm`; `max_norm = 1.0` is the folklore default from LLM pretraining configs. It must sit *after* `backward()` (grads exist) and *before* `step()` (or it does nothing). Under [[Concept - Mixed Precision Training]] there is a third constraint: the loss scaler multiplies all gradients by a scale factor (e.g. $2^{16}$), so you must call `scaler.unscale_(opt)` *before* clipping — otherwise you are comparing the scaled norm against 1.0 and the clip is a de-facto no-op.

**Mode switching.** `model.train()` / `model.eval()` flips two behaviors: [[Concept - Dropout]] (active vs identity) and BatchNorm (batch statistics + running-stat updates vs frozen running stats — mechanics in [[Breakdown - Batch Normalization]]). Evaluating in train mode leaks dropout noise into metrics *and corrupts the running stats with eval-set statistics*; training in eval mode quietly removes regularization. Pair `model.eval()` with `torch.no_grad()` so the eval forward skips activation caching entirely.

**Scheduler ordering.** Since PyTorch 1.1, `scheduler.step()` belongs *after* `optimizer.step()`. Reversed, every update uses the *next* step's LR — you silently skip the first LR value, which matters exactly where LR is most sensitive: the first steps of warmup. The schedules themselves are owned by [[Concept - Learning Rate Schedules for Pretraining]].

## In practice

The runnable 40-line version with all orderings correct — including the weight-decay param-group split — is [[Snippet - A Minimal Training Loop in PyTorch]]; the optimizer doing the actual update is typically [[Concept - Adam and AdamW]]. At scale the same loop acquires distributed collectives, sharded state, and checkpointing, but its skeleton is unchanged — see [[Deep Dive - Anatomy of a Pretraining Run]] for what production decoration looks like. Typical values: `max_norm` 1.0, $N_\text{accum}$ chosen to hit multi-million-token effective batches on fixed hardware, eval every N steps rather than per-epoch once epochs stop being meaningful.

**The first debugging move is always overfit-a-single-batch:** loop on one batch until loss ≈ 0 (for CE, from $\ln(C)$ at init — see [[Concept - Loss Functions for Neural Networks]] — down to ~0). A healthy model+loop *must* be able to memorize one batch; if it can't, the bug is in the loop, the loss, or the data plumbing — not in capacity or regularization. The full diagnostic sequence is [[Playbook - Debugging a Neural Network That Won't Train]].

## Failure modes

| Symptom | Cause | Detection |
|---|---|---|
| Loss stalls/explodes; grad norm grows monotonically | Missing `zero_grad` | Log $\|g\|$ every step |
| Val metrics nondeterministic across identical evals | `model.eval()` forgotten (dropout active) | Run eval twice, diff results |
| Val fine early, degrades as training proceeds | BatchNorm running stats corrupted by eval-in-train-mode | Compare batch-stat vs running-stat eval |
| Loss spikes survive despite clipping (mixed precision) | Clipping before `unscale_` | Log the *unscaled* grad norm |
| LR-sensitive run diverges only at warmup | Scheduler stepped before optimizer | Print LR at steps 0-5 vs config |
| Loss jumps when $N_\text{accum}$ changes | Loss not divided by accumulation steps | Per-example loss should be invariant |

## The non-obvious

The loop is a fixed *ordering contract*, not a style choice: zero → forward → backward → (unscale) → clip → step → scheduler. Every entry in the table above is a permutation of that contract, and none of them raises an error — the framework cannot know your intent. Experienced practitioners audit a new codebase by reading its training loop first, in order, line by line; thirty seconds of checking the contract catches more real bugs than an hour of staring at model definitions. Corollary: when a run misbehaves after a refactor, diff the loop before you diff the model.

## Connections

- [[Concept - Backpropagation]] — supplies the gradients and the accumulate-by-default semantics that force the `zero_grad` discipline.
- [[Concept - Loss Functions for Neural Networks]] — the scalar the loop minimizes; loss-at-init $\ln(C)$ is the loop's first sanity check (down-link).
- [[Concept - Adam and AdamW]] — the `opt.step()` that consumes the gradients; its state is why checkpointing a run means more than saving weights.
- [[Snippet - A Minimal Training Loop in PyTorch]] — the complete runnable form of this note, with the expert decisions annotated.
- [[Concept - Gradient Accumulation and Microbatching]] — the memory-for-steps trade built directly on backward's `+=` semantics.
- [[Concept - Mixed Precision Training]] — adds the scaler to the loop and the unscale-before-clip ordering constraint.
- [[Concept - Learning Rate Schedules for Pretraining]] — what `sched.step()` implements and why its position in the loop matters.
- [[Breakdown - Batch Normalization]] — the running-stats machinery that makes `train()`/`eval()` mode a correctness issue, not a convention.
- [[Concept - Dropout]] — the other train/eval-dependent module; active dropout at eval is a classic silent metric corruptor.
- [[Reference - Memory Math for Transformers]] — quantifies the activation memory that gradient accumulation and `no_grad` eval are managing.
- [[Playbook - Debugging a Neural Network That Won't Train]] — the operational procedure that starts from this loop's invariants (loss-at-init, overfit-a-batch).
- [[Gotchas - Training Neural Networks]] — the aggregated pain catalog; half its entries are violations of this loop's ordering contract.
- [[Deep Dive - Anatomy of a Pretraining Run]] — this loop scaled to thousands of GPUs: same skeleton, industrial decoration.

## Sources

- Karpathy (2019) — A Recipe for Training Neural Networks (blog). Source of the overfit-a-single-batch discipline and the "most model bugs are loop/data bugs" stance.
- Pascanu et al. (2013) — On the difficulty of training recurrent neural networks. The origin of global-norm gradient clipping.
- Micikevicius et al. (2018) — Mixed Precision Training. Loss scaling, and why unscale must precede clipping and stepping.
- PyTorch 1.1 release notes (2019) — the `scheduler.step()`-after-`optimizer.step()` ordering change that created the skipped-first-LR trap.
