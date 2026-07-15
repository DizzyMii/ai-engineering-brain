---
tags: [deep-dive, domain/fine-tuning, level/advanced]
aliases: [LoRA, Low-Rank Adaptation]
summary: "How LoRA freezes W and trains a low-rank BA update, why it works, and how it merges for free inference."
---
# Deep Dive - LoRA

> **One-paragraph hook:** LoRA (Low-Rank Adaptation) is the reason fine-tuning a 70B-parameter model became something you can do on a single GPU over a weekend instead of a multi-node training job. Instead of updating the full weight matrix W, LoRA freezes W entirely and learns a low-rank correction ΔW = BA, injected as a parallel branch beside the frozen linear layer. The insight cuts optimizer and gradient memory by two orders of magnitude while, for most tasks, closing most of the gap to full fine-tuning — and because ΔW is just a matrix, it can be folded back into W at serving time for exactly zero added latency.

## The mechanism

Core equation:

$$W' = W + \Delta W, \qquad \Delta W = \frac{\alpha}{r} BA$$

$W \in \mathbb{R}^{d\times k}$ is frozen. $A \in \mathbb{R}^{r\times k}$ is initialized $\sim \mathcal{N}(0,\sigma^2)$ (small variance). $B \in \mathbb{R}^{d\times r}$ is initialized to **zero**. At step 0, $\Delta W = 0$ because $B=0$: training starts exactly at the pretrained function, and this is a free correctness check — assert output equality at init before trusting anything else. Only $A$ and $B$ receive gradients via [[Concept - Backpropagation]]; $W$'s gradient is never computed at all, so autograd never touches the $d\times k$ matrix.

Params: full weight is $d\cdot k$; $A$ is $r\cdot k$, $B$ is $d\cdot r$, so trainable params $= r(d+k)$ instead of $d\cdot k$. For $d=k=4096$ (a typical hidden dim) and $r=16$: full = 16.8M, LoRA = ~131K, a ~128x reduction per matrix — the payoff of factoring a dense update through a low-rank bottleneck, the same [[Concept - Matrix Multiplication as the Atom of Deep Learning]] cost structure that makes rank-reduction cheap in the first place.

Hu et al. 2021 hypothesize — building on Aghajanyan et al. 2020's intrinsic-dimensionality result, that fine-tuning updates live on a low-dimensional manifold even though the full parameter space is huge — that the ΔW needed to adapt an already-capable pretrained model to a new task or style has low intrinsic rank. Empirically $r=1\text{-}8$ often suffices to adapt existing capabilities (steering a skill the base already has), though harder distribution shifts need more.

Scaling: the $\alpha/r$ factor decouples the update's magnitude from $r$. Double $r$ without doubling $\alpha$ and you halve the effective update magnitude — same direction, different amplitude — which behaves like silently changing the learning rate. This is the single most common LoRA footgun in practice (see [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]]).

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

Mechanically this is a forward hook or wrapped `nn.Linear` (implemented end-to-end in [[Snippet - LoRA Linear Layer from Scratch]]): the frozen base computes $Wx$ as normal; a parallel branch computes $B(A(\text{dropout}(x)))$ and scales by $\alpha/r$; the two are summed. Dropout is applied to the *input* of $A$, not to $A$'s output — per the original paper, this regularizes the low-rank path specifically.

Target modules: the original paper applied LoRA only to the [[Concept - Attention Mechanism]]'s q and v projections, leaving k, o, and the entire MLP untouched — a conservative choice that kept the method simple to reason about. Modern practice (established by the QLoRA paper and popularized by community benchmarking such as Sebastian Raschka's from-scratch LoRA experiments) applies LoRA to every linear layer in the block: q, k, v, o, and the MLP's gate/up/down projections — which layers exist to target at all depends on the [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] in use, since GQA/MQA models share k/v projections across heads. Coverage turns out to matter more than rank for closing the gap to full FT — a rank-8 LoRA on all linear layers frequently beats a rank-64 LoRA on q,v alone.

Optimizer footprint: trainable params scale as $r(d+k)$ per matrix, summed over every targeted matrix. For a 7B model with LoRA on all linear layers at $r=16$, this comes out to roughly 40M trainable parameters — about 0.6% of the base's 7B. [[Concept - Adam and AdamW]]'s optimizer state (two fp32 moments plus an fp32 master copy) for those 40M params is on the order of a few hundred MB, versus tens of GB for full fine-tuning of the same model (see [[Reference - Memory Math for Transformers]] for the full breakdown).

