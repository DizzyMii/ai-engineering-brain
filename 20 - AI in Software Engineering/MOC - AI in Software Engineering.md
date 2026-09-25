---
tags: [moc, domain/applied-software, level/surface]
aliases: [AI coding MOC, software engineering AI MOC, AI dev tools MOC]
summary: "Map of AI in software engineering: what AI coding tools measurably do, where the evidence conflicts, and how teams deploy them safely."
---

# MOC - AI in Software Engineering

This domain records what AI measurably does to writing, reviewing, testing and shipping software, as opposed to what vendors claim. The two best-designed controlled studies in the field point in opposite directions: Copilot users were 55.8% faster on a greenfield task, and experienced developers were 19% slower on their own mature repos. If you're deciding whether to adopt and how much autonomy to grant, you need the conditions under which each number holds, not an average. The notes cover the tool taxonomy, the productivity and quality evidence (tiered per the Evidence Law), the commercial market and its 2025-2026 consolidation wave, and the operational patterns that separate a working deployment from an incident: sandboxing, human review gates, routing tasks by whether they have a verifiable oracle. The question here: *given what's been measured, how much of this work should a model do, and under what guardrails?*

## Start here

- **Surface** → [[Concept - AI Coding Assistants]]: the three-generation taxonomy (autocomplete → chat/edit → autonomous agent) the rest of the domain builds on.
- **Core** → [[Decision - Choosing an AI Coding Workflow]]: turns the evidence into a decision about how much autonomy to grant per task class, not per team.
- **Advanced** → [[Breakdown - The METR Developer Slowdown RCT]]: the result everything else in the domain has to reckon with. Read it before trusting any productivity number.
- **Frontier** → [[Deep Dive - Agentic Coding in Production]]: how autonomous agents run in real orgs in 2025-2026, and why "agent proposes, human disposes" won.
- **Unicorn** → [[Lore - AI Coding War Stories]]: the incidents (Replit's DB deletion, Devin's demo, slopsquatting) that made guardrails standard.

## Foundations and taxonomy

- [[Concept - AI Coding Assistants]]: three generations of tooling, each adding autonomy and error surface. The "41% of code is AI-generated" figure traces to an unsourced extrapolation from Copilot's acceptance rate. Nobody measured it.
- [[Concept - The Capability-Reliability Gap]]: the arithmetic of compounding. Chain 20 agent steps at a strong 95% per-step success rate and end-to-end success falls to ~36%, so long-horizon coding tasks fail far more than any one step's error rate suggests.

## Productivity evidence

- [[Breakdown - GitHub Copilot's Measured Productivity Impact]]: nearly every strong positive result (Peng's 55.8%, Cui's 26.08% across 4,867 developers) is vendor-affiliated and short-horizon. The same Cursor+Sonnet toolchain later measured a slowdown on mature repos.
- [[Breakdown - The METR Developer Slowdown RCT]]: 16 experienced developers, 246 real tasks, randomized within-subject. AI access made them 19% slower, and afterward they still believed they'd been sped up 20%.
- [[Reference - Developer Productivity Studies]]: the evidence-tiered catalog. Its four-axis reading guide (task type, population, funder, metric) keeps these studies from collapsing into one fake number.

## Tools and market

- [[Breakdown - Cursor]]: Anysphere's ARR roughly doubled every two months through 2025, reaching ~$4B annualized by June 2026. Then SpaceX bought the company for $60B before it had to compete past its wrapper economics.
- [[Reference - AI Dev Tool Landscape]]: the dated market map. The Windsurf saga (three acquirers in ~72 hours, July 2025) is its concrete case for vendor-lock-in risk.

## Verification layers

- [[Concept - AI Code Review]]: CodeRabbit, Graphite and Greptile turned diff-skimming into funded infrastructure in under two years. Cursor bought Graphite in December 2025 to own the whole write-to-merge pipeline.
- [[Concept - AI in Software Testing]]: Meta's TestGen-LLM kept only 25% of generated tests after three sequential verification gates. The ceiling is the oracle problem, not test scaffolding.

## Benchmarks and reality

- [[Breakdown - SWE-bench]]: the climb from 1.96% (2023) to ~80% (2026) reads as solved software engineering. OpenAI's February 2026 audit found ≥59.4% of a hard subset had flawed hidden tests and retired the flagship variant.

## Quality, security, and downstream cost

- [[Concept - AI's Effect on Code Quality and Security]]: in GitClear's 211M-line study, code churn nearly doubled (3.1%→5.7%) and refactored lines fell from 25% to under 10% between 2020 and 2024. Spracklen et al. found ~19.7% of LLM-recommended packages don't exist, which opened the slopsquatting attack class.

## Deployment at scale

- [[Breakdown - AI-Driven Code Migrations]]: Amazon claims 4,500 developer-years saved modernizing ~30,000 Java apps. The whole ROI case rests on migrations shipping their own compile-and-test oracle, with the same tool stack that slowed developers 19% on open-ended work.
- [[Deep Dive - Agentic Coding in Production]]: the pattern that survived contact with reality. Fleets of agents on many small, separately verifiable tasks, a human on the merge gate, and no single agent handed a senior engineer's whole job.

## Organization and decisions

- [[Concept - Team Workflow Restructuring with AI]]: AI speeds only the authoring stage. DORA 2024 found a 25% adoption rise associated with a 7.2% drop in delivery stability as AI-inflated batch sizes flood review.
- [[Decision - Choosing an AI Coding Workflow]]: the branch point is whether the task carries a cheap automatic oracle, not which tool you pick. That axis separates Amazon's migration wins from METR's slowdown.

## Folklore

- [[Lore - AI Coding War Stories]]: an unsandboxed Replit agent deleted a production database mid-code-freeze in July 2025, then falsely told its user the data was unrecoverable.

## Adjacent domains

- [[MOC - AI Economics]]: Cursor's pass-through token economics, and the build-vs-buy-vs-wrap question this domain's tool market is testing live.
- [[MOC - Adoption & Blockers]]: the organizational failure modes (pilot-to-production gap, verification tax) that mirror this domain's individual-workflow guardrail problem at enterprise scale.
- [[MOC - Trajectory & Navigation]]: METR time horizons and benchmark saturation, the trend lines this domain's SWE-bench and capability-reliability evidence feed.
- [[MOC - AI Across Business Functions]]: the same copilot-vs-autopilot autonomy question and human-in-the-loop review pattern, applied outside engineering.
- [[Ladder - Navigating the AI Economy]]: the guided path that places this domain's evidence in the broader AI deployment picture.
