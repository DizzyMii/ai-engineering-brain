---
tags: [concept, domain/architectures, level/advanced]
aliases: [Pre-LN, Post-LN, Pre-Norm, Post-Norm, DeepNorm]
summary: "Where LayerNorm/RMSNorm sits relative to the residual add — the single choice that decides whether a deep transformer trains at all."
---
# Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)
> **One-paragraph hook:** There are two ways to write `x = x + f(x)` with a norm somewhere nearby, and they train very differently at depth. One needs a fragile warmup schedule and caps out around a few dozen layers. The other trains stably to hundreds of layers but silently inflates activation magnitude along the way. Every transformer author picks one, and months later the pick shows up as either a divergence at step 500 or a representation-collapse plateau at layer 80.

## The mechanism
The original transformer (Vaswani et al. 2017) is **post-norm**: normalization comes *after* the residual add.

$$x \leftarrow \text{Norm}(x + \text{Sublayer}(x))$$

Each block's output is renormalized to a fixed scale, so activations stay well-behaved from layer to layer. The cost is in backprop. The gradient path from the loss to layer 1 goes *through* every intervening `Norm`, and norm layers aren't gradient-neutral: their Jacobian scales and rotates the gradient, and that compounds over depth. Past roughly 20-30 layers, post-norm transformers become unstable to train without a long, carefully tuned learning-rate warmup. Skip or shorten the warmup and loss diverges in the first few hundred steps.

**Pre-norm** (GPT-2 onward) moves the norm inside the sublayer call:

$$x \leftarrow x + \text{Sublayer}(\text{Norm}(x))$$

The residual path is now a pure identity. Only addition sits between layer 1's output and the final layer, so gradients reach early layers undamped (see [[Concept - The Residual Stream]]). That's why pre-norm trains stably at depths post-norm can't reach, and why essentially every LLM since GPT-2 uses it.

The price is architectural. Every block *adds* to `x` and the stream itself is never renormalized, so `Var(x)` grows roughly monotonically with depth. Late layers get an input whose magnitude dwarfs any single sublayer's contribution, and `Norm(x)` at layer 80 looks nearly the same whether or not layer 80's own update fires. The layer's effective contribution to the stream shrinks relative to everything before it. Liu et al. (2020) called this **representation collapse**: in very deep pre-norm stacks, late layers stop doing useful work because their normalized input can barely be moved.

**DeepNorm** (Wang et al. 2022) is a post-norm variant built to remove the warmup fragility while keeping activation growth bounded. It scales the residual branch by a constant $\alpha > 1$ before the add, and scales down the sublayer's initialization by a constant $\beta < 1$:

$$x \leftarrow \text{Norm}(\alpha \cdot x + \text{Sublayer}(x))$$

Up-weighting by $\alpha$ keeps the residual signal dominant, which approximates the pre-norm gradient highway, while post-norm's per-layer renormalization bounds activation growth. With it the authors trained a 1000-layer transformer without instability, which neither vanilla post-norm nor vanilla pre-norm manages at that depth.

**Sandwich norm** puts a norm both before *and* after the sublayer: `x <- x + Norm_out(Sublayer(Norm_in(x)))`. The idea comes from CogView/NormFormer-era work, and Gemma 2 revived it at frontier scale in 2024 to control activation growth while keeping pre-norm's trainability. It composes with **QK-norm** and soft-capped final logits (see [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]]), which go after the same growing-magnitude problem at the attention-score and logit level instead of at the residual add.

```
post-norm block:            pre-norm block:              DeepNorm block:
  x ---> Sublayer ---> +       x ----------------> +         x --*alpha--> + <---- Sublayer(x)
         ^             |       |                    |                     ^
  x -----+          Norm       +---> Norm --> Sublayer      Norm(...)------+
                       |        (residual, untouched)
                       v
                    x' (renormalized)
```

