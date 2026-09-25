---
tags: [concept, domain/agents, level/core]
aliases: [function calling, tool calling]
summary: "How an LLM invokes external functions: schemas define the interface, the model emits structured calls, the harness executes and returns results."
---
> **One-paragraph hook:** Tool use turns a language model from a text generator into something that can act. But the model never sees your code, only the names, descriptions and parameter schemas you write for it. Every failure mode in this note traces back to that: the tool definition *is* the interface, and a badly written one produces a badly behaved agent however capable the model underneath is.

## The mechanism

The developer supplies **tool schemas**. Each tool gets a name, a natural-language description, and a JSON Schema for its parameters (types, which are required, enums where they apply). At inference time the model sees the user's request and the available schemas and emits a **structured call**, a tool name plus a JSON object of arguments, instead of (or alongside) natural-language text. The harness parses the call, runs the matching function, and returns the result as a **tool result message keyed by a call id**. That goes back into the transcript for the model's next turn (the full loop is in [[Deep Dive - The Agent Loop]]).

The two dominant provider APIs frame this differently on the wire. OpenAI's chat completions API uses a `tools` array of schemas and a `tool_calls` array on the assistant message, with results returned as `role: "tool"` messages keyed by `tool_call_id`. Anthropic's Messages API puts `tool_use` content blocks on the assistant turn and `tool_result` content blocks (keyed by the matching `tool_use_id`) in the next user turn. Both are JSON, but message roles and id placement differ, so code that switches providers has to handle both shapes explicitly (see [[Reference - Agent Framework Landscape]] for how frameworks abstract over this).

Valid JSON isn't down to the model's discipline. The decoder is typically **constrained/grammar-guided** during tool-call generation: at each step, sampling is restricted to tokens that keep the output schema-valid (see [[Concept - Constrained Decoding]]). On top of that, the models have been post-trained on large volumes of tool-call traces, so well-formed calls are the default and don't need coaxing through the prompt alone. That post-training is part of the broader [[Concept - Supervised Fine-Tuning (SFT)]] pipeline for tool-calling models.

`tool_choice` controls *whether* and *which* tool gets called on a turn. `auto` leaves it to the model, `required`/`any` forces a call to some registered tool instead of a plain-text reply, and naming a tool forces that one. Forcing is the standard fix for a model that narrates an intended action in prose ("I'll now search for...") without emitting the call. That happens surprisingly often when `tool_choice` is on `auto` and the system prompt is vague about when action is expected.

Modern models also do **parallel tool calls**. One assistant turn can hold several tool-call requests for independent actions (say, three unrelated searches at once). The harness fans out execution and must return *all* results before the next turn; a turn with some results missing will confuse the model or error.

## In practice

The most important fact about tool design: **the model only sees the name, the description, and the parameter descriptions**, never your implementation. Two tools with identical behavior and different descriptions get selected at meaningfully different rates. A tool named `search` described as "searches" gets picked worse than `search_product_catalog` with a description saying when to use it and when not to (the review process is in [[Checklist - Agent Tool Definition Review]]). Use enums over free-form strings for constrained parameters (`unit: "celsius" | "fahrenheit"`, not a free string). The schema then rules out invalid values, which removes a whole class of malformed-argument failures.

Selection accuracy also depends on how many tools are registered. Past roughly **20-40 tools** in one agent's toolset, selection quality has historically degraded: the model confuses tools with similar names or descriptions, or doesn't notice the right one exists in a long list. The standard mitigations:

- Retrieval over tools: inject only the schemas relevant to the current step, the same move as RAG applied to tool definitions.
- Namespacing: group related tools under a prefix so the model can reason about categories.
- Splitting a large toolset across sub-agents that each see a smaller, focused set.

## Failure modes

- **Hallucinated tool names.** The model calls a tool that isn't in the registered set, usually because a similarly named tool exists in its training or in an earlier turn's context. Fix: validate the name against the registry before dispatch and return a clear error. Don't silently no-op.
- **Malformed or wrongly typed arguments.** A required field is missing, or a value has the wrong type (string `"5"` where an integer is expected). Constrained decoding reduces this but doesn't eliminate it, so you still need strict server-side validation with an error string the model can read.
- **Ignoring available tools.** The model answers from its own (possibly stale or wrong) knowledge instead of calling a tool that would have grounded the answer. Often the cause is a vague description that didn't signal the tool fit this situation.
- **Oversized results eating context.** A tool that returns 10K tokens of raw JSON crowds out the rest of the transcript and can push a long-running agent toward context overflow. Truncate, summarize or paginate on the tool side before the result reaches the model (see [[Checklist - Agent Tool Definition Review]]).

## The non-obvious

Teams keep over-investing in model choice and under-investing in tool descriptions. Past the simplest single-tool case, the description does more work than the model's raw capability. A stronger model rarely fixes a selection problem caused by two tools with overlapping descriptions; rewriting the descriptions usually does. Treat the schema as a user interface for a very literal-minded user, and give it the design care you'd give a public API.

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
