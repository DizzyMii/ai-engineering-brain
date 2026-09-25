---
tags: [concept, domain/applied-software, level/core]
aliases: [AI PR review, automated code review, LLM code review]
summary: "LLMs reviewing pull requests as an LLM-as-judge pass over diffs — strong at shallow bugs, blind to architecture, now a funded market race."
---
# Concept - AI Code Review

> AI code review runs an LLM over every pull request roughly the way a human reviewer skims one: build context, read the diff, flag problems, post comments. It doesn't get tired and doesn't skip files. It catches enough mechanical slop that three well-funded startups (CodeRabbit, Graphite, Greptile) built real businesses on it in under two years. It also carries a real risk. If the same generation of models writes the code and approves it, the human who used to catch what the model missed can drop out of the loop without anyone noticing.

## The mechanism

The tool sits as a bot on the pull-request pipeline (GitHub/GitLab/Bitbucket/Azure DevOps webhook). On each push it runs a fixed loop: build context around the diff, prompt a model to find problems, post the findings as inline PR comments or a summary. Products differ mostly in the context step. CodeRabbit and Greptile both index the *whole* codebase up front. Greptile builds and maintains a repo-wide dependency graph so it can reason about a changed function's callers as well as the changed lines. Lighter tools fall back to RAG over the diff plus nearby files. In every case the judgment step is [[Concept - LLM-as-Judge]] applied to source code: the model grades a diff against implicit criteria (correctness, security, style, test coverage) and emits structured findings. So the LLM-as-judge failure modes carry straight over: inconsistency across runs, sensitivity to prompt framing, no calibrated confidence.

Review costs less to run than code generation. Reading a diff and classifying candidate issues is a shorter, more bounded context than driving an [[Deep Dive - Agentic Coding in Production|agentic]] edit-run-observe loop, which partly explains why review tooling reached a large paying market before autonomous coding did. It still costs money. A full-repo-context model call on every push is a recurring inference bill that scales with PR volume, not headcount, and teams running these tools at scale hit the budgeting problem covered in [[Concept - Cost Engineering for LLM Applications]].

The diff, and any linked issue the model pulls in for context, is untrusted input to the reviewer model. That's the same [[Concept - Prompt Injection]] surface as any LLM reading external text. It gets less attention here because the "attacker" is usually assumed to be a teammate.

## In practice

Faster authoring pushes PR volume up, and review, historically flat and linear in headcount, becomes the limit on how fast a team ships. That's the bottleneck [[Concept - Team Workflow Restructuring with AI|AI accelerates on the way in]]. AI review is the industry's bet on absorbing the surge, paying down [[Concept - The Verification Tax]] with machines instead of headcount. Across 2025 the market went from novelty to funded infrastructure:

- **CodeRabbit** raised a $60M Series B at a $550M valuation in September 2025 (Scale Venture Partners leading, NVentures/Nvidia and CRV participating). It reported >$15M ARR growing ~20%/month and more than 8,000 paying organizations including Chegg, Groupon and Mercury (E2, company-reported, TechCrunch and CodeRabbit's own announcement, Sept 2025). It became one of the most-installed apps on the GitHub Marketplace.
- **Graphite** raised a $52M Series B in March 2025 for its "Diamond" review agent, with Anthropic's Anthology Fund and Accel among investors. It served 500+ companies including Shopify, Snowflake and Figma (E2, TechCrunch, March 2025). **Cursor** acquired Graphite in December 2025. CEO Michael Truell's stated rationale: as AI collapses the time to *write* code, review takes a growing share of a developer's week, so owning the review agent completes the authoring-to-merge pipeline (E2, Fortune, Dec 2025). Terms weren't officially disclosed; reports put it at "way over $290M" cash-and-equity (E2, Fortune/TechCrunch, Dec 2025). Graphite kept its brand through 2026 pending integration. It's a live case of [[Concept - Moats in the AI Application Layer]]: value moved toward whoever owns the full loop instead of one stage of it.
- **Greptile** raised a $25M Series A led by Benchmark in September 2025. Reports in July 2025 had described a larger round at a $180M valuation that came down by close. It reported analyzing 500M+ lines of code monthly for customers including Brex, Substack and PostHog (E2, TechCrunch/SiliconANGLE, Sept 2025).
- **GitHub Copilot's review mode** and equivalents from Amazon and Google ride incumbent distribution, so they don't have to win on review quality alone. Funding, ownership and head-to-head positioning are in [[Reference - AI Dev Tool Landscape]].

They're reliably good at high-recall, low-context work that doesn't require holding the whole system's intent in mind: mechanical bugs (null checks, off-by-ones, unhandled exceptions), obvious security smells (hardcoded secrets, missing input validation), style and consistency enforcement, and PR summaries for reviewer onboarding.

They reliably miss whether a change is the *right* change. Architectural fit, business-logic correctness, cross-service side effects, anything that depends on what the team intended: none of it can be recovered from a diff plus a dependency graph. Vendor claims of "catches X% more bugs than human review" come from self-run tests on small internal PR samples (E1). There's no standard, independent AI-code-review benchmark as of 2026, so those numbers can't be compared across vendors.

## Failure modes

**Alert fatigue.** Every false positive costs reviewer attention. Once a team learns the bot is noisy, they skim and dismiss all its comments, real ones included. The tool's marginal value goes negative when volume is highest, which is when it was supposed to help most. It's the verification tax in miniature: past the noise threshold, a tool sold as cutting the cost of checking AI output raises it.

**Confidence without correctness.** Since the mechanism is LLM-as-judge, findings come out as confident, well-formatted prose whether or not the model understood the change. A plausible wrong comment is harder to dismiss than an obviously wrong one and burns more reviewer time to re-verify.

**AI writing, AI reviewing.** This is the scenario [[Lore - AI Coding War Stories|the field worries about most]]. An [[Concept - AI Coding Assistants|AI coding assistant]] drafts a PR, an AI reviewer approves it, and no human reads the diff closely, so the [[Pattern - Human-in-the-Loop Review Workflow]] decays into machine-approves-machine. The damage goes beyond one bad merge. Human oversight thins across the whole codebase over time, which is what [[Concept - The Capability-Reliability Gap]] predicts. Capability (the reviewer can catch this class of bug sometimes) gets treated as reliability (it will catch this specific bug every time), and architectural and business-logic errors live in that gap.

## The non-obvious

In practice the best-measured value of these tools is *summarization and reviewer context*, more than bug-catching. Turning a 40-file diff into a paragraph a human can orient from in 30 seconds cuts review latency even when the bot finds nothing. Teams that adopt AI review purely to "catch more bugs" tend to be disappointed by the false-positive rate. Teams that adopt it to make human review *faster to start* get consistent value. The dangerous case follows from that. If a team also drops careful human review because the bot approved the PR, it has swapped a slower real check for a faster shallow one. The failure only shows up months later, as the architectural drift [[Concept - AI's Effect on Code Quality and Security]] documents in aggregate.

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
