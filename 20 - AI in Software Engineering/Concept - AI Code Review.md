---
tags: [concept, domain/applied-software, level/core]
aliases: [AI PR review, automated code review, LLM code review]
summary: "LLMs reviewing pull requests as an LLM-as-judge pass over diffs — strong at shallow bugs, blind to architecture, now a funded market race."
---
# Concept - AI Code Review

> **One-paragraph hook:** AI code review runs an LLM over every pull request the way a human reviewer would skim it — build context, read the diff, flag problems, post comments — except it never gets tired and never skips a file. It caught enough of the mechanical slop that three well-funded startups (CodeRabbit, Graphite, Greptile) built real businesses on it in under two years. It also creates a genuine risk: if the same generation of models both writes the code and blesses it, the human who used to catch what the model missed can quietly disappear from the loop.

## The mechanism

An AI code review tool sits as a bot on the pull-request pipeline (GitHub/GitLab/Bitbucket/Azure DevOps webhook) and on each push runs a fixed loop: build context around the diff, prompt a model to find problems, then post the findings as inline PR comments or a summary. The context-building step is where products differentiate. CodeRabbit and Greptile both index the *whole* codebase up front rather than just the diff — Greptile specifically builds and maintains a repo-wide dependency graph so it can reason about a changed function's callers, not just the lines that changed — while lighter tools fall back to RAG over the diff plus nearby files. Either way, the actual judgment step is [[Concept - LLM-as-Judge]] applied to source code instead of model outputs: the model is asked to grade a diff against implicit criteria (correctness, security, style, test coverage) and emit structured findings, which is why the failure modes of LLM-as-judge — inconsistency across runs, sensitivity to prompt framing, no calibrated confidence — carry over directly.

This is strictly cheaper to run than generating code: reading a diff and classifying candidate issues is a much shorter, more bounded context than driving an [[Deep Dive - Agentic Coding in Production|agentic]] edit-run-observe loop, which is part of why review tooling scaled to a large paying market faster than autonomous coding did. It is not free, though — a full-repo-context model call on every push is a real, recurring inference bill that scales with PR volume rather than headcount, and teams running these tools at scale hit the same budgeting problem covered in [[Concept - Cost Engineering for LLM Applications]].

A diff, or a linked issue the model pulls in for context, is also untrusted input to the reviewer model — the same [[Concept - Prompt Injection]] surface that affects any LLM ingesting external text, just less explored here because the "attacker" is usually assumed to be a teammate, not an adversary.

## In practice

Review is the bottleneck [[Concept - Team Workflow Restructuring with AI|AI accelerates on the way in]]: once authoring gets faster, PR volume rises and review — historically a flat, linear-in-headcount process — becomes the binding constraint on how fast a team can actually ship. AI review is the industry's bet on absorbing that surge — an attempt to pay down the [[Concept - The Verification Tax]] with machines instead of headcount — and the market moved from novelty to funded infrastructure across 2025:

