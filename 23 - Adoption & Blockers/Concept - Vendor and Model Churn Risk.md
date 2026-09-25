---
tags: [concept, domain/adoption-blockers, level/core]
aliases: [model churn, vendor lock-in risk, model deprecation risk, snapshot pinning]
summary: "Building durable systems on models and vendors that change, regress, or vanish — and why 'just upgrade' is never free."
---
# Concept - Vendor and Model Churn Risk

> **One-paragraph hook:** Every production AI system sits on a dependency its provider can retire, silently change, reprice, or (for a startup vendor) stop existing altogether. A pinned library version stays put. An LLM endpoint you don't own can shift under you with no code change on your side. Model churn in 2025–2026 moved fast enough that "which model we're on" is now a standing operational risk, not a one-time integration decision.

## The mechanism

Churn comes from several distinct sources, each with its own failure signature.

**Deprecation churn.** Providers retire model snapshots on a schedule, and the schedule is now aggressive. OpenAI's stated policy is at least 6 months' notice for generally available models (as little as 2 weeks for preview models). Its 2026 deprecation wave is one of its largest: 25+ model IDs across `gpt-4`, `o1`, `o4-mini` and older snapshots retire on hard shutdown dates in July and October 2026, and `gpt-3.5-turbo` itself finally retires 23 Oct 2026 (E2, OpenAI's own deprecation changelog, 2026). Anthropic commits to a minimum 60 days' notice for publicly released models and uses dated snapshot IDs (`claude-opus-4-5-20251101`) so a pinned integration doesn't silently move. It still retired Claude Opus 3 on 5 Jan 2026, the first model to go through its full retirement process (E2, Anthropic's own deprecation commitments page, 2026). Both policies favor the provider. The vendor sets the notice window, and an integration pinned to a retiring snapshot has to be re-qualified against a newer model on the vendor's timeline, not yours.

**Silent regression.** Even without a formal deprecation, a provider can change what a model ID serves, and its behavior, with zero notice. This is documented. Chen, Zaharia & Zou (Stanford/UC Berkeley, arXiv:2307.09009, 2023) ran GPT-3.5 and GPT-4 on identical tasks in March vs. June 2023 and found real drift. GPT-4's accuracy at identifying prime vs. composite numbers fell from 84% to 51%, both models made more code-formatting errors, and GPT-4 became measurably less willing to answer sensitive or opinion-survey questions (E2, single academic study, tasks and time window specific to 2023; cited for the mechanism, not as a claim about current models). The mechanism generalizes. A tuned prompt or a passing eval suite captures behavior at one moment, and nothing keeps the endpoint behind a non-dated alias fixed. That's why [[Concept - The Evaluation Gap]] and vendor churn are one failure surface seen from two sides: an eval suite that runs only at launch can't catch a regression the vendor introduces six months later.

**Price/quality volatility.** The cost of a fixed unit of capability fell roughly an order of magnitude per year across 2023–2026 (mechanism in [[Concept - Token Price Deflation]]). Good for margins, but the model that was cost-optimal at launch very likely isn't a year later, which creates pressure to re-benchmark and re-optimize on a cadence most teams don't budget for.

**Provider concentration and lock-in.** Proprietary features (structured-output modes, tool-call formats, prompt-caching semantics, context-window length) each add switching cost, and it compounds the longer a system runs on one vendor's API surface. A model-agnostic abstraction layer, a thin interface that normalizes calls across providers, defends against this. The price is waiting for the abstraction to catch up before you get the newest provider-specific feature.

**Vendor mortality.** The vendor can disappear, not just the model. Builder.ai was backed by Microsoft and the Qatar Investment Authority, raised as much as $445M, and reportedly peaked at a $1.2-1.5B valuation depending on the round cited. It filed for insolvency 20 May 2025 after lender Viola Credit seized $37M from its accounts (leaving ~$5M restricted), and customers who depended on its platform were stranded overnight. Bloomberg's later reporting found it had also inflated its 2024 revenue (claimed $220M vs. an actual ~$55M) (E2/E3, TechCrunch/Rest of World/Bloomberg reporting and court filings, May-Jul 2025).

Inflection AI is the subtler version. In March 2024 Microsoft paid Inflection roughly $650M to license its models and hired its co-founders and most of its technical staff in a "reverse acqui-hire," a deal built to avoid the regulatory review a full acquisition would trigger. Inflection didn't shut down, but Pi's development pace and competitive position slowed measurably once the people who built it left (E2, TechCrunch/The Information reporting, 2024; [[Breakdown - Frontier Lab Economics]] covers the burn dynamics that make this outcome common). Neither case is a model deprecation. In both, the company changed shape in a way customers didn't choose and couldn't stop.

The base rate makes this a portfolio-level risk, not a tail case. Of roughly 14,000 AI startups launched in 2024, an estimated ~3,800 shut down in 2025 and another ~1,800 by early 2026, a ~40% failure rate inside 24 months (E1, SimpleClosure/industry shutdown-tracking analysis, 2026; an aggregator estimate, not an audited count, tier accordingly).

## In practice

One discipline holds up against every source of churn: **pin, gate, and abstract.**

