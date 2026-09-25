---
tags: [reference, domain/adoption-blockers, level/core]
aliases: [EU AI Act, AI Act, Regulation (EU) 2024/1689, Digital Omnibus on AI]
summary: "Date-stamped lookup for operators: EU AI Act risk tiers, enforcement dates, deployer duties, GPAI rules, and penalties, mid-2026."
---
# Reference - The EU AI Act for Operators

*Dates stamped mid-July 2026. Digital Omnibus: adopted by Parliament 16 Jun 2026, Council 29 Jun 2026; legislatively final, awaiting OJ publication.*

## Risk-tier table

| Tier | Meaning | Obligation weight | Examples |
|---|---|---|---|
| Unacceptable | Banned outright (Art. 5) | N/A; prohibited | Social scoring, real-time remote biometric ID in public spaces (with narrow law-enforcement carve-outs), manipulative/subliminal techniques causing harm, AI-generated non-consensual intimate imagery and CSAM (added by the 2026 Digital Omnibus) |
| High-risk | Annex III systems / Annex I safety components | Heaviest: full deployer/provider duty stack | Employment screening, credit scoring, biometric categorization, critical-infrastructure safety, law-enforcement risk assessment, medical devices with AI components |
| Limited | Transparency/disclosure only | Light | Chatbots (must disclose AI interaction), emotion-recognition systems, deepfakes (must be labeled) |
| Minimal | Unregulated | None | Spam filters, AI-enabled video games, most internal productivity tooling |

## Enforcement timeline (as of mid-2026)

| Date | What took/takes effect | Status |
|---|---|---|
| 1 Aug 2024 | Regulation (EU) 2024/1689 enters into force | E3, in force |
| 2 Feb 2025 | Prohibited-practice bans (Art. 5) and AI-literacy duties apply | E3, in force |
| 2 Aug 2025 | GPAI-model obligations apply (Arts. 51-55) for models placed on the market after this date; models placed before get until 2 Aug 2027 to comply | E3, in force; AI Office's full enforcement powers (recalls, fines) do not activate until 2 Aug 2026 |
| 2 Aug 2026 | Original date for Annex III high-risk obligations; Art. 50 transparency obligations (chatbot disclosure, deepfake labeling) — **transparency obligations remain on this date**, watermarking gets a 4-month grace period to 2 Dec 2026 | E3, transparency track unaffected by the Omnibus delay |
| **2 Dec 2027** | **New** deferred date for Annex III standalone high-risk systems (was 2 Aug 2026) | E3 — Parliament adopted 16 Jun 2026, Council final green light 29 Jun 2026; legislative process complete, awaiting Official Journal publication and entry into force (expected Jul 2026) |
| **2 Aug 2028** | **New** deferred date for Annex I embedded high-risk products (was 2 Aug 2027) | Same status as above |
| 2 Aug 2027 | AI regulatory sandbox establishment deadline (deferred one year by the same Omnibus) | Same status as above |
| 2 Dec 2026 | Deadline for providers to implement transparency/watermarking solutions for AI-generated content (Art. 50) — grace period shortened from the original 6 months to 3 months in the final text | E3, same Omnibus |

**The Dec 2027 / Aug 2028 dates are settled at the legislative level, not merely proposed.** The Digital Omnibus on AI cleared both co-legislators, the European Parliament (16 Jun 2026) and the Council of the EU (29 Jun 2026), and amends the AI Act's own compliance calendar. All that's left is Official Journal publication and the standard entry-into-force lag, expected in July 2026. Confirm the exact publication date before hard-coding it into a compliance calendar. The policy outcome itself (the 2-year-plus deferral of Annex III/Annex I high-risk obligations) is no longer in question.

## Penalties (Article 99)

| Breach type | Maximum fine | Basis |
|---|---|---|
| Prohibited-practice violations (Art. 5) | EUR 35M or 7% of global annual turnover | Whichever is **higher** |
| Other high-risk / GPAI obligation breaches | EUR 15M or 3% of global annual turnover | Whichever is **higher** |
| Supplying incorrect/incomplete information to authorities | EUR 7.5M or 1% of global annual turnover | Whichever is **higher** |

SMEs, startups included, get the *lower* of the fixed amount or the percentage in each tier, the inverse of the "whichever is higher" rule for larger undertakings. It's a deliberate ceiling to keep exposure proportionate for small deployers. (E3, statutory text, Art. 99.)

## Provider vs. deployer

Most enterprises deploying AI in or into the EU are **deployers**, not providers: they use a third party's model instead of building one and placing it on the market. Putting a third-party high-risk model into a high-risk use case still carries its own substantial deployer duty stack under **Article 26**:

- Use the system per the provider's instructions for use.
- Assign human oversight to natural persons with the competence, training, and authority to understand the system's capabilities/limitations, monitor output, override or disregard it, and report malfunctions.
- Ensure input data is relevant to the system's intended purpose.
- Monitor operation for risk; suspend use and inform the provider/market surveillance authority if a serious risk or incident emerges.
- Retain system-generated logs for at least 6 months.
- Inform affected workers/employee representatives before deployment in the workplace.
- Conduct a data protection impact assessment (DPIA) where GDPR already requires one.
- Cooperate with market surveillance authorities on request.

