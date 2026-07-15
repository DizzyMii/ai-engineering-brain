---
tags: [concept, domain/adoption-blockers, level/advanced]
aliases: [enterprise AI security, AI attack surface, LLM security exposure, AI data leakage]
summary: "The two-sided AI attack surface: outward data leakage and inward adversarial input, and why autonomy grows it fast."
---
# Concept - Enterprise AI Security Exposure

> **One-paragraph hook:** Deploying an LLM into an enterprise does not add a feature to the existing security model — it opens a new attack surface with two faces the old perimeter was never built to guard. One faces *outward*: employees and applications pushing company data into models whose retention terms nobody read. The other faces *inward*: the model ingesting attacker-controlled text through documents, emails, and web pages, and then acting on it with the credentials you gave it. The second face is the genuinely new one, because a system that both reads untrusted content and takes actions is a confused-deputy machine by construction. Guardrails and disclaimers narrow the exposure; they do not close it, and you remain accountable for everything your deployed system says and does.

## The mechanism

Enterprise AI exposure splits cleanly into two classes, and conflating them is the first mistake operators make.

**Outward leakage** is the exfiltration of company data *into* a model context that the company does not control. Its mechanism is contractual, not behavioral: consumer-tier products (free/Plus ChatGPT, Gemini, consumer Copilot) may retain inputs and use them for training under their terms of service, while enterprise API tiers and zero-retention agreements contractually exclude that. The leak happens the instant data crosses from a governed tool into an ungoverned one — one paste moves it outside every DLP control, retention policy, and audit log the company built. This is the [[Concept - Shadow AI]] vector, and its remedy lives in procurement and configuration, not in a smarter model.

**Inward adversarial input** is the new and harder class. An LLM cannot reliably distinguish its operator's instructions from instructions embedded in the *data* it is asked to process, because both arrive as tokens in the same context window with no privileged channel separating them. This is [[Concept - Prompt Injection]]: an attacker who controls any content the model ingests — a webpage it browses, an email it summarizes, a document it retrieves, a tool description it reads — can plant instructions the model may follow. Unlike a [[Concept - Jailbreak Taxonomy|jailbreak]], which is the *user* subverting the model against the operator, injection is a *third party* subverting the model against both. Classic input sanitization does not help, because the malicious input is natural-language text that is indistinguishable in form from the legitimate content the system exists to read.

The two classes multiply when the system gains autonomy. Simon Willison's **lethal trifecta** (E2, practitioner framing, Willison, Jun 2025) names the precise condition under which injection becomes exfiltration: an agent with **(1) access to private data, (2) exposure to untrusted content, and (3) the ability to communicate externally**. Hold any two and the system is defensible; grant all three in one session and an attacker who controls the untrusted content can read your private data and ship it out, with no exploit code — just words. Most useful enterprise agents are built to have all three: they read your documents (private data), browse or process inbound mail (untrusted content), and send messages or call APIs (external communication). Autonomy is therefore not a capability you bolt security onto afterward — it is the thing that assembles the trifecta.

## In practice

**Outward, the archetype is Samsung, April 2023** (E2, Bloomberg/Forbes/The Register, AI Incident Database): engineers in the semiconductor division pasted proprietary equipment source code, an internal defect-detection algorithm, and a confidential meeting transcript into ChatGPT across three episodes within ~20 days; Samsung banned public GenAI on corporate devices by May 2023. No model was exploited. The terms of service governing that data simply changed, unsigned.

**Inward, the practical defense is least-privilege tool scoping.** Every tool an agent can call, every data source it can read, and every channel it can write to is a widening of the trifecta. The [[Concept - Model Context Protocol (MCP)]] ecosystem makes this concrete and worse: MCP servers expose tool *descriptions* that the model reads as trusted instructions, so a poisoned or malicious server can inject at the tool-definition layer before any user turn — the supply chain is inside the prompt. The governing pattern from [[Gotchas - Agents in Production]] is taint tracking: treat any exposure to untrusted content as a taint event, and once tainted, block actions with exfiltration potential (outbound HTTP, email/chat sends, even rendering a clickable link, since a URL with query params is a covert channel).

**The model and plugin supply chain is an emerging third front.** Poisoned open weights, backdoored models on public hubs, and prompt-injected tool descriptions are all live vectors; provenance verification and sandboxing of tool execution matter as much as prompt-level defenses.

**Observability collides with data minimization.** The instinct to "log everything" for [[Concept - LLM Observability and Tracing|tracing]] turns your prompt and completion logs into a regulated data store: PII/PHI that transited a prompt now sits in your logging pipeline, in scope for GDPR and HIPAA. See [[Reference - The EU AI Act for Operators]] for the deployer-side obligations this creates.

## Failure modes

- **Trifecta assembled by accident.** A team adds "let the agent read email" and "let the agent send Slack" in separate sprints, each reviewed in isolation, and ships the full lethal trifecta with no single review that saw all three. Detection: enumerate, per deployed agent, its private-data reach × untrusted-content channels × egress channels — the product, not any single factor, is the risk.
- **Injection treated as a content-filter problem.** Teams bolt an output classifier on and declare injection handled. But the classifier sees only the final text, not the tool calls the injection already triggered; exfiltration via a crafted URL or an "innocent" API call sails past it. Detection: red-team with an injection corpus that targets *actions*, not just toxic text.
- **Zero-retention assumed, not verified.** An enterprise agreement is signed but a subprocessor, a logging integration, or a debug flag re-introduces retention. Detection: contractual + configuration audit, plus a data-flow map that follows a prompt all the way to every store it lands in.
- **Disclaimers mistaken for liability transfer.** "The AI may be wrong" in the footer does not make the output not-your-representation — see [[Lore - Hallucination Liability Incidents]]. Detection: legal review of what a customer-facing agent is empowered to assert or promise.

## The non-obvious

The security bar for an agent that *acts* is categorically higher than for a chatbot that *talks*, and the jump is discontinuous, not gradual. A chat error is a wrong sentence a human reads and discards; an action error is a wrong *deed* — money moved, email sent, record deleted — with no human in the loop to catch it. This is why [[Concept - Agentic Deployment Risk|bounded autonomy]] wins in production: small trusted action sets, human approval on irreversible steps, and cheap verification. Adding tools to an agent feels like adding capability, but each tool widens the trifecta and raises the security bar faster than it raises the value — the counterintuitive result is that *more agentic* frequently means *less deployable*. Guardrails and disclaimers reduce exposure at the margin; they never eliminate accountability, because you own what your system does with the authority you granted it. The [[Playbook - Crossing the Pilot-to-Production Gap|production crossing]] treats security scoping as a gating step precisely because it cannot be retrofitted onto an agent that already has the keys.

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
