---
tags: [gotchas, domain/agents, level/advanced]
aliases: [agent ops pitfalls, running agents in production]
summary: "Production failure modes of autonomous agents, ordered by pain: injection exfiltration, loops, cost/context blowups, silent tool failures."
---
Each item here looks obvious on its own and gets missed anyway, because agents don't fail with exceptions. They do the wrong thing, keep going, and burn budget while they're at it. Ordered roughly by how much pain each causes in practice.

## 1. Prompt injection turns tool results into commands

**Symptom:** the agent takes an action nobody asked for: sends data somewhere unexpected, or follows instructions embedded in a webpage, email or file it was only supposed to read.
**Cause:** anything a tool returns (a scraped page, a document, an MCP resource) is untrusted text, and the model reads it with the same attention it gives your system prompt. If that content carries instructions and the agent also has write/network access plus access to sensitive data, you have the "lethal trifecta." See [[Concept - The Lethal Trifecta for Agents]] and the injection taxonomy in [[Concept - Prompt Injection]].
**Fix:** treat every tool output as untrusted input. Deny network egress by default and put destructive or exfil-capable actions behind explicit approval ([[Checklist - Sandboxing an Agent]]). An agent that reads untrusted content should never have unrestricted write/network access in the same turn.
**Detection:** audit-log every tool call with full arguments. Alert on egress to new domains, and on write actions right after the agent ingests external content.

## 2. Infinite or oscillating tool-call loops

**Symptom:** the same tool call, or a small cycle of two or three, repeats indefinitely and burns tokens with no progress.
**Cause:** the model talks itself past a failing action. It reads an error, reasons about why it should retry, and does the same thing again with minor cosmetic changes.
**Fix:** a hard `max_iterations` cap (typically 10–50 depending on task), loop detection on identical or near-identical calls, and richer error observations that give the model something new to reason about.
**Detection:** trace-level tooling that flags N consecutive calls to the same tool with the same or near-identical arguments.

## 3. Context window overflow degrades quality mid-task

**Symptom:** answers get vaguer, earlier constraints are forgotten, information from early in the run stops being referenced. No hard token-limit error ever fires.
**Cause:** unbounded transcript growth. Every turn appends messages and nothing prunes them, so the run hits [[Concept - Context Rot]] and lost-in-the-middle degradation well before any API limit.
**Fix:** compact old turns, isolate parallelizable subtasks in sub-agent contexts, and offload state to a scratchpad or filesystem outside the window. The toolkit is in [[Concept - Context Engineering for Agents]].
**Detection:** track transcript token count per turn against a budget. Regression-test long-running tasks specifically; short-task evals never surface this.

## 4. Token cost blows up 10–15x without warning

**Symptom:** the bill for a "simple" agent feature is an order of magnitude higher than for the workflow it replaced.
**Cause:** per-turn token cost compounds with turn count, and multi-agent fan-out compounds it again. Anthropic measured roughly 15x the tokens of a single chat interaction for its multi-agent research system (see [[Concept - Cost Engineering for LLM Applications]]).
**Fix:** per-run token/cost budgets enforced in the harness, not only monitored afterward. Tie alert thresholds to task type, since a research agent and a lookup agent have wildly different normal-cost baselines.
**Detection:** cost dashboards keyed by agent run. Aggregate spend by API key hides which run type is the outlier.

## 5. Silent tool failures the model doesn't notice

**Symptom:** the agent confidently produces a final answer built on a false premise: a file that was never written, a query that silently returned zero rows, a deploy that failed.
**Cause:** the tool call errored or did nothing, but the observation didn't say so unambiguously. The model read it as a normal result and moved on.
**Fix:** make tool handlers return explicit, actionable error text on failure, never empty or success-shaped output. Add post-condition checks where you can (did the file get written? re-read it).
**Detection:** compare the agent's stated final state with ground truth in evals and spot-checks. Any gap between "agent said it worked" and "it worked" is this failure mode by definition.

## 6. Over-eager destructive actions with no rollback

**Symptom:** data loss or an irreversible external side effect (a deleted resource, a sent email, a production change) because the agent acted on an incomplete or wrong plan.
**Cause:** the agent had unmediated access to an irreversible action, and no gate stopped it from taking that action on its own.
**Fix:** put destructive and irreversible actions behind human approval or a confirmation step. Run agents in an isolated sandbox with least-privilege credentials so any single bad action has a bounded blast radius (full checklist in [[Checklist - Sandboxing an Agent]]).
**Detection:** inventory every tool by whether it's reversible. An irreversible tool without an approval gate is a finding, not a maybe.

## 7. Long-run goal drift, latency compounding, and flaky evals

**Symptom:** on long runs the agent drifts into solving a different problem than the one it was given, wall-clock latency stacks up turn after turn, and the same eval task passes one run and fails the next with no code change.
**Cause:** three separate things. Nothing re-anchors the agent to the original goal each turn, so small deviations accumulate ([[Concept - Long-Horizon Agency and Error Compounding]] has the math). N sequential model calls can't overlap, so latency adds up. And sampling non-determinism lets two runs of the same task diverge early and end in different places.
**Fix:** recite the goal/todo list explicitly each turn or on a fixed interval. Parallelize independent steps where you can. For evals, run each task several times and report a distribution or a pass^k rate, not a single pass/fail.
**Detection:** periodically diff the agent's stated current objective against the original task. Track eval variance across repeated runs of the same task alongside mean pass rate.

If you invest in one thing across all seven, make it trace-level observability on every tool call and every model turn ([[Concept - LLM Observability and Tracing]]). Every fix above depends on first seeing what happened.

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
