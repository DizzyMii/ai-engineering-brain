---
tags: [concept, domain/ai-economics, level/surface]
aliases: [LLMflation, inference price deflation]
summary: "The rapid, sustained fall in the price of a fixed-quality unit of LLM inference (~10x/yr), and what it does to AI business models."
---
# Concept - Token Price Deflation

> Hold model quality constant and the price of a million tokens falls by roughly an order of magnitude every year. Consumer technology pricing has no real precedent for that rate. It reshapes AI business models on both sides. Cost-plus token pricing becomes a melting ice cube, and inference-heavy features that don't pay today ship on a predictable delay. Anyone pricing an AI product, or deciding whether to build a feature, is betting on where this curve will be in twelve months, whether they say so or not.

## The mechanism

a16z's Guido Appenzeller coined **"LLMflation"** (Nov 2024, E1; an analyst framing built on his own price comparison, not a controlled study). The finding: for a model of *fixed quality* (measured by a benchmark score such as MMLU), the $/million-token price fell roughly **10x per year** for three straight years (2021-2024). Running a GPT-3-quality model (MMLU ≈ 42) cost **$60/M tokens in November 2021** (GPT-3 via OpenAI) and **$0.06/M tokens in November 2024** (Llama 3.2 3B via Together.ai). That's a **1,000x** drop in three years (E2, a16z analysis of published price lists, Nov 2024).

Three mechanisms drive the curve, and they compound:

1. **Hardware $/FLOP** improves each generation (Hopper → Blackwell), and inference-specific silicon (custom ASICs, better memory bandwidth) lowers the cost floor for serving any given model size.
2. **Algorithmic efficiency.** [[Concept - Knowledge Distillation]] packs frontier capability into smaller models that are cheaper to serve. [[Concept - Post-Training Quantization Formats]] shrink memory footprint and raise arithmetic throughput per GPU. Better [[Concept - Attention Mechanism]] variants and serving techniques (batching, caching) raise throughput per dollar of compute.
3. **Competition and open weights** push labs to price near marginal cost instead of on value, because a near-parity open-weight substitute caps what any lab can charge for a capability tier.

Epoch AI's more granular 2025 analysis (E2, single research organization) found the rate isn't one number. It ranges from **9x to 900x per year** (median ~50x/year) depending on which capability milestone is held fixed. Commodity-tier tasks (simple classification, short summarization) deflate fastest because many providers compete to serve them cheaply. Frontier-tier capability (the newest reasoning benchmarks) deflates slowest, because only a handful of labs can serve it at all and they price to scarcity instead of marginal cost.

## In practice

**Public price history is the visible proof.** GPT-4 launched in March 2023 at **$30/M input, $60/M output tokens** (E3, OpenAI published pricing). GPT-4o (2024) came in at **$2.50/M input, $10/M output**, an 8-12x drop at roughly comparable frontier capability within about 18 months (E3, OpenAI published pricing). GPT-4o-mini undercut that to **$0.15/M input, $0.60/M output** (E3, OpenAI published pricing). By 2026, open-weight models at GPT-4-launch-era quality, such as DeepSeek V3 and Llama 3.3 70B, serve for under **$0.50/M tokens** through third-party inference providers (E2, provider price lists). That's a **>60x** drop from the March 2023 frontier price at a similar capability tier.

**The DeepSeek shock put a number on competitive pressure.** DeepSeek's January 2025 release (R1, and the V3 base model) made "cheap frontier is possible" vivid enough to wipe **$589 billion off Nvidia's market capitalization in a single trading day** (Jan 27, 2025), the largest one-day market-cap loss in stock market history at the time (E3, multiple outlets: Bloomberg, Forbes, Yahoo Finance, Jan 27, 2025). The trigger was DeepSeek's claimed training cost of **~$5.6M** for the V3 base model, against Western frontier training runs reported at $100M+. Expectations about how much compute frontier capability needs got repriced. Whether DeepSeek's number captures the full picture is contested, since it excludes prior research, earlier model runs and hardware capex. Read it as a single-source, company-reported figure (E2), not an audited total cost of ownership.

**Business consequence #1: cost-plus token pricing is a melting ice cube.** A margin that depends on today's per-token cost staying flat evaporates within a year. A competitor, or the same lab's next model tier, will serve equivalent quality at a fraction of the price. [[Concept - Unit Economics of LLM Products]] shows how this plays out at the query level.

