---
tags: [concept, domain/applied-software, level/frontier]
aliases: [AI team workflow, engineering process with AI, review bottleneck, author-to-reviewer shift]
summary: "AI speeds authoring, so the bottleneck moves to review and integration; teams that don't restructure get slower while everyone feels faster."
---

# Concept - Team Workflow Restructuring with AI

> The individual-productivity debate asks whether AI makes *a developer* faster. What it does to *a team's* process matters more. AI makes authoring cheap, which moves the constraint to review, integration and QA. If you don't rebuild those stages, the team hasn't sped up. You've moved the queue somewhere harder to see. The signature failure is an org where every developer reports feeling faster while delivery throughput and stability slip. That's a process failure, not a tooling one.

## The mechanism

Software delivery is a pipeline: specify → author → review → integrate → verify → ship. AI assistants and agents speed up one stage, *authoring*, and on the right tasks can multiply its output several-fold. By the theory of constraints, speeding a non-bottleneck stage does nothing for end-to-end throughput, and it can *hurt* by flooding the real bottleneck downstream.

That bottleneck is **review and integration**, and three coupled effects push the wrong way.

1. **Review demand rises with authoring speed.** More PRs, more lines, arriving faster. Review is human work and gets no equivalent AI multiplier. Reading code for correctness, security and architectural fit is the harder half of the job, and it's now the constraint. [[Concept - AI Code Review]] tries to absorb the surge but only catches shallow issues.
2. **Batch size grows.** AI makes it cheap to write more code per change, so diffs get bigger, and larger batches have historically meant *worse* delivery. Google's DORA 2024 report found a 25% increase in AI adoption associated with **−1.5% delivery throughput and −7.2% delivery stability** (E2/E3, DORA survey, 2024), with growing batch size as the proposed mechanism. The individual's "speed" pushes a cost onto the team's flow.
3. **The reviewer of AI code is often the person least equipped to catch its errors.** Juniors gain the most from assistants (Peng 2023, Cui 2024) and produce the most AI code. Seniors, who should review it, can be slowed on exactly the mature codebases where AI is weakest ([[Breakdown - The METR Developer Slowdown RCT]]). The oversight burden lands on the scarcest people.

So the developer's role shifts **from author to reviewer/orchestrator**. Less typing; more specifying tasks, reading diffs and steering agents. The skill premium moves to system design, fast and accurate code reading, and verification design, the abilities that let you *check* output cheaply ([[Concept - The Capability-Reliability Gap]]).

## In practice

What has worked in 2025-2026 deployments:

- **Scale review on purpose.** Treat review capacity as the constraint and invest there first: smaller mandatory PR sizes, review SLAs, AI review tools for shallow triage *plus* a human on correctness, and rotation so review doesn't crush the seniors.
- **Cap batch size.** Push back on the AI-enabled mega-diff and enforce small changes to protect delivery stability. It's the DORA lever run in reverse.
- **Make guardrails standard process** instead of per-team heroics: agent sandboxes, mandatory human PR-review gates for AI-authored code, dependency allowlists (post-slopsquatting), and "planning-only" agent modes that propose without executing. All of these became defaults after the 2025 incidents in [[Lore - AI Coding War Stories]].
- **Change what you measure.** Lines of code, commit count and "devs feel faster" surveys become actively misleading. METR's subjects *slowed 19% while estimating a 20% speedup*, a ~39-point self-report gap. Move to outcome metrics: defect/escape rate, lead time for change, rework/churn, delivery stability ([[Reference - Developer Productivity Studies]], [[Concept - The Evaluation Gap]]). Instrument with real tracing, not surveys ([[Concept - LLM Observability and Tracing]]).
- **Budget the workflow's token cost.** Agent-heavy processes carry usage-based inference costs that can exceed per-seat pricing for heavy users, so process design has a direct bill ([[Concept - Cost Engineering for LLM Applications]]). The same margin math applies as for any other LLM product ([[Concept - Unit Economics of LLM Products]]).

