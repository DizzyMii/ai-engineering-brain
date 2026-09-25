---
tags: [concept, domain/neural-networks, level/core]
aliases: [train loop, optimization loop, training step]
summary: "The canonical forward-loss-backward-clip-step-zero cycle, its ordering hazards, and effective batch size — where most 'model' bugs live."
---

# Concept - The Training Loop

> **One-paragraph hook:** All of deep learning runs as one small loop: forward, loss, backward, clip, step, zero. It looks too simple to get wrong, which is why most "model" bugs live there. Nearly every line has an ordering hazard, and violating it gives no error, no warning, just a silently degraded or diverging run. Know *why* each line sits where it does and you can diagnose most training failures without opening the model code.

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

### Why `zero_grad` exists

[[Concept - Backpropagation]] accumulates adjoints into `.grad` with `+=` by design. Originally that was for RNN graphs with shared weights; now gradient accumulation depends on it. Forget `zero_grad` and each step sums *all previous* gradients, so the effective gradient (and its norm) grows every step and loss stalls or explodes. It's the #1 beginner bug, top slot in [[Gotchas - Training Neural Networks]]. `set_to_none=True` (the default since PyTorch 2.0) frees the grad tensors instead of writing zeros, which saves memory and bandwidth, but it changes `None`-vs-`0` semantics that code inspecting `.grad` directly may depend on.

### Epochs, steps, and effective batch

A *step* is one optimizer update, an *epoch* one pass over the data. Optimization cares about the **effective batch size**:

$$B_\text{eff} = B_\text{micro} \times N_\text{accum} \times W_\text{data-parallel}$$

[[Concept - Gradient Accumulation and Microbatching]] runs steps 2-3 $N_\text{accum}$ times before one `step()`, using backward's accumulate semantics. It trades wall-clock steps for lower peak activation memory at a fixed $B_\text{eff}$. Each `loss` must be divided by $N_\text{accum}$, or you've multiplied the LR. [[Reference - Memory Math for Transformers]] quantifies where that memory goes.

### Clipping

Global-norm gradient clipping rescales the whole gradient vector if $\|g\|_2 >$ `max_norm`. `max_norm = 1.0` is the folklore default from LLM pretraining configs. It goes *after* `backward()` (grads exist) and *before* `step()` (or it does nothing). [[Concept - Mixed Precision Training]] adds a third constraint. The loss scaler multiplies all gradients by a scale factor (e.g. $2^{16}$), so you must call `scaler.unscale_(opt)` *before* clipping. Otherwise you compare the scaled norm against 1.0 and the clip is a de-facto no-op.

### Mode switching

`model.train()` / `model.eval()` flips two behaviors: [[Concept - Dropout]] (active vs identity) and BatchNorm (batch statistics plus running-stat updates vs frozen running stats; mechanics in [[Breakdown - Batch Normalization]]). Evaluating in train mode leaks dropout noise into metrics *and corrupts the running stats with eval-set statistics*. Training in eval mode silently removes regularization. Pair `model.eval()` with `torch.no_grad()` so the eval forward skips activation caching entirely.

### Scheduler ordering

Since PyTorch 1.1, `scheduler.step()` goes *after* `optimizer.step()`. Reverse them and every update uses the *next* step's LR. You silently skip the first LR value, right where LR is most sensitive: the first steps of warmup. The schedules themselves belong to [[Concept - Learning Rate Schedules for Pretraining]].

## In practice

[[Snippet - A Minimal Training Loop in PyTorch]] is the runnable 40-line version with every ordering correct, including the weight-decay param-group split. The optimizer is typically [[Concept - Adam and AdamW]]. At scale it picks up distributed collectives, sharded state and checkpointing on the same skeleton; [[Deep Dive - Anatomy of a Pretraining Run]] shows the production version. Typical values: `max_norm` 1.0, $N_\text{accum}$ chosen to hit multi-million-token effective batches on fixed hardware, eval every N steps once epochs stop meaning much.

The first debugging move is always to overfit a single batch. Loop on one batch until loss ≈ 0 (for CE, it starts at $\ln(C)$ at init, see [[Concept - Loss Functions for Neural Networks]], and should go to ~0). A healthy model and loop *must* memorize one batch. If it can't, the bug is in the loop, the loss or the data plumbing, not in capacity or regularization. The full diagnostic sequence is [[Playbook - Debugging a Neural Network That Won't Train]].

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

Treat the loop as a fixed ordering contract: zero → forward → backward → (unscale) → clip → step → scheduler. Every row in the table above is a permutation of that contract, and none of them raises an error, because the framework can't know your intent. Experienced practitioners audit a new codebase by reading its training loop first, line by line. Thirty seconds checking the contract catches more real bugs than an hour of staring at model definitions. Corollary: when a run misbehaves after a refactor, diff the loop before you diff the model.

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
