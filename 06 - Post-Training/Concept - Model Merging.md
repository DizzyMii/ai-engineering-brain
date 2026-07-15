---
tags: [concept, domain/post-training, level/advanced]
aliases: [model soups, weight averaging, task arithmetic, TIES-merging, DARE, mergekit, frankenmerge]
summary: "Combining fine-tuned checkpoints by arithmetic on their weights — free at inference, no retraining, if they share a base."
---

# Concept - Model Merging
> **One-paragraph hook:** Two teams independently fine-tune the same base model on different skills, and instead of picking a winner or building an ensemble that doubles inference cost, you average the weights — for free, at inference time, with no retraining. Model merging exploits the fact that fine-tunes of a shared base stay close enough in weight space that arithmetic on checkpoints behaves like arithmetic on the skills they encode, and it quietly powered a large fraction of the open-weights leaderboard climbers of 2023–2024.

## The mechanism

The premise is linear mode connectivity: independently fine-tuned copies of the same base model, having started from an identical initialization and moved a relatively small distance during fine-tuning, tend to lie in the same connected low-loss basin of the loss landscape rather than in separate basins separated by a loss barrier. Wortsman et al. 2022 generalized the earlier SGD-noise version of this result (Frankle et al.) to *independently* fine-tuned models. Because the basin is roughly convex between these points, a straight-line interpolation between two or more checkpoints stays low-loss instead of crossing a barrier — which is what makes weight averaging work at all, unlike averaging two models trained from scratch with different random seeds.

**Model soups** (Wortsman et al. 2022) are the simplest case: average the weights of several fine-tunes of one base, $\theta_{soup} = \frac{1}{k}\sum_i \theta_i$ (uniform soup), or add checkpoints one at a time and keep each only if it improves a held-out metric (greedy soup). This beats the single best fine-tune and is free at inference — one forward pass, no ensembling cost.

**Task arithmetic** (Ilharco et al. 2022) treats the *delta* from fine-tuning as a portable object: the task vector $\tau = \theta_{ft} - \theta_{base}$ can be added to inject a skill, summed across several task vectors to compose skills ($\theta_{base} + \sum_i \lambda_i \tau_i$), or *negated* ($\theta_{base} - \tau$) to suppress or unlearn a behavior — the mechanism behind post-hoc toxicity or style removal without retraining.

**SLERP** (spherical linear interpolation) fixes a specific failure of linear averaging: interpolating two vectors linearly shrinks the resulting weight norm toward the midpoint of the path, which can hurt a model whose behavior is sensitive to activation scale. SLERP instead moves along the great-circle arc between two normalized weight vectors, preserving norm:

$$\text{slerp}(\theta_1, \theta_2, t) = \frac{\sin((1-t)\Omega)}{\sin\Omega}\theta_1 + \frac{\sin(t\Omega)}{\sin\Omega}\theta_2, \qquad \Omega = \arccos\!\left(\frac{\theta_1 \cdot \theta_2}{\Vert\theta_1\Vert \Vert\theta_2\Vert}\right)$$

but it is inherently pairwise — merging $k>2$ models needs a different operator.

**TIES** (Yadav et al. 2023) targets *interference* between several task vectors merged at once, in three steps: **T**rim each task vector to its top-magnitude fraction (zeroing small deltas, which are mostly noise), **E**lect a per-parameter consensus sign by majority vote across the contributing models (resolving cases where different fine-tunes push the same weight in opposite directions), then **M**erge by averaging only the values that agree with the elected sign. **DARE** (Yu et al. 2023) takes a complementary approach: randomly **D**rop 90–99% of each task vector's parameters (set to zero) **A**nd **RE**scale the survivors by $1/(1-p)$ to preserve the delta's expected magnitude — sparsifying task vectors so they collide less when summed. DARE and TIES compose (DARE-TIES is a standard preset in tooling), sparsifying first and resolving sign conflicts on what remains.

## In practice

