---
tags: [concept, domain/fine-tuning, level/unicorn]
aliases: [rsLoRA, rank-stabilized LoRA, rank stabilization]
summary: "Why standard alpha/r scaling caps usable LoRA rank and how rank-stabilized LoRA's 1/sqrt(r) fix unlocks it."
---

# Concept - rsLoRA and the Rank-Alpha Scaling Trap

> **One-paragraph hook:** the $\alpha/r$ factor in LoRA looks cosmetic. It's a scaling term that decides how much rank buys you. With the conventional $\alpha/r$, the low-rank branch's contribution shrinks as rank grows, so high-rank LoRAs train sluggishly and plateau. That's where the widespread, false belief that "rank doesn't help past 16" comes from. A one-character fix, $\alpha/\sqrt{r}$ (rank-stabilized LoRA, Kalajdzievski 2023), makes the update magnitude rank-invariant, and high rank starts paying off. The same $\alpha/r$ term is also the most common *silent* misconfiguration in fine-tuning. $\alpha$ and $r$ are separate knobs, so copying someone's $\alpha$ while changing $r$ quietly retunes your effective learning rate.

## The mechanism

The [[Deep Dive - LoRA]] update is $\Delta W = \gamma_r \, B A$, with scaling factor $\gamma_r = \alpha/r$ in the standard formulation, $A \in \mathbb{R}^{r\times k}$ initialized $\sim \mathcal{N}(0,\sigma^2)$ and $B \in \mathbb{R}^{d\times r}$ initialized to zero. At init $\Delta W = 0$. After a few steps both factors carry $O(1)$-scale entries, and that's when the rank dependence bites.

Take a single entry of the product before scaling:

$$(BA)_{ij} = \sum_{l=1}^{r} B_{il}\, A_{lj}.$$

It's a sum of $r$ roughly independent, mean-zero products, an inner product across the rank dimension (a [[Concept - Matrix Multiplication as the Atom of Deep Learning|matrix product]] contracting over $r$). Its variance grows $\propto r$, so its typical **magnitude grows $\propto \sqrt{r}$**. Multiply by the standard scaling and the LoRA branch's effective contribution goes as

$$\gamma_r \cdot \|BA\| \;\sim\; \frac{\alpha}{r}\cdot\sqrt{r} \;=\; \frac{\alpha}{\sqrt{r}} \;\xrightarrow{\ r\to\infty\ }\; 0.$$

The signal *decays* as you add rank, **and so does its gradient**, since the same factor scales the backward pass. Large-$r$ LoRAs learn more slowly per step and their gains flatten. Practitioners measured this, saw nothing past $r\approx 16$, and concluded rank was useless. What they measured was a scaling artifact, not a capacity ceiling.

### The rsLoRA fix

**Kalajdzievski 2023** ("A Rank Stabilization Scaling Factor for Fine-Tuning with LoRA") sets

$$\gamma_r = \frac{\alpha}{\sqrt{r}}.$$

The effective contribution becomes $\frac{\alpha}{\sqrt{r}}\cdot\sqrt{r} = \alpha = O(1)$: forward and backward magnitudes are **rank-invariant**. The paper shows $\Theta(1/\sqrt{r})$ is the unique scaling *order* that keeps activations and gradients stable as $r\to\infty$. Any faster decay (like $1/r$) collapses the branch, and any slower one blows it up. With rank stabilized, $r = 64$ or $256$ really do improve results, which gives hard domains the capacity they need ([[Concept - Why LoRA Underperforms Full Fine-Tuning]] explains why coverage plus rank matters).

## In practice

- **Turn it on above $r=32$.** HF `peft` exposes `use_rslora=True` in `LoraConfig`; Unsloth and most trainers pass it through. Below $r\approx 16$ the difference is small. Above $r=32$, enable it or expect the plateau. Typical numeric defaults are in [[Reference - Fine-Tuning Hyperparameters]].
- **The $\alpha=2r$ convention is a defense against the trap, not an optimum.** Setting $\alpha=2r$ keeps $\alpha/r=2$ fixed as $r$ varies, so at least the *nominal* scale holds still. It's a heuristic guardrail with no theory behind it. Under rsLoRA the scaling is $\alpha/\sqrt r$, so $\alpha$ means something different: set it to control magnitude directly instead of cargo-culting $2r$.
- **Fix scaling first, then tune LR.** The two knobs multiply (next section), so tuning both independently is wasted work.

