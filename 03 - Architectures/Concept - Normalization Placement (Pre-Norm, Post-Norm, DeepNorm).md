---
tags: [concept, domain/architectures, level/advanced]
aliases: [Pre-LN, Post-LN, Pre-Norm, Post-Norm, DeepNorm]
summary: "Where LayerNorm/RMSNorm sits relative to the residual add — the single choice that decides whether a deep transformer trains at all."
---
# Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)
> **One-paragraph hook:** Two ways to write `x = x + f(x)` with a norm somewhere near it produce wildly different training dynamics at depth — one needs a fragile warmup schedule and caps out around a few dozen layers, the other trains stably to hundreds of layers but silently blows up activation magnitude as it goes. Every transformer author has to pick a side, and the pick shows up months later as either a divergence at step 500 or a representation-collapse plateau at layer 80.

## The mechanism
The original transformer (Vaswani et al. 2017) is **post-norm**: the normalization is applied *after* the residual add.

$$x \leftarrow \text{Norm}(x + \text{Sublayer}(x))$$

Every block's output is renormalized to a fixed scale, which keeps activations well-behaved layer to layer. The cost shows up in backprop: the gradient path from the loss back to layer 1 has to pass *through* every intervening `Norm`, and normalization layers are not gradient-neutral — their Jacobian scales and rotates the gradient, and this compounds over depth. Post-norm transformers beyond roughly 20-30 layers become unstable to train without a long, carefully-tuned learning-rate warmup; skip or shorten the warmup and loss diverges in the first few hundred steps.

**Pre-norm** (GPT-2 onward) moves the normalization inside the sublayer call:

$$x \leftarrow x + \text{Sublayer}(\text{Norm}(x))$$

Now the residual path is a pure identity — nothing but addition sits between layer 1's output and the final layer, so gradients flow to early layers undamped (see [[Concept - The Residual Stream]]). This is why pre-norm transformers train stably at depths post-norm can't reach, and it's why essentially every LLM since GPT-2 uses it. The price is architectural, not optimization-theoretic: because every block *adds* to `x` without ever renormalizing the stream itself, `Var(x)` grows roughly monotonically with depth. Late layers receive an input whose magnitude dwarfs any single sublayer's contribution, so `Norm(x)` at layer 80 looks nearly identical whether or not layer 80's own update fires — the layer's effective contribution to the stream shrinks relative to what came before. Liu et al. (2020) documented this as **representation collapse**: late pre-norm layers in very deep stacks stop doing useful work because their normalized input has nowhere left to move the needle.

**DeepNorm** (Wang et al. 2022) is a post-norm variant engineered specifically to kill the warmup fragility while keeping bounded activation growth. It rescales the residual branch by a constant $\alpha > 1$ before adding, and down-scales the sublayer's initialization by a constant $\beta < 1$:

$$x \leftarrow \text{Norm}(\alpha \cdot x + \text{Sublayer}(x))$$

The $\alpha$ up-weighting keeps the residual signal dominant (approximating the pre-norm gradient highway) while post-norm's per-layer renormalization bounds activation growth, letting the authors train a 1000-layer transformer without instability — something neither vanilla post-norm nor vanilla pre-norm can do at that depth.

**Sandwich norm** puts a norm both before *and* after the sublayer — `x <- x + Norm_out(Sublayer(Norm_in(x)))` — an idea from CogView/NormFormer-era work that Gemma 2 revived at frontier scale in 2024 specifically to control activation growth without giving up pre-norm's trainability. It composes with **QK-norm** and soft-capped final logits (see [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]]), which attack the same growing-magnitude problem at the attention-score and logit level rather than the residual-add level.

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
Nearly every production LLM as of 2026 is pre-norm + [[Concept - RMSNorm and LayerNorm]] — LLaMA, Mistral, Qwen, GPT-3/4-class models. The warmup asymmetry is concrete: post-norm models typically need thousands of warmup steps and a lower peak LR to avoid early divergence, while pre-norm models tolerate much shorter warmups because the gradient highway doesn't route through a norm. That said, the field has not fully converged — Gemma 2's sandwich norm and QK-norm combination is a direct, scale-tested rebuttal to "pre-norm solved it," and it exists precisely because pure pre-norm's residual growth becomes a real quality problem past a few dozen layers at frontier parameter counts. DeepNorm-style scaling shows up wherever people push layer count far beyond the ~100-layer range that plain pre-norm tolerates comfortably.

## Failure modes
- **Post-norm divergence at depth:** loss goes to NaN or explodes in the first few hundred steps once you stack past ~20-30 layers without DeepNorm-style scaling or an aggressive warmup. Detect by watching gradient norm at the first block — it will spike orders of magnitude above later blocks before the NaN.
- **Pre-norm representation collapse:** deep pre-norm stacks show late layers whose output barely differs from a no-op; measurable as near-zero relative update norm (`||Sublayer(Norm(x))|| / ||x||`) at late layers, and as marginal loss improvement per added layer past a certain depth (Liu et al. 2020).
- **Residual-scale loss spikes:** training-stability incidents at scale (loss spikes mid-run) frequently trace back to normalization placement interacting with residual-stream magnitude growth and attention-logit blowup — see [[Concept - Training Stability and Loss Spikes]] for the broader diagnostic playbook.
- **Warmup mismatch when porting recipes:** copying a pre-norm model's short warmup schedule onto a post-norm architecture (or vice versa) is a common cause of "this recipe worked for X but not for Y" bug reports.

## The non-obvious
The "pre-norm won, case closed" narrative practitioners repeat is folklore that's slightly stale: pre-norm doesn't eliminate the depth problem, it just trades an *optimization* failure (divergence) for a *capacity* failure (late layers doing less work, growing activation magnitude feeding downstream massive-activation and attention-sink pathologies). Gemma 2's return to sandwich norm at frontier scale is the field's own admission of that — the choice is a live tradeoff between "trains easily but wastes late-layer capacity" and "uses capacity fully but needs a fragile schedule," not a solved problem with one right answer.

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
