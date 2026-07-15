---
tags: [concept, domain/ai-economics, level/surface]
aliases: [value capture, picks and shovels, layer-cake model]
summary: "Maps where money actually accrues across the AI stack and why the profit pool sits upstream of where most economic value is created."
---
# Concept - Value Capture Across the AI Stack

> **One-paragraph hook:** Every AI dollar spent by an enterprise passes through five layers — silicon, cloud/neocloud, foundation-model lab, application, distribution — and each layer takes a cut before the next one sees the money. As of 2026 the fattest, most durable margins sit at the bottom of that stack (chips) and the thinnest, most contested margins sit in the middle (models), while most of the *economic value* created lands with neither: it lands with the enterprises buying the tokens. An engineer picking where to build, or an operator picking what to build on, is picking a position in this stack — and the position determines the margin ceiling before a single feature ships.

## The mechanism

The AI stack decomposes into five layers, each buying from the one below and selling to the one above:

1. **Silicon** — Nvidia, AMD, TSMC (fab), Broadcom (custom ASICs). Sells compute capacity at hardware margins.
2. **Cloud / neocloud** — AWS, Azure, GCP, plus GPU-specialist neoclouds (CoreWeave, Lambda, Crusoe). Buys chips, rents them out as compute-hours.
3. **Foundation-model labs** — OpenAI, Anthropic, Google DeepMind, Meta, DeepSeek. Buys compute, trains models, sells tokens via API (or gives weights away).
4. **Application layer** — Cursor, Harvey, every SaaS company bolting on LLM calls. Buys tokens, sells a workflow.
5. **Distribution** — the channel that reaches the end user (an IDE, a browser, an OS, an app store). Often collapsed into the app layer, but distinct when a platform (e.g., an OS vendor) captures rent purely for being the door the user walks through.

The critical asymmetry: **pricing power flows downward, cost flows upward.** Nvidia sets GPU prices largely on its own terms (in a supply-constrained market); clouds mark that up into compute-hours; labs buy compute as their largest COGS line and sell tokens at a margin the market allows; apps buy tokens as *their* largest COGS line and sell a subscription or seat at whatever price the customer will pay. Each layer is a price-taker on its inputs and a price-setter (weakly) on its outputs — except the top layer, silicon, which is a price-setter on both sides because it faces the least competition.

This is why the FY2025 numbers look the way they do: Nvidia's Data Center segment posted **$115.2B in revenue** for fiscal year 2025 (ended Jan 26, 2025) at a company-wide **75.0% gross margin**, up from 72.7% a year earlier (E3, Nvidia FY2025 10-K, SEC filing, Feb 2025) — a hardware margin structure unmatched anywhere else in the stack. Meanwhile the application layer, per Bessemer's *State of AI* work, runs LLM-native gross margins around **65%** (E2, Bessemer, 2025), and ICONIQ Capital's January 2026 bi-annual survey of AI-native companies put average product gross margin at **52%**, up from 41% in 2024 and 45% in 2025 (E2, ICONIQ, single survey) — improving, but still well under the 80-90% that defined SaaS. See [[Concept - Unit Economics of LLM Products]] for why the app-layer number is structurally lower than legacy software.

## In practice

**"Picks and shovels."** In a gold rush, the surest returns go to whoever sells the shovels, not whoever pans for gold. In the 2023-2026 AI buildout, that has meant the reliably profitable position is compute supply — Nvidia, TSMC, and (more speculatively, on thinner public data) the neoclouds like CoreWeave — because every layer above them has to buy their product regardless of which model or app wins. a16z's "Who Owns the Generative AI Platform?" (Bornstein et al. — Matt Bornstein, Guido Appenzeller, Martin Casado — Jan 2023, E1 — a thesis piece, not measured data) argued infrastructure would capture the most durable value because apps face retention and margin pressure while models commoditize; by 2026 that framing has aged well directionally, though the app layer has produced faster-growing outliers than the thesis implied (below).

**Model-layer commoditization.** [[Concept - Token Price Deflation]] and open-weight parity — DeepSeek's R1/V3 family, Meta's Llama line — have compressed the pricing power labs hold over the app layer. A model that cost $30/M input tokens at frontier quality in March 2023 (GPT-4) has an open-weight, near-parity substitute under $0.50/M by 2026. When the input a layer sells becomes a commodity, its margin gets squeezed by the layer below (compute costs don't fall as fast as token prices) and the layer above (customers won't pay a premium for a fungible token). This is the **"thin-margin sandwich"**: app companies buy inference cost-plus from labs, who buy GPUs from Nvidia at hardware margins; each layer's pricing power leans on the one below it, so the app layer's margin ceiling is set by forces two layers removed from its own product. See [[Concept - Moats in the AI Application Layer]] for how apps escape this by owning something other than the model call.

**Counter-evidence — apps can still win fast.** Cursor (Anysphere) crossed **$100M ARR in January 2025** and **$500M+ ARR by June 2025**, closing a $900M Series C at a **$9.9B valuation** (E2, TechCrunch, June 2025) — one of the fastest revenue ramps recorded in software. This is real evidence against a strict "apps can't capture value" reading of the picks-and-shovels thesis. But Cursor's growth ran almost entirely on other labs' compute (Anthropic and OpenAI model calls); it demonstrates that an app can capture *revenue* fast, not that it has secured a durable *margin* independent of what those labs charge it next quarter. See [[Breakdown - The Cursor Ramp]] for the mechanism.

## Failure modes

- **Confusing value creation with value capture.** McKinsey estimates generative AI could add **$2.6-4.4 trillion/year** in economic value across 63 use cases (E1, McKinsey Global Institute, 2023, since referenced and updated through 2025-2026) — but that value is measured as cost saved or output gained by the *enterprises deploying* AI, not revenue captured by AI *vendors*. A team building an app-layer product that expects to capture a meaningful slice of "the trillion-dollar AI market" is conflating a macro productivity estimate with an addressable revenue pool for their specific product — the two numbers are not the same thing and the second is almost always far smaller.
- **Assuming today's layer margins are stable.** Layer margins move with competitive intensity, not just structurally. GPU margins held up through 2025-2026 because demand outstripped supply; if that reverses (more fabs, more competing silicon, an AI capex slowdown), the "safest" layer stops being safe. See [[Deep Dive - Bubble or Boom]] for the buildout-sustainability question this depends on.
- **Building at the wrong layer for your team's actual advantage.** A team with model-training expertise but no distribution loses to a team with distribution and no model expertise, because distribution captures the relationship with the paying customer regardless of which layer below it churns.

## The non-obvious

Value capture is not value creation, and this gap is not new to AI — it recurs in every general-purpose-technology wave (electrification, the internet, mobile). The pattern: the technology's suppliers rarely capture a share of the surplus proportional to how much value they created, because competition among suppliers (and substitutability of their product) transfers most of the surplus to users. The AI-specific twist is *how fast* the compression is happening at the model layer specifically — [[Concept - Token Price Deflation]] compresses model-layer pricing power on a timescale of quarters, not the decade-plus it took cloud infrastructure margins to normalize after the 2006-2010 AWS launch era. An operator's practical takeaway: don't build a business model that depends on a *specific* layer's current margin persisting — build one that captures value through a mechanism (data, workflow, distribution) that survives the layer below it commoditizing.

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
