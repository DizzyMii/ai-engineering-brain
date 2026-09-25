---
tags: [breakdown, domain/applied-software, level/advanced]
aliases: [AI code migration, Amazon Q Java migration, LLM code modernization, automated code migration]
summary: "Large-scale migrations are AI's most defensible ROI — Amazon Q and Google's LLM programs, and why a cheap verification oracle is the cause."
---

# Breakdown - AI-Driven Code Migrations

> The strongest real-world evidence that AI writes economically valuable code comes from boring, high-volume migrations (version upgrades, framework ports, type-widening across huge codebases), more than from autocomplete or feature-building agents. Amazon (Q Developer, 2024) and Google (a 2025 research paper) both ran production programs and published numbers. Model brilliance isn't why it works. A migration ships with a built-in oracle, *does it still compile and pass the tests?*, and that condition narrows the [[Concept - The Capability-Reliability Gap]]. (as of 2026)

## The headline numbers

| Program | Task | Scale | Claimed outcome | Tier |
|---|---|---|---|---|
| Amazon Q Developer | Java 8/11 → 17 | ~30,000 internal apps | 4,500 developer-years saved; $260M/yr efficiency; ~50 dev-days → a few hours per app; >half of prod Java modernized "in a small number of months" | E2 (Amazon's own, Jassy Q2-2024 earnings call, Aug 2024) |
| Google (Ziftci et al.) | 32-bit → 64-bit integer ID widening | 39 migrations, 3 developers, 12 months | 595 change-lists, 93,574 edits; **74.45% of change-lists and 69.46% of edits LLM-generated**; developers self-reported ~50% less total time vs manual | E2 (company study, self-reported time; arXiv 2504.09691, Apr 2025) |

Two numbers to remember. Amazon's **$260M/yr and 4,500 developer-years** is a modeled counterfactual, not a measured line-item saving, and part of the $260M is the *runtime performance* win of newer Java, not labor. Google's **~70% of edits machine-generated** came with developer time cut in half. Both are the vendor grading its own homework. They're still the most credible AI-coding ROI claims around, because migrations are measurable.

## How it works

A migration is a search-and-transform problem with a verifier attached. Both programs converge on the same pipeline:

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

Discovery is harder than generation. Google's system uses Kythe, its code-index graph, to walk direct and indirect references to a field up to a fixed reference distance. It then buckets each site by confidence that it needs changing. Some sites are identified with 100% confidence as *not* needing a change, and the LLM never runs on them. The model only fires where a human-scale judgment is required.

The LLM does the local rewrite. Given a specific location and its surrounding context, it produces the edit: change the type, update the call site, fix the resulting compile break. Google used an internal LLM trained on its monorepo and developer activity (the DIDACT line of work, E2/E1, Google's own description). Amazon Q wraps frontier models behind an agentic "code transformation" job.

The oracle closes the loop. Compilation and the existing test suite decide whether an edit is accepted. Feature work lacks this. A migration's spec is implicit but checkable ("behave identically, just on the new version/type"), so wrong edits get caught mechanically before they ship. Meta's assured-LLMSE filter in [[Concept - AI in Software Testing]] runs on the same principle: keep only output that passes an automated gate. It also explains how migrations mostly dodge the [[Concept - The Verification Tax]] that drags down most enterprise AI deployments. The tax falls toward zero when the oracle is a compiler and a test suite, not a human reading a diff.

Humans stay in the loop, and they're needed. Google had 3 developers steering 39 migrations; Amazon had engineers reviewing transformations. The gain is *throughput per engineer* (one dev drives thousands of edits), not autonomy.

## The clever parts

**Pick tasks where verification is nearly free.** The whole ROI case rests on the oracle. A Java version bump or an int32→int64 widening has a crisp pass/fail: it compiles, tests are green, behavior is preserved. You don't need the model to be *right*. You need it right *often enough that checking the batch is cheaper than writing it*. That's the verification tax driven to near zero, and the idea transfers well beyond code ([[Concept - Support Deflection Economics]] runs the same logic in a different function).

**Confidence-bucketed discovery.** Skipping the model on the ~majority of sites that provably need no change is how 93,574 edits stay tractable for 3 people. LLM calls and human review go only to real ambiguity.

**Batch parallelism over depth.** Migrations break into thousands of small, independent, separately verifiable edits, which suits an agent fleet. A single long-horizon feature is the opposite case, where errors compound (see [[Deep Dive - Agentic Coding in Production]]).

**Modeled savings as headline results.** Cynically clever. "4,500 developer-years" is a counterfactual, what the manual path *would* have cost, so it's enormous and unfalsifiable. It isn't a lie. It isn't an audited E3 number either.

## What it got wrong / what's dated

- **Every big number comes from the tool's vendor.** Amazon sells Q; Google published to show off its internal capability. Nobody has independently audited "$260M/yr" or "4,500 developer-years." Treat them as E2, and remember that "developer-years saved" is a model output.
- **Narrow task class.** Google's paper covers one migration *type* (ID widening). Amazon's headline is one upgrade (Java LTS). Neither shows that "AI migrates anything." Take away the clean oracle (semantics change, no test coverage, cross-service contracts) and the property that makes this work is gone.
- **Selection and survivorship.** We hear about the migrations that succeeded and were publishable. The 30% of Google edits that were *not* LLM-generated, and the human review time, get compressed out of the headline.
- **The contrast that dates the hype.** The same tooling that "saved 4,500 developer-years" on migrations made experienced developers **19% slower** on open-ended tasks in the [[Breakdown - The METR Developer Slowdown RCT]]. Task structure decides the sign of the outcome. Model IQ doesn't.

## What to steal

- **AI value scales with how cheaply you can verify output.** How smart the model is matters less. With a cheap correctness oracle (compiler, type checker, golden tests, idempotent re-run), AI multiplies output. Without one, you buy speed and pay it back in review and rework.
- **Route work by verifiability.** Migrations, dependency bumps and mechanical refactors get high autonomy behind an automatic gate. Ambiguous, semantic, cross-service work stays assist-only. That's the core of [[Decision - Choosing an AI Coding Workflow]].
- **Build the oracle before you bring in the model.** The first engineering spend on an AI migration is test coverage and a reproducible build/verify loop. That's what turns a plausible-code generator into one you can trust.
- **Measure the counterfactual honestly.** "Developer-years saved" is a fine internal planning number and a bad external truth claim. Report throughput per engineer and review load next to it (see [[Reference - AI Impact by Business Function]], and [[Playbook - Measuring AI ROI]] for instrumenting the counterfactual without laundering it into fact).

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
