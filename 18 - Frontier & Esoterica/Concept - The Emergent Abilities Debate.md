---
tags: [concept, domain/esoterica, level/surface]
aliases: [emergent abilities, emergence mirage]
summary: "Whether LLM capability jumps at scale are real phase transitions or artifacts of discontinuous metrics — unresolved and safety-relevant."
---
> **One-paragraph hook:** In 2022 a widely-cited paper claimed LLMs acquire capabilities — 3-digit arithmetic, MMLU, word unscrambling — as sharp, unpredictable jumps at specific scale thresholds. A year later a NeurIPS best-paper rebuttal argued the jumps were mostly a mirage created by the choice of evaluation metric, not the model. The debate is still open, and which side is right determines whether you can forecast a model's dangerous capabilities before you train it.

## The mechanism
[[Concept - Scaling Laws]] describe smooth power-law relationships between compute/data/parameters and loss — a backdrop that holds even in the data-constrained regime studied by [[Concept - Data-Constrained Scaling Laws]]. Wei et al. 2022 ("Emergent Abilities of Large Language Models") observed something different at the *task* level: on benchmarks like 3-digit addition, MMLU subject accuracy, and word-unscrambling, performance sits near-random for a long stretch of model scale, then rises sharply to well above chance within a narrow band — often reported between roughly 10^22 and 10^24 training FLOPs depending on the task and model family. Crucially, the jump is *unpredictable* from the trend of smaller models: you cannot extrapolate a smooth curve through the sub-threshold points and see it coming.

Schaeffer et al. 2023 ("Are Emergent Abilities of Large Language Models a Mirage?", NeurIPS best paper) offered a deflationary account. Many of the benchmarks Wei et al. used score with **exact-match** or **multiple-choice accuracy** — metrics with a knife-edge threshold: you either get the whole k-token answer right or you get zero credit. If the model's *per-token* probability of being correct improves smoothly and continuously with scale (which it does, and which scaling laws already predict), then the probability of getting an entire k-token sequence exactly right scales roughly as

$$P(\text{exact match}) \approx p^k$$

where $p$ is the smooth per-token accuracy. This function is famously flat-then-steep: for $k=5$ and $p$ rising smoothly from 0.5 to 0.9, $p^k$ crawls from ~3% to ~59% — a sharp-looking cliff manufactured entirely by exponentiating a smooth curve. Swap the metric to something continuous — token-edit distance, per-token log-likelihood, Brier score — and the *same* underlying models produce smooth, predictable curves with no discontinuity. The claim isn't that the metric is "wrong," it's that the metric, not the model, is the source of the apparent phase transition.

The rebuttal to the rebuttal is that not everything folds under smoother metrics. Some capabilities — certain BIG-Bench "breakthrough" tasks, and novel in-context learning of tasks not seen in training — still show sharpness under continuous scoring. And [[Concept - Grokking]] is a clean existence proof that a network's internal representation *can* undergo a genuine discrete phase transition (a circuit forming, not a metric artifact) — so "sharp changes never happen in neural nets" is too strong a claim to make in general.

## In practice
The practical fingerprint of the mirage: if you re-plot a benchmark that shows an "emergent" curve using a continuous score, and the elbow disappears, that's evidence for artifact. If it survives, that's evidence for something structural. Anthropic, OpenAI, and DeepMind eval teams now routinely report both exact-match and continuous variants for exactly this reason — see [[Concept - Statistical Rigor in Model Evaluation]] for the broader methodology of not trusting a single metric's shape.

The debate also connects to **BIG-Bench**'s own "breakthroughness" and "linearity" scores, metrics designed specifically to quantify how discontinuous a task's scaling curve is, and to the discovery of [[Concept - Inverse Scaling and U-Shaped Scaling]] — tasks where accuracy *falls* with scale before later recovering. Non-monotone scaling is itself evidence that "capability vs. scale" is not a single clean curve you can extrapolate in either direction, which undercuts both the strong-emergence and the pure-mirage positions equally: the relationship is more complicated than either side's cleanest story.

## Failure modes
- **Forecasting on exact-match curves.** If you evaluate a capability only with strict exact-match and see it flat near zero up to your largest checkpoint, you cannot conclude the capability won't appear at the next scale step — the mirage argument says you're measuring the wrong thing to see it coming.
- **Overclaiming "true emergence" from a single benchmark.** Any one benchmark showing a jump is weak evidence; check whether a continuous variant of the same task smooths it out before citing it as emergence.
- **Ignoring non-monotonicity.** A task that looks emergent in one scale range can be inverse-scaling in another (the U-shape) — fitting a single "emergence point" to it is fitting a mirage on top of a mirage.
- **Detection:** rerun the benchmark with a continuous scoring function (log-prob of the correct completion, token-level edit distance) across the same checkpoints. A discontinuity that survives the swap is the stronger claim.

## The non-obvious
The practically damaging version of this debate isn't philosophical — it's that AI safety arguments about "we'll see dangerous capabilities coming because they'll ramp up gradually" and "we won't see them coming because they emerge discontinuously" are *both* live positions supported by the same literature, and the answer plausibly depends on which metric a lab happens to use for its internal capability evals. Eval design (see [[Reference - Where Real AI Knowledge Lives]] for where evaluation methodology lives in this vault) is therefore not a downstream detail of the emergence debate — it *is* the debate, operationally. A team that picks exact-match dashboards by default is implicitly betting on the mirage-adjacent world without realizing it made that bet. [[Reference - Open Problems in LLM Engineering]] names exactly this as "the measurement problem" — arguably the most practically damaging open question in the field, because it is upstream of every other capability claim.

## Connections
- [[Concept - Scaling Laws]] — the smooth power-law backdrop that emergent-abilities curves are claimed to depart from.
- [[Concept - Data-Constrained Scaling Laws]] — shows the smooth-scaling backdrop holds even when data, not compute, is the binding constraint.
- [[Concept - Grokking]] — the clearest counter-example showing genuine discrete phase transitions do occur in trained networks.
- [[Concept - Inverse Scaling and U-Shaped Scaling]] — non-monotone scaling curves that complicate both the emergence and mirage positions.
- [[Concept - Statistical Rigor in Model Evaluation]] — the methodology for not being fooled by a single metric's shape.
- [[Concept - Induction Heads]] — a mechanistic circuit whose formation is the kind of internal change that could underlie a real capability jump.
- [[Reference - Where Real AI Knowledge Lives]] — points to where eval-design practice is treated in depth.
- [[Reference - Open Problems in LLM Engineering]] — catalogs the emergence-vs-mirage measurement problem as a standing unsolved question.

## Sources
- Wei et al. (2022) — "Emergent Abilities of Large Language Models". Documents sharp, unpredictable capability jumps across benchmarks and model scale.
- Schaeffer, Miranda & Koyejo (2023) — "Are Emergent Abilities of Large Language Models a Mirage?" (NeurIPS best paper). Shows exact-match/multiple-choice metrics manufacture apparent discontinuities from smooth underlying per-token improvement.
- Wei et al. (2023) — "Inverse Scaling Can Become U-Shaped". Evidence that scale-vs-capability curves are non-monotone, complicating both emergence positions.
