---
tags: [moc, domain/ai-economics, level/surface]
aliases: [AI Economics MOC, MOC - AI Econ]
summary: "Map of AI Economics: value capture, unit economics, pricing, moats, capex accounting, and the buildout's financing question."
---
# MOC - AI Economics

Where the money in AI actually goes. Which layer of the stack captures margin, why an LLM call breaks SaaS-era gross-margin assumptions, how products get priced against a falling and shifting cost curve, what keeps an application defensible once the model under it is a commodity, and whether the trillion-dollar capex buildout is funded by real demand or by suppliers financing their own customers. Every build, pricing and fundraising decision in AI is a bet on one of these, usually made without saying so. The domain keeps circling one question: *inference is a real, metered, falling-but-volatile cost, so who ends up holding the profit, and who ends up holding the bag?* The numbers move fast and are tiered per the Evidence Law. Check the tier before you repeat a figure.

**Start here, by level:**
- **Surface:** [[Concept - Value Capture Across the AI Stack]]: the five-layer map (silicon → cloud → labs → apps → distribution) every other note here assumes.
- **Core:** [[Concept - Unit Economics of LLM Products]]: the per-query cost model behind why "just add AI" breaks the SaaS margin playbook.
- **Advanced:** [[Breakdown - Frontier Lab Economics]]: the labs' actual P&L, with fast revenue growth, faster losses, and a 10-20x compute-commitment gap.
- **Frontier:** [[Deep Dive - Circular Financing in the AI Buildout]]: the open question under the whole buildout. Is the money real demand or a closed loop?
- **Unicorn:** [[Lore - AI Wrapper Graveyard]]: the war stories (Jasper, Windsurf) that make the moat arguments concrete.

## The stack and its structure

- [[Concept - Value Capture Across the AI Stack]]: Nvidia's 75.0% company gross margin (FY2025 10-K) against the app layer's 52% average (ICONIQ, Jan 2026). Pricing power flows down the stack, cost flows up.
- [[Concept - Token Price Deflation]]: "LLMflation". GPT-3-quality tokens fell ~1,000x from $60/M (Nov 2021) to $0.06/M (Nov 2024), but Epoch AI found the rate runs from 9x/yr at the frontier tier to 900x/yr at the commodity tier. Deflation isn't one number.
- [[Concept - GPU Depreciation and Compute Capex Accounting]]: Meta's single 2025 useful-life extension (to 5.5 years) cut reported depreciation ~$2.9B for the year. Michael Burry's ~$176B industry-understatement estimate runs into the "waterfall" counter that old chips keep earning on cheap inference.
- [[Deep Dive - Circular Financing in the AI Buildout]]: traces the Nvidia→OpenAI→Oracle→Nvidia loop. The headline "$100B Nvidia investment" was never signed and shrank to a $30B unconditional equity stake by March 2026. Announced isn't funded.
- [[Breakdown - Frontier Lab Economics]]: OpenAI's ~$21B operating loss on ~$13B 2025 revenue, against compute commitments (Oracle, Stargate, Nvidia) roughly 10-20x that revenue. Anthropic's enterprise-led model got it close to OpenAI's run-rate with an order of magnitude fewer users.

## Pricing and unit economics at the product layer

- [[Concept - Unit Economics of LLM Products]]: reasoning models' invisible "thinking tokens" can run 5-20x the visible output count. Flat-rate coding tools (Cursor, Claude Code) both added usage caps in 2025 once heavy users broke the SaaS zero-marginal-cost assumption.
- [[Decision - Pricing Models for AI Products]]: the 2026 default is hybrid (base + metered overage). GitHub Copilot Business only moved off flat $19/seat pricing to usage credits in June 2026, after seats couldn't absorb agentic coding-agent consumption.
- [[Concept - Outcome-Based Pricing]]: Intercom Fin's $0.99-per-resolution model scaled from ~$1M to $100M+ ARR. Salesforce Agentforce's clean per-conversation launch (Oct 2024) split into three simultaneous pricing schemes within ~18 months once "what counts as a conversation" turned into a fight.
- [[Playbook - Measuring AI ROI]]: METR's controlled trial found developers were 19% slower with AI while believing they were ~20% faster. A Feb 2026 follow-up shrank the effect to a statistically insignificant -4%, and METR itself called the original headline "out of date."

## Strategy, moats, and the build/buy/wrap question

- [[Decision - Build vs Buy vs Wrap]]: pretraining a frontier model costs an estimated $100M-$1B+, so the real 2026 question is "wrap well or wrap thin?" Jasper's $125M Series A landed six weeks before ChatGPT ate its moat.
- [[Concept - Moats in the AI Application Layer]]: the model call is never the moat, since any two companies with an API key get the same completion. Cursor's codebase indexing and habit lock-in vs. Jasper's prompt-templates-only stack are the two poles.
- [[Breakdown - The Cursor Ramp]]: ARR doubling roughly every two months forced a botched June 16, 2025 repricing (500 fast requests collapsed into a ~$20 API allowance). Within weeks came a public apology, refunds, and a new $200/mo Ultra tier.
- [[Lore - AI Wrapper Graveyard]]: Windsurf's ~$3B OpenAI acquisition collapsed on July 11, 2025, and within 72 hours the company was split three ways (Google's ~$2.4B reverse-acquihire, then Cognition buying the remainder). Even a winner can end up a supplier's pawn.

## Market sizing and capital flows

- [[Reference - AI Market Sizing Claims]]: McKinsey's $2.6-4.4T/yr value estimate and Sequoia's Cahn "$600B question" (revenue needed to justify capex) measure three different things (value, market, spend) that headlines routinely mash into one number.
- [[Reference - AI Venture Funding Patterns]]: AI took 52.5% of global VC dollars in FY2025 and ~86% of US VC in H1 2026. OpenAI's ~$122B round (Mar 2026) is the largest private tech raise in history, and part of the "funding" behind these marks is really pre-purchased GPU capacity.

## Adjacent domains

- [[MOC - AI in Software Engineering]]: coding is where this domain's moat and pricing arguments (Cursor, agentic workloads) play out first, because verifiable output narrows the reliability gap that stalls AI economics elsewhere.
- [[MOC - AI Across Business Functions]]: the per-vertical numbers (support, legal, medical scribing) behind the deflection and outcome math this domain's pricing and ROI notes treat abstractly.
- [[MOC - Adoption & Blockers]]: the pilot-to-production gap and evaluation gap are the organizational reasons the ROI and outcome-pricing numbers here so often go unmeasured, or can't be measured.
- [[MOC - Trajectory & Navigation]]: bubble or boom for the circular-financing buildout depends on the demand and compute-scaling trajectories mapped there.

See also [[Ladder - Navigating the AI Economy]] for a guided, ordered walk through this domain from surface to unicorn.
