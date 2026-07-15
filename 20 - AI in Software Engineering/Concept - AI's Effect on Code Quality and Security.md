---
tags: [concept, domain/applied-software, level/advanced]
aliases: [AI code quality, AI code churn, slopsquatting, insecure AI code, AI technical debt]
summary: "The measured downstream cost of AI-written code: rising churn/duplication, falling refactoring, insecure code, hallucinated-package attacks."
---

# Concept - AI's Effect on Code Quality and Security

> AI writes code faster; the question this note answers is what that code costs *after* it's committed. The measured signals — code churn, duplication, declining refactoring, delivery instability, insecure patterns, and a new supply-chain attack class called slopsquatting — point the same direction: LLMs optimize for locally-plausible code and externalize the maintenance and security cost to whoever reads it next. The productivity gain and the quality debt can both be real at once; which one you see depends on whether you measure at commit time or twelve months out.

## The mechanism

An LLM generates the most probable continuation of code given context. "Probable" is not "maintainable" and not "secure," and the divergence is systematic, not random:

- **It cannot feel maintenance cost.** Refactoring — extracting a shared abstraction, deleting a duplicate — is an investment that pays off later. The model has no later; it minimizes next-token loss over the current buffer. Presented with a near-duplicate block, generating a fresh copy is higher-probability and lower-friction than restructuring the codebase to share it. So AI **biases toward adding over refactoring**: copy-paste up, moved/refactored lines down.
- **It asserts current behavior, not correct behavior.** When drafting tests or patches, the model's prior is "what does this code do," which freezes existing bugs into the regression suite — the oracle problem from [[Concept - AI in Software Testing]].
- **It inherits its training corpus's vulnerabilities.** Public code is full of insecure patterns (string-concatenated SQL, disabled cert checks, hardcoded secrets). The model reproduces them at their training frequency, and does so with fluent, confident-looking code that *reads* as correct — which is exactly what defeats a skimming reviewer.
- **It hallucinates referents.** Package names, API functions, config flags that don't exist are generated because they're plausible tokens. For dependencies this opens an attack surface (below).

The through-line is the [[Concept - The Capability-Reliability Gap]]: the model is capable of correct, secure, well-factored code, but its *expected* output regresses toward the plausible mean of its corpus, and the last mile of quality is the expensive part.

## In practice

The measured evidence, tiered (see [[Reference - Developer Productivity Studies]] for the full catalog):

**Churn, duplication, refactoring — GitClear** (211M+ changed lines, Jan 2020–Dec 2024):
| Metric | 2020/21 baseline | 2024 | Tier |
|---|---|---|---|
| Code revised within 2 weeks of commit (churn) | 3.1% (2020) | 5.7% | E2 (single-vendor) |
| Copy-pasted (cloned) lines | 8.3% | 12.3% | E2 |
| Refactored / "moved" lines | 25% (2021) | <10% | E2 |
| Blocks with 5+ duplicated lines | — | ~8x increase during 2024 | E2 |

