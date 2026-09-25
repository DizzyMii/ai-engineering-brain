---
tags: [gotchas, domain/agents, level/advanced]
aliases: [function calling pitfalls, tool calling bugs]
summary: "Pitfalls of the tool-calling interface: malformed args, selection degradation, id mismatches, ordering bugs, oversized results, injection."
---
These are the bugs you hit at the tool-call layer, as distinct from the run-level failures in [[Gotchas - Agents in Production]]. Most share a root cause: the model sees your schema and description text and never your implementation, so any ambiguity there becomes a runtime bug.

## 1. Malformed or wrongly-typed arguments

**Symptom:** a handler throws on a call that looked plausible: a string `"5"` where an int was expected, a missing required field, a date in the wrong format.
**Cause:** a weak or ambiguous parameter schema/description. Nobody told the model the exact type, format or constraint, so it guessed from the parameter name.
**Fix:** strict JSON Schema validation with explicit types, formats, and enums where possible. The decoder can also be grammar-constrained to emit only schema-valid JSON in the first place (see [[Concept - Constrained Decoding]]).
**Detection:** log every rejected call with its validation error. A nonzero rejection rate on one tool almost always traces to an under-specified schema, not a "bad" model.

## 2. Tool-selection degradation as the tool count grows

**Symptom:** the model picks a plausible but wrong tool, or ignores an available one, on tasks it handled fine with a smaller tool set.
**Cause:** selection accuracy drops as the number of available tools grows. Historically, past roughly 20–40 tools in a single context the model gets noticeably worse at telling similar-sounding options apart.
**Fix:** namespace tools by domain, retrieve only the subset relevant to the current task, or delegate to sub-agents that each hold a smaller set.
**Detection:** track tool-selection accuracy against the number of tools exposed in each call. The signal is a downward trend as you add tools; a single failure tells you little.

## 3. Ambiguous or overlapping tool descriptions

**Symptom:** the model keeps calling tool A when tool B was right, or alternates between them unpredictably on near-identical inputs.
**Cause:** two descriptions that read as interchangeable to the model, even if the tools are obviously different to a human who knows the implementation.
**Fix:** write "use when / do NOT use when" language that separates each tool from every sibling. Describing a tool in isolation isn't enough. This is the core of [[Checklist - Agent Tool Definition Review]].
**Detection:** build a confusion matrix of actual vs. intended tool on a labeled eval set. Overlapping descriptions show up as a consistent off-diagonal pattern, not random noise.

## 4. `tool_call_id` / `tool_use_id` mismatches

**Symptom:** the API call errors outright, or the model gives a confused or repeated response about a tool result that doesn't match what it asked for.
**Cause:** the harness keyed a tool result to the wrong call id. Easy to do when dispatching several calls concurrently and racing the response assembly.
**Fix:** key every dispatched call and its result by id explicitly in the harness, and assert that every emitted call id has a matching result before sending the next turn.
**Detection:** this fails loudly (API-level 400) far more often than silently, so it usually shows up in integration testing. Still, log id-matching failures separately from other API errors so generic retry logic doesn't bury them.

## 5. Parallel tool calls with hidden data dependencies executed out of order

**Symptom:** a call that depended on another call's output in the same batch runs against stale or missing data and returns a wrong result with no error.
**Cause:** modern models emit several tool calls in one turn for actions that look independent. The model doesn't reliably reason about implicit ordering between them, and the harness fans them out without checking.
**Fix:** declare dependencies explicitly and sequence dependent calls across turns, or force strictly sequential calling (`tool_choice` set to a single named tool) when the task has known ordering constraints.
**Detection:** audit parallel batches for calls that touch the same resource. Two calls on the same entity in one batch means ordering risk, whether or not it has bitten yet.

## 6. Oversized tool results eating the context window

**Symptom:** the transcript jumps after a single tool call, and later turns degrade in the way [[Concept - Context Rot]] describes, though only one tool was involved.
**Cause:** the tool returns its full, unbounded output (a whole file, a full API response, a complete search result set) instead of a token-budgeted summary.
**Fix:** truncate and paginate large outputs in the handler before they reach the model. Return summaries with an explicit way to fetch more on demand.
**Detection:** log the token count of every tool result and flag any single result above a fixed threshold (e.g., a few thousand tokens) for review.

## 7. Missing tool result stalls the model, or the model narrates instead of calling

**Symptom:** either the agent hangs on a turn that never resolves, or the model writes "I will now call the search tool" in plain text without emitting a tool call.
**Cause:** in the stall case, a call was emitted but the harness never dispatched it or never returned a result. In the narration case, the model was on `tool_choice: auto` and chose to talk instead of act, often under a system prompt that doesn't clearly require tool use.
**Fix:** assert every emitted call gets a result before proceeding. When the task needs an action and a description won't do, force tool use with `tool_choice: required` or a named tool.
**Detection:** a turn with no matching tool result in the trace is an unambiguous bug signature. Narration shows up as assistant text mentioning tool names or verbs with zero `tool_use`/`tool_calls` blocks that turn.

## 8. Injection via attacker-controlled tool descriptions or results

**Symptom:** the agent's behavior changes after it reads a tool's description or a result from a third-party tool/MCP server, in a way the user's instructions don't explain.
**Cause:** tool descriptions and results are both text the model reads with full attention, and a malicious or compromised MCP server can plant instructions in either. [[Concept - The Lethal Trifecta for Agents]] covers when this becomes exfiltration-capable.
**Fix:** treat third-party tool descriptions as untrusted at install time (review before granting access, pin versions, watch for silent updates or "rug pulls"). Treat every tool result as untrusted at runtime, whatever its source.
**Detection:** diff tool descriptions on every update from a third-party server. Alert on tool results with instruction-like language ("ignore previous instructions," embedded system-prompt-style text).

## Connections
- [[Concept - Tool Use and Function Calling]] — the mechanism this note catalogs the failure modes of; read that first for the request/response wire format.
- [[Checklist - Agent Tool Definition Review]] — the pre-flight review that prevents most of #1, #2, and #3 before a tool ever ships.
- [[Gotchas - Agents in Production]] — the broader run-level failures (loops, cost, context overflow) these tool-level bugs feed into.
- [[Concept - Context Rot]] — the quality-decay mechanism an oversized tool result (#6) triggers once it lands in the transcript.
- [[Concept - Constrained Decoding]] — the decoding-level fix underlying schema-valid tool calls (#1).
- [[Concept - The Lethal Trifecta for Agents]] — the structural condition that turns tool-content injection (#8) into actual data exfiltration.
- [[Concept - Model Context Protocol (MCP)]] — the standardized tool-serving protocol where third-party description/rug-pull risk (#8) is most acute.
- [[Playbook - Reliable Structured Output]] — the general discipline of getting models to emit valid structured data, which tool-call argument formatting is one instance of.

## Sources
- Anthropic and OpenAI tool-use API documentation (2025-26) — the `tool_choice` semantics (auto/required/named) and parallel-call behavior referenced throughout.
