---
tags: [checklist, domain/agents, level/advanced]
aliases: [agent sandboxing, agent isolation checklist]
summary: "Pre-flight hardening checklist before granting an agent real tool access — isolation, egress allowlisting, least privilege, approval gates, audit, kill switch."
---
# Checklist - Sandboxing an Agent

## Isolation

- [ ] Agent execution runs inside an isolated container or microVM (gVisor, Firecracker), never directly on a host with production access
- [ ] No host filesystem is mounted into the sandbox; any mounted paths are read-only unless a specific write is required
- [ ] The sandbox is single-use or fully reset between tasks — state from one run cannot leak into the next

## Network egress

- [ ] Outbound network access is default-deny with an explicit allowlist of domains/IPs the task actually needs
- [ ] DNS resolution is scoped to the same allowlist — an open resolver is itself an exfiltration channel
- [ ] Egress logging captures every outbound request the agent's tools make, not just the ones that "look" suspicious

## Credentials and identity

- [ ] No long-lived or ambient credentials (API keys, SSH keys, cloud identity) sit in the sandbox environment by default
- [ ] Every credential the agent uses is short-lived and scoped to exactly the tool/action that needs it, not a broad service account
- [ ] Secrets are injected per-call and never echoed back into the transcript or logs in plaintext

## Permission gating

- [ ] Every tool the agent can call has an explicit, reviewed permission level (read-only / write / destructive)
- [ ] Destructive or irreversible actions (delete, overwrite, send, pay, deploy) require a human-approval gate before execution, not just a log entry after
- [ ] Actions with exfiltration potential (send email, post externally, write to a public endpoint) are gated the same as destructive ones

## Resource limits

- [ ] CPU, memory, and wall-clock limits are enforced on the sandbox itself, independent of any application-level timeout
- [ ] A hard token/cost budget per run is enforced and the run is killed, not just alerted on, past the ceiling
- [ ] External API calls the agent triggers are rate-limited to cap blast radius on both cost and downstream systems

## Trust boundary

- [ ] Every tool output — web page, file contents, email body, [[Concept - Model Context Protocol (MCP)|MCP]] resource — is treated as untrusted input that may carry embedded instructions, never as trusted context
- [ ] Tool descriptions from third-party or unreviewed sources are diffed on every update before being re-trusted

## Audit and control

- [ ] Every tool call is audit-logged with full arguments and results, tied to a run ID, before the call executes
- [ ] A kill switch exists that can halt a running agent immediately, independent of the agent's own loop noticing anything is wrong
- [ ] Logs are retained long enough to reconstruct a full incident timeline after the fact

## Why these items

**Isolation in a microVM, not a container alone**, is on this list because a compromised or hallucinating agent that runs a destructive shell command needs a blast-radius boundary that survives kernel-level exploits, not just process isolation — gVisor and Firecracker (the microVM behind AWS Lambda, Agache et al. 2020) both interpose a minimal kernel surface specifically because container namespacing alone has a long history of escape CVEs. The same reasoning applies doubly to [[Concept - Computer Use and GUI Grounding|computer-use agents]], whose action space (arbitrary clicks and keystrokes) can trigger anything the underlying OS permits, not just what an API surface exposes.

**Network egress allowlisting** is the single highest-leverage item here because it is the one control that breaks the [[Concept - The Lethal Trifecta for Agents|exfiltration chain]] regardless of what went wrong upstream: an agent that read a poisoned document and decided to leak a secret still cannot succeed if it has nowhere to send the data.

**No ambient credentials** is on this list because the default failure mode isn't a targeted attack, it's an agent with a broad service-account key that a prompt-injected instruction repurposes for something the task never asked for — scoping credentials per-call means the blast radius of any single compromised step is one action, not the whole account.

**Reviewed permission levels per tool** assumes each tool has already passed [[Checklist - Agent Tool Definition Review|its own definition review]] — side effects and idempotency documented at definition time are what make a runtime permission gate meaningful instead of guesswork.

**Human approval on destructive/irreversible actions** is here because agents rationalize a wrong action the same way they rationalize a wrong belief: once a delete or send is queued as "the right next step," nothing in the loop stops to double-check unless a human is explicitly in the path.

**Enforced resource limits, not just monitored ones,** exist because a runaway agent doesn't announce itself before it burns the budget — the same rate-limiting discipline used to protect any external-facing system (see [[Concept - Rate Limiting and Quota Design]]) has to apply to the calls an agent triggers on your behalf.

**Treating every tool output as untrusted** is on this list because it's the one item teams skip once they trust a tool "because we wrote it" — but the content the tool *returns* (a search result, an email, a fetched page) is attacker-reachable even when the tool code itself is safe, and that content is exactly what carries the [[Concept - Prompt Injection|injection]].

**A kill switch independent of the agent's own loop** exists because a runaway or looping agent cannot be trusted to notice it should stop — the same failure mode documented in [[Gotchas - Agents in Production]] means the halt mechanism has to live outside the thing that's malfunctioning.

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
