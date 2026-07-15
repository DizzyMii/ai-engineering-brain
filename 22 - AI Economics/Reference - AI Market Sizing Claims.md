---
tags: [reference, domain/ai-economics, level/core]
aliases: [AI market size, AI TAM claims, gen AI economic value estimates]
summary: "Tiered lookup of major AI market-size, value, and ROI claims with source, date, and the methodology catch that makes each easy to misread."
---
# Reference - AI Market Sizing Claims

> Reading rule before using any number below: every figure here is **E1 at best** (an estimator's model, not a measurement). Check who paid for it, what year it targets, and — critically — which of three different things it measures: **value/productivity** (economic surplus an AI use creates, e.g. cost saved or output gained), **market/revenue** (what AI vendors sell), or **spend/capex** (what buyers or infrastructure owners pay out). Headlines routinely conflate all three into one number. None of these figures should be averaged together or laundered into a single "the AI market is worth $X" fact.

## Macro value / market-size claims

| Claim | Source | Date published | Tier | What it actually measures | Methodological catch |
|---|---|---|---|---|---|
| Gen AI could add **$2.6T–$4.4T/yr** in economic value across 63 use cases (net of overlaps, $6.1T–$7.9T/yr including broader productivity effects) | McKinsey Global Institute, "The economic potential of generative AI" | Jun 2023 | E1 | Value/productivity — potential cost saved or output gained by *deploying* enterprises, ~75% concentrated in customer ops, marketing/sales, software engineering, R&D | A theoretical ceiling from task-automation modeling, not observed spend or revenue; routinely misquoted as "the AI market is worth $4.4T" |
| AI could add **$15.7T** to global GDP by 2030 (~14% higher GDP) | PwC, "Sizing the Prize" | 2017 (still cited through 2026) | E1 | Value/productivity — GDP-level macro model, >50% from labor-productivity gains, the rest from AI-driven consumer demand | Predates the 2022-2023 generative-AI wave entirely; a general-AI GDP model retrofitted into gen-AI headlines |
| Generative AI market reaches **$1.3T by 2032** → revised to **$1.8T** (Mar 2025) → revised to **$2.3T** (Jun 2026) | Bloomberg Intelligence | Jun 2023 / Mar 2025 / Jun 2026 | E1 | Market/revenue — vendor sales across hardware, software, services, ads, gaming tied to gen AI | The three successive revisions in three years (+77% cumulative) show how fast a single estimator's own model moves; present as a trend line, never just the latest number |

## The revenue-reality gap

| Claim | Source | Date | Tier | Note |
|---|---|---|---|---|
| AI infrastructure spend implies **~$600B/yr** in AI revenue is needed to justify the capex (up from a **$200B** estimate a year earlier) | Sequoia Capital, David Cahn, "AI's $600B Question" | Jun 2024 (updates a Sep 2023 "$200B" piece) | E1 | Back-of-envelope: 2× Nvidia data-center run-rate (Nvidia ≈ half of data-center TCO) × 2× (infra needs ~50% gross margin to pencil); the gap between this figure and actual AI revenue is the bear case's central number — see [[Deep Dive - Circular Financing in the AI Buildout]] |
| OpenAI booked **~$13.1B** revenue in 2025, reaching **~$25B** annualized run-rate by Feb 2026 | Company disclosures via reporting (Epoch AI, press) | 2025-2026 | E2 | Actual revenue anchor, not a market estimate — useful for sanity-checking TAM claims against what one leading vendor actually collects |
| Anthropic's annualized run-rate rose from **~$1B** (Jan 2025) to **~$30B** (Apr 2026) to **~$47B** (mid-May 2026, reported) | Epoch AI tracking, press reporting | 2025-2026 | E2 | A ~30x run-rate increase in 16 months, driven substantially by Claude Code coding-agent usage; illustrates how fast a single company's actuals can move relative to any static market-size estimate |

Total disclosed app-and-lab-layer revenue across the industry remains a small fraction — low single-digit percent — of the multi-hundred-billion-dollar annual compute capex being deployed by hyperscalers in 2026 (~$725-750B hyperscaler capex projected for 2026, analyst tallies vary — Bloomberg Intelligence, Jun 2026; PitchBook/hyperscaler guidance, E1). That gap *is* Cahn's $600B question, restated.

## ROI claims

| Claim | Source | Date | Tier | Note |
|---|---|---|---|---|
| Organizations report **$3.70 returned per $1** spent on gen AI on average; top 5% of performers report **>$10 per $1** | IDC, commissioned by Microsoft, survey of ~4,000 leaders | Jan 2025 | E1 | Vendor-sponsored self-report survey, not an audited outcome measure — state with "(Microsoft-commissioned)" attached every time it's cited |
| **~95%** of generative AI pilots show **no measurable P&L impact**; just 5% of integrated pilots extract most of the value | MIT Project NANDA, "The GenAI Divide: State of AI in Business 2025" (150 interviews, 350-employee survey, 300 deployments analyzed) | Jul-Aug 2025 | E2 | The direct counter-evidence to the IDC figure above — same claimed universe (enterprise gen-AI ROI), opposite conclusion; the divide is attributed to integration/workflow-retention approach, not model quality |

**Contested-claims rule applied:** IDC's $3.70-per-$1 and MIT NANDA's 95%-no-impact are not reconcilable into an average — they measure different populations with different incentives (a vendor-commissioned survey of self-selected AI adopters vs. an independent audit of deployments including failures) and neither should be cited without the other in the same breath. See [[Playbook - Measuring AI ROI]] for how to produce a number for your own deployment instead of citing either.

## Reading checklist

- **Who paid for it.** McKinsey, PwC, Bloomberg Intelligence are independent analyst/consultancy estimates (E1); IDC's ROI figure above is vendor-commissioned (E1, flag explicitly); actual revenue disclosures (OpenAI, Anthropic) are the only entries here above E1.
- **What year and what's included.** "By 2030," "by 2032," "annually" targets differ by a decade across these claims — never compare figures with different target years as if simultaneous.
- **Value vs. market vs. spend.** McKinsey/PwC measure value created for *users* of AI; Bloomberg measures revenue captured by *vendors* of AI; Cahn's $600B measures required revenue to justify *capex*. A 10x swing in "the AI market's size" is often just three different definitions of "the AI market."
- **Gen AI vs. all AI.** Several widely-quoted figures (PwC 2017, some McKinsey citations) predate or exceed the scope of the 2022+ generative-AI wave; check the underlying report, not just the headline.

## Connections

- [[Reference - The AI Forecasting Track Record]] — how analyst forecasts like these have historically performed against realized outcomes.
- [[Deep Dive - Bubble or Boom]] — whether the capex implied by these figures is sustainable if realized revenue stays below the $600B line.
- [[Concept - The Pilot-to-Production Gap]] — the organizational mechanism behind MIT NANDA's 95% no-impact finding.
- [[Reference - AI Impact by Business Function]] — the McKinsey-style value estimates broken down by function rather than aggregated into one headline number.
- [[Concept - Value Capture Across the AI Stack]] — why value/market/spend diverge structurally across the stack's layers.
- [[Breakdown - Frontier Lab Economics]] — the lab-layer cost structure behind OpenAI's and Anthropic's actual revenue figures cited above.
- [[Deep Dive - Circular Financing in the AI Buildout]] — the capex-financing mechanics that make Cahn's $600B gap dangerous rather than merely academic.

## Sources

- McKinsey Global Institute, "The economic potential of generative AI: The next productivity frontier" (Jun 2023).
- PwC, "Sizing the Prize" (2017).
- Bloomberg Intelligence, generative AI market-size research (Jun 2023; update Mar 2025; update "Generative AI 2026 Outlook," Jun 2026).
- Sequoia Capital, David Cahn, "AI's $200B Question" (Sep 2023) and "AI's $600B Question" (Jun 2024).
- Epoch AI, AI company revenue tracking (2025-2026); press reporting on OpenAI and Anthropic run-rate.
- IDC, "The Business Opportunity of AI," commissioned by Microsoft (Jan 2025).
- MIT Project NANDA, "The GenAI Divide: State of AI in Business 2025" (Jul-Aug 2025).