- **CodeRabbit** raised a $60M Series B (Scale Venture Partners leading, NVentures/Nvidia and CRV participating) at a $550M valuation in September 2025, reporting >$15M ARR growing ~20%/month and more than 8,000 paying organizations including Chegg, Groupon, and Mercury (E2, company-reported, TechCrunch and CodeRabbit's own announcement, Sept 2025). It became one of the most-installed apps on the GitHub Marketplace.
- **Graphite** (Anthropic's Anthology Fund and Accel among investors) raised a $52M Series B in March 2025 for its "Diamond" review agent, serving 500+ companies including Shopify, Snowflake, and Figma (E2, TechCrunch, March 2025). Graphite was then itself acquired by **Cursor** in December 2025 — Cursor CEO Michael Truell's stated rationale was that as AI collapses the time to *write* code, review becomes the growing share of a developer's week, so owning the review agent completes the authoring-to-merge pipeline (E2, Fortune, Dec 2025). Terms were not officially disclosed; reported at "way over $290M" cash-and-equity (E2, Fortune/TechCrunch, Dec 2025); Graphite kept its brand through 2026 pending integration — a live instance of [[Concept - Moats in the AI Application Layer]]: the value migrated toward whoever owns the full loop, not just one stage of it.
- **Greptile** raised a $25M Series A led by Benchmark in September 2025 (after reports in July 2025 of a larger round at a $180M valuation that came down by close) and reported analyzing 500M+ lines of code monthly for customers including Brex, Substack, and PostHog (E2, TechCrunch/SiliconANGLE, Sept 2025).
- **GitHub Copilot's review mode** and equivalents from Amazon and Google ride the incumbent distribution advantage rather than needing to win on review quality alone. Full detail on funding, ownership, and how these vendors stack against each other lives in [[Reference - AI Dev Tool Landscape]].

What these tools are reliably good at: mechanical bugs (null checks, off-by-ones, unhandled exceptions), obvious security smells (hardcoded secrets, missing input validation), style/consistency enforcement, and PR summarization for reviewer onboarding — high-recall, low-context tasks that don't require holding the whole system's intent in mind.

What they reliably miss: whether a change is the *right* change — architectural fit, business-logic correctness, cross-service side effects, and anything that requires knowing what the team actually intended, none of which is recoverable from a diff plus a dependency graph. Vendor claims of "catches X% more bugs than human review" are self-run on small internal PR samples (E1) — there is no standard, independent AI-code-review benchmark as of 2026, so these numbers cannot be compared across vendors.

## Failure modes

**Alert fatigue.** Every extra false positive costs reviewer attention; once a team learns the bot's comments are noisy, they start skimming and dismissing all of them, including the real ones — the tool's marginal value goes negative exactly when volume is highest, which is precisely when it was supposed to help most. This is the verification tax in miniature: a tool sold as reducing the cost of checking AI output can, past the noise threshold, raise it instead.

**Confidence without correctness.** Because the underlying mechanism is LLM-as-judge, findings read as confident, well-formatted prose regardless of whether the model actually understood the change — a plausible-sounding wrong comment is harder to dismiss than an obviously wrong one, and burns more reviewer time re-verifying it.

**AI writing, AI reviewing.** The scenario [[Lore - AI Coding War Stories|the field worries about most]]: an [[Concept - AI Coding Assistants|AI coding assistant]] drafts a PR, an AI reviewer approves it, and no human ever reads the diff closely — the [[Pattern - Human-in-the-Loop Review Workflow]] degenerating into machine-approves-machine. This doesn't just risk one bad merge — it thins the human oversight loop across the whole codebase over time, which is the mechanism [[Concept - The Capability-Reliability Gap]] predicts: capability (can the reviewer model catch this class of bug sometimes) gets treated as reliability (will it catch this specific bug, every time), and the gap is exactly where architectural and business-logic errors live.

## The non-obvious

The best-measured value of these tools in practice is not bug-catching, it's *summarization and reviewer context* — turning a 40-file diff into a paragraph a human reviewer can orient from in 30 seconds, which shortens review latency even when the bot finds nothing wrong. Teams that adopt AI review purely to "catch more bugs" tend to be disappointed by the false-positive rate; teams that adopt it to make human review *faster to start* get consistent value. The corollary is the dangerous case: if a team also stops doing careful human review because the bot approved the PR, they've swapped a slower-but-real check for a faster-but-shallow one, and the failure only shows up months later as the kind of architectural drift [[Concept - AI's Effect on Code Quality and Security]] documents in aggregate.

## Connections

- [[Concept - Team Workflow Restructuring with AI]] — review is the bottleneck AI coding assistants create by accelerating authoring; AI review is the industry's attempt to absorb that surge.
- [[Concept - AI's Effect on Code Quality and Security]] — the downstream churn/security cost that AI review is supposed to catch but often doesn't.
- [[Reference - AI Dev Tool Landscape]] — where CodeRabbit, Graphite, and Greptile sit in the full market map alongside funding and ownership.
- [[Concept - AI Coding Assistants]] — the tools generating the PR volume that made review a bottleneck in the first place.
- [[Concept - The Capability-Reliability Gap]] — why a reviewer that can catch a bug class sometimes is not the same as one that will catch a specific bug reliably.
- [[Deep Dive - Agentic Coding in Production]] — the "agent proposes, human disposes" pattern that AI review either supports (fast, faithful summaries) or undermines (rubber-stamp approval).
- [[Lore - AI Coding War Stories]] — where AI-writes-and-AI-reviews with no human gate went wrong in production.
- [[Concept - Moats in the AI Application Layer]] — the Cursor-Graphite acquisition as a live case of value migrating to whoever owns the full write-to-merge pipeline.
- [[Concept - LLM-as-Judge]] — the underlying mechanism (grading text/code against implicit criteria) and the inconsistency/calibration failures that carry over into review tools.
- [[Concept - Prompt Injection]] — a diff or a linked issue is untrusted input to the reviewer model, an underexplored attack surface as these bots get write access to comment/merge flows.
- [[Concept - Cost Engineering for LLM Applications]] — running a full-repo-context review model on every PR is a real, recurring inference cost that scales with PR volume, not headcount.
- [[Pattern - Human-in-the-Loop Review Workflow]] — AI review is a machine-filter-then-human-approve gate; its worst failure is that same workflow degenerating into machine-approves-machine (cross-domain: business functions).
- [[Concept - The Verification Tax]] — AI review both pays down the human cost of checking AI-written code and adds its own recurring inference bill; it is verification labor either way (cross-domain: adoption).

## Sources

- CodeRabbit — "Raising our $60 million Series B" (company blog, Sept 2025) and TechCrunch, "CodeRabbit raises $60M, valuing the 2-year-old AI code review startup at $550M" (Sept 16, 2025) — funding, ARR, growth rate, customer count.
- TechCrunch — "Anthropic-backed AI-powered code review platform Graphite raises cash" (Mar 18, 2025) — Series B terms, investors, customer list.
- Fortune — "Exclusive: Cursor acquires code review startup Graphite as AI coding competition heats up" (Dec 19, 2025) — acquisition rationale and terms.
- TechCrunch — "Benchmark in talks to lead Series A for Greptile, valuing AI-code reviewer at $180M" (Jul 18, 2025) and SiliconANGLE, "Greptile bags $25M in funding to take on CodeRabbit and Graphite" (Sept 23, 2025) — final round terms and product scale.
