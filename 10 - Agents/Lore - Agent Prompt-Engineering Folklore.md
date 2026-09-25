---
tags: [lore, domain/agents, level/unicorn]
aliases: [agent prompting tricks, agent prompt folklore, recitation trick, error-as-observation]
summary: "Agent prompting tricks sorted into mechanism vs cargo cult: recitation, error-as-observation, tool_choice forcing, the reflection tax."
---

# Lore - Agent Prompt-Engineering Folklore

> Every team that has shipped an agent keeps a private list of prompt tricks that "made it reliable": one-liners in the system prompt, formatting conventions they swear by, small rituals in the loop. Some are real mechanism you can trace to a paper or a KV-cache fact. Some are cargo cult: they worked once, got copied, and now ride along untested. From the outside you can't tell the two apart, so this note writes the folklore down *with the label attached*, each item marked by how well it holds up.

## What happened

No single event here. It's folklore in the literal sense, built up over 2023–2026 from practitioner writing (Anthropic's *Building Effective Agents* and *effective context engineering*, the Manus "context engineering for AI agents" post, aider's and Cursor's public engineering notes, OpenAI's GPT-4.1 prompting guide) and a much larger pile of Discord messages, bug reports and "this fixed it for us" tweets. The common thread: agents fail without making noise (see [[Deep Dive - The Agent Loop]]), so people reach for prompt-level fixes before architecture, and a fix that coincides with a good run gets adopted whether or not it caused it. The catalog below runs from best-grounded to most cargo-cult.

**Recitation: well grounded.** Restating the goal, or a running to-do list, in the context *every turn* (or on a fixed interval) measurably reduces goal drift on long runs. The mechanism is concrete. A long transcript pushes the original instruction thousands of tokens back, into the lost-in-the-middle zone where attention is weakest (Liu et al. 2023, "Lost in the Middle"; the general degradation is [[Concept - Context Rot]]). Re-emitting the goal into the *most recent* tokens, the highest-attention position, re-anchors it. Manus described doing this: the agent rewrites a `todo.md` each step so the objective always sits in the freshest part of the window. Coding agents ship it as the live to-do list (`TodoWrite` in [[Breakdown - Claude Code]]). It puts the goal where the model can see it.

**Think-before-acting: grounded.** Forcing a short reasoning scratchpad *before* the tool call ("think about which tool and why") improves action selection. That's [[Concept - The ReAct Pattern]] at the prompt level. A Thought before each Action is why ReAct beats act-only agents: the reasoning grounds and decomposes before the model commits. Modern versions use interleaved extended thinking, but the folklore ("make it plan out loud first") predates the feature and runs on the same mechanism as [[Concept - Chain-of-Thought and Why It Works]].

**Error-as-observation: grounded.** When a tool handler throws, return the exception *as an ordinary tool result string the model can read*. Don't raise and crash the loop. The model then sees "FileNotFoundError: no such file `/foo`" and corrects itself next turn, and the harness stays alive. These are among the most valuable four lines in any agent codebase, and everyone recommends them. The catch is that the error text has to be actionable. "error: 3" teaches the model nothing; "error: argument `date` must be ISO-8601, got `March 3`" lets it retry correctly.

**`tool_choice` forcing: grounded.** A model that *narrates* an action ("I will now search for...") without *emitting* the tool call is a common and maddening failure. Setting `tool_choice` to `required`/`any` (must call something) or to a named tool (must call that one) forces the call and ends the narration. Mechanically, it constrains the decoder to the tool-call grammar instead of free text (see [[Concept - Tool Use and Function Calling]]). This one is a real lever, not folklore.

**The reflection tax: grounded caution.** A "now critique your answer and revise" pass feels like it should help and often doesn't. Without an external signal, self-critique of *reasoning* can leave quality flat or make it worse (Huang et al. 2023, "Large Language Models Cannot Self-Correct Reasoning Yet"); the model defends its original answer instead of finding the flaw. Each extra pass also adds tokens and latency linearly. Reflection pays only when it's wired to a real oracle: a test suite, a compiler, retrieved evidence (full treatment in [[Concept - Reflection and Self-Correction]]). "Always add a reflection step" is cargo cult. "Add a reflection step gated on a verifier" is engineering.

