---
tags: [moc, domain/applied-business, level/surface]
aliases: [AI by business function, Applied Business AI, Business AI MOC]
summary: "Map of where AI actually deployed across support, legal, health, education, marketing, finance, HR, and sales — and why copilot beat autopilot."
---

# MOC - AI Across Business Functions

This domain records where generative AI has been deployed inside real companies (customer support, legal, healthcare documentation, education, marketing, finance operations, HR, sales), what each deployment measurably did, and at what evidence tier. The applied-AI narrative runs years ahead of the evidence. One Klarna press release or Harvey valuation round gets cited as proof of a trend long before anyone checks the definition behind the headline number. So the question here isn't which function adopted AI fastest. It's **which functions let AI act without a human commit gate, and what happened when they did**. That one variable predicts which deployments scaled durably and which (Klarna, 11x, Amazon's recruiting tool) had to walk back, correct, or get sued, better than task complexity or executive enthusiasm. Read the domain as an evidence-tiered ledger of that split, function by function, dated to mid-2026.

## Start here, by level

- **Surface**: [[Concept - The Front-Office Back-Office Adoption Split]]. The domain's organizing fact: error tolerance and where the review gate sits predict deployment durability better than task complexity or function name.
- **Core**: [[Decision - Which Business Function to Automate First]]. A scoring flowchart (volume, error tolerance, reversibility, review cost, data readiness) that turns the split into a prioritization call, with the full per-function matrix.
- **Advanced**: [[Reference - AI Impact by Business Function]]. The tiered, dated lookup table the other notes' numbers feed into. Open it when you need a function's flagship deployment and evidence tier fast.
- **Frontier**: [[Concept - Vertical AI Agents by Function]]. The 2025–2026 app-layer thesis (Harvey, Abridge, Decagon) of outcome-priced agents that own a whole workflow, with the review gate still hiding under the autonomy marketing.
- **Unicorn**: [[Lore - The Klarna Reversal and Support Bot Walk-Backs]]. The tribal-knowledge version of the central lesson: announce capability, not headcount-equivalence, or the walk-back gets measured against the number you bragged about.

## Organizing frameworks and decision tools

- [[Concept - The Front-Office Back-Office Adoption Split]]: a medical scribe scaled cleanly and a customer-service bot got walked back at the same model maturity. The difference is a human sign-off. "Healthcare is more careful" doesn't explain it.
- [[Concept - Copilot vs Autopilot Deployment Modes]]: a "90% capable, 95% reliable" agent still fails roughly 1 in 20 unsupervised attempts. Tolerable as a suggestion a human catches, unacceptable as an action a customer receives.
- [[Decision - Which Business Function to Automate First]]: the flow eliminates on hard blockers (EU AI Act Annex III exposure, no existing reviewer) before volume or reversibility get scored. MIT's 2025 "GenAI Divide" study found 95% of enterprise pilots produced no measurable P&L impact.
- [[Reference - AI Impact by Business Function]]: the cross-function ledger where Klarna's contested, unaudited "$40M" sits next to Kaiser Permanente's peer-reviewed 15,791 physician-hours saved, tier by tier.

## Customer support

- [[Concept - Support Deflection Economics]]: AI support costs $0.50–1.50 per contact against $8–35 for a human, a real 10–24x gap. But a Gartner survey of 5,728 customers found only ~14% of self-service issues get fully resolved.
- [[Breakdown - Klarna's AI Customer Service Bet]]: "work of ~700 agents" was a workload equivalence, not 700 people fired. Most of the parallel headcount drop came from a hiring freeze the press lumped in with the bot.
- [[Lore - The Klarna Reversal and Support Bot Walk-Backs]]: Siemiatkowski, May 2025: Klarna "went too far," put cost ahead of quality, and started rehiring humans for the nuanced cases the bot couldn't judge.
- [[Lore - What Vendors Don't Say About Deflection Rates]]: a customer who rage-quits the bot and emails support anyway is a deflection success, a containment failure and a resolution failure at once. The deck only shows the first.

## Professional and licensed services

- [[Breakdown - Harvey and AI in Legal Work]]: valuation ran $3B→$11B in thirteen months. The Stanford RegLab hallucination study everyone cites against "legal AI" tested Lexis+ and Westlaw, not Harvey.
- [[Breakdown - AI Medical Scribes]]: Kaiser Permanente's 63-week, 2.5M-encounter evaluation is the best-evidenced clinical AI deployment on record, and ambient notes still hallucinate at a measured 1.5–7%.
- [[Breakdown - Khanmigo and AI Tutoring]]: 700,000+ provisioned users, but Khan Academy's own reporting puts active use around 15%. Tutoring quality was never the bottleneck. Getting students to open the app was.

## Content and language

- [[Concept - AI in Marketing and Content]]: Jasper raised at a $1.5B valuation in October 2022 and cut it roughly 20% within a year, once ChatGPT gave every marketer the same generation capability for free.
- [[Concept - Machine Translation and the Localization Industry]]: Duolingo cut ~10% of its translator and writer contractors in January 2024, citing generative AI. It's a confirmed, dated labor-market event, not a projection.

## Back-office operations

- [[Concept - AI in Finance Operations]]: JPMorgan's LLM Suite reached 200,000+ employees within eight months, and no reported use case lets the model send a client communication or move money without human sign-off.
- [[Breakdown - AI in Recruiting and HR Screening]]: Amazon's resume tool didn't malfunction. It learned that a decade of hires skewed male and penalized the token "women's." Mobley v. Workday now tests whether the vendor, and not only the employer, is liable.

## Sales and the autonomy frontier

- [[Concept - AI SDRs and Sales Automation]]: 11x listed ZoomInfo as a customer from November onward. ZoomInfo says it ran a one-month trial that performed "significantly worse" than its own human SDRs.
- [[Concept - Vertical AI Agents by Function]]: outcome pricing moves reliability risk from buyer to vendor, which is why "assumed resolution" and elastic outcome definitions show up right behind it.

## Cross-cutting pattern

- [[Pattern - Human-in-the-Loop Review Workflow]]: four unrelated functions (medical scribes, Harvey, MTPE translators, JPMorgan's LLM Suite) arrived independently at the same draft-then-sign shape. That's the strongest evidence it's a real pattern and not a vendor slogan.

## Adjacent domains

- [[MOC - AI in Software Engineering]]: the capability-reliability gap and the copilot-vs-autonomous-agent tradeoff that this domain applies to support, legal and sales showed up first as a developer-tooling problem.
- [[MOC - AI Economics]]: the unit economics, wrapper commoditization and outcome-pricing mechanics (Jasper's collapse, Harvey's valuation, Intercom's $0.99/resolution) behind this domain's case studies.
- [[MOC - Adoption & Blockers]]: the pilot-to-production gap, the evaluation gap and the EU AI Act obligations. They explain why so many flagship wins here are still copilot-shaped, and why HR screening sits at the bottom of every priority list.
- [[MOC - Trajectory & Navigation]]: the portfolio-level discipline (picking profitable use cases, the current-state cheatsheet) for deciding what to automate next after reading this domain's per-function evidence.
- [[Ladder - Navigating the AI Economy]]: the guided path that sequences this domain against the economics and adoption-blocker domains, for someone learning the applied side end to end.
