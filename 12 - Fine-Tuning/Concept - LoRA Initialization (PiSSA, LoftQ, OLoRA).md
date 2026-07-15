---
tags: [concept, domain/fine-tuning, level/frontier]
aliases: [PiSSA, LoftQ, OLoRA]
summary: "PiSSA, OLoRA, and LoftQ replace LoRA's zero-init with SVD/QR/quantization-aware starts, changing convergence speed and final quality."
---

# Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)

> **One-paragraph hook:** Standard [[Deep Dive - LoRA]] initializes $A$ from a small Gaussian and $B$ at zero purely so training starts at the identity — it says nothing about where the adapter *should* head. PiSSA, OLoRA, and LoftQ replace that arbitrary starting point with something structured: PiSSA starts the adapter directly on the base weight's most important directions, OLoRA starts it orthonormal for optimization stability, and LoftQ starts it compensating for the quantization error that [[Concept - QLoRA]] introduces. Same LoRA forward pass, different first step — and for hard domains or aggressive quantization, the first step matters more than intuition suggests.

## The mechanism

**Baseline (zero-init):** $A \sim \mathcal{N}(0, \sigma^2)$, $B = 0$, so $\Delta W = BA = 0$ at step 0. This guarantees an identity start, but the adapter has no information about the base weight's structure — it has to discover useful directions from scratch via gradient descent, which tends to first find directions that reduce loss fastest locally, not necessarily the directions the pretrained model already relies on most.

**PiSSA** (Meng et al. 2024, "Principal Singular values and Singular vectors Adaptation") inverts the framing. It takes the SVD of the base weight, $W = U\Sigma V^\top$, and initializes the adapter from the **top-$r$ singular components** — the highest-energy directions of $W$ — while freezing the *residual* ($W$ minus that top-$r$ component) as the new frozen base. The adapter therefore starts already sitting on the principal subspace the pretrained model actually uses most, rather than in some residual direction orthogonal to it; PiSSA reports convergence noticeably faster than random init and better final quality on math/code fine-tuning at matched rank.

**OLoRA** takes a stability-focused route instead of a principal-subspace one: it initializes $A$ and $B$ via QR decomposition to get orthonormal starting columns, avoiding the correlated or near-rank-deficient directions a plain Gaussian draw can produce, especially as rank grows. The claim is smoother, more stable early optimization rather than a head start on the "important" subspace.

**LoftQ** (Li et al. 2023) solves a different problem: the interaction between quantization and LoRA init. Naive [[Concept - QLoRA]] quantizes $W$ to NF4 once, then starts the LoRA adapter at $B{=}0$ — meaning the full quantization error between $W$ and its 4-bit approximation is left **uncompensated** at step 0, and the adapter has to spend early training just correcting for lossy rounding before it can do anything else. LoftQ instead alternates: quantize $W$ to get $Q_0$, take the SVD of the residual $W - Q_0$ to get a low-rank $(A_0, B_0)$ that approximates it, then re-quantize $W - A_0B_0$ to get a tighter $Q_1$, and repeat for a handful of iterations. The result is a frozen quantized base $Q$ plus an adapter init $(A,B)$ such that $Q + A_0B_0 \approx W$ far more closely than naive QLoRA's $Q_0$ alone — the gap it closes is largest at aggressive bit-widths (2-bit, tight 4-bit) where quantization error is largest.

## In practice

- All three are init-time, not architecture-time changes: HF `peft` exposes `init_lora_weights="pissa"` (with fast randomized-SVD variants like `"pissa_niter_4"` for large models) and `"olora"`; LoftQ requires a separate preprocessing pass (`loftq_init`) that produces the quantized base and adapter checkpoint before training starts.
- Cost is real but one-time: SVD/QR of a single 4096×4096 linear layer takes seconds on GPU, and a 7B model has on the order of a couple hundred target linear layers — expect low-single-digit minutes of setup, cached to disk, not a training-time cost.
- LoftQ needs its alternating loop run to enough iterations (paper uses roughly 1–5) to actually close the gap; run too few and it barely beats naive QLoRA init while still costing the extra preprocessing step.
- Folklore, weakly sourced: the advantage of fancy init shrinks as the fine-tuning dataset and step count grow — with enough gradient steps, the model has time to "fix" a bad starting point on its own, so the payoff is largest for short fine-tunes on hard or low-data domains, smallest for long runs on abundant data.

## Failure modes

- Treating SVD/QR init as free like the standard random init causes surprise multi-minute startup delays in automated training pipelines that weren't budgeted for it.
- **PiSSA's frozen residual is base-specific.** Because the "frozen base" it trains against is $W$ minus the top-$r$ component, not $W$ itself, a PiSSA adapter is tied to that specific residual — dropping a PiSSA-trained adapter onto the *original*, non-residual base (as you would with a normal LoRA adapter) silently produces wrong outputs. Treat PiSSA adapters as non-portable across checkpoints the way vanilla LoRA adapters are.
- LoftQ under-iterated (too few alternating steps) gives a false negative: teams conclude "LoftQ didn't help" when the preprocessing simply wasn't run to convergence.
- None of these methods raise the underlying rank ceiling — they change where training starts, not the size of the subspace it can reach; on very large distribution shifts, gains from a better init shrink, the same regime discussed in [[Concept - Why LoRA Underperforms Full Fine-Tuning]].

## The non-obvious

The zero-init baseline is often described as "no prior," but it's actually a specific and fairly strong one: it assumes the useful adaptation direction is whatever gradient descent finds fastest from a blank slate, which is frequently *not* aligned with the directions the pretrained model already relies on heavily. PiSSA's result reframes this: if a weight's top singular vectors capture most of the variance in its linear map, and the needed fine-tuning update mostly reinforces or redirects along those same high-energy directions (rather than introducing an orthogonal new capability), then starting the adapter already there means the earliest gradient steps land in a subspace the model is already sensitive to — that's the mechanistic reason it converges faster, not just a tuning trick.

## Connections
- [[Deep Dive - LoRA]] — these methods change only the initialization of $A, B$ in the standard low-rank update; the base mechanism is the prerequisite.
- [[Concept - QLoRA]] — LoftQ exists specifically to fix the initialization gap naive QLoRA leaves open at low bit-width.
- [[Concept - DoRA]] — an orthogonal LoRA refinement (weight decomposition, not initialization); the two compose.
- [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] — a third orthogonal refinement (update scaling, not initialization).
- [[Reference - PEFT Method Comparison]] — where these init variants sit relative to plain LoRA in the broader method landscape.
- [[Concept - Post-Training Quantization Formats]] — LoftQ's quantize step draws on the same NF4/int4 machinery used for inference-time quantization.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — SVD/QR decomposition factors the same weight matrices this whole family adapts.
- [[Concept - Floating Point for Deep Learning]] — the quantization error LoftQ compensates for is fundamentally a floating-point representation problem.
- [[Gotchas - LoRA Fine-Tuning]] — merge and precision pitfalls compound with a mismatched or misunderstood init.

## Sources
- Meng et al. (2024) — "PiSSA: Principal Singular values and Singular vectors Adaptation of Large Language Models." SVD-based init on the base weight's principal subspace.
- Li et al. (2023) — "LoftQ: LoRA-Fine-Tuning-Aware Quantization for Large Language Models." Alternating quantize-then-SVD initialization for the QLoRA setting.
- Hu et al. (2021) — "LoRA: Low-Rank Adaptation of Large Language Models." Defines the zero-init baseline this whole family improves on.
