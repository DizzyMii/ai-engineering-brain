---
tags: [concept, domain/ai-economics, level/surface]
aliases: [value capture, picks and shovels, layer-cake model]
summary: "Maps where money actually accrues across the AI stack and why the profit pool sits upstream of where most economic value is created."
---
# Concept - Value Capture Across the AI Stack

> **One-paragraph hook:** An enterprise AI dollar passes through five layers (silicon, cloud/neocloud, foundation-model lab, application, distribution), and each takes a cut before the next sees the money. As of 2026 the fattest, most durable margins sit at the bottom (chips) and the thinnest, most contested ones in the middle (models). Most of the *economic value* created lands with neither. It lands with the enterprises buying the tokens. Picking where to build, or what to build on, means picking a position in this stack, and that position sets your margin ceiling before a single feature ships.

## The mechanism

Five layers, each buying from the one below and selling to the one above:

1. **Silicon**: Nvidia, AMD, TSMC (fab), Broadcom (custom ASICs). Sells compute capacity at hardware margins.
2. **Cloud / neocloud**: AWS, Azure, GCP, plus GPU-specialist neoclouds (CoreWeave, Lambda, Crusoe). Buys chips and rents them out as compute-hours.
3. **Foundation-model labs**: OpenAI, Anthropic, Google DeepMind, Meta, DeepSeek. Buys compute, trains models, sells tokens via API (or gives weights away).
4. **Application layer**: Cursor, Harvey, every SaaS company bolting on LLM calls. Buys tokens, sells a workflow.
5. **Distribution**: the channel that reaches the end user (an IDE, a browser, an OS, an app store). Often folded into the app layer, but distinct when a platform such as an OS vendor collects rent just for being the door the user walks through.

Pricing power flows downward and cost flows upward. Nvidia sets GPU prices largely on its own terms in a supply-constrained market. Clouds mark that up into compute-hours. Labs buy compute as their largest COGS line and sell tokens at whatever margin the market allows. Apps buy tokens as *their* largest COGS line and sell a subscription or seat at whatever the customer will pay. Each layer takes the price on its inputs and (weakly) sets it on its outputs. Silicon is the exception: it faces the least competition, so it sets price on both sides.

The FY2025 numbers show it. Nvidia's Data Center segment posted **$115.2B in revenue** for fiscal 2025 (ended Jan 26, 2025) at a company-wide **75.0% gross margin**, up from 72.7% a year earlier (E3, Nvidia FY2025 10-K, SEC filing, Feb 2025). Nothing else in the stack has a margin structure like that. At the application layer, Bessemer's *State of AI* work puts LLM-native gross margins around **65%** (E2, Bessemer, 2025), and ICONIQ Capital's January 2026 bi-annual survey of AI-native companies put average product gross margin at **52%**, up from 41% in 2024 and 45% in 2025 (E2, ICONIQ, single survey). That's improving, but still well under the 80-90% that defined SaaS. [[Concept - Unit Economics of LLM Products]] explains why the app-layer number sits lower than legacy software.

## In practice

### Picks and shovels

In a gold rush the surest returns go to whoever sells shovels. In the 2023-2026 AI buildout the reliably profitable position has been compute supply: Nvidia, TSMC, and (more speculatively, on thinner public data) neoclouds like CoreWeave. Every layer above has to buy from them whichever model or app wins. a16z's "Who Owns the Generative AI Platform?" (Bornstein et al.: Matt Bornstein, Guido Appenzeller, Martin Casado, Jan 2023, E1, a thesis piece and not measured data) argued infrastructure would capture the most durable value, since apps face retention and margin pressure while models commoditize. By 2026 that has aged well directionally, though the app layer produced faster-growing outliers than the thesis implied (below).

### Model-layer commoditization

[[Concept - Token Price Deflation]] and open-weight parity (DeepSeek's R1/V3 family, Meta's Llama line) have cut the pricing power labs hold over apps. GPT-4 cost $30/M input tokens at frontier quality in March 2023; by 2026 there's an open-weight, near-parity substitute under $0.50/M. Once what a layer sells becomes a commodity, it gets squeezed from below (compute costs fall slower than token prices) and from above (customers won't pay extra for a fungible token).

Call it the **"thin-margin sandwich"**. App companies buy inference cost-plus from labs, who buy GPUs from Nvidia at hardware margins. Each layer's pricing power leans on the one below, so an app's margin ceiling is set by forces two layers away from its own product. [[Concept - Moats in the AI Application Layer]] covers how apps get out by owning something other than the model call.

### Counter-evidence: apps can still win fast

