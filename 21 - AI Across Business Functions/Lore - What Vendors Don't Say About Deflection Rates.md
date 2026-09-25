---
tags: [lore, domain/applied-business, level/unicorn]
aliases: [deflection rate tricks, assumed resolution trap, containment vs resolution]
summary: "How support-AI vendors define deflection, containment, and resolution to look good — and what operators find after signing."
---

# Lore - What Vendors Don't Say About Deflection Rates

> The headline number on a support-AI slide, "resolves 70% of tickets," is almost never a lie and almost never means what the buyer thinks. The trick is in the *definition*, not the model. This is the tribal knowledge of operators who bought the deck, ran the pilot, and found out which word was doing the work.

## What happened

Every support-automation pitch in 2025–2026 runs on one big number. Intercom's Fin leads with **~67% resolution rate across 40M+ conversations at $0.99/resolution** (E2, Intercom's own reporting, ~Dec 2025). Decagon, Sierra, Lorikeet and Ada all pitch similar figures. The number is real in that their instrumentation computes it. Nobody puts the real question up front: *resolution as defined how?*

Look up the definition and the game shows. Fin counts a "resolution" two ways: **confirmed** (the customer explicitly says "yes, that solved it") and **assumed** (the session ends without the customer asking for more help) (E2, Intercom's published Fin outcome docs, 2026). Assumed resolution is the tell. A customer who reads the bot's answer and closes the tab counts the same whether they were helped, got distracted, gave up, or, worst case, silently went to another channel to email a human because the bot was useless. All of those are billable "resolutions." Only one is a solved problem.

Now stack the three metrics vendors deliberately blur:

- **Deflection**: the contact never reached a human. Says nothing about outcome.
- **Containment**: the customer stayed inside the bot channel. Says nothing about outcome.
- **Resolution**: the problem was fixed. The only one anyone should care about.

A customer who rage-quits the bot and emails support is a *deflection success*, a *containment failure* and a *resolution failure*, and the deck shows you the first one. Industry benchmarks give a sense of the gap. One widely circulated pairing puts **raw AI deflection near ~45% against genuine self-service resolution near ~14%** on the same footing, roughly a 31-point wedge of contacts that got a bot response and came back another way (E1, attributed to Gartner and repeated across CX vendor benchmarks, 2026; see Evidence status, since it spreads faster than its primary source). Other 2026 benchmarks are far less bearish: median tier-1 deflection ~41% and industry-average *resolution* near ~45% (E1, Lorikeet CX 2026, a vendor with the opposite incentive). The exact digits are contested and vendor-motivated in both directions. The shape isn't contested: deflection and true resolution are different numbers, and the gap is real. Mature teams that fix the knowledge base and scope query types *before* automating reach 55–70% *true* deflection measured by re-contact. That's earned, not default.

Then the part nobody puts on a slide. **Gartner knocked over the savings assumption.** A January 2026 prediction projected that **GenAI cost-per-resolution will exceed ~$3 by 2030 and surpass many offshore human-agent costs**, driven by rising data-center costs, vendors moving from subsidized growth to profitability, and complex queries burning more tokens and more retrieval (E1, Gartner press release, 2026-01-26). Gartner expects most orgs to *stop* chasing cost cuts through automation and aim AI at CX quality and lifetime value instead. That's the opposite of the savings deck that sold the pilot.

Operators only feel the next effect about three months in: the residual-difficulty trap. Automating the easy 50–60% of tickets leaves the *hard* queue behind, not an average one. The bot eats password resets and order-status pings. Humans get the angry, ambiguous, multi-system, edge-case work. So **cost per remaining ticket goes up and agent burnout can get worse even as total headcount falls** (analytic; see [[Concept - Support Deflection Economics]]). The blended-savings math on the slide assumed the residual queue would look like the old average. It never does.

## The lesson

**In support automation, the metric definition is a product decision, not a reporting detail.** Two vendors with identical models can report wildly different "resolution" rates just by choosing confirmed-only vs. assumed-inclusive, and by choosing the denominator (all contacts, in-scope contacts, or bot-eligible contacts). Optimizing raw deflection rewards the worst outcome. An abandoning customer scores the same as a helped one, and abandonment is cheaper for the bot to produce than a real answer. If you measure deflection, you're paying a vendor to manufacture abandonment.

The honest KPI is **re-contact rate**: did the same customer come back within N days with the same issue? Definition games can't fake it, because a fake resolution reappears in the data as a re-contact. So it rarely leads a pitch.

The buyer's defense, the actual tribal knowledge:

1. **Redefine resolution before the pilot starts.** Put it in the contract: resolution = CSAT-confirmed OR no re-contact within 7 days. Not "session ended."
2. **Hand-audit a sample of "resolved" transcripts.** Pull 100 flagged resolutions and read them. The difference between what the dashboard calls resolved and what a human calls solved is the whole ballgame. It's [[Concept - The Evaluation Gap]] in a support-vendor costume.
3. **Price against re-contact-adjusted resolution**, not the headline. If 15% of "resolutions" re-contact, your real $0.99/resolution is closer to $1.16, before the residual-queue cost inflation.
4. **Model the residual queue explicitly.** Budget for cost per remaining ticket rising, not for the old average holding.

The deployment succeeds or fails in the gap between the headline rate and the re-contact-adjusted rate, which stays invisible until you force the second number into existence.

## Evidence status

- **Cost per contact ($8–12 human blended, $25–35 B2B SaaS; $0.99–2.00 AI):** E2, industry benchmark reports (The Office Gurus 2026 blended figures; SaaS Capital B2B support spending). Varies widely by geography and queue. Directionally solid, not universal.
- **~45% deflection vs ~14% true resolution:** E1 and contested. Attributed to Gartner and echoed across CX vendor blogs in 2026. The specific 45/14 pairing circulates far more than its traceable primary source, so treat it as a well-repeated benchmark, not a controlled measurement. Competing 2026 benchmarks (Lorikeet CX) put deflection ~41% and *resolution* near ~45%, a much smaller gap. Vendors on both sides pick the digits that flatter their pitch. The *shape* (deflection and true resolution diverge) is uncontested; the exact numbers are soft and directional only.
- **Fin 67% resolution / $0.99 / 40M+ conversations, assumed-resolution definition:** E2, Intercom's own published figures and outcome documentation, 2026. The definition is documented fact. Whether "assumed" inflates the true rate is the practitioner critique, widely observed and disputed by the vendor.
- **Gartner GenAI cost-per-resolution >$3 by 2030, exceeding offshore agents:** E1, Gartner press release, 2026-01-26 (a forecast, and Gartner's, so name it). It's a sharper, later version of Gartner's earlier 2024 "costs will rise" line. The *direction* is the durable claim; the dollar figure is a projection.
- **Residual difficulty / cost per remaining ticket rising:** analytic plus widely observed practitioner folklore. It follows mechanically from what bots can and can't handle, but is rarely measured cleanly in public, hence the label.

Bottom line: the cost and benchmark ranges are E1/E2 figures that swing hard by vendor and queue. The "assumed resolution" and residual-difficulty critiques are strong practitioner knowledge, sourced where possible and flagged as folklore where the primary is a repeated benchmark instead of a study.

## Connections

- [[Concept - Support Deflection Economics]] — the clean, quantified version of this story; this Lore note is the part you learn *after* the spreadsheet.
- [[Breakdown - Klarna's AI Customer Service Bet]] — the most-cited savings headline, and the reference case where the definitional games played out at scale.
- [[Lore - The Klarna Reversal and Support Bot Walk-Backs]] — what happened when one of those headline numbers met reality and got walked back.
- [[Concept - The Evaluation Gap]] — cross-domain (evaluation): "resolved" vs. actually-solved is the support-vendor instance of the general eval-vs-reality gap.
- [[Concept - Vertical AI Agents by Function]] — support bots are the most-deployed vertical agent; their metric games generalize to every function's ROI deck.
- [[Reference - AI Impact by Business Function]] — where support-automation ROI claims sit relative to other functions; use it to sanity-check the headline.
- [[Concept - Unit Economics of LLM Products]] — cross-domain (ai-economics): why complex queries burn tokens and retrieval, the mechanism under Gartner's rising-cost call.
- [[Concept - Token Price Deflation]] — cross-domain (ai-economics): the counter-force vendors bank on to save the savings deck; Gartner's bet is that complexity growth outruns it.

## Sources
- Intercom — Fin AI Agent outcomes documentation and public resolution reporting (2026). Defines confirmed vs. assumed resolution; source of the 67% / $0.99 / 40M figures.
- Gartner — "GenAI Cost Per Resolution for Customer Service Will Exceed Offshore Human Agent Costs by 2030" press release, 2026-01-26. The rising-cost contrarian call.
- Gartner — earlier 2024 predictions on GenAI support cost trajectory and third-party GenAI resolving 40% of issues by 2027 (via CX Dive coverage). Origin of the "costs will rise" thesis.
- CX vendor benchmark blogs (Decagon, eesel, getmacha, Alhena; 2026) — repeated source of the ~45% deflection / ~14% resolution pairing attributed to Gartner. Treat as repeated-benchmark, not primary.
- The Office Gurus / industry benchmarking (2026) and SaaS Capital B2B Support Spending — cost-per-ticket ranges ($8–12 blended, $25–35 SaaS).
