---
tags: [lore, domain/esoterica, level/unicorn]
aliases: [3e-4, Grad-Student Descent, Magic Hyperparameters, Divine Benevolence]
summary: "The war stories and superstitions behind the magic hyperparameters everyone copies without deriving — and the invariances that make copying work."
---

## What happened

There is a set of numbers that appears, nearly unchanged, in almost every large training config: learning rate `3e-4`, ~2000 steps of linear warmup, AdamW with betas `(0.9, 0.95)`, epsilon `1e-8`, weight decay `0.1`, gradient clip `1.0`. Very few of the people typing them can derive them. They are copied lineage-to-lineage like a recipe passed down without the chemistry — and, remarkably, they mostly work. This is the folklore layer of deep learning, and it is real working knowledge, not ignorance.

**The `3e-4` legend.** In 2016 Andrej Karpathy tweeted "3e-4 is the best learning rate for Adam, hands down." It was half a joke, and it became genuine folklore — dropped into countless configs as a default. The reason the joke keeps landing is mechanical: Adam's update is approximately *scale-invariant*. The step is
$$\Delta\theta_t = -\,\eta\,\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon},\qquad \hat m_t \approx \mathbb{E}[g],\ \ \hat v_t \approx \mathbb{E}[g^2].$$
If you scale the loss (and hence every gradient) by a constant $c$, both $\hat m$ and $\sqrt{\hat v}$ scale by $c$, so the ratio is unchanged and the step size in *parameter units* stays $\approx\eta$ regardless of gradient magnitude. A single learning rate therefore transfers across problems that would need very different rates under raw SGD. See [[Concept - Adam and AdamW]] for the moment estimates this rests on. The lesson buried in the meme: the constant is robust because the optimizer removed the scale you would otherwise have to tune for.

**Warmup superstition.** Linear LR warmup over ~2000 steps (or 0.1–1% of the run) is near-universal in [[Concept - Learning Rate Schedules for Pretraining]], and under-explained. The leading account is that Adam's second-moment estimate $\hat v_t$ is high-variance early — it is an average over only a handful of gradients, so $1/\sqrt{\hat v_t}$ can spike and produce enormous first steps that corrupt the initialization. RAdam (Liu et al. 2019, "On the Variance of the Adaptive Learning Rate") tried to *rectify* this analytically and remove warmup entirely. It works, and almost nobody uses it: plain warmup is one line, has no failure modes, and "just works," so the superstition persisted over the principled fix.

**Batch-size folklore.** Two results anchor it. The linear scaling rule (Goyal et al. 2017, "Accurate, Large Minibatch SGD: Training ImageNet in 1 Hour") — scale the LR linearly with batch size and warm up — let them train ImageNet in an hour and made large-batch training routine. The [[Concept - Critical Batch Size]] (McCandlish et al. 2018, "An Empirical Model of Large-Batch Training") explains the ceiling: the *gradient noise scale* sets a batch size past which extra examples buy wall-clock time but not sample efficiency — you take the same number of optimizer steps, just faster per step. That single fact sets the economics of every large run: it tells you when adding GPUs stops reducing time-to-loss.

**The divine-benevolence quote.** Noam Shazeer's 2020 note "GLU Variants Improve Transformer" — the paper that put SwiGLU into the modern transformer — ends: *"We offer no explanation as to why these architectures seem to work; we attribute their success, as all else, to divine benevolence."* It is the field's most honest one-liner. SwiGLU beats GELU/ReLU in the [[Concept - Feed-Forward Networks and GLU Variants]], reliably, and the best paper on the subject explicitly declines to say why. That sentence is the entire domain in miniature.

**The betas nobody re-derives.** Adam's library default is `(0.9, 0.999)`, but LLM configs quietly use `(0.9, 0.95)`. The reason is the effective memory of the second-moment EMA, $\approx 1/(1-\beta_2)$: `0.999` averages over ~1000 steps, `0.95` over ~20. At LLM batch sizes and step counts the 1000-step horizon is too sluggish — it lags real curvature changes — so labs shortened it, and then everyone copied `0.95` without re-deriving it for their own batch size. The same is true of epsilon (`1e-8` vs `1e-6`, and whether it sits inside or outside the square root): copied, not chosen.

