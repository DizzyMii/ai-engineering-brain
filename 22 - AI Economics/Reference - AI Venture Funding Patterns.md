---
tags: [reference, domain/ai-economics, level/advanced]
aliases: [AI Venture Funding Patterns, AI mega-rounds, AI VC concentration]
summary: "Lookup of AI mega-rounds, valuations, VC concentration, revenue multiples, strategic money, and secondaries — with tiers and reading rules."
---

# Reference - AI Venture Funding Patterns

## Mega-rounds and valuations (2025–2026)

| Company | Round | Post-money valuation | Date | Tier |
|---|---|---|---|---|
| OpenAI | $40B (SoftBank $30B + $10B syndicate) | $300B | Mar 2025 | E2 |
| OpenAI | ~$122B (Amazon ~$50B, Nvidia ~$30B, SoftBank ~$30B) | $852B post | Mar 31 2026 | E2 |
| OpenAI | prior tender/round | ~$157B → $300B → later $500B secondary talk | 2024–2026 | E2 |
| Anthropic | $3.5B Series E | $61.5B | Mar 2025 | E2 |
| Anthropic | $13B Series F (ICONIQ-led) | $183B | Sep 2025 | E2 |
| Anthropic | $30B Series G (GIC + Coatue-led) | **$380B** | Feb 2026 | E3 |
| xAI | multi-billion raises | ~$50B+ | 2025 | E1/E2 |
| Anysphere (Cursor) | $900M | $9.9B | Jun 2025 | E2 |

OpenAI's ~$122B round at $852B post (Mar 31, 2026) is the **largest private tech raise in history**, beating its own prior record of $40B at $300B post (Mar 2025; E2, Bloomberg/CNBC/TechCrunch). Anthropic's $30B Series G (Feb 12, 2026) is the **third-largest private tech round ever, after OpenAI's $122B (Mar 2026) and $40B (Mar 2025)**. It doubled Anthropic's valuation from $183B to $380B in five months (E3, Anthropic newsroom / CNBC / Crunchbase), and the speed of these marks is a signal in itself. SoftBank's OpenAI commitment was structured to drop to as low as $20B if OpenAI failed to restructure to for-profit by end-2025 (E2). Headline round size ≠ committed cash.

## VC concentration

| Metric | Figure | Date | Tier |
|---|---|---|---|
| AI share of GLOBAL VC dollars | **52.5%** ($192.7B of $366.8B) — first time AI took the majority | FY2025 | E2 (PitchBook) |
| AI share, broader measure | ~two-thirds of US capital invested | FY2025 | E1/E2 |
| AI share of US VC | ~86% of $412.7B | H1 2026 | E2 (PitchBook) |
| US total VC | record ~$267B (Q-level) / global total VC $366.8B FY2025 | 2025 | E2 |

A handful of foundation-model labs absorbed most of the AI dollars. That **inflates** headline VC totals and **starves** everything that isn't a frontier lab, both at once.

## Revenue multiples

| Asset class | Forward multiple (× run-rate ARR) | Tier |
|---|---|---|
| Frontier labs (OpenAI, Anthropic) | ~10–30× forward run-rate | E1 |
| App-layer breakouts (Cursor) | ~15–20× ARR | E1/E2 |
| Public SaaS comp (for contrast) | ~6–12× forward revenue | E3 |

Lab multiples run richer than SaaS norms. Growth rate and winner-take-most bets justify them, **not** profitability: none of these companies is profitable (see [[Breakdown - Frontier Lab Economics]]). Whether the multiples are sane depends on the forecasts in [[Reference - AI Market Sizing Claims]] actually materializing, which is the crux of [[Deep Dive - Bubble or Boom]].

## Strategic / vendor money (the "funding" that is really compute)

| Investor → investee | Amount | What it really is | Date | Tier |
|---|---|---|---|---|
| Nvidia → OpenAI | up to $100B | drawn as GPUs deploy; supplier funding customer | Sep 2025 | E2 |
| Nvidia → CoreWeave | ~$2B equity + $6.3B take-or-pay backstop | supplier + investor + demand backstop | 2025 | E2 |
| Microsoft → OpenAI | tens of $B (cash + Azure credits) | cloud-credit-heavy | 2023–2025 | E2 |
| SoftBank/Oracle/MGX → Stargate | $500B umbrella ($100B initial) | infra JV, spend commitment not cash raise | Jan 2025 | E2 |

