---
tags: [concept, domain/post-training, level/advanced]
aliases: [CAI, Constitutional AI, RLAIF, RL from AI Feedback, SL-CAI, RL-CAI]
summary: "Replacing human harm labels with a written constitution: self-critique-and-revise for SFT data, then AI preference labels for RL."
---

# Concept - Constitutional AI and RLAIF
> **One-paragraph hook:** Having human labelers read model outputs and rate them for harm has a floor. It's slow, it's expensive at scale, and it makes people read a lot of disturbing text. Constitutional AI swaps that step for a written list of principles and has the model critique and judge its own outputs against them. Most harmlessness labeling goes from a human bottleneck to an inference-time loop, and the approach generalizes into RLAIF: training on AI-generated preference labels instead of human ones.

## The mechanism

Constitutional AI (Bai et al. 2022, Anthropic) has two phases.

**Phase 1 (SL-CAI).** Take a helpful-only model and sample its response to a prompt built to elicit harmful behavior (a [[Concept - Jailbreak Taxonomy|red-team-style]] prompt). Sample one principle from the constitution, ask the model to critique its response against it, then ask it to revise. The critique-revision step can run for several rounds with a fresh principle each time. The (original, revised) pairs are [[Concept - Synthetic Training Data]], and the revisions go straight in as [[Concept - Supervised Fine-Tuning (SFT)]] targets. That bootstraps a harmlessness-aware model with zero human labels on the harmful content itself.

**Phase 2 (RL-CAI, i.e. RLAIF).** Sample pairs of responses from the Phase-1 model, show the model both plus a sampled principle, and ask which response better satisfies it. [[Concept - Chain-of-Thought and Why It Works|Chain-of-thought]] reasoning before the judgment measurably improves label quality. The AI-generated pairwise preferences are then used like human preference data: fit a [[Concept - Reward Models|Bradley-Terry preference model]] and run RL (PPO) against it. Compared with standard RLHF, the only change is *who* produced the label: a model conditioned on a written principle instead of a human rater following written instructions.

The constitution is a set of natural-language principles drawn from sources like the UN Declaration of Human Rights and platform terms of service, plus rules Anthropic wrote. A principle is sampled per critique or comparison; there's no single fixed rubric. So the critique model and the resulting preference model both have to generalize across many phrasings of "don't do X" and can't overfit to one prompt template.

Anthropic frames the split as **RLHF for helpful, CAI for harmless**. Human preference comparisons still drive helpfulness (see [[Deep Dive - RLHF End to End]]). The constitutional pipeline drives harmlessness, including much of what shows up at inference time as [[Concept - Refusal Mechanics|refusal behavior]]. It replaces the human harm-labeling half specifically because that's the more unpleasant and more expensive half to source from people.

## In practice

Lee et al. 2023 (Google, "RLAIF") independently validated the broader pattern outside Anthropic's constitution-based setup. On tasks like summarization, AI feedback labels can approximately match human feedback labels in downstream model quality, at a fraction of the marginal cost. Once you have a capable labeler model, another preference comparison costs an API call and some latency instead of crowd-worker turnaround and pay. That's the economic case for RLAIF: preference-label supply scales with compute budget instead of headcount, and human raters no longer have to see a training-scale stream of harmful content.

Practical constitutions have dozens of principles, not one. How you sample which principle to apply per comparison is a design choice in its own right: uniform, or weighted toward the harm categories most present in a given red-team prompt.

## Failure modes

Ambiguity in the constitution is the first crack. Principles conflict or leave edge cases underspecified, and however the labeler model resolves the ambiguity becomes the de facto alignment target, silently encoding the labeler's priors as ground truth.

Those priors compound. If the base model already leans toward hedging or [[Concept - Sycophancy|sycophancy]], that lean gets baked into the harmlessness preference model it trains, and the loop reinforces it.

