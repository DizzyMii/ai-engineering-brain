---
tags: [deep-dive, domain/applied-software, level/frontier]
aliases: [coding agents, autonomous coding, agentic software engineering, SWE agents, Devin Claude Code Codex]
summary: "How autonomous coding agents run in real orgs (2025-2026): the loop, where it works, where errors compound, oversight costs."
---

# Deep Dive - Agentic Coding in Production

> An autonomous coding agent is a frontier LLM in a tool loop: it reads and edits files, runs shell commands and tests, and iterates until a goal is met or a budget runs out. In 2024 these were demos. By 2025-2026 they're real infrastructure at Devin/Cognition, Anthropic (Claude Code), OpenAI (Codex), Cursor (Composer) and GitHub (Copilot agent mode), plus open-source SWE-agent, OpenHands and Aider. It can write code. The question now is what it does *reliably*, and what human oversight costs. The production answer, learned the hard way, is one pattern: **agent proposes, human disposes.** (as of 2026)

## The mechanism

A coding agent is [[Deep Dive - The Agent Loop]] specialized to a repository. Given a task, tools ([[Concept - Tool Use and Function Calling]]) and a working copy of the codebase, the model loops:

```
observe (repo state, last tool output)
  → think (plan next edit)
  → act (edit file / run test / run shell / search)
  → observe result
  → repeat until tests pass OR budget exhausted OR stuck
```

Three things separate a *production* agent from a chat model that emits code.

1. **A closed feedback loop with a verifier.** The agent runs the tests or compiler, *reads the failure*, and repairs. The model supplies capability; this scaffold supplies dependability (the [[Concept - The Capability-Reliability Gap]] made operational). With no cheap oracle to check itself against, an agent degrades into a confident guesser.
2. **Repo context.** The codebase is indexed (embeddings + symbol/AST search, often exposed over [[Concept - Model Context Protocol (MCP)]]) so the agent can pull roughly the right files. Stuffing the whole repo into the context window would trigger [[Concept - Context Rot]] and blow the budget.
3. **A sandbox and an exit to human review.** Most production agents run in an isolated container with a scoped filesystem and network, and their *output is a pull request*, not a merge. The human gate is the product.

## Walkthrough

One task, "fix issue #451, the CSV parser drops the last row," through a review-gated cloud agent (the Devin/Codex/Copilot-agent shape):

```mermaid
flowchart TD
    A[Issue #451 assigned to agent] --> B[Spin up sandbox: clone repo, install deps]
    B --> C[Index / retrieve relevant files: csv_parser.py, tests/]
    C --> D[Plan: reproduce bug as failing test]
    D --> E[Act: write test, run it]
    E -->|test fails as expected| F[Edit csv_parser.py]
    E -->|test passes unexpectedly| D
    F --> G[Run test suite in sandbox]
    G -->|red| H[Read traceback, revise edit]
    H --> G
    G -->|green| I[Run linter / type check / full CI subset]
    I -->|fail| H
    I -->|pass| J[Open PR with diff + summary + test]
    J --> K{Human review}
    K -->|approve| L[Merge]
    K -->|request changes| H
    K -->|reject| M[Discard branch]
```

The steps that matter most are the ones demos skip.
- **Reproduce before fixing** (D→E). Agents that write a failing test first are dramatically more reliable, because they manufacture their own oracle. Agents that jump straight to editing "fix" symptoms and assert the buggy behavior, the oracle problem from [[Concept - AI in Software Testing]].
- **The repair sub-loop** (G↔H, I↔H). Most of the token budget and most failures live here. Each repair iteration succeeds with probability < 1, so tasks needing many iterations are where error compounding bites (below).
- **The sandbox boundary** (B) and **the human gate** (K). Remove either and you get the incidents in [[Lore - AI Coding War Stories]].

## In practice

**Where it works:** well-scoped, verifiable, bounded tasks.
- Bug fixes *with a reproduction*, since the repro is the oracle.
- Test writing, dependency bumps, mechanical refactors.
- Large migrations, the strongest documented ROI in agentic coding. Amazon Q's Java modernization and Google's LLM migration program (see [[Breakdown - AI-Driven Code Migrations]]) had ~70% of edits machine-generated, because compile+test verification is nearly free.

