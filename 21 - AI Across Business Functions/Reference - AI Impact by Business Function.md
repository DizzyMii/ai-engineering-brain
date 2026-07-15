---
tags: [reference, domain/applied-business, level/advanced]
aliases: [AI by function matrix, AI deployment by business function, function impact table]
summary: "Per-function lookup: flagship AI deployment, best measured outcome with evidence tier and date, and dominant deployment mode. Mid-2026."
---

# Reference - AI Impact by Business Function

**Every figure below is fast-moving; each is date-stamped and tier-marked (E3 verified / E2 single credible source / E1 estimate / E0 speculation). Vendor and consultancy numbers never appear as fact.** Snapshot: 2026-07.

## Function matrix

| Function | Flagship deployment | Best measured outcome | Tier / date | Mode |
|---|---|---|---|---|
| Customer support | Klarna assistant (OpenAI) | 2.3M chats/mo, ~work of 700 agents, ~$40M/yr claimed profit | E2, Klarna 2024 — later rebalanced¹ | Autopilot-for-routine |
| Customer support | Intercom Fin | 40M+ resolutions; 67% resolution (vendor); $0.99/resolution² | E2, Intercom 2025 — see note² | Autopilot, outcome-priced |
| Customer support | (cost baseline) | Human ticket ~$8-12 (B2B SaaS ~$25-35); AI contact ~$0.50-1.50 | E2, SaaS Capital 2024 | — |
| Healthcare docs | Kaiser Permanente ambient scribes | 15,791 physician-hours saved / 63 weeks; 2.5M+ uses yr 1 | E2, Tierney et al. NEJM Catalyst 2024-25 | Copilot (draft-then-sign) |
| Healthcare docs | Microsoft DAX / Dragon Copilot | ~3M ambient conversations/mo across ~600 orgs | E2, Microsoft 2025-03 | Copilot |
| Legal | Harvey | 700k+ tasks/day; A&O ~3,500 lawyers; valuation ~$3B→~$11B³ | E2, 2025-02→2026-03 | Copilot, mandatory review |
| Translation / localization | DeepL | ~$2B valuation, ~$185M revenue 2024; claimed 1.3× Google accuracy⁴ | E2, 2024 | MT post-editing (MTPE) |
| Translation / localization | Duolingo | Cut ~10% of translation/content contractors, Jan 2024 | E2/E3, TechCrunch/WaPo 2024 | Content generation + review |
| Finance ops | JPMorgan LLM Suite | 200,000+ employees; 450+ use cases; target 1,000 by 2026 | E2, JPMorgan/CNBC 2025 | Internal copilot |
| Marketing / content | Jasper | $1.5B valuation (Oct 2022) → ~20% internal cut, ARR forecast down post-ChatGPT | E2, 2023⁵ | Copilot (commoditized) |
| Sales | 11x (Alice) / Artisan (Ava) | AI-SDR ARR contested; ~70-80% churn alleged | E2, TechCrunch investigation 2025⁶ | Autopilot (credibility crisis) |
| HR / recruiting | Amazon (scrapped); Workday (litigated) | Amazon scrapped biased tool 2018; Mobley v. Workday collective certified 2025 | E3 / E2-E3⁷ | High-risk — avoid/gate |
| Education | Khan Academy Khanmigo (GPT-4) | 700k+ users; small 2025 study (~69 undergrads) found **no statistically significant** learning-outcome difference vs Google-search/paper-only conditions | E2, single small study, 2025⁸ | Socratic copilot |

## Cross-cutting anchor

| Claim | Value | Tier / date |
|---|---|---|
| Gen-AI annual value potential | $2.6T-$4.4T across 63 use cases | E1, McKinsey 2023-06 — estimate, not realized value |
| Value concentration | ~75% in customer ops, marketing/sales, software eng, R&D | E1, McKinsey 2023-06 |

## Footnotes

