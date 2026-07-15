---
tags: [concept, domain/fine-tuning, level/unicorn]
aliases: [rsLoRA, rank-stabilized LoRA, rank stabilization]
summary: "Why standard alpha/r scaling caps usable LoRA rank and how rank-stabilized LoRA's 1/sqrt(r) fix unlocks it."
---

# Concept - rsLoRA and the Rank-Alpha Scaling Trap

> **One-paragraph hook:** The $\alpha/r$ factor in LoRA looks like a cosmetic hyperparameter and is actually a load-bearing scaling term that decides how much rank buys you. With the conventional $\alpha/r$, the low-rank branch's contribution shrinks as rank grows, so high-rank LoRAs train sluggishly and plateau — the origin of the widespread and false belief that "rank doesn't help past 16." A one-character fix, $\alpha/\sqrt{r}$ (rank-stabilized LoRA, Kalajdzievski 2023), makes the update magnitude rank-invariant and actually unlocks high rank. The same $\alpha/r$ term is also the single most common *silent* misconfiguration in fine-tuning: because $\alpha$ and $r$ are separate knobs, copying someone else's $\alpha$ while changing $r$ quietly retunes your effective learning rate.

## The mechanism

The [[Deep Dive - LoRA]] update is $\Delta W = \gamma_r \, B A$ with scaling factor $\gamma_r = \alpha/r$ in the standard formulation, where $A \in \mathbb{R}^{r\times k}$ initialized $\sim \mathcal{N}(0,\sigma^2)$ and $B \in \mathbb{R}^{d\times r}$ initialized to zero. At init $\Delta W = 0$, but after a few steps both factors carry $O(1)$-scale entries, and that is where the rank dependence bites.

Consider a single entry of the product before scaling:

$$(BA)_{ij} = \sum_{l=1}^{r} B_{il}\, A_{lj}.$$

This is a sum of $r$ roughly-independent, mean-zero products (an inner product across the rank dimension — a [[Concept - Matrix Multiplication as the Atom of Deep Learning|matrix product]] contracting over $r$). Its variance grows $\propto r$, so its typical **magnitude grows $\propto \sqrt{r}$**. Multiply by the standard scaling and the LoRA branch's effective contribution scales as

$$\gamma_r \cdot \|BA\| \;\sim\; \frac{\alpha}{r}\cdot\sqrt{r} \;=\; \frac{\alpha}{\sqrt{r}} \;\xrightarrow{\ r\to\infty\ }\; 0.$$

The signal — **and its gradient**, since the same factor scales the backward pass — *decays* as you add rank. Large-$r$ LoRAs therefore learn more slowly per step and their gains flatten. Practitioners measured this, saw no improvement past $r\approx 16$, and concluded rank was useless. They were measuring a scaling artifact, not a capacity ceiling.

### The rsLoRA fix

**Kalajdzievski 2023** ("A Rank Stabilization Scaling Factor for Fine-Tuning with LoRA") sets

$$\gamma_r = \frac{\alpha}{\sqrt{r}}.$$

Now the effective contribution is $\frac{\alpha}{\sqrt{r}}\cdot\sqrt{r} = \alpha = O(1)$ — **rank-invariant** forward and backward magnitudes. The paper's result is that $\Theta(1/\sqrt{r})$ is the unique scaling *order* that keeps activations and gradients stable as $r\to\infty$; any faster decay (like $1/r$) collapses the branch, any slower blows it up. With rank stabilized, $r = 64$ or $256$ genuinely improve, unlocking the capacity hard domains actually need (the reason coverage-plus-rank matters is spelled out in [[Concept - Why LoRA Underperforms Full Fine-Tuning]]).

## In practice

- **Enable it above $r=32$.** HF `peft` exposes `use_rslora=True` in `LoraConfig`; Unsloth and most trainers pass it through. Below $r\approx 16$ the difference is small; above $r=32$, turn it on or expect the plateau. Typical numeric defaults are in [[Reference - Fine-Tuning Hyperparameters]].
- **The $\alpha=2r$ convention exists to defend against the trap, not because it's optimal.** Setting $\alpha=2r$ keeps $\alpha/r=2$ fixed as you vary $r$, so at least the *nominal* scale is stable. It is a heuristic guardrail, not theory — and under rsLoRA the scaling is $\alpha/\sqrt r$, so $\alpha$'s meaning changes: set it to control magnitude directly rather than cargo-culting $2r$.
- **Fix scaling first, then tune LR.** See below — these two knobs multiply, so tuning both independently is redundant work.

### The effective-learning-rate view

$\alpha/r$ (or $\alpha/\sqrt r$) is a **fixed multiplier on the update** that composes *multiplicatively* with the optimizer's learning rate. The optimizer step on the adapter and this scaling factor are two numbers multiplied together before they touch $W$. That has three consequences:

1. Tuning LR *and* $\alpha/r$ as independent knobs is redundant — you are sweeping a product. Fix the scaling regime ($\alpha/r$ or rsLoRA's $\alpha/\sqrt r$), then sweep [[Concept - Adam and AdamW|AdamW]]'s LR alone.
2. The folklore that "LoRA wants ~10× the full-FT learning rate" is entangled with this factor; part of that 10× is the $\alpha/r$ multiplier, not a property of LoRA optimization per se.
3. **The silent bug:** copy a config with $\alpha=32$ and change $r$ from 16 to 64, and the update multiplier moves from $\alpha/16$ to $\alpha/64$ — a factor of $1/4$ — while you thought you only changed rank. In additive terms the scaling shifts by $\alpha\left(\tfrac{1}{r_2}-\tfrac{1}{r_1}\right)$. Countless public configs were trained at an effectively wrong LR this way; the incident lives in [[Lore - LoRA Folklore and Hard-Won Defaults]], and the operational catch is in [[Gotchas - LoRA Fine-Tuning]].

## Failure modes

- **Loss flattens as you raise rank (LR unchanged).** Read as scaling collapse, *not* a capacity limit. **Detection:** rerun the exact config with `use_rslora=True`; if the higher rank now improves, the ceiling was the scaling factor. This is the diagnostic that separates a real capacity wall from the artifact.
- **Divergence after "just bumping alpha."** Raising $\alpha$ without lowering LR increases the effective step and can blow up training, because you moved the multiplier, not just a regularizer. **Detection:** loss spikes within the first few hundred steps after an $\alpha$ change with LR held constant.
- **Inherited config, silently mis-scaled.** You forked someone's rank-16 recipe to rank-64 and quality got *worse*, not better. **Detection:** compute the effective scale $\alpha/r$ (or $\alpha/\sqrt r$) for both the source and your config and compare — if it moved, your LR moved with it.

## The non-obvious

**"Rank doesn't matter past 16" is one of the most repeated pieces of LoRA folklore, and it is false — it is a measurement artifact of the $\alpha/r$ scaling.** The community's default rank ceiling was, in effect, set by a bug in the scaling factor rather than a property of low-rank adaptation. Once you replace $1/r$ with $1/\sqrt{r}$, the ceiling lifts, and the ranks that "never helped" start helping. It is a rare case where a one-line change in a normalization constant overturns a widely-held empirical belief — and a reminder that when a hyperparameter "stops mattering," the first suspect should be a scaling term hiding in the update, not the model's capacity. The gap-narrowing methods it composes with — [[Concept - DoRA]] and principled [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)|initialization]] — target *different* failure modes, so rsLoRA stacks with them rather than competing.

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