None of this requires *building* a model. It attaches purely to *using* one in a high-risk context, which surprises enterprises that assumed "we didn't build it, so it's not our problem."

## GPAI obligations (Arts. 51-55)

| Requirement | Applies to | Detail |
|---|---|---|
| Technical documentation, training-data summary, copyright-compliance policy | All GPAI-model providers | Flows down to operators through vendor documentation, not a direct operator duty |
| Systemic-risk extra duties (model evaluation, adversarial testing, incident reporting, cybersecurity) | GPAI models presumed to carry systemic risk: trained above **10^25 FLOPs**, or so designated by the Commission | Providers must notify the Commission within 2 weeks of reasonably foreseeing they'll cross the threshold |
| Compliance deadline for models already on the market before 2 Aug 2025 | Legacy GPAI providers | 2 Aug 2027 |

For operators the exposure is indirect. GPAI duties bind the model *provider* (OpenAI, Anthropic, Google, Meta, etc.), but an operator relying on that model has to obtain and keep the provider's documentation as part of its own Art. 26 due-diligence and human-oversight obligations.

## High-risk deployer checklist (the duties that make a high-risk deployment expensive to run)

- [ ] Risk-management process documented and current
- [ ] Data-governance controls on input data (relevance, quality, provenance)
- [ ] Human oversight assigned to a named, competent, authorized person
- [ ] Accuracy, robustness, and cybersecurity requirements verified against the provider's documentation
- [ ] Event logging retained ≥6 months
- [ ] Post-market monitoring plan in place, with a path to suspend use and notify authorities on a serious incident
- [ ] Workers/employee representatives informed before deployment
- [ ] DPIA completed where GDPR requires one

## Footnotes

- **"Operator" (AI Act) != "controller" (GDPR).** The two regimes use different roles and tests. One entity can be a GDPR controller and an AI Act deployer at once, and fines under each can stack independently for the same incident.
- **Reach is extraterritorial.** The Act applies wherever the AI system's *output* is used in the EU, whatever the provider's or deployer's location. A US company serving EU users through a non-EU-hosted model is in scope.
- **The Omnibus delay is legislatively final as of late Jun 2026** (Parliament 16 Jun, Council 29 Jun); see the timeline table above. Only the Official Journal publication date is open. Confirm it before setting an internal compliance deadline, but don't plan for the original 2 Aug 2026 date coming back.
- **Enforcement lag matters in practice.** GPAI obligations applied from 2 Aug 2025, but the AI Office's full enforcement powers (information requests, recalls, fines) only activate 2 Aug 2026. Some operators treat that year-long gap as a soft grace period. That's a risk judgment, not a legal one.

## Connections
- [[Reference - AI Copyright Litigation Tracker]] — the GPAI copyright-policy duty here (Arts. 51-55) is the regulatory mirror of the copyright exposure tracked case-by-case there.
- [[Gotchas - Enterprise AI Adoption]] — entitlement leakage and hallucination-as-liability incidents are exactly the failure modes the Art. 26 human-oversight and logging duties exist to catch.
- [[Concept - Enterprise AI Security Exposure]] — the PII/PHI-in-prompts collision with GDPR that this note's compliance duties formalize into statute.
- [[Concept - The Pilot-to-Production Gap]] — regulatory overhead is a top-cited reason pilots stall before reaching a governed production deployment.
- [[Concept - Shadow AI]] — unsanctioned use of consumer AI tools with company data can itself trigger deployer-adjacent data-processing exposure even without a formal high-risk deployment.
- [[Decision - Build vs Buy vs Wrap]] — a bought/wrapped high-risk system still leaves the *deployer* duties (Art. 26) with the enterprise, not the vendor — a material input to the build-vs-buy calculus.
- [[Concept - Refusal Mechanics]] — transparency obligations for limited-risk systems (chatbot disclosure) intersect with how and when a system is designed to decline or flag its own outputs.
- [[Concept - LLM Observability and Tracing]] — the logging and monitoring infrastructure that operationalizes the Art. 26 event-logging and post-market-monitoring duties.
- [[Reference - The 2026 Navigation Cheatsheet]] — situates the AI Act's 2026 timeline within the broader mid-2026 regulatory and market landscape.

## Sources
- Regulation (EU) 2024/1689 (the AI Act) — official text, Arts. 5, 26, 51-55, 99.
- European Commission, Digital Strategy — "EU rules on general-purpose AI models start to apply" (Aug 2025) and GPAI Q&A guidance.
- Council of the European Union — press releases on the Digital Omnibus on AI political agreement (7 May 2026) and final Council green light (29 Jun 2026); European Parliament formal adoption (16 Jun 2026).
- Gibson Dunn — "EU AI Act Omnibus Agreement: Postponed High-Risk Deadlines and Other Key Changes" (2026) — deferred date detail (2 Dec 2027 / 2 Aug 2028) and sandbox deadline.
- artificialintelligenceact.eu — Article 26 and Article 99 reference pages, GPAI guidelines overview.
