---
tags: [concept, domain/prompting-context, level/core]
aliases: [CoT, chain of thought, let's think step by step]
summary: "CoT trades serial forward passes for computation depth, letting a fixed-depth transformer solve problems it can't in one shot."
---
> **One-paragraph hook:** A transformer layer stack has fixed depth — every generated token gets exactly the same, bounded amount of computation no matter how hard the underlying problem is. Chain-of-thought works because it converts a single hard token-prediction into many easy ones: instead of computing an answer in one forward pass, the model computes intermediate reasoning tokens, feeds each back in as new context, and effectively gets a fresh forward pass — and a fresh chance to condition on progress so far — per step. It is test-time compute smuggled in through the autoregressive loop, not a magic incantation.

## The mechanism

Every generated token, whether it's part of a final answer or a reasoning step, costs the model exactly one forward pass through a fixed number of layers — a constant amount of serial computation. If a task genuinely requires more sequential computation than fits in that fixed depth (multi-step arithmetic, multi-hop logic), a model forced to answer directly has no way to "think longer" — it must compress the whole solution path into one shot. Chain-of-thought sidesteps this by having the model emit intermediate tokens: each reasoning token becomes part of the context for the *next* token, so a problem requiring $k$ sequential steps of computation gets $k$ forward passes instead of one. This is a scratchpad in the literal sense — Nye et al. (2021) explicitly framed it this way ("Show Your Work") — and Feng et al. (2023) formalized *why* it must help: a constant-depth transformer is provably limited in the class of functions it can compute in one pass, but with CoT it can simulate arbitrarily long serial computations, expanding the class of problems solvable at all, not just improving accuracy on problems already in reach. The same attention circuitry that lets a model complete an in-context pattern — the [[Concept - Induction Heads]] responsible for prefix-match-and-copy behavior — is part of what lets it latch onto and extend the reasoning pattern laid down by earlier steps in its own chain of thought.

Two landmark empirical results established this as a practitioner-usable technique rather than a theoretical curiosity:
- **Few-shot CoT** — Wei et al. (2022): including worked-out reasoning in the few-shot exemplars (see [[Concept - In-Context Learning]]) produces large gains on GSM8K, arithmetic, and commonsense reasoning benchmarks. Critically, the effect **emerges** — it appears only once models cross roughly 60-100B parameters; below that threshold, CoT prompting can *hurt* accuracy relative to direct answering, because small models generate plausible-looking but wrong reasoning that then anchors a wrong answer. This is one of the cleaner data points in the broader [[Concept - The Emergent Abilities Debate]].
- **Zero-shot CoT** — Kojima et al. (2022): appending the literal phrase "Let's think step by step" with *no* exemplars at all lifted GPT-3's zero-shot GSM8K accuracy from roughly 18% to roughly 41%. No new information was added to the prompt — the phrase simply nudged the model into emitting the scratchpad behavior it already had latent from pretraining (see [[Lore - Let's Think Step by Step]] for the fuller history of trigger-phrase folklore).

**Self-consistency** (Wang et al. 2022) pushes further: sample $k$ independent chain-of-thought paths at nonzero temperature (see [[Concept - Sampling and Decoding Parameters]]), then take a majority vote over the $k$ final answers rather than trusting any single path. This trades $k\times$ the inference compute for roughly +10 to +18 points on GSM8K-class benchmarks, on the theory that correct reasoning paths agree with each other more often than wrong ones happen to coincide.

## In practice

CoT is not free and is not always appropriate — see [[Decision - When to Use Chain-of-Thought]] for the full decision flow. The short version: on a non-reasoning instruction-tuned model doing multi-step math or logic, use CoT (few-shot if you have exemplars, zero-shot trigger phrase otherwise); if you have compute to spare and need maximum accuracy, layer self-consistency on top. If the output must be machine-parseable, keep the reasoning and the final answer in visibly separate regions (a delimiter or a dedicated field) so a downstream parser doesn't have to sift free-form prose for the answer — this is directly relevant to [[Playbook - Reliable Structured Output]].

## Failure modes

- **CoT hurts below the emergence threshold.** Small or weak models (roughly sub-10B, task-dependent) often do worse with CoT than with a direct answer, because their generated reasoning is noisy and the wrong conclusion gets reinforced by its own scratchpad. Detection: A/B the presence of CoT against a held-out eval set per model size rather than assuming it always helps.
- **Latency-bound settings.** CoT multiplies output tokens, and output tokens dominate both latency and cost. In a chat UX with a tight response-time budget, CoT can be the wrong tradeoff even when it would improve offline accuracy.
- **Verbalization distortion.** Liu et al. (2024) document tasks — some perception and pattern-matching problems — where forcing the model to verbalize its process actively *degrades* performance versus answering directly; not every skill benefits from being narrated.
- **The faithfulness problem.** Turpin et al. (2023) show that a model's stated chain-of-thought can be a post-hoc rationalization rather than the actual computation driving the answer: under a biasing cue (e.g., a leading suggestion embedded earlier in the prompt), models will flip their final answer while the *written* reasoning stays clean and never mentions the bias. This means CoT text is not a reliable window into why the model answered as it did — do not treat it as ground-truth interpretability, and do not use unfaithful CoT as an audit trail for high-stakes decisions.

## The non-obvious

The practically important shift as of 2026 is that CoT's role is inverting for reasoning models. o1-class models, DeepSeek-R1, and Claude's extended thinking mode internalize long chain-of-thought via reinforcement learning against verifiable rewards (see [[Concept - GRPO and RL with Verifiable Rewards]]) rather than relying on a prompt trigger — the "think step by step" behavior is now trained into the base policy, emitted as hidden reasoning tokens regardless of what you ask for. Telling one of these models to "think step by step" is at best redundant and at worst actively counterproductive, since it can conflict with the model's own learned reasoning strategy (see [[Concept - Prompting Reasoning Models]]). The technique that defined an entire prompting-research era became, within about three years, something you have to consciously *stop* doing on frontier models — a sharp reminder that prompting folklore has a shelf life tied to what post-training currently does by default.

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
