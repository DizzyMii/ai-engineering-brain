---
tags: [concept, domain/adoption-blockers, level/surface]
aliases: [shadow AI, unsanctioned AI use, bring-your-own-AI, BYOAI]
summary: "Employees routing company data through consumer AI tools outside IT governance — a contractual leak, not a model exploit."
---
# Concept - Shadow AI

> **One-paragraph hook:** Long before an enterprise finishes evaluating, buying and rolling out a sanctioned AI tool, its employees are pasting real company data into ChatGPT, Gemini and consumer Copilot in their browser tabs. The gap between sanctioned rollout speed and unsanctioned adoption speed is Shadow AI. IT can't see it, no contract covers it, and it was the fastest-growing category of enterprise data exposure in 2025–2026.

## The mechanism

Shadow AI is employees using public generative AI tools with company data, outside IT governance, logging or contractual protection. Nobody exploits the model. The problem is a mismatch between the data-handling terms of the tool the employee is actually using and the tool the company thinks it controls. Consumer-tier products (free ChatGPT, Gemini, or Copilot without an enterprise agreement) commonly retain inputs and may use them for model training and product improvement under consumer terms of service. Enterprise API tiers and zero-retention agreements contractually exclude that.

So an employee who opens the free tier in a browser tab has, with one paste, moved company data outside every DLP tool, retention policy and audit log the company built. The model is fine. The *contract* covering that data changed, and nobody signed off. That's why the fix lives in procurement and configuration, not in a smarter or more "aligned" model.

The pressure behind it is built into the situation. Consumer AI tools are free and one tab away. Sanctioned enterprise tools need procurement cycles, SSO integration and training rollouts that trail employee demand by months. People on deadline route around governance the way they did with unsanctioned SaaS in the shadow-IT era. This time what leaves the building can be verbatim source code, a customer record or a legal document, pasted into a prompt box.

## In practice

The canonical incident is Samsung, April 2023. Engineers in the semiconductor division pasted proprietary equipment source code, an internal defect-detection algorithm, and the transcript of a confidential internal meeting into ChatGPT across three separate episodes within about 20 days (E2, reported at the time by Bloomberg, Forbes and The Register, and logged in the AI Incident Database). Samsung banned public generative AI tools on corporate devices and networks by May 2023 and started building an internal alternative. Nearly every enterprise Shadow AI policy since has followed that sequence: ban first, then replace with a governed equivalent.

Prevalence depends heavily on the survey, so read it as a range. 2025–2026 surveys put the share of employees using AI tools their employer hasn't sanctioned anywhere from roughly 45% (Verizon's 2026 Data Breach Investigations Report, regular corporate-device AI users) to 66% (PagerDuty's 2026 Shadow AI Survey, professionals at large companies who used AI tools despite believing them out of policy) to "more than 80%" (UpGuard, workers self-reporting unapproved tool use, including nearly 90% of security professionals themselves). All are E2, single-survey and methodology-dependent; don't average across them. Several 2025–2026 surveys agree on the worse follow-on number: a majority of shadow AI users admit sharing sensitive material with it, most commonly customer data, employee data and internal documents (E2, BlackFog and others).

Compliance exposure stacks on top of the security exposure. PII or PHI pasted into a consumer tool by someone in a regulated industry can itself be a reportable data-processing event under GDPR or, in the US, HIPAA, whether or not the data is ever misused. [[Reference - The EU AI Act for Operators]] covers the EU-side obligations this creates for the employer as deployer.

## Failure modes

- **Ban-only policies push usage underground.** Prohibition without an approved alternative increases *hiding* (several 2025–2026 surveys find employees actively conceal shadow AI use from employers) without reducing the use. Friction drives circumvention.
- **DLP tooling built for shadow IT misses shadow AI.** File-transfer and network-egress monitoring doesn't see a paste into a browser-rendered chat box. You need prompt-aware monitoring or, more reliably, contractual/configuration control (zero-retention enterprise tiers) instead of detection after the fact.
- **Shelved sanctioned tools reopen the gap.** If the approved tool is slower, weaker or has fewer features than the free consumer version, employees drift back even after a rollout. [[Concept - Organizational Resistance and Change Management]] explains why adoption of the sanctioned tool is the metric that counts, not its existence.
- **Cost blindness.** Personal accounts used for work produce no cost telemetry the company can see. That's a governance problem before it's a security one; [[Concept - Cost Engineering for LLM Applications]] and [[Concept - Unit Economics of LLM Products]] show what visibility should look like once usage comes in-house.

## The non-obvious

The fastest, most durable way to cut shadow AI is a sanctioned tool as good as the consumer one employees already prefer. A better firewall won't do it. Every documented enterprise response (Samsung's internal tool, and the 2024–2026 wave of enterprise ChatGPT/Copilot/Gemini rollouts) treats it as a change-management problem instead of a security-control one: the leak stops when the easiest path is also the governed path. A ban with no good alternative fails as soon as the deadline pressure that caused the behavior comes back. The mirror-image failure is in [[Concept - The Pilot-to-Production Gap]], where the sanctioned tool never reaches usable production quality and employees route around it out of necessity, not preference.

## Connections
- [[Concept - Enterprise AI Security Exposure]] — shadow AI is the outward-leakage half of the enterprise AI attack surface; this note is the narrower, employee-driven case.
- [[Concept - Organizational Resistance and Change Management]] — the change-management lever (a sanctioned tool employees actually want to use) is the durable fix, not prohibition.
- [[Reference - The EU AI Act for Operators]] — pasting PII/PHI into an ungoverned tool can itself trigger deployer obligations under EU data-processing rules.
- [[Gotchas - Enterprise AI Adoption]] — shadow AI sits alongside shelfware and entitlement leakage as a top pitfall in real deployments.
- [[Concept - The Pilot-to-Production Gap]] — shadow AI often fills the vacuum left when a sanctioned rollout stalls in pilot.
- [[Lore - Failed Enterprise AI Deployments]] — governance failures of this kind compound the broader pattern of enterprise AI initiatives that quietly die.
- [[Concept - Unit Economics of LLM Products]] — shadow usage is invisible cost as well as invisible risk; there is no telemetry on personal-account spend.
- [[Reference - AI Impact by Business Function]] — shadow AI prevalence varies sharply by function (knowledge work vs. regulated ops), which this reference tracks.
- [[Concept - Prompt Injection]] — a distinct inward-facing risk class from shadow AI's outward leakage; both fall under the same governance umbrella.
- [[Concept - Cost Engineering for LLM Applications]] — what governed, metered usage looks like once shadow spend is brought on-platform.

## Sources
- AI Incident Database, Incident 768 — "ChatGPT Reportedly Implicated in Samsung Data Leak of Source Code and Meeting Notes" (contemporaneous reporting aggregation, original incidents Apr 2023).
- CIO Dive, Apr–May 2023 — reporting on Samsung's ChatGPT ban following the leak.
- Verizon — *2026 Data Breach Investigations Report* — regular corporate-device AI usage figures.
- UpGuard — *The State of Shadow AI* (2025–2026) — survey on unsanctioned AI tool use among workers and security professionals.
- PagerDuty — *2026 Shadow AI Survey* — usage-despite-policy figures at large companies.
- BlackFog — shadow AI research (2025–2026) — data-sharing behavior among shadow AI users.