## Failure modes

- **The productivity paradox.** Adopt AI without restructuring review or metrics, and throughput and stability fall while morale-style surveys glow. You're measuring perception, which is inflated, instead of output, which dropped. It's the most common and most expensive failure, and activity dashboards don't show it.
- **Review laundering.** AI writes the code, AI review approves it, no human reads it closely. Oversight thins to zero and subtle defects ship at scale. This is the worst form of the AI-writes/AI-reviews collapse.
- **Mentorship erosion.** Juniors generate and merge AI code they don't fully understand while seniors drown in review. The skill-formation pipeline breaks, and fewer people build the deep code-reading judgment the whole process now depends on.
- **Queue relocation.** Teams celebrate faster authoring and are surprised when lead time doesn't improve. The work piled up at review and integration instead of at the keyboard.

## The non-obvious

An organization can adopt AI, have every developer report feeling faster, and get measurably slower and less stable. That's the expected outcome, not a fluke. The mechanism is mundane: AI speeds a non-bottleneck, inflates batch size, floods review, and self-report gaps hide the loss. A better model is never the fix. The fix is process: scale and protect review, cap batch size, and replace activity metrics with outcome metrics. Whether AI helps a *team* comes down to whether you restructured the pipeline. It's the same organizational muscle that separates a stalled pilot from production in [[Concept - The Pilot-to-Production Gap]].

## Connections

- [[Concept - AI Code Review]] — the tool aimed at the new bottleneck; necessary but insufficient because it catches only shallow issues.
- [[Concept - AI's Effect on Code Quality and Security]] — the churn/duplication/security tax that larger AI-authored batches push into the review and maintenance stages.
- [[Breakdown - The METR Developer Slowdown RCT]] — the self-report gap that breaks perception-based team metrics, and the senior-on-mature-code slowdown.
- [[Reference - Developer Productivity Studies]] — the evidence base (DORA batch-size effect, junior/senior split) behind the process claims here.
- [[Concept - The Capability-Reliability Gap]] — why the skill premium moves to verification: reliability, not capability, is what review is protecting.
- [[Deep Dive - Agentic Coding in Production]] — the "agent proposes, human disposes" pattern is this process change at the individual-workflow level.
- [[Concept - The Pilot-to-Production Gap]] — the same restructuring failure that strands enterprise pilots (cross-domain: adoption).
- [[Concept - The Evaluation Gap]] — why activity metrics mislead and outcome metrics are needed (cross-domain: adoption).
- [[Gotchas - Enterprise AI Adoption]] — the organizational pitfalls that show up when process isn't rebuilt (cross-domain: adoption).
- [[Lore - AI Coding War Stories]] — the incidents that turned guardrails from optional to standard process.
- [[Concept - LLM Observability and Tracing]] — the instrumentation needed to measure outcomes instead of surveying feelings (cross-domain: production-ops).
- [[Concept - Cost Engineering for LLM Applications]] — the token bill an agent-heavy workflow generates (cross-domain: production-ops).
- [[Concept - Unit Economics of LLM Products]] — the margin framework that governs whether an agent-heavy review/orchestration process is affordable at scale, not just fast (cross-domain: economics).

## Sources

- Google DORA (2024) — *Accelerate State of DevOps Report*. 25% AI-adoption rise associated with −1.5% throughput, −7.2% delivery stability; batch size as mechanism. (E2/E3, large survey.)
- METR (2025) — arXiv 2507.09089. The −19%/+20%-estimated self-report gap that invalidates perception metrics. (E3, RCT.)
- Peng et al. (2023), Cui/Peng et al. (2024) — RCTs establishing the junior-benefits-more pattern that concentrates review load. (E2.)
- GitClear (2024-2025) — churn/duplication rising with AI, the downstream maintenance cost of larger batches. (E2, single-vendor.)
