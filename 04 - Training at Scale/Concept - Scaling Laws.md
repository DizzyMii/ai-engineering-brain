---
tags: [concept, domain/training-at-scale, level/core]
aliases: [neural scaling laws, Chinchilla scaling laws, compute-optimal scaling]
summary: "The power-law relationship between pretraining loss, model size, and data, and the compute-optimal N/D allocation it implies."
---

# Concept - Scaling Laws

> **One-paragraph hook:** Before you spend $50M on a training run, scaling laws let you predict, with real accuracy, how low the loss will go and how to split a fixed compute budget between model size and data to get there cheapest. They're also the single most consequential empirical result in modern LLM engineering. A 2022 correction to a 2020 paper (Chinchilla vs. Kaplan) changed how every later frontier model was sized.

## The mechanism

The empirical loss model:

$$L(N, D) = E + \frac{A}{N^{\alpha}} + \frac{B}{D^{\beta}}$$

$N$ is parameter count, $D$ is training tokens, $E$ is the irreducible entropy of the data distribution, and $A$, $B$, $\alpha$, $\beta$ are fitted constants. Chinchilla's fits give $\alpha \approx 0.34$, $\beta \approx 0.28$. Loss falls as a power law along both axes, and scaling either one alone gives diminishing returns that never reach zero.

Training compute is approximated as:

$$C \approx 6ND \text{ FLOPs}$$

Where the 6 comes from: each parameter does roughly 2 FLOPs (one multiply, one add) per token in the forward pass. The backward pass costs roughly twice the forward (one pass for gradients w.r.t. activations, one for gradients w.r.t. weights). Forward (2) + backward (4) = 6 FLOPs per parameter per token.

For a fixed compute budget $C$ there's an optimal split between $N$ and $D$ that minimizes $L$ subject to $C = 6ND$. You get it with a Lagrange-multiplier optimization over the fitted power law, and that's the actual mechanism behind "compute-optimal" model sizing.

## In practice

**Kaplan et al. (2020)** ran the first large-scale fits and concluded that at a fixed compute budget you should scale parameters much faster than data. That pushed early-2020s model design toward ever-larger, comparatively undertrained models. **Hoffmann et al. (2022), "Chinchilla,"** redid the analysis with **IsoFLOP profiles** (train many model sizes at each of several fixed compute budgets, find the loss-minimizing size per budget) plus a direct parametric fit of $L(N,D)$. They found Kaplan's conclusion was largely a methodology artifact: those runs didn't re-tune the learning-rate schedule length per run, which systematically favored larger models. Corrected, $N$ and $D$ should scale **roughly equally**, landing near **~20 tokens per parameter** at compute-optimal.

The standard illustration is **Gopher** (280B params, 300B tokens) against **Chinchilla** (70B params, 1.4T tokens). Both used roughly equal compute, and Chinchilla, 4x smaller, matched or beat Gopher on downstream benchmarks. That one comparison reset the field's intuition about the param/token ratio overnight.

The frontier has since moved past pure compute-optimality into **inference-optimal overtraining**. A deployed model's serving cost scales with parameter count and not with training tokens, so it's often worth spending extra training compute to shrink the final model. Llama-3 8B was trained on ~15T tokens, roughly **1875 tokens per parameter** and nearly 100x past the Chinchilla-optimal ratio: a deliberate trade of training compute for a smaller, cheaper-to-serve model.

**Budgeting a real run**: start from a compute number $C$ (GPU-hours × peak FLOPs/GPU × achieved MFU; see [[Deep Dive - Anatomy of a Pretraining Run]]). Solve $6ND = C$ under the Chinchilla-optimal ratio or your chosen overtraining multiple to get target $N$ and $D$, then convert $D$ to wall-clock with measured tokens/sec.

## Failure modes

- **Extrapolating a fitted law outside the compute range it was fit on.** Power-law fits are local approximations. Projecting one 10-100x past the largest run in the fit is a common and dangerous mistake.
- **Treating the constants as universal.** $A$, $B$, $\alpha$, $\beta$ and $E$ depend on architecture, tokenizer and data distribution, so a law fit on one data mixture doesn't transfer exactly to another (see [[Concept - Data Mixtures]]).
- **Conflating pretraining-loss improvement with downstream capability gains.** The loss curve is smooth and predictable and benchmark performance isn't. A model can follow a clean, expected loss trajectory while specific capabilities appear suddenly or never show up (see [[Concept - The Emergent Abilities Debate]]).
- **Ignoring the repeated-data regime.** The clean power law assumes fresh tokens. Once a corpus is exhausted and data repeats, returns degrade differently; that's its own regime, covered in [[Concept - Data-Constrained Scaling Laws]].

## The non-obvious

The Kaplan-to-Chinchilla correction was an experimental-methodology bug (an under-tuned learning-rate schedule) passing as a scientific finding, and it shaped a generation of model-sizing decisions before anyone caught it. The lesson generalizes. A scaling-law fit is only as trustworthy as the hyperparameter discipline of the runs behind it, and a power law with a suspiciously clean $R^2$ deserves the skepticism you'd give a benchmark number. Check that every point in the fit was run at its own optimum and not at whatever hyperparameters were convenient.

Loss is also a compressed signal. Two models with identical pretraining loss can differ sharply on a specific downstream task, because loss averages over the whole token distribution and any one capability lives in a thin slice of it.

## Connections
- [[Concept - Why Models Don't Fit on One GPU]] — the memory constraints that make the $N$ side of the compute-optimal tradeoff a hard engineering wall, not just a free variable.
- [[Concept - Data-Constrained Scaling Laws]] — what happens to this power law once fresh tokens run out and data must be repeated.
- [[Deep Dive - Anatomy of a Pretraining Run]] — where the compute budget $C$ derived here becomes an actual run configuration.
- [[Concept - Data Mixtures]] — the data-distribution dependence hiding inside the fitted constants $A$, $B$, $E$.
- [[Concept - The Emergent Abilities Debate]] — the downstream-capability side of the loss-vs-benchmark gap this note's failure modes warn about.
- [[Reference - Memory Math for Transformers]] — converts the target $N$ from a compute-optimal fit into an actual per-GPU memory budget.
- [[Concept - Critical Batch Size]] — batch size is the other lever (alongside $N$/$D$) that determines how efficiently a compute budget converts to loss reduction.
- [[Concept - Entropy and Cross-Entropy]] — the $E$ term in $L(N,D)$ is the irreducible cross-entropy floor of the data distribution.

## Sources
- Kaplan et al. (2020) — "Scaling Laws for Neural Language Models" — the original power-law fits; over-weighted parameter count due to an under-tuned LR schedule.
- Hoffmann et al. (2022) — "Training Compute-Optimal Large Language Models" (Chinchilla) — IsoFLOP profiling method, corrected fit, ~20 tokens/parameter at compute-optimal.
- Llama-3 team, Meta (2024) — Llama-3 8B trained on ~15T tokens, the reference example of deliberate inference-optimal overtraining far past the Chinchilla ratio.
