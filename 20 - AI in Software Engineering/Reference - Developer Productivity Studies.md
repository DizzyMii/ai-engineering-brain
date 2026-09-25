---
tags: [reference, domain/applied-software, level/advanced]
aliases: [AI coding studies, developer productivity evidence, Copilot studies, AI productivity research]
summary: "Evidence-tiered catalog of AI-coding productivity, quality, and security studies — design, N, effect, tier — check claims against sources."
---

# Reference - Developer Productivity Studies

_As of 2026. Effect sizes below are NOT comparable across different tasks and populations, so don't average them into one number. Read the [reading guide](#reading-guide) footnotes before quoting any row._

## Productivity: controlled / randomized

| Study | Design | N | Task / population | Effect | Tier |
|---|---|---|---|---|---|
| Peng et al. 2023 [^funder][^task] | RCT | 95 freelancers | Implement an HTTP server in JavaScript (greenfield, self-contained) | **+55.8% faster** completion | E2 (GitHub-authored, unpublished/not peer-reviewed) |
| Cui, Demirer, Jaffe, Musolff, Peng, Salz 2024 [^funder] | 3 field RCTs | 4,867 devs | Microsoft, Accenture, a Fortune-100 electronics firm (real work) | **+26.08%** completed tasks/PRs (SE 10.3%) | E2 (company-run RCTs; pub. *Management Science* 2025) |
| GitHub–Accenture 2024 [^funder] | Enterprise deployment | ~thousands | Enterprise devs | ~80% retention; higher PR throughput | E2 (company-claimed) |
| **METR 2025** [^pop] | **Within-subject RCT** | 16 devs, 246 tasks | Experienced OSS maintainers on mature repos they'd owned ~5 yrs | **−19% (i.e. 19% SLOWER)** | **E3** (independent, randomized) |

