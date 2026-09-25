---
tags: [concept, domain/trajectory, level/surface]
aliases: [durable AI value, scenario-robust positioning, invariant value in AI]
summary: "The positions that hold value whether AI scales, plateaus, or bubbles — never the model layer itself."
---

# Concept - What Stays Valuable Through Any Scenario
> **One-paragraph hook:** AI forecasts disagree on timing. [[Concept - The AGI Timeline Debate|AGI medians]] span 2030 to 2050, and [[Deep Dive - Bubble or Boom|bubble-or-boom]] is unresolved. Four positions still pay off under nearly every branch of that uncertainty. An engineer or operator who can't wait for the forecast to resolve should build toward those, not toward whichever scenario sounds loudest this month.

## The mechanism

This is a dominance argument, not a prediction. Find actions whose payoff doesn't depend on which scenario happens, and take those first. Two facts do the work.

First, capability is deflating and commoditizing. Token prices for a fixed quality bar have fallen roughly 10x/year since 2022 (E2, a16z "LLMflation" analysis of published price lists, Nov 2024). GPT-3-equivalent (MMLU 42) quality went from ~$60/M tokens (late 2021) to ~$0.06/M (late 2024). Epoch AI's independent 2025 analysis agrees on direction and finds the rate ranges 9x-900x/yr depending on which capability tier is held fixed. Several labs reach near-frontier capability within months of the leader ([[Reference - Model Genealogy]]). So owning "a model" is a depreciating asset by construction. Whatever a model does today, a cheaper one does within a year and a comparable open-weight one within months ([[Concept - Token Price Deflation]]).

Second, the bottleneck has moved off raw capability onto everything capability touches but doesn't replace. That gives four invariants, all sitting *below* the model (inputs it needs but doesn't generate) or *above* it (what happens to its output before it matters), not *at* the model layer:

1. **Proprietary data and distribution.** A model is general-purpose. Your customer data, workflow history and distribution channel aren't. The application-layer moat is data and workflow lock-in, not a clever prompt ([[Concept - Moats in the AI Application Layer]]). Thin wrappers with no proprietary input get hit twice: by price deflation from below, and by frontier labs absorbing the wrapper's function from above.

2. **Verification and judgment.** The 80%-reliability time horizon lags the 50% horizon by roughly 5x (E2, [[Concept - METR Time Horizons]], METR Time Horizon 1.1, Jan 2026), so models do short tasks reliably and longer ones only sometimes; see [[Concept - The Capability-Reliability Gap]]. Someone still has to check the output and own the consequences when it's wrong. Whoever does that cheaply, and will hold the liability, captures value the model can't capture for itself ([[Concept - The Evaluation Gap]]).

3. **Taste and problem selection.** Once execution is cheap, picking the right problem is the scarce skill. MIT NANDA's 2025 study of ~300 enterprise AI deployments found the ~5% of pilots with measurable P&L impact were narrow and well-targeted, not broad. Problem selection and workflow fit made the difference, not model access (E2, single study, 150 leader interviews + 350-employee survey).

4. **Integration and accountable ownership.** The Anthropic Economic Index's telemetry (November 2025 data, published Jan 2026) shows augmentation still ahead of automation on Claude.ai, 52% vs 45%, with augmentation's share rising. Human-in-the-loop integration work is still where most usage sits, not a transitional phase on its way out (E2, single-company telemetry; see [[Deep Dive - AI and the Labor Market]]).

## In practice

The four invariants map onto the buy-vs-build default in [[Playbook - Picking Profitable AI Use Cases]] (buy commodity capability; invest in proprietary data pipelines and verification tooling) and onto the no-regret-moves row of [[Reference - The 2026 Navigation Cheatsheet]]. A quick test: would this feature survive a frontier lab shipping the same capability natively next quarter? Wrapper features fail. Features built on your data, your verification pipeline or your customers' trust survive, because the lab's native feature needs those same three things and doesn't have them.

## Failure modes

The main failure is building, or investing in, a thin wrapper on a frontier model for a task the vendor is likely to absorb: a UI over a single API call, with no data moat and no verification step the provider's own product team couldn't copy in a quarter. [[Lore - AI Wrapper Graveyard]] catalogs the pattern.

The second is reading "augmentation still leads automation" as permanent. The AEI's trend line shows automation's share rising over 2025-2026 even though augmentation leads today. A position that needs augmentation to stay dominant forever isn't scenario-robust; it's a bet on a snapshot. Detection: if your pitch is "we call the model well" and not "we own data/verification/distribution the model can't reach," you're in the failure mode whatever your current revenue.

## The non-obvious

The least defensible position in AI right now is sitting right at the model layer, more than being "too early" or "too speculative." Value can't accumulate there, because deflation erodes it from below while lab feature-absorption erodes it from above. Durable value sits *below* the model (proprietary data, infrastructure, verification tooling the model consumes or gets checked against) or *above* it (workflow ownership, accountability, distribution, trust). Almost never in the thin layer where the model lives.

It's also why "bubble or boom" is close to the wrong question for an individual operator to settle before acting. Per [[Deep Dive - Bubble or Boom]], a real capital bubble and real technological transformation have historically been independent: the dot-com crash was a real bubble and the internet still reshaped the economy. The four invariants pay off in both the boom branch and the bust branch, so build toward them before the scenario resolves, not after.

## Connections
- [[Concept - Token Price Deflation]] — the deflation mechanism that makes the model layer specifically unsafe to build a business on.
- [[Concept - Moats in the AI Application Layer]] — the detailed theory behind invariant 1 (data/distribution).
- [[Concept - The Capability-Reliability Gap]] — the reliability mechanism behind invariant 2 (verification/judgment).
- [[Concept - METR Time Horizons]] — supplies the quantitative 50%/80% gap that makes invariant 2 concrete.
- [[Concept - The Evaluation Gap]] — what "cheap verification" actually requires in practice.
- [[Deep Dive - Bubble or Boom]] — why these invariants are scenario-robust rather than boom-only or bust-only bets.
- [[Deep Dive - AI and the Labor Market]] — the population-level evidence behind invariant 4 (integration/accountability persisting).
- [[Reference - The 2026 Navigation Cheatsheet]] — the compact, date-stamped version of the no-regret moves this concept underpins.
- [[Reference - Model Genealogy]] — evidence for the commoditization claim (near-frontier capability converging across labs within months).
- [[Playbook - Picking Profitable AI Use Cases]] — operational procedure that applies these invariants to a use-case decision.
- [[Lore - AI Wrapper Graveyard]] — case-level evidence for the primary failure mode described above.

## Sources
- Andreessen Horowitz, "Welcome to LLMflation" (Guido Appenzeller, Nov 2024) — the ~10x/yr deflation framing underlying the "capability commoditizes" claim.
- Epoch AI (2025) — "LLM inference prices have fallen rapidly but unequally across tasks." Independent corroboration; 9x-900x/yr range by capability tier.
- MIT NANDA (2025) — "The GenAI Divide: State of AI in Business 2025." Basis for invariant 3 (taste/problem-selection).
- Anthropic (Jan 2026) — Anthropic Economic Index report, November 2025 usage data. Basis for invariant 4 and the failure-mode caveat about rising automation share.
- METR (Jan 2026) — Time Horizon 1.1. Basis for the 50%/80% reliability gap underlying invariant 2.