**Ritual and reproducibility.** Around the numbers sits a culture: "babysitting the run," staring at `loss.png` for the tell of an impending spike, the reputation of lucky seeds, and *grad-student descent* — manual hyperparameter search dressed up as methodology. muP (Yang et al. 2022, "Tensor Programs V") offers a principled escape: parameterize so that optimal hyperparameters *transfer across width*, tune on a small proxy model, and reuse the settings at scale — see [[Concept - muP and Hyperparameter Transfer]]. Few teams adopt the full recipe (it constrains initialization, LR, and multipliers together), so guess-and-check endures alongside it.

## The lesson

Each of these constants encodes a real invariance that nobody bothers to re-derive per run: `3e-4` rides Adam's scale-invariance; warmup patches the early-variance of the second moment; the linear scaling rule + critical batch size are the gradient-noise-scale physics of large batches; `β2=0.95` sets the curvature-tracking horizon. Copying the number is usually correct *because the underlying invariance holds* — which is exactly why the folklore is robust and worth cataloging rather than sneering at.

It bites precisely when the invariance breaks. Push batch size past the critical point and the linear scaling rule silently stops helping. Change width without muP and the "transferred" LR is now wrong. Move to a very different data distribution and the copied warmup length may be too short for the new second-moment variance. The failure mode of folklore is that it fails *silently*, at the seams where the unstated assumption no longer holds — you get a slightly worse model, not an error. This is what the [[Deep Dive - Anatomy of a Pretraining Run]] and the numbers in [[Reference - Architecture Numerology]] are for: to make the invariances explicit so you know when copying is safe.

## Evidence status

**Verified:** the quotes and papers are all public and citable — Karpathy's 2016 tweet, Shazeer 2020, Goyal et al. 2017, McCandlish et al. 2018, Liu et al. 2019 (RAdam), Yang et al. 2022 (muP). **Well-sourced folklore:** the scale-invariance explanation for `3e-4` and the critical-batch-size economics are solidly theorized. **Labeled folklore (weakly theorized, strongly practiced):** the precise *causal* story for why 2000-step warmup is the right length, and why `β2=0.95` specifically (rather than `0.98` or `0.9`) — these are copied by convention and rationalized after the fact more than derived, which is exactly what makes them unicorn knowledge. This is the same empirical-over-rigor culture catalogued in [[Lore - Machine Learning Is Alchemy]] and lived out step-by-step in the [[Lore - The OPT-175B Logbook]].

## Connections
- [[Concept - Adam and AdamW]] — the scale-invariant update that makes a single learning rate transfer; the source of `3e-4`.
- [[Concept - The Training Loop]] — where warmup, clipping, and the betas actually live in code.
- [[Concept - Learning Rate Schedules for Pretraining]] — the warmup-then-decay schedule the superstition is about.
- [[Concept - Critical Batch Size]] — the gradient-noise-scale limit behind the batch-size folklore and its economics.
- [[Concept - muP and Hyperparameter Transfer]] — the principled alternative to grad-student descent, rarely fully adopted.
- [[Concept - Feed-Forward Networks and GLU Variants]] — home of SwiGLU, the "divine benevolence" architecture that works for no stated reason.
- [[Reference - Architecture Numerology]] — the tabulated constants this note tells the war stories behind.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where these settings are chosen and babysat in a real run.
- [[Lore - Machine Learning Is Alchemy]] — the parent argument for why folklore is legitimate knowledge in this domain.
- [[Lore - The OPT-175B Logbook]] — a documented run where the babysitting-and-superstition culture is on display.

## Sources
- Karpathy (2016, tweet) — "3e-4 is the best learning rate for Adam, hands down." Half-jest that became a real default.
- Shazeer (2020) — *GLU Variants Improve Transformer*. Ends with the "divine benevolence" line; introduced SwiGLU.
- Goyal et al. (2017) — *Accurate, Large Minibatch SGD (ImageNet in 1 Hour)*. Linear LR scaling rule + warmup.
- McCandlish et al. (2018) — *An Empirical Model of Large-Batch Training*. Gradient noise scale and critical batch size.
- Liu et al. (2019) — *On the Variance of the Adaptive Learning Rate (RAdam)*. Explains and tries to remove warmup.
- Yang et al. (2022) — *Tensor Programs V (muP)*. Hyperparameter transfer across width; the principled cure that few fully adopt.
