---
tags: [gotchas, domain/agents, level/advanced]
aliases: [agent ops pitfalls, running agents in production]
summary: "Production failure modes of autonomous agents, ordered by pain: injection exfiltration, loops, cost/context blowups, silent tool failures."
---
Everything in this note reads as obvious in isolation and gets missed anyway, because agents fail in ways that don't throw exceptions — they just quietly do the wrong thing, keep going, and burn budget while they do it. Ordered roughly by how much pain each one causes in practice.

## 1. Prompt injection turns tool results into commands

**Symptom:** the agent takes an action nobody asked for — sends data somewhere unexpected, follows instructions embedded in a webpage, email, or file it was only supposed to read.
**Cause:** any content a tool returns (a scraped page, a document, an MCP resource) is untrusted text the model reads with the same attention it gives your system prompt. If that content contains instructions and the agent also has write/network access and access to sensitive data, you have the "lethal trifecta" — see [[Concept - The Lethal Trifecta for Agents]] and the injection taxonomy in [[Concept - Prompt Injection]].
**Fix:** treat every tool output as untrusted input; deny by default on network egress and gate destructive/exfil-capable actions behind explicit approval (link [[Checklist - Sandboxing an Agent]]); never let an agent that reads untrusted content also have unrestricted write/network access in the same turn.
**Detection:** audit-log every tool call with full arguments; alert on egress to novel domains or on write actions immediately following ingestion of external content.

## 2. Infinite or oscillating tool-call loops

**Symptom:** the same tool call (or a small cycle of two or three calls) repeats indefinitely, burning tokens without progress.
**Cause:** the model rationalizes a failing action instead of recognizing failure — it reads an error, reasons about why it should retry, and does the same thing again with minor cosmetic variation.
**Fix:** hard `max_iterations` cap (typically 10–50 depending on task), loop detection on repeated identical or near-identical calls, and richer error observations that give the model something new to reason about instead of the same dead end.
**Detection:** trace-level tooling that flags N consecutive calls to the same tool with the same or near-identical arguments.

## 3. Context window overflow degrades quality mid-task

**Symptom:** the agent's answers get vaguer, it forgets earlier constraints, or it stops referencing information from early in the run — without ever hitting a hard token-limit error.
**Cause:** unbounded transcript growth; every turn appends messages and nothing prunes them, so the run eventually hits [[Concept - Context Rot]] and lost-in-the-middle degradation well before any API limit fires.
**Fix:** compaction of old turns, sub-agent context isolation for parallelizable subtasks, and scratchpad/filesystem offload so state persists outside the window — the toolkit in [[Concept - Context Engineering for Agents]].
**Detection:** track transcript token count per turn against a budget; regression-test long-running tasks specifically, since short-task evals never surface this.

## 4. Token cost blows up 10–15x without warning

**Symptom:** the bill for a "simple" agent feature is an order of magnitude higher than the workflow it replaced.
**Cause:** per-turn token cost compounds with turn count, and for multi-agent setups compounds again with fan-out — Anthropic measured roughly 15x the tokens of a single chat interaction for its multi-agent research system (see [[Concept - Cost Engineering for LLM Applications]]).
**Fix:** per-run token/cost budgets enforced in the harness, not just monitored after the fact; alert thresholds tied to task type, since a research agent and a lookup agent have wildly different normal-cost baselines.
**Detection:** cost dashboards keyed by agent run, not just by API key — aggregate spend hides which specific run type is the outlier.

## 5. Silent tool failures the model doesn't notice

**Symptom:** the agent confidently proceeds and produces a final answer built on a false premise — a file that was never actually written, a query that silently returned zero rows, a deploy that failed.
**Cause:** the tool call errored or no-op'd, but the error wasn't surfaced as an unambiguous signal in the returned observation, so the model reads it as a normal result and moves on.
**Fix:** make tool handlers return explicit, actionable error text on failure rather than empty or ambiguous success-shaped output; add post-condition checks where feasible (did the file actually get written? re-read it).
**Detection:** compare the agent's stated final state against ground truth in evals and spot-checks; a gap between "agent said it worked" and "it actually worked" is this failure mode by definition.

## 6. Over-eager destructive actions with no rollback

**Symptom:** data loss or an irreversible external side effect — a deleted resource, a sent email, a production change — triggered by the agent acting on an incomplete or wrong plan.
**Cause:** the agent had unmediated access to an irreversible action and no gate stopped it from taking that action autonomously.
**Fix:** gate destructive/irreversible actions behind human approval or a confirmation step; run agents in an isolated sandbox with least-privilege credentials so the blast radius of any single bad action is bounded (full checklist in [[Checklist - Sandboxing an Agent]]).
**Detection:** inventory every tool by whether it's reversible; any irreversible tool without an approval gate is a finding, not a maybe.

## 7. Long-run goal drift, latency compounding, and flaky evals

**Symptom:** on long runs, the agent gradually solves a different problem than the one it was given; wall-clock latency stacks turn after turn; the same eval task passes one run and fails the next with no code change.
**Cause:** nothing re-anchors the agent to the original goal each turn, so small deviations accumulate (link [[Concept - Long-Horizon Agency and Error Compounding]] for the underlying math); N sequential model calls have no way to overlap, so latency is additive; and non-determinism in sampling means two runs of the identical task can diverge early and land in different outcomes.
**Fix:** recite the goal/todo list explicitly each turn or on a fixed interval; parallelize independent steps where possible instead of forcing strict sequence; for evals, run each task multiple times and report a distribution or a pass^k rate rather than a single pass/fail.
**Detection:** diff the agent's stated current objective against the original task periodically; track eval variance across repeated runs of the same task, not just mean pass rate.

The single highest-leverage investment across all seven of these is trace-level observability on every tool call and every model turn — see [[Concept - LLM Observability and Tracing]] — because every fix above depends on first being able to see what actually happened.

## Connections
- [[Gotchas - Tool Use and Function Calling]] — the narrower, tool-call-level bugs that sit one layer below the production failures cataloged here.
- [[Concept - Context Engineering for Agents]] — the direct fix for context-overflow degradation (#3).
- [[Concept - Context Rot]] — the underlying quality-decay mechanism that unbounded transcript growth triggers before any hard token limit fires.
- [[Concept - The Lethal Trifecta for Agents]] — the precise structural condition (untrusted input + tool access + private data) behind injection-driven exfiltration (#1).
- [[Concept - Prompt Injection]] — the attack taxonomy for how instructions get smuggled into tool content in the first place.
- [[Concept - LLM Observability and Tracing]] — the detection backbone that every fix in this note depends on.
- [[Concept - Cost Engineering for LLM Applications]] — the budgeting discipline that catches #4 before the invoice does.
- [[Concept - Long-Horizon Agency and Error Compounding]] — the compounding-error math underlying goal drift on long runs (#7).
- [[Checklist - Sandboxing an Agent]] — the pre-flight hardening that prevents #1 and #6 from having a blast radius in the first place.

## Sources
- Anthropic (2025) — "How we built our multi-agent research system." Source of the ~15x token-cost multiplier for multi-agent fan-out.
- Cognition (2025) — public commentary on production agent failures, including write-conflict and coordination pitfalls that compound the issues here.