Peng's +55.8% and METR's −19% are the two poles of the field, and they don't contradict. One is juniors and freelancers on a greenfield toy task. The other is experts on familiar production code. The effect depends on task type and population; there's no single constant. Interpretation is in [[Breakdown - GitHub Copilot's Measured Productivity Impact]] and [[Breakdown - The METR Developer Slowdown RCT]].

## Quality & delivery

| Study | Design | Scale | Finding | Tier |
|---|---|---|---|---|
| Google DORA 2024 | Survey + modeling | Large (industry) | 25% rise in AI adoption ↔ **−1.5% throughput, −7.2% delivery stability**; batch-size mechanism | E2/E3 |
| GitClear 2024–25 [^funder] | Git history analysis | 211M+ changed lines (2020–2024) | Churn **3.1%→5.7%**; copy-paste **8.3%→12.3%**; refactoring **25%→<10%**; 8x duplicated blocks in 2024 | E2 (single-vendor, methodology debated) |
| GitHub "passes tests" claim [^funder] | Single study | — | Copilot code "53.2% more likely to pass unit tests" (sometimes misreported as 56%) | E2 (single study; read against the oracle caveat) |

Detail and mechanism in [[Concept - AI's Effect on Code Quality and Security]]. On GitClear churn: an earlier report *projected* ~7% for 2024, and the measured figure was 5.7%.

## Security

| Study | Design | Finding | Tier |
|---|---|---|---|
| Perry et al. 2023 (Stanford, ACM CCS) | Controlled user study (codex-davinci-002) | Devs with an AI assistant wrote **less secure code** (4 of 5 tasks) yet were **more confident** it was secure | E2 |
| Spracklen et al. 2025 (USENIX Security) | 576k samples, 16 models | **~19.7%** of recommended packages don't exist (open **21.7%**, commercial **5.2%**) → **slopsquatting** | E2/E3 |

## Agentic benchmarks (not the same as productivity)

| Benchmark | What it measures | 2026 reading | Tier |
|---|---|---|---|
| SWE-bench Verified | Patch resolves a real GitHub issue (hidden tests) | ~70–80%+ on Verified, but ≥59% of a hard subset had flawed tests; **retired by OpenAI Feb 2026** | E2 |
| SWE-bench Pro | Contamination-resistant successor | Same models drop to ~23–58% | E2 |

A benchmark score belongs to a *model + scaffold + prompt* tuple and doesn't measure productivity (see [[Breakdown - SWE-bench]]). Benchmark competence overstates deployed reliability; that's [[Concept - The Capability-Reliability Gap]].

## Enterprise / self-report

Vendor ROI surveys (developers report saving 20–55% of time) are **E1/E2**. METR found developers mis-estimate their own speedup by ~40 points, so these surveys measure *perception*, not output. Read any "our engineers feel faster" metric as evidence of adoption, not productivity. That's the core warning of [[Concept - The Evaluation Gap]].

## Reading guide

Before quoting any row, classify it on four axes. Nearly all large *positive* effects are greenfield, junior, speed-metric and vendor-affiliated.

[^task]: **Task type.** Greenfield/synthetic (Peng's HTTP server) vs mature high-context production code (METR). Gains shrink or reverse as context grows.
[^pop]: **Population.** Juniors/newcomers gain most; senior devs on familiar code can lose. METR sits at the population where every prior study found the *smallest* benefit, so its slowdown doesn't contradict the RCTs above.
[^funder]: **Funder.** Vendor-affiliated (GitHub, Microsoft, GitClear) vs independent (METR, Stanford, academic). Publication and task-selection bias both run one way. Apply the discipline of [[Concept - Statistical Rigor in Model Evaluation]].

The fourth axis is **metric**: speed, PRs/tasks, code quality, delivery stability, security. A study can be positive on one and negative on another *at the same time* (fast to write, costly to maintain), so never collapse them. Date-stamp everything (as of 2026), because effect sizes decay as tools and models change. To build your own eval instead of borrowing these, see [[Deep Dive - Designing an Eval Harness]]. For how these forecasts have held up, see [[Reference - The AI Forecasting Track Record]]; for the market and funding side, [[Reference - AI Dev Tool Landscape]].

## Connections
- [[Breakdown - GitHub Copilot's Measured Productivity Impact]] — prose reading of the pro-productivity rows.
- [[Breakdown - The METR Developer Slowdown RCT]] — prose reading of the strongest independent row; source of the self-report warning.
- [[Concept - AI's Effect on Code Quality and Security]] — the mechanism behind the quality/security tables.
- [[Concept - The Capability-Reliability Gap]] — why benchmark rows overstate deployed value.
- [[Reference - AI Dev Tool Landscape]] — the market/funding companion to this evidence catalog.
- [[Breakdown - SWE-bench]] — deep treatment of the agentic-benchmark rows.
- [[Concept - The Evaluation Gap]] — why self-report/enterprise rows are the weakest evidence.
- [[Concept - Statistical Rigor in Model Evaluation]] — the standard for judging each study's design.
- [[Deep Dive - Designing an Eval Harness]] — how to build a study instead of citing one.
- [[Reference - The AI Forecasting Track Record]] — cross-domain check on whether these effects were predicted.
- [[Lore - AI Coding War Stories]] — the unicorn-level folklore these dry effect sizes cash out as in practice; read the numbers here, then the incidents there.

## Sources
- Peng, Kalliamvakou, Cihon, Demirer, 2023 — "The Impact of AI on Developer Productivity: Evidence from GitHub Copilot", arXiv:2302.06590 (E2).
- Cui, Demirer, Jaffe, Musolff, Peng, Salz, 2024 — "The Effects of Generative AI on High-Skilled Work", SSRN 4945566, pub. *Management Science* 2025 (E2).
- METR, 2025 — "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity", arXiv:2507.09089 (E3).
- Google DORA, 2024 — Accelerate State of DevOps Report (E2/E3).
- GitClear, 2025 — "AI Copilot Code Quality" (E2, single-vendor).
- Perry, Srivastava, Kumar, Boneh, 2023 — "Do Users Write More Insecure Code with AI Assistants?", ACM CCS (E2).
- Spracklen et al., 2025 — "We Have a Package for You!", USENIX Security (E2/E3).
