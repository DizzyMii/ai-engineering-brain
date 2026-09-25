---
tags: [concept, domain/fine-tuning, level/frontier]
aliases: [PiSSA, LoftQ, OLoRA]
summary: "PiSSA, OLoRA, and LoftQ replace LoRA's zero-init with SVD/QR/quantization-aware starts, changing convergence speed and final quality."
---

# Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)

> **One-paragraph hook:** standard [[Deep Dive - LoRA]] initializes $A$ from a small Gaussian and $B$ at zero only so training starts at the identity. That says nothing about where the adapter *should* go. PiSSA, OLoRA and LoftQ swap the arbitrary start for a structured one. PiSSA starts the adapter on the base weight's most important directions, OLoRA starts it orthonormal for optimization stability, and LoftQ starts it compensating for the quantization error that [[Concept - QLoRA]] introduces. The forward pass is the same LoRA; only the first step differs. For hard domains or aggressive quantization, that first step matters more than intuition suggests.

## The mechanism

**Baseline (zero-init):** $A \sim \mathcal{N}(0, \sigma^2)$, $B = 0$, so $\Delta W = BA = 0$ at step 0. The start is guaranteed to be the identity, but the adapter knows nothing about the base weight's structure. It has to find useful directions from scratch by gradient descent, which tends to find the directions that cut loss fastest locally first, and those aren't necessarily the ones the pretrained model relies on most.

**PiSSA** (Meng et al. 2024, "Principal Singular values and Singular vectors Adaptation") flips this. It takes the SVD of the base weight, $W = U\Sigma V^\top$, initializes the adapter from the **top-$r$ singular components** (the highest-energy directions of $W$), and freezes the *residual* ($W$ minus that top-$r$ component) as the new base. The adapter starts on the principal subspace the pretrained model uses most, instead of in some residual direction orthogonal to it. PiSSA reports noticeably faster convergence than random init and better final quality on math/code fine-tuning at matched rank.

**OLoRA** goes for stability instead of the principal subspace. It initializes $A$ and $B$ by QR decomposition to get orthonormal starting columns, avoiding the correlated or near-rank-deficient directions a plain Gaussian draw can produce, especially at higher rank. The claim is smoother, more stable early optimization, not a head start on the "important" subspace.

**LoftQ** (Li et al. 2023) tackles a different problem: how quantization interacts with LoRA init. Naive [[Concept - QLoRA]] quantizes $W$ to NF4 once and starts the adapter at $B{=}0$. The full quantization error between $W$ and its 4-bit approximation is left **uncompensated** at step 0, so the adapter spends early training correcting lossy rounding before it does anything useful. LoftQ alternates instead. Quantize $W$ to get $Q_0$, take the SVD of the residual $W - Q_0$ to get a low-rank $(A_0, B_0)$ that approximates it, re-quantize $W - A_0B_0$ to get a tighter $Q_1$, and repeat for a handful of iterations. You end up with a frozen quantized base $Q$ plus an adapter init $(A,B)$ where $Q + A_0B_0 \approx W$ far more closely than naive QLoRA's $Q_0$ alone. The gap it closes is largest at aggressive bit-widths (2-bit, tight 4-bit), where quantization error is largest.

## In practice

- All three change initialization, not architecture. HF `peft` exposes `init_lora_weights="pissa"` (with fast randomized-SVD variants like `"pissa_niter_4"` for large models) and `"olora"`. LoftQ needs a separate preprocessing pass (`loftq_init`) that produces the quantized base and adapter checkpoint before training.
- The cost is real but paid once. SVD/QR of one 4096×4096 linear layer takes seconds on GPU, and a 7B model has on the order of a couple hundred target linear layers. Expect low-single-digit minutes of setup, cached to disk, with no training-time cost.
- LoftQ's alternating loop needs enough iterations (the paper uses roughly 1–5) to close the gap. Too few and it barely beats naive QLoRA init while still costing the preprocessing step.
- Folklore, weakly sourced: the advantage of fancy init shrinks as the dataset and step count grow. Given enough gradient steps the model "fixes" a bad start on its own, so the payoff is largest for short fine-tunes on hard or low-data domains and smallest for long runs on abundant data.

## Failure modes

- Treating SVD/QR init as free, like standard random init, leads to surprise multi-minute startup delays in automated pipelines that didn't budget for them.
- **PiSSA's frozen residual is base-specific.** The base it trains against is $W$ minus the top-$r$ component, not $W$ itself, so a PiSSA adapter is tied to that residual. Drop it onto the *original*, non-residual base (as you would a normal LoRA adapter) and you silently get wrong outputs. Treat PiSSA adapters as non-portable across checkpoints, the same way vanilla LoRA adapters are.
- Under-iterated LoftQ (too few alternating steps) gives a false negative. Teams conclude "LoftQ didn't help" when the preprocessing never ran to convergence.
- None of these raise the rank ceiling. They change where training starts, not the size of the subspace it can reach. On very large distribution shifts the gains from a better init shrink, the regime discussed in [[Concept - Why LoRA Underperforms Full Fine-Tuning]].

## The non-obvious

Zero-init is often called "no prior," but it's a specific and fairly strong prior. It assumes the useful adaptation direction is whatever gradient descent finds fastest from a blank slate, and that frequently *doesn't* line up with the directions the pretrained model already leans on. PiSSA's result reframes this. Suppose a weight's top singular vectors capture most of the variance in its linear map, and the needed update mostly reinforces or redirects along those high-energy directions (instead of adding an orthogonal new capability). Then an adapter that starts there puts its earliest gradient steps in a subspace the model is already sensitive to. That's the mechanistic reason it converges faster; it isn't a tuning trick.

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
