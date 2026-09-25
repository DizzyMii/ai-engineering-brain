---
tags: [checklist, domain/architectures, level/advanced]
aliases: [architecture bring-up, model bring-up checklist]
summary: "Pre-flight checks before spending compute on a new or modified transformer: shapes, init, causality, position, overfit, MoE load, MFU."
---

# Checklist - New Architecture Bring-Up

> **Run this before you put a single GPU-hour of real training into a new or modified transformer.** Each item is cheap (seconds to minutes on a toy config) and catches a class of bug that otherwise shows up 10,000 steps into an expensive run as "the loss is a bit high," the most expensive way to find out you had a `repeat_interleave` bug. Work top to bottom, and don't skip a stage because the model "looks like it's training."

## Stage 0 — Static checks (no forward pass yet)

- [ ] **Parameter count matches the analytic formula.** For a dense pre-norm decoder, total ≈ `12·n_layers·d_model² + vocab·d_model` (attention QKVO = 4d², a 4× FFN = 8d²; embedding counted once if weight-tied). A mismatch above ~1–2% means a wrong `d_ff`, a missing GLU 2/3 rescale, wrong `n_kv_heads`, or a vocab error. Reconcile against the [[Reference - Transformer Architecture Cheat Sheet]].
- [ ] **`d_ff` is the intended value after the GLU rescale.** LLaMA-style is `d_ff ≈ round(8/3·d_model)` snapped to a multiple of 128/256, *not* a raw `4·d_model`. Getting this wrong silently changes param count by ~15% per block.
- [ ] **Every tensor shape through one block is asserted**: `[B, T, d_model]` on the residual bus, `[B, n_heads, T, d_head]` inside attention with `d_head = d_model / n_heads`, and K/V projected to `n_kv_heads` (not `n_heads`) under GQA.
- [ ] **Weight tying is wired the way you intend** (tied vs untied embedding/unembedding), and the tied case shares one physical tensor, not two copies that silently drift.

## Stage 1 — Single forward / backward numerical correctness

- [ ] **Init loss ≈ random-guess cross-entropy.** One forward pass on a fixed batch gives finite logits (no NaN/Inf) and a loss within ~0.3 of `ln(vocab)`. Vocab 128k → `ln(128000) ≈ 11.76`, so a step-0 loss of 11.7–12.0 is healthy. 20+ means broken init or a missing/incorrect logit scale.
- [ ] **Activation and gradient RMS are roughly flat across depth at step 0**, with no monotonic explosion or decay layer by layer. Divergence here is a residual/norm-placement bug; check against [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]].
- [ ] **Softmax and the final logit projection run in fp32**, even in a bf16 model (upcast → op → downcast).
- [ ] **Backward populates a gradient on every trainable parameter** (no `None` grads), so the autograd graph is connected end to end.

## Stage 2 — Learning sanity (overfit a single batch)

- [ ] **The model overfits one small batch** (8–32 sequences) to near-zero loss (`<0.05`) within a few hundred steps at a modest LR. If it can't, backprop isn't wired end to end, an output is detached, or a mask is leaking. Mechanics in [[Concept - The Training Loop]].

## Stage 3 — Causal & positional correctness

- [ ] **Causality test:** perturbing tokens `t+1 … T` leaves the output at position `t` bitwise unchanged. Any change means the causal mask lets a position see the future.
- [ ] **Treat suspiciously low training loss at step ~0 as label leakage** until disproven. It's the single most common "it trains great!" self-own (see [[Gotchas - Implementing Attention]]).
- [ ] **Positional dependence:** shuffling input positions must change the output. If not, positional encoding isn't being applied (attention is permutation-equivariant without it).
- [ ] **RoPE base θ matches the intended context length** (≈10k for ~4k ctx, ≈500k for long ctx), and the interleaved-vs-half rotation convention matches your weights. If in doubt, run [[Playbook - Numerically Matching a Reference Implementation]] against a reference.

## Stage 4 — Precision & stability

- [ ] **No NaN for the first few hundred steps** under the target bf16/fp8 recipe, with attention logits and final logits bounded. Wire the mixed-precision policy per [[Concept - Mixed Precision Training]].
- [ ] **Global grad norm is finite and clipping fires occasionally, not every step.** Clipping every step means the threshold is too low or the LR/warmup is wrong.

## Stage 5 — MoE-specific (skip if dense)

