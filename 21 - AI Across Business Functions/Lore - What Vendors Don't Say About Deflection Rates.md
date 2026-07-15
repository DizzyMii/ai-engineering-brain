---
tags: [lore, domain/applied-business, level/unicorn]
aliases: [deflection rate tricks, assumed resolution trap, containment vs resolution]
summary: "How support-AI vendors define deflection, containment, and resolution to look good — and what operators find after signing."
---

# Lore - What Vendors Don't Say About Deflection Rates

> **One-paragraph hook:** The headline number on a support-AI slide — "resolves 70% of tickets" — is almost never a lie, and almost never means what a buyer thinks it means. The model isn't the trick. The *definition* is. This is the tribal knowledge of the operators who bought the deck, ran the pilot, and discovered which word was doing the load-bearing work.

## What happened

Every support-automation pitch in 2025–2026 runs on one big number. Intercom's Fin leads with **~67% resolution rate across 40M+ conversations at $0.99/resolution** (E2, Intercom's own reporting, ~Dec 2025). Decagon, Sierra, Lorikeet, Ada all pitch adjacent figures. The number is real in the narrow sense that their instrumentation computes it. The question no vendor foregrounds is: *resolution as defined how?*

Pull the definition and the game appears. Fin counts a "resolution" two ways: **confirmed** (the customer explicitly says "yes, that solved it") and **assumed** (the customer's session ends without asking for more help) (E2, Intercom's published Fin outcome docs, 2026). Assumed resolution is the tell. A customer who reads the bot's answer and closes the tab counts identically whether they were helped, got distracted, gave up, or — the poisonous case — silently walked to a different channel to email a human because the bot was useless. All three billable "resolutions." Only one is a solved problem.

Now stack the three metrics vendors deliberately blur:

- **Deflection** — the contact never reached a human. Says nothing about outcome.
- **Containment** — the customer stayed inside the bot channel. Says nothing about outcome.
- **Resolution** — the problem was actually fixed. The only one anyone should care about.

A customer who rage-quits the bot and emails support is a *deflection success* and a *containment failure* and a *resolution failure* — and the deck shows you the first one. The industry-benchmark spread makes the size of the gap concrete: one widely circulated pairing puts **raw AI deflection near ~45% against genuine self-service resolution near ~14%** on the same footing — roughly a 31-point wedge of contacts that got a bot response and came back another way (E1, figure attributed to Gartner and repeated across CX vendor benchmarks, 2026 — see Evidence status; it circulates faster than its primary). Counter-evidence in the same breath: other 2026 benchmarks are far less bearish, putting median tier-1 deflection ~41% and industry-average *resolution* near ~45% (E1, Lorikeet CX 2026, a vendor with the opposite incentive). The exact digits are contested and vendor-motivated in both directions; what is *not* contested is the shape — deflection and true resolution are different numbers, and the gap between them is real. Mature teams that fix the knowledge base and scope query types *before* automating reach 55–70% *true* deflection measured by re-contact, but that's an earned number, not a default.

Then the part nobody puts on a slide: **Gartner walked into the savings assumption and knocked it over.** In a January 2026 prediction it projected **GenAI cost-per-resolution will exceed ~$3 by 2030 and surpass many offshore human-agent costs** — driven by rising data-center costs, the vendor pivot from subsidized growth to profitability, and complex queries burning more tokens and more retrieval (E1, Gartner press release, 2026-01-26). Gartner's read: most orgs will *stop* chasing cost cuts via automation and re-aim AI at CX quality and lifetime value. That is the exact opposite of the savings deck that sold the pilot.

And the effect operators only feel three months in — the residual-difficulty trap. Automating the easy 50–60% of tickets doesn't leave an average queue behind; it leaves the *hard* queue behind. Password resets and order-status pings are what the bot eats. What's left for humans is angry, ambiguous, multi-system, edge-case work. So **cost-per-remaining-ticket goes up and agent burnout can worsen even as total headcount falls** (analytic; see [[Concept - Support Deflection Economics]]). The blended-savings math on the slide quietly assumed the residual queue looked like the old average. It never does.

## The lesson

The mechanism to internalize: **in support automation, the metric definition is the product decision, not a reporting detail.** Two vendors with identical models report wildly different "resolution" rates purely by choosing confirmed-only vs. assumed-inclusive, and by choosing the denominator (all contacts vs. in-scope contacts vs. bot-eligible contacts). Optimizing raw deflection actively rewards the worst outcome — a customer who abandons scores the same as one who's helped, and abandonment is cheaper for the bot to produce than a real answer. You get what you measure, and if you measure deflection you are paying a vendor to manufacture abandonment.

The honest KPI is **re-contact rate**: did the same customer come back within N days for the same issue? It's the one number that can't be faked by definition-gaming, because a fake resolution reappears in the data as a re-contact. Which is precisely why it rarely leads a pitch.

The buyer's defense — the actual tribal knowledge:

1. **Redefine resolution before the pilot starts.** Contractually: resolution = CSAT-confirmed OR no re-contact within 7 days. Not "session ended."
2. **Hand-audit a sample of "resolved" transcripts.** Pull 100 flagged resolutions and read them. The delta between what the dashboard calls resolved and what a human calls solved is the whole ballgame — this is [[Concept - The Evaluation Gap]] wearing a support-vendor costume.
3. **Price against re-contact-adjusted resolution**, not the headline. If 15% of "resolutions" re-contact, your true $0.99/resolution is closer to $1.16, before the residual-queue cost inflation.
4. **Model the residual queue explicitly.** Budget for cost-per-remaining-ticket rising, not the old average holding.

The gap between the headline rate and the re-contact-adjusted rate is where the deployment quietly succeeds or quietly fails — and it's invisible until you force the second number into existence.

## Evidence status

- **Cost-per-contact ($8–12 human blended, $25–35 B2B SaaS; $0.99–2.00 AI):** E2 — industry benchmark reports (The Office Gurus 2026 blended figures; SaaS Capital B2B support spending), vary widely by geography and queue. Directionally solid, not universal.
- **~45% deflection vs ~14% true resolution:** E1 and contested — attributed to Gartner and echoed across CX vendor blogs in 2026. The specific 45/14 pairing circulates far more than its traceable primary source; treat as a well-repeated benchmark, not a controlled measurement. Competing 2026 benchmarks (Lorikeet CX) put deflection ~41% and *resolution* near ~45%, i.e. a much smaller gap — vendors on both sides pick the digits that flatter their pitch. The *shape* (deflection and true resolution diverge) is uncontested; the exact numbers are soft and directional only.
- **Fin 67% resolution / $0.99 / 40M+ conversations, assumed-resolution definition:** E2 — Intercom's own published figures and outcome documentation, 2026. The definition is documented fact; whether "assumed" inflates the true rate is the practitioner critique, well-observed but vendor-disputed.
- **Gartner GenAI cost-per-resolution >$3 by 2030, exceeding offshore agents:** E1 — Gartner press release, 2026-01-26 (a forecast; Gartner's, so name it). A sharper, later restatement of Gartner's earlier 2024 "costs will rise" line; the *direction* is the durable claim, the dollar figure is a projection.
- **Residual-difficulty / cost-per-remaining-ticket rising:** analytic + well-observed practitioner folklore. Mechanically forced by the composition of what bots can vs. can't handle; rarely measured cleanly in public, so labeled as such.

Honest bottom line: the cost and benchmark ranges are E1/E2 figures that swing hard by vendor and queue. The "assumed resolution" and residual-difficulty critiques are strong practitioner knowledge — sourced where possible, flagged as folklore where the primary is a repeated-benchmark rather than a study.

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
