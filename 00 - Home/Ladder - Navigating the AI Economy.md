---
tags: [ladder, domain/home, level/surface]
aliases: [Navigating the AI Economy, AI economy cheatsheet, applied AI learning path, where AI actually pays]
summary: "Ordered surface-to-unicorn walk of the Applied Wing: where AI landed, what it costs, what blocks it, where it's going, how to play it."
---

# Ladder - Navigating the AI Economy

A walk through the Applied Wing (folders 20–24) around one question: *where has AI actually been deployed, what does it cost and earn, what's blocking it, where is it going, and how do I play it without getting burned?* Nineteen steps. Measured deployment reality first, then economics, blockers, trajectory and the playbook, ending on the graveyard of confident predictions. Read each note for the one thing named under it; pass the self-test and move on. Every number in this wing is date-stamped and evidence-tiered (E0–E3), so check the date before you quote it. This ladder only covers the Applied Wing. For the full 25-domain map, including the Engineering Wing (01-19) whose mechanics this wing's economics rest on, start at [[Home]].

---

## Act I: What actually happened (measured deployment reality)

**1. [[Concept - The Front-Office Back-Office Adoption Split]]**
The organizing fact of applied AI as of mid-2026: adoption speed tracks *error tolerance and who bears the cost of review*. Task complexity doesn't predict it. Back-office work (drafting a note, summarizing a contract) sends model output through an accountable human before it has consequences. Front-office work (a support bot, an SDR agent) often skips that gate by design, and skipping it is the whole economic case for automating it. "Function" is the wrong unit. AI automates *tasks*, and the review gate is what survives as the task mix inside a role shifts.
*Self-test:* A medical scribe scaled cleanly to thousands of physicians while an equally mature customer-service bot had to be walked back. Why is "healthcare is just more careful" the wrong explanation?

**2. [[Concept - AI Coding Assistants]]**
Take the three-generation taxonomy (inline autocomplete → in-IDE chat/edit → autonomous agents) and its main point: each generation buys more autonomy with a longer chain of unverified model decisions, and that chain is where reliability degrades. Coding is the most-deployed, best-measured application (Copilot passed 20M users, 90% of the Fortune 100), so the evidence is sharpest here. AI-authored share of new code is ~25–30% (measured), not the folkloric "41%."
*Self-test:* Why don't the two best-run coding-productivity RCTs, Peng's +55.8% and METR's −19%, contradict each other?

