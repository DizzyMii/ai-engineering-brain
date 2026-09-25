---
tags: [deep-dive, domain/fine-tuning, level/advanced]
aliases: [LoRA, Low-Rank Adaptation]
summary: "How LoRA freezes W and trains a low-rank BA update, why it works, and how it merges for free inference."
---
# Deep Dive - LoRA

> **One-paragraph hook:** LoRA (Low-Rank Adaptation) is why fine-tuning a 70B-parameter model became a weekend job on a single GPU instead of a multi-node training run. It freezes the full weight matrix W and learns a low-rank correction ΔW = BA, injected as a parallel branch beside the frozen linear layer. That cuts optimizer and gradient memory by two orders of magnitude and, for most tasks, closes most of the gap to full fine-tuning. And since ΔW is just a matrix, it can be folded back into W at serving time for zero added latency.

## The mechanism

Core equation:

$$W' = W + \Delta W, \qquad \Delta W = \frac{\alpha}{r} BA$$

$W \in \mathbb{R}^{d\times k}$ is frozen. $A \in \mathbb{R}^{r\times k}$ is initialized $\sim \mathcal{N}(0,\sigma^2)$ (small variance). $B \in \mathbb{R}^{d\times r}$ is initialized to **zero**. At step 0, $\Delta W = 0$ because $B=0$, so training starts at the pretrained function. That gives you a free correctness check: assert output equality at init before trusting anything else. Only $A$ and $B$ get gradients via [[Concept - Backpropagation]]. $W$'s gradient is never computed, and autograd never touches the $d\times k$ matrix.

Params: the full weight is $d\cdot k$; $A$ is $r\cdot k$ and $B$ is $d\cdot r$, so trainable params $= r(d+k)$ instead of $d\cdot k$. For $d=k=4096$ (a typical hidden dim) and $r=16$: full = 16.8M, LoRA = ~131K, a ~128x reduction per matrix. That's what factoring a dense update through a low-rank bottleneck buys, given the [[Concept - Matrix Multiplication as the Atom of Deep Learning]] cost structure that makes rank reduction cheap.

Hu et al. 2021 hypothesize that the ΔW needed to adapt an already-capable pretrained model to a new task or style has low intrinsic rank. They build on Aghajanyan et al. 2020's intrinsic-dimensionality result: fine-tuning updates live on a low-dimensional manifold even though the full parameter space is huge. Empirically $r=1\text{-}8$ often suffices to adapt existing capabilities (steering a skill the base already has), though harder distribution shifts need more.

Scaling: the $\alpha/r$ factor decouples the update's magnitude from $r$. Double $r$ without doubling $\alpha$ and you halve the effective update magnitude (same direction, different amplitude), which acts like silently changing the learning rate. It's the most common LoRA footgun in practice (see [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]]).

## Architecture / walkthrough

```
              x  (input activation)
              │
      ┌───────┴────────┐
      │                 │
      ▼                 ▼
 frozen W (d×k)     dropout(x)
      │                 │
      │                 ▼
      │            A (r×k), grad ✓
      │                 │
      │                 ▼
      │            B (d×r), grad ✓
      │                 │
      │                 ▼
      │           × (α/r) scaling
      │                 │
      ▼                 ▼
   Wx  ──────────(+)────┘
              │
              ▼
          output h
```

Mechanically it's a forward hook or a wrapped `nn.Linear` (implemented end to end in [[Snippet - LoRA Linear Layer from Scratch]]). The frozen base computes $Wx$ as normal, a parallel branch computes $B(A(\text{dropout}(x)))$ and scales by $\alpha/r$, and the two are summed. Dropout goes on the *input* of $A$, not its output; per the original paper, that regularizes the low-rank path specifically.

Target modules: the original paper applied LoRA only to the [[Concept - Attention Mechanism]]'s q and v projections, leaving k, o and the whole MLP alone, a conservative choice that kept the method easy to reason about. Modern practice (set by the QLoRA paper and popularized by community benchmarking such as Sebastian Raschka's from-scratch LoRA experiments) applies LoRA to every linear layer in the block: q, k, v, o, and the MLP's gate/up/down projections. Which layers exist to target depends on the [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] in use, since GQA/MQA models share k/v projections across heads. Coverage matters more than rank for closing the gap to full FT. A rank-8 LoRA on all linear layers frequently beats a rank-64 LoRA on q,v alone.

Optimizer footprint: trainable params scale as $r(d+k)$ per matrix, summed over every targeted matrix. A 7B model with LoRA on all linear layers at $r=16$ comes out to roughly 40M trainable parameters, about 0.6% of the base's 7B. [[Concept - Adam and AdamW]]'s state (two fp32 moments plus an fp32 master copy) for those 40M params is on the order of a few hundred MB, versus tens of GB for full fine-tuning of the same model ([[Reference - Memory Math for Transformers]] has the full breakdown).

Merging: for inference, $W_{\text{merged}} = W + (\alpha/r)BA$ is computed once, offline, and the adapter is discarded. The served model is a single dense weight with the base's shape and zero added FLOPs or latency versus the unmodified model. The one sharp edge is merging into a *quantized* base, which loses precision because you're adding a full-precision correction to an already-rounded value. The standard fix: dequantize to fp16/bf16, merge, then re-quantize if needed (see [[Concept - QLoRA]]).

## In practice

Typical hyperparameters (full table in [[Reference - Fine-Tuning Hyperparameters]]): $r=8\text{-}64$, with $r=16$ a common default; $\alpha=2r$ by convention (the *ratio* matters, not the absolute values); dropout 0.05-0.1; LR roughly 10x the equivalent full-FT LR (1e-4 to 3e-4), since only a tiny low-dimensional subspace is being optimized.