**Reliability numbers, read honestly:**
- **[[Breakdown - SWE-bench]] Verified.** Frontier agents report roughly 80-95% (2026, model- and scaffold-dependent). OpenAI *deprecated* Verified in Feb 2026 over contamination, since the public Python repos predate training cutoffs. A "SWE-bench score" belongs to a *model + scaffold + prompt* tuple, not to the model, and Verified tasks are curated Python bug-fixes with known tests.
- **The harder-set drop.** On SWE-bench Pro (held-out/commercial codebases, standardized scaffolding) the same frontier models fall well below their Verified numbers. As of mid-2026 the top *active* scores are ~59% (GPT-5.4 on Scale's standardized public set), ~69% (Opus 4.8, vendor aggregate) and ~47% (Opus 4.6 on Scale's *private commercial* set). That's up from the ~15-25% early Pro scores of mid-2025, but still a persistent ~20-40 point gap under Verified (E2, Scale Labs SWE-bench Pro leaderboard; volatile across splits). The operational fact is the Verified-to-Pro gap, not any point estimate. *(Numbers move monthly; track the gap, not the leaderboard.)*
- **Independent end-to-end.** In Answer.AI's month with Devin it completed **3 of 20** real tasks autonomously (~15%, E2, independent, Jan 2025), close to Devin's original 13.86% SWE-bench launch figure. Autonomous completion on messy real work sits far below curated-benchmark peaks.

**Oversight economics.** Agents move human labor from *writing* to *specifying and reviewing*, and that costs something. A bad agent PR can take longer to review than the fix would have taken to write ([[Concept - The Verification Tax]]). The accounting question is whether many small verifiable tasks in parallel net out positive after review load. The deployments that win run *fleets* of agents on small tasks, not one agent on a big one.

## Failure modes

- **Error compounding over long horizons.** An agent chaining $N$ steps at per-step success $p$ succeeds at roughly $p^N$. At a strong $p = 0.95$, twenty steps gives $0.95^{20} \approx 0.36$, a 64% failure rate from accumulation alone with no single step incapable. Agent reliability drops off a cliff as task length grows ([[Concept - METR Time Horizons]]), so bounding the horizon is the first reliability lever.
- **No oracle, confident wrong output.** No tests, an ambiguous spec, or unverifiable behavior removes the feedback signal. The agent optimizes for plausible-looking code and merges bugs.
- **Weak context on large unfamiliar repos.** Retrieval misses the file that matters and the agent "fixes" the wrong layer. This is the population where [[Breakdown - The METR Developer Slowdown RCT]] found experienced devs **19% slower**: mature codebases with lots of implicit context are the agent's worst case.
- **Destructive autonomy.** An agent with production access and no sandbox is an incident waiting to happen. Replit's agent deleted a production database *during an explicit code freeze* in July 2025 (see [[Lore - AI Coding War Stories]]). The cause was missing guardrails, not model malice (see [[Gotchas - Agents in Production]]).
- **Slopsquatting and hallucinated dependencies.** Agents install packages the model invented. ~19.7% of LLM-recommended packages don't exist (Spracklen et al. 2025), and attackers register the names. Covered in [[Concept - AI's Effect on Code Quality and Security]].
- **AI-writes / AI-reviews collapse.** If an agent writes the code and [[Concept - AI Code Review]] approves it with no human reading closely, oversight thins to nothing. It's the most efficient way to ship a subtle bug at scale.

## The non-obvious

**The pattern that wins in production is "agent proposes, human disposes," and the value comes from parallel breadth, not autonomous depth.** The instinct is to have one agent do a senior engineer's whole job, and that's where error compounding and weak context make it fail. Teams getting real leverage run many agents on small, separately verifiable tasks (a bug with a repro, a dependency bump, one migration slice) and keep a human on the merge gate. A second point follows: **the scaffold and the verification oracle matter as much as the model.** The same model can double its effective reliability with reproduce-before-fix, tight retrieval and a compile+test loop. Every team that removed the human gate to "go faster" bought itself a war story.

## Evolution

- **2021-2023, autocomplete.** GitHub Copilot ships inline suggestions. The model has no tools and no loop: capability without agency.
- **2024, first agents and peak hype.** Devin launches (Mar 2024) as "the first AI software engineer" with a 13.86% SWE-bench figure on a custom subset. Carl Brown's *Debunking Devin* (Apr 2024) shows the demo was oversold. SWE-agent and OpenDevin/OpenHands open-source the loop. Agency arrives; reliability lags.
- **2025-2026, review-gated production.** Claude Code, Codex, Cursor Composer and Copilot agent mode become daily tools. SWE-bench Verified saturates toward 90%+ while private-stack and real-work numbers stay far lower. The Replit incident (Jul 2025) makes sandboxing, dev/prod separation and planning-only modes the norm. The direction is **more autonomy behind more verification**, not unsupervised coding.

