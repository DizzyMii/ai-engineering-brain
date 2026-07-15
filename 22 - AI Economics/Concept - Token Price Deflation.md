---
tags: [concept, domain/ai-economics, level/surface]
aliases: [LLMflation, inference price deflation]
summary: "The rapid, sustained fall in the price of a fixed-quality unit of LLM inference (~10x/yr), and what it does to AI business models."
---
# Concept - Token Price Deflation

> **One-paragraph hook:** Hold model quality constant and watch the price of a million tokens fall by roughly an order of magnitude every year — a rate of deflation with no real precedent in consumer technology pricing. This single fact reshapes AI business models on both sides: it turns cost-plus token pricing into a melting ice cube, and it turns inference-heavy features that are uneconomical today into features that ship on a predictable delay. Anyone pricing an AI product, or deciding whether to build a feature, is implicitly betting on where this curve will be in twelve months.

## The mechanism

a16z's Guido Appenzeller coined **"LLMflation"** (Nov 2024, E1 — an analyst framing built on his own price comparison, not a controlled study) to describe the finding: for a model of *fixed quality* (measured by benchmark score, e.g., MMLU), the $/million-token price has fallen roughly **10x per year** for three consecutive years (2021-2024). Concretely, the price to run a GPT-3-quality model (MMLU ≈ 42) fell from **$60/M tokens in November 2021** (GPT-3 via OpenAI) to **$0.06/M tokens in November 2024** (Llama 3.2 3B via Together.ai) — a **1,000x** decline in three years (E2, a16z analysis of published price lists, Nov 2024).

Three mechanisms drive the curve, compounding rather than substituting for each other:

1. **Hardware $/FLOP** improves generation over generation (Hopper → Blackwell), and inference-specific silicon (custom ASICs, better memory bandwidth) lowers the cost floor for serving any given model size.
2. **Algorithmic efficiency** — [[Concept - Knowledge Distillation]] compresses frontier capability into smaller models cheaper to serve; [[Concept - Post-Training Quantization Formats]] shrinks memory footprint and increases arithmetic throughput per GPU; better [[Concept - Attention Mechanism]] variants and serving techniques (batching, caching) raise achievable throughput per dollar of compute.
3. **Competition and open weights** force labs to price near marginal cost rather than value-based pricing, because a near-parity open-weight substitute caps what any lab can charge for a given capability tier.

Epoch AI's more granular 2025 analysis (E2, single research organization) found the deflation rate is not one number — it ranges from **9x to 900x per year** (median ~50x/year) depending on which capability milestone is held fixed: commodity-tier tasks (simple classification, short-form summarization) deflate fastest because many providers compete to serve them cheaply, while frontier-tier capability (the newest reasoning benchmarks) deflates slowest because only a handful of labs can serve it at all, and they price to their scarcity rather than to marginal cost.

## In practice

**The public price history is the visible proof.** GPT-4 launched in March 2023 at **$30/M input, $60/M output tokens** (E3, OpenAI published pricing). GPT-4o (2024) priced at **$2.50/M input, $10/M output** — an 8-12x drop at (roughly) comparable frontier capability within about 18 months (E3, OpenAI published pricing). GPT-4o-mini undercut that further to **$0.15/M input, $0.60/M output** (E3, OpenAI published pricing). By 2026, open-weight models at GPT-4-launch-era quality — DeepSeek V3, Llama 3.3 70B — serve under **$0.50/M tokens** through third-party inference providers (E2, provider price lists), a **>60x** drop from the March 2023 frontier price at a similar capability tier.

**The DeepSeek shock quantified the competitive-pressure channel.** DeepSeek's January 2025 release (R1, and the V3 base model) crystallized a "cheap frontier is possible" narrative sharply enough to wipe **$589 billion off Nvidia's market capitalization in a single trading day** (Jan 27, 2025) — the largest single-day market-cap loss in stock market history at the time (E3, multiple outlets: Bloomberg, Forbes, Yahoo Finance, Jan 27, 2025). The proximate cause was DeepSeek's claimed training cost of **~$5.6M** for the V3 base model, against Western frontier training runs reported in the $100M+ range — triggering a repricing of expectations about how much compute frontier capability actually requires. Whether DeepSeek's reported training cost captures the full picture (it excludes prior research, prior model runs, and hardware capex) is contested and should be read as a single-source, company-reported figure (E2), not an audited total-cost-of-ownership number.

**Business consequence #1 — cost-plus token pricing is a melting ice cube.** Any product margin that depends on today's per-token cost staying flat evaporates within a year, because a competitor (or the same lab's next model tier) will serve equivalent quality at a fraction of the price. See [[Concept - Unit Economics of LLM Products]] for how this plays out at the query level.

**Business consequence #2 — Jevons paradox offsets the price collapse on the demand side.** Satya Nadella invoked the 160-year-old **Jevons paradox** on Jan 27-28, 2025 in direct response to the DeepSeek shock (E2, Nadella's own public statement) — cheaper compute-per-unit-of-intelligence expands total usage faster than the price falls, so aggregate AI spend can rise even as unit price collapses. The pattern shows up in the top-line numbers: GPT-3.5-level query pricing fell roughly 280x between November 2022 ($20/M tokens) and October 2024 ($0.07/M tokens), while enterprise generative-AI spending grew from an estimated $1.7B (2023) to $37B (2025) — a ~22x increase over the same window that per-token prices fell >90% (E1, figures compiled via Stanford AI Index-referenced estimates and industry spend trackers; spend figures are modeled estimates, treat as E1). Price and volume moved in opposite directions simultaneously; neither number alone tells the demand story.

## Failure modes

- **Pricing a feature off today's token cost and getting undercut by your own vendor.** A team that ships a feature priced to be marginally profitable at current API rates finds the same model's price cut by 80% eighteen months later — competitors who waited now serve the same feature at a fifth of the cost, or the team's own margin balloons in a way that invites a price war they didn't plan for.
- **Assuming deflation applies uniformly.** Per Epoch AI, frontier-capability tasks deflate 9x/year while commodity tasks deflate 900x/year — a product built on the newest reasoning tier should not budget as if its costs will fall at the commodity-tier rate; it will overspend against its own forecast.
- **Reading DeepSeek's $5.6M figure as the full training cost and drawing conclusions about frontier lab economics from it.** The figure is a single-source, self-reported final-run cost that excludes prior research and infrastructure capex; treating it as comparable to a fully-loaded frontier training budget understates true compute requirements. See [[Breakdown - Frontier Lab Economics]].

## The non-obvious

Deflation is measured **per quality level held fixed, not per token you're actually buying.** Practitioners routinely misread "GPT-3-quality tokens are 1,000x cheaper" as "my AI bill will fall 1,000x" — but frontier users don't stay on GPT-3-quality models; they migrate to whatever the newest, most expensive capability tier is, because that's where competitive advantage lives. This is why frontier labs' revenue has grown even as their own per-token prices for any *fixed* model have fallen: customers keep re-purchasing the top of the price ladder rather than riding a fixed model down the cost curve. The deflation curve is a curve you can only capture the savings from if you're willing to *not* upgrade — and almost nobody in a competitive market chooses that.

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
