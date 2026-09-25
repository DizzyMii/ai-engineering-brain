---
tags: [concept, domain/esoterica, level/surface]
aliases: [emergent abilities, emergence mirage]
summary: "Whether LLM capability jumps at scale are real phase transitions or artifacts of discontinuous metrics — unresolved and safety-relevant."
---
> **One-paragraph hook:** In 2022 a widely cited paper claimed LLMs acquire capabilities (3-digit arithmetic, MMLU, word unscrambling) as sharp, unpredictable jumps at specific scale thresholds. A year later a NeurIPS best-paper rebuttal argued the jumps were mostly a mirage produced by the evaluation metric. The debate is still open, and the answer decides whether you can forecast a model's dangerous capabilities before you train it.

## The mechanism
[[Concept - Scaling Laws]] describe smooth power-law relationships between compute/data/parameters and loss, and that backdrop holds even in the data-constrained regime studied in [[Concept - Data-Constrained Scaling Laws]]. Wei et al. 2022 ("Emergent Abilities of Large Language Models") saw something else at the *task* level. On 3-digit addition, MMLU subject accuracy and word unscrambling, performance sits near random over a long stretch of scale, then rises well above chance within a narrow band, often reported somewhere between 10^22 and 10^24 training FLOPs depending on task and model family. And the jump is *unpredictable* from smaller models: draw a smooth curve through the sub-threshold points and it won't show the jump coming.

Schaeffer et al. 2023 ("Are Emergent Abilities of Large Language Models a Mirage?", NeurIPS best paper) gave a deflationary account. Many of Wei et al.'s benchmarks score with **exact match** or **multiple-choice accuracy**, metrics with a knife-edge threshold: get the whole k-token answer right or get zero credit. If the model's *per-token* probability of being right improves smoothly with scale (it does, and scaling laws already predict it), the probability of getting a whole k-token sequence exactly right goes roughly as

$$P(\text{exact match}) \approx p^k$$

where $p$ is the smooth per-token accuracy. That function is famously flat-then-steep. For $k=5$ and $p$ rising smoothly from 0.5 to 0.9, $p^k$ crawls from ~3% to ~59%, a sharp-looking cliff made entirely by exponentiating a smooth curve. Switch to a continuous metric (token-edit distance, per-token log-likelihood, Brier score) and the *same* models give smooth, predictable curves. Schaeffer et al. don't call the metric "wrong." Their claim is that the metric produces the apparent phase transition, and the model doesn't.

The counter-rebuttal: not everything flattens under smoother metrics. Some capabilities, certain BIG-Bench "breakthrough" tasks and novel in-context learning of tasks unseen in training, stay sharp under continuous scoring. And [[Concept - Grokking]] is a clean existence proof that a network's internal representation *can* go through a real discrete phase transition (a circuit forming, not a metric artifact). "Sharp changes never happen in neural nets" is too strong as a general claim.

## In practice
The fingerprint of the mirage: re-plot an "emergent" benchmark curve with a continuous score. If the elbow disappears, that's evidence for artifact; if it survives, evidence for something real in the model. Anthropic, OpenAI and DeepMind eval teams now routinely report both exact-match and continuous variants for this reason. [[Concept - Statistical Rigor in Model Evaluation]] covers the broader habit of not trusting one metric's shape.

BIG-Bench has its own "breakthroughness" and "linearity" scores, built to quantify how discontinuous a task's scaling curve is. The debate also ties into [[Concept - Inverse Scaling and U-Shaped Scaling]], tasks where accuracy *falls* with scale before recovering. Non-monotone scaling shows "capability vs. scale" isn't one clean curve you can extrapolate either way, which undercuts the strong-emergence and pure-mirage positions equally. The relationship is messier than either side's cleanest story.

## Failure modes
- **Forecasting from exact-match curves.** If you measure a capability only with strict exact match and it sits flat near zero up to your largest checkpoint, you can't conclude it won't appear at the next scale step. By the mirage argument, you're measuring the wrong thing to see it coming.
- **Claiming "true emergence" from one benchmark.** A single benchmark jump is weak evidence. Check whether a continuous variant of the same task smooths it out before citing it.
- **Ignoring non-monotonicity.** A task that looks emergent in one scale range can show inverse scaling in another (the U-shape). Fitting one "emergence point" to it is a mirage on top of a mirage.
- **Detection:** rerun the benchmark across the same checkpoints with a continuous score (log-prob of the correct completion, token-level edit distance). A discontinuity that survives the swap is the stronger claim.

## The non-obvious
The damaging part of this debate is practical. Safety arguments that "we'll see dangerous capabilities coming because they ramp up gradually" and "we won't, because they emerge discontinuously" are *both* live, supported by the same literature, and the answer plausibly depends on which metric a lab happens to use for internal capability evals. So eval design (see [[Reference - Where Real AI Knowledge Lives]] for where evaluation methodology lives in this vault) is the debate, operationally, and can't be treated as a downstream detail. A team that defaults to exact-match dashboards is betting on the mirage-adjacent world without knowing it made the bet. [[Reference - Open Problems in LLM Engineering]] calls this "the measurement problem," arguably the most practically damaging open question in the field because it sits upstream of every other capability claim.

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
