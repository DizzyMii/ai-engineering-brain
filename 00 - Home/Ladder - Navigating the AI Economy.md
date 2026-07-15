---
tags: [ladder, domain/home, level/surface]
aliases: [Navigating the AI Economy, AI economy cheatsheet, applied AI learning path, where AI actually pays]
summary: "Ordered surface-to-unicorn walk of the Applied Wing: where AI landed, what it costs, what blocks it, where it's going, how to play it."
---

# Ladder - Navigating the AI Economy

A guided walk through the Applied Wing (folders 20–24) for one question: *where has AI actually been deployed, what does it cost and earn, what's blocking it, where is it going, and how do I play it without getting burned?* Nineteen steps, ordered so the story builds — measured deployment reality first, then the economics, then the blockers, then the trajectory, then the operating playbook, closing on the graveyard of confident predictions. Read each note for the one thing named under it; if you can answer the self-test, you got the point and can move on. Every number in this wing is date-stamped and evidence-tiered (E0–E3) — check the date before you quote it. This ladder covers the Applied Wing only; for the full 25-domain map, including the Engineering Wing (01-19) this wing's economics ultimately rest on, start at [[Home]].

---

## Act I — What actually happened (measured deployment reality)

**1. [[Concept - The Front-Office Back-Office Adoption Split]]**
Extract the organizing fact of applied AI as of mid-2026: adoption speed tracks *error tolerance and who bears the cost of review*, not task complexity. Back-office work (drafting a note, summarizing a contract) routes model output through an accountable human before it has consequences; front-office work (a support bot, an SDR agent) often skips that gate by design, which is the entire economic case for automating it. Note the reframe: "function" is the wrong unit — AI automates *tasks*, and the review gate is what survives even as the task mix inside a role shifts.
*Self-test:* A medical scribe scaled cleanly to thousands of physicians while an equally-mature customer-service bot had to be walked back — why is "healthcare is just more careful" the wrong explanation?

**2. [[Concept - AI Coding Assistants]]**
Extract the three-generation taxonomy — inline autocomplete → in-IDE chat/edit → autonomous agents — and the load-bearing point that each generation trades more autonomy for a longer chain of unverified model decisions, which is exactly where reliability degrades. Coding is the most-deployed, best-measured application (Copilot passed 20M users, 90% of the Fortune 100), so it is where the evidence is sharpest. Hold onto the fact that AI-authored share of new code is ~25–30% (measured), not the folkloric "41%."
*Self-test:* Why do the two best-run coding-productivity RCTs — Peng's +55.8% and METR's −19% — not actually contradict each other?

