---
tags: [playbook, domain/ai-economics, level/core]
aliases: [AI ROI measurement, calculating AI ROI, gen AI ROI methodology]
summary: "An end-to-end procedure for producing a defensible, falsifiable AI ROI number instead of the vanity metrics behind most claimed ROI."
---
# Playbook - Measuring AI ROI

> **Goal:** an AI ROI figure that would survive a skeptical CFO or auditor, instead of a number produced by comparing a vibe to a headline. **When to run this:** before a pilot's budget is scaled to production, before any ROI number leaves the building, and every quarter after that for anything already in production. **Prerequisites:** a documented pre-AI baseline (or enough historical records to build one retroactively), production usage logs ([[Concept - LLM Observability and Tracing]]), and the ability to run an A/B test or holdout instead of a straight before/after comparison.

## Steps

1. **Baseline the human/legacy process before you deploy.** Measure the pre-AI process's cost, time and quality/error rate on a representative task sample. You should end up with a documented number ("$X per ticket resolved, Y minutes median, Z% error rate") dated before the AI system goes live. Skip this and deploy first, and there's no pre-AI number to compare against. Any post-hoc ROI claim is then unfalsifiable by construction, and that's the most common reason claimed AI "ROI" falls apart under scrutiny (see [[Concept - The Pilot-to-Production Gap]]).

2. **Compute the fully-loaded cost.** Add up inference tokens and retries, build/integration engineering time (amortized), prompt/eval maintenance, human oversight and review time, and error-remediation cost. Fully-loaded cost typically runs several multiples of raw token spend once oversight and remediation are in. If your total comes out roughly equal to your token spend, you're almost certainly missing the hidden denominator: the oversight and remediation lines that turn a positive pilot negative at scale (see [[Concept - Unit Economics of LLM Products]]).

3. **Attribute the effect with a counterfactual.** Randomize a matched set of tasks or users into AI-assisted and non-AI-assisted conditions over the same time window. The output is an effect size with a confidence interval, not a point estimate from comparing "before" to "after". Before/after comparisons confound seasonality, other concurrent process changes and self-selection.

   This has already bitten people. METR's July 2025 randomized trial found experienced developers took **19% longer** on real coding tasks with AI tools, while the same developers *believed* afterward that AI had made them **~20% faster** (E3, METR, n=16, 246 tasks). Self-report and measurement pointed in opposite directions. METR's February 2026 follow-up found the effect shrank to a statistically insignificant **-4%** (CI: -15% to +9%), after developers refusing to work without AI (30-50% declined non-AI tasks even at $50/hour) worsened the sample's self-selection bias. METR now flags the 2025 headline as "out of date." The takeaway isn't that AI helps or hurts. **Only a controlled counterfactual, run and re-run, catches an effect this easy to get backwards from self-report** (see [[Breakdown - The METR Developer Slowdown RCT]], [[Reference - Developer Productivity Studies]]).

4. **Pick outcome metrics that survive Goodhart's law.** Track outcomes that have to *hold*: tickets resolved and still resolved, pull requests merged and not reverted. Never proxies like messages sent or suggestions accepted. As usage matures, the Goodhart-resistant metric and the easy proxy drift apart. If your only dashboard is acceptance rate or engagement, you're measuring adoption, and it can climb while real outcomes stay flat or get worse (see [[Concept - The Evaluation Gap]]).

5. **Subtract the quality and liability tail.** Net out downstream costs the gross savings created: support deflection that raises churn, AI-authored code or content that raises defect/rework rates, hallucination-driven liability events. Net savings come in below gross, sometimes far below. A reported ROI with gross savings and no tail-cost line hasn't been measured against a liability side at all. [[Lore - Hallucination Liability Incidents]] shows what that tail can cost per incident.

6. **Sanity-check against the public spread, then trust your own number over either end of it.** Compare against the two most-cited public benchmarks: IDC's Microsoft-commissioned "$3.70 returned per $1 spent" (E1, vendor-sponsored survey, Jan 2025) and MIT Project NANDA's finding that ~95% of enterprise gen-AI pilots show no measurable P&L impact (E2, Jul-Aug 2025). Your number should land somewhere explainable by your deployment's maturity and integration depth, not a match for either headline. A figure that suspiciously matches a vendor-sponsored benchmark, or one that just declares "we're in the 5%" without the steps above behind it, hasn't been measured (full context in [[Reference - AI Impact by Business Function]]).

