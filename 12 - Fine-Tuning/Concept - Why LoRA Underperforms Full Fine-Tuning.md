---
tags: [concept, domain/fine-tuning, level/unicorn]
aliases: [LoRA gap, LoRA Learns Less and Forgets Less, intruder dimensions]
summary: "Mechanistic account of the LoRA vs full fine-tuning quality gap: rank limits, intruder dimensions, coverage, and when it vanishes."
---

# Concept - Why LoRA Underperforms Full Fine-Tuning

> **One-paragraph hook:** The pitch for LoRA is "as good as full fine-tuning at a fraction of the memory." That is true for instruction-following, tone, format, and style — and false the moment you try to teach a genuinely new skill or domain. The gap is not noise and it is not a tuning failure you can always grind away; it is a structural consequence of constraining the weight update to a low-rank subspace. This note is the mechanistic account of *when* the gap appears, *when* it vanishes, and *why* two fine-tunes with identical benchmark scores can still be different solutions with different downstream robustness.

## The mechanism

Full fine-tuning is free to move the weight matrix $W \in \mathbb{R}^{d \times k}$ anywhere; the update $\Delta W$ can be full rank. The [[Deep Dive - LoRA]] low-rank update constrains it to $\Delta W = \frac{\alpha}{r} B A$ with $\mathrm{rank}(\Delta W) \le r$, a low-rank [[Concept - Matrix Multiplication as the Atom of Deep Learning|matrix product]]. Whether that constraint costs you depends entirely on the *intrinsic rank of the task's update*:

- **Adapting an existing capability** (make the model answer in JSON, refuse a category, adopt a house tone) has low intrinsic rank — Aghajanyan et al. 2020 ("Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning") showed fine-tuning objectives live on a surprisingly small subspace, and Hu et al. 2021 built LoRA on exactly that observation. Here $r = 8\text{–}16$ suffices and LoRA ≈ full FT.
- **Acquiring a new skill or domain** (a programming language poorly represented in pretraining, arithmetic reasoning learned from a base model, a non-Latin script) needs a high-rank update. The rank budget you can afford ($r$ in the tens) is smaller than the update the task actually wants, so LoRA underfits no matter how clean the data is.

The load-bearing empirical result is **Biderman et al. 2024** (Databricks, "LoRA Learns Less and Forgets Less"): on **code and math continued pretraining**, LoRA underperforms full FT *substantially* — and raising rank narrows but does not close the gap in the regime you can practically train. On **instruction fine-tuning**, the same setup shows the gap nearly disappears. Effective learning capacity scales with rank, echoing the [[Concept - Scaling Laws|scaling-law]] intuition that capability tracks a resource budget — but the budget here is the rank of the update, and hard domains want more of it than is practical.

### Intruder dimensions — matching a number is not matching a solution

The subtler finding is **Shuttleworth et al. 2024** ("LoRA vs Full Fine-Tuning: An Illusion of Equivalence"). Take the SVD of the trained update $\Delta W$ and compare spectra:

- **Full FT** nudges the *existing* singular directions of $W$ — the update stays roughly aligned with the pretrained weight's structure.
- **LoRA** introduces brand-new high-ranking singular vectors — **"intruder dimensions"** — that are nearly orthogonal to anything in $W$'s original spectrum.

Even when in-domain accuracy is identical, models carrying intruder dimensions show **worse continual learning and more out-of-distribution brittleness**. Two solutions that agree on your eval set have different geometry, and the geometry predicts what happens off-distribution. This is why "LoRA matched full FT on our benchmark" is a weaker claim than it sounds — it connects to why generalization is not a single scalar, a theme running through phenomena like [[Concept - Double Descent]].

### Rank saturation and the scaling interaction

A natural response is "just raise the rank." Two traps:

1. Naively raising $r$ without fixing the $\alpha/r$ scaling **collapses the effective learning rate** — see [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]]. This produces the false folklore that "rank doesn't help past 16."
2. Even with *correct* $\alpha/\sqrt{r}$ scaling, high rank alone does not fully recover full-FT quality, because the update subspace differs *qualitatively* (the intruder-dimension result), not just in dimension.

### Coverage beats rank

The single highest-leverage fix is target-module coverage. The original paper applied LoRA to attention $q,v$ only; applying it to **all linear layers** (including the MLP gate/up/down projections) recovers much of the gap. Empirically, going from $q,v$-only to all-linear buys more quality than doubling rank on a narrow module set.

## In practice

Decide by asking whether the gap is *shape* or *substance*:

