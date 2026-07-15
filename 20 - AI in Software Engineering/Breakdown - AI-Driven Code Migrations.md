---
tags: [breakdown, domain/applied-software, level/advanced]
aliases: [AI code migration, Amazon Q Java migration, LLM code modernization, automated code migration]
summary: "Large-scale migrations are AI's most defensible ROI — Amazon Q and Google's LLM programs, and why a cheap verification oracle is the cause."
---

# Breakdown - AI-Driven Code Migrations

> The strongest real-world evidence that AI writes economically valuable code is not autocomplete or agents building features — it is boring, high-volume migrations: version upgrades, framework ports, and type-widening across huge codebases. Amazon (Q Developer, 2024) and Google (a 2025 research paper) both ran production programs and published numbers. The reason it works is not model brilliance; it is that a migration ships with a built-in oracle — *does it still compile and pass the tests?* — which is exactly the condition that narrows the [[Concept - The Capability-Reliability Gap]]. (as of 2026)

## The headline numbers

| Program | Task | Scale | Claimed outcome | Tier |
|---|---|---|---|---|
| Amazon Q Developer | Java 8/11 → 17 | ~30,000 internal apps | 4,500 developer-years saved; $260M/yr efficiency; ~50 dev-days → a few hours per app; >half of prod Java modernized "in a small number of months" | E2 (Amazon's own, Jassy Q2-2024 earnings call, Aug 2024) |
| Google (Ziftci et al.) | 32-bit → 64-bit integer ID widening | 39 migrations, 3 developers, 12 months | 595 change-lists, 93,574 edits; **74.45% of change-lists and 69.46% of edits LLM-generated**; developers self-reported ~50% less total time vs manual | E2 (company study, self-reported time; arXiv 2504.09691, Apr 2025) |

The two numbers to hold onto: Amazon's **$260M/yr and 4,500 developer-years** (a modeled counterfactual, not a measured line-item saving — note the $260M is partly the *runtime performance* win of newer Java, not purely labor), and Google's **~70% of edits machine-generated** while still cutting developer time in half. Both are the vendor grading its own homework; both are still the most credible AI-coding ROI claims in existence, precisely because migrations are measurable.

## How it actually works

A migration is a search-and-transform problem with a verifier attached. The generic pipeline both programs converge on:

```
┌─────────────┐   ┌──────────────────┐   ┌─────────────────┐   ┌──────────────┐
│ 1. Discover  │──▶│ 2. Categorize     │──▶│ 3. LLM transform │──▶│ 4. Verify     │
│ change sites │   │ (needs change?)   │   │ each site/CL     │   │ compile+tests │
│ (index/AST/  │   │ high/low/no-conf  │   │                  │   │               │
│  Kythe refs) │   └──────────────────┘   └─────────────────┘   └──────┬───────┘
└─────────────┘                                    ▲                    │ fail
                                                    └────────────────────┘ retry/repair
                                                                         │ pass
                                                                    ┌────▼─────┐
                                                                    │5. Human   │
                                                                    │ review→   │
                                                                    │ submit CL │
                                                                    └──────────┘
```

- **Discovery, not generation, is the hard part.** Google's system uses Kythe (its code-index graph) to walk direct and indirect references to a field up to a fixed reference distance, then buckets each site by confidence that it needs changing — including sites identified with 100% confidence as *not* needing a change, so the LLM is never invoked there. The model only fires where a human-scale judgment is actually required.
- **The LLM does the local rewrite.** Given a specific location plus surrounding context, the model produces the edit (change the type, update the call site, fix the resulting compile break). Google used an internal LLM trained on its monorepo and developer activity (the DIDACT line of work — E2/E1, Google's own description); Amazon Q wraps frontier models behind an agentic "code transformation" job.
- **The oracle closes the loop.** Compilation and the existing test suite decide whether an edit is accepted. This is what makes migrations different from feature work: the specification is implicit-but-checkable ("behave identically, just on the new version/type"), so wrong edits are caught mechanically instead of shipping. This is the same principle behind Meta's assured-LLMSE filter in [[Concept - AI in Software Testing]] — keep only output that passes an automated gate. It is also why migrations largely dodge the [[Concept - The Verification Tax]] that plagues most enterprise AI deployments: the tax collapses toward zero when the oracle is a compiler and a test suite instead of a human reading a diff.
- **Human-in-the-loop is load-bearing, not decorative.** Google kept 3 developers steering 39 migrations; Amazon kept engineers reviewing transformations. The win is *throughput per engineer* (one dev drives thousands of edits), not autonomy.

## The clever parts

- **Pick tasks where verification is nearly free.** The entire ROI case rests on the oracle. A Java version bump or an int32→int64 widening has a crisp pass/fail (compiles, tests green, behavior preserved). That collapses the reliability problem: you don't need the model to be *right*, you need it to be right *often enough that checking the batch is cheaper than writing it*. This is the verification tax driven to near-zero — the transferable insight, and it generalizes far beyond code (link [[Concept - Support Deflection Economics]] — same logic, different function).
- **Confidence-bucketed change discovery.** Not invoking the model on the ~majority of sites that provably don't need changing is what makes 93,574 edits tractable with 3 people. The expensive resource (LLM calls + human review) is spent only on genuine ambiguity.
- **Batch parallelism over depth.** Migrations decompose into thousands of small, independent, individually verifiable edits — the ideal shape for an agent fleet. Contrast a single long-horizon feature, where errors compound (see [[Deep Dive - Agentic Coding in Production]]).
- **Modeled savings framed as headline results.** Cynically clever: "4,500 developer-years" is a counterfactual (what the manual path *would* have cost), which is unfalsifiable and enormous. It is not a lie, but it is not an audited E3 number either.

## What it got wrong / what's dated

- **Every big number is self-reported by the tool's vendor.** Amazon sells Q; Google published to show its internal capability. There is no independent audit of "$260M/yr" or "4,500 developer-years." Treat as E2, and remember "developer-years saved" is a model, not a measurement.
- **Narrow task class.** Google's paper is one migration *type* (ID widening); Amazon's headline is one upgrade (Java LTS). Neither demonstrates general "AI migrates anything." A migration with no clean oracle — semantics change, no test coverage, cross-service contracts — loses the property that makes this work.
- **Selection and survivorship.** We hear about the migrations that succeeded and were worth publishing. The 30% of Google edits that were *not* LLM-generated, and the human review time, are the part the headline compresses away.
- **The contrast that dates the hype.** The same tooling that "saved 4,500 developer-years" on migrations made experienced developers **19% slower** on open-ended tasks in the [[Breakdown - The METR Developer Slowdown RCT]]. Task structure, not model IQ, decides the sign of the outcome.

## What to steal

- **AI value scales with how cheaply you can verify output, not with how smart the model is.** If you can build or already have a cheap correctness oracle (compiler, type checker, golden tests, idempotent re-run), AI is a genuine force multiplier. If you can't, you are buying speed and paying it back in review and rework.
- **Route work by verifiability.** Migrations, dependency bumps, and mechanical refactors → high autonomy behind an automatic gate. Ambiguous, semantic, cross-service work → assist-only. This is the core of [[Decision - Choosing an AI Coding Workflow]].
- **Instrument the oracle before the model.** The first engineering investment in an AI migration is test coverage and a reproducible build/verify loop — that is what converts a plausible-code generator into a trustworthy one.
- **Measure the counterfactual honestly.** "Developer-years saved" is a fine internal planning number and a terrible external truth claim. Report throughput per engineer and review load alongside it (link [[Reference - AI Impact by Business Function]], and [[Playbook - Measuring AI ROI]] for how to instrument the counterfactual without laundering it into fact).

## Connections

- [[Concept - The Capability-Reliability Gap]] — migrations are the case where the gap is *narrow*, because verification is cheap; the whole ROI story is one instance of this concept.
- [[Deep Dive - Agentic Coding in Production]] — migrations are the canonical "where agents actually work" example; this Breakdown is its strongest evidence.
- [[Breakdown - The METR Developer Slowdown RCT]] — the mirror image: same tools, open-ended tasks, negative result; the contrast isolates task structure as the causal variable.
- [[Concept - AI in Software Testing]] — the built-in oracle (compile + tests) is the mechanism migrations share with assured test generation.
- [[Concept - AI's Effect on Code Quality and Security]] — mechanical migrations mostly dodge the maintainability/churn tax that free-form AI code incurs; worth stating why.
- [[Reference - Developer Productivity Studies]] — where these Amazon/Google figures sit in the evidence-tiered catalog, next to the RCTs.
- [[Breakdown - GitHub Copilot's Measured Productivity Impact]] — a different slice of the same "does AI help?" question; migrations are the strongest positive, Copilot RCTs the contested middle.
- [[Concept - Team Workflow Restructuring with AI]] — migrations shift one engineer from author to reviewer-of-thousands-of-edits, the process change made concrete.
- [[Concept - Tool Use and Function Calling]] — the transform step is an LLM driving edit/compile/test tools in a loop; the migration pipeline is a constrained agent (cross-domain: agents).
- [[Concept - Support Deflection Economics]] — the same "value tracks cheap verification" logic governs where AI pays off in a business function (cross-domain: business functions).
- [[Reference - AI Impact by Business Function]] — engineering migrations are one row in the cross-function ROI map (cross-domain: business functions).
- [[Deep Dive - Designing an Eval Harness]] — the compile+test oracle is a domain-specific eval harness; building one is the prerequisite work (cross-domain: evaluation).
- [[Concept - The Verification Tax]] — migrations are the limiting case where the tax of checking AI output collapses to near-zero, which is why their ROI is defensible where free-form AI coding's is not (cross-domain: adoption).
- [[Playbook - Measuring AI ROI]] — how to report "4,500 developer-years saved" as the modeled counterfactual it is, instrumenting throughput and review load instead of laundering it into an audited number (cross-domain: economics).

## Sources

- Ziftci, Nikolov, Sjövall, Kim, Codecasa, Kim (2025) — *Migrating Code At Scale With LLMs At Google*, arXiv 2504.09691. 39 migrations, 3 devs, 12 months; 74.45% of change-lists / 69.46% of edits LLM-generated; ~50% self-reported time reduction. (E2, company study.)
- Andy Jassy, Amazon Q2-2024 earnings call (Aug 2024) — Q Developer migrated ~30,000 apps to Java 17, 4,500 developer-years and $260M/yr saved, ~50 dev-days → hours per app. Reported by Digiday, The Decoder, AWS DevOps blog. (E2, Amazon's own claim, not independently audited.)
- METR (2025) — *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*, arXiv 2507.09089. The counter-case: −19% on open-ended tasks. (E3, RCT, small N.)
- Alshahwan et al. (2024) — Meta *TestGen-LLM* / assured LLMSE. The "keep only what passes an automatic gate" pattern migrations rely on. (E2, Meta's own.)