7. **Recompute quarterly on real production data.** Rerun steps 1-6 with current token prices and current usage volume, not pilot-era numbers. Falling token cost ([[Concept - Token Price Deflation]]) helps the cost side. But agentic and reasoning workloads burn far more tokens per task than the pilot's chat-style usage, and that can hurt the volume side faster than deflation helps. An ROI figure computed once at pilot stage and never revisited is stale by definition. Pilot ROI rarely survives production scale in either direction, and only recomputation tells you which way it moved.

## Verification

The number is defensible only if all four hold:

- (a) it's measured against a documented pre-deployment baseline, not inferred after the fact;
- (b) it comes from a counterfactual (A/B or holdout), not a before/after comparison;
- (c) it's net of fully-loaded cost and the quality/liability tail, not gross savings;
- (d) rerunning the procedure on a fresh quarter of production data gives a similar number, or a difference you can explain (token price change, usage mix change, workflow change).

Missing any of the four, it's a claim and not a measurement. Tier it E0/E1 accordingly under the Applied Wing evidence law instead of stating it as fact.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| ROI looks great in the deck but finance can't find the savings in the actual budget | No pre-AI baseline was ever measured; the "savings" numerator is inferred, not observed | Step 1 |
| ROI collapses once the pilot scales from a small team to the whole org | Fully-loaded cost undercounted oversight/build/maintenance cost that scales with headcount | Step 2 |
| Users report big time savings, but throughput or output metrics don't move | Self-report bias, the same pattern METR measured (perceived speedup, measured slowdown or null effect) | Step 3 |
| Adoption/engagement metrics are up, but nobody can name a business outcome that changed | Tracking proxy metrics (usage, acceptance) instead of Goodhart-resistant outcome metrics | Step 4 |
| Reported net savings quietly evaporate a quarter or two after rollout | Quality/liability tail (rework, churn, incidents) was never subtracted, or cost/usage assumptions went stale | Steps 5 and 7 |

## Connections

- [[Concept - Unit Economics of LLM Products]] — the fully-loaded cost math that Step 2 requires.
- [[Concept - The Pilot-to-Production Gap]] — the organizational failure mode that makes Step 1's baseline routinely get skipped.
- [[Breakdown - The METR Developer Slowdown RCT]] — the full trial design and result behind Step 3's counterfactual-attribution requirement.
- [[Concept - The Evaluation Gap]] — why proxy metrics substitute for real outcome measurement in Step 4.
- [[Lore - Hallucination Liability Incidents]] — the incident record behind Step 5's liability-tail subtraction.
- [[Reference - AI Impact by Business Function]] — the per-function evidence base for sanity-checking a measured ROI number in Step 6.
- [[Reference - Developer Productivity Studies]] — the wider set of studies (beyond METR) to weigh a coding-specific ROI claim against.
- [[Concept - Token Price Deflation]] — the cost-side variable that makes Step 7's quarterly recomputation necessary.
- [[Concept - Outcome-Based Pricing]] — how a defensible ROI measurement (this playbook) becomes the basis for pricing a product on outcomes rather than seats or tokens.
- [[Concept - LLM Observability and Tracing]] — the instrumentation prerequisite that makes Steps 2-4 possible from production data rather than guesswork.

## Sources

- METR, "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity" (Jul 10, 2025) — 19% slower / 20% believed-faster RCT result, n=16, 246 tasks.
- METR, "We are Changing our Developer Productivity Experiment Design" (Feb 24, 2026) — follow-up finding -4% (CI -15% to +9%) and explicit "results out of date" notice on the 2025 study.
- IDC, "The Business Opportunity of AI," commissioned by Microsoft (Jan 2025) — $3.70 per $1 claim.
- MIT Project NANDA, "The GenAI Divide: State of AI in Business 2025" (Jul-Aug 2025) — 95% of pilots show no P&L impact.