**Format lore: partly grounded, partly artifact.** "XML-tag tool formatting works better with Claude, JSON schemas suit other models" is real but shallow. Part of it is a training-distribution artifact (a model post-trained on one tool-call format is more fluent in it). Part is parser robustness (XML tags are easier to pull out of a partly malformed generation than nested JSON). It's true enough to act on and not reliable enough to treat as law, so measure it on your model instead of importing another team's convention. The same goes for delimiter and section-header rituals.

**Budget signals: folklore, weakly sourced.** Telling the agent "you have 5 turns left" or "you are running low on budget" to make it wrap up. Sometimes behavior visibly changes (the model summarizes and concludes). Often it's ignored, because the model has no reliable sense of its remaining budget and the number is just more text. Treat it as a maybe. Real budget enforcement lives in the harness (`max_iterations`, token caps), not in a sentence the model can ignore.

**Persona and persistence framing: mixed evidence, where cargo cult starts.** Lines like *"You are an autonomous agent. Do not stop until the task is completely resolved. Do not hand back to the user prematurely."* have real provenance. OpenAI's GPT-4.1 prompting guide (2025) explicitly recommends a persistence reminder, a tool-calling reminder and a planning reminder, and reports that they lift agentic benchmark scores for that model. The trouble is that people copy the same lines onto every model and every task. A persistence prompt on a task that *should* ask the user a clarifying question makes the agent worse. Persona framing ("you are a senior engineer") has the weakest evidence of all: occasionally a small nudge, often pure ritual. End-of-turn hygiene (clean stop instructions, "return only the final answer") is better grounded because it interacts with the actual termination logic.

## The lesson

The same three things separate grounded tricks from cargo cult every time:

1. **A grounded trick names its mechanism, and the mechanism is usually about *position or grounding*, not magic words.** Recitation works because of attention position. Error-as-observation turns a crash into a signal. `tool_choice` constrains the decoder. If you can't explain a trick in terms of tokens, attention, the loop or the training distribution, suspect cargo cult: flag it and A/B it.
2. **Whether a trick helps or hurts almost always depends on an external signal.** Reflection with a verifier helps; reflection alone hurts. Persistence on a well-specified task helps; on an underspecified one it hurts. Few tricks are good or bad everywhere. It depends on whether ground truth is in the loop.
3. **Prompt fixes are cheap, so they spread.** A one-line addition costs nothing to add and nothing to leave in, so agent system prompts collect tricks like barnacles and nobody removes them. *Evaluate* each addition against a fixed task set and delete the ones that don't move the number. It's the same habit that retired a generation of unmeasured training superstitions, catalogued in [[Lore - Hyperparameter Folklore]]. Most of this folklore is fine. The danger is the untested line that makes your agent worse and stays forever because nobody measured it.

## Evidence status

- **Well-grounded (mechanism traceable):** recitation, think-before-acting, error-as-observation, `tool_choice` forcing, and the reflection-tax caution. Each maps to a documented mechanism (attention position, decoder constraint) or a published result (Liu et al. 2023 lost-in-the-middle; Huang et al. 2023 self-correction limits), and each is corroborated by several independent practitioner sources (Anthropic, Manus, aider).
- **Real but shallow-rooted:** format lore (XML vs JSON) and persistence/planning reminders. The effects are real (the GPT-4.1 guide's own measurements; training-distribution artifacts) but model-specific and routinely over-generalized. Act on them only after measuring on your own model and task.
- **Folklore, weakly sourced:** budget signals and persona framing. Sometimes helpful, often inert, rarely harmful, essentially never independently validated. The honest label is "maybe," and the honest response is to move the real control (budgets, clarification behavior) out of the prompt and into code.

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
