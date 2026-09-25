---
tags: [moc, domain/adoption-blockers, level/surface]
aliases: [Adoption & Blockers MOC, Enterprise AI Adoption MOC]
summary: "Map of why enterprise GenAI pilots stall before production, and the eval, data, org, security, legal, and vendor failure modes behind it."
---
# MOC - Adoption & Blockers

What actually happens when an enterprise tries to take GenAI from pilot to production. The question here is whether the surrounding system (evals, data plumbing, humans, security, law, vendors) is ready to carry the model, more than whether the model is capable. The headline fact is a reliability cliff: MIT NANDA puts the share of enterprise GenAI initiatives with no measurable P&L impact at roughly 95%, and these notes take apart *why*, case by case and mechanism by mechanism. In 2026 the gating question for any deployment is "will this survive real data, real users, real auditors and a real regulator?", not "can the model do this?" Every empirical claim here carries an evidence tier per the Applied Wing's Evidence Law, because vendor claims and consultancy projections are the noise this domain teaches you to filter. The question it answers: given a system that works in a demo, what has to be true for it to still be working, trusted and legal a year into production?

## Start here

- **Surface:** [[Concept - The Pilot-to-Production Gap]]: the headline 95%-no-P&L-impact fact, and why the gap won't close on its own as models improve.
- **Core:** [[Playbook - Crossing the Pilot-to-Production Gap]]: the operational answer, a 7-step procedure (eval set → readiness → human-in-the-loop → guardrails → staged rollout → continuous monitoring) followed by the minority of pilots that reach production.
- **Advanced:** [[Gotchas - Enterprise AI Adoption]]: the symptom-first list of what bites real deployments, ranked by damage.
- **Frontier:** [[Concept - Agentic Deployment Risk]]: why letting a system *act*, not only talk, raises the reliability bar exponentially and reopens every blocker below at a harder level.
- **Unicorn:** [[Lore - Failed Enterprise AI Deployments]]: Watson, Zillow Offers, McDonald's drive-thru. Three named flops a decade apart that fail the same way.

## Why pilots don't reach production

- [[Concept - The Pilot-to-Production Gap]]: ~95% of enterprises report no measurable P&L impact despite an estimated $30-40B in GenAI spend (MIT NANDA, Aug 2025). Buying from a vendor reaches production ~67% of the time, versus ~33% for internal builds.
- [[Concept - The Evaluation Gap]]: most enterprises run GenAI with no labeled task-specific eval set at all. The METR RCT showed what that hides: developers measured 19% *slower* with AI while forecasting a 24% speedup.
- [[Concept - Data and Integration Readiness]]: data/integration/permissions work commonly eats 60-80%+ of real deployment effort. Watson for Oncology never got wired into MD Anderson's live Epic EHR and spent four years and ~$62M finding that out.
- [[Playbook - Crossing the Pilot-to-Production Gap]]: the 7-step crossing procedure. Survivable use case, eval set before code, entitlement verification, human-in-the-loop calibrated to error tolerance, guardrails against injection, staged shadow→canary→full rollout, and re-baselining on every model swap.
- [[Gotchas - Enterprise AI Adoption]]: seven symptom-first pitfalls ranked by damage, from cherry-picked demos to the Air Canada tribunal loss (~CAD 812) over a chatbot-invented refund policy.

## The human and organizational layer

- [[Concept - Organizational Resistance and Change Management]]: Klarna's Feb 2024 claim of ~700-FTE-equivalent AI customer service turned, by spring 2025, into rehiring humans after CEO Siemiatkowski admitted "the result was lower quality."
- [[Concept - The Verification Tax]]: net value is generation savings *minus* review cost. A stronger model can *raise* the tax, because fluent wrong output is harder to catch than obviously wrong output.
- [[Concept - Shadow AI]]: Samsung engineers pasted proprietary source code, a defect-detection algorithm and a confidential meeting transcript into ChatGPT across three episodes in ~20 days (Apr 2023). 2025-26 surveys put unsanctioned AI use anywhere from ~45% to over 80% of employees, a range too wide to trust any single number.

## Security, legal, and regulatory exposure

- [[Concept - Enterprise AI Security Exposure]]: Willison's "lethal trifecta" (private-data access + untrusted content + external communication) is the condition under which prompt injection becomes exfiltration, no exploit code required.
- [[Reference - AI Copyright Litigation Tracker]]: Bartz v. Anthropic's $1.5B settlement drew the line at data *provenance*. Training on pirated LibGen/PiLiMi copies loses even where training on lawfully acquired books wins.
- [[Lore - Hallucination Liability Incidents]]: Air Canada argued in tribunal that its chatbot was "a separate legal entity" and lost. The dealership bot that called $1 for a Chevy Tahoe "a legally binding offer" hit ~20 million views in a day.
- [[Reference - The EU AI Act for Operators]]: the Digital Omnibus pushed Annex III high-risk obligations from 2 Aug 2026 to 2 Dec 2027, but Art. 50 transparency duties (chatbot disclosure, deepfake labeling) still land on the original date. Penalties run up to €35M or 7% of global turnover.

## Durability risk: vendors and autonomy

- [[Concept - Vendor and Model Churn Risk]]: OpenAI's 2026 deprecation wave retires 25+ model IDs including `gpt-3.5-turbo` (23 Oct 2026). Builder.ai, backed by Microsoft and Qatar Investment Authority after raising $445M, filed for insolvency overnight in May 2025 once a lender seized $37M from its accounts.
- [[Concept - Agentic Deployment Risk]]: a model that's 95%-reliable per step finishes a 20-step trajectory only ~36% of the time. Autonomy exponentiates the reliability requirement.

## The graveyard

- [[Lore - Failed Enterprise AI Deployments]]: Watson for Oncology (~$62M, never treated a patient outside pilot), Zillow Offers (>$500M inventory write-down, ~2,000 laid off), and McDonald's/IBM drive-thru voice AI (killed after a 2022 survey clocked low-80s% accuracy against a 95% bar). A decade apart, an LLM boundary between them, the same failure shape.

## Adjacent domains

- [[MOC - AI in Software Engineering]]: coding agents backed by tests and version control are where this domain's blockers get tamed most clearly. Cheap verification and reversibility are what [[Concept - The Verification Tax]] and [[Concept - Agentic Deployment Risk]] say production needs.
- [[MOC - AI Across Business Functions]]: Klarna, Harvey and the AI-medical-scribe deployments catalogued there are named case studies whose successes and reversals this domain's mechanisms (evaluation gap, verification tax, change management) explain.
- [[MOC - AI Economics]]: unit economics, ROI measurement and vendor pricing volatility are the financial mirror of the churn and verification-tax risk here.
- [[MOC - Trajectory & Navigation]]: whether these blockers are transient friction that better tooling removes, or a lasting ceiling on deployable autonomy, feeds the bubble-or-boom and timeline debates housed there.
- [[Ladder - Navigating the AI Economy]]: the guided path that sequences this domain against the economics and trajectory wings for a full operator's view.
