---
tags: [playbook, domain/agents, level/core]
aliases: []
summary: "End-to-end procedure to build a tool-use agent on a raw model API -- no framework -- from tool schemas to a hardened loop."
---

# Playbook - Building a Tool-Use Agent from Scratch

> **Goal:** stand up a working [[Deep Dive - The Agent Loop|agent loop]] against a raw provider SDK, with correctly dispatched tool calls and a clean stop condition. **When to run this:** any time you need a tool-use agent and the task doesn't yet justify a framework -- see [[Decision - Choosing an Agent Framework]] for when it does. **Prerequisites:** a model API with native [[Concept - Tool Use and Function Calling|tool calling]], 1-3 real tools (not toy stubs), and a task that genuinely needs more than one step.

## Steps

1. **Write tool schemas and handlers.**
   Action: for each tool, define a JSON Schema (name, natural-language description, typed parameters) and the Python function that executes it -- run every schema against the [[Checklist - Agent Tool Definition Review]] before moving on.
   Expected observation: the schema round-trips through the SDK's tool-definition validator with no error, and a trivial single-step task calls the right tool on the first try.
   What deviation means: an SDK validation error usually means a malformed `required` array or an unsupported JSON Schema type; a wrong-tool-called result on a trivial task means a description problem, not a loop problem -- fix it here before it contaminates every later step.

2. **Write the system prompt.**
   Action: state the agent's role, name the available tools and when to use each, and give an explicit stopping rule ("emit a final answer with no tool call once the task is complete").
   Expected observation: the model calls a tool directly rather than narrating an intended action in prose ("I'll now look up...").
   What deviation means: narration instead of action is the standard symptom of an ambiguous stopping/acting instruction, or `tool_choice` left on `auto` when the task needs it forced -- set `tool_choice="required"` (or name the tool directly) for the first turn to confirm the model *can* act before debugging anything else.

3. **Build the loop.**
   Action: call the model with the running message list and tool schemas; if the response contains tool calls, dispatch each handler and append a tool-result message keyed by the call's id; otherwise treat the response as the final answer and exit.
   Expected observation: a task requiring two dependent tool calls produces exactly two tool-result messages, each id-matched to its call, before the final answer arrives.
   What deviation means: an API error citing an unmatched id means a result was appended out of order, duplicated, or dropped in the harness -- the bug is in your dispatch code, not the model's output.

4. **Add hard limits.**
   Action: cap `max_iterations` (10-50 is typical for a single-agent loop, per [[Deep Dive - The Agent Loop]]) and enforce a running token/cost budget; on either limit, stop the loop and return an explicit "budget exceeded" message instead of the model's incomplete state.
   Expected observation: a deliberately adversarial test tool (one that always replies "try again") halts the loop at the iteration cap instead of running indefinitely.
   What deviation means: if it doesn't halt, the cap check is sitting outside the actual per-turn call site -- verify it executes on every iteration, not just at loop entry.

5. **Wrap every handler so exceptions return as tool-result error text.**
   Action: catch exceptions inside each handler (or in the dispatch wrapper) and return an actionable, model-readable string ("file not found: check the path argument") as the tool result -- never let an exception propagate and kill the process.
   Expected observation: an intentionally broken call (bad path, invalid argument) produces a tool result the model reads and reacts to, typically by retrying with corrected arguments.
   What deviation means: a crashed process means an exception escaped the wrapper somewhere in the dispatch path -- audit every handler, not just the one you tested.

6. **Log every turn as a structured span.**
   Action: record the full message, the tool call(s), and the tool result(s) per turn as structured, queryable spans -- not stdout prints -- as the seed of real [[Concept - LLM Observability and Tracing|observability]].
   Expected observation: you can reconstruct the entire trace of any run, including a failed one, from the logs alone without rerunning it.
   What deviation means: if you can't, the logging is capturing summaries instead of raw turns -- fix this before shipping, since it's the only lever you have for debugging Steps 3-5 after the fact.

## Verification

Run a task that requires **two dependent tool calls** -- the second call's arguments must depend on the first call's result (e.g., "look up the user's account id, then fetch their order history"). Inspect the trace: every tool-result id must match its originating call's id, the second call's arguments must reflect the first call's actual output rather than a hallucinated value, and the loop must exit on a final message containing no tool call. A single-tool-call task is not sufficient verification -- it can pass even with broken id-matching logic, because there's only ever one id to get right.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Infinite or oscillating tool loop, same call repeated | Model rationalizing a failing action; no loop detection | Cap `max_iterations`; detect and short-circuit identical repeated calls (see [[Gotchas - Tool Use and Function Calling]]) |
| Model never calls the tool, just narrates | Weak stopping/acting instruction, or `tool_choice="auto"` with an ambiguous prompt | Force `tool_choice="required"` or a named tool; sharpen the "when to use" language in the description |
| API error: malformed or wrongly-typed arguments | Underspecified schema -- missing enum, loose type | Validate args before dispatch; return the validation error as tool-result text so the model self-corrects |
| Loop stalls, model never responds again | A tool call was emitted but no matching tool-result was ever appended | Audit the dispatch path in Step 3 -- every emitted call id needs exactly one appended result |
| Agent stops with a partial or incomplete answer | Stopping instruction too loose, or `max_iterations` hit on a task that genuinely needed more steps | Tighten the stopping rule first; only raise the iteration cap after confirming it isn't masking an actual infinite loop |

## Connections
- [[Snippet - A Minimal ReAct Loop]] -- the concrete ~65-line implementation of exactly this playbook, worth reading alongside it.
- [[Deep Dive - The Agent Loop]] -- the theory, termination logic, and evolution behind the loop this playbook builds step by step.
- [[Concept - Tool Use and Function Calling]] -- the wire-level mechanics (schemas, ids, `tool_choice`) each step depends on.
- [[Checklist - Agent Tool Definition Review]] -- run this against every tool schema written in Step 1, not just glance at it.
- [[Gotchas - Tool Use and Function Calling]] -- the catalog of failure modes Steps 4-5's guards exist to defend against.
- [[Concept - LLM Observability and Tracing]] -- what Step 6's logging should grow into once this agent leaves prototype status.
- [[Playbook - Reliable Structured Output]] -- the sibling procedure for getting well-formed structured output when the target is a JSON shape rather than a tool action.
- [[Reference - Agent Framework Landscape]] -- reach for this once the raw loop built here stops being enough on its own.
- [[Decision - Choosing an Agent Framework]] -- the decision this playbook is the "no, not yet" branch of.

## Sources
- Yao et al. (2022) -- "ReAct: Synergizing Reasoning and Acting in Language Models." The thought-action-observation loop this playbook operationalizes with native tool calling instead of parsed text.
- Anthropic -- "Building Effective Agents" (Dec 2024). The workflow-vs-agent framing behind this playbook's "when to run this" guidance.
