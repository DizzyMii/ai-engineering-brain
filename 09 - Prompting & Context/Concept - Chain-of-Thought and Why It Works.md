---
tags: [concept, domain/prompting-context, level/core]
aliases: [CoT, chain of thought, let's think step by step]
summary: "CoT trades serial forward passes for computation depth, letting a fixed-depth transformer solve problems it can't in one shot."
---
> **One-paragraph hook:** A transformer's layer stack has fixed depth, so every generated token gets the same bounded amount of computation however hard the problem is. Chain-of-thought turns one hard token prediction into many easy ones. The model writes intermediate reasoning tokens and feeds each back in as context, so every step gets a fresh forward pass and a fresh chance to condition on the progress so far. It's test-time compute smuggled in through the autoregressive loop. There's no magic in the incantation.

## The mechanism

Every generated token, answer or reasoning step, costs one forward pass through a fixed number of layers: a constant amount of serial computation. If a task needs more sequential computation than that depth allows (multi-step arithmetic, multi-hop logic), a model forced to answer directly can't "think longer". It has to squeeze the whole solution path into one shot. Chain-of-thought gets around this by emitting intermediate tokens. Each reasoning token becomes context for the *next* one, so a problem needing $k$ sequential steps gets $k$ forward passes instead of one.

It's a scratchpad in the literal sense; Nye et al. (2021) framed it that way ("Show Your Work"). Feng et al. (2023) formalized *why* it has to help. A constant-depth transformer is provably limited in which functions it can compute in one pass, but with CoT it can simulate arbitrarily long serial computations. That expands the set of problems it can solve at all, beyond raising accuracy on ones already in reach. The attention circuitry that lets a model complete an in-context pattern, the [[Concept - Induction Heads]] behind prefix-match-and-copy, is part of what lets it pick up and extend the reasoning pattern its own earlier steps laid down.

Two empirical results made it something practitioners could use:
- **Few-shot CoT**, Wei et al. (2022). Putting worked reasoning into the few-shot exemplars (see [[Concept - In-Context Learning]]) gives large gains on GSM8K, arithmetic and commonsense reasoning benchmarks. The effect **emerges**: it only appears once models pass roughly 60-100B parameters. Below that, CoT prompting can *hurt* accuracy compared with answering directly, because small models write plausible but wrong reasoning that then anchors a wrong answer. It's one of the cleaner data points in the [[Concept - The Emergent Abilities Debate]].
- **Zero-shot CoT**, Kojima et al. (2022). Appending "Let's think step by step" with *no* exemplars raised GPT-3's zero-shot GSM8K accuracy from roughly 18% to roughly 41%. The prompt gained no new information. The phrase just nudged the model into scratchpad behavior it already had latent from pretraining ([[Lore - Let's Think Step by Step]] has the longer history of trigger-phrase folklore).

**Self-consistency** (Wang et al. 2022) goes further. Sample $k$ independent chains at nonzero temperature (see [[Concept - Sampling and Decoding Parameters]]) and take a majority vote over the $k$ final answers. You pay $k\times$ the inference compute for roughly +10 to +18 points on GSM8K-class benchmarks. The theory is that correct reasoning paths agree with each other more often than wrong ones happen to coincide.

## In practice

CoT costs something and doesn't always fit. [[Decision - When to Use Chain-of-Thought]] has the full decision flow. Short version: on a non-reasoning instruction-tuned model doing multi-step math or logic, use CoT (few-shot if you have exemplars, the zero-shot trigger phrase if not). With compute to spare and a need for maximum accuracy, add self-consistency on top. If the output has to be machine-parseable, put the reasoning and the final answer in visibly separate regions (a delimiter or a dedicated field) so the parser doesn't have to dig the answer out of free-form prose. [[Playbook - Reliable Structured Output]] covers this.

## Failure modes

- **CoT hurts below the emergence threshold.** Small or weak models (roughly sub-10B, task-dependent) often do worse with CoT than with a direct answer. Their reasoning is noisy, and the scratchpad reinforces the wrong conclusion. Detection: A/B CoT on and off against a held-out eval set for each model size; don't assume it helps.
- **Latency-bound settings.** CoT multiplies output tokens, and output tokens dominate both latency and cost. In a chat UX with a tight response-time budget it can be the wrong trade even when it would improve offline accuracy.
- **Verbalization distortion.** Liu et al. (2024) document tasks, some perception and pattern-matching problems, where making the model verbalize its process *degrades* performance compared with answering directly. Not every skill benefits from narration.
- **Faithfulness.** Turpin et al. (2023) show that a model's stated chain-of-thought can be a post-hoc rationalization, separate from the computation that produced the answer. Given a biasing cue (e.g., a leading suggestion earlier in the prompt), models flip their final answer while the *written* reasoning stays clean and never mentions the bias. So CoT text doesn't reliably tell you why the model answered as it did. Don't treat it as ground-truth interpretability, and don't use unfaithful CoT as an audit trail for high-stakes decisions.

## The non-obvious

CoT's role is flipping for reasoning models (as of 2026). o1-class models, DeepSeek-R1 and Claude's extended thinking mode learn long chain-of-thought through reinforcement learning against verifiable rewards (see [[Concept - GRPO and RL with Verifiable Rewards]]), with no prompt trigger needed. "Think step by step" is now trained into the base policy and comes out as hidden reasoning tokens whatever you ask for. Telling one of these models to think step by step is redundant at best and counterproductive at worst, since it can clash with the model's learned reasoning strategy (see [[Concept - Prompting Reasoning Models]]). Within about three years, the technique that defined a whole era of prompting research became something you have to consciously *stop* doing on frontier models. Prompting folklore expires when post-training changes its defaults.

## Connections
- [[Concept - GRPO and RL with Verifiable Rewards]] — the RL method that now trains long CoT directly into reasoning models, obsoleting the prompt-level trigger.
- [[Concept - Induction Heads]] — a lower-level circuit-based mechanism (prefix-match-and-copy) that contributes to why models can pick up and extend a reasoning pattern at all.
- [[Concept - The Emergent Abilities Debate]] — CoT's sharp parameter-count threshold is a canonical data point in that debate.
- [[Concept - Sampling and Decoding Parameters]] — self-consistency's $k$-sample majority vote depends directly on nonzero-temperature sampling.
- [[Decision - When to Use Chain-of-Thought]] — the operational decision flow this concept note feeds into.
- [[Concept - Prompting Reasoning Models]] — how CoT's role inverts once the model itself is RL-trained to reason.
- [[Concept - In-Context Learning]] — few-shot CoT is a specific, reasoning-augmented case of the general in-context learning mechanism.
- [[Playbook - Reliable Structured Output]] — why the reasoning trace and the final answer need visibly separate regions when CoT output must be parsed downstream.
- [[Lore - Let's Think Step by Step]] — the fuller folklore history of the trigger phrase and its machine-discovered successors.

## Sources
- Wei et al. (2022) — "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." The founding few-shot CoT result and its emergence threshold.
- Kojima et al. (2022) — "Large Language Models are Zero-Shot Reasoners." The "let's think step by step" zero-shot result (GSM8K ~18% → ~41%).
- Wang et al. (2022) — "Self-Consistency Improves Chain of Thought Reasoning in Language Models." The sample-and-vote technique.
- Turpin et al. (2023) — "Language Models Don't Always Say What They Think." The CoT faithfulness problem.
- Feng et al. (2023) — theoretical account of why CoT expands the class of problems a constant-depth transformer can solve.
- Nye et al. (2021) — "Show Your Work: Scratchpads for Intermediate Computation with Language Models." The original scratchpad framing.