Autocomplete didn't die. It became one mode inside agentic IDEs (see [[Breakdown - Cursor]]). Next up is multi-agent orchestration ([[Concept - Multi-Agent Orchestration]]) with planner/worker/reviewer splits. It trades single-agent error compounding for coordination overhead, an open reliability question as of 2026.

## Connections

- [[Deep Dive - The Agent Loop]] — the general loop this note specializes to code; read it first for the observe-think-act mechanics (cross-domain: agents).
- [[Concept - Tool Use and Function Calling]] — the primitive that lets the model edit files and run tests; no tool calls, no agent (cross-domain: agents).
- [[Concept - Model Context Protocol (MCP)]] — the standard interface repo/tool context is increasingly exposed through (cross-domain: agents).
- [[Concept - Multi-Agent Orchestration]] — the next architectural step (planner/worker/reviewer) and its coordination costs (cross-domain: agents).
- [[Gotchas - Agents in Production]] — the concrete guardrail failures (prod access, no sandbox) that turn agents into incidents (cross-domain: agents).
- [[Concept - The Capability-Reliability Gap]] — the core lens: agents have capability; the scaffold buys reliability.
- [[Breakdown - SWE-bench]] — where the ~80-95% Verified vs ~47-69% Pro numbers come from and why the delta matters.
- [[Breakdown - The METR Developer Slowdown RCT]] — the mature-repo, experienced-dev worst case where agents slowed people 19%.
- [[Breakdown - AI-Driven Code Migrations]] — the best-case counterpoint: verifiable, bounded work where agents deliver real ROI.
- [[Concept - AI in Software Testing]] — reproduce-before-fix and the oracle problem the agent inherits.
- [[Concept - AI Code Review]] — the review gate; also the AI-writes/AI-reviews collapse risk.
- [[Concept - AI Coding Assistants]] — the taxonomy this note is the frontier of (generation 3, autonomous agents).
- [[Breakdown - Cursor]] — Composer is the agent mode inside the dominant AI-native IDE.
- [[Concept - Team Workflow Restructuring with AI]] — the org-level consequence: labor shifts from author to reviewer/orchestrator.
- [[Lore - AI Coding War Stories]] — what happens when the sandbox or human gate is removed.
- [[Concept - METR Time Horizons]] — the formal treatment of why long-horizon tasks fail from compounding (cross-domain: trajectory).
- [[Concept - Context Rot]] — why stuffing the whole repo into context degrades the agent (cross-domain: prompting/context).
- [[Concept - The Verification Tax]] — the review cost that decides whether agent fleets net out positive (cross-domain: adoption).
- [[Reference - AI Dev Tool Landscape]] — the market map of the agents named here.

## Sources

- Jimenez et al. (2023) — *SWE-bench*, Princeton. The benchmark whose Verified/Pro split defines the reliability gap. (E3, peer-reviewed dataset.)
- METR (2025) — arXiv 2507.09089. −19% on experienced devs, mature repos; the agent worst-case population. (E3, RCT.)
- Cognition (2024) — Devin launch, 13.86% SWE-bench on a subset; Carl Brown, *Debunking Devin* (Apr 2024), Internet of Bugs. (E2 vendor claim + E2 independent rebuttal.)
- Answer.AI (Jan 2025) — *Thoughts On A Month With Devin*: 3/20 tasks completed autonomously. (E2, independent.)
- Scale Labs — *SWE-bench Pro* leaderboard (public/private/commercial), mid-2026: top active models ~59% standardized public, ~69% vendor aggregate, ~47% private commercial, vs ~80-95% on the (contamination-flagged, Feb-2026-deprecated) Verified. (E2, benchmark operator; volatile.)
- Ziftci et al. (2025) — *Migrating Code At Scale With LLMs At Google*, arXiv 2504.09691. Agent-shaped migration, ~70% of edits machine-generated. (E2, company study.)
- Spracklen et al. (2025) — package hallucination, USENIX Security. 19.7% of recommended packages don't exist. (E3.)
- Replit incident (Jul 2025) — Fortune, The Register, Fast Company; agent deleted a production DB during a code freeze. (E2/E3, widely reported.)
