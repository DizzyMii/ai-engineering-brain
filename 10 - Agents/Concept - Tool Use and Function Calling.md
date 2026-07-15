---
tags: [concept, domain/agents, level/core]
aliases: [function calling, tool calling]
summary: "How an LLM invokes external functions: schemas define the interface, the model emits structured calls, the harness executes and returns results."
---
> **One-paragraph hook:** Tool use is the mechanism that turns a language model from a text generator into something that can act — but the model never sees your code, only the names, descriptions, and parameter schemas you write for it. Every failure mode in this note traces back to that one fact: the tool definition *is* the interface, and a badly written one produces a badly behaved agent regardless of how capable the underlying model is.

## The mechanism

The developer supplies **tool schemas**: for each tool, a name, a natural-language description, and a JSON Schema describing its parameters (types, which are required, enums where applicable). At inference time the model, seeing the user's request and the available schemas, emits a **structured call** — a tool name plus a JSON object of arguments — instead of (or alongside) natural-language text. The harness parses that call, executes the corresponding function, and returns the result as a **tool result message keyed by a call id**, which goes back into the transcript for the model's next turn (the full loop is [[Deep Dive - The Agent Loop]]).

The two dominant provider APIs implement this with different wire framing though the same underlying idea. OpenAI's chat completions API uses a `tools` array of schemas and a `tool_calls` array on the assistant message, with results returned as `role: "tool"` messages keyed by `tool_call_id`. Anthropic's Messages API uses `tool_use` content blocks on the assistant turn and `tool_result` content blocks (keyed by the matching `tool_use_id`) in the next user turn. Both are JSON under the hood, but they diverge on message roles and id placement — code that switches providers has to handle both shapes explicitly (see [[Reference - Agent Framework Landscape]] for how frameworks abstract over this).

Under the hood, the model doesn't just "decide" to produce valid JSON by discipline — the decoder is typically **constrained/grammar-guided** during tool-call generation, meaning the sampling process is restricted at each step to only tokens that keep the output schema-valid (see [[Concept - Constrained Decoding]]). This is layered on top of models that have also been post-trained on large volumes of tool-call traces, so schema-valid, well-formed calls are the default behavior rather than something the model has to be coaxed into with prompting alone (this post-training is part of the broader [[Concept - Supervised Fine-Tuning (SFT)]] pipeline for tool-calling models).

`tool_choice` gives the caller control over *whether* and *which* tool gets called on a given turn: `auto` leaves the decision to the model, `required`/`any` forces it to call something (any registered tool) rather than respond in plain text, and naming a specific tool forces exactly that one. Forcing is the standard fix for a model that narrates an intended action in prose ("I'll now search for...") instead of actually emitting the call — a surprisingly common failure when `tool_choice` is left on `auto` and the system prompt is ambiguous about when action is expected.

Modern models also support **parallel tool calls**: a single assistant turn can contain multiple tool-call requests for independent actions (e.g., searching three unrelated queries at once), and the harness is responsible for fanning out execution and returning *all* results before sending the next turn — a turn with some results present and others missing will confuse or error the model.

## In practice

The single highest-leverage fact about tool design is that **the model only ever sees the name, the description, and the parameter descriptions** — never your implementation. Two tools with identical underlying behavior but different descriptions will be selected at meaningfully different rates; a tool named `search` with the description "searches" will be picked worse than one named `search_product_catalog` with a description stating exactly when to use it and when not to (formalized as a review process in [[Checklist - Agent Tool Definition Review]]). Preferring enums over free-form strings for constrained parameters (e.g., `unit: "celsius" | "fahrenheit"` instead of a free string) removes an entire class of malformed-argument failure, because the schema itself rules out invalid values rather than relying on the model to get a string exactly right.

Tool-selection accuracy is not flat with respect to how many tools are registered. Past roughly **20-40 tools** in a single agent's toolset, selection quality historically degrades — the model starts confusing similarly-named or similarly-described tools, or fails to notice the right tool exists at all among a long list. The standard mitigations are retrieval over tools (only inject the schemas relevant to the current step, rather than all of them, into context — the same move as RAG applied to tool definitions), namespacing (grouping related tools under a prefix so the model can reason about categories), and splitting a large toolset across sub-agents that each see a smaller, focused set.

## Failure modes

- **Hallucinated tool names**: the model emits a call to a tool that doesn't exist in the registered schema set, usually because a similarly-named tool exists elsewhere in its training or a previous turn's context. Fix: validate the call name against the registry before dispatch and return a clear error rather than silently no-op'ing.
- **Malformed or wrongly-typed arguments**: a required field missing, or a value of the wrong type (string `"5"` where an integer is expected). Constrained decoding reduces but does not eliminate this — strict server-side validation with a model-readable error string is still required.
- **Ignoring available tools**: the model answers from its own (possibly stale or wrong) knowledge instead of calling a tool that would have grounded the answer — often a symptom of a vague description that didn't signal the tool was relevant to this situation.
- **Oversized results eating context**: a tool that returns 10K tokens of raw JSON crowds out the rest of the transcript and can push a long-running agent toward context overflow; the fix is tool-side truncation, summarization, or pagination before the result ever reaches the model (see [[Checklist - Agent Tool Definition Review]]).

## The non-obvious

Teams consistently over-invest in model choice and under-invest in tool description quality, when in practice the description is doing more work than the model's raw capability for anything past the simplest single-tool case — swapping in a stronger model rarely fixes a tool-selection problem caused by two tools with overlapping descriptions, but rewriting the descriptions usually does. The tool schema is a user interface, written for an unusual and very literal-minded user, and it deserves the same design rigor a public API would get.

## Connections
- [[Concept - Model Context Protocol (MCP)]] — the open standard for packaging and distributing tool (and resource) definitions across applications, built directly on this tool-calling mechanism.
- [[Reference - Agent Framework Landscape]] — where the OpenAI-vs-Anthropic wire-format split this note describes gets abstracted away (or leaks through) across frameworks.
- [[Deep Dive - The Agent Loop]] — the surrounding control loop that calls the model, dispatches the tool, and feeds the result back in; this note is the mechanics of one link in that chain.
- [[Concept - Constrained Decoding]] — the decoder-level technique that keeps tool-call output schema-valid, underlying every provider's structured tool calling.
- [[Checklist - Agent Tool Definition Review]] — the concrete pre-flight process for applying the naming/description/schema guidance in this note to a real tool before shipping it.
- [[Gotchas - Tool Use and Function Calling]] — the aggregated pitfall list this note's failure-modes section is a preview of, ordered by frequency and pain.
- [[Snippet - A Minimal ReAct Loop]] — a complete runnable implementation showing schema definition, dispatch, and id-matching in ~50 lines.
- [[Playbook - Reliable Structured Output]] — the broader technique family (of which forced tool_choice is one instance) for getting models to reliably emit a specific shape.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the post-training stage that teaches models to emit well-formed tool calls natively rather than needing heavy in-context coaxing.

## Sources
- OpenAI and Anthropic API documentation — the two dominant wire formats (`tools`/`tool_calls` vs `tool_use`/`tool_result`) referenced in this note reflect each provider's current (2026) Messages/Chat Completions specification.
