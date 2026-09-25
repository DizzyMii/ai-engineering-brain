---
tags: [concept, domain/evaluation, level/surface]
aliases: [Goodhart's Law]
summary: "A benchmark you optimize toward stops measuring the capability it was built to proxy — the general principle behind contamination, leaderboard-hacking, and reward hacking."
---
> **One-paragraph hook:** "When a measure becomes a target, it ceases to be a good measure." That's Marilyn Strathern's 1997 restatement of a point economist Charles Goodhart made about UK monetary policy in 1975. In model evaluation it's the mechanism behind almost every benchmark scandal. Once a lab starts optimizing toward a number (through data mix, architecture choices or explicit tuning), the number decouples from the capability it was meant to proxy, and every downstream decision made on it quietly gets worse.

## The mechanism

A benchmark score is a proxy: $\text{score} = f(\text{capability}) + \epsilon$, where $\epsilon$ is noise and idiosyncrasy specific to that benchmark's questions, format and scoring method. While nobody optimizes against the benchmark, $\epsilon$ stays small and uncorrelated with your training decisions, and the score tracks capability reasonably well.

Trouble starts as soon as the benchmark becomes a training-time or product-time target. Tune your data mixture (see [[Concept - Data Mixtures]]) toward benchmark-adjacent material, adjust architecture choices to help MCQ formats specifically, or optimize a leaderboard metric directly, and you're optimizing $f(\text{capability}) + \epsilon$ instead of capability. $\epsilon$ is far easier to move than real capability (often it's just format-matching or memorization), so most of the optimization pressure goes into inflating $\epsilon$. The score rises and the thing it was supposed to measure doesn't rise with it.

Manheim & Garrabrant (2018) split this into four failure modes. The split is useful because a single "Goodhart's Law" label hides that the mechanisms differ:

- **Regressional Goodhart:** proxy and target are correlated but not identical, so picking extreme proxy values partly selects for noise. You pick the model that got lucky on this benchmark's item distribution, which isn't necessarily the most capable one.
- **Extremal Goodhart:** relationships that hold in the normal range break down at the extremes strong optimization reaches. Behavior at 95%+ benchmark accuracy isn't a linear extrapolation of behavior at 60%.
- **Causal Goodhart:** you move the proxy through a path that never touches the target (e.g., training on near-benchmark data raises the score with zero capability gain).
- **Adversarial Goodhart:** an agent (a lab chasing leaderboard position) games the proxy on purpose, knowing it's being watched.

## In practice

The cleanest quantified example of decoupling is GSM1k (Zhang et al. 2024). The authors built fresh GSM8K-style grade-school math problems (same difficulty, same format, no overlap with the original test set) and reran existing models. Several model families dropped 8-13 points against their GSM8K scores, with some Mistral and Phi checkpoints hit hardest; frontier models (GPT-4/Claude-class at the time) held up comparatively well. The gap between GSM8K and GSM1k performance directly measures how much of a model's GSM8K score was capability and how much was overfit to that test distribution.

Leaderboard hillclimbing is the product-facing version. AlpacaEval's win-rate could be gamed just by making outputs longer. Judges (see [[Concept - LLM-as-Judge]]) systematically preferred verbose answers regardless of quality, so a length-tuning pass could inflate win-rate with no quality gain. The benchmark authors shipped a length-controlled variant (AlpacaEval 2.0 LC) to close the loophole. MT-Bench shows a related style-gaming pattern, where confident, well-formatted answers win whether or not they're correct.

[[Concept - Benchmark Contamination]] is Goodhart's Law at the data layer: training on near-distribution or verbatim test data is the causal-Goodhart failure, run at pretraining-corpus scale instead of through explicit tuning. [[Concept - Reward Hacking]] is the RL-training-time cousin. An RL policy exploits a flawed reward model the way a lab exploits a flawed benchmark, and the mechanism (optimization pressure decoupling proxy from target) is the same. This note owns the general principle; that one owns the training-loop mechanics.

## Failure modes

**Symptom:** a model's benchmark score rises across checkpoints or generations while performance on held-out, fresh or real-world tasks stays flat or degrades. **Detection:** run a freshly built variant of the benchmark (GSM1k-style) or a distribution-shifted version and compare deltas. A large capability-vs-benchmark gap is the tell.

**Symptom:** a leaderboard win-rate correlates suspiciously well with a superficial feature (output length, markdown formatting) instead of with task success. **Detection:** regress the metric directly on the superficial feature; AlpacaEval's own length-controlled analysis is the template.

**Symptom:** the score jumps after a data-mixture or fine-tuning change with no plausible mechanism for a real capability gain. **Detection:** check for direct or near-duplicate overlap between the new data and the benchmark's test items (n-gram or embedding overlap, per [[Concept - Membership Inference for Contamination Detection]] techniques).

## The non-obvious

Goodhart pressure doesn't need intent. A lab can decouple a benchmark from reality just by using it honestly as its main target for months of ablations. Every architecture and data decision that "helps the eval" without a controlled capability check implicitly selects for $\epsilon$ along with capability, and nobody has to be trying to cheat. So the standard defenses are structural, not behavioral: private/held-out sets that can't be optimized against directly; rotating/templated benchmarks like GSM-Symbolic that generate fresh instances so memorizing the item set doesn't help; deliberate evaluation under distribution shift; and tracking the correlation between benchmark score and real downstream task success over time, so a widening gap gets caught before it compounds. [[Concept - Private and Dynamic Benchmarks]] covers the mechanics of each.

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
