---
tags: [deep-dive, domain/trajectory, level/advanced]
aliases: [AI Bubble, AI Boom, Is AI a Bubble, AI Capex Bubble]
summary: "Market-scale scenario analysis of the 2024-2026 AI buildout, and why 'bubble' and 'transformative' are orthogonal questions."
---

# Deep Dive - Bubble or Boom

> **One-paragraph hook:** By 2026 the AI industry is spending on infrastructure at a rate that dwarfs its revenue, financing much of that demand through deals its own suppliers underwrite, on hardware whose useful life is itself disputed. That's the textbook shape of a bubble. It's also the textbook shape of every real infrastructure revolution in its capital-formation phase. The most common analytical error in this debate is treating "AI is a bubble" and "AI is transformative" as opposites. They're independent questions, and both were true of the internet in 2000. Below: a framework that keeps them apart, the numbers on both sides, and the signals that tell you which world you're in.

## The gap, quantified

The bear thesis starts with an accounting gap, which Sequoia's David Cahn made concrete in **"AI's $600B Question" (June 2024, E1, named analyst)**. Take Nvidia's data-center run-rate revenue, double it to cover the rest of a data center's total cost of ownership (GPUs are roughly half), then double again for the ~50% gross margin the cloud provider needs. That's the annual end-user AI revenue required to justify the spend. By mid-2024 it implied **~$600B/yr of AI revenue needed against an actual run-rate an order of magnitude lower**. Cahn's September 2023 version was "the $200B question"; the gap *widened* even as OpenAI's revenue doubled, because capex grew faster than demand. Cahn himself doesn't read it as "bubble". His is a *timing* argument: the revenue will come, capital is running years ahead of it, and surviving the gap decides the winners.

Goldman Sachs' Jim Covello sharpened the skeptical case in the June 2024 report **"Gen AI: Too Much Spend, Too Little Benefit?" (E1, named analyst)**: ~$1T to be spent on data centers, chips and grid upgrades "with little to show for it so far," and the pointed question, *what trillion-dollar problem does AI actually solve?* Covello argues that "replacing low-wage jobs with tremendously costly technology is the polar opposite of prior technology transitions." It's a bank equity-research view, contested inside Goldman. By mid-2026 Covello was still asking the same question ahead of the OpenAI/Anthropic IPO cycle, which is either vindication or a broken clock depending on your priors.

## Circular financing: how demand gets made to look organic

The 2026 worry is less the size of the spend than its *topology*. The money moves in a loop:

```
        equity / "investment"
   Nvidia ───────────────────────► OpenAI
     ▲                                │
     │                                │ cloud commitments
     │ GPU purchases                  │ (hundreds of $B)
     │ ("revenue")                    ▼
   Oracle / CoreWeave / clouds ◄──────┘
```

Nvidia invests in OpenAI (a **$100B partnership** announced 2025). OpenAI commits hundreds of billions to clouds like Oracle (**a ~$300B cloud deal**). Those clouds buy Nvidia GPUs to build the capacity. Cash leaves Nvidia's balance sheet as an *investment* and comes back on its income statement as *revenue*, laundered through two counterparties into what looks like third-party demand. **2026 analyses put the total of such arrangements at $800B+ (E1/E2, Bloomberg and others, 2026).**

Vendor financing isn't inherently fraudulent; it built the railroads and the telecom networks. It has two failure properties, though. It *inflates apparent demand*, since the same dollar counts as demand at every hop. And it *magnifies losses on the way down*: if OpenAI's revenue disappoints, the impairment cascades back through Oracle to Nvidia. [[Deep Dive - Circular Financing in the AI Buildout]] traces the individual deal structures.

## The historical parallel, named

The closest analog is the **late-1990s telecom fiber overbuild (E2, historical)**, more than the dot-com equity mania. Vendors like Lucent and Nortel financed their own customers (CLECs) to buy switching gear. Carriers laid ~80M miles of fiber on projections that assumed internet traffic would keep doubling every ~100 days. Demand grew fast, just not that fast. When the vendor financing unwound, bandwidth prices collapsed, ~85-95% of the lit fiber sat "dark," and the equipment makers were destroyed.

The lesson: **the fiber was real, the internet was real, and the traffic did eventually arrive.** The overbuild was a real bubble *and* the infrastructure it left behind subsidized the next decade of the web. Vendor-financed capacity ahead of demand is the pattern repeating now with GPUs and data centers.

## The accounting fault line: GPU depreciation

The bear case's sharpest empirical claim is about depreciation. Michael Burry (2025-26, a **disclosed short position, not neutral analysis, E1**) argues hyperscalers depreciate GPUs over **5-6 year book schedules** while real economic useful life is **~2-3 years** (obsolescence with each Nvidia generation, plus thermal wear at 100% utilization). A longer schedule understates depreciation expense, which mechanically flatters earnings. Burry's estimate: **~$176B of overstated earnings across the big players 2026-28**, with Oracle and Meta profits potentially overstated ~27% and ~21% respectively by 2028. Nvidia's rebuttal is that customers see 4-6 year utilization in practice.