Merging: at inference time, $W_{\text{merged}} = W + (\alpha/r)BA$ is computed once, offline, and the adapter is discarded — the served model is a single dense weight, identical shape to the base, with zero added FLOPs or latency versus the unmodified model. The one sharp edge: merging into a *quantized* base loses precision, because you're adding a full-precision correction to a value that's already been rounded — the standard fix is to dequantize to fp16/bf16 first, merge, then re-quantize if needed (see [[Concept - QLoRA]]).

## In practice

Typical hyperparameters (full table in [[Reference - Fine-Tuning Hyperparameters]]): $r=8\text{-}64$ with $r=16$ a common default; $\alpha=2r$ as a convention (the *ratio*, not the absolute values, is what matters); dropout 0.05-0.1; LR roughly 10x higher than the equivalent full-FT LR (1e-4 to 3e-4) because only a tiny low-dimensional subspace is being optimized.

Concretely: a 7B model's weights in bf16 are ~14GB; a LoRA adapter targeting all linear layers at $r=16$ adds well under 200MB of trainable state and a correspondingly tiny optimizer footprint. That's why LoRA fine-tuning fits on a single 24GB consumer GPU when full fine-tuning of the same model needs ~84GB (weights + gradients + fp32 optimizer state) and multi-GPU sharding.

Non-obvious operational fact: LoRA does *not* meaningfully reduce forward-pass FLOPs. The frozen matmul $Wx$ still runs at full cost; the low-rank branch $BAx$ adds a small amount of *extra* compute on top. The entire benefit is optimizer, gradient, and (with checkpointing) activation memory — not raw compute. A LoRA step on the same batch size is not dramatically faster per step than full FT on the same hardware; it's *possible on hardware where full FT isn't*, which is a different claim.

## Failure modes

- **Underfitting from q,v-only targeting.** Default configs in older tutorials only touch attention q,v. Symptom: quality plateaus well below full FT regardless of rank. Fix: target all linear layers.
- **Silent LR rescaling.** Changing $r$ without adjusting $\alpha$ rescales the effective update by $\alpha(1/r_2 - 1/r_1)$. Symptom: loss curve flattens or diverges when you "just try a bigger rank." Fix: hold $\alpha/r$ fixed, or switch to rsLoRA's $1/\sqrt{r}$ scaling.
- **Gradient checkpointing with no gradient flow.** LoRA's forward branch depends on an input that, under naive gradient checkpointing, may not have `requires_grad` set, so no gradient reaches A/B. Symptom: loss is exactly constant across steps. Fix: `enable_input_require_grads()` or `prepare_model_for_kbit_training`.
- **Base revision mismatch at load time.** Saving only the adapter (the normal, correct thing to do) and later loading it against a different revision of the base silently degrades quality with no error. Fix: pin and record the base model hash.
- **Merging into a quantized base.** See above — dequantize first.

Full catalog: [[Gotchas - LoRA Fine-Tuning]].

## The non-obvious

The rank hypothesis is about *adapting an existing capability*, not injecting one. On instruction-following and style/format adaptation — tasks where the base model already has the relevant capability and needs to be steered — LoRA closes nearly all of the gap to full FT at $r$ as low as 8-16. On tasks requiring genuinely new skills the pretraining distribution under-covers (Biderman et al. 2024 measured this on code and math continued pretraining), the gap reopens and stays open even at high rank, because the update needed doesn't actually live in a low-rank subspace of the *existing* solution — see [[Concept - Why LoRA Underperforms Full Fine-Tuning]]. Treating "which regime am I in" as the first question, before touching rank or LR, saves most LoRA debugging sessions.

## Evolution

The line runs: intrinsic dimensionality (Aghajanyan et al. 2020, showing fine-tuning updates are low-rank in an absolute sense) → LoRA (Hu et al. 2021, operationalizing that as a trainable factorization) → [[Concept - QLoRA]] (Dettmers et al. 2023, quantizing the frozen base to 4-bit so the memory savings extend to the base weights themselves, not just the optimizer state) → a current wave of refinements attacking LoRA's specific weaknesses: [[Concept - DoRA]] (decomposing weight into magnitude and direction to recover full-FT-like learning dynamics), [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] (fixing the scaling law so high rank is actually usable), and [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] (starting the adapter somewhere smarter than zero). None of these have displaced vanilla LoRA as the default — they're increasingly composable add-ons on top of it, not replacements, and they mostly matter once you already understand [[Concept - Parameter-Efficient Fine-Tuning (PEFT)]] and where its baseline falls short.

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