| Target | Intrinsic rank | Recommendation |
|---|---|---|
| Instruction/tone/format/refusal style | Low | LoRA, $r=16$, all-linear — gap is negligible |
| Fixed classification scheme, output schema | Low | LoRA is fine |
| New programming language, math from base | High | Full FT, or [[Concept - DoRA]] + high rank + rsLoRA; expect a residual gap |
| New knowledge/facts | N/A (wrong tool) | Not a rank problem — see [[Concept - What Fine-Tuning Can and Cannot Teach]] |

Concretely, Biderman's code experiments show full FT clearly ahead across ranks on HumanEval-style tasks, while their instruction-tuning runs have LoRA and full FT overlapping within noise. When you do need to close the gap, the ordering of fixes by payoff is: all-linear coverage → [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)|principled initialization]] → DoRA → higher rank with rsLoRA → full FT of a few layers. The [[Reference - PEFT Method Comparison]] tabulates where each method lands.

## Failure modes

- **"LoRA can't learn my domain."** Before concluding the method is at fault, rule out the four cheap causes: (a) $q,v$-only coverage, (b) too-low rank for a genuine new skill, (c) [[Concept - rsLoRA and the Rank-Alpha Scaling Trap|scaling collapse]] at high rank, (d) it is actually a knowledge-injection task LoRA structurally cannot do. **Detection:** as a diagnostic, full-FT a *few* layers and compare — if that closes the gap, it was capacity/coverage, not data.
- **Silent OOD brittleness.** In-domain metrics look great; robustness quietly degrades because of intruder dimensions. **Detection:** you will never see this on the training distribution — you must hold out a *distribution-shifted* eval and a continual-learning probe (fine-tune again on a second task and measure retention). A fine-tune evaluated only in-domain is untested for exactly the failure LoRA is prone to.
- **Forgetting mistaken for the gap.** A LoRA that "got dumber" may not have underfit the target at all — it may have overwritten general capability. That is the mirror image of this note; see [[Concept - Catastrophic Forgetting]].

## The non-obvious

**The gap and the forgetting are the same coin.** Biderman's title is not two findings, it is one: LoRA *learns less* **and** *forgets less* for the identical reason — a frozen base plus a small, low-rank update keeps you near the pretrained basin. That proximity is a regularizer. You cannot extract full-FT-level acquisition and LoRA-level preservation from the same knob, because they are the *same* knob pointed in opposite directions. Asking "why does LoRA underperform?" is asking "why is LoRA a good regularizer?" — and the answer is the constraint you deliberately imposed.

**Second, benchmark equivalence hides spectral divergence.** Two fine-tunes can post identical eval numbers while having qualitatively different weight spectra, and the *difference* — not the average — predicts continual-learning and OOD behavior. The practical lesson: when a paper or a vendor claims "LoRA matched full FT," ask on which axis and off which distribution. In-domain parity is the easy half.

## Connections
- [[Deep Dive - LoRA]] — the base mechanism whose low-rank constraint is the root cause analyzed here.
- [[Concept - DoRA]] — the fix that reintroduces full-FT-like magnitude/direction decoupling and narrows the gap, especially at low rank.
- [[Concept - rsLoRA and the Rank-Alpha Scaling Trap]] — why "raise the rank" fails silently unless you also fix the scaling factor.
- [[Concept - LoRA Initialization (PiSSA, LoftQ, OLoRA)]] — starting the adapter on the base's principal subspace recovers part of the gap.
- [[Concept - Catastrophic Forgetting]] — the mirror image: the same proximity-to-base that caps learning also limits forgetting.
- [[Concept - What Fine-Tuning Can and Cannot Teach]] — separates the "not enough rank" gap from the "wrong tool entirely" knowledge-injection failure.
- [[Reference - PEFT Method Comparison]] — where LoRA and its gap-narrowing variants sit on quality vs cost.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the low-rank product $BA$ is the object whose rank is the whole story.
- [[Concept - Scaling Laws]] — capacity-scales-with-a-budget intuition, here with rank as the budget.
- [[Concept - Double Descent]] — a reminder that generalization is not a single scalar, which is why intruder-dimension geometry matters beyond the eval number.

## Sources
- Biderman et al. 2024 — "LoRA Learns Less and Forgets Less." The central evidence: large gap on code/math continued pretraining, small gap on instruction tuning; capacity scales with rank.
- Shuttleworth et al. 2024 — "LoRA vs Full Fine-Tuning: An Illusion of Equivalence." Introduces intruder dimensions and the in-domain-parity / OOD-divergence result.
- Hu et al. 2021 — "LoRA: Low-Rank Adaptation of Large Language Models." The low-rank hypothesis and the $q,v$-only default that later coverage work corrected.
- Aghajanyan et al. 2020 — "Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning." The low-intrinsic-dimension foundation LoRA rests on.
