---
tags: [concept, domain/evaluation, level/surface]
aliases: [Goodhart's Law]
summary: "A benchmark you optimize toward stops measuring the capability it was built to proxy — the general principle behind contamination, leaderboard-hacking, and reward hacking."
---
> **One-paragraph hook:** "When a measure becomes a target, it ceases to be a good measure" — Marilyn Strathern's 1997 restatement of a point economist Charles Goodhart made about UK monetary policy in 1975. In model evaluation this is not a cute aphorism, it's the mechanism behind almost every benchmark scandal: the moment a lab starts optimizing toward a number (via data mix, architecture choices, or explicit tuning), that number decouples from the underlying capability it was supposed to proxy, and every downstream decision made on the number gets quietly worse.

## The mechanism

A benchmark score is a proxy: $\text{score} = f(\text{capability}) + \epsilon$, where $\epsilon$ is measurement noise and idiosyncrasy specific to that benchmark's questions, format, and scoring method. As long as nobody is optimizing against the benchmark, $\epsilon$ stays small and uncorrelated with your training decisions, so the score tracks the capability reasonably well.

The problem starts the instant the benchmark becomes a training-time or product-time target. If you tune your data mixture (see [[Concept - Data Mixtures]]) to include more benchmark-adjacent material, adjust architecture choices to specifically help MCQ formats, or directly optimize a leaderboard metric, you are now optimizing $f(\text{capability}) + \epsilon$ rather than capability itself — and because $\epsilon$ is far easier to move than actual capability (it's often just format-matching or memorization), most of your optimization pressure goes into inflating $\epsilon$, not capability. The score rises; the thing it was supposed to measure does not rise proportionally.

Manheim & Garrabrant (2018) formalize this into four distinct failure modes, useful because "Goodhart's Law" as a single label hides that the mechanisms are different:

- **Regressional Goodhart:** the proxy and the target are correlated but not identical, so selecting extreme values of the proxy selects partly for noise — you pick the model that got lucky on this benchmark's specific item distribution, not necessarily the most capable model.
- **Extremal Goodhart:** relationships that hold in the normal operating range break down at the extremes reached under strong optimization pressure — behavior at 95%+ benchmark accuracy is not a linear extrapolation of behavior at 60%.
- **Causal Goodhart:** you intervene on the proxy through a path that doesn't run through the target at all (e.g., training directly on near-benchmark data raises the score with zero capability gain).
- **Adversarial Goodhart:** an agent (a lab chasing leaderboard position) deliberately games the proxy, knowing it's being watched.

## In practice

The cleanest quantified example of decoupling is GSM1k (Zhang et al. 2024): the authors rebuilt fresh, GSM8K-style grade-school math problems — same difficulty, same format, no overlap with the original test set — and reran existing models. Several model families dropped 8-13 points relative to their GSM8K scores, with some Mistral and Phi checkpoints hit worst; frontier models (GPT-4/Claude-class at the time) stayed comparatively robust. The gap between GSM8K and GSM1k performance is a direct, quantified measurement of how much of a model's GSM8K score was capability versus overfit to that specific test distribution.

Leaderboard hillclimbing is the product-facing version. AlpacaEval's win-rate metric was gameable simply by making outputs longer — judges (see [[Concept - LLM-as-Judge]]) systematically preferred verbose answers independent of quality, so win-rate could be inflated by a length-tuning pass with no quality improvement. The benchmark authors shipped a length-controlled variant (AlpacaEval 2.0 LC) specifically to close this loophole. MT-Bench shows a related style-gaming pattern where confident, well-formatted answers win regardless of correctness.

[[Concept - Benchmark Contamination]] is Goodhart's Law applied at the data layer specifically: training on near-distribution or verbatim test data is the causal-Goodhart failure mode, executed at pretraining-corpus scale rather than through explicit tuning. [[Concept - Reward Hacking]] is the RL-training-time cousin: an RL policy exploits a flawed reward model the same way a lab exploits a flawed benchmark, and the mechanism (optimization pressure decoupling proxy from target) is structurally identical — this note owns the general principle; that note owns the training-loop-specific mechanics.

## Failure modes

**Symptom:** a model's benchmark score rises across training checkpoints or model generations while its performance on held-out, fresh, or real-world tasks stays flat or even degrades. **Detection:** run a freshly-constructed variant of the benchmark (GSM1k-style) or a distribution-shifted version and compare deltas; a large capability-vs-benchmark gap is the tell.

**Symptom:** a leaderboard win-rate correlates suspiciously well with a superficial feature (output length, markdown formatting) rather than task success. **Detection:** regress the metric against the superficial feature directly — AlpacaEval's own length-controlled analysis is the template.

**Symptom:** score improves sharply after a data-mixture or fine-tuning change with no plausible mechanism for a genuine capability jump. **Detection:** check for direct or near-duplicate overlap between the new data and the benchmark's test items (n-gram or embedding overlap, per [[Concept - Membership Inference for Contamination Detection]] techniques).

## The non-obvious

Goodhart pressure doesn't require intent. A lab can decouple a benchmark from reality just by using it honestly as the primary north star for months of ablations — every architecture and data decision that "helps the eval" without a controlled capability check is implicitly selecting for $\epsilon$ along with capability, and nobody involved needs to be trying to cheat. This is why the standard defenses are structural rather than behavioral: private/held-out sets that can't be directly optimized against, rotating/templated benchmarks like GSM-Symbolic that regenerate fresh instances so memorizing the item set doesn't help, deliberately evaluating under distribution shift, and tracking the correlation between benchmark score and real downstream task success over time so a widening gap gets caught before it compounds. See [[Concept - Private and Dynamic Benchmarks]] for the mechanics of each defense.

## Connections

- [[Concept - Benchmark Contamination]] — the specific data-leakage vector by which Goodhart decoupling happens at pretraining scale; this note owns the general principle, that one owns the vector.
- [[Concept - Private and Dynamic Benchmarks]] — the structural defenses (held-out sets, rotation, templating) that blunt Goodhart pressure by removing the ability to directly optimize against fixed items.
- [[Concept - Reward Hacking]] — the RL-training-time instance of the exact same decoupling mechanism, owned by domain 06.
- [[Concept - Scaling Laws]] — scaling laws are themselves a proxy relationship (loss vs. compute) that can decouple under the same regressional/extremal dynamics if used to justify decisions far outside their fitted regime.
- [[Concept - Data Mixtures]] — tuning the data mixture toward benchmark-adjacent content is the most common causal-Goodhart vector in practice.
- [[Concept - LLM-as-Judge]] — a judge that becomes an optimization target (verbosity-gamed win-rate) is Goodhart's Law playing out inside the judging mechanism itself.
- [[Concept - Membership Inference for Contamination Detection]] — the detection toolkit for the specific causal-Goodhart signature of training data overlapping benchmark items.
- [[Lore - Benchmark Scandals]] — the concrete war stories (Reflection-70B, AlpacaEval gaming, GSM1k) that this concept explains mechanically.

## Sources
- Goodhart, C. (1975) — Problems of Monetary Management: The U.K. Experience. Original formulation, in a central-banking context.
- Strathern, M. (1997) — 'Improving ratings': audit in the British University system. Coined the widely-quoted phrasing.
- Manheim, D. & Garrabrant, S. (2018) — Categorizing Variants of Goodhart's Law. The regressional/extremal/causal/adversarial taxonomy used above.
- Zhang et al. (2024) — A Careful Examination of Large Language Model Performance on Grade School Arithmetic (GSM1k). Quantifies the GSM8K overfit gap.
