---
tags: [reference, domain/applied-software, level/core]
aliases: [AI coding tool market map, AI dev tools 2026]
summary: "Date-stamped market map of AI coding tools as of mid-2026: category, ownership, funding/valuation, and evidence tier for every figure."
---
# Reference - AI Dev Tool Landscape

Every $ figure here is press- or vendor-reported and volatile. ARR ≠ profit. "Users" are typically all-time unless marked "paid"/"active." Re-verify before quoting past 2026. This page covers the tool layer only. The [[Concept - AI Coding Assistants|three-generation taxonomy]] these tools implement has its own note. Whether *measured productivity* backs any given scale claim is in [[Reference - Developer Productivity Studies]], and the adopt-vs-build call this table feeds is [[Decision - Build vs Buy vs Wrap]].

## Incumbent / model-backed assistants

| Tool | Owner | Scale claim | Tier | Date |
|---|---|---|---|---|
| GitHub Copilot | Microsoft/GitHub, OpenAI models | 20M all-time users (crossed Jul 2025); ~4.7M paid subscribers (+75% YoY); ~90% of Fortune 100 deployed; ~42% share of the paid AI-coding-tool market (company-claimed, E1 market-share estimate) | E2 (user/subscriber/Fortune-100 figures, GitHub/Microsoft self-reported) | Jul 2025 / Jan 2026 |
| Anthropic Claude Code | Anthropic | Terminal-based agent; no independent user-count disclosure as of mid-2026 | — | 2026 |
| OpenAI Codex / Codex CLI | OpenAI | Agentic coding product line; no independent user-count disclosure | — | 2026 |
| Google Gemini Code Assist | Google | IDE assistant; used internally for large-scale LLM-driven migrations (link [[Breakdown - AI-Driven Code Migrations]]) | E2 (Google's own paper) | Apr 2025 |
| Amazon Q Developer | Amazon/AWS | Java 8/11→17 modernization: claimed 4,500 developer-years saved, ~$260M/yr efficiency, >50% of production Java modernized in <6 months | E2 (Amazon's own claim, unaudited) | Aug 2024 |

## AI-native IDEs and orchestrators

| Tool | Owner | Scale / funding | Tier | Date |
|---|---|---|---|---|
| Cursor (full case study: [[Breakdown - Cursor]]) | Anysphere (founded 2022) | ARR: ~$100M (Jan 2025) → ~$1B (Nov 2025) → ~$2B (Feb 2026) → ~$4B annualized (Jun 2026). Series D: $2.3B raise at $29.3B post-money (Nov 2025). **Acquired by SpaceX for $60B all-stock, announced Jun 16 2026, expected to close Q3 2026**; reportedly the largest acquisition of a VC-backed startup on record; SpaceX had held an option since Apr 21 2026 (walk-away fee ~$10B). Deal ties Cursor into SpaceX's post-xAI-merger AI push. | E1/E2 (press-reported ARR/valuation; deal terms company-confirmed) | Jun 2026 |
| Windsurf (formerly Codeium) | Split three ways in Jul 2025: OpenAI's $3B acquisition letter of intent collapsed (Microsoft IP-access dispute) → Google DeepMind hired CEO Varun Mohan + core team and licensed the tech non-exclusively (~$2.4B reported "reverse acqui-hire") → Cognition Labs (Devin) acquired the remaining product, brand, IP, and staff, all within ~72 hours | E2 (multiple outlets: TechCrunch, CNBC, Fortune) | Jul 2025 |

## Autonomous coding agents

How these agents run day to day inside real engineering orgs, beyond their benchmark scores, is in [[Deep Dive - Agentic Coding in Production]].

| Tool | Owner | Scale claim | Tier | Date |
|---|---|---|---|---|
| Devin | Cognition Labs | 13.86% on a 25%-subset SWE-bench (unassisted; prior unassisted SOTA was 1.96%) at Mar 2024 launch; independent estimates of real-world autonomous task completion ~14-15% | E2 (Cognition's own technical report + independent replications) | Mar 2024 |
| SWE-agent, OpenHands (formerly OpenDevin), Aider | Open source | No centralized funding/scale figures; used as baseline harnesses in [[Breakdown - SWE-bench]] comparisons | — | 2024-2026 |

## AI code review

Mechanism, what these tools catch and miss, and the alert-fatigue failure mode are in [[Concept - AI Code Review]]. This table is funding and ownership only.

| Tool | Owner | Funding / scale | Tier | Date |
|---|---|---|---|---|
| CodeRabbit | Independent | $60M Series B (Scale Venture Partners lead, NVentures/Nvidia + CRV) at $550M valuation; >$15M ARR growing ~20%/month; 8,000+ paying orgs (Chegg, Groupon, Mercury); most-installed app on GitHub Marketplace | E2 (company-reported, corroborated by TechCrunch) | Sep 2025 |
| Graphite | **Acquired by Cursor**, Dec 2025 | $52M Series B (Accel lead; Anthropic's Anthology Fund, a16z, Shopify/Figma Ventures participating) before acquisition; served 500+ companies (Shopify, Snowflake, Figma); terms not officially disclosed; reported at "way over $290M" cash-and-equity (E2, Fortune/TechCrunch, Dec 2025); brand kept independent through integration in 2026 | E2 | Mar 2025 (raise) / Dec 2025 (acquired) |
| Greptile | Independent | $25M Series A led by Benchmark (after Jul 2025 reports of a larger ~$180M-valuation round that came down by close); 500M+ lines of code analyzed monthly (Brex, Substack, PostHog) | E2 | Sep 2025 |

## Business models

| Model | Examples | Note |
|---|---|---|
| Per-seat subscription | GitHub Copilot (~$10-39/mo tiers) | Predictable cost; doesn't scale with usage intensity |
| Usage-based (tokens) | Agent modes across most tools | Pass-through on model inference cost (see [[Concept - Unit Economics of LLM Products]]); heavy users can cost the vendor more than they pay |
| Hybrid | Cursor, most AI-native IDEs | Seat floor + usage ceiling; margins depend on [[Concept - Token Price Deflation]] outpacing usage growth |

The tool-level view is a fraction of the macro number. [[Reference - AI Market Sizing Claims]] covers how analysts size the whole AI-coding-tools category, and [[Reference - Model Genealogy]] shows which frontier model lineage sits under each wrapper's capability.

## Consolidation and churn risk (as of mid-2026)

- **Vertical integration.** Cursor buying Graphite (write + review) and SpaceX buying Cursor (a coding tool folded into a much larger AI/compute platform) both point to the market moving from point tools to owned pipelines. See [[Concept - Moats in the AI Application Layer]].
- **Vendor discontinuity has already happened.** The Windsurf split showed a well-funded, widely adopted tool can be reorganized across three acquirers within days. Teams that build workflows on one vendor's agent harness carry real switching-cost risk; the general form is [[Concept - Vendor and Model Churn Risk]].
- **There's no independent cross-vendor benchmark** for code-review quality or agent task-completion rate as of 2026. Every scale or quality claim in these tables is vendor- or press-sourced (E1/E2). Treat vendor-vs-vendor comparisons as marketing until an independent evaluator publishes one.

## Connections

- [[Concept - AI Coding Assistants]] — the three-generation taxonomy (autocomplete/chat/agent) these vendors compete across.
- [[Breakdown - Cursor]] — full case study of Cursor's product mechanics and economics prior to the SpaceX acquisition.
- [[Concept - AI Code Review]] — mechanism and market detail behind the CodeRabbit/Graphite/Greptile row.
- [[Deep Dive - Agentic Coding in Production]] — how the autonomous-agent row's tools actually run in real organizations.
- [[Concept - Unit Economics of LLM Products]] — why usage-based pricing in this table is a pass-through cost problem, not just a pricing choice.
- [[Concept - Moats in the AI Application Layer]] — the theory behind why consolidation (Graphite, SpaceX deals) is happening now.
- [[Reference - AI Market Sizing Claims]] — the macro market-size numbers this tool-level table rolls up into.
- [[Decision - Build vs Buy vs Wrap]] — the build-vs-adopt decision this landscape is the input to.
- [[Concept - Token Price Deflation]] — the trend line that determines whether usage-based rows in this table get cheaper or more expensive to run over time.
- [[Reference - Model Genealogy]] — which frontier models (Anthropic, OpenAI, Google) underlie each wrapper product's actual capability.
- [[Reference - Developer Productivity Studies]] — the evidence-tiered catalog of whether the tools in this table actually measurably help, independent of their funding/scale numbers.
- [[Concept - Vendor and Model Churn Risk]] — the Windsurf split and the Cursor/Graphite/SpaceX consolidation wave are concrete instances of the vendor-dependency risk this concept catalogs (cross-domain: adoption).

## Sources

- GitHub — Copilot user-count and Fortune 100 disclosures (Jul 2025); Copilot paid-subscriber and market-share figures (Jan 2026 earnings commentary).
- CNBC — "SpaceX to acquire the AI coding startup Cursor for $60 billion" (Jun 16, 2026); TechFundingNews and Qz.com coverage of deal structure and option agreement.
- TechCrunch — "Windsurf's CEO goes to Google; OpenAI's acquisition falls apart" (Jul 11, 2025); CNBC — "Cognition to buy AI startup Windsurf" (Jul 14, 2025).
- TechCrunch — CodeRabbit Series B (Sep 16, 2025); Graphite Series B (Mar 18, 2025); Greptile Series A reporting (Jul 18 and Sep 23, 2025).
- Fortune — "Cursor acquires code review startup Graphite" (Dec 19, 2025).
- Cognition Labs — "SWE-bench technical report" (Mar 2024) — Devin's 13.86% figure and methodology caveats.