- [ ] **Every expert gets a non-trivial token share** on the first batches, and the per-expert load histogram hasn't collapsed onto a handful of experts. Log per-expert token counts from step 0 (see [[Gotchas - Mixture of Experts]]).
- [ ] **Capacity factor is set on purpose** and you know your token-drop rate at that capacity. A dropped token silently passes through the residual unchanged.
- [ ] **The always-on shared expert (if used) is counted once** in the param budget and is always active regardless of routing.

## Stage 6 — Throughput / MFU

- [ ] **Measured MFU is in the expected band** for the hardware: roughly 35–55% on H100 for a well-tuned dense pretrain. A much lower number points to a data stall, a bad shape, or an unfused kernel. Cross-check the arithmetic-intensity story with [[Concept - The Roofline Model]] and the definition in [[Concept - Model FLOPs Utilization (MFU)]].
- [ ] **The measured attention-vs-FFN time split matches the cheat-sheet estimate** at your sequence length (FFN-dominated at short ctx, attention-dominated at long ctx). A gross mismatch means a shape or kernel-dispatch bug.
- [ ] **Only after all of the above:** scale up, following the run mechanics in [[Deep Dive - Anatomy of a Pretraining Run]] and the full data-path map in [[Deep Dive - The Transformer]].

## Why these items

- **Param count vs formula.** The missing SwiGLU 2/3 rescale is the classic silent error. The model trains fine at 15% bigger or smaller than the config you think you're running, and every scaling-law comparison is invalid.
- **Init loss ≈ ln(vocab).** A step-0 loss far from random-guess cross-entropy almost always means an unscaled or double-scaled logit path, which hides later because the loss still descends.
- **Flat activation RMS across depth.** Pre-norm with a wrong residual scale grows the stream monotonically; you notice at a loss spike at depth 40.
- **Overfit a batch.** The cheapest proof that gradients reach every parameter. Skip it and you find the detached output head after a week of "training."
- **Causality, and low loss as leakage.** An off-by-one causal mask leaks the label and produces beautiful, meaningless loss curves. Any too-good early loss is guilty until proven innocent.
- **Position shuffle changes output.** Catches positional encoding that was built but never added to the stream, a bug that only shows up much later as mediocre long-context behavior.
- **Per-expert load histogram.** Routing collapse stays invisible in the loss for a long time while most experts starve. The histogram is the only early signal.
- **MFU in band.** 12% MFU when you expected 45% is a systems bug (dataloader, host-device stall, unfused softmax), and it'll 3× your bill if you scale before fixing it.

## Connections

- [[Deep Dive - The Transformer]] — the full architecture this checklist is validating a variant of; every item maps back to a component of that data path.
- [[Gotchas - Implementing Attention]] — the causal-mask, scaling, dtype, reshape, and RoPE bugs that Stage 1 and Stage 3 exist to catch.
- [[Gotchas - Mixture of Experts]] — the routing-collapse and token-drop failures behind Stage 5.
- [[Concept - The Training Loop]] — the overfit-a-batch test is a direct application of the loop's backprop wiring; the down-link to prerequisite mechanics.
- [[Deep Dive - Anatomy of a Pretraining Run]] — what you graduate to once bring-up passes; this checklist is the gate before that expensive procedure.
- [[Concept - Mixed Precision Training]] — the bf16/fp8 policy that Stage 4's NaN checks assume is in place.
- [[Playbook - Numerically Matching a Reference Implementation]] — the deeper procedure to run when a bring-up check fails against a known-good reference; the up-link for debugging.
- [[Reference - Transformer Architecture Cheat Sheet]] — the source of the parameter and FLOP formulas Stage 0 and Stage 6 check against.
- [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] — the mechanism behind the flat-RMS-across-depth check in Stage 1.
- [[Concept - The Roofline Model]] — the arithmetic-intensity framing that tells you whether your MFU number is reasonable.
- [[Concept - Model FLOPs Utilization (MFU)]] — the exact metric Stage 6 measures and its expected bands by hardware.

## Sources

- Elhage et al. (2021) — *A Mathematical Framework for Transformer Circuits.* The residual-stream view that makes the "flat RMS across depth" check meaningful.
- Karpathy (nanoGPT / "A Recipe for Training Neural Networks") — the overfit-a-single-batch discipline and "become one with the data" bring-up ethos.
- Chowdhery et al. (2022) — *PaLM.* Source of realistic MFU targets (they report ~46% MFU) and the logit-instability motivation behind Stage 4.
