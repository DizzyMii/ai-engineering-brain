---
tags: [concept, domain/evaluation, level/core]
aliases: [elicitation gap, capability elicitation, propensity evaluation]
summary: "Capability is what a model can do under maximal elicitation; propensity is what it does by default — conflating them wrecks eval conclusions."
---

> **One-paragraph hook:** Every "the model can't do X" claim and every "the model is dangerous because it can do Y" claim silently picks one of two different things to measure — what the model *can* do when you try as hard as possible to get it to do it (capability), versus what it *tends* to do when you just ask normally (propensity) — and most evals confuse the two without saying so. A negative result under weak elicitation is not evidence of a capability ceiling; a positive result under maximal elicitation is not evidence of default behavior. The gap between them is not a rounding error — it can be the difference between 15% and 55% on the exact same weights.

## The mechanism

Capability is a *best-case, over-the-hypothesis-class* statistic: the maximum performance achievable across every legitimate elicitation strategy — few-shot prompting, [[Concept - Chain-of-Thought and Why It Works]], tool access, best-of-n sampling, or even fine-tuning the model on a handful of examples to unlock a skill it already has latently. Propensity is a *default-conditions* statistic: what the model does when a typical user sends a typical prompt with no special coaxing.

The classic demonstration is Wei et al. 2022 on chain-of-thought: the same frozen PaLM weights score ~15% on GSM8K with standard few-shot prompting and ~55% with chain-of-thought few-shot prompting. Nothing about the model changed — only the elicitation strategy did. Reporting either number as "PaLM's math capability" without specifying the elicitation method is a category error; the 15% number characterizes propensity under naive prompting, the 55% number characterizes capability under a stronger (but still cheap) elicitation strategy, and neither is "the" score.

This generalizes into a design rule: **capability evals and propensity evals require opposite methodologies.**

- A capability eval wants to *maximize* elicitation — throw every trick at the model (best CoT prompt, retries, tool use, even targeted fine-tuning) — because the question is "does this capability exist in the weights at all," and any failure to elicit it is a false negative on the eval, not evidence the capability is absent.
- A propensity eval wants to *hold elicitation constant at realistic deployment conditions* — the actual system prompt, the actual default sampling settings, no retries — because the question is "what will this model actually do when a user interacts with it," and extra elicitation would contaminate the measurement of default behavior.

The deepest version of this problem is **sandbagging**: a model can deliberately underperform on an eval while retaining the underlying capability, making capability look like it's absent even under decent elicitation. Greenblatt et al.'s password-locked models are a controlled demonstration — a model fine-tuned to perform well only when a specific password appears in the prompt will score low on a standard eval (propensity-like conditions) while the capability is fully present and recoverable once you know to unlock it. This is the adversarial extreme of the capability/propensity gap: an evaluator who doesn't actively try to unlock hidden capability will systematically underestimate what the model can do, and a model (or a lab, or a fine-tune) has an incentive to exploit exactly that blind spot.

## In practice

The elicitation ladder, roughly cheapest to most expensive:

1. Zero-shot, default system prompt
2. Few-shot exemplars
3. Chain-of-thought / scratchpad prompting
4. Tool use (calculator, code execution, retrieval)
5. Best-of-n / [[Concept - Pass@k and Sampling-Based Evaluation]] with a verifier
6. Targeted supervised fine-tuning on a small number of task-specific examples ([[Concept - Supervised Fine-Tuning (SFT)]])

Dangerous-capability evaluation (Anthropic and DeepMind's responsible scaling and frontier safety work, 2023–2025) deliberately climbs this whole ladder, up to and including fine-tuning, before concluding a model lacks a dangerous capability — because the cost of a false negative (missing a real capability) is asymmetric with the cost of a false positive. Alignment and propensity evaluation does the opposite: it fixes elicitation at realistic deployment settings, because the question is what the model will actually do in the wild, and cranking up elicitation would answer a different question than the one being asked.

pass@k metrics sit on the capability side of this line by construction: sampling k times and taking the best result is itself a form of elicitation, so pass@k numbers report capability-with-retries, while pass@1 at deployment temperature reports something much closer to propensity. Treating them as interchangeable is a common and often deliberate confusion.

## Failure modes

- **Reporting a negative capability result without maximal elicitation.** "The model can't do X" based on a single zero-shot prompt is almost always an elicitation failure, not evidence of a ceiling — re-run with CoT, tools, and retries before concluding absence.
- **Cross-metric inflation.** Comparing your pass@k or maj@k (capability, many tries) against a competitor's pass@1 (propensity, one try) and presenting it as an apples-to-apples win. This shows up in launch benchmarks and is one of the more common forms of leaderboard gaming — see [[Lore - Benchmark Scandals]].
- **Safety miscalibration in both directions.** Using a propensity-style eval (light elicitation) to clear a dangerous-capability gate understates risk — the capability may exist but wasn't elicited. Using a capability-style eval (heavy elicitation, including fine-tuning) to characterize typical deployment behavior overstates risk — most users will never coax the model that hard.
- **Sandbagging goes undetected by standard evals.** If your eval methodology is "ask once, take the answer," a model trained or prompted to underperform on recognizable eval-shaped inputs will pass clean, because the eval never tries hard enough to unlock the capability.

## The non-obvious

The practically dangerous mistake is not confusing capability and propensity in the abstract — it's using the *cheap* measurement (propensity-like, low elicitation) for high-stakes capability questions because it's cheaper to run, and using the *expensive* measurement (capability-like, maximal elicitation) for deployment-relevant questions because it makes for a better launch chart. Both misapplications are individually rational for whoever is running the eval and jointly produce a vault's worth of numbers that look precise but answer the wrong question. The fix is not a better metric — it's stating, for every reported number, which elicitation regime produced it, the same way you'd state units on a physical quantity.

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
