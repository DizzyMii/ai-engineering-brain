---
tags: [lore, domain/agents, level/unicorn]
aliases: [agent prompting tricks, agent prompt folklore, recitation trick, error-as-observation]
summary: "Agent prompting tricks sorted into mechanism vs cargo cult: recitation, error-as-observation, tool_choice forcing, the reflection tax."
---

# Lore - Agent Prompt-Engineering Folklore

> Every team that has shipped an agent has a private list of prompt tricks that "made it reliable" — one-liners they add to the system prompt, formatting conventions they swear by, small rituals in the loop. Some of these are load-bearing mechanism you can trace to a paper or a KV-cache fact. Some are cargo cult: things that worked once, got copied, and now ride along untested. The two are indistinguishable from the outside, which is why this folklore is worth writing down *with the label attached*. What follows is the field's accumulated tribal knowledge, each item marked by how well it actually holds up.

## What happened

There was never a single event here — this is folklore in the literal sense, accreted across 2023–2026 out of practitioner writing (Anthropic's *Building Effective Agents* and *effective context engineering*, the Manus "context engineering for AI agents" post, aider's and Cursor's public engineering notes, OpenAI's GPT-4.1 prompting guide) and a much larger mass of Discord messages, bug reports, and "this fixed it for us" tweets. The through-line is that agents fail quietly (see [[Deep Dive - The Agent Loop]]), so people reach for prompt-level fixes before they reach for architecture, and a fix that correlates with a good run gets adopted whether or not it caused the good run. Here is the catalog, ordered from best-grounded to most cargo-cult.

**Recitation — well grounded.** Re-stating the goal, or a running to-do list, in the context *every turn* (or on a fixed interval) measurably fights goal drift on long runs. The mechanism is concrete: a long agent transcript pushes the original instruction thousands of tokens into the past, into the lost-in-the-middle dead zone where attention is weakest (Liu et al. 2023, "Lost in the Middle"; the general degradation is [[Concept - Context Rot]]). Re-emitting the goal into the *most recent* tokens — the highest-attention position — re-anchors it. Manus described this exactly: the agent rewrites a `todo.md` each step so the objective is always in the freshest part of the window. This is productized as the live to-do list in coding agents (`TodoWrite` in [[Breakdown - Claude Code]]). It is not decoration; it is putting the goal where the model can actually see it.

**Think-before-acting — grounded.** Forcing a short reasoning scratchpad *before* the tool call — an explicit "think about which tool and why" step — improves action selection. This is just [[Concept - The ReAct Pattern]] at the prompt level: interleaving a Thought before each Action is why ReAct beats act-only agents, because the reasoning grounds and decomposes before the model commits. Modern versions use interleaved extended thinking, but the folklore ("make it plan out loud first") predates the feature and is the same mechanism as [[Concept - Chain-of-Thought and Why It Works]].

**Error-as-observation — grounded.** When a tool handler throws, return the exception *as a normal tool result string the model can read*, rather than raising and crashing the loop. This lets the model see "FileNotFoundError: no such file `/foo`" and self-correct on the next turn instead of the harness dying. It is one of the highest-value four lines in any agent codebase and universally recommended. The subtlety: the error text has to be actionable — "error: 3" teaches the model nothing; "error: argument `date` must be ISO-8601, got `March 3`" lets it retry correctly.

**`tool_choice` forcing — grounded.** A model that *narrates* an action ("I will now search for...") instead of *emitting* the tool call is a common, maddening failure. Setting `tool_choice` to `required`/`any` (must call something) or to a named tool (must call that one) forces the call and breaks the narration loop. Mechanistically it constrains the decoder to the tool-call grammar rather than free text (see [[Concept - Tool Use and Function Calling]]). This one is a genuine lever, not folklore.

**The reflection tax — grounded caution.** Adding a "now critique your answer and revise" pass feels like it should help and often does not. Without an external signal, self-critique of *reasoning* can leave quality flat or make it worse (Huang et al. 2023, "Large Language Models Cannot Self-Correct Reasoning Yet"); the model rationalizes its original answer rather than finding the flaw. Extra reflection passes also burn tokens and latency linearly. The grounded version: reflection pays only when wired to a real oracle — a test suite, a compiler, retrieved evidence (full treatment in [[Concept - Reflection and Self-Correction]]). "Always add a reflection step" is cargo cult; "add a reflection step gated on a verifier" is engineering.

**Format lore — partly grounded, partly artifact.** The claim "XML-tag tool formatting works better with Claude, JSON schemas suit other models" is real but shallow-rooted. Part of it is a genuine training-distribution artifact (a model post-trained on a particular tool-call format is more fluent in it), and part is parser robustness (XML tags are easier to extract from a partially-malformed generation than nested JSON). It is true enough to act on and wrong enough to not treat as law — measure it on your model rather than importing another team's convention. Same caveat applies to delimiter and section-header rituals.

**Budget signals — folklore, weakly sourced.** Telling the agent "you have 5 turns left" or "you are running low on budget" to induce urgency and wrap-up. Sometimes it visibly changes behavior (the model summarizes and concludes); often it is simply ignored, because the model has no reliable internal sense of its remaining budget and the number is just more text. Treat it as a maybe, not a control — the actual budget enforcement has to live in the harness (`max_iterations`, token caps), not in a sentence the model can disregard.

