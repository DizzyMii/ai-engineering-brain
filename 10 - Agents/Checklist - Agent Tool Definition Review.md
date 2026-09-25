---
tags: [checklist, domain/agents, level/core]
aliases: []
summary: "Pre-flight review for any tool exposed to an agent -- naming, description, parameters, returns, errors, and safety gating."
---

# Checklist - Agent Tool Definition Review

Run this on every tool schema before a model sees it. The agent [[Concept - Tool Use and Function Calling|only ever sees the name, description and parameter descriptions]], never your implementation, so for the model this document *is* the tool.

## Naming

- [ ] Name is verb-noun and unambiguous (`get_order_status`, not `orders`)
- [ ] Name doesn't overlap in meaning with a sibling tool. Two tools that could both mean "search" get confused for each other

## Description

- [ ] Says **when to use** the tool
- [ ] Also says **when NOT to use** it, especially relative to a sibling with a similar name or scope
- [ ] Includes a short example invocation
- [ ] Length matches how confusable the tool is: one line for trivial tools, more for ambiguous ones

## Parameters

- [ ] Every parameter has a description with units and format (`"date, ISO-8601 (YYYY-MM-DD)"`, not `"date"`)
- [ ] Free-string parameters become enums wherever the set of valid values is finite
- [ ] Required vs. optional is set correctly, and each optional parameter's default behavior is in its description
- [ ] The schema went through the provider's validator; eyeballing doesn't count, since some SDKs fail silently on a malformed schema

## Returns

- [ ] Return payload is concise and structured (JSON, not a prose paragraph the model has to re-parse)
- [ ] Return size is token-budgeted and measured. A tool that can return 10K tokens of JSON on a bad day crowds out the rest of the transcript (see [[Concept - Context Engineering for Agents]])
- [ ] Large or paginated results get truncated or summarized before they go back, with a documented way to fetch more

## Errors

- [ ] Errors come back as actionable text the model can read ("no order found for id X; check the id format"), never a raw stack trace or exception repr
- [ ] The error path was tested by calling the tool with a bad argument on purpose

## Safety & side effects

- [ ] Side effects (writes, sends, deletes) are stated explicitly in the description
- [ ] Idempotency is documented: can the tool be retried safely after a timeout?
- [ ] Destructive or irreversible actions sit behind an explicit confirmation step or human-in-the-loop approval (see [[Checklist - Sandboxing an Agent]])

## Cost

- [ ] The token cost of the schema itself (name, description and every parameter description, times every tool loaded into the system prompt) has been measured (see [[Concept - Cost Engineering for LLM Applications]])

## Why these items

**Vague description → wrong tool picked.** Tool selection depends entirely on the description text. An ambiguous one makes the model call the wrong tool or waver between two. It looks like a capability problem and is really a documentation problem.

**Unhelpful error text → the agent loops.** A stack trace tells a human what broke and tells the model nothing it can act on, so it retries the same broken call or gives up. [[Gotchas - Tool Use and Function Calling]] covers the resulting loop.

**Verbose returns → context blowout.** An unbudgeted tool result is the most common way a long-running agent silently burns through its context window mid-task.

**Ungated destructive ops → data loss.** This is the "agent ran `rm -rf`", "agent sent the email", "agent issued the refund" story. Cheap to prevent here, expensive to clean up afterward.

**Unmeasured schema cost → surprise bill.** Tool schemas get re-sent (or re-cached) every turn. A system with thirty verbosely described tools can spend more tokens describing itself than doing the task.

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