In numbers: a 7B model's weights in bf16 are ~14GB. A LoRA adapter on all linear layers at $r=16$ adds well under 200MB of trainable state and a correspondingly tiny optimizer footprint. So LoRA fine-tuning fits on a single 24GB consumer GPU, while full fine-tuning of the same model needs ~84GB (weights + gradients + fp32 optimizer state) and multi-GPU sharding.

An operational fact people miss: LoRA does *not* meaningfully cut forward-pass FLOPs. The frozen matmul $Wx$ still runs at full cost, and the low-rank branch $BAx$ adds a little *extra* compute. The whole benefit is optimizer, gradient and (with checkpointing) activation memory. A LoRA step at the same batch size isn't dramatically faster than full FT on the same hardware. It's *possible on hardware where full FT isn't*, which is a different claim.

## Failure modes

- **Underfitting from q,v-only targeting.** Default configs in older tutorials only touch attention q,v. Symptom: quality plateaus well below full FT regardless of rank. Fix: target all linear layers.
- **Silent LR rescaling.** Changing $r$ without adjusting $\alpha$ rescales the effective update by $\alpha(1/r_2 - 1/r_1)$. Symptom: loss curve flattens or diverges when you "just try a bigger rank." Fix: hold $\alpha/r$ fixed, or switch to rsLoRA's $1/\sqrt{r}$ scaling.
- **Gradient checkpointing with no gradient flow.** LoRA's forward branch depends on an input that, under naive gradient checkpointing, may not have `requires_grad` set, so no gradient reaches A/B. Symptom: loss is exactly constant across steps. Fix: `enable_input_require_grads()` or `prepare_model_for_kbit_training`.
- **Base revision mismatch at load time.** Saving only the adapter (the normal, correct thing to do) and later loading it against a different base revision silently degrades quality with no error. Fix: pin and record the base model hash.
- **Merging into a quantized base.** See above: dequantize first.

Full catalog: [[Gotchas - LoRA Fine-Tuning]].

## The non-obvious

The rank hypothesis is about *adapting an existing capability*, not injecting one. On instruction-following and style/format adaptation, where the base already has the capability and only needs steering, LoRA closes nearly all of the gap to full FT at $r$ as low as 8-16. On tasks that need new skills the pretraining distribution under-covers (Biderman et al. 2024 measured this on code and math continued pretraining), the gap reopens and stays open even at high rank. The needed update doesn't live in a low-rank subspace of the *existing* solution; see [[Concept - Why LoRA Underperforms Full Fine-Tuning]]. Ask "which regime am I in?" before touching rank or LR and you'll skip most LoRA debugging sessions.

## Evolution

The line runs: intrinsic dimensionality (Aghajanyan et al. 2020, showing fine-tuning updates are low-rank in an absolute sense) → LoRA (Hu et al. 2021, turning that into a trainable factorization) → [[Concept - QLoRA]] (Dettmers et al. 2023, quantizing the frozen base to 4-bit so the memory savings reach the base weights too, not only the optimizer state) → a current wave of refinements aimed at LoRA's specific weaknesses. Those are [[Concept - DoRA]] (splitting the weight into magnitude and direction to recover full-FT-like learning dynamics), [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] (fixing the scaling so high rank is usable), and [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] (starting the adapter somewhere smarter than zero). None has displaced vanilla LoRA as the default. They're increasingly composable add-ons on top of it, and they mostly matter once you understand [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] and where its baseline falls short.

## Connections

- [[Concept - QLoRA]] — quantizes the frozen base to 4-bit on top of the same LoRA math, the direct memory-saving successor.
- [[Concept - DoRA]] — decomposes W into magnitude and direction to close the quality gap LoRA leaves on the table.
- [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] — fixes the α/r scaling collapse that caps usable rank in vanilla LoRA.
- [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] — alternatives to the B=0 init that speed convergence and (for LoftQ) compensate for quantization error.
- [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] — the family LoRA belongs to; explains the shared memory motivation across all PEFT methods.
- [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — the mechanistic account of exactly when and why the gap to full FT reopens.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the BA factorization is only cheap because matmul cost is what you're economizing on.
- [[Concept - Adam and AdamW]] — the optimizer whose state LoRA shrinks from d×k to r(d+k) per matrix.
- [[Concept - Backpropagation]] — why freezing W means its gradient is never computed, not just discarded.
- [[Concept - Attention Mechanism]] — q,k,v,o are the layers LoRA was originally targeted at.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — the attention variant in play changes which projections exist to target with LoRA.
- [[Reference - Memory Math for Transformers]] — the source of the concrete GB figures behind LoRA's memory savings.
- [[Gotchas - LoRA Fine-Tuning]] — the full catalog of the failure modes summarized above.
- [[Snippet - LoRA Linear Layer from Scratch]] — the ~40-line implementation that makes this mechanism concrete.
- [[Reference - Fine-Tuning Hyperparameters]] — the numeric defaults (r, α, LR, dropout) referenced throughout this note.

## Sources
- Hu et al. (2021) — "LoRA: Low-Rank Adaptation of Large Language Models." The original low-rank adapter method.
- Aghajanyan et al. (2020) — "Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning." The theoretical basis for why low-rank updates suffice.
- Biderman et al. (2024) — "LoRA Learns Less and Forgets Less." Measures the LoRA-vs-full-FT quality gap on code/math continued pretraining.
