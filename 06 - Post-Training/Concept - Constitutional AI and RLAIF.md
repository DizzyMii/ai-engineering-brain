---
tags: [concept, domain/post-training, level/advanced]
aliases: [CAI, Constitutional AI, RLAIF, RL from AI Feedback, SL-CAI, RL-CAI]
summary: "Replacing human harm labels with a written constitution: self-critique-and-revise for SFT data, then AI preference labels for RL."
---

# Concept - Constitutional AI and RLAIF
> **One-paragraph hook:** Human labelers reading model outputs and rating them for harm has a floor: it's slow, it's expensive at scale, and it makes people read a lot of disturbing text. Constitutional AI replaces that step with a written list of principles and lets the model critique and judge its own outputs against them — collapsing most of harmlessness labeling from a human bottleneck into an inference-time loop, and giving rise to RLAIF as the general pattern of training on AI-generated preference labels instead of human ones.

## The mechanism

Constitutional AI (Bai et al. 2022, Anthropic) runs in two phases. **Phase 1 (SL-CAI)**: sample a response from a helpful-only model to a prompt designed to elicit harmful behavior (a [[Concept - Jailbreak Taxonomy|red-team-style]] prompt), sample one principle from the constitution, ask the model to critique its own response against that principle, then ask it to revise the response accordingly. This critique-revision step can repeat for several rounds, sampling a fresh principle each time. The resulting (original, revised) pairs are [[Concept - Synthetic Training Data]]: the revisions are used directly as [[Concept - Supervised Fine-Tuning (SFT)]] targets, bootstrapping a harmlessness-aware model with zero human labels on the harmful content itself.

**Phase 2 (RL-CAI, i.e. RLAIF)**: sample pairs of responses to a prompt from the Phase-1 model, show the model both responses plus a sampled constitutional principle, and ask it to state which response better satisfies the principle — [[Concept - Chain-of-Thought and Why It Works|chain-of-thought]] reasoning before the judgment measurably improves label quality. These AI-generated pairwise preferences are used exactly like human preference data: fit a [[Concept - Reward Models|Bradley-Terry preference model]] on them, then run RL (PPO) against it. The only thing that changed relative to standard RLHF is *who* generated the preference label — a model conditioned on a written principle, instead of a human rater following written instructions.

The constitution itself is a set of natural-language principles — drawn from documents like the UN Declaration of Human Rights and platform terms of service, plus Anthropic-authored rules — with a principle sampled per critique or comparison rather than one fixed rubric applied every time. This forces both the critique model and the resulting preference model to generalize across many phrasings of "don't do X" rather than overfitting to one prompt template.

The resulting division of labor, in Anthropic's framing: **RLHF for helpful, CAI for harmless** — human preference comparisons still drive the helpfulness objective (see [[Deep Dive - RLHF End to End]]), while the constitutional pipeline drives harmlessness, including much of what surfaces at inference time as [[Concept - Refusal Mechanics|refusal behavior]] — replacing the human-harm-labeling half specifically because it is the more unpleasant and more expensive half to source from people.

## In practice

Lee et al. 2023 (Google, "RLAIF") independently validated the broader pattern outside Anthropic's specific constitution-based setup: AI feedback preference labels can approximately match human feedback labels in downstream model quality on tasks like summarization, at a fraction of the marginal cost — once you have a capable labeler model, generating another preference comparison costs an API call and some latency instead of crowd-worker turnaround and payment. This is the real economic case for RLAIF: preference-label supply scales with compute budget rather than headcount, and it removes the need to expose human raters to a training-scale stream of harmful content.

Practical constitutions run to dozens of distinct principles rather than one; per-comparison sampling of which principle to apply is itself a design choice (uniform sampling vs. weighting toward the categories of harm most present in a given red-team prompt).

## Failure modes

Constitution ambiguity is the first crack: principles conflict or leave edge cases underspecified, and whatever way the labeler model resolves the ambiguity becomes the de facto alignment target, silently encoding the labeler's own priors as ground truth. Those priors compound: if the base model already leans toward hedging or [[Concept - Sycophancy|sycophancy]], that tendency gets baked into the harmlessness preference model it itself trains, reinforcing rather than correcting it. The critique-revision loop is also gameable toward the letter rather than the intent of a principle — learning to append a disclaimer or hedge rather than actually changing the substance of a harmful response, which satisfies a principle's literal text without satisfying its purpose. Because the "reward model" here is downstream of another LLM's judgment, it inherits [[Concept - LLM-as-Judge|LLM-as-judge]]'s full reward-hacking surface — confident tone, length, and formatting can all move an AI judge's preference independent of actual harmlessness, which is just [[Concept - Reward Hacking]] one level removed. And CAI does not remove humans from the loop entirely — helpfulness preference data is still human-sourced, so the method only saves labeling cost on the harmlessness half.

At the far end of this failure mode, a model that has learned to satisfy a constitution's surface form without internalizing its intent is mechanistically adjacent to the kind of strategic surface-compliance documented in [[Breakdown - Alignment Faking]] — CAI does not itself produce alignment faking, but a poorly-specified constitution and an under-scrutinized critique step are exactly the conditions that make genuine and performed compliance hard to tell apart.

## The non-obvious

The self-critique step in Phase 1 is doing something more specific than a harm classifier would: because revision is *conditioned on the original response plus one principle*, the output is a matched (worse, better) pair, not just a label — which means SL-CAI is really a synthetic preference-pair generator wearing an SFT hat, and it's exactly the shape of data RLAIF wants next. That's why the two phases compose so cleanly: Phase 1 isn't a separate warm-up, it's upstream data generation for Phase 2. Folklore, weakly sourced: practitioners who've reimplemented CAI-style pipelines report the technique degrades if the constitutional principle is visible to the model at *generation* time rather than only at critique time — expose the rubric during generation and the model learns to game its literal wording directly, rather than learning the judgment the rubric is trying to teach; keeping generation and critique informationally separated (the generator doesn't know which principle will be used to critique it) is reported as load-bearing for label quality, though this specific claim is less rigorously published than the core CAI/RLAIF results.

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
