---
tags: [concept, domain/evaluation, level/advanced]
aliases: [pass@k, pass@1, unbiased pass@k estimator]
summary: "The unbiased estimator for at least one of k samples passing a verifier, and why quoting it against a rival pass@1 inflates launch charts."
---

> **One-paragraph hook:** Some tasks have a machine-checkable verifier. Code passes the test suite or it doesn't; a math answer matches or it doesn't. For those tasks the natural question isn't how one deterministic attempt does, but whether at least one of k tries would work. That question is pass@k, and it comes with a statistical trap: computing it naively from exactly k samples per problem is high-variance and biased, and setting it against a competitor's single-shot pass@1 in a launch chart is one of the field's most common apples-to-oranges inflations.

## The mechanism

$\text{pass@}k$ is the probability that **at least one** of $k$ sampled outputs for a problem passes its verifier. The naive estimator draws exactly $k$ samples, checks whether any pass, and averages over problems. It's unbiased in expectation but has punishing per-problem variance, because it throws away everything past $k$ even when you could afford to sample more.

Chen et al. (2021), the paper that introduced Codex and HumanEval, fixed this with an unbiased, low-variance estimator that uses more samples than $k$ without changing the target. Draw $n \geq k$ samples per problem, count $c$ correct, then

$$\text{pass@}k = \mathbb{E}_{\text{problems}}\left[1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}\right]$$

$\binom{n-c}{k} / \binom{n}{k}$ is the probability that a random $k$-subset of the $n$ samples has **zero** correct ones, i.e. all $k$ came from the $n-c$ incorrect pool. One minus that is the probability the subset has at least one correct sample, which is the pass@k event, computed from all $n$ samples. It marginalizes over all $\binom{n}{k}$ subsets in closed form instead of drawing one at random, so for the same sampling budget its variance is dramatically lower than the naive version's. Essentially every serious pass@k report should use it.

## In practice

The original Codex paper sampled $n = 200$ completions per problem and reported pass@1, pass@10 and pass@100 from that one pool via the estimator above. It also tuned temperature per $k$: low for pass@1, favoring the single best-guess completion, and higher for pass@100, favoring diversity across the pool. The two metrics reward opposite properties of the same model's sampling distribution.

Related metrics share the sample-and-verify shape but aggregate differently. **maj@k / self-consistency** (Wang et al. 2022) samples $k$ chain-of-thought traces and majority-votes their final answers instead of crediting a lone success, so it's closer to "what would the model say under repeated self-checking" than "is any single attempt right." **Best-of-$n$** picks the best of $n$ samples with a trained reward model instead of a verifier, which helps when no hard pass/fail check exists. **cons@k** and **g-pass@k** add partial-credit and stability variants for tasks where one verifier call is noisy. [[Breakdown - SWE-bench]] is an execution-verified benchmark commonly reported this way: pass@k over sampled patch attempts, graded by running the hidden test suite instead of a judge.

## Failure modes

**Capability versus deployment.** Pass@k measures capability under retries. Pass@1 measures single-shot behavior, which is close to how most products deploy a model. This maps onto [[Concept - Capability versus Propensity]]: pass@k leans toward capability elicitation, pass@1 toward default propensity. Putting a strong cons@64 or pass@100 figure next to a competitor's pass@1 in a launch chart is a recurring, misleading comparison, and several reasoning-model launches have done it.

**Verifier quality caps everything.** A weak test suite gives false positives: code passes the provided tests but is subtly wrong on cases the suite never checks, which inflates pass@k above true correctness. Math answer-matching gives false negatives on equivalent answers written differently (`1/2` versus `0.5`, an unsimplified versus simplified expression), which deflates it. To catch this, audit a sample of "failed" items for answers that were right but rejected by a strict matcher, and a sample of "passed" items for whether the suite exercised the interesting cases.

**Missing reporting discipline.** A pass@k number without $n$, $k$, temperature and the exact verifier isn't a comparable measurement. Two "pass@1" figures from different $n$, different temperatures or a looser verifier are different quantities under the same label.

## The non-obvious

The naive practitioner mistake goes past charting pass@k against pass@1. It's implementing pass@k *itself* wrong: drawing exactly $k$ samples per problem and averaging pass/fail instead of using the $n \geq k$ estimator above. The naive version is a legitimate estimator of the same quantity, but at realistic problem-set sizes its variance makes small pass@k deltas between models statistically meaningless. The usual [[Concept - Statistical Rigor in Model Evaluation|statistical-rigor discipline]] for benchmark scores applies here too, and this case happens to have a clean closed-form variance fix if you bother to use it.

## Connections
- [[Concept - Capability versus Propensity]] — pass@k-versus-pass@1 is the concrete, named instance of the general capability-elicitation-versus-default-behavior distinction.
- [[Concept - GRPO and RL with Verifiable Rewards]] — cross-domain (Post-Training): RL training itself samples groups of completions and scores them against the same verifiable-reward machinery pass@k measures at eval time.
- [[Concept - Sampling and Decoding Parameters]] — cross-domain (Inference & Serving): temperature is the lever that trades pass@1 quality against pass@k sample diversity from the same model.
- [[Concept - Chain-of-Thought and Why It Works]] — cross-domain (Prompting & Context): longer reasoning traces change both the correctness distribution being sampled from and maj@k's aggregation behavior.
- [[Breakdown - SWE-bench]] — a concrete execution-verified benchmark commonly reported with pass@k over sampled patch attempts.
- [[Concept - Statistical Rigor in Model Evaluation]] — the general variance and sample-size discipline that the unbiased pass@k estimator is a specialized, closed-form instance of.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — cross-domain (Post-Training): reasoning-model training and evaluation both lean on maj@k/pass@k as the load-bearing metric family.
- [[Decision - Choosing an Evaluation Method]] — names pass@k execution as the default choice for tasks that are generative but have a verifiable ground truth.

## Sources
- Chen, M. et al. (2021) — "Evaluating Large Language Models Trained on Code" (Codex/HumanEval). Introduces the unbiased, low-variance pass@k estimator.
- Wang, X. et al. (2022) — "Self-Consistency Improves Chain of Thought Reasoning in Language Models." The maj@k / self-consistency majority-vote aggregation.