This decides whether the buildout is profitable. It's the crux shared with [[Deep Dive - The AI Compute Buildout]]. If Burry is right, reported hyperscaler AI margins are partly an artifact of depreciation policy. If Nvidia is right, they're real. As of mid-2026 it's unresolved.

## The bull specifics

The bull case rests on a measured cost curve and a demand mechanism, not on "trust us."

- **Inference cost fell ~1000x in three years (E2, provider price histories).** GPT-4-class output ran ~$30/M tokens in March 2023. By 2026 comparable quality costs under ~$0.50/M, and often ~$0.05-0.10/M from open-weight hosts. a16z's "LLMflation" analysis puts the sustained pace at ~10x/yr for a fixed quality bar. Each order-of-magnitude price drop is a Jevons event: it opens use cases that weren't economic before, so *demand expands as price falls*. That's the core of [[Concept - Token Price Deflation]].
- **Revenue is growing fast in absolute terms**, even while it trails capex. The gap is a ratio problem, not a zero-revenue problem.
- **The MIT NANDA "95% of pilots show no P&L impact" finding (E2, "The GenAI Divide," 2025, ~150 executive interviews / 350-employee survey / 300 deployments, against $30-40B enterprise GenAI spend)** gets cited as a bear point but cuts the other way. NANDA's authors blame *pilot approach*, not model capability: the 5% that worked bought focused solutions and set KPIs. That's a deployment-execution problem, not a technology ceiling. See [[Concept - The Pilot-to-Production Gap]].

## The three-question framework

People argue one question while thinking about another. Separate them:

```mermaid
flowchart TD
    A[The AI buildout] --> Q1{Q1: Bubble in EQUITIES?<br/>Are public AI stocks priced<br/>above any defensible cashflow?}
    A --> Q2{Q2: Bubble in REAL CAPEX?<br/>Is physical spend running<br/>ahead of absorbable demand?}
    A --> Q3{Q3: Does the TECHNOLOGY work?<br/>Does AI deliver real,<br/>growing economic value?}
    Q1 --> R[Any combination of<br/>YES/NO is possible]
    Q2 --> R
    Q3 --> R
    R --> I[Internet c.2000:<br/>Q1 YES, Q2 YES, Q3 YES<br/>— all three at once]
```

**Walk a claim through it.** "Nvidia is overvalued" is a Q1 statement and says nothing about Q3. "There's too much data-center capex" is Q2 and says nothing about Q1 or Q3. "AI is useless hype" is a Q3 claim that most evidence contradicts whatever the answers to Q1/Q2. The dot-com era proves all three can be YES at once: pets.com was a real equity bubble, the fiber overbuild was a real capex bubble, *and* the internet reshaped the entire economy. Mixing the three up is the error.

**What to track**, quarter over quarter:

| Signal | Bubble-unwind reading | Boom reading | Tier |
|---|---|---|---|
| Revenue / capex ratio | Falling; gap widening | Stabilizing / rising | E1/E2 |
| Circular-financing share of "demand" | Rising toward the $800B loop | Third-party revenue growing | E1/E2 |
| GPU depreciation reality | Real life ≪ book life (Burry) | Utilization holds 4-6 yr (Nvidia) | E1 |
| Real usage: tokens served, DAU | Flat/declining | Still ~10x-ing | E2 |
| Token price vs demand | Price falling, demand *not* expanding | Jevons holds — demand expands | E2 |

If the top three deteriorate together while usage stalls, that's an unwind. If usage keeps compounding while the financing normalizes, it's a boom that ran ahead of its revenue.

## Evolution

In 2023 the debate was binary: hype vs skepticism. Cahn's 2023-24 "$200B → $600B" reframing turned it into a *timing* question (capital ahead of revenue). Through 2025-26 the center of gravity moved to the accounting layer, GPU depreciation and circular financing, because that's where the numbers can actually be contested and where an unwind would show first. The likely next phase is empirical. The OpenAI/Anthropic IPO cycle and hyperscaler segment reporting will, for the first time, put real AI-segment margins in public view, which neither the $600B question nor the depreciation debate could settle from outside. The successor question to "bubble or boom" is "whose balance sheet holds when the timing gap is longest?" That's a [[Reference - AI Market Sizing Claims]] and [[Concept - Unit Economics of LLM Products]] problem, not a vibes problem.

## Failure modes