**3. [[Breakdown - GitHub Copilot's Measured Productivity Impact]]**
The positive evidence and its main weakness. Nearly every large positive result (Peng, Cui et al.'s three-RCT +26%, Accenture) comes from short, well-scoped, often greenfield tasks, with populations skewed toward less-experienced developers, who gain most. Suggestion "acceptance rate" (~27–30%) is a weak proxy: accepted ≠ correct, and code kept at commit isn't necessarily kept at month six. The honest summary is "faster on short low-familiarity work, can be slower on long high-familiarity work." Never a single multiplier.
*Self-test:* What do essentially all the large positive Copilot studies share that caps how far their numbers generalize?

**4. [[Breakdown - The METR Developer Slowdown RCT]]**
The domain's most important number. Experienced developers were measured 19% *slower* with AI on their own mature repos. They forecast +24% and still believed +20% afterward, wrong on *direction* by ~40 points despite living through it. Within-subject randomization over real merged tasks removes confounds vendor studies can't. Read the scope honestly: N=16 elite maintainers on familiar code, the population where every study finds the smallest benefit. Don't quote it as "AI makes developers slower," full stop.
*Self-test:* The METR developers' perception was off by ~40 points. What does that invalidate about most corporate AI-ROI programs?

**5. [[Breakdown - AI Medical Scribes]]**
The best-evidenced clinical AI deployment (Permanente: 7,260 physicians, 2.5M+ encounters, 15,791 hours saved, peer-reviewed), and *why* it worked. The pipeline stops at a **draft**, and the physician's signature, not a model confidence score, is the real quality gate. That design let vendors ship at a documented 1.5–7% hallucination rate, because the accountable human catches the residual. About 80% of a draft is retained, so a fifth is human correction. Picking documentation over diagnosis is the whole trick: high burden, low decision risk.
*Self-test:* AI scribes ship despite a 1.5–7% hallucination rate. What design decision makes that acceptable, and what does it inherit that autonomous diagnosis wouldn't?

**6. [[Breakdown - Klarna's AI Customer Service Bet]]**
A tool-grounded assistant (retrieval plus live API) deflected 2.3M chats/month for bounded query types, then publicly walked back in May 2025 ("we went too far... lower quality"). Klarna did **not** un-deploy. It rebalanced to a copilot+autopilot split, keeping AI on routine volume and rehiring humans for nuanced cases. The failure was built into the setup: removing the easy 60% leaves a harder, angrier residual queue, and a cost-only metric with no quality guardrail hid the decline until lagged trust and churn signals arrived.
*Self-test:* Klarna kept its bot running. So what did it correct, and why was the quality collapse a design problem and not a bug?

---

## Act II: What it costs and what it earns (the economics)

**7. [[Concept - Value Capture Across the AI Stack]]**
The five-layer stack (silicon → cloud → labs → apps → distribution) and its governing asymmetry: **pricing power flows downward, cost flows upward.** Silicon (Nvidia, 75% gross margin, $115B data-center revenue) holds the fattest durable margin because it sets prices on both sides. The model layer gets squeezed into a "thin-margin sandwich." Key distinction: value *created* (McKinsey's $2.6–4.4T, E1) lands with the enterprises deploying AI, not the vendors selling it. Don't confuse a macro productivity estimate with your product's addressable revenue.
*Self-test:* Why does the fattest, most durable margin sit at the *bottom* of the stack (silicon) while most of the economic value lands with neither the labs nor the app vendors?

**8. [[Concept - Token Price Deflation]]**
"LLMflation": prices fall roughly 10x/year for a *fixed* quality bar (GPT-3-quality: $60/M → $0.06/M in three years). Consequences: cost-plus token pricing is a melting ice cube, and Jevons demand expansion offsets the price collapse (spend rose ~22x while unit prices fell >90%). Deflation is measured *per quality level held fixed*, not per token you actually buy.
*Self-test:* "GPT-3-quality tokens are 1000x cheaper" does *not* mean your AI bill falls 1000x. Why not, and what would you have to do to capture that saving?

**9. [[Concept - Unit Economics of LLM Products]]**
Why LLM products run ~52–65% gross margin against SaaS's 80–90%: every call is metered variable cost, which kills the near-zero-marginal-cost assumption that made flat pricing safe. Costs come from output tokens (3–5x input), retries, RAG overhead and reasoning "thinking" tokens (5–20x visible output); the levers are prompt/semantic caching, model routing and quantization. The discipline: measure cost per *outcome* (per resolved ticket, per merged PR), per cohort. Never blended.
*Self-test:* Why does flat-rate per-seat pricing, fine for SaaS for decades, become dangerous once an LLM sits in the request path?

**10. [[Concept - Moats in the AI Application Layer]]**
Telling a moat from a demo. The model call is never the moat; it commoditizes every quarter. Durable defensibility comes from proprietary *outcome* data, workflow and switching-cost lock-in, distribution, or network effects. The strongest moat is becoming the *system of record for a workflow's outcomes*, captured from day one, because it can't be bolted on later. Cursor's habit lock-in is the win. Jasper is the cautionary wrapper.
*Self-test:* What's the one-question test for whether an AI product has a real moat, and why did Jasper fail it the week ChatGPT launched?

---

## Act III: What blocks it (the adoption reality)

**11. [[Concept - The Pilot-to-Production Gap]]**
The headline blocker: ~95% of enterprise GenAI initiatives show no measurable P&L impact (MIT NANDA, E2). Read it honestly. Many are un-instrumented pilots, not broken systems, and the press version, "95% of AI fails," is a claim the report doesn't make. The mechanism is a **reliability cliff, not a slope**. A demo is a curated slice; production is the full adversarial long tail. A 20%-more-capable model closes only the failures that fall below the new line. Buy-vs-build asymmetry: purchased tools reach production ~67% of the time, internal builds ~1/3.
*Self-test:* Why does a model that is "20% more capable" *not* close 20% of the pilot-to-production gap?

**12. [[Concept - The Evaluation Gap]]**
The instrument failure behind the pilot gap. Most teams run production GenAI without a task-specific labeled eval set, so they can't detect a regression, defend a go/no-go, or say anything more rigorous than a vibe. It's inherently hard: there's no single correct answer, public benchmarks measure a different distribution, and LLM judges need their own validation. The fix is 50–500 labeled real cases, adversarial ones included, *before* launch. Building the eval set *is* the product work.
*Self-test:* Why is building the eval set the real work and not a preliminary to it? What does its absence cost on every model swap and prompt tweak?

**13. [[Concept - The Verification Tax]]**
The equation vendors leave out: net value = generation savings − verification cost − (miss probability × error cost). AI wins only where checking is much cheaper than doing (the generation–verification asymmetry). Tests, citations and runnable queries are cheap to verify. Legal arguments and medical summaries aren't. The counterintuitive part: a stronger, more fluent model can *raise* the tax, since plausibly wrong output is harder to catch than obviously wrong output.
*Self-test:* Why can upgrading to a *more* capable model increase the verification tax instead of shrinking it?

---

## Act IV: Where it's going (the trajectory)

**14. [[Concept - METR Time Horizons]]**
The metric that survived benchmark saturation: the length of human task a model completes unattended at a given reliability. It doubled roughly every 7 months (2019–25), has sped up to ~3–4 months since 2024, and reached ~16–20 hours at the frontier by mid-2026. Two traps. First, the **50/80 gap**: the deployment-ready 80% horizon is ~5x shorter, ~3–4 hours. Second, the suite only scores *checkable* pass/fail tasks, so by construction it can't measure the ambiguous judgment work most jobs are made of.
*Self-test:* A model has a "16-hour time horizon." Give two independent reasons that doesn't mean you can hand it a two-day ambiguous project.

**15. [[Concept - The Data Wall]]**
It's a *quality* wall, not a byte wall. ~300T usable tokens remain after dedup and filtering (Epoch, E1/E2; a model, not a measurement, and it has already moved from ~2024 to ~2028). "More internet every day" doesn't rebut it, because most of the new text fails the filter. By 2026 the bite is economic, not physical. It removes the cheapest scaling lever and pushes spend toward compute, synthetic data and RL on verifiable rewards. That's why frontier gains visibly shifted from bigger pretraining to post-training RL.
*Self-test:* Why is "there's more internet created every day" not a rebuttal to the data wall, and what does the wall change by 2026, as opposed to stop?

**16. [[Deep Dive - Bubble or Boom]]**
A three-question framework that dissolves the debate: (Q1) are equities overpriced, (Q2) is real capex running ahead of demand, (Q3) does the technology deliver value. The three are *orthogonal*, and all three were true of the internet c.2000 at once. Then the circular-financing topology (Nvidia→OpenAI→clouds→Nvidia, $800B+ in loops) that inflates apparent demand and magnifies losses on the way down, the fiber-overbuild analog, and the open GPU-depreciation question. Stance: agnostic on the bubble, strict on the use case.
*Self-test:* Why aren't "AI is a bubble" and "AI is transformative" opposites, and which of the three questions should be the only one driving *your* deployment decision?

---

## Act V: How to play it (the operating cheatsheet)

**17. [[Playbook - Picking Profitable AI Use Cases]]**
The six-step filter: (1) classify error tolerance, (2) default to augmentation over automation, (3) score value with real counts, not vibes, (4) price verification honestly, (5) buy or wrap before building commodity capability, (6) write the kill metric and baseline *before* any code ships. Evidence anchors: augmentation helps your weaker performers most (+34% novice, ~0 expert in Brynjolfsson-Li-Raymond), and a missing kill criterion is the single best predictor of a pilot silently draining budget for a year.
*Self-test:* Which step does NANDA's 95%-stall finding most directly indict, and why is skipping it the best predictor of a doomed pilot?

**18. [[Reference - The 2026 Navigation Cheatsheet]]**
The date-stamped, tier-marked lookup. What's profitable today (coding-in-the-loop, support deflection, scribes) versus overhyped (fully autonomous high-stakes agents, wholesale headcount replacement, KPI-less pilots), the cost curve, the reliability frontier (build inside the 80% horizon), and the forecast spread: four methods, decades apart, *never averaged*. Anchor on the four no-regret moves.
*Self-test:* Name the four no-regret moves that hold whether we're in a bubble or a boom, and the shared property that makes them hold up in every scenario.

---

## The unicorn tier: the graveyard

**19. [[Lore - Failed AI Predictions]]**
What sits under the war stories (self-driving "a year away," Hinton's radiologists, Watson Health's $4B, Klarna's 700 agents). Almost every bust is one of two errors. **Demo-to-deployment extrapolation** forecasts a 50%-reliable demo as if it ships, ignoring that 99.9% is most of the remaining work. **Task-vs-job confusion** treats automating a task as eliminating a job. The directional rule holds for hype and doom alike: capability curves get *under*-forecast (wrong slow, pleasant), while reliability and adoption timelines get *over*-forecast (wrong fast, expensive). Weight your reading accordingly.
*Self-test:* Radiology is the purest case of which of the two forecasting errors, and what's the directional asymmetry the whole graveyard teaches about "how good" versus "how soon"?