1. **Klarna** — launch numbers are Klarna/OpenAI's own (E2); the $40M is an unaudited internal estimate. In May 2025 Klarna publicly walked back to an AI-routine + human-complex split (E2/E3). See [[Breakdown - Klarna's AI Customer Service Bet]]. The "700 agents" is a *workload* equivalence, not 700 people fired.
2. **Fin resolution** — 67% is Intercom's trailing-30-day vendor figure (as of late 2025); independent/production reports and Intercom's own case studies put real-world resolution nearer 45–53% (E1/E2, third-party 2026). "$0.99/resolution" is genuine outcome pricing, but billable "outcomes" include *resolution, procedure handoff, or disqualification*, which inflates the count vs verified problem-solving — the "assumed resolution" critique in [[Lore - What Vendors Don't Say About Deflection Rates]].
3. **Harvey valuation** — announced rounds: ~$3B (Feb 2025) → ~$5B (Jun 2025) → ~$8B (Dec 2025) → ~$11B (Mar 2026). A conviction marker, not realized value. ARR ~$300M mid-2026 (E1/E2, Sacra). See [[Breakdown - Harvey and AI in Legal Work]].
4. **DeepL 1.3× accuracy** — a DeepL-run blind-test claim (vendor benchmark, single-source E2); an ALC 2024 survey found 82% of language-service firms use DeepL vs 46% Google (E2, industry survey). Frontier LLMs are eroding the specialist MT edge.
5. **Jasper** — the commoditization marker: a GPT-3-wrapper copywriting tool at a $1.5B valuation that cut its internal valuation ~20% and revised ARR down after ChatGPT shipped a near-free substitute. Model-is-the-product wrappers have no moat.
6. **AI SDRs** — a March 2025 TechCrunch investigation alleged 11x listed non-customers as customers, counted trial contracts as ARR, and ran ~70-80% churn (E2, single investigation). Autonomous cold outbound is the worst-fit-for-autopilot case. See [[Concept - Vertical AI Agents by Function]].
7. **HR** — Amazon's scrapped tool is E3 (Reuters 2018); Mobley v. Workday advanced a novel *vendor-as-agent* discrimination theory, collective certified May 2025 (E2/E3). EU AI Act classes employment AI as high-risk (high-risk obligations deferred from 2 Aug 2026 to 2 Dec 2027 by the EU Digital Omnibus, agreed June 2026; the high-risk classification itself is unchanged). See [[Breakdown - AI in Recruiting and HR Screening]].
8. **Khanmigo** — Khan Academy's own Nov 2024 efficacy report concerns the *core Khan Academy platform* (~20% larger test-score gains at 30+ min/week), not Khanmigo specifically; the post states Khanmigo-specific efficacy studies were "underway." The null result — significant gains across conditions but no statistically significant difference between groups — traces to a separate, small 2025 study (Journal of Teaching and Learning, ~69 undergraduates, physics) comparing Khanmigo, a Google-search condition, and paper-only (E2, single small study, 2025). No independently verified Khanmigo-specific RCT has surfaced as of mid-2026. See [[Breakdown - Khanmigo and AI Tutoring]].

## Connections
- [[Concept - Support Deflection Economics]] — the cost-per-contact and deflection-vs-resolution mechanics behind the support rows.
- [[Breakdown - Klarna's AI Customer Service Bet]] — the narrative and evidence tiers behind the customer-support flagship row.
- [[Breakdown - AI Medical Scribes]] — the narrative behind the healthcare-docs row and the strongest measured copilot outcome.
- [[Concept - The Front-Office Back-Office Adoption Split]] — the frame explaining why copilot modes dominate the outcome column.
- [[Concept - Vertical AI Agents by Function]] — the outcome-priced-autonomy trend feeding the support, legal, and sales rows.
- [[Reference - AI Market Sizing Claims]] — where the McKinsey $2.6-4.4T anchor and other market-sizing dollar claims are tiered (domain 22).
- [[Reference - Developer Productivity Studies]] — the software-engineering function's measured-impact table, the sibling to this one (domain 20).
- [[Reference - The 2026 Navigation Cheatsheet]] — the top-level operator's quick-reference this matrix feeds into (domain 24).

## Sources
- Klarna (2024) / Bloomberg (2025) — support-row launch numbers and reversal.
- Tierney et al., NEJM Catalyst (2024-25) — Kaiser ambient-scribe hours-saved study.
- CNBC / Sacra (2026) — Harvey valuation and ARR.
- TechCrunch (2024-25) — DeepL raise, Duolingo contractor cuts, 11x AI-SDR investigation.
- JPMorgan / CNBC (2025) — LLM Suite scale.
- McKinsey, "The economic potential of generative AI" (2023-06) — the $2.6-4.4T / 75% cross-cutting anchor.
- Reuters (2018); Mobley v. Workday filings (2024-25) — HR row.
- Khan Academy efficacy report (2024-11) — core-platform efficacy findings, not Khanmigo-specific. Journal of Teaching and Learning (2025) — the small single-study Khanmigo null result.
