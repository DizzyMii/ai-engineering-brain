---
tags: [concept, domain/prompting-context, level/frontier]
aliases: [prompting o1, prompting thinking models]
summary: "Prompting inverts for RL-trained reasoning models: drop CoT and few-shot, use direct prompts, and budget thinking tokens."
---
# Concept - Prompting Reasoning Models

Everything an engineer learned about eliciting reasoning through prompt engineering — "let's think step by step," carefully chosen few-shot exemplars, self-consistency sampling — was built for models that reason only if you ask them to, in the prompt, every time. Reasoning models (OpenAI's o-series, DeepSeek-R1, Claude's extended thinking, Gemini's thinking mode) invert that assumption: they've been trained via reinforcement learning to produce long internal reasoning before answering, unprompted. Applying the old toolkit to the new models doesn't just waste tokens — it measurably degrades output, and that reversal is the single most important thing to internalize about prompting them (as of 2026).

## The mechanism
Classic instruction-tuned models compute one fixed-depth forward pass per output token; [[Concept - Chain-of-Thought and Why It Works]] works by getting the model to emit intermediate reasoning tokens in the prompt-visible output stream, effectively spending extra serial computation on a problem that a single forward pass couldn't solve. That extra computation had to be *requested* — hence "think step by step" as a lever an engineer pulls.

Reasoning models fold that lever into training. They are optimized with reinforcement learning against verifiable rewards (see [[Concept - GRPO and RL with Verifiable Rewards]]) to *decide for themselves*, per problem, how much internal reasoning to do before committing to an answer, and that reasoning is emitted as hidden "thinking" tokens — generated, billed, but not necessarily shown to the end user by default. The model has learned, from reward signal on correctness, its own policy for when reasoning helps and how long to keep going; a hand-written prompt heuristic layered on top isn't adding information the model lacks, it's competing with a policy that's already been optimized end-to-end for the same objective. That's why the classic techniques stop helping and start hurting: they're redundant instructions to a process the model already runs autonomously, and redundant instructions consume attention and token budget without adding signal.

## In practice
Stop adding explicit chain-of-thought instructions. OpenAI's own guidance for o1 is that it performs best with simple, direct prompts — state the task and constraints plainly and let the model's trained reasoning policy decide how to work through it, rather than prescribing a manual reasoning structure.

Few-shot exemplars can actively hurt. This is the sharpest reversal from classic [[Concept - In-Context Learning]]: OpenAI's reasoning-model guidance documents that few-shot exemplars often *reduce* o1/o3 performance relative to zero-shot, likely because exemplars anchor the model's own reasoning trace toward the exemplar's specific pattern instead of letting its trained policy explore the solution space for the live problem. Prefer a crisp, unambiguous zero-shot task specification.

DeepSeek-R1 has its own documented specifics: no system prompt (put everything in the user turn), temperature around 0.6 to avoid repetition and incoherence in the reasoning trace, avoid few-shot for the same reason as above, and force the final answer into a clearly delimited section separate from the reasoning — see [[Concept - Sampling and Decoding Parameters]] for the general role temperature plays in decoding.

Claude and Gemini expose an explicit thinking-token budget rather than making it fully implicit. Raising the budget helps on genuinely hard problems with diminishing returns, and it's a real cost lever: hidden thinking tokens are billed the same as any other output token, so a larger budget is a direct, sometimes large, addition to [[Concept - Cost Engineering for LLM Applications]] and introduces a latency step-change, not a gradual one — a problem that used to answer in two seconds can now take twenty because of an internal reasoning pass the user never sees.

When you need structured output from a reasoning model, keep the hidden reasoning and the final structured answer strictly separate: never attempt to parse the thinking trace as if it were the deliverable, and use tool-calling or a clearly labeled final field to extract the answer (see [[Playbook - Reliable Structured Output]]) — mixing the two invites both parsing failures and, worse, silently shipping half-formed reasoning as if it were a conclusion.

## Failure modes
Layering explicit CoT onto a reasoning model can degrade output quality and inflate cost simultaneously — the model reasons about how to follow your reasoning instructions on top of reasoning about the actual problem, burning thinking-token budget on meta-work. Few-shot exemplars silently regressing performance below zero-shot is easy to miss if a team ports over a few-shot template that worked well on an older instruct model without re-testing it against the reasoning model — see [[Decision - When to Use Chain-of-Thought]] for the explicit decision flow that flags reasoning models as the "skip CoT" branch. "Overthinking" — a reasoning model burning a large, expensive thinking budget on a trivial task ("what's 2+2") — is a real, observed failure mode with no universal fix beyond monitoring thinking-token counts per request and flagging outliers. And reasoning traces leaking into user-facing output (verbose, sometimes unpolished internal deliberation shown where only the final answer was wanted) is a UX and, in some deployments, an information-disclosure problem, not just an aesthetic one.

## The non-obvious
The entire folklore layer of prompt engineering — magic trigger phrases, tipping the model $200, threatening it, all cataloged in [[Lore - Let's Think Step by Step]] — was already perishable on classic instruct models, expiring as training regimes shifted. Reasoning models make that folklore actively counterproductive rather than merely useless: because the model's own RL-trained policy for *when and how much* to reason is more calibrated to the specific problem than any fixed heuristic an engineer writes once and reuses across tasks, stacking a hand-written reasoning nudge on top doesn't just fail to help — it can pull the model's trace away from the policy it learned and toward whatever pattern the nudge implies, for no benefit. The practical implication is uncomfortable for anyone with a large library of battle-tested prompts: that library needs to be re-evaluated, not ported, the first time a reasoning model enters the rotation, and open questions remain about how faithful the emitted reasoning trace actually is to the process producing the final answer (the same faithfulness problem documented for classic CoT — see [[Concept - Chain-of-Thought and Why It Works]] — has not been resolved for RL-trained reasoning traces either).

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
