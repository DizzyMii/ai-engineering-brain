---
tags: [moc, domain/ai-economics, level/surface]
aliases: [AI Economics MOC, MOC - AI Econ]
summary: "Map of AI Economics: value capture, unit economics, pricing, moats, capex accounting, and the buildout's financing question."
---
# MOC - AI Economics

This domain records where the money in AI actually goes: which layer of the stack captures margin, why an LLM call breaks SaaS-era gross-margin assumptions, how products get priced against a falling and shifting cost curve, what makes an application layer defensible once the model underneath it is a commodity, and whether the trillion-dollar capex buildout is financed by real demand or by suppliers financing their own customers. It matters because every build, pricing, and fundraising decision in AI is a bet on one of these dynamics, usually made implicitly. The domain answers one question from several angles: *given that inference is a real, metered, falling-but-volatile cost, who ends up holding the profit — and who ends up holding the bag?* Numbers here move fast and are tiered per the Evidence Law; read the tier before you repeat the figure.

**Start here, by level:**
- **Surface:** [[Concept - Value Capture Across the AI Stack]] — the five-layer map (silicon → cloud → labs → apps → distribution) that every other note in this domain assumes.
- **Core:** [[Concept - Unit Economics of LLM Products]] — the per-query cost model that explains why "just add AI" breaks the SaaS margin playbook.
- **Advanced:** [[Breakdown - Frontier Lab Economics]] — the labs' actual P&L: fast revenue growth, faster losses, a 10-20x compute-commitment gap.
- **Frontier:** [[Deep Dive - Circular Financing in the AI Buildout]] — the open question the whole buildout rests on: is the money real demand or a closed loop?
- **Unicorn:** [[Lore - AI Wrapper Graveyard]] — the war stories (Jasper, Windsurf) that make the moat arguments visceral instead of theoretical.

## The stack and its structure

- [[Concept - Value Capture Across the AI Stack]] — Nvidia's 75.0% company gross margin (FY2025 10-K) against the app layer's 52% average (ICONIQ, Jan 2026): pricing power flows down the stack, cost flows up.
- [[Concept - Token Price Deflation]] — "LLMflation": GPT-3-quality tokens fell ~1,000x from $60/M (Nov 2021) to $0.06/M (Nov 2024), but Epoch AI found the rate ranges 9x/yr at the frontier tier to 900x/yr at the commodity tier — deflation is not one number.
- [[Concept - GPU Depreciation and Compute Capex Accounting]] — Meta's single 2025 useful-life extension (to 5.5 years) cut reported depreciation ~$2.9B for the year; Michael Burry's ~$176B industry-understatement estimate collides with the "waterfall" counter-argument that old chips just keep earning on cheap inference.
- [[Deep Dive - Circular Financing in the AI Buildout]] — traces the Nvidia→OpenAI→Oracle→Nvidia loop; the headline "$100B Nvidia investment" was never signed and shrank to a $30B unconditional equity stake by March 2026 — announced is not funded.
- [[Breakdown - Frontier Lab Economics]] — OpenAI's ~$21B operating loss on ~$13B 2025 revenue, against compute commitments (Oracle, Stargate, Nvidia) roughly 10-20x that revenue; Anthropic's enterprise-led model let it approach OpenAI's run-rate despite an order of magnitude fewer users.

## Pricing and unit economics at the product layer

- [[Concept - Unit Economics of LLM Products]] — reasoning models' invisible "thinking tokens" can run 5-20x the visible output count; flat-rate coding tools (Cursor, Claude Code) both introduced usage caps in 2025 once heavy users broke the SaaS zero-marginal-cost assumption.
- [[Decision - Pricing Models for AI Products]] — the 2026 default is hybrid (base + metered overage): GitHub Copilot Business only moved off flat $19/seat pricing to usage credits in June 2026, after seat pricing couldn't absorb agentic coding-agent consumption.
- [[Concept - Outcome-Based Pricing]] — Intercom Fin's $0.99-per-resolution model scaled from ~$1M to $100M+ ARR, while Salesforce Agentforce's clean per-conversation launch (Oct 2024) fractured into three simultaneous pricing schemes within ~18 months once "what counts as a conversation" became a fight.
- [[Playbook - Measuring AI ROI]] — METR's controlled trial found developers were 19% slower with AI while believing they were ~20% faster; a Feb 2026 follow-up shrank the effect to a statistically insignificant -4%, and METR itself flagged the original headline "out of date."

## Strategy, moats, and the build/buy/wrap question

- [[Decision - Build vs Buy vs Wrap]] — pretraining a frontier model costs an estimated $100M-$1B+, which is why the real 2026 question isn't build-vs-buy, it's "wrap well vs. wrap thin"; Jasper's $125M Series A landed six weeks before ChatGPT ate its moat.
- [[Concept - Moats in the AI Application Layer]] — the model call is never the moat (any two companies with an API key produce the same completion); Cursor's codebase-indexing and habit lock-in vs. Jasper's prompt-templates-only stack are the note's two poles.
- [[Breakdown - The Cursor Ramp]] — ARR doubling roughly every two months forced a botched June 16, 2025 repricing (500 fast requests collapsed into a ~$20 API allowance) that triggered public apology, refunds, and a new $200/mo Ultra tier within weeks.
- [[Lore - AI Wrapper Graveyard]] — Windsurf's ~$3B OpenAI acquisition collapsed on July 11, 2025 and the company was dismembered three ways (Google's ~$2.4B reverse-acquihire, then Cognition buying the remainder) within 72 hours — even a winner can become a supplier's pawn.

## Market sizing and capital flows

- [[Reference - AI Market Sizing Claims]] — McKinsey's $2.6-4.4T/yr value estimate and Sequoia's Cahn "$600B question" (revenue needed to justify capex) measure three different things — value, market, and spend — that headlines routinely collapse into one number.
- [[Reference - AI Venture Funding Patterns]] — AI took 52.5% of global VC dollars in FY2025 and ~86% of US VC in H1 2026; OpenAI's ~$122B round (Mar 2026) is the largest private tech raise in history, and a chunk of the "funding" behind these marks is really pre-purchased GPU capacity.

## Adjacent domains

- [[MOC - AI in Software Engineering]] — coding is where the moat and pricing arguments here (Cursor, agentic workloads) play out first, because verifiable output narrows the reliability gap that stalls AI economics elsewhere.
- [[MOC - AI Across Business Functions]] — the function-level deflection and outcome math (support, legal, medical scribing) that this domain's pricing and ROI notes treat abstractly gets its concrete, per-vertical numbers there.
- [[MOC - Adoption & Blockers]] — the pilot-to-production gap and evaluation gap are the organizational reasons the ROI and outcome-pricing numbers in this domain are so often unmeasured or unmeasurable.
- [[MOC - Trajectory & Navigation]] — whether the circular-financing buildout is bubble or boom depends on demand and compute-scaling trajectories mapped on that side of the wing.

See also [[Ladder - Navigating the AI Economy]] for a guided, ordered walk through this domain's notes from surface to unicorn.