`mergekit` (Arcee AI) is the de facto standard tool, implementing linear, SLERP, TIES, DARE, and "passthrough" merges through a YAML config. Passthrough merges — "frankenmerges" — don't average at all; they stack or duplicate *layers* from one or more checkpoints to increase depth without any training, as in SOLAR-10.7B's depth up-scaling and the community frankenmerge Goliath-120B (built from two independently fine-tuned 70B Llama-2 checkpoints). Typical DARE settings drop $p = 0.9$–$0.99$ of parameters per task vector; typical TIES trims keep the top 10–20% by magnitude. The whole operation is CPU-bound tensor arithmetic — no GPU training run, no gradient step — orders of magnitude cheaper than another round of [[Concept - Supervised Fine-Tuning (SFT)]] or a further pass of [[Decision - Choosing a Preference Optimization Algorithm|preference optimization]], and iterable in minutes, which is why merges proliferated on the Open LLM Leaderboard through 2023–2024.

## Failure modes

Merging only works across checkpoints that share the same base model and architecture (same tokenizer, same tensor shapes) — merging unrelated bases, even same-size ones, produces incoherent weights because there is no shared basin to interpolate through. Naive linear averaging of several task vectors without TIES's sign-election can silently cancel large, useful updates whenever two source models disagree on a parameter's sign — the net contribution washes out even though each individual fine-tune was strong on its own. Merge coefficients ($\lambda_i$ scaling each task vector) are sensitive: too high degrades base capability and coherence, too low has no measurable effect, and there is no principled default — teams grid-search or eval-sweep them. The most insidious failure is silent regression on unmeasured tasks: a merge tuned (explicitly via greedy soup, or informally by iterating configs until a leaderboard number improves) against one eval suite is a textbook Goodhart setup, the same pathology [[Concept - The Emergent Abilities Debate|benchmark-score-versus-real-capability]] gaps show up in elsewhere — merges that top a leaderboard have repeatedly been shown to regress badly on held-out capabilities nobody checked before shipping.

## The non-obvious

Merging's real precondition is quantitative, not just architectural: it works because RLHF/DPO/SFT fine-tunes typically stay within a small relative displacement of the base model in weight space — folklore, weakly sourced: a few percent by L2 norm is a common figure practitioners cite — which is exactly the regime where linear mode connectivity holds and interpolation doesn't cross a loss barrier. The same arithmetic fails outright between models trained from *different* random initializations, even with identical architecture and data, because permutation symmetry means functionally-identical neurons can sit in arbitrarily different weight coordinates across two independent training runs — there is no shared basin, and naively averaging two from-scratch models is close to averaging noise. (Neuron-matching approaches that permute one model to align with another before merging exist specifically to work around this, and are a substantially harder problem than merging fine-tunes of a shared base.) The practical upshot: model merging is a fine-tuning-regime trick riding on how conservative modern post-training already is, not a general weight-space free lunch — and [[Concept - Floating Point for Deep Learning]] rounding during averaging is rarely the bottleneck compared to getting the merge coefficients right.

## Connections
- [[Concept - Knowledge Distillation]] — the other free-standing way to combine or compress model capability, without a training loop of its own once outputs exist.
- [[Concept - Mixture of Experts Architecture]] — cross-domain: MoE keeps merged skills as separately routed experts at inference cost, where merging collapses them into one dense checkpoint for free.
- [[Concept - Supervised Fine-Tuning (SFT)]] — merging combines the outputs of independent SFT/DPO runs rather than replacing the need for them.
- [[Reference - Model Genealogy]] — cross-domain: merges are a real edge in the model lineage graph, not a footnote — many shipped open checkpoints are merges of other checkpoints.
- [[Concept - The Emergent Abilities Debate]] — cross-domain: benchmark-chasing merges are a sharp case study in the gap between eval score and real capability.
- [[Concept - Floating Point for Deep Learning]] — cross-domain: merge arithmetic happens in whatever precision the checkpoints are stored in, and precision interacts with how much of a small task vector actually survives averaging.
- [[Concept - Mode Connectivity and Flat Minima]] — cross-domain, up-link: the deeper theoretical grounding for why interpolating between fine-tunes doesn't cross a loss barrier.
- [[Decision - Choosing a Preference Optimization Algorithm]] — merging is frequently a cheaper alternative to running another full preference-optimization pass to combine skills.

## Sources
- Wortsman et al. (2022) — Model Soups: Averaging Weights of Multiple Fine-Tuned Models Improves Accuracy Without Increasing Inference Time.
- Ilharco et al. (2022) — Editing Models with Task Arithmetic.
- Yadav et al. (2023) — TIES-Merging: Resolving Interference When Merging Models.
- Yu et al. (2023) — Language Models are Super Mario: Absorbing Abilities from Homologous Models via DARE.