(Churn nearly doubled off its 2020 base; GitClear's earlier 2024 report *projected* it would reach ~7%, the actual 2024 figure came in at 5.7%. GitClear is single-vendor and its methodology is debated — E2, not E3.)

**Delivery — Google DORA 2024** (large survey): a 25% increase in AI adoption is *associated with* a **−1.5%** delivery throughput and **−7.2%** delivery stability, with **growing batch size** as the proposed mechanism — AI makes it cheap to write more code per change, and larger changesets have always hurt stability (E2/E3). This is the individual-vs-org disconnect that [[Concept - Team Workflow Restructuring with AI]] centers on.

**Security — insecure code, Perry et al. 2023 (Stanford, ACM CCS):** in a controlled user study (codex-davinci-002), participants with an AI assistant wrote **less secure code on 4 of 5 tasks** yet were **more confident it was secure** — a measured "false sense of security" (E2). Participants who trusted the AI less and iterated on prompts produced more secure code.

**Security — supply chain, Spracklen et al. 2025 (USENIX Security):** "We Have a Package for You!" — across 576,000 code samples from 16 models (Sept 2024 cohort), **~19.7% of recommended packages did not exist** (open-source models **21.7%**, commercial **5.2%**), yielding 205,474 unique hallucinated names (E2/E3). Attackers register those names on PyPI/npm — **slopsquatting** (term coined by Seth Larson, PSF), the first AI-native supply-chain attack class, and a fixture of [[Lore - AI Coding War Stories]]. It is distinct from, but rhymes with, [[Concept - Prompt Injection]] as an AI-specific attack surface.

**Maintainability lag** — "Echoes of AI" (2025) and related work find AI-assisted code trending toward lower maintainability, with the cost surfacing months later as tech debt rather than at commit time (E1/E2, emerging).

## Failure modes

- **Coverage theater.** AI cheaply inflates line/branch coverage while assertions stay weak, so a dashboard shows "quality up" while the suite catches nothing new — see [[Concept - AI in Software Testing]].
- **Reviewer laundering.** AI writes the code, AI reviews the code (see [[Concept - AI Code Review]]), and no human ever reads it deeply. Alert fatigue from false positives makes reviewers rubber-stamp. The oversight loop thins exactly where the [[Concept - The Capability-Reliability Gap]] is widest.
- **Silent dependency compromise.** A hallucinated `import` that a slopsquatter has pre-registered installs malware on first `pip install` — detected only by dependency allowlisting, not by tests. Autonomous agents that install packages unattended (see [[Gotchas - Agents in Production]]) amplify this.
- **Debt that surfaces off-cycle.** Because maintainability is a lagging indicator, the team that measured a speedup at commit time gets the bill 6–12 months later as slowing feature velocity, and mis-attributes it.

## The non-obvious

The productivity effect and the quality effect are **not in contradiction** — both are real, and they are measured at different times. AI genuinely makes code *faster to write* and often *costlier to maintain*, so "does AI help?" is underspecified until you name the measurement horizon. Nearly every vendor ROI claim stops measuring at commit time, where AI looks best; the churn, duplication, and stability costs land later, where nobody is still counting — an unpriced cost that the true [[Concept - Unit Economics of LLM Products]] of shipping with AI ought to include alongside the inference bill, but rarely does. An honest evaluation instruments rework rate and delivery stability over quarters, not keystrokes over minutes — the discipline [[Playbook - Measuring AI ROI]] exists to enforce — and this measurement horizon problem is why AI-written code sits at the center of emerging liability and disclosure regimes ([[Lore - Hallucination Liability Incidents]], [[Reference - The EU AI Act for Operators]]).

## Connections

- [[Concept - AI Code Review]] — the proposed remedy; also the laundering risk when AI both writes and reviews.
- [[Concept - AI in Software Testing]] — coverage-not-correctness and the oracle problem are the testing face of this quality debt.
- [[Reference - Developer Productivity Studies]] — the tiered catalog of every study cited here.
- [[Breakdown - The METR Developer Slowdown RCT]] — the high quality bar that rejected AI output is this maintainability pressure felt as lost time.
- [[Concept - The Capability-Reliability Gap]] — the root cause: expected output regresses to the plausible corpus mean.
- [[Lore - AI Coding War Stories]] — slopsquatting and vibe-coding disasters are these mechanisms in the wild.
- [[Concept - Team Workflow Restructuring with AI]] — batch-size growth and the individual-vs-org disconnect.
- [[Lore - Hallucination Liability Incidents]] — who is liable when AI-written code ships a vulnerability.
- [[Concept - Prompt Injection]] — the other major AI-specific security surface in the coding stack.
- [[Reference - The EU AI Act for Operators]] — the regulatory pressure toward disclosing and controlling AI-generated code.
- [[Gotchas - Agents in Production]] — unattended package installation and command execution amplify the supply-chain risk.
- [[Playbook - Measuring AI ROI]] — the measurement-horizon problem here (commit-time speedup vs quarter-scale maintenance cost) is exactly what an honest ROI measurement has to instrument (cross-domain: economics).
- [[Concept - Unit Economics of LLM Products]] — churn, duplication, and rework are a deferred cost the per-token/per-seat price of AI-generated code doesn't capture (cross-domain: economics).

## Sources
- GitClear, 2025 — "AI Copilot Code Quality" (211M+ lines, 2020–2024): churn 3.1%→5.7%, copy-paste 8.3%→12.3%, refactoring 25%→<10%, 8x duplicated blocks (E2, single-vendor, methodology debated).
- Google DORA, 2024 — Accelerate State of DevOps Report: 25% AI adoption ↔ −1.5% throughput, −7.2% stability, batch-size mechanism (E2/E3).
- Perry, Srivastava, Kumar, Boneh, 2023 — "Do Users Write More Insecure Code with AI Assistants?" ACM CCS. Less-secure code plus false confidence (E2).
- Spracklen et al., 2025 — "We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs", USENIX Security. ~19.7% hallucinated packages; slopsquatting (E2/E3).
- "Echoes of AI" and related maintainability studies, 2025 — AI-assisted code trends toward lower maintainability (E1/E2, emerging).