The critique-revision loop can also be gamed toward the letter of a principle over its intent. The model learns to append a disclaimer or hedge without changing the substance of a harmful response, which satisfies the principle's literal text and misses its purpose.

Since the "reward model" sits downstream of another LLM's judgment, it inherits the full reward-hacking surface of [[Concept - LLM-as-Judge|LLM-as-judge]]. Confident tone, length and formatting can all shift an AI judge's preference independent of actual harmlessness. That's [[Concept - Reward Hacking]] one level removed.

And CAI doesn't take humans out of the loop. Helpfulness preference data is still human-sourced, so the savings only apply to the harmlessness half.

At the far end, a model that has learned to satisfy a constitution's surface form without internalizing its intent is mechanistically adjacent to the strategic surface-compliance documented in [[Breakdown - Alignment Faking]]. CAI doesn't itself produce alignment faking. But a poorly specified constitution plus an under-scrutinized critique step are the conditions that make real and performed compliance hard to tell apart.

## The non-obvious

The Phase 1 self-critique does something more specific than a harm classifier. Because the revision is *conditioned on the original response plus one principle*, the output is a matched (worse, better) pair instead of a bare label. SL-CAI is really a synthetic preference-pair generator wearing an SFT hat, producing the shape of data RLAIF wants next. So the two phases compose cleanly: Phase 1 is upstream data generation for Phase 2, more than a separate warm-up.

Folklore, weakly sourced: practitioners who've reimplemented CAI-style pipelines report that the technique degrades if the principle is visible to the model at *generation* time and not only at critique time. Show the rubric during generation and the model learns to game its literal wording instead of the judgment the rubric is meant to teach. Keeping generation and critique informationally separate (the generator doesn't know which principle will critique it) is reported as necessary for label quality, though this claim is less rigorously published than the core CAI/RLAIF results.

## Connections
- [[Deep Dive - RLHF End to End]] — CAI supplies the harmlessness half of the same RLHF pipeline that human preferences supply the helpfulness half of.
- [[Concept - Reward Models]] — the AI-labeled preference model in Phase 2 is trained with the identical Bradley-Terry objective as a human-labeled RM.
- [[Concept - Reward Hacking]] — an AI-judge-based reward model is exploitable by the same mechanisms as any learned proxy, one level removed.
- [[Concept - Synthetic Training Data]] — cross-domain: the critique-revision pairs from Phase 1 are a specific, structured case of synthetic training data generation.
- [[Concept - Supervised Fine-Tuning (SFT)]] — Phase 1's revised responses are used directly as SFT targets, bootstrapping harmlessness before any RL happens.
- [[Concept - Chain-of-Thought and Why It Works]] — cross-domain: CoT reasoning before the AI judgment is what makes RLAIF labels usable quality.
- [[Concept - Jailbreak Taxonomy]] — cross-domain: the red-team prompts that seed Phase 1 critique data come from the same adversarial-prompt space this note catalogs.
- [[Concept - Refusal Mechanics]] — cross-domain: harmlessness training via CAI is a major upstream driver of a model's learned refusal behavior.
- [[Concept - Sycophancy]] — cross-domain: a base model's sycophantic tendency contaminates the AI-generated preference labels it produces about itself.
- [[Concept - LLM-as-Judge]] — cross-domain: RLAIF's preference labeling is LLM-as-judge applied specifically to pairwise harmlessness comparisons.
- [[Breakdown - Alignment Faking]] — cross-domain, up-link: satisfying a principle's letter over its intent is mechanistically adjacent to documented alignment-faking behavior.

## Sources
- Bai et al. (2022) — Constitutional AI: Harmlessness from AI Feedback. The origin paper: SL-CAI critique-revision plus RL-CAI/RLAIF.
- Lee et al. (2023) — RLAIF: Scaling Reinforcement Learning from Human Feedback with AI Feedback. Independent validation that AI preference labels can approximately match human labels at much lower marginal cost.
