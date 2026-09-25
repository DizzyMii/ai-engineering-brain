---
tags: [concept, domain/adoption-blockers, level/core]
aliases: [eval gap, no ground truth problem, vibes-based deployment]
summary: "Most enterprises deploy GenAI without a task-specific eval set, so they can't quantify accuracy or defend a go/no-go call."
---
# Concept - The Evaluation Gap

> **One-paragraph hook:** Ask most teams running a production GenAI feature how accurate it is on their actual task, and the honest answer is "we don't really know." They shipped on a demo and a handful of spot-checks, with no labeled eval set, so they have nothing to catch a regression, defend a go/no-go call, or give a stakeholder anything firmer than a vibe. That missing instrument, more than model capability, is what keeps most enterprise AI from earning institutional trust.

## The mechanism

Classic ML came with a discipline built in. You can't train a model without labeled data, and that data doubles as a held-out test set with a scalar accuracy number. Generative AI dropped that. A team can build a working RAG system or agent, watch it produce plausible answers in a demo, and ship it without an equivalent test set, because nothing forced them to build one. So most enterprises run GenAI systems with no task-specific eval set at all: no fixed set of representative inputs with known-correct (or known-acceptable) outputs, no regression suite, no statistical baseline. It's a direct case of what [[Concept - The Pilot-to-Production Gap]] calls the "learning gap". Nobody can show that an unmeasured system is improving, degrading or even working, so trust either floats on anecdote or collapses at the first visible failure.

The gap is hard to close for three reasons, beyond neglect. (1) Generative outputs often have no single correct answer. Exact-match scoring doesn't apply, so teams fall back on spot-checking a handful of cases, which misses the "fixed case A, broke case B" regressions a full suite would catch. (2) Public benchmarks (MMLU, SWE-bench and similar) measure a different distribution from an enterprise's proprietary task mix, so a high score says little about production accuracy. [[Concept - Benchmark Contamination]] inflates that weak signal further, as training-set leakage lifts public scores above true held-out performance. (3) Without labels, teams use an LLM as the grader ([[Concept - LLM-as-Judge]]). That brings its own biases (position, verbosity, self-preference), and the judge has to be validated against a human-labeled slice before you can trust it. Now you have a second eval problem on top of the first.

## In practice

The sharpest documented case of perceived value diverging from measured value is the METR randomized controlled trial (Jul 2025). 16 experienced open-source developers completed 246 real tasks in their own mature repositories (avg 22k+ GitHub stars, 1M+ lines of code), each task randomly assigned to allow or disallow AI tools (Cursor Pro with Claude 3.5/3.7). With AI they were measured 19% *slower*. Beforehand they'd forecast a ~24% speedup, and afterward they still believed AI had made them about 20% faster (E2, single RCT, n=16; a small sample, measuring early-2025 tools on developers' own large repos, not a universal claim about AI coding). [[Breakdown - The METR Developer Slowdown RCT]] and [[Reference - Developer Productivity Studies]] have the fuller context and caveats. It matters here because it's a demonstration, not an argument. Without a controlled measurement, the developers' self-reports would have given the opposite sign from the truth. METR applies the same discipline to capability growth over time in [[Concept - METR Time Horizons]], which is worth reading as the same rigor aimed at a different question.

Once teams do start measuring, weak statistics make things worse. A two-point swing on a fifty-example spot-check is noise, yet it routinely gets treated as proof a prompt change helped or hurt. [[Concept - Statistical Rigor in Model Evaluation]] has the sample-size and significance math most ad hoc enterprise evals skip. Teams that close the gap consistently do it the same way. They build a labeled set of real cases *before* the system ships, not after a complaint; [[Playbook - Crossing the Pilot-to-Production Gap]] specifies 50–500, including deliberately adversarial and edge-case inputs. [[Deep Dive - Designing an Eval Harness]] covers construction. At this level the point is that building the eval set is product work, not a chore to clear before "real" development starts.

## Failure modes

- **Silent regression on model or prompt swap.** With no gating eval suite, a provider endpoint update or a "small" prompt tweak degrades quality invisibly until a customer complains. [[Concept - Vendor and Model Churn Risk]] covers the upstream cause.
- **Spot-check blindness.** Eyeballing ten outputs catches obvious breakage but reliably misses a change that fixes one failure class while introducing another. The sample looks fine and the population is wrong.
- **LLM judge without validation.** An LLM grader with no human-labeled calibration slice launders judge bias into false rigor. The judge needs its own accuracy number against ground truth before its scores mean anything.
- **Perception-reality inversion under cognitive load.** As METR shows, self-reported speedup can have the *wrong sign* against measured speedup on unfamiliar or high-context tasks. The harder and more expert the task, the less you can trust the anecdote. This compounds [[Concept - The Verification Tax]], since checking AI output takes effort that's easy to underestimate.

## The non-obvious

Building the eval set is the real work, not preparation for it. Teams that get across the pilot-to-production boundary invest up front in 50–500 labeled real cases, adversarial and edge inputs included, before writing the production system. Teams that skip it ship on a demo and regress silently, again and again, finding each regression only when a user does. The trade is lopsided. An eval suite takes a few days to a few weeks to build, then pays for itself on every model swap, prompt change and vendor negotiation for the life of the system. Without one, each of those is a blind deploy.

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
