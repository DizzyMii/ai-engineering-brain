---
tags: [concept, domain/adoption-blockers, level/advanced]
aliases: [enterprise AI security, AI attack surface, LLM security exposure, AI data leakage]
summary: "The two-sided AI attack surface: outward data leakage and inward adversarial input, and why autonomy grows it fast."
---
# Concept - Enterprise AI Security Exposure

> **One-paragraph hook:** Putting an LLM into an enterprise opens a new attack surface with two faces the old perimeter was never built to guard. One faces *outward*: employees and applications pushing company data into models whose retention terms nobody read. The other faces *inward*: the model ingesting attacker-controlled text through documents, emails and web pages, then acting on it with the credentials you gave it. The inward face is the new one. A system that both reads untrusted content and takes actions is a confused-deputy machine by construction. Guardrails and disclaimers narrow the exposure without closing it, and you stay accountable for everything your deployed system says and does.

## The mechanism

Enterprise AI exposure splits into two classes. Operators' first mistake is lumping them together.

**Outward leakage** is company data leaving *into* a model context the company doesn't control. The mechanism is contractual, not behavioral. Consumer-tier products (free/Plus ChatGPT, Gemini, consumer Copilot) may retain inputs and train on them under their terms of service; enterprise API tiers and zero-retention agreements contractually exclude that. The leak happens the moment data crosses from a governed tool to an ungoverned one. One paste takes it outside every DLP control, retention policy and audit log the company built. That's the [[Concept - Shadow AI]] vector, and the fix is procurement and configuration, not a smarter model.

**Inward adversarial input** is the new, harder class. An LLM can't reliably tell its operator's instructions from instructions embedded in the *data* it's processing, because both arrive as tokens in the same context window with no privileged channel between them. That's [[Concept - Prompt Injection]]. An attacker who controls any content the model ingests (a webpage it browses, an email it summarizes, a document it retrieves, a tool description it reads) can plant instructions the model may follow. A [[Concept - Jailbreak Taxonomy|jailbreak]] is the *user* turning the model against the operator; injection is a *third party* turning it against both. Classic input sanitization doesn't help, since the malicious input is natural-language text shaped exactly like the legitimate content the system exists to read.

Autonomy multiplies both. Simon Willison's **lethal trifecta** (E2, practitioner framing, Willison, Jun 2025) names the condition under which injection becomes exfiltration: an agent with **(1) access to private data, (2) exposure to untrusted content, and (3) the ability to communicate externally**. Any two are defensible. Grant all three in one session and whoever controls the untrusted content can read your private data and ship it out, with no exploit code, just words. Most useful enterprise agents are built with all three: they read your documents (private data), browse or process inbound mail (untrusted content), and send messages or call APIs (external communication). You can't bolt security onto autonomy afterward, because autonomy is what assembles the trifecta.

## In practice

**Outward, the archetype is Samsung, April 2023** (E2, Bloomberg/Forbes/The Register, AI Incident Database). Engineers in the semiconductor division pasted proprietary equipment source code, an internal defect-detection algorithm, and a confidential meeting transcript into ChatGPT across three episodes within ~20 days. Samsung banned public GenAI on corporate devices by May 2023. No model was exploited. The terms of service covering that data just changed, and nobody signed anything.

**Inward, the practical defense is least-privilege tool scoping.** Every tool an agent can call, every data source it reads and every channel it writes to widens the trifecta. The [[Concept - Model Context Protocol (MCP)]] ecosystem makes this concrete, and worse. MCP servers expose tool *descriptions* the model reads as trusted instructions, so a poisoned or malicious server can inject at the tool-definition layer before any user turn. The supply chain is inside the prompt. The pattern from [[Gotchas - Agents in Production]] is taint tracking: count any exposure to untrusted content as a taint event, and once tainted, block actions that could exfiltrate (outbound HTTP, email/chat sends, even rendering a clickable link, since a URL with query params is a covert channel).

**The model and plugin supply chain is an emerging third front.** Poisoned open weights, backdoored models on public hubs and prompt-injected tool descriptions are all live vectors. Provenance checks and sandboxed tool execution matter as much as prompt-level defenses.

**Observability collides with data minimization.** "Log everything" for [[Concept - LLM Observability and Tracing|tracing]] turns your prompt and completion logs into a regulated data store. PII/PHI that passed through a prompt now sits in your logging pipeline, in scope for GDPR and HIPAA. [[Reference - The EU AI Act for Operators]] covers the deployer-side obligations this creates.

