---
tags: [checklist, domain/agents, level/advanced]
aliases: [agent sandboxing, agent isolation checklist]
summary: "Pre-flight hardening checklist before granting an agent real tool access — isolation, egress allowlisting, least privilege, approval gates, audit, kill switch."
---
# Checklist - Sandboxing an Agent

## Isolation

- [ ] Agent execution runs in an isolated container or microVM (gVisor, Firecracker), never directly on a host with production access
- [ ] No host filesystem is mounted into the sandbox; any mounted path is read-only unless a specific write needs it
- [ ] The sandbox is single-use or fully reset between tasks, so state from one run can't leak into the next

## Network egress

- [ ] Outbound network is default-deny, with an explicit allowlist of the domains/IPs the task needs
- [ ] DNS resolution is limited to the same allowlist; an open resolver is an exfiltration channel in its own right
- [ ] Egress logging captures every outbound request the agent's tools make, including the ones that don't "look" suspicious

## Credentials and identity

- [ ] No long-lived or ambient credentials (API keys, SSH keys, cloud identity) in the sandbox environment by default
- [ ] Every credential the agent uses is short-lived and scoped to the one tool/action that needs it, never a broad service account
- [ ] Secrets are injected per call and never echoed into the transcript or logs in plaintext

## Permission gating

- [ ] Every tool the agent can call has an explicit, reviewed permission level (read-only / write / destructive)
- [ ] Destructive or irreversible actions (delete, overwrite, send, pay, deploy) need human approval before they run; a log entry afterward isn't enough
- [ ] Actions that could exfiltrate (send email, post externally, write to a public endpoint) are gated like destructive ones

## Resource limits

- [ ] CPU, memory and wall-clock limits are enforced on the sandbox itself, separately from any application-level timeout
- [ ] Each run has a hard token/cost budget, and the run is killed past the ceiling, not merely alerted on
- [ ] External API calls the agent triggers are rate-limited to cap the blast radius on cost and on downstream systems

## Trust boundary

- [ ] Every tool output (web page, file contents, email body, [[Concept - Model Context Protocol (MCP)|MCP]] resource) is treated as untrusted input that may carry embedded instructions, never as trusted context
- [ ] Tool descriptions from third-party or unreviewed sources are diffed on every update before being trusted again

## Audit and control

- [ ] Every tool call is audit-logged with full arguments and results, tied to a run ID, before it executes
- [ ] A kill switch can halt a running agent immediately, whether or not the agent's own loop has noticed anything wrong
- [ ] Logs are kept long enough to reconstruct a full incident timeline afterward

## Why these items

**A microVM, not a container alone.** A compromised or hallucinating agent that runs a destructive shell command needs a blast-radius boundary that survives kernel-level exploits, and process isolation doesn't provide one. gVisor and Firecracker (the microVM behind AWS Lambda, Agache et al. 2020) both put a minimal kernel surface in the way because container namespacing has a long history of escape CVEs. This goes double for [[Concept - Computer Use and GUI Grounding|computer-use agents]]. Their action space (arbitrary clicks and keystrokes) can trigger anything the OS permits, beyond what an API surface exposes.

**Network egress allowlisting** is the highest-leverage item on the list. It's the one control that breaks the [[Concept - The Lethal Trifecta for Agents|exfiltration chain]] whatever went wrong upstream. An agent that read a poisoned document and decided to leak a secret still fails if it has nowhere to send the data.

**No ambient credentials.** The default failure isn't a targeted attack. It's an agent holding a broad service-account key that a prompt-injected instruction redirects to something the task never asked for. Scope credentials per call, and a single compromised step can do one action instead of anything the whole account allows.

**Reviewed permission levels per tool** assume each tool already passed [[Checklist - Agent Tool Definition Review|its own definition review]]. Side effects and idempotency documented at definition time are what give a runtime permission gate something to check besides guesses.

**Human approval on destructive or irreversible actions.** Agents rationalize a wrong action the same way they rationalize a wrong belief. Once a delete or send is queued as "the right next step", nothing in the loop double-checks it unless a human is explicitly in the path.

**Enforced resource limits, beyond monitoring.** A runaway agent doesn't announce itself before it burns the budget. The rate-limiting discipline that protects any external-facing system (see [[Concept - Rate Limiting and Quota Design]]) has to cover the calls an agent triggers on your behalf.

**Every tool output is untrusted.** Teams skip this once they trust a tool "because we wrote it". The tool code can be safe while the content it *returns* (a search result, an email, a fetched page) is attacker-reachable, and that content is what carries the [[Concept - Prompt Injection|injection]].

**A kill switch outside the agent's own loop.** A runaway or looping agent can't be trusted to notice it should stop. Given the failure modes in [[Gotchas - Agents in Production]], the halt mechanism has to live outside the thing that's malfunctioning.

## Connections

- [[Concept - The Lethal Trifecta for Agents]] — the exfiltration pattern (private data + untrusted content + network egress) that egress allowlisting specifically breaks.
- [[Concept - Prompt Injection]] — the attack class that makes the trust-boundary items on this checklist necessary, not optional.
- [[Gotchas - Agents in Production]] — the aggregated production failure modes (loops, silent tool failures, cost blowups) this checklist exists to prevent before they happen.
- [[Checklist - Agent Tool Definition Review]] — the companion checklist for the tool's interface itself; this one hardens the runtime around it.
- [[Concept - Computer Use and GUI Grounding]] — computer-use agents need every item here plus screen-level isolation, since their action space includes arbitrary clicks.
- [[Concept - Model Context Protocol (MCP)]] — MCP servers, especially third-party ones, are a common way ungated tool access and untrusted output both enter a sandboxed agent at once.
- [[Concept - Rate Limiting and Quota Design]] — the general mechanism behind the resource-limit and rate-limit items above.

## Sources

- Agache, A. et al. (2020) — "Firecracker: Lightweight Virtualization for Serverless Applications" (NSDI). The microVM isolation model behind AWS Lambda and a common agent-sandboxing substrate.
- Google gVisor project — application-kernel sandboxing as a container-escape mitigation, the alternative isolation substrate to microVMs.
