---
tags: [concept, domain/applied-software, level/surface]
aliases: [capability vs reliability, demo-to-production gap]
summary: "Why what a model can sometimes do (capability) and what it dependably does in your pipeline (reliability) don't converge as models improve."
---

# Concept - The Capability-Reliability Gap
> **One-paragraph hook:** Capability is a max over samples — can the model ever produce the right answer, given enough tries, cherry-picked demos, or a benchmark's exact conditions. Reliability is closer to a min or expectation — will it produce the right answer *this time*, in *your* pipeline, unattended. Marketing sells capability; deployment value is entirely a function of reliability. Confusing the two is the single most common mistake in evaluating whether an AI coding tool is ready for a given task.

## The mechanism
Formally: capability ≈ $\max_i P(\text{success on attempt } i)$ across many samples, retries, or favorable framings — it's pass@k with k large, or a demo where the operator picked the run that worked. Reliability ≈ the success rate you actually get on a single unattended attempt in production conditions — closer to pass@1 under your data distribution, your prompts, your codebase.

The gap compounds across steps. An agent that chains $N$ sequential actions (read file → plan → edit → run tests → fix) with per-step success probability $p$ succeeds end-to-end at roughly $p^N$ if steps are independent. At $p = 0.95$ per step — a good number for a single well-scoped edit — 20 chained steps gives $0.95^{20} \approx 0.36$. This is the arithmetic reason long-horizon agentic coding tasks fail far more often than any single step's error rate would suggest: the failure is accumulation, not a single incapable step (link [[Concept - METR Time Horizons]], [[Deep Dive - Agentic Coding in Production]]).

Benchmarks make the gap concrete and measurable. SWE-bench Verified scores from frontier coding agents reached roughly 70-80%+ by mid-2026 (E2, leaderboard-reported), but the same class of model drops on SWE-bench Pro — a harder, decontaminated benchmark built specifically because Verified's public GitHub-issue tasks were increasingly contaminated by training-data overlap and, per an OpenAI audit (Feb 2026), had flawed hidden tests in ~59% of the hardest sampled cases (E2). GPT-5's mid-2025 launch scores were ~23.3% on the public split and ~15-18% on the private held-out split; by mid-2026 the top *active* scores across models had climbed to ~59% (standardized public), ~69% (vendor aggregate), and ~47% (private commercial) — still a persistent gap under Verified, and volatile across splits (E2, Scale Labs SWE-bench Pro leaderboard, mid-2026). The score didn't get worse — the measurement got more honest (link [[Breakdown - SWE-bench]]).

## In practice
Demo asymmetry is the visible form of the gap: a demo is, definitionally, a capability sample the presenter chose to show. Cognition's March 2024 Devin launch claimed 13.86% on SWE-bench (~7x the prior Claude-2 baseline of 1.96%) and a viral Upwork "hire a freelance AI engineer" demo; independent reviewer Carl Brown's April 2024 video "Debunking Devin" walked the actual session traces frame-by-frame and showed the demo task was misrepresented (the AI was shown running an existing model, not writing new code) and that the SWE-bench figure came from a 45-minute-budget subset run, not a like-for-like comparison (E2, well-documented). Treat every unaudited demo as an upper bound on capability, not an estimate of reliability.

The gap persists because LLM output is high-variance by construction — sampling temperature, context-window position effects, and prompt sensitivity all move single-attempt success without moving the ceiling. RLHF and verifier-based RL raise the floor (fewer catastrophic failures) but don't eliminate variance, and the last few points of reliability are disproportionately expensive to buy — going from 90% to 99% reliable typically costs far more engineering (verification harnesses, narrower task scoping, human gates) than going from 50% to 90% did.

## Failure modes
- **Trusting a benchmark number as a production estimate.** A SWE-bench Verified score is a model+scaffold+prompt tuple, not a property of the model — the same base model scores very differently under different agent harnesses.
- **Trusting a self-report as a reliability estimate.** METR's 2025 RCT found experienced developers forecast a 24% AI speedup, still believed after the fact they'd gotten a 20% speedup, and had in fact been measured 19% slower (E3) — humans cannot reliably introspect their own reliability gain, so "developers feel faster" survey metrics measure perception, not output (link [[Breakdown - The METR Developer Slowdown RCT]]).
- **Widening gap with capability growth.** Benchmark scores saturate fast (SWE-bench Verified went from single digits in 2024 to 90%+ by 2026); reliability on messy, ambiguous, large-context real work improves much more slowly. The gap can widen even as headline capability rises — which is why capable 2025-2026 coding agents stayed gated behind mandatory human review in every serious production deployment rather than being trusted to merge autonomously (link [[Deep Dive - Agentic Coding in Production]]).

## The non-obvious
Because capability and reliability improve at different rates, "the model got better" is not evidence your pipeline got safer to automate further — check whether the improvement showed up in your task distribution's reliability, not in the benchmark's capability ceiling. This is why organizations kept the human-review gate in place through multiple "generational" model upgrades rather than progressively removing it: the gate wasn't calibrated to 2024's capability, it was calibrated to the fact that reliability is the binding constraint and moves slowly regardless of headline scores.

## Connections
- [[Concept - AI Coding Assistants]] — the taxonomy this gap explains: each generation (autocomplete → chat → agent) widens the gap by adding autonomous steps.
- [[Deep Dive - Agentic Coding in Production]] — where the gap is operationally managed via sandboxing, human review gates, and task scoping.
- [[Breakdown - SWE-bench]] — the concrete Verified-vs-Pro numbers that make the gap measurable.
- [[Breakdown - The METR Developer Slowdown RCT]] — the RCT that demonstrates the self-report version of the gap (perceived vs. measured productivity).
- [[Concept - The Evaluation Gap]] — the broader evaluation-methodology problem of benchmarks not reflecting deployment conditions.
- [[Concept - METR Time Horizons]] — the related metric of how task duration/complexity predicts where the gap widens.
- [[Concept - The Pilot-to-Production Gap]] — the organizational analogue: pilots show capability, production demands reliability.
- [[Lore - AI Coding War Stories]] — real incidents (Devin's demo, Replit's DB deletion) that are this gap made concrete.
- [[Gotchas - Agents in Production]] — tactical mitigations for narrowing the gap in deployed agent systems.
- [[Deep Dive - Designing an Eval Harness]] — how to build evaluation that measures reliability instead of capability.
- [[Concept - Statistical Rigor in Model Evaluation]] — the statistical discipline needed to distinguish a real reliability improvement from noise.

## Sources
- METR (2025) — "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity," arXiv:2507.09089. Source of the 19% slowdown / 20% perceived speedup gap.
- Cognition (March 2024) — Devin launch claim of 13.86% on SWE-bench; Brown, C. (April 2024) — "Debunking Devin," Internet of Bugs (YouTube). The demo-vs-reality critique.
- Jimenez, C. et al. (2023) — SWE-bench, Princeton; OpenAI (Aug 2024) — SWE-bench Verified; Scale AI (Sept 2025) — "SWE-Bench Pro," arXiv:2509.16941. Source of the ~70-80%+ Verified vs. ~15-25% Pro gap.