**Persona and persistence framing — mixed evidence, the cargo-cult frontier.** Lines like *"You are an autonomous agent. Do not stop until the task is completely resolved. Do not hand back to the user prematurely."* have real provenance — OpenAI's GPT-4.1 prompting guide (2025) explicitly recommends a persistence reminder, a tool-calling reminder, and a planning reminder, and reports they lift agentic benchmark scores for that model. But the same lines get copied onto every model and every task indiscriminately, which is where it turns cargo cult: a persistence prompt on a task that *should* ask the user a clarifying question makes the agent worse, not better. Persona framing ("you are a senior engineer") has the weakest evidence of all — occasionally a small nudge, often pure ritual. End-of-turn hygiene (clean stop instructions, "return only the final answer") is more grounded because it interacts with the actual termination logic.

## The lesson

Mechanically, three things separate the grounded tricks from the cargo cult, and they are the same three every time:

1. **A grounded trick names its mechanism, and the mechanism is usually about *position or grounding*, not magic words.** Recitation works because of attention position. Error-as-observation works because it converts a crash into a signal. `tool_choice` works because it constrains the decoder. If a trick can't say *why* in terms of tokens, attention, the loop, or the training distribution, it is a candidate for cargo cult — flag it and A/B it.
2. **The dividing line between "helps" and "hurts" is almost always the presence of an external signal.** Reflection with a verifier helps; reflection alone hurts. Persistence on a well-specified task helps; persistence on an underspecified one hurts. The trick is rarely universally good or bad — it is conditional on whether there is ground truth in the loop.
3. **Prompt fixes are cheap, which is exactly why they metastasize.** A one-line addition to a system prompt costs nothing to add and nothing to leave in, so agent system prompts accrete tricks like barnacles and nobody removes them. The discipline is to *evaluate* each addition against a fixed task set and delete the ones that don't move the number — the same instinct that retired a generation of unmeasured training superstitions, catalogued in [[Lore - Hyperparameter Folklore]]. Most of this folklore is fine; the danger is the untested line that quietly makes your agent worse and rides along forever because no one measured it.

## Evidence status

- **Well-grounded (mechanism traceable):** recitation, think-before-acting, error-as-observation, `tool_choice` forcing, and the reflection-tax caution. Each maps to a documented mechanism (attention position, decoder constraint) or a published result (Liu et al. 2023 lost-in-the-middle; Huang et al. 2023 self-correction limits), and each is corroborated across multiple independent practitioner sources (Anthropic, Manus, aider).
- **Real but shallow-rooted:** format lore (XML vs JSON) and persistence/planning reminders — genuine effects (the GPT-4.1 guide's own measurements; training-distribution artifacts), but model-specific and routinely over-generalized. Act on them only after measuring on your own model and task.
- **Folklore, weakly sourced:** budget signals and persona framing — sometimes helpful, often inert, rarely harmful, essentially never independently validated. The honest label is "maybe," and the honest response is to move the actual control (budgets, clarification behavior) out of the prompt and into code.

## Connections
- [[Concept - Context Rot]] — the attention-degradation mechanism that makes recitation work; the "why" behind re-stating the goal each turn.
- [[Concept - The ReAct Pattern]] — the grounded basis for think-before-acting: interleaving reasoning before each action is the mechanism, not a superstition.
- [[Concept - Reflection and Self-Correction]] — the full treatment of the reflection tax and the external-signal boundary that decides whether self-critique helps.
- [[Concept - Context Engineering for Agents]] — where recitation, scratchpad offload, and cache-friendly layout become deliberate engineering rather than folklore.
- [[Deep Dive - The Agent Loop]] — the formal loop these tricks are trying to stabilize; error-as-observation and `tool_choice` forcing are loop-level interventions.
- [[Breakdown - Claude Code]] — a shipped agent where the recitation trick is productized as a live to-do list and error-as-observation is standard.
- [[Concept - Chain-of-Thought and Why It Works]] — the underlying reason a reasoning scratchpad before acting improves selection.
- [[Concept - Tool Use and Function Calling]] — the interface that `tool_choice` forcing operates on; the grounded fix for a model that narrates an action instead of emitting the call.
- [[Lore - Hyperparameter Folklore]] — the direct precedent from training: a body of copied, mostly-unmeasured lore where the discipline is the same — measure it or delete it.

## Sources
- Anthropic (2024) — "Building Effective Agents." The augmented-LLM baseline and the argument for the most-constrained pattern that works; source for several loop-level conventions.
- Anthropic (2025) — "Effective context engineering for AI agents." Recitation, scratchpad/filesystem offload, and cache-friendly transcript layout.
- Manus / Yichao Ji (2025) — "Context Engineering for AI Agents: Lessons from Building Manus." The `todo.md` recitation pattern and KV-cache-stability arguments from a production agent.
- Liu et al. (2023) — "Lost in the Middle: How Language Models Use Long Contexts." The positional-attention basis for why recitation and freshness matter.
- Huang et al. (2023) — "Large Language Models Cannot Self-Correct Reasoning Yet." The evidence behind the reflection tax and the external-signal requirement.
- OpenAI (2025) — "GPT-4.1 Prompting Guide." The persistence / tool-calling / planning reminders and their measured (model-specific) effect on agentic benchmarks.
