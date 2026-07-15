---
tags: [moc, domain/applied-business, level/surface]
aliases: [AI by business function, Applied Business AI, Business AI MOC]
summary: "Map of where AI actually deployed across support, legal, health, education, marketing, finance, HR, and sales — and why copilot beat autopilot."
---

# MOC - AI Across Business Functions

This domain records where generative AI has actually been deployed inside real companies — customer support, legal, healthcare documentation, education, marketing, finance operations, HR, and sales — what each deployment measurably did, and at what evidence tier. It matters because the applied-AI narrative runs years ahead of the applied-AI evidence: a single Klarna press release or Harvey valuation round gets cited as proof of a trend long before anyone checks the definition behind the headline number. The organizing question this domain answers is not "which function adopted AI fastest" but **which functions let AI act without a human commit gate, and what happened when they did** — because that one variable, not task complexity or executive enthusiasm, predicts which deployments scaled durably and which ones (Klarna, 11x, Amazon's recruiting tool) had to walk back, correct, or get sued. Read this domain as an evidence-tiered ledger of that split, function by function, dated to mid-2026.

## Start here, by level

- **Surface** — [[Concept - The Front-Office Back-Office Adoption Split]]. The single organizing fact of the domain: error tolerance and review-gate placement predict deployment durability better than task complexity or function name.
- **Core** — [[Decision - Which Business Function to Automate First]]. A scoring flowchart (volume, error tolerance, reversibility, review cost, data readiness) that operationalizes the surface-level split into an actual prioritization call, with the full per-function matrix.
- **Advanced** — [[Reference - AI Impact by Business Function]]. The tiered, dated lookup table every other note's numbers feed into — open this when you need the flagship deployment and its evidence tier for any function fast.
- **Frontier** — [[Concept - Vertical AI Agents by Function]]. The 2025–2026 app-layer thesis (Harvey, Abridge, Decagon) of outcome-priced agents that own a whole workflow — and the review gate still hiding underneath the autonomy marketing.
- **Unicorn** — [[Lore - The Klarna Reversal and Support Bot Walk-Backs]]. The tribal-knowledge version of the domain's central lesson: announce capability, not headcount-equivalence, or the walk-back gets measured against the number you bragged about.

## Organizing frameworks and decision tools

- [[Concept - The Front-Office Back-Office Adoption Split]] — a medical scribe scaled cleanly and a customer-service bot got walked back at the same model maturity; the difference is a human sign-off, not "healthcare is more careful."
- [[Concept - Copilot vs Autopilot Deployment Modes]] — a "90% capable, 95% reliable" agent still fails roughly 1 in 20 unsupervised attempts: tolerable as a suggestion a human catches, unacceptable as an action a customer receives.
- [[Decision - Which Business Function to Automate First]] — the decision flow eliminates on hard blockers (EU AI Act Annex III exposure, no existing reviewer) before volume or reversibility ever get scored; MIT's 2025 "GenAI Divide" study found 95% of enterprise pilots produced no measurable P&L impact.
- [[Reference - AI Impact by Business Function]] — the cross-function ledger where Klarna's contested, unaudited "$40M" sits next to Kaiser Permanente's peer-reviewed 15,791 physician-hours saved, tier by tier.

## Customer support

- [[Concept - Support Deflection Economics]] — AI support runs $0.50–1.50 per contact against $8–35 for a human, a real 10–24x gap, but a Gartner survey of 5,728 customers found only ~14% of self-service issues are actually, fully resolved.
- [[Breakdown - Klarna's AI Customer Service Bet]] — the "work of ~700 agents" figure was a workload equivalence, not 700 people fired; most of the parallel headcount drop came from a hiring freeze the press conflated with the bot.
- [[Lore - The Klarna Reversal and Support Bot Walk-Backs]] — Siemiatkowski's own words, May 2025: Klarna "went too far," optimized cost over quality, and started rehiring humans for the nuanced cases the bot couldn't judge.
- [[Lore - What Vendors Don't Say About Deflection Rates]] — a customer who rage-quits the bot and emails support anyway is a deflection success, a containment failure, and a resolution failure simultaneously — the deck only ever shows the first one.

## Professional and licensed services

- [[Breakdown - Harvey and AI in Legal Work]] — valuation ran $3B→$11B in thirteen months; the Stanford RegLab hallucination study everyone cites against "legal AI" actually tested Lexis+ and Westlaw, not Harvey.
- [[Breakdown - AI Medical Scribes]] — Kaiser Permanente's 63-week, 2.5M-encounter evaluation is the best-evidenced clinical AI deployment on record, and ambient notes still hallucinate at a measured 1.5–7%.
- [[Breakdown - Khanmigo and AI Tutoring]] — 700,000+ provisioned users, but Khan Academy's own reporting puts active use around 15%; the bottleneck was never tutoring quality, it was getting a student to open the app.

## Content and language

- [[Concept - AI in Marketing and Content]] — Jasper raised at a $1.5B valuation in October 2022 and cut it roughly 20% within a year once ChatGPT gave every marketer the same generation capability for free.
- [[Concept - Machine Translation and the Localization Industry]] — Duolingo cut ~10% of its translator/writer contractors in January 2024 citing generative AI — a confirmed, dated labor-market event, not a projection.

## Back-office operations

- [[Concept - AI in Finance Operations]] — JPMorgan's LLM Suite reached 200,000+ employees within eight months, and not one reported use case lets the model send a client communication or move money without a human sign-off.
- [[Breakdown - AI in Recruiting and HR Screening]] — Amazon's resume tool didn't malfunction, it faithfully learned that a decade of hires skewed male and penalized the token "women's"; Mobley v. Workday now tests whether the vendor, not just the employer, is liable for the outcome.

## Sales and the autonomy frontier

- [[Concept - AI SDRs and Sales Automation]] — 11x listed ZoomInfo as a customer from November onward; ZoomInfo says it ran a one-month trial that performed "significantly worse" than its own human SDRs.
- [[Concept - Vertical AI Agents by Function]] — outcome pricing quietly moves reliability risk from buyer to vendor, which is exactly why "assumed resolution" and elastic outcome definitions show up right behind it.

## Cross-cutting pattern

- [[Pattern - Human-in-the-Loop Review Workflow]] — four unrelated functions (medical scribes, Harvey, MTPE translators, JPMorgan's LLM Suite) converged independently on the identical draft-then-sign shape — the strongest evidence this is a real pattern and not a vendor slogan.

## Adjacent domains

- [[MOC - AI in Software Engineering]] — the capability-reliability gap and the copilot-vs-autonomous-agent tradeoff that this domain applies to support, legal, and sales first showed up as a developer-tooling problem.
- [[MOC - AI Economics]] — the unit economics, wrapper-commoditization, and outcome-pricing mechanics (Jasper's collapse, Harvey's valuation, Intercom's $0.99/resolution) that this domain's case studies are all instances of.
- [[MOC - Adoption & Blockers]] — the pilot-to-production gap, the evaluation gap, and the EU AI Act obligations that explain why so many of this domain's flagship wins are still copilot-shaped and why HR screening sits at the bottom of every priority list.
- [[MOC - Trajectory & Navigation]] — the portfolio-level discipline (picking profitable use cases, the current-state cheatsheet) for deciding what to automate next once this domain's per-function evidence has been read.
- [[Ladder - Navigating the AI Economy]] — the guided path that sequences this domain's notes against the economics and adoption-blocker domains for someone learning the applied landscape end to end.
