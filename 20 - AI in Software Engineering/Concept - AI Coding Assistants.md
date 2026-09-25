---
tags: [concept, domain/applied-software, level/surface]
aliases: [AI coding tools, AI pair programmer, code assistant]
summary: "Taxonomy of AI developer tools across three generations of autonomy, and why the headline 'faster' claim is contested, not settled."
---

# Concept - AI Coding Assistants
> An AI coding assistant is a code-tuned LLM wrapped in scaffolding that gives it repo context and the ability to act: autocomplete, chat, or agent. The wrapping turns a model into something a developer can use daily, and it's also where most of the reliability problems live. If you're choosing one, know which generation you're picking. Each generation trades more autonomy for more error surface.

## The mechanism
Every AI coding assistant mixes the same three ingredients in different ratios. There's a code-tuned LLM. There's context about the specific repo, usually retrieval or indexing over the codebase instead of the whole thing stuffed in-context. And there's a chat template plus tool calls that let the model act as well as predict text ([[Concept - Tool Use and Function Calling]], [[Concept - Model Context Protocol (MCP)]]). Products differ in the loop the model runs inside:

1. **Inline autocomplete (2021-):** the model sees the cursor position and surrounding code, predicts the next tokens, and stops. No planning, execution or verification. The human accepts or rejects each suggestion, the lightest form of the [[Pattern - Human-in-the-Loop Review Workflow]] every generation here depends on. GitHub Copilot (2021), Tabnine and Codeium/Windsurf's completion engine belong here. It fires on every keystroke, so the latency budget is tight (sub-second), and these tools use small, distilled models instead of the frontier model.
2. **In-IDE chat/edit (2023-):** the model gets a multi-turn conversation and can propose a diff across one or a few files; the human still applies it. Copilot Chat and Cursor's chat/Tab-plus-inline-edit belong here. The scaffolding adds retrieval over the repo (embeddings-based indexing), so the model can answer "where is X defined" without the whole codebase in context.
3. **Autonomous agents (2024-):** the model runs its own read→edit→execute→observe loop. It opens files, runs shell commands, executes tests and iterates without a human at each step, stopping only at a budget or a PR boundary. Devin (Cognition), Claude Code (Anthropic), Cursor Composer and OpenAI Codex belong here ([[Deep Dive - The Agent Loop]], [[Deep Dive - Agentic Coding in Production]]).

Each step up adds autonomy, and with it a longer chain of model decisions between the human's last input and the resulting code. Reliability degrades along that chain ([[Concept - The Capability-Reliability Gap]]).

## In practice
Scale first. GitHub Copilot passed 20 million all-time users by July 2025, adding 5M in Q2 FY25 alone, and Satya Nadella reported deployment across 90% of the Fortune 100 (E2, Microsoft's own earnings disclosure, July 2025). Direct estimates put AI-generated code at roughly 25-30% of new code by late 2024 (E2: Sundar Pichai on Google's Q3-2024 earnings call, ~25% of new Google code; DX telemetry across 4.2M developers, 26.9%; a 2025 *Science* study, ~30% of U.S. Python functions). The widely quoted "41%" didn't come from GitClear. GitClear's 211M-line study measures churn, clone rate and refactoring share and says nothing about authorship. The 41% is an E1 extrapolation, popularized by Emad Mostaque, from GitHub Copilot's suggestion-acceptance rate. Don't cite it as a direct measurement of AI-generated-code share.

"Vibe coding" is Andrej Karpathy's term, posted to X on February 2, 2025, for the far end of generation 3: "I just see stuff, say stuff, run stuff, and copy-paste stuff, and it mostly works." You give in to the model's output without reading it line by line. Karpathy meant it for disposable weekend projects. The term escaped that scope and now stands for both the productivity promise and the incident class it produces on production systems ([[Lore - AI Coding War Stories]]).

Day to day, these tools move developer time from typing to reviewing. The bottleneck shifts from writing code to verifying it, which is the [[Concept - The Verification Tax]] that each higher-autonomy generation raises. The shift compounds as more of the team adopts higher-autonomy tools ([[Concept - Team Workflow Restructuring with AI]]).

## Failure modes
- **Autocomplete:** plausible but subtly wrong completions get accepted without scrutiny because they compile. Low risk per suggestion, but at volume small error rates add up.
- **Chat/edit:** the model edits from a retrieval window that can miss relevant context elsewhere in a large repo, so changes come out locally correct and globally wrong.
- **Agents:** the full failure mode of an autonomous loop. An agent can act on a wrong plan for many steps before anyone notices ([[Concept - The Capability-Reliability Gap]] covers error compounding). The standard incident is Replit's agent deleting a production database mid-code-freeze in July 2025 ([[Lore - AI Coding War Stories]]).

