---
tags: [gotchas, domain/agents, level/advanced]
aliases: [function calling pitfalls, tool calling bugs]
summary: "Pitfalls of the tool-calling interface: malformed args, selection degradation, id mismatches, ordering bugs, oversized results, injection."
---
These are the bugs you hit at the tool-call layer specifically, as distinct from the broader run-level failures in [[Gotchas - Agents in Production]]. Most of them trace back to one root cause: the model only ever sees your schema and description text, never your implementation, so any ambiguity there becomes a runtime bug.

## 1. Malformed or wrongly-typed arguments

**Symptom:** a handler throws on a call that looked plausible — a string `"5"` where an int was expected, a missing required field, a date in the wrong format.
**Cause:** weak or ambiguous parameter schema/description; the model was never told the exact type, format, or constraint, so it guessed from the parameter name.
**Fix:** strict JSON Schema validation with explicit types, formats, and enums where possible; the underlying decoder can also be grammar-constrained to only emit schema-valid JSON in the first place (see [[Concept - Constrained Decoding]]).
**Detection:** log every rejected call with the validation error; a nonzero rejection rate on a specific tool almost always traces to an under-specified schema, not a "bad" model.

## 2. Tool-selection degradation as the tool count grows

**Symptom:** the model picks a plausible-but-wrong tool, or ignores an available tool entirely, on tasks it handled fine with a smaller tool set.
**Cause:** selection accuracy degrades as the number of available tools grows — historically past roughly 20–40 tools in a single context, the model's ability to discriminate between similar-sounding options drops noticeably.
**Fix:** namespace tools by domain, retrieve only the relevant subset for the current task instead of exposing everything, or delegate to sub-agents each holding a smaller tool set.
**Detection:** track tool-selection accuracy against total tools exposed in that call; a downward trend as you add tools is the signal, not any single failure.

## 3. Ambiguous or overlapping tool descriptions

**Symptom:** the model consistently calls tool A when tool B was correct, or alternates between the two unpredictably for near-identical inputs.
**Cause:** two tools whose descriptions read as interchangeable to the model, even if they're obviously different to a human who knows the implementation.
**Fix:** write descriptions with explicit "use when / do NOT use when" language that disambiguates against every sibling tool, not just describes the tool in isolation — this is the core discipline in [[Checklist - Agent Tool Definition Review]].
**Detection:** confusion-matrix the tool calls against the intended tool for a labeled eval set; overlapping descriptions show up as a consistent off-diagonal pattern, not random noise.

## 4. `tool_call_id` / `tool_use_id` mismatches

**Symptom:** the API call errors outright, or the model produces a confused or repeated response referencing a tool result that doesn't match what it asked for.
**Cause:** the harness returned a tool result keyed to the wrong call id — easy to introduce when dispatching multiple calls concurrently and racing the response assembly.
**Fix:** key every dispatched call and its result by id explicitly in the harness code, and assert the full set of emitted call ids has a matching result before sending the next turn.
**Detection:** this fails loudly (API-level 400) far more often than silently, so it usually surfaces in integration testing — but log id-matching failures distinctly from other API errors so they don't get lost in generic retry logic.

## 5. Parallel tool calls with hidden data dependencies executed out of order

**Symptom:** a call that depended on the output of another call in the same batch runs against stale or missing data, producing a wrong result with no error.
**Cause:** modern models emit multiple tool calls in one turn for what look like independent actions, but the model doesn't reliably reason about implicit ordering dependencies between them, and the harness fans them out without checking.
**Fix:** either declare dependencies explicitly and sequence dependent calls across turns, or force strictly sequential calling (`tool_choice` set to a single named tool) when a task has known ordering constraints.
**Detection:** audit parallel-call batches for calls that reference the same resource; if two calls in one batch touch the same entity, ordering risk is present regardless of whether it's manifested yet.

## 6. Oversized tool results eating the context window

**Symptom:** the transcript grows sharply after a single tool call, and subsequent turns show quality degradation consistent with [[Concept - Context Rot]] — even though only one tool was involved.
**Cause:** a tool returns its full, unbounded output (a whole file, a full API response, a complete search result set) instead of a token-budgeted summary.
**Fix:** truncate and paginate large outputs at the handler level before they ever reach the model; return summaries with an explicit mechanism to fetch more on demand.
**Detection:** log the token count of every tool result; flag any single result above a fixed threshold (e.g., a few thousand tokens) for review.

## 7. Missing tool result stalls the model, or the model narrates instead of calling

**Symptom:** either the agent hangs waiting on a turn that never resolves, or the model writes out "I will now call the search tool" in plain text instead of actually emitting a tool call.
**Cause:** for the stall — a call was emitted but the harness never dispatched or returned a result for it. For the narration case — the model defaulted to `tool_choice: auto` and chose to talk instead of act, often under a system prompt that doesn't clearly mandate tool use.
**Fix:** assert every emitted call gets a result before proceeding; force tool use with `tool_choice: required` or a named tool when the task structurally requires an action, not a description of one.
**Detection:** a turn with no corresponding tool result in the trace is an unambiguous bug signature; narration-instead-of-calling shows up as assistant text containing tool names or verbs with zero actual `tool_use`/`tool_calls` blocks that turn.

## 8. Injection via attacker-controlled tool descriptions or results

**Symptom:** the agent's behavior changes after reading a tool's own description or a result from a third-party tool/MCP server, in a way that doesn't trace back to the user's instructions.
**Cause:** tool descriptions and results are both just text the model reads with full attention; a malicious or compromised MCP server can embed instructions in either — see [[Concept - The Lethal Trifecta for Agents]] for when this becomes exfiltration-capable.
**Fix:** treat third-party tool descriptions as untrusted at install time (review before granting access, pin versions, watch for silent updates/"rug pulls"), and treat every tool result as untrusted at runtime regardless of source.
**Detection:** diff tool descriptions on every update from a third-party server; alert on tool results containing instruction-like language ("ignore previous instructions," embedded system-prompt-style text).

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
