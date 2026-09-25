---
tags: [concept, domain/applied-software, level/surface]
aliases: [capability vs reliability, demo-to-production gap]
summary: "Why what a model can sometimes do (capability) and what it dependably does in your pipeline (reliability) don't converge as models improve."
---

# Concept - The Capability-Reliability Gap
> Capability is a max over samples: can the model ever produce the right answer, given enough tries, cherry-picked demos, or a benchmark's exact conditions? Reliability is closer to a min or an expectation: will it produce the right answer *this time*, in *your* pipeline, unattended? Marketing sells capability. Deployment value depends entirely on reliability. Mixing the two up is the most common mistake people make when judging whether an AI coding tool is ready for a task.

## The mechanism
Formally, capability ≈ $\max_i P(\text{success on attempt } i)$ across many samples, retries, or favorable framings. That's pass@k with k large, or a demo where the operator picked the run that worked. Reliability ≈ the success rate you get on a single unattended attempt in production conditions, closer to pass@1 on your data distribution, your prompts, your codebase.

The gap compounds across steps. An agent chaining $N$ sequential actions (read file → plan → edit → run tests → fix) with per-step success probability $p$ succeeds end-to-end at roughly $p^N$ if the steps are independent. At $p = 0.95$ per step, a good number for one well-scoped edit, 20 chained steps gives $0.95^{20} \approx 0.36$. That arithmetic is why long-horizon agentic coding tasks fail far more often than any single step's error rate would suggest. No single step is incapable; the failures accumulate ([[Concept - METR Time Horizons]], [[Deep Dive - Agentic Coding in Production]]).

Benchmarks make the gap measurable. Frontier coding agents reached roughly 70-80%+ on SWE-bench Verified by mid-2026 (E2, leaderboard-reported). The same class of model drops on SWE-bench Pro, a harder, decontaminated benchmark. Pro was built because Verified's public GitHub-issue tasks were increasingly contaminated by training-data overlap and, per an OpenAI audit (Feb 2026), had flawed hidden tests in ~59% of the hardest sampled cases (E2). At its mid-2025 launch GPT-5 scored ~23.3% on Pro's public split and ~15-18% on the private held-out split. By mid-2026 the top *active* scores across models had reached ~59% (standardized public), ~69% (vendor aggregate) and ~47% (private commercial). That's still a persistent gap under Verified, and volatile across splits (E2, Scale Labs SWE-bench Pro leaderboard, mid-2026). The models didn't get worse. The measurement got more honest ([[Breakdown - SWE-bench]]).

## In practice
Demos are the visible form of the gap. A demo is by definition a capability sample the presenter chose to show. Cognition's March 2024 Devin launch claimed 13.86% on SWE-bench (~7x the prior Claude-2 baseline of 1.96%), along with a viral Upwork "hire a freelance AI engineer" demo. In April 2024 independent reviewer Carl Brown's video "Debunking Devin" walked the session traces frame by frame. The demo task was misrepresented: the AI was shown running an existing model, not writing new code. The SWE-bench figure came from a 45-minute-budget subset run, not a like-for-like comparison (E2, well documented). Treat every unaudited demo as an upper bound on capability, not an estimate of reliability.

The gap persists because LLM output is high-variance by construction. Sampling temperature, context-window position effects and prompt sensitivity all move single-attempt success without moving the ceiling. RLHF and verifier-based RL raise the floor (fewer catastrophic failures) but don't remove variance. The last few points of reliability cost disproportionately more: going from 90% to 99% reliable typically takes far more engineering (verification harnesses, narrower task scoping, human gates) than going from 50% to 90%.

## Failure modes
- **Reading a benchmark number as a production estimate.** A SWE-bench Verified score belongs to a model+scaffold+prompt tuple. The same base model scores very differently under different agent harnesses.
- **Reading a self-report as a reliability estimate.** In METR's 2025 RCT, experienced developers forecast a 24% AI speedup, still believed afterward they'd gotten a 20% speedup, and were measured 19% slower (E3). People can't reliably introspect their own reliability gain, so "developers feel faster" surveys measure perception, not output ([[Breakdown - The METR Developer Slowdown RCT]]).
- **The gap widening as capability grows.** Benchmark scores saturate fast: SWE-bench Verified went from single digits in 2024 to 90%+ by 2026. Reliability on messy, ambiguous, large-context real work improves much more slowly. The gap can widen while headline capability rises. Capable 2025-2026 coding agents stayed behind mandatory human review in every serious production deployment instead of merging autonomously ([[Deep Dive - Agentic Coding in Production]]).

## The non-obvious
Capability and reliability improve at different rates, so "the model got better" isn't evidence your pipeline got safer to automate further. Check whether the improvement shows up as reliability on your task distribution, not as a higher benchmark ceiling. Organizations kept the human-review gate through multiple "generational" model upgrades instead of peeling it back. The gate wasn't calibrated to 2024's capability. It was calibrated to reliability, which is the limit that matters and which moves slowly whatever the headline scores say.

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