Strategic capital blurs "funding," "revenue," and "spending commitment." When Nvidia invests in a lab that buys Nvidia chips, part of the "round" is effectively **pre-purchased GPU capacity**. [[Deep Dive - Circular Financing in the AI Buildout]] takes that mechanism apart. The CoreWeave structure is the debt half of AI funding, where [[Concept - GPU Depreciation and Compute Capex Accounting]] decides whether the GPU collateral holds its value.

## Secondaries and liquidity

| Mechanism | Example | Signal | Tier |
|---|---|---|---|
| Employee tender offers | OpenAI, Anthropic, Anysphere | paper value → cash without IPO | E2 |
| Structured strategic shares | SoftBank/Nvidia positions | valuation set by non-market-clearing buyers | E2 |

Tenders that turn equity into cash without an IPO mark a **private-market-heavy, IPO-light cycle**. Capital and liquidity both stay private, so public-market price discovery never checks the marks.

## Reading rules

1. A private "valuation" is the price of the *last* (often strategic, structured) share, not a market-clearing price. Treat lab valuations as **E1 signals**, not audited worth.
2. `raised ≠ revenue ≠ valuation`.[^1] Mixing up any two is the most common funding-headline error.
3. Since much 2025-26 capital is earmarked for compute, a "raise" is frequently a **spending commitment routed straight to the infra layer**: the money enters the app/model layer and leaves for Nvidia (see [[Concept - Value Capture Across the AI Stack]]).
4. Discount round sizes for structure: escrows, tranches, and conditionality (SoftBank's $40B→$20B clause) mean headline ≠ wired cash.
5. Stress-test every valuation against real revenue: the [[Concept - The Pilot-to-Production Gap]] is why the ARR behind these marks can stall. For primary data, track filings and the trackers in [[Reference - Where Real AI Knowledge Lives]], not press-reported round sizes.

[^1]: **raised** = capital committed to the company's balance sheet; **revenue** = sales to customers (ARR is annualized run-rate, not audited GAAP revenue); **valuation** = implied equity value from the marginal share price. A company can raise $13B, book $1B revenue, and be "worth" $183B at the same time: Anthropic in Sep 2025.

## Connections
- [[Breakdown - Frontier Lab Economics]] — where these raises go: funding the burn the multiples ignore.
- [[Deep Dive - Circular Financing in the AI Buildout]] — how strategic/vendor money loops through the same balance sheets.
- [[Concept - Value Capture Across the AI Stack]] — why raised capital exits the model/app layer toward silicon.
- [[Reference - AI Market Sizing Claims]] — the market forecasts these valuations are implicitly priced against.
- [[Deep Dive - Bubble or Boom]] — the scenario question the concentration and multiples feed.
- [[Concept - GPU Depreciation and Compute Capex Accounting]] — GPU-backed debt (CoreWeave) is the debt half of this funding picture.
- [[Concept - The Pilot-to-Production Gap]] — the revenue-reality check against which these valuations are stress-tested.
- [[Reference - Where Real AI Knowledge Lives]] — where to track primary funding data (PitchBook, CB Insights, filings).

## Sources
- PitchBook (Jan/Apr 2026) — US VC 2025: AI 52.5% of dollars ($192.7B/$366.8B); H1 2026 ~86%. E2.
- CNBC / TechCrunch / Bloomberg (Mar 31, 2025) — OpenAI $40B at $300B post, largest private raise. E2.
- TechCrunch / Anthropic (Sep 2, 2025) — $13B Series F at $183B, up from $61.5B (Mar 2025). E2.
- Anthropic newsroom / CNBC / Axios / Crunchbase (Feb 12, 2026) — $30B Series G at $380B post, GIC + Coatue-led; second-largest private tech round; company-disclosed ~$14B run-rate. E3.
- CNBC / NVIDIA (Sep 22, 2025) — Nvidia up-to-$100B in OpenAI, drawn per gigawatt. E2.
- Quartz / Forbes (2026) — CoreWeave GPU-backed debt (>$21B total, ~$7.5B GPU-collateralized), Nvidia $2B equity + $6.3B backstop. E2.
- OpenAI (Jan 2025) — Stargate $500B / $100B initial. E2 (announcement).
