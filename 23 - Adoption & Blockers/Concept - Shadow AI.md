---
tags: [concept, domain/adoption-blockers, level/surface]
aliases: [shadow AI, unsanctioned AI use, bring-your-own-AI, BYOAI]
summary: "Employees routing company data through consumer AI tools outside IT governance — a contractual leak, not a model exploit."
---
# Concept - Shadow AI

> **One-paragraph hook:** Long before an enterprise finishes evaluating, procuring, and rolling out a sanctioned AI tool, its employees are already pasting real company data into ChatGPT, Gemini, and consumer Copilot in their browser tabs. That gap between sanctioned rollout speed and unsanctioned adoption speed is Shadow AI — invisible to IT, uncovered by contract, and the single fastest-growing category of enterprise data exposure in 2025–2026.

## The mechanism

Shadow AI is unsanctioned employee use of public generative AI tools with company data, outside IT governance, logging, or contractual protection. The mechanism is not a security exploit against the model — it's a mismatch between the data-handling terms of the tool an employee is actually using and the tool the company thinks it controls. Consumer-tier products (free ChatGPT, Gemini, or Copilot without an enterprise agreement) commonly retain user inputs and may use them for model training and product improvement under their consumer terms of service; enterprise API tiers and zero-retention agreements contractually exclude that. An employee who opens the free tier in a browser tab has, in one paste, moved company data outside every DLP tool, retention policy, and audit log the company built — not because the model is insecure, but because the *contract* governing that data just changed and nobody signed off on it. This is why the fix for shadow AI lives in procurement and configuration, not in a smarter or more "aligned" model.

The adoption pressure that drives this is structural: consumer AI tools are one browser tab away and free; sanctioned enterprise tools require procurement cycles, SSO integration, and training rollouts that lag employee demand by months. Employees under deadline pressure route around governance the same way they did with unsanctioned SaaS in the shadow-IT era — except the artifact leaving the building this time can be verbatim source code, a customer record, or a legal document, pasted into a prompt box.

## In practice

The canonical incident is Samsung, April 2023: engineers in Samsung's semiconductor division pasted proprietary equipment source code, an internal defect-detection algorithm, and the transcript of a confidential internal meeting into ChatGPT across three separate episodes within about 20 days (E2, contemporaneously reported by Bloomberg, Forbes, and The Register, and logged in the AI Incident Database). Samsung banned public generative AI tools on corporate devices and networks by May 2023 and began building an internal alternative — the pattern nearly every enterprise Shadow AI policy has followed since: ban first, then replace with a governed equivalent.

Prevalence is genuinely survey-dependent and should be read as a range, not a fact: 2025–2026 surveys put the share of employees using AI tools not sanctioned by their employer anywhere from roughly 45% (Verizon's 2026 Data Breach Investigations Report, regular corporate-device AI users) to "more than 80%" (UpGuard, workers self-reporting unapproved tool use, including nearly 90% of security professionals themselves) to 66% (PagerDuty's 2026 Shadow AI Survey, professionals at large companies who used AI tools despite believing them out of policy) (all E2, single-survey, methodology-dependent — do not average across sources). Multiple 2025–2026 surveys converge on the more damaging follow-on statistic: a majority of employees who use shadow AI admit to sharing sensitive material with it — customer data, employee data, and internal documents most commonly (E2, BlackFog and others).

The compliance exposure compounds the security one: PII or PHI pasted into a consumer tool by a regulated-industry employee can itself constitute a reportable data-processing event under GDPR or, in the US, HIPAA, independent of whether the data is ever misused — see [[Reference - The EU AI Act for Operators]] for the EU-side obligations this creates for the employer as deployer.

## Failure modes

- **Ban-only policy pushes usage underground rather than eliminating it.** Prohibition without an approved alternative increases the *hiding* of usage (several 2025–2026 surveys find employees actively conceal shadow AI use from employers) without reducing the usage itself — friction drives circumvention, it doesn't stop it.
- **DLP tooling built for shadow IT misses shadow AI.** File-transfer and network-egress monitoring doesn't catch a paste into a browser-rendered chat box; the leak vector requires prompt-aware monitoring or, more reliably, contractual/configuration control (zero-retention enterprise tiers) rather than detection after the fact.
- **Shelved sanctioned tools reopen the gap.** If the enterprise-approved tool is slower, less capable, or has fewer features than the free consumer version, employees drift back to shadow use even after a rollout — see [[Concept - Organizational Resistance and Change Management]] for why adoption of the sanctioned tool, not its mere existence, is the real metric.
- **Cost blindness compounds the risk.** Employees using personal accounts for work tasks generate no cost telemetry the company can see, which is a governance problem before it's even a security one — see [[Concept - Cost Engineering for LLM Applications]] and [[Concept - Unit Economics of LLM Products]] for what visibility should look like once usage is brought in-house.

## The non-obvious

The fastest, most durable way to cut shadow AI is not a better firewall — it's giving employees a sanctioned tool that is as good as the consumer one they already prefer. Every documented enterprise response (Samsung's internal tool, and the broader 2024–2026 wave of enterprise ChatGPT/Copilot/Gemini rollouts) treats this as a change-management problem, not a security-control problem: the leak stops when the path of least resistance is also the governed path. A ban with no good alternative is a control that fails the moment the deadline pressure that caused the behavior in the first place reappears — see [[Concept - The Pilot-to-Production Gap]] for the mirror-image failure mode, where the sanctioned tool itself never reaches usable production quality and employees route around it by necessity, not preference.

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
