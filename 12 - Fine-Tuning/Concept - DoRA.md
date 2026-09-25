---
tags: [concept, domain/fine-tuning, level/frontier]
aliases: [Weight-Decomposed Low-Rank Adaptation]
summary: "DoRA decomposes weights into magnitude and direction, training magnitude fully and applying LoRA only to direction, closing part of the LoRA-vs-full-FT gap."
---

# Concept - DoRA

> **One-paragraph hook:** [[Deep Dive - LoRA]] trains a low-rank update $BA$ added to a frozen weight. That constraint has a side effect people miss: it forces the update's magnitude and direction to change in lockstep, while in full fine-tuning they move more independently. DoRA (Weight-Decomposed Low-Rank Adaptation) re-parameterizes the weight into a magnitude vector and a direction matrix, fine-tunes the magnitude directly, and uses the low-rank LoRA update for direction only. At equal trainable-parameter count it consistently beats plain LoRA, most visibly at the low ranks where LoRA is weakest.

## The mechanism

Decompose a weight matrix $W \in \mathbb{R}^{d \times k}$ column-wise into magnitude and direction:

$$W = m \cdot \frac{V}{\lVert V \rVert_c}$$

Here $V \in \mathbb{R}^{d \times k}$ is the direction matrix, $m \in \mathbb{R}^{1 \times k}$ is a per-column magnitude vector, and $\lVert V \rVert_c$ is the column-wise (L2, per-output-unit) norm broadcast across columns. With $m_0 = \lVert W \rVert_c$ and $V_0 = W$ this is an exact identity. $W$ is unchanged at step 0, the same "start at the pretrained function" property that [[Deep Dive - LoRA]]'s $B{=}0$ init gives.

Fine-tuning then takes two paths. $m$ is trained directly and fully; it's tiny, one scalar per output column (e.g. 4096 numbers for a 4096×4096 matrix). The direction $V$ gets a standard LoRA update, $V' = V + BA$. At any point in training the weight is:

$$W' = m' \cdot \frac{V + BA}{\lVert V + BA \rVert_c}$$

The motivating analysis (Liu et al. 2024) measures how magnitude change correlates with direction change across training steps, for full fine-tuning versus LoRA. In full FT the two move with low or even negative correlation. LoRA's $\Delta W = BA$ couples them mathematically: scaling the low-rank direction tends to scale the effective magnitude along with it. DoRA breaks the coupling by giving magnitude its own free parameter. That reproduces more of full FT's update geometry while the bulk of the new parameters still go through a low-rank direction update.

## In practice

- Hugging Face `peft` exposes it as one flag, `LoraConfig(..., use_dora=True)`. Unsloth ships a fused, faster DoRA kernel for single-GPU training.
- The gains are largest at **low rank**. The paper reports its biggest jumps around $r{=}4$–8 on commonsense-reasoning benchmarks for LLaMA-7B/13B, roughly +1 to +4 points average accuracy over LoRA at matched trainable-parameter count. So DoRA is useful when you're VRAM-constrained and can't simply raise rank. [[Reference - Fine-Tuning Hyperparameters]] has the rank/alpha defaults it still follows.
- It stacks with the other LoRA refinements. [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] fixes the alpha/r scaling collapse and [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] fixes where $A,B$ start. DoRA changes the decomposition of $W$ itself, an independent axis, so you can use all three together.
- It's still mergeable. After training, compute $W'$ once with the formula above and fold it into a plain dense weight: zero inference overhead, same as a vanilla LoRA merge. [[Reference - PEFT Method Comparison]] shows where it sits among the other methods.

## Failure modes

- **Extra compute.** Recomputing $\lVert V + BA \rVert_c$ every forward and backpropagating through it adds real wall-clock time over vanilla LoRA at the same rank, commonly a single-digit to low-double-digit percentage slowdown depending on implementation and matrix size. Budget for it; DoRA isn't free.
- **Norm computation in reduced precision.** The column-norm op can be numerically fragile in bf16 if a column norm gets close to zero early in training (a bad init or an unlucky gradient step). The usual lesson from [[Concept - RMSNorm and LayerNorm]] applies: keep the norm in fp32 even under mixed-precision training.
- **Merging into a quantized base loses accuracy**, as with plain QLoRA. Dequantize to bf16 first, then apply the merge formula.
- **The low-rank ceiling stays.** The directional update is still low-rank, so on large-distribution-shift domains (code, math) DoRA narrows the gap to full fine-tuning without erasing it. [[Concept - Why LoRA Underperforms Full Fine-Tuning]] explains why.

## The non-obvious

DoRA doesn't add expressive capacity to the model class in any deep sense. The decomposition is an exact reparameterization, and at initialization it's the identity, same as $B{=}0$ LoRA. It changes the *optimization geometry*. Decoupling magnitude and direction gives each its own effective gradient scale, so the optimizer can move them independently instead of pushing both through one coupled low-rank channel. Weight normalization (Salimans & Kingma, 2016) used the same trick to improve conditioning, splitting a weight into scale and direction; DoRA applies it only to the LoRA update path, not the whole network. So when DoRA beats LoRA at equal parameter count, the win comes from *how the gradient moves through the update*, not extra storage capacity. That's also why the improvement is largest at low rank, where LoRA's coupling hurts most.

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
