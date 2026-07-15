---
tags: [concept, domain/evaluation, level/advanced]
aliases: [pass@k, pass@1, unbiased pass@k estimator]
summary: "The unbiased estimator for at least one of k samples passing a verifier, and why quoting it against a rival pass@1 inflates launch charts."
---

> **One-paragraph hook:** Some tasks have a machine-checkable verifier — code either passes the test suite or it doesn't, a math answer either matches or it doesn't — and for those tasks the natural way to evaluate a model isn't a single deterministic attempt, it's "if the model got k tries, would at least one of them work?" That question has a name, pass@k, and a subtle statistical trap: computing it naively from exactly k samples per problem is high-variance and biased, and reporting it against a competitor's single-shot pass@1 number in a launch chart is one of the field's most common apples-to-oranges inflations.

## The mechanism

The quantity of interest is $\text{pass@}k$: the probability that **at least one** of $k$ sampled outputs for a problem passes its verifier. The naive estimator — draw exactly $k$ samples, check whether any pass, average over problems — is unbiased in expectation but has punishing variance at the problem level, because it discards all but $k$ data points per problem even when you could afford to sample more.

Chen et al. (2021), introducing Codex and HumanEval, fixed this with an unbiased, low-variance estimator that uses *more* samples than $k$ without changing what's being estimated: draw $n \geq k$ samples per problem, count $c$ of them correct, then

$$\text{pass@}k = \mathbb{E}_{\text{problems}}\left[1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}\right]$$

The intuition: $\binom{n-c}{k} / \binom{n}{k}$ is the probability that a random $k$-sized subset drawn from all $n$ samples contains **zero** correct ones (every one of the $k$ chosen samples comes from the $n-c$ incorrect pool), so one minus that is the probability the subset contains at least one correct sample — exactly the pass@k event, computed by reusing all $n$ samples' worth of information rather than throwing away everything beyond the first $k$. Because it marginalizes over all $\binom{n}{k}$ possible $k$-subsets in closed form instead of drawing one subset at random, this estimator has dramatically lower variance than the naive version for the same sampling budget, and it is the version essentially every serious pass@k report should be using.

## In practice

The original Codex paper sampled $n = 200$ completions per problem and reported pass@1, pass@10, and pass@100 from that single pool via the estimator above — and tuned decoding temperature per $k$, using a low temperature (favoring the single best-guess completion) for pass@1 and a higher temperature (favoring diversity across the sample pool) for pass@100, because the two metrics reward opposite properties of the sampling distribution from the same model.

A family of related metrics share the same sample-and-verify shape but aggregate differently: **maj@k / self-consistency** (Wang et al. 2022) samples $k$ chain-of-thought traces and takes a majority vote over their final answers rather than crediting a lone success — closer to "what would the model output under repeated self-checking" than "is any single attempt right." **Best-of-$n$** uses a trained reward model instead of a verifier to pick the best of $n$ samples, useful when no hard pass/fail check exists. **cons@k** and **g-pass@k** extend the family with partial-credit and stability variants for tasks where a single verifier call is noisy. [[Breakdown - SWE-bench]] is a concrete execution-verified benchmark commonly reported this way — pass@k over sampled patch attempts, graded by running the hidden test suite rather than a judge.

## Failure modes

**Capability-versus-deployment conflation.** Pass@k measures capability under retries; pass@1 measures single-shot behavior close to how most products actually deploy a model. These correspond to the general distinction in [[Concept - Capability versus Propensity]] — pass@k leans toward capability elicitation, pass@1 toward default propensity — and reporting a strong cons@64 or pass@100 figure in a launch chart positioned next to a competitor's pass@1 number is a recurring, structurally misleading comparison seen in several reasoning-model launches.

**Verifier quality caps everything.** A weak test suite gives false positives — code that passes the provided tests but is subtly wrong on cases the suite never checks — inflating pass@k above true correctness. Math answer-matching gives false negatives on semantically equivalent but syntactically different forms (`1/2` versus `0.5`, an unsimplified versus simplified expression), deflating pass@k below true correctness. Detection: audit a sample of items marked "failed" for whether the underlying answer was actually right but the matcher was too strict, and a sample marked "passed" for whether the test suite actually exercised the interesting cases.

**Missing reporting discipline.** A pass@k number without $n$, $k$, temperature, and the exact verifier stated is not a comparable measurement — two "pass@1" figures computed from different $n$, different temperature, or a looser verifier are not the same quantity even when the label matches.

## The non-obvious

The naive practitioner mistake isn't just conflating pass@k with pass@1 in a chart — it's implementing pass@k *itself* wrong, by literally drawing exactly $k$ samples per problem and averaging pass/fail, instead of using the $n \geq k$ unbiased estimator above. That naive version is a legitimate estimator of the same quantity, but its variance at realistic problem-set sizes is large enough to make small pass@k deltas between models statistically meaningless — the same [[Concept - Statistical Rigor in Model Evaluation|statistical-rigor discipline]] that applies to any other benchmark score applies here, just with an unusually clean, closed-form variance-reduction fix available if you bother to use it.

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