**Business consequence #2: Jevons paradox offsets the collapse on the demand side.** Satya Nadella invoked the 160-year-old **Jevons paradox** on Jan 27-28, 2025 in direct response to the DeepSeek shock (E2, Nadella's own public statement). Cheaper compute per unit of intelligence expands total usage faster than the price falls, so aggregate AI spend can rise while unit price collapses. The top-line numbers show it. GPT-3.5-level query pricing fell roughly 280x between November 2022 ($20/M tokens) and October 2024 ($0.07/M tokens). Over the same window, enterprise generative-AI spending grew from an estimated $1.7B (2023) to $37B (2025), a ~22x increase while per-token prices fell >90% (E1, figures compiled via Stanford AI Index-referenced estimates and industry spend trackers; spend figures are modeled estimates, treat as E1). Price and volume moved in opposite directions at the same time, and neither number alone tells the demand story.

## Failure modes

- **Pricing a feature off today's token cost and getting undercut by your own vendor.** A team ships a feature priced to be marginally profitable at current API rates. Eighteen months later the same model's price is cut by 80%. Competitors who waited now serve the same feature at a fifth of the cost, or the team's own margin balloons in a way that invites a price war it didn't plan for.
- **Assuming deflation is uniform.** Per Epoch AI, frontier-capability tasks deflate 9x/year while commodity tasks deflate 900x/year. A product built on the newest reasoning tier shouldn't budget as if its costs will fall at the commodity rate, or it will overspend against its own forecast.
- **Reading DeepSeek's $5.6M as the full training cost** and drawing conclusions about frontier lab economics from it. It's a single-source, self-reported final-run cost that excludes prior research and infrastructure capex. Treating it as comparable to a fully loaded frontier training budget understates true compute requirements. See [[Breakdown - Frontier Lab Economics]].

## The non-obvious

Deflation is measured **per fixed quality level, not per token you actually buy.** People routinely read "GPT-3-quality tokens are 1,000x cheaper" as "my AI bill will fall 1,000x." But frontier users don't stay on GPT-3-quality models. They move to whatever the newest, most expensive capability tier is, because competitive advantage lives there. So frontier labs' revenue has grown even as their per-token prices for any *fixed* model fell: customers keep buying the top of the price ladder instead of riding one model down the cost curve. You only capture the savings if you're willing to *not* upgrade, and almost nobody in a competitive market makes that choice.

## Connections

- [[Concept - Unit Economics of LLM Products]] — the query-level mechanics of how falling token prices interact with rising token *volume* (reasoning models, agents) to determine whether margin actually improves.
- [[Breakdown - Frontier Lab Economics]] — how labs' own P&L absorbs the pressure to keep cutting prices while training costs keep rising.
- [[Decision - Build vs Buy vs Wrap]] — token deflation is a primary reason "build your own model" keeps losing to "buy" for most teams: the make-vs-buy crossover point moves further from you every year.
- [[Concept - Value Capture Across the AI Stack]] — deflation is the mechanism that compresses the model layer's share of stack-wide value capture.
- [[Concept - Moats in the AI Application Layer]] — why app-layer defensibility can't rest on model access once the underlying model is a deflating commodity.
- [[Deep Dive - Circular Financing in the AI Buildout]] — the tension between deflating per-token revenue and the capex commitments financing the compute that produces those tokens.
- [[Concept - The Capability-Reliability Gap]] — cheaper tokens fund more inference-time compute (retries, self-consistency, agents) as a way to buy reliability, which is part of why total spend rises even as unit price falls.
- [[Reference - The 2026 Navigation Cheatsheet]] — situates the deflation trend within the broader set of trends an operator should track through 2026.
- [[Concept - Post-Training Quantization Formats]] — one of the concrete serving-side mechanisms that lowers the cost floor driving deflation.
- [[Concept - Knowledge Distillation]] — the training-side mechanism that lets smaller, cheaper models approach frontier-quality output.
- [[Concept - Scaling Laws]] — the compute-quality relationship that defines what "fixed quality" costs to produce in the first place, i.e. the supply-side constraint the deflation curve is pushing against.

## Sources

- Andreessen Horowitz, "Welcome to LLMflation" (Guido Appenzeller, Nov 2024) — the 10x/year framing and the GPT-3-quality 1,000x/3-year data point.
- Epoch AI, "LLM inference prices have fallen rapidly but unequally across tasks" (2025) — the 9x-900x/year range by capability milestone.
- OpenAI, published API pricing (accessed 2026) — GPT-4, GPT-4o, GPT-4o-mini price points.
- Bloomberg, Forbes, Yahoo Finance — Nvidia $589B single-day market cap loss, Jan 27, 2025 (DeepSeek reaction coverage).
- Fortune, "What is Jevons paradox? The reason Satya Nadella says DeepSeek's new AI is good news for tech" (Jan 27, 2025).
