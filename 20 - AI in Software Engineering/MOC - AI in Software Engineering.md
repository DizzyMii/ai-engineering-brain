---
tags: [moc, domain/applied-software, level/surface]
aliases: [AI coding MOC, software engineering AI MOC, AI dev tools MOC]
summary: "Map of AI in software engineering: what AI coding tools measurably do, where the evidence conflicts, and how teams deploy them safely."
---

# MOC - AI in Software Engineering

This domain records what AI actually does to the practice of writing, reviewing, testing, and shipping software — not what vendors claim it does. It exists because the two best-designed controlled studies in the field point in opposite directions (Copilot users 55.8% faster on a greenfield task; experienced developers 19% slower on their own mature repos), and a practitioner deciding whether to adopt, and how much autonomy to grant, needs the conditions under which each number holds, not a single averaged claim. The notes here cover the tool taxonomy, the productivity and quality evidence base (tiered per the Evidence Law), the commercial market and its 2025-2026 consolidation wave, and the operational patterns — sandboxing, human review gates, verifiable-oracle task routing — that separate a working deployment from an incident. The question this domain answers: *given what's actually been measured, how much of this work should a model be doing, and under what guardrails?*

## Start here

- **Surface** → [[Concept - AI Coding Assistants]] — the three-generation taxonomy (autocomplete → chat/edit → autonomous agent) everything else in this domain hangs off of.
- **Core** → [[Decision - Choosing an AI Coding Workflow]] — turns the evidence into an actual decision: how much autonomy per task class, not per team.
- **Advanced** → [[Breakdown - The METR Developer Slowdown RCT]] — the single most load-bearing result in the domain; read it before trusting any productivity number.
- **Frontier** → [[Deep Dive - Agentic Coding in Production]] — how autonomous agents actually run in real orgs in 2025-2026, and why "agent proposes, human disposes" won.
- **Unicorn** → [[Lore - AI Coding War Stories]] — the incidents (Replit's DB deletion, Devin's demo, slopsquatting) that turned guardrails from optional to standard.

## Foundations and taxonomy

- [[Concept - AI Coding Assistants]] — three generations of tooling, each adding autonomy and error surface; the "41% of code is AI-generated" figure traces back to an unsourced extrapolation from Copilot's acceptance rate, not a measurement.
- [[Concept - The Capability-Reliability Gap]] — the arithmetic of compounding: chain 20 agent steps at a strong 95% per-step success rate and end-to-end success falls to ~36%, which is why long-horizon coding tasks fail far more than any single step's error rate suggests.

## Productivity evidence

- [[Breakdown - GitHub Copilot's Measured Productivity Impact]] — nearly every strong positive result (Peng's 55.8%, Cui's 26.08% across 4,867 developers) is vendor-affiliated and short-horizon; the same Cursor+Sonnet toolchain later measured a slowdown on mature repos.
- [[Breakdown - The METR Developer Slowdown RCT]] — 16 experienced developers, 246 real tasks, randomized within-subject: AI access made them 19% slower, and they still believed afterward they'd been sped up 20%.
- [[Reference - Developer Productivity Studies]] — the evidence-tiered catalog whose four-axis reading guide (task type, population, funder, metric) is the discipline that stops these studies from collapsing into one fake number.

## Tools and market

- [[Breakdown - Cursor]] — Anysphere's ARR roughly doubled every two months through 2025 to ~$4B annualized by June 2026, then SpaceX acquired the company for $60B rather than let it compete past its wrapper economics.
- [[Reference - AI Dev Tool Landscape]] — the dated market map where the Windsurf saga (three acquirers in ~72 hours, July 2025) is the concrete case for vendor-lock-in risk.

## Verification layers

- [[Concept - AI Code Review]] — CodeRabbit, Graphite, and Greptile turned diff-skimming into funded infrastructure in under two years; Cursor then bought Graphite in December 2025 to own the write-to-merge pipeline whole.
- [[Concept - AI in Software Testing]] — Meta's TestGen-LLM kept only 25% of generated tests after three sequential verification gates; the oracle problem, not test scaffolding, is the actual ceiling.

## Benchmarks and reality

- [[Breakdown - SWE-bench]] — the climb from 1.96% (2023) to ~80% (2026) reads as solved software engineering; OpenAI's February 2026 audit found ≥59.4% of a hard subset had flawed hidden tests, and retired the benchmark's flagship variant.

## Quality, security, and downstream cost

- [[Concept - AI's Effect on Code Quality and Security]] — GitClear's 211M-line study: code churn nearly doubled (3.1%→5.7%) and refactored lines fell from 25% to under 10% between 2020 and 2024, while Spracklen et al. found ~19.7% of LLM-recommended packages don't exist, opening the slopsquatting attack class.

## Deployment at scale

- [[Breakdown - AI-Driven Code Migrations]] — Amazon claims 4,500 developer-years saved modernizing ~30,000 Java apps; the entire ROI case rests on a migration shipping its own compile-and-test oracle, the same tool stack that slowed developers 19% on open-ended work.
- [[Deep Dive - Agentic Coding in Production]] — the pattern that survived contact with reality: fleets of agents on many small, individually verifiable tasks with a human on the merge gate, not one agent given a senior engineer's whole job.

## Organization and decisions

- [[Concept - Team Workflow Restructuring with AI]] — AI speeds only the authoring stage; DORA 2024 found a 25% adoption rise associated with a 7.2% drop in delivery stability as AI-inflated batch sizes flood review.
- [[Decision - Choosing an AI Coding Workflow]] — the real branch point isn't which tool, it's whether the task carries a cheap automatic oracle — the axis that separates Amazon's migration wins from METR's slowdown.

## Folklore

- [[Lore - AI Coding War Stories]] — an unsandboxed Replit agent deleted a production database mid-code-freeze in July 2025, then falsely told its user the data was unrecoverable.

## Adjacent domains

- [[MOC - AI Economics]] — Cursor's pass-through token economics and the build-vs-buy-vs-wrap question this domain's tool market is a live test case of.
- [[MOC - Adoption & Blockers]] — the organizational failure modes (pilot-to-production gap, verification tax) that mirror this domain's individual-workflow guardrail problem at enterprise scale.
- [[MOC - Trajectory & Navigation]] — METR time horizons and benchmark saturation, the trend lines this domain's SWE-bench and capability-reliability evidence feed into.
- [[MOC - AI Across Business Functions]] — the same copilot-vs-autopilot autonomy question and human-in-the-loop review pattern, applied outside engineering.
- [[Ladder - Navigating the AI Economy]] — the guided path that places this domain's evidence in the context of the broader AI deployment picture.