Cursor (Anysphere) crossed **$100M ARR in January 2025** and **$500M+ ARR by June 2025**, closing a $900M Series C at a **$9.9B valuation** (E2, TechCrunch, June 2025), one of the fastest revenue ramps recorded in software. That's real evidence against a strict "apps can't capture value" reading of picks-and-shovels. But Cursor's growth ran almost entirely on other labs' compute (Anthropic and OpenAI model calls). It shows an app can capture *revenue* fast. It doesn't show a durable *margin* independent of what those labs charge next quarter. Mechanism in [[Breakdown - The Cursor Ramp]].

## Failure modes

- **Confusing value creation with value capture.** McKinsey estimates generative AI could add **$2.6-4.4 trillion/year** in economic value across 63 use cases (E1, McKinsey Global Institute, 2023, since referenced and updated through 2025-2026). That's cost saved or output gained by the *enterprises deploying* AI, not revenue for AI *vendors*. An app team expecting a meaningful slice of "the trillion-dollar AI market" is treating a macro productivity estimate as its addressable revenue pool. The second number is almost always far smaller.
- **Assuming today's layer margins are stable.** Margins move with competitive intensity. GPU margins held through 2025-2026 because demand outran supply. If that reverses (more fabs, competing silicon, an AI capex slowdown), the "safest" layer stops being safe. [[Deep Dive - Bubble or Boom]] covers the buildout-sustainability question this hangs on.
- **Building at the wrong layer for your team's actual advantage.** A team with model-training expertise and no distribution loses to a team with distribution and no model expertise. Distribution owns the relationship with the paying customer, whichever layer below it churns.

## The non-obvious

The gap between creating value and capturing it isn't new to AI. It recurs in every general-purpose-technology wave (electrification, the internet, mobile): suppliers rarely capture surplus in proportion to the value they create, because competition and substitutability hand most of it to users. What's specific to AI is the speed at the model layer. [[Concept - Token Price Deflation]] erodes model-layer pricing power over quarters, where cloud infrastructure margins took a decade-plus to normalize after the 2006-2010 AWS launch era. The practical takeaway for an operator: don't build a business model that needs a *specific* layer's current margin to persist. Capture value through something (data, workflow, distribution) that survives the layer below you commoditizing.

## Connections

- [[Concept - Unit Economics of LLM Products]] — the app-layer margin numbers cited here (52-65% gross margin) are explained mechanically at the query level in that note.
- [[Concept - Moats in the AI Application Layer]] — the escape route from the thin-margin sandwich: what makes an app's margin defensible when the model underneath is commoditized.
- [[Breakdown - Frontier Lab Economics]] — the lab layer's own cost structure (training capex vs. inference revenue), the layer sandwiched between silicon and apps.
- [[Breakdown - The Cursor Ramp]] — the clearest counter-example of fast app-layer value capture, examined in full.
- [[Concept - Token Price Deflation]] — the mechanism compressing the model layer's margin and reshaping the whole stack's economics.
- [[Reference - AI Market Sizing Claims]] — where the McKinsey-style macro estimates cited here come from and how to read them without conflating market size with capturable revenue.
- [[Concept - Support Deflection Economics]] — a concrete, function-level example of where "value created" (cost saved) shows up when it is *not* captured by an AI vendor but by the deploying enterprise.
- [[Deep Dive - Bubble or Boom]] — whether the silicon layer's current margin structure is sustainable if the compute buildout outruns demand.
- [[Concept - Cost Engineering for LLM Applications]] — the app-layer's practical lever for defending margin against the sandwich described here.
- [[Reference - Model Genealogy]] — traces how open-weight releases (DeepSeek, Llama) have driven the model-layer commoditization discussed above.

## Sources

- Nvidia Corporation, Form 10-K, fiscal year 2025 (SEC, filed Feb 2025) — Data Center revenue $115.2B, company gross margin 75.0%.
- Andreessen Horowitz, "Who Owns the Generative AI Platform?" (Bornstein et al. — Matt Bornstein, Guido Appenzeller, Martin Casado; Jan 19, 2023) — the original infrastructure-captures-value thesis.
- Bessemer Venture Partners, State of AI report (2025) — LLM-native company gross margins ~65%.
- ICONIQ Capital, State of AI: Bi-Annual Snapshot (Jan 2026) — average AI product gross margin 52%, up from 41% (2024) / 45% (2025).
- TechCrunch, "Cursor's Anysphere nabs $9.9B valuation, soars past $500M ARR" (June 5, 2025).
- McKinsey Global Institute, "The economic potential of generative AI: The next productivity frontier" (2023, updated through 2025-2026 commentary) — $2.6-4.4T/yr value estimate across 63 use cases.
