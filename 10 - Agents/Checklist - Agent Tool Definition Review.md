---
tags: [checklist, domain/agents, level/core]
aliases: []
summary: "Pre-flight review for any tool exposed to an agent -- naming, description, parameters, returns, errors, and safety gating."
---

# Checklist - Agent Tool Definition Review

Run this against every tool schema before it goes in front of a model. The agent [[Concept - Tool Use and Function Calling|only ever sees the name, description, and parameter descriptions]] -- never your implementation -- so this document *is* the tool as far as the model is concerned.

## Naming

- [ ] Name is verb-noun and unambiguous (`get_order_status`, not `orders`)
- [ ] Name doesn't semantically overlap with a sibling tool -- two tools that both plausibly mean "search" get confused for each other

## Description

- [ ] Description states **when to use** the tool
- [ ] Description also states **when NOT to use** it, especially against a similarly-named or similarly-scoped sibling
- [ ] Description includes a short example invocation
- [ ] Description length is proportional to how confusable the tool is -- trivial tools need one line, ambiguous ones need more

## Parameters

- [ ] Every parameter has a description, including units and format (`"date, ISO-8601 (YYYY-MM-DD)"`, not just `"date"`)
- [ ] Free-string parameters are replaced with enums wherever the valid value set is finite
- [ ] Required-vs-optional is set correctly, and every optional parameter's default behavior is documented in its description
- [ ] The schema was round-tripped through the provider's validator, not just eyeballed -- a malformed schema fails silently in some SDKs

## Returns

- [ ] Return payload is concise and structured (JSON, not a prose paragraph the model has to re-parse)
- [ ] Return size is token-budgeted -- measure it; a tool that can return 10K tokens of JSON on a bad day crowds out the rest of the transcript (see [[Concept - Context Engineering for Agents]])
- [ ] Large or paginated results are truncated or summarized before being handed back, with a documented way to fetch more

## Errors

- [ ] Errors return actionable, model-readable text ("no order found for id X; check the id format"), never a raw stack trace or exception repr
- [ ] The error path was tested by deliberately calling the tool with a bad argument, not just imagined

## Safety & side effects

- [ ] Side effects (writes, sends, deletes) are declared explicitly in the description, not left implicit
- [ ] Idempotency is documented -- can this tool be safely retried after a timeout?
- [ ] Destructive or irreversible actions are gated behind an explicit confirmation step or a human-in-the-loop approval (see [[Checklist - Sandboxing an Agent]])

## Cost

- [ ] The token cost of the schema itself -- name, description, and every parameter description, multiplied across every tool loaded into the system prompt -- has been measured, not assumed (see [[Concept - Cost Engineering for LLM Applications]])

## Why these items

**Vague description → wrong tool picked.** Tool selection is entirely a function of the description text; an ambiguous one causes the model to call the wrong tool or hedge between two, which looks like a "capability" problem but is actually a documentation problem.

**Unhelpful error text → the agent loops.** A stack trace tells a human what broke; it tells the model nothing actionable, so it retries the same broken call or gives up -- see [[Gotchas - Tool Use and Function Calling]] for the loop failure mode this causes.

**Verbose returns → context blowout.** An unbudgeted tool result is the single most common way a long-running agent silently burns its context window mid-task.

**Ungated destructive ops → data loss.** The incident class behind this item is exactly the "agent ran `rm -rf`," "agent sent the email," or "agent issued the refund" story -- cheap to prevent here, expensive to clean up after.

**Unmeasured schema cost → surprise bill.** Tool schemas are re-sent (or re-cached) on every turn; a system with thirty verbosely-described tools can spend more tokens describing itself than doing the task.

## Connections
- [[Concept - Tool Use and Function Calling]] -- the wire mechanics (schemas, `tool_choice`, parallel calls) this checklist is reviewing the surface of.
- [[Concept - Model Context Protocol (MCP)]] -- the same review applies to an MCP tool's docstring, which becomes its model-facing contract verbatim.
- [[Gotchas - Tool Use and Function Calling]] -- the failure catalog each checklist section is a preventive measure against.
- [[Checklist - Sandboxing an Agent]] -- the runtime-level hardening that picks up where this schema-level review leaves off.
- [[Playbook - Building a Tool-Use Agent from Scratch]] -- run this checklist at Step 1 of that playbook, before the loop is ever built.
- [[Playbook - Reliable Structured Output]] -- shares the enum-over-freestring and schema-validation discipline this checklist enforces for tools specifically.
- [[Concept - Cost Engineering for LLM Applications]] -- where the schema-token-cost item connects to system-wide budget tracking.
- [[Concept - Context Engineering for Agents]] -- the transcript-management discipline the return-size items exist to protect.
- [[Concept - What Is an LLM Agent]] -- the tool set is one of the four load-bearing components of an agent's anatomy that this checklist scrutinizes.