- **Conflating the three questions** (above). This is the master error. "It's a bubble, therefore AI is fake" doesn't follow.
- **Averaging forecasts into mush.** Don't split the bear (Covello, Burry) and bull (Jevons/deflation) cases down the middle. Both are conditional on the depreciation and revenue/capex facts. Track the facts instead of averaging the opinions (per the [[Reference - The AI Forecasting Track Record]] discipline).
- **Mistaking timing risk for thesis risk.** The buildout runs years ahead of demand, so a 12-18 month demand air pocket can trigger a *financial* unwind without disproving the *technology*; see [[Deep Dive - The AI Compute Buildout]].
- **Taking any single number at face value.** Every headline here is tiered E1/E2 and often walked back. Cahn's own conclusion isn't "bubble." Covello is contested inside his own bank. Burry holds a disclosed short. Provenance matters as much as the number.

## The non-obvious

Practitioners learn this the hard way: **a real bubble tells you nothing about whether the technology is useful.** Reasoning "capex is irrational, so AI won't matter" gets it backwards. The internet was a real bubble and *still* reshaped the economy, and the fiber laid during that bubble is what made YouTube possible five years later.

If you're deploying AI, the equities question (Q1) and even the capex question (Q2) barely matter to you. Only Q3, whether it delivers value in *your* task, should drive decisions. The market can be in a bubble while your use case is one of the 5% with real ROI. And a roaring market says nothing about whether your thin-wrapper product survives; for that, see [[Concept - Moats in the AI Application Layer]] and [[Concept - What Stays Valuable Through Any Scenario]]. Be agnostic about the bubble and strict about the use case.

## Connections
- [[Deep Dive - The AI Compute Buildout]] — the physical/engineering companion; the depreciation and power facts that make the finance question concrete.
- [[Deep Dive - Circular Financing in the AI Buildout]] — the frontier-level deep treatment of the vendor-financing deal structures summarized here.
- [[Concept - Token Price Deflation]] — the ~10x/yr cost curve that powers the Jevons demand engine at the heart of the bull case.
- [[Breakdown - Frontier Lab Economics]] — the lab P&L detail (burn, gross margin) that the revenue/capex gap is measured against.
- [[Concept - Unit Economics of LLM Products]] — whether individual products clear a margin is the microfoundation of the macro question.
- [[Reference - AI Market Sizing Claims]] — the demand-side numbers (TAM estimates) whose credibility the $600B gap tests.
- [[Concept - The Pilot-to-Production Gap]] — the MIT 95%-fail finding is about deployment execution, not capability; it belongs on the bull side.
- [[Concept - Moats in the AI Application Layer]] — a boom does not save an undefensible position; this is what survives either way.
- [[Concept - The Data Wall]] — a supply-side constraint that, if it binds, changes the demand curve the capex is betting on.
- [[Concept - What Stays Valuable Through Any Scenario]] — the practitioner's answer to "which world are we in": positions robust to both.
- [[Reference - The AI Forecasting Track Record]] — why you track facts (revenue/capex, depreciation) rather than average pundit opinions.
- [[Concept - The AGI Timeline Debate]] — the capability-timeline question is orthogonal to the market question; conflating them is the master error.
- [[Reference - The 2026 Navigation Cheatsheet]] — the no-regret moves that hold in both bubble and boom.
- [[Lore - Failed AI Predictions]] — the graveyard of confident calls on both the hype and the "AI winter" sides.
- [[Reference - AI Impact by Business Function]] — where real, measurable revenue is actually landing, function by function.
- [[Concept - Cost Engineering for LLM Applications]] — the discipline that converts the deflating cost curve into an actual margin.
- [[Concept - Scaling Laws]] — the technical premise (capability rises with compute) that the entire capex bet capitalizes.
- [[Reference - The Open Questions Ledger]] — "bubble or boom?" is tracked there as a live, unresolved question with resolution criteria.

## Sources
- Cahn, D. (2023, 2024) — "AI's $200B/$600B Question," Sequoia Capital. The canonical statement of the capex-revenue gap and its 4x TCO/margin derivation.
- Covello, J. et al. (2024) — "Gen AI: Too Much Spend, Too Little Benefit?", Goldman Sachs Research. The bank-skeptic $1T "little to show for it" view; contested internally.
- Bloomberg and others (2026) — reporting on Nvidia/OpenAI/Oracle circular financing, ~$800B+ in arrangements. Demand-inflation and unwind-magnification mechanics.
- Burry, M. (2025-26) — public commentary on GPU depreciation (2-3yr vs 5-6yr) and ~$176B earnings overstatement; disclosed short position.
- MIT Project NANDA (2025) — "The GenAI Divide: State of AI in Business 2025." 95% of pilots show no P&L impact; failure attributed to approach, not capability.
- a16z (2024-25) — "LLMflation": ~10x/yr inference-cost decline for a fixed quality bar.
- Historical: late-1990s telecom fiber overbuild and vendor financing (Lucent/Nortel/CLECs) — the closest structural analog.
