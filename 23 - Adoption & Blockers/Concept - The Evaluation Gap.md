---
tags: [concept, domain/adoption-blockers, level/core]
aliases: [eval gap, no ground truth problem, vibes-based deployment]
summary: "Most enterprises deploy GenAI without a task-specific eval set, so they can't quantify accuracy or defend a go/no-go call."
---
# Concept - The Evaluation Gap

> **One-paragraph hook:** Ask most teams running a production GenAI feature how accurate it is on their actual task, and the honest answer is "we don't really know." They deployed on the strength of a demo and a handful of spot-checks, not a labeled eval set, so they have no instrument to detect a regression, defend a go/no-go decision, or tell a stakeholder anything more rigorous than a vibe. That absence — not model capability — is what blocks most enterprise AI from getting institutional trust.

## The mechanism

Classic ML shipped with a built-in discipline: you can't train a model without labeled data, and that same labeled data doubles as a held-out test set with a scalar accuracy number. Generative AI broke that discipline. A team can build a working RAG system or agent, see it produce plausible-looking answers in a demo, and ship it — with no equivalent labeled test set, because nothing forced them to build one. The result is that most enterprises operate GenAI systems with no task-specific eval set at all: no fixed set of representative inputs with known-correct (or known-acceptable) outputs, no regression suite, no statistical baseline. This is a direct expression of what [[Concept - The Pilot-to-Production Gap]] calls the "learning gap" — a system nobody is measuring cannot be shown to be improving, degrading, or even working, so trust either free-floats on anecdote or collapses on the first visible failure.

Three structural reasons this gap is hard to close, not merely neglected: (1) generative outputs frequently have no single correct answer, so naive exact-match scoring doesn't apply and teams default to spot-checking a handful of cases, which misses the "fixed case A, broke case B" regression pattern that a full eval suite would catch; (2) public benchmarks (MMLU, SWE-bench, and similar) measure a different distribution than an enterprise's actual proprietary task mix, so a high benchmark score is only weakly informative about production accuracy — and that weak signal is further inflated by [[Concept - Benchmark Contamination]], where training-set leakage lifts public scores above true held-out performance; (3) without labels, teams reach for an LLM as the grader ([[Concept - LLM-as-Judge]]), which introduces its own biases (position, verbosity, self-preference) and must itself be validated against a human-labeled slice before it can be trusted — a second eval problem stacked on the first.

## In practice

