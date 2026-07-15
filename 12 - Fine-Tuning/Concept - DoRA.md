---
tags: [concept, domain/fine-tuning, level/frontier]
aliases: [Weight-Decomposed Low-Rank Adaptation]
summary: "DoRA decomposes weights into magnitude and direction, training magnitude fully and applying LoRA only to direction, closing part of the LoRA-vs-full-FT gap."
---

# Concept - DoRA

> **One-paragraph hook:** [[Deep Dive - LoRA]] trains a low-rank update $BA$ added to a frozen weight, but that constraint has a hidden side effect: it forces the update's magnitude and direction to change in lockstep, unlike full fine-tuning where they move more independently. DoRA (Weight-Decomposed Low-Rank Adaptation) re-parameterizes the weight into a magnitude vector and a direction matrix, fine-tunes the magnitude directly, and reserves the low-rank LoRA update for direction only — at equal trainable-parameter count it consistently beats plain LoRA, most visibly at the low ranks where LoRA is weakest.

## The mechanism

Decompose a weight matrix $W \in \mathbb{R}^{d \times k}$ column-wise into magnitude and direction:

$$W = m \cdot \frac{V}{\lVert V \rVert_c}$$

where $V \in \mathbb{R}^{d \times k}$ is the direction matrix, $m \in \mathbb{R}^{1 \times k}$ is a per-column magnitude vector, and $\lVert V \rVert_c$ denotes the column-wise (L2, per-output-unit) norm broadcast across columns. Initialized at $m_0 = \lVert W \rVert_c$, $V_0 = W$, this is an exact identity — $W$ is unchanged at step 0, the same "start at the pretrained function" property [[Deep Dive - LoRA]]'s $B{=}0$ init gives.

Fine-tuning then splits into two paths: $m$ is trained directly and fully (it's tiny — one scalar per output column, e.g. 4096 numbers for a 4096×4096 matrix), while the direction $V$ receives a standard LoRA update, $V' = V + BA$. The new weight at any point in training is:

$$W' = m' \cdot \frac{V + BA}{\lVert V + BA \rVert_c}$$

The motivating analysis (Liu et al. 2024) measures the correlation between magnitude change and direction change across training steps for full fine-tuning versus LoRA: full FT shows the two moving with low or even negative correlation, while LoRA's $\Delta W = BA$ mathematically couples them — scaling the low-rank direction tends to scale the effective magnitude proportionally too. DoRA breaks that coupling by giving magnitude its own free parameter, reproducing more of full FT's update geometry while still routing the bulk of new parameters through a low-rank direction update.

## In practice

- Hugging Face `peft` exposes it as a single flag: `LoraConfig(..., use_dora=True)`; Unsloth ships a fused, faster DoRA kernel for single-GPU training.
- DoRA's gains are largest at **low rank** (the paper reports its biggest jumps around $r{=}4$–8 on commonsense-reasoning benchmarks for LLaMA-7B/13B, roughly +1 to +4 points average accuracy over LoRA at matched trainable-parameter count). This makes DoRA a useful lever when you're VRAM-constrained and can't just raise rank — see [[Reference - Fine-Tuning Hyperparameters]] for the rank/alpha defaults it still respects.
- It composes with the other LoRA refinements rather than competing with them: [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] fixes the alpha/r scaling collapse, [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] fixes where $A,B$ start — DoRA changes the decomposition of $W$ itself, an orthogonal axis, and all three can be stacked.
- Still mergeable: after training, compute $W'$ once with the formula above and fold it into a plain dense weight — zero inference overhead, same story as vanilla LoRA merge. See [[Reference - PEFT Method Comparison]] for where it sits against the rest of the method landscape.

## Failure modes

- **Extra compute overhead:** recomputing $\lVert V + BA \rVert_c$ every forward and backpropagating through it costs real wall-clock time on top of vanilla LoRA at the same rank — commonly a single-digit-to-low-double-digit percentage slowdown depending on implementation and matrix size; budget for it, don't assume DoRA is free.
- **Norm computation in reduced precision:** the column-norm op can be numerically fragile in bf16 if a column norm gets close to zero early in training (a bad init or an unlucky gradient step) — the standard lesson from [[Concept - RMSNorm and LayerNorm]] applies directly: keep the norm computation in fp32 even under mixed-precision training.
- **Merging into a quantized base loses accuracy**, exactly as with plain QLoRA — dequantize to bf16 first, then apply the merge formula.
- **Doesn't remove the low-rank ceiling:** the directional update is still low-rank, so on large-distribution-shift domains (code, math) DoRA narrows the gap to full fine-tuning but doesn't erase it — see [[Concept - Why LoRA Underperforms Full Fine-Tuning]] for why.

## The non-obvious

DoRA doesn't add expressive capacity to the model class in any deep sense — the decomposition is an exact reparameterization, and at initialization it's mathematically the identity, same as $B{=}0$ LoRA. What it changes is the *optimization geometry*: decoupling magnitude and direction gives each its own effective gradient scale, so the optimizer can move the two independently instead of being forced through a single coupled low-rank channel. This is the same trick weight normalization (Salimans & Kingma, 2016) used to improve conditioning by splitting a weight into scale and direction — DoRA applies it specifically to the LoRA update path rather than the whole network. The practical upshot: when you see DoRA beat LoRA at equal parameter count, the win is coming from *how the gradient moves through the update*, not from any extra storage capacity — which is also why the improvement is largest exactly where LoRA's coupling hurts most, at low rank.

## Connections
- [[Deep Dive - LoRA]] — DoRA is a drop-in reparameterization of the same low-rank update; the vanilla mechanism is the prerequisite.
- [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — DoRA is cited there as one of the concrete fixes that narrows the LoRA-vs-full-FT gap.
- [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] — an orthogonal fix (update scaling, not decomposition) that composes with DoRA.
- [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] — a third orthogonal axis of LoRA improvement (initialization, not decomposition).
- [[Reference - PEFT Method Comparison]] — where DoRA's param count, mergeability, and relative quality sit against every other PEFT method.
- [[Reference - Fine-Tuning Hyperparameters]] — the rank/alpha defaults that still apply with `use_dora=True`.
- [[Breakdown - Unsloth]] — ships a fused, faster DoRA implementation worth using over the naive `peft` path.
- [[Concept - RMSNorm and LayerNorm]] — the same fp32-norm-computation stability lesson applies to DoRA's column-norm operation.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the column-norm and matmul cost DoRA adds sits directly on top of this primitive.

## Sources
- Liu et al. (2024) — "DoRA: Weight-Decomposed Low-Rank Adaptation." Introduces the magnitude/direction decomposition and the update-correlation analysis motivating it.
- Hu et al. (2021) — "LoRA: Low-Rank Adaptation of Large Language Models." The baseline low-rank update DoRA re-parameterizes.