- **Pin dated snapshots** for anything in production, never a floating alias. A floating alias (`gpt-4o`, `claude-opus-4-5`) is convenient, but it lets the vendor's release calendar define "the model I'm calling."
- **Gate every swap behind the eval suite** built for [[Concept - The Evaluation Gap]]. A model swap, forced or voluntary, is a deploy and gets the same regression check as a code change. Teams that treat "just point at the new model" as a config change find the regression in production.
- **Abstract the provider surface** where portability matters (structured output, tool calling, retrieval interfaces), so a forced migration is a re-point and not a rewrite. Accept that the abstraction delays access to provider-specific capability.
- **Budget the swap, not just the subscription.** Every model upgrade, forced or chosen, reopens the prompt-tuning and eval bill. AI TCO estimates that count only the token price routinely leave this recurring cost out.

## Failure modes

- **"It worked last week" incidents** with no code change on your side. Classic sign of an unpinned model or a provider-side silent update. The fix is dated pinning plus a continuous regression eval; code review won't find it.
- **Deprecation deadline surprise.** A retirement notice arrives with the standard 60-90 day window, and the team finds the migration means re-tuning prompts and re-running the eval suite from scratch, because nobody budgeted swap cost as a recurring line.
- **Vendor-mortality exposure on a critical path.** A core workflow depends on a Series A or B vendor with unclear runway. The failure comes all at once, as a bankruptcy filing or acqui-hire announcement with days of warning (Builder.ai's customers had essentially none).
- **Lock-in found too late.** The team built straight against one provider's proprietary tool-call schema or caching semantics. With no abstraction layer, leaving means a rewrite.

## The non-obvious

"Just upgrade to the new model" is never free, and treating it as free is the most common budgeting error in production LLM systems. Every swap, whether forced by a deprecation or chosen because a newer model is better or cheaper, reopens the eval-and-prompt-tuning bill. Prompts tuned to one model's behavior (its verbosity, its tool-call formatting quirks, its refusal boundaries) don't transfer cleanly, and the only way to know whether the new model regressed on your task is to re-run the eval suite you built for launch.

So frontier progress is a standing deployment cost as well as a benefit. A team that ships once and never revisits its model choice is either accumulating regression risk (if it never re-checks) or re-qualification debt (if it does). There's no third option. [[Deep Dive - Bubble or Boom]] covers how this compounds industry-wide: a wave of frontier-lab and provider consolidation would turn today's optional swap into a forced one, all at once, for every team that didn't abstract.

## Connections
- [[Concept - Token Price Deflation]] — the price side of volatility; falling cost per unit of capability is what makes re-benchmarking a recurring, not one-time, task.
- [[Decision - Build vs Buy vs Wrap]] — churn risk is a direct input to the build-vs-buy calculus: a vendor dependency is a churn exposure a build avoids and a buy accepts.
- [[Breakdown - Frontier Lab Economics]] — the burn dynamics behind why AI-startup vendors are prone to acqui-hires, shutdowns, and restructurings.
- [[Concept - The Evaluation Gap]] — the eval suite that should exist for launch is the same asset that gates every subsequent model swap; without it, churn is undetectable until it's already broken something.
- [[Gotchas - Enterprise AI Adoption]] — silent model-update regression and vendor lock-in are catalogued there as symptom-first production pitfalls.
- [[Concept - The Pilot-to-Production Gap]] — a system that never accounted for churn is a system that will re-enter "pilot" status the day its underlying model is retired.
- [[Concept - Agentic Deployment Risk]] — agentic systems compound churn risk because a silent regression in one step propagates through a multi-step trajectory.
- [[Deep Dive - Bubble or Boom]] — industry-level consolidation or a funding pullback would turn distributed vendor-mortality risk into a correlated shock across many deployments at once.
- [[Reference - Model Genealogy]] — tracks which models descend from which, useful context for understanding what a "swap" actually changes under the hood.
- [[Concept - LLM Observability and Tracing]] — the instrumentation that actually catches a silent regression in production rather than discovering it from a user complaint.

## Sources
- OpenAI — API deprecations page / 2026 deprecation changelog (accessed 2026) — notice-period policy and the 2026 model retirement wave.
- Anthropic — "Commitments on model deprecation and preservation" and model-deprecations documentation (accessed 2026) — 60-day minimum notice, dated snapshot IDs, Claude Opus 3 retirement (5 Jan 2026).
- Chen, L., Zaharia, M., Zou, J. (2023) — "How Is ChatGPT's Behavior Changing over Time?" arXiv:2307.09009 — documented drift in GPT-3.5/GPT-4 behavior between March and June 2023 snapshots.
- TechCrunch, Rest of World, Bloomberg — reporting on Builder.ai's May 2025 insolvency filing, the preceding cash seizure, and the subsequent revenue-inflation findings.
- TechCrunch, The Information, DeepLearning.AI's *The Batch* — reporting on Microsoft's March 2024 Inflection AI reverse acqui-hire.
- SimpleClosure / industry startup-shutdown tracking (2026) — AI startup failure-rate estimate (E1, aggregator analysis, not an audited count).