### The effective-learning-rate view

$\alpha/r$ (or $\alpha/\sqrt r$) is a **fixed multiplier on the update** that composes *multiplicatively* with the optimizer's learning rate. The optimizer step on the adapter and the scaling factor are two numbers multiplied together before they touch $W$. Three consequences:

1. Tuning LR *and* $\alpha/r$ separately is redundant, because you're sweeping a product. Fix the scaling regime ($\alpha/r$ or rsLoRA's $\alpha/\sqrt r$), then sweep [[Concept - Adam and AdamW|AdamW]]'s LR alone.
2. The folklore that "LoRA wants ~10× the full-FT learning rate" is tangled up with this factor. Part of that 10× is the $\alpha/r$ multiplier, not a property of LoRA optimization itself.
3. **The silent bug:** copy a config with $\alpha=32$, change $r$ from 16 to 64, and the update multiplier goes from $\alpha/16$ to $\alpha/64$, a factor of $1/4$, while you think you only changed rank. In additive terms the scaling shifts by $\alpha\left(\tfrac{1}{r_2}-\tfrac{1}{r_1}\right)$. Countless public configs were trained at an effectively wrong LR this way. The story is in [[Lore - LoRA Folklore and Hard-Won Defaults]], and the operational check is in [[Gotchas - LoRA Fine-Tuning]].

## Failure modes

- **Loss flattens as you raise rank (LR unchanged).** Read it as scaling collapse, *not* a capacity limit. **Detection:** rerun the same config with `use_rslora=True`. If the higher rank now improves, the ceiling was the scaling factor. This diagnostic separates a real capacity wall from the artifact.
- **Divergence after "just bumping alpha."** Raising $\alpha$ without lowering LR increases the effective step and can blow up training; you moved the multiplier, which is more than a regularizer. **Detection:** loss spikes within the first few hundred steps after an $\alpha$ change with LR held constant.
- **Inherited config, silently mis-scaled.** You took someone's rank-16 recipe to rank-64 and quality got *worse*. **Detection:** compute the effective scale $\alpha/r$ (or $\alpha/\sqrt r$) for the source config and yours. If it moved, your LR moved with it.

## The non-obvious

**"Rank doesn't matter past 16" is one of the most repeated pieces of LoRA folklore, and it's false: a measurement artifact of the $\alpha/r$ scaling.** The community's default rank ceiling was in effect set by a bug in the scaling factor, not by any property of low-rank adaptation. Replace $1/r$ with $1/\sqrt{r}$ and the ceiling lifts; the ranks that "never helped" start helping. It's a rare case of a one-line change in a normalization constant overturning a widely held empirical belief. When a hyperparameter "stops mattering," suspect a scaling term hiding in the update before you blame the model's capacity. The other gap-narrowing methods, [[Concept - DoRA]] and principled [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)|initialization]], target *different* failure modes, so rsLoRA stacks with them.

## Connections
- [[Deep Dive - LoRA]] — defines $\Delta W = (\alpha/r)BA$; this note dissects the $\alpha/r$ term it treats as given.
- [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — high rank is one lever for closing the gap, but only after the scaling trap is fixed.
- [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] — an orthogonal knob (where the adapter starts) that composes with rank stabilization.
- [[Concept - DoRA]] — another orthogonal fix (magnitude/direction decoupling) that stacks with rsLoRA scaling.
- [[Reference - Fine-Tuning Hyperparameters]] — the numeric defaults for $r$, $\alpha$, and LR, with the scaling caveat flagged.
- [[Gotchas - LoRA Fine-Tuning]] — the operational checklist entry for "changed rank, forgot alpha."
- [[Lore - LoRA Folklore and Hard-Won Defaults]] — the war story of the $\alpha=2r$ cargo cult and the rank-16 ceiling.
- [[Concept - Adam and AdamW]] — the optimizer whose LR multiplies with $\alpha/r$; why tuning both independently is redundant.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the $\sum_l B_{il}A_{lj}$ contraction whose $\sqrt r$ growth drives the whole effect.

## Sources
- Kalajdzievski 2023 — "A Rank Stabilization Scaling Factor for Fine-Tuning with LoRA." Derives the $\alpha/\sqrt r$ scaling and shows $1/r$ collapses high-rank learning.
- Hu et al. 2021 — "LoRA: Low-Rank Adaptation of Large Language Models." Source of the $\alpha/r$ convention that the trap lives in.
