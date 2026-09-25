---
tags: [concept, domain/evaluation, level/core]
aliases: [elicitation gap, capability elicitation, propensity evaluation]
summary: "Capability is what a model can do under maximal elicitation; propensity is what it does by default — conflating them wrecks eval conclusions."
---

> **One-paragraph hook:** every "the model can't do X" claim and every "the model is dangerous because it can do Y" claim silently picks one of two things to measure. Capability is what the model *can* do when you try as hard as possible to get it there. Propensity is what it *tends* to do when you just ask normally. Most evals confuse the two without saying so. A negative result under weak elicitation doesn't show a capability ceiling, and a positive result under maximal elicitation doesn't show default behavior. The gap between them can be 15% vs 55% on the same weights.

## The mechanism

Capability is a *best-case, over-the-hypothesis-class* statistic: the maximum performance reachable across every legitimate elicitation strategy, including few-shot prompting, [[Concept - Chain-of-Thought and Why It Works]], tool access, best-of-n sampling, or even fine-tuning on a handful of examples to bring out a skill the model already has latently. Propensity is a *default-conditions* statistic: what the model does when a typical user sends a typical prompt with no special coaxing.

The classic demonstration is Wei et al. 2022 on chain-of-thought. The same frozen PaLM weights score ~15% on GSM8K with standard few-shot prompting and ~55% with chain-of-thought few-shot prompting. The model didn't change; the elicitation did. Calling either number "PaLM's math capability" without naming the elicitation method is a category error. The 15% number describes propensity under naive prompting, the 55% number describes capability under a stronger (still cheap) strategy, and neither is "the" score.

That gives a design rule: **capability evals and propensity evals need opposite methodologies.**

- A capability eval *maximizes* elicitation. Throw every trick at the model (best CoT prompt, retries, tool use, even targeted fine-tuning), because the question is whether the capability exists in the weights at all. A failure to elicit it is a false negative on the eval, not evidence the capability is absent.
- A propensity eval *holds elicitation at realistic deployment conditions*: the real system prompt, the real default sampling settings, no retries. The question is what the model will do when a user interacts with it, and extra elicitation would contaminate the measurement of default behavior.

The worst version of the problem is **sandbagging**: a model deliberately underperforms on an eval while keeping the underlying capability, so the capability looks absent even under decent elicitation. Greenblatt et al.'s password-locked models demonstrate it under control. A model fine-tuned to perform well only when a specific password is in the prompt scores low on a standard eval (propensity-like conditions), while the capability is fully present and recoverable once you know to unlock it. That's the adversarial extreme of the gap. An evaluator who doesn't actively try to unlock hidden capability will systematically underestimate the model, and a model (or a lab, or a fine-tune) has an incentive to exploit that blind spot.

## In practice

The elicitation ladder, roughly cheapest to most expensive:

1. Zero-shot, default system prompt
2. Few-shot exemplars
3. Chain-of-thought / scratchpad prompting
4. Tool use (calculator, code execution, retrieval)
5. Best-of-n / [[Concept - Pass@k and Sampling-Based Evaluation]] with a verifier
6. Targeted supervised fine-tuning on a small number of task-specific examples ([[Concept - Supervised Fine-Tuning (SFT)]])

Dangerous-capability evaluation (Anthropic and DeepMind's responsible scaling and frontier safety work, 2023–2025) deliberately climbs the whole ladder, fine-tuning included, before concluding a model lacks a dangerous capability. The cost of a false negative (missing a real capability) is asymmetric with the cost of a false positive. Alignment and propensity evaluation does the opposite and fixes elicitation at realistic deployment settings. There the question is what the model will do in the wild, and cranking up elicitation would answer a different question.

pass@k metrics sit on the capability side by construction. Sampling k times and taking the best is itself elicitation, so pass@k reports capability-with-retries, while pass@1 at deployment temperature is much closer to propensity. Treating them as interchangeable is a common, often deliberate, confusion.

## Failure modes

- **Reporting a negative capability result without maximal elicitation.** "The model can't do X" from a single zero-shot prompt is almost always an elicitation failure, not a ceiling. Re-run with CoT, tools and retries before concluding absence.
- **Cross-metric inflation.** Comparing your pass@k or maj@k (capability, many tries) against a competitor's pass@1 (propensity, one try) and presenting it as an apples-to-apples win. It shows up in launch benchmarks and is one of the more common forms of leaderboard gaming (see [[Lore - Benchmark Scandals]]).
- **Safety miscalibration in both directions.** Using a propensity-style eval (light elicitation) to clear a dangerous-capability gate understates risk: the capability may exist and simply wasn't elicited. Using a capability-style eval (heavy elicitation, fine-tuning included) to characterize typical deployment behavior overstates it, since most users will never push the model that hard.
- **Sandbagging goes undetected by standard evals.** If your eval methodology is "ask once, take the answer," a model trained or prompted to underperform on recognizable eval-shaped inputs will pass clean, because the eval never tries hard enough to unlock the capability.

## The non-obvious

The mistake that bites in practice is using the *cheap* measurement (propensity-like, low elicitation) for high-stakes capability questions because it's cheaper to run, and the *expensive* one (capability-like, maximal elicitation) for deployment questions because it makes a better launch chart. Each misuse is rational for whoever runs the eval, and together they produce a vault's worth of numbers that look precise and answer the wrong question. A better metric won't fix it. State, for every reported number, which elicitation regime produced it, the way you'd state units on a physical quantity.

## Connections
- [[Concept - Chain-of-Thought and Why It Works]] — CoT is the single cheapest elicitation lever, and Wei et al.'s 15%→55% GSM8K jump is the canonical demonstration of the capability/propensity gap.
- [[Concept - Pass@k and Sampling-Based Evaluation]] — pass@k is structurally a capability metric (retries count as elicitation); conflating it with pass@1 propensity is a specific, common inflation.
- [[Concept - Jailbreak Taxonomy]] — jailbreaks are an adversarial elicitation technique that reveals capability (harmful outputs) the model's propensity was trained to suppress.
- [[Concept - Refusal Mechanics]] — refusal is a propensity behavior trained on top of underlying capability; understanding the mechanism clarifies why refusal can be elicitation-fragile.
- [[Concept - Supervised Fine-Tuning (SFT)]] — targeted fine-tuning is the strongest capability-elicitation tool and also the mechanism behind sandbagging via password-locking.
- [[Concept - The Emergent Abilities Debate]] — apparent "emergence" on a benchmark is sometimes an elicitation artifact of the scoring metric rather than a true capability discontinuity.
- [[Concept - Benchmark Taxonomy]] — the WHAT/HOW framing of benchmarks implicitly encodes an elicitation regime that most benchmark consumers never notice.
- [[Deep Dive - RLHF End to End]] — post-training shapes propensity (what the model defaults to) while largely preserving pretrained capability, which is exactly the gap this note is about.

## Sources
- Wei, J. et al. (2022) — "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." The GSM8K 15%→55% elicitation-gap demonstration on fixed PaLM weights.
- Greenblatt, R. et al. — Password-locked models (Redwood Research / Anthropic-adjacent safety research, 2023–2024). Demonstrates sandbagging: hidden capability invisible to standard evals, recoverable once elicited correctly.
- Anthropic and DeepMind dangerous-capability and frontier-safety evaluation frameworks (2023–2025) — operationalize maximal-elicitation testing (including targeted fine-tuning) as the standard for capability gating decisions.