**3. [[Breakdown - GitHub Copilot's Measured Productivity Impact]]**
Extract the shape of the positive evidence and its load-bearing weakness: nearly every large positive result (Peng, Cui et al.'s three-RCT +26%, Accenture) comes from short, well-scoped, often greenfield tasks with populations skewed toward less-experienced developers, who gain most. Note that suggestion "acceptance rate" (~27–30%) is a weak proxy — accepted ≠ correct, and code retained at commit isn't retained at month six. The honest summary is "faster on short low-familiarity work, can be slower on long high-familiarity work," never a single multiplier.
*Self-test:* What do essentially all the large positive Copilot studies share that caps how far their numbers generalize?

**4. [[Breakdown - The METR Developer Slowdown RCT]]**
Extract the single most important number in the applied-software domain: experienced developers were measured 19% *slower* with AI on their own mature repos, while forecasting +24% and still believing +20% afterward — wrong about the *direction* by ~40 points despite living through it. The within-subject randomization over real merged tasks is what kills the confounds vendor studies can't. Read the scope honestly: N=16 elite maintainers on familiar code, the exact population where every study finds the smallest benefit — do not quote it as "AI makes developers slower," full stop.
*Self-test:* The METR developers' perception was off by ~40 points — what does that specifically invalidate about most corporate AI-ROI programs?

**5. [[Breakdown - AI Medical Scribes]]**
Extract the best-evidenced clinical AI deployment (Permanente: 7,260 physicians, 2.5M+ encounters, 15,791 hours saved, peer-reviewed) and *why* it worked: the pipeline stops at a **draft**, and the physician's signature — not a model confidence score — is the real quality gate. That design let vendors ship at a documented 1.5–7% hallucination rate because the accountable human catches the residual; ~80% of a draft is retained, meaning a fifth is human correction. The task selection (documentation, not diagnosis) is the whole trick: high burden, low decision-risk.
*Self-test:* AI scribes ship despite a 1.5–7% hallucination rate — what design decision makes that acceptable, and what does it inherit that autonomous diagnosis wouldn't?

**6. [[Breakdown - Klarna's AI Customer Service Bet]]**
Extract the most-cited case of the cycle in both directions: a tool-grounded, retrieval-plus-live-API assistant that genuinely deflected 2.3M chats/month for bounded query types, then was publicly walked back in May 2025 ("we went too far... lower quality"). Crucially, Klarna did **not** un-deploy — it rebalanced to a copilot+autopilot split, keeping AI on routine volume and rehiring humans for nuanced cases. The failure was structural: removing the easy 60% leaves a harder, angrier residual queue, and a cost-only metric with no quality guardrail hid the degradation until lagged trust/churn signals landed.
*Self-test:* Klarna kept its bot running — so what exactly did it correct, and why was the quality collapse structural rather than a bug?

---

## Act II — What it costs and what it earns (the economics)

**7. [[Concept - Value Capture Across the AI Stack]]**
Extract the five-layer stack (silicon → cloud → labs → apps → distribution) and the asymmetry that governs it: **pricing power flows downward, cost flows upward.** Silicon (Nvidia, 75% gross margin, $115B data-center revenue) captures the fattest durable margin because it's a price-setter on both sides; the model layer gets squeezed into a "thin-margin sandwich." The master distinction: value *created* (McKinsey's $2.6–4.4T, E1) lands with the enterprises deploying AI, not the vendors selling it — don't conflate a macro productivity estimate with your product's addressable revenue.
*Self-test:* Why does the fattest, most durable margin sit at the *bottom* of the stack (silicon) while most of the economic value lands with neither the labs nor the app vendors?

**8. [[Concept - Token Price Deflation]]**
Extract "LLMflation" — roughly 10x/year price decline for a *fixed* quality bar (GPT-3-quality: $60/M → $0.06/M in three years) — and the two business consequences: cost-plus token pricing is a melting ice cube, and Jevons demand expansion offsets the price collapse (spend rose ~22x while unit prices fell >90%). The non-obvious core: deflation is measured *per quality level held fixed*, not per token you actually buy.
*Self-test:* "GPT-3-quality tokens are 1000x cheaper" does *not* mean your AI bill falls 1000x — why not, and what would you have to do to actually capture that saving?

**9. [[Concept - Unit Economics of LLM Products]]**
Extract why LLM products run ~52–65% gross margin instead of SaaS's 80–90%: every call is metered variable cost, so the near-zero-marginal-cost assumption that made flat pricing safe is dead. Learn the cost drivers (output tokens 3–5x input, retries, RAG overhead, reasoning "thinking" tokens at 5–20x visible output) and the levers (prompt/semantic caching, model routing, quantization). The discipline that matters: measure cost per *outcome* (per resolved ticket, per merged PR), per-cohort — never blended.
*Self-test:* Why does flat-rate per-seat pricing — fine for SaaS for decades — become dangerous the moment an LLM sits in the request path?

**10. [[Concept - Moats in the AI Application Layer]]**
Extract the checklist for telling a moat from a demo: the model call is never the moat (it commoditizes every quarter); durable defensibility comes from proprietary *outcome* data, workflow/switching-cost lock-in, distribution, or network effects. The strongest moat is becoming the *system of record for a workflow's outcomes* — captured from day one, structurally, because it can't be bolted on later. Cursor's habit lock-in is the win; Jasper is the cautionary wrapper.
*Self-test:* What is the one-question test for whether an AI product has a real moat, and why did Jasper fail it the week ChatGPT launched?

---

## Act III — What blocks it (the adoption reality)

**11. [[Concept - The Pilot-to-Production Gap]]**
Extract the headline blocker: ~95% of enterprise GenAI initiatives show no measurable P&L impact (MIT NANDA, E2) — but read it honestly, since many are un-instrumented pilots, not broken systems, and the press "95% of AI fails" flattening is a claim the report does not make. The mechanism is a **reliability cliff, not a slope**: a demo is a curated slice, production is the full adversarial long tail, and a 20%-more-capable model closes only whatever failures fall below the new line. Note the buy-vs-build asymmetry: purchased tools reach production ~67% of the time vs ~1/3 for internal builds.
*Self-test:* Why does a model that is "20% more capable" *not* close 20% of the pilot-to-production gap?

**12. [[Concept - The Evaluation Gap]]**
Extract the instrument failure behind the pilot gap: most teams run production GenAI with no task-specific labeled eval set, so they can't detect a regression, defend a go/no-go, or say anything more rigorous than a vibe. Learn why it's structurally hard (no single correct answer, public benchmarks measure a different distribution, LLM-judges need their own validation) and the fix (50–500 labeled real cases, including adversarial ones, *before* launch). The reframe: building the eval set *is* the product work, not a chore before it.
*Self-test:* Why is building the eval set the real work rather than a preliminary to it — what does its absence cost on every model swap and prompt tweak?

**13. [[Concept - The Verification Tax]]**
Extract the equation vendors omit: net value = generation savings − verification cost − (miss probability × error cost). AI wins only where checking is much cheaper than doing (the generation–verification asymmetry): tests, citations, runnable queries are cheap to verify; legal arguments and medical summaries are not. The counterintuitive kicker: a stronger, more fluent model can *raise* the tax, because plausibly-wrong output is harder to catch than obviously-wrong output.
*Self-test:* Why can upgrading to a *more* capable model increase the verification tax instead of shrinking it?

---

## Act IV — Where it's going (the trajectory)

**14. [[Concept - METR Time Horizons]]**
Extract the metric that survived benchmark saturation: the human-task-length a model completes unattended at a given reliability, doubling roughly every 7 months (2019–25) and accelerating to ~3–4 months since 2024, reaching ~16–20 hours at the frontier by mid-2026. Learn the two traps: the **50/80 gap** (the deployment-ready 80% horizon is ~5x shorter, ~3–4 hours), and that the suite only scores *checkable* pass/fail tasks, so it structurally can't measure the ambiguous judgment work most jobs are made of.
*Self-test:* A model has a "16-hour time horizon" — give two independent reasons that does not mean you can hand it a two-day ambiguous project.

**15. [[Concept - The Data Wall]]**
Extract that it's a *quality* wall, not a byte wall: ~300T usable tokens after dedup/filtering (Epoch, E1/E2 — a model, not a measurement, which already moved from ~2024 to ~2028), so "more internet every day" is not a rebuttal because most of it fails the filter. The bite by 2026 is economic, not physical: it removes the cheapest scaling lever and reallocates spend toward compute, synthetic data, and RL-on-verifiable-rewards — which is why frontier gains visibly shifted from bigger pretraining to post-training RL.
*Self-test:* Why is "there's more internet created every day" not a rebuttal to the data wall, and what does the wall actually change by 2026 rather than stop?

**16. [[Deep Dive - Bubble or Boom]]**
Extract the three-question framework that dissolves the debate: (Q1) are equities overpriced, (Q2) is real capex running ahead of demand, (Q3) does the technology deliver value — three *orthogonal* questions, all three simultaneously true of the internet c.2000. Learn the circular-financing topology (Nvidia→OpenAI→clouds→Nvidia, $800B+ in loops) that inflates apparent demand and magnifies losses on the way down, the fiber-overbuild analog, and the unresolved GPU-depreciation crux. The practitioner's posture: bubble-agnostic, use-case-fundamentalist.
*Self-test:* Why are "AI is a bubble" and "AI is transformative" not opposites, and which of the three questions is the only one that should drive *your* deployment decision?

---

## Act V — How to play it (the operating cheatsheet)

**17. [[Playbook - Picking Profitable AI Use Cases]]**
Extract the six-step filter: (1) classify error tolerance, (2) default to augmentation over automation, (3) score value with real counts not vibes, (4) price verification honestly, (5) buy/wrap over build for commodity capability, (6) write the kill metric and baseline *before* any code ships. The evidence anchors: augmentation helps your weaker performers most (+34% novice, ~0 expert in Brynjolfsson-Li-Raymond), and the missing kill criterion is the single best predictor of a pilot silently draining budget for a year.
*Self-test:* Which step does NANDA's 95%-stall finding most directly indict, and why is skipping it the best predictor of a doomed pilot?

**18. [[Reference - The 2026 Navigation Cheatsheet]]**
Extract the date-stamped, tier-marked lookup: what's profitable today (coding-in-the-loop, support deflection, scribes) versus overhyped (fully-autonomous high-stakes agents, wholesale headcount replacement, KPI-less pilots), the cost curve, the reliability frontier (build inside the 80% horizon), and the forecast spread — four methods, decades apart, *never averaged*. Anchor on the four no-regret moves that hold in bubble or boom.
*Self-test:* Name the four no-regret moves that hold whether we're in a bubble or a boom, and the shared property that makes them scenario-robust.

---

## The unicorn tier — the graveyard

**19. [[Lore - Failed AI Predictions]]**
Extract the tribal knowledge under the war stories (self-driving "a year away," Hinton's radiologists, Watson Health's $4B, Klarna's 700 agents): almost every bust is one of two errors — **demo-to-deployment extrapolation** (forecasting a 50%-reliable demo as if it ships, ignoring that 99.9% is most of the remaining work) or **task-vs-job confusion** (automating a task ≠ eliminating a job). The durable directional rule, symmetric across hype and doom: capability curves get *under*-forecast (wrong slow, pleasant); reliability and adoption timelines get *over*-forecast (wrong fast, expensive). Weight your own reading accordingly.
*Self-test:* Radiology is the purest case of which of the two forecasting errors, and what's the directional asymmetry the whole graveyard teaches about "how good" versus "how soon"?
