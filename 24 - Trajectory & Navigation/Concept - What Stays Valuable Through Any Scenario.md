---
tags: [concept, domain/trajectory, level/surface]
aliases: [durable AI value, scenario-robust positioning, invariant value in AI]
summary: "The positions that hold value whether AI scales, plateaus, or bubbles — never the model layer itself."
---

# Concept - What Stays Valuable Through Any Scenario
> **One-paragraph hook:** every AI forecast disagrees on timing — [[Concept - The AGI Timeline Debate|AGI medians]] span 2030 to 2050, [[Deep Dive - Bubble or Boom|bubble-or-boom]] is genuinely unresolved — but four positions pay off under nearly every branch of that uncertainty. An engineer or operator who can't wait for the forecast to resolve should build toward those positions, not toward whichever scenario currently sounds loudest.

## The mechanism

The reasoning is a dominance argument, not a prediction: identify actions whose payoff doesn't depend on which scenario obtains, and take those first. Two structural facts do the work.

First, capability is deflating and commoditizing. Token prices for a fixed quality bar have fallen roughly 10x/year since 2022 (E2, a16z "LLMflation" analysis of published price lists, Nov 2024) — GPT-3-equivalent (MMLU 42) quality went from ~$60/M tokens (late 2021) to ~$0.06/M (late 2024); Epoch AI's independent 2025 analysis corroborates the direction while finding the rate ranges 9x-900x/yr depending on which capability tier is held fixed. Near-frontier capability is now available from multiple labs within months of the leader (link [[Reference - Model Genealogy]]). Owning "a model" is therefore a depreciating asset by construction: whatever a model does today, a cheaper model does it within a year, and a comparable open-weight model does it within months (link [[Concept - Token Price Deflation]]).

Second, the bottleneck has moved off raw capability and onto everything capability touches but doesn't replace. This produces four invariants — value that sits *below* the model (inputs it needs but doesn't generate) or *above* it (what happens to its output before it matters), rather than *at* the model layer:

1. **Proprietary data and distribution.** A model is general-purpose; your customer data, workflow history, and distribution channel are not. The application-layer moat is data and workflow lock-in, not a clever prompt (link [[Concept - Moats in the AI Application Layer]]) — thin wrappers with no proprietary input are exposed twice over, to price deflation from below and to frontier labs absorbing the wrapper's function from above.

2. **Verification and judgment.** Because the 80%-reliability time horizon lags the 50%-horizon by roughly 5x (E2, [[Concept - METR Time Horizons]], METR Time Horizon 1.1, Jan 2026), models do short tasks reliably and longer tasks only sometimes — see [[Concept - The Capability-Reliability Gap]]. Someone still has to check the output and own the consequence of it being wrong. Whoever can do that cheaply, and is willing to hold liability for it, captures value the model structurally cannot capture for itself (link [[Concept - The Evaluation Gap]]).

3. **Taste and problem-selection.** Once execution is cheap, choosing the right problem becomes the scarce skill. MIT NANDA's 2025 study of ~300 enterprise AI deployments found the ~5% of pilots that produced measurable P&L impact were narrow and well-targeted rather than broad — the difference was problem selection and workflow fit, not model access (E2, single study, 150 leader interviews + 350-employee survey).

4. **Integration and accountable ownership.** The Anthropic Economic Index's own telemetry (November 2025 data, published Jan 2026) shows augmentation still ahead of automation on Claude.ai — 52% vs 45%, with augmentation's share rising — meaning human-in-the-loop integration work is still where most usage actually sits, not a transitional phase being phased out (E2, single-company telemetry; link [[Deep Dive - AI and the Labor Market]]).

## In practice

These four invariants are not abstract: they map directly onto the buy-vs-build default in [[Playbook - Picking Profitable AI Use Cases]] (default to buying commodity capability, invest in proprietary data pipelines and verification tooling instead) and onto the no-regret-moves row of [[Reference - The 2026 Navigation Cheatsheet]]. A concrete test: ask whether a feature would survive a frontier lab shipping an equivalent capability natively next quarter. Wrapper features fail this test; features built on your data, your verification pipeline, or your customer trust relationship survive it, because the lab's native feature still needs those same three things and doesn't have them.

## Failure modes

The dominant failure is building — or investing in — a thin wrapper on a frontier model for a task the model vendor is likely to absorb: a UI layer over a single API call, with no data moat and no verification step that couldn't be replicated by the model provider's own product team in a quarter. [[Lore - AI Wrapper Graveyard]] catalogs the pattern. The second failure is misreading "augmentation still leads automation" as static — the AEI's own trend line shows automation's share rising over 2025-2026 even though augmentation currently leads, so a position that depends on augmentation staying dominant forever is not actually scenario-robust; it is betting on a snapshot. Detection: if your value proposition is "we call the model well," not "we own data/verification/distribution the model can't reach," you are in the failure mode regardless of current revenue.

## The non-obvious

The least defensible position in AI right now is not "too early" or "too speculative" — it's sitting exactly at the model layer, one layer where value structurally cannot accumulate because deflation erodes it from below and lab feature-absorption erodes it from above simultaneously. Durable value sits *below* the model (proprietary data, infrastructure, verification tooling the model consumes or is checked against) or *above* it (workflow ownership, accountability, distribution, trust) — almost never in the thin layer where the model itself lives. This is also why "bubble or boom" is close to the wrong question for an individual operator to answer before acting: per [[Deep Dive - Bubble or Boom]], a real capital bubble and genuine technological transformation are historically orthogonal (the dot-com crash was a real bubble and the internet still reshaped the economy) — the four invariants above pay off in both the boom and the bust branch, which is exactly why they're worth building toward before the scenario resolves rather than after.

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