## The non-obvious
"AI makes developers faster" doesn't have one effect size. It depends entirely on task type and population, and the two best-designed controlled studies in this domain point in opposite directions. Peng et al.'s 2023 RCT found Copilot users finished a narrow greenfield HTTP-server task 55.8% faster (E2, N=95 freelancers, GitHub/Microsoft-affiliated). METR's 2025 RCT gave experienced developers Cursor Pro + Claude 3.5/3.7 Sonnet on their own mature open-source repos and found them 19% *slower* (E3, N=16, 246 real tasks). Afterward, those same developers still believed AI had sped them up by 20% ([[Breakdown - GitHub Copilot's Measured Productivity Impact]], [[Breakdown - The METR Developer Slowdown RCT]]). Both studies are real and well run. They measured different regimes: novice/greenfield vs. expert/mature-codebase. Read any single productivity number in this space as conditional on task and population, never as a universal constant. Coding is one instance of a general enterprise problem that [[Concept - The Evaluation Gap]] names: without a task-matched eval, demos and vendor studies can point one way while measured reality points the other.

## Connections
- [[Concept - The Capability-Reliability Gap]] — the framework for why more autonomy (generation 3) means a wider gap between what the model can do and what it reliably does.
- [[Breakdown - GitHub Copilot's Measured Productivity Impact]] — the evidence base for generation-1/2 productivity claims, read critically.
- [[Breakdown - Cursor]] — the commercial product that popularized generation-2-into-3 (Tab + Composer) and became the fastest-growing dev tool of the cycle.
- [[Deep Dive - Agentic Coding in Production]] — the full architecture and failure-mode walkthrough for generation-3 agents.
- [[Concept - Team Workflow Restructuring with AI]] — how the authoring-to-reviewing time shift changes team process, not just individual output.
- [[Reference - AI Dev Tool Landscape]] — the market map of specific vendors in each generation.
- [[Breakdown - The METR Developer Slowdown RCT]] — the contradicting evidence that keeps the "faster" claim honest.
- [[Lore - AI Coding War Stories]] — where vibe coding and unsupervised agents actually went wrong.
- [[Deep Dive - The Agent Loop]] — the generic mechanism (read/act/observe) that generation-3 tools implement for coding specifically.
- [[Concept - Tool Use and Function Calling]] — the mechanism that lets a chat model become an agent that can run shell commands and tests.
- [[Concept - Model Context Protocol (MCP)]] — the emerging standard for how coding agents connect to external tools and data sources.
- [[Concept - Token Price Deflation]] — falling inference costs are part of why generation-3 (expensive, many-step agents) became commercially viable in 2025-2026.
- [[Concept - The Verification Tax]] — each generation shifts more developer time from authoring to checking output; that verification cost is the hidden price of autonomy (cross-domain: adoption).
- [[Pattern - Human-in-the-Loop Review Workflow]] — from accept/reject on autocomplete to a PR gate on agent output, the human-review workflow is what keeps each generation usable (cross-domain: business functions).
- [[Concept - The Evaluation Gap]] — the general pattern (demo/self-report vs. measured reality diverging) that the Peng-vs-METR contradiction here is a specific, well-documented instance of (cross-domain: adoption).

## Sources
- Peng, S. et al. (2023) — "The Impact of AI on Developer Productivity: Evidence from GitHub Copilot," arXiv:2302.06590. The 55.8% RCT.
- METR (2025) — "Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity," arXiv:2507.09089. The 19% slowdown RCT.
- GitClear (2025) — "AI Copilot Code Quality Research," gitclear.com. Source of the churn (3.1%→5.7%) and clone-rate (8.3%→12.3%) data; not a source for AI-authorship share.
- Karpathy, A. (Feb 2, 2025) — X post coining "vibe coding," x.com/karpathy/status/1886192184808149383.
- Microsoft (July 2025) — FY2025 Q4 earnings call; source of the 20M users / 90% Fortune 100 figures.
- Pichai, S., Google Q3-2024 earnings call (Oct 2024) — ~25% of new Google code AI-generated; DX (2024) — telemetry across 4.2M developers, 26.9%; Science (2025) — ~30% of U.S. Python functions by late 2024. The direct-measurement estimates. The "~41%" figure is an E1 extrapolation popularized by Emad Mostaque from Copilot acceptance-rate data, not a direct measurement.