The sharpest documented case of "perceived value" diverging from "measured value" is the METR randomized controlled trial (Jul 2025): 16 experienced open-source developers completed 246 real tasks in their own mature repositories (avg 22k+ GitHub stars, 1M+ lines of code), each task randomly assigned to allow or disallow AI tool use (Cursor Pro with Claude 3.5/3.7). Developers were measured 19% *slower* with AI assistance than without it — while forecasting a ~24% speedup beforehand and still believing, after the fact, that AI had made them about 20% faster (E2, single RCT, n=16 — small sample, and it measures early-2025 tools on developers' own large repos specifically, not a universal claim about AI coding) (see [[Breakdown - The METR Developer Slowdown RCT]], [[Reference - Developer Productivity Studies]] for the fuller context and caveats). The result matters here because it is a demonstration, not an argument: without a controlled, measured eval, the same developers' self-reported experience would have shown the opposite sign from the truth. METR applies the same measurement discipline outside single RCTs, tracking capability growth itself over time in [[Concept - METR Time Horizons]] — worth reading as the same rigor standard applied to a different question.

Statistical illiteracy compounds the gap once teams do start measuring: a two-point swing on a fifty-example spot-check is noise, not signal, yet it's routinely treated as proof a prompt change helped or hurt — see [[Concept - Statistical Rigor in Model Evaluation]] for the sample-size and significance math that most ad hoc enterprise evals skip entirely. Teams that do close the gap consistently do it the same way: they build a labeled set of real cases — [[Playbook - Crossing the Pilot-to-Production Gap]] specifies 50–500, including deliberately adversarial and edge-case inputs — *before* the system ships, not after a complaint. [[Deep Dive - Designing an Eval Harness]] covers the construction mechanics; the point at this level is that building that eval set is itself the product work, not a side task to get through before "real" development starts.

## Failure modes

- **Silent regression on model or prompt swap.** Without a gating eval suite, a provider's endpoint update or a "small" prompt tweak degrades quality with no visible signal until a customer complains — see [[Concept - Vendor and Model Churn Risk]] for the upstream cause.
- **Spot-check blindness.** Manually eyeballing ten outputs catches obvious breakage but systematically misses the pattern where a change fixes one failure class while introducing another — the net effect looks fine on the sample and is wrong on the population.
- **LLM-judge-without-validation.** Using an LLM grader with no human-labeled calibration slice launders judge bias into a false sense of rigor; the judge needs its own accuracy number against ground truth before its scores mean anything.
- **Perception-reality inversion under cognitive load.** As METR shows, self-reported speedup can have the *wrong sign* relative to measured speedup on unfamiliar or high-context tasks — the harder and more expert the task, the less trustworthy the anecdote (this compounds [[Concept - The Verification Tax]], where checking AI output is itself effortful and easy to underestimate).

## The non-obvious

Building the eval set is not preparation for the real work — it *is* the real work. Teams that successfully cross the pilot-to-production boundary invest upfront in 50–500 labeled real cases, including adversarial and edge inputs, before writing the production system; teams that skip this ship on the strength of a demo and regress silently and repeatedly, discovering each regression only when a user does. The asymmetry is stark: an eval suite costs a few days to a few weeks to build and then pays for itself on every subsequent model swap, prompt change, and vendor negotiation for the life of the system — while its absence means every one of those events is a blind deploy.

## Connections
- [[Concept - The Pilot-to-Production Gap]] — the evaluation gap is the concrete, addressable instrument-failure behind NANDA's "learning gap" framing.
- [[Playbook - Crossing the Pilot-to-Production Gap]] — specifies eval-set-before-launch as the load-bearing step (Step 1) of the crossing procedure.
- [[Gotchas - Enterprise AI Adoption]] — "demo works, production doesn't" is this concept's most common symptom in the wild.
- [[Concept - The Verification Tax]] — the cost of checking AI output by hand is what an eval suite is designed to amortize and quantify.
- [[Concept - Vendor and Model Churn Risk]] — a gating eval suite is the only reliable defense against silent regressions from provider-side model swaps.
- [[Concept - The Capability-Reliability Gap]] — an eval set is how you actually measure where a system sits on the reliability curve, rather than guessing from a demo.
- [[Breakdown - The METR Developer Slowdown RCT]] — the sharpest documented case of measured value diverging from perceived value.
- [[Reference - Developer Productivity Studies]] — the broader evidence base this single RCT sits inside, with its caveats and competing studies.
- [[Deep Dive - Designing an Eval Harness]] — the construction mechanics (sampling, labeling, scoring) for building the eval set this concept argues is mandatory.
- [[Concept - LLM-as-Judge]] — the common crutch for scoring generative output without ground truth, and its bias failure modes.
- [[Concept - Benchmark Contamination]] — why the public benchmark numbers teams substitute for a real eval are inflated and non-transferable.
- [[Concept - Statistical Rigor in Model Evaluation]] — the sample-size discipline needed so a small eval set doesn't produce its own false signal.
- [[Concept - METR Time Horizons]] — the same rigorous-measurement standard METR applies to a single productivity RCT here, applied instead to capability growth over time (cross-domain: trajectory).

## Sources
- METR — "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity" (10 Jul 2025). RCT design, 19% measured slowdown vs. 24% forecast and ~20% perceived speedup.
- Simon Willison — commentary and summary of the METR study (12 Jul 2025), useful for the perception-gap framing.
- Zvi Mowshowitz — "On METR's AI Coding RCT" (Substack, Jul 2025) — critical discussion of the study's scope and limits (n=16, early-2025 tools, mature-repo context).