## In practice
Nearly every production LLM as of 2026 is pre-norm + [[Concept - RMSNorm and LayerNorm]]: LLaMA, Mistral, Qwen, GPT-3/4-class models. The warmup gap is concrete. Post-norm models typically need thousands of warmup steps and a lower peak LR to avoid early divergence. Pre-norm models tolerate much shorter warmups, since the gradient highway doesn't pass through a norm.

The field hasn't fully converged, though. Gemma 2's sandwich norm plus QK-norm is a direct, scale-tested rebuttal to "pre-norm solved it," and it exists because pure pre-norm's residual growth becomes a real quality problem past a few dozen layers at frontier parameter counts. DeepNorm-style scaling appears wherever people push layer count far past the ~100-layer range plain pre-norm handles comfortably.

## Failure modes
- **Post-norm divergence at depth.** Stack past ~20-30 layers without DeepNorm-style scaling or an aggressive warmup and loss goes to NaN or explodes in the first few hundred steps. Watch gradient norm at the first block: before the NaN it spikes orders of magnitude above later blocks.
- **Pre-norm representation collapse.** In deep pre-norm stacks, late layers produce output barely different from a no-op. It shows up as near-zero relative update norm (`||Sublayer(Norm(x))|| / ||x||`) at late layers, and as marginal loss improvement per added layer past a certain depth (Liu et al. 2020).
- **Residual-scale loss spikes.** Mid-run loss spikes at scale frequently trace back to normalization placement interacting with residual-stream magnitude growth and attention-logit blowup. [[Concept - Training Stability and Loss Spikes]] has the broader diagnostic playbook.
- **Warmup mismatch when porting recipes.** Copying a pre-norm model's short warmup onto a post-norm architecture, or the reverse, is a common cause of "this recipe worked for X but not for Y" bug reports.

## The non-obvious
Practitioners still repeat "pre-norm won, case closed," and that's slightly stale folklore. Pre-norm doesn't eliminate the depth problem. It trades an *optimization* failure (divergence) for a *capacity* failure: late layers do less work, and the growing activation magnitude feeds downstream massive-activation and attention-sink pathologies. Gemma 2 going back to sandwich norm at frontier scale is the field admitting as much. The choice is a live tradeoff between "trains easily but wastes late-layer capacity" and "uses capacity fully but needs a fragile schedule," with no single right answer.

## Connections
- [[Concept - RMSNorm and LayerNorm]] — normalization placement is about *where* this operation sits, not what it computes; the two notes are complementary halves of the norm story.
- [[Concept - The Residual Stream]] — placement decides whether the residual stream stays a clean gradient highway or accumulates unbounded magnitude with depth.
- [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]] — QK-norm and soft-capping attack the same growing-magnitude problem at the attention-score level, and Gemma 2 combines them with sandwich norm.
- [[Deep Dive - The Transformer]] — placement is one of the block-level choices this deep dive assembles into the full architecture.
- [[Concept - Backpropagation]] — the mechanism by which post-norm's extra Jacobian in the gradient path causes instability at depth; the down-link prerequisite for this note.
- [[Deep Dive - Anatomy of a Pretraining Run]] — warmup schedule tuning is chosen jointly with normalization placement in any real pretraining run.
- [[Concept - Training Stability and Loss Spikes]] — mid-run loss spikes are a top-level symptom whose root cause is frequently normalization placement and residual scaling.
- [[Lore - The Standardization of the Transformer Block]] — the historical narrative of how the field converged (imperfectly) on pre-norm + RMSNorm as the default block.

## Sources
- Vaswani et al. (2017) — "Attention Is All You Need." Defines the original post-norm block.
- Liu et al. (2020) — "Understanding the Difficulty of Training Transformers." Names and diagnoses pre-norm representation collapse.
- Wang et al. (2022) — "DeepNet: Scaling Transformers to 1,000 Layers." Introduces DeepNorm's residual up-scaling plus init down-scaling.
- Google DeepMind, Gemma 2 Technical Report (2024) — describes the sandwich-norm plus QK-norm combination used at scale.
