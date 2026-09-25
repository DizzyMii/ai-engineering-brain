---
tags: [concept, domain/prompting-context, level/frontier]
aliases: [prompting o1, prompting thinking models]
summary: "Prompting inverts for RL-trained reasoning models: drop CoT and few-shot, use direct prompts, and budget thinking tokens."
---
# Concept - Prompting Reasoning Models

The prompting toolkit for eliciting reasoning ("let's think step by step", carefully picked few-shot exemplars, self-consistency sampling) was built for models that only reason when the prompt asks them to, every time. Reasoning models (OpenAI's o-series, DeepSeek-R1, Claude's extended thinking, Gemini's thinking mode) flip that. Reinforcement learning has trained them to produce long internal reasoning before answering, unprompted. Using the old toolkit on them wastes tokens and measurably degrades output, and that reversal is the main thing to understand about prompting them (as of 2026).

## The mechanism
Classic instruction-tuned models do one fixed-depth forward pass per output token. [[Concept - Chain-of-Thought and Why It Works]] gets the model to write intermediate reasoning tokens into the visible output, which spends extra serial computation on a problem one forward pass couldn't solve. That extra computation had to be *requested*, so "think step by step" was a lever the engineer pulled.

Reasoning models move the lever into training. They're optimized with reinforcement learning against verifiable rewards (see [[Concept - GRPO and RL with Verifiable Rewards]]) to *decide for themselves*, per problem, how much to reason before committing to an answer. The reasoning comes out as hidden "thinking" tokens: generated and billed, but not necessarily shown to the user by default. From reward on correctness, the model has learned its own policy for when reasoning helps and how long to continue. A hand-written prompt heuristic on top adds no information the model lacks; it competes with a policy already optimized end to end for the same goal. So the classic techniques stop helping and start hurting. They're redundant instructions to a process the model already runs, and redundant instructions use attention and token budget without adding signal.

## In practice
Drop explicit chain-of-thought instructions. OpenAI's guidance for o1 is that it does best with simple, direct prompts: state the task and constraints plainly and let the trained reasoning policy decide how to work through it. Don't prescribe a manual reasoning structure.

Few-shot exemplars can hurt. This is the sharpest reversal from classic [[Concept - In-Context Learning]]. OpenAI's reasoning-model guidance documents few-shot exemplars often *reducing* o1/o3 performance compared with zero-shot, likely because they anchor the model's reasoning trace to the exemplar's pattern instead of letting its policy explore the live problem. Prefer a crisp, unambiguous zero-shot task spec.

DeepSeek-R1 has its own documented specifics. No system prompt (put everything in the user turn). Temperature around 0.6 to avoid repetition and incoherence in the reasoning trace. No few-shot, for the reason above. And force the final answer into a clearly delimited section apart from the reasoning. [[Concept - Sampling and Decoding Parameters]] covers the general role of temperature in decoding.

Claude and Gemini expose an explicit thinking-token budget instead of keeping it fully implicit. A bigger budget helps on hard problems, with diminishing returns, and it's a real cost lever. Hidden thinking tokens bill like any other output token, so a larger budget adds directly, sometimes heavily, to [[Concept - Cost Engineering for LLM Applications]]. Latency jumps in a step, not gradually: a problem that answered in two seconds can now take twenty because of a reasoning pass the user never sees.

When you need structured output from a reasoning model, keep the hidden reasoning and the final structured answer strictly apart. Never parse the thinking trace as if it were the deliverable. Extract the answer through tool calling or a clearly labeled final field (see [[Playbook - Reliable Structured Output]]). Mixing the two causes parsing failures and, worse, can silently ship half-formed reasoning as a conclusion.

## Failure modes
Adding explicit CoT to a reasoning model can hurt quality and raise cost at once. The model reasons about how to follow your reasoning instructions on top of reasoning about the problem, burning thinking budget on meta-work.

Few-shot exemplars dropping performance below zero-shot is easy to miss when a team ports a few-shot template that worked on an older instruct model and doesn't re-test it. [[Decision - When to Use Chain-of-Thought]] has the decision flow that sends reasoning models down the "skip CoT" branch.

"Overthinking", where a reasoning model burns a large, expensive thinking budget on a trivial task ("what's 2+2"), is a real, observed failure. There's no universal fix beyond monitoring thinking-token counts per request and flagging outliers.

Reasoning traces can also leak into user-facing output: verbose, sometimes unpolished deliberation shown where only the answer was wanted. That's a UX problem and, in some deployments, an information-disclosure problem, beyond aesthetics.

## The non-obvious
The folklore layer of prompt engineering (magic trigger phrases, tipping the model $200, threatening it, all collected in [[Lore - Let's Think Step by Step]]) was already perishable on classic instruct models and expired as training regimes changed. Reasoning models make it counterproductive, which is worse than useless. The model's RL-trained policy for *when and how much* to reason is better calibrated to each problem than any fixed heuristic an engineer writes once and reuses. A hand-written nudge on top can pull the trace away from the learned policy toward whatever pattern the nudge implies, for no benefit.

That's uncomfortable if you own a big library of battle-tested prompts. The first time a reasoning model enters the rotation, the library needs re-evaluating; porting it over as-is won't do. There are also open questions about how faithful the emitted reasoning trace is to the process that produces the answer. The faithfulness problem documented for classic CoT (see [[Concept - Chain-of-Thought and Why It Works]]) hasn't been resolved for RL-trained reasoning traces either.

## Connections
- [[Concept - GRPO and RL with Verifiable Rewards]] — the training mechanism that internalizes reasoning, which is why prompting it externally becomes redundant.
- [[Concept - Chain-of-Thought and Why It Works]] — the classic technique this concept explicitly inverts, and whose faithfulness problem persists in the new setting.
- [[Concept - In-Context Learning]] — the mechanism whose usual benefit (few-shot exemplars) reverses sign on reasoning models.
- [[Decision - When to Use Chain-of-Thought]] — the decision flow that operationalizes "reasoning model → skip CoT" as a concrete branch.
- [[Concept - Cost Engineering for LLM Applications]] — hidden thinking tokens are a direct, sometimes large, line item this discipline must account for.
- [[Concept - Sampling and Decoding Parameters]] — temperature and other decoding settings behave differently for reasoning traces (e.g. R1's ~0.6 recommendation).
- [[Playbook - Reliable Structured Output]] — the procedure for keeping hidden reasoning and the final answer cleanly separated.
- [[Lore - Let's Think Step by Step]] — the folklore layer of prompt tricks that this concept shows going from merely perishable to actively counterproductive.

## Sources
- OpenAI — reasoning-model (o1) prompting guidance: the source for "simple, direct prompts" and the documented few-shot regression versus zero-shot.
- DeepSeek-AI (2025) — DeepSeek-R1 usage recommendations: no system prompt, temperature ~0.6, avoid few-shot, delimited final-answer section.
- Turpin et al. (2023) — "Language Models Don't Always Say What They Think": the CoT faithfulness problem this note flags as unresolved for RL-trained reasoning traces too.