## Failure modes

- **Trifecta assembled by accident.** One sprint adds "let the agent read email," another adds "let the agent send Slack." Each is reviewed alone, and the full lethal trifecta ships without any single review seeing all three. Detection: for each deployed agent, list private-data reach × untrusted-content channels × egress channels. The risk is the product, not any one factor.
- **Injection treated as a content-filter problem.** Teams add an output classifier and call injection handled. The classifier sees only the final text, not the tool calls the injection already fired, so exfiltration through a crafted URL or an "innocent" API call gets straight past it. Detection: red-team with an injection corpus that targets *actions*, not only toxic text.
- **Zero-retention assumed, not verified.** The enterprise agreement is signed, but a subprocessor, a logging integration or a debug flag brings retention back. Detection: a contractual + configuration audit, plus a data-flow map that follows a prompt to every store it lands in.
- **Disclaimers mistaken for liability transfer.** "The AI may be wrong" in the footer doesn't stop the output being your representation; see [[Lore - Hallucination Liability Incidents]]. Detection: legal review of what a customer-facing agent is allowed to assert or promise.

## The non-obvious

The security bar for an agent that *acts* is categorically higher than for a chatbot that *talks*, and the jump is a step, not a slope. A chat error is a wrong sentence a human reads and discards. An action error is a wrong *deed* (money moved, email sent, record deleted) with no human in the loop to catch it. So [[Concept - Agentic Deployment Risk|bounded autonomy]] wins in production: small trusted action sets, human approval on irreversible steps, cheap verification.

Adding tools feels like adding capability. Each tool also widens the trifecta and raises the security bar faster than it raises value, so *more agentic* frequently means *less deployable*. Guardrails and disclaimers reduce exposure at the margin but never remove accountability, because you own what your system does with the authority you gave it. The [[Playbook - Crossing the Pilot-to-Production Gap|production crossing]] makes security scoping a gating step since it can't be retrofitted onto an agent that already has the keys.

## Connections
- [[Concept - Shadow AI]] — the outward-leakage half of this surface; the employee-driven special case of contractual data exposure.
- [[Concept - Prompt Injection]] — the core mechanism of the inward attack class; this note is its operator-risk framing.
- [[Concept - Jailbreak Taxonomy]] — the sibling threat (user-vs-operator) that injection (third-party-vs-both) is often confused with.
- [[Concept - Model Context Protocol (MCP)]] — tool descriptions become a trusted-instruction injection channel; autonomy tooling grows the surface.
- [[Concept - Agentic Deployment Risk]] — the frontier note on why action-taking multiplies this exposure; the up-link from here.
- [[Gotchas - Agents in Production]] — the taint-tracking and least-privilege patterns that operationally contain the trifecta.
- [[Lore - Hallucination Liability Incidents]] — why disclaimers don't transfer liability; the accountability half of the exposure.
- [[Reference - The EU AI Act for Operators]] — logs-as-regulated-data and the deployer obligations PII-in-prompts triggers.
- [[Gotchas - Enterprise AI Adoption]] — entitlement leakage and injection-via-ingested-data as top real-world pitfalls.
- [[Playbook - Crossing the Pilot-to-Production Gap]] — security scoping as a gating step that can't be retrofitted.
- [[Concept - The Pilot-to-Production Gap]] — security exposure is a leading reason pilots that "worked" fail production sign-off.
- [[Deep Dive - Agentic Coding in Production]] — a domain where scoped, verifiable autonomy actually clears the higher security bar.
- [[Decision - Build vs Buy vs Wrap]] — buy-vs-build shifts who owns the retention contract and the supply-chain provenance.

## Sources
- Simon Willison — "The lethal trifecta for AI agents: private data, untrusted content, and external communication" (simonwillison.net, 16 Jun 2025) — names the exact condition under which injection becomes exfiltration.
- AI Incident Database, Incident 768 — Samsung ChatGPT source-code/meeting-notes leak (original incidents Apr 2023; Bloomberg/Forbes/The Register reporting).
- OWASP — *Top 10 for LLM Applications* — prompt injection (LLM01) and related classes as the enumerated enterprise risk taxonomy.
- Moffatt v. Air Canada, BC Civil Resolution Tribunal (2024) — precedent that a company owns its deployed system's outputs; see the Hallucination Liability note.
