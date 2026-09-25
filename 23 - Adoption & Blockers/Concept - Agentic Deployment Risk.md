---
tags: [concept, domain/adoption-blockers, level/frontier]
aliases: [agentic risk, agent deployment risk, autonomous agent risk, agent blast radius]
summary: "Autonomy multiplies the reliability bar: per-step error compounds, actions carry blast radius, and every tool widens the injection surface."
---

# Concept - Agentic Deployment Risk

> **One-paragraph hook:** A chatbot that's wrong 5% of the time is annoying. An agent that's wrong 5% of the time *per step*, across twenty side-effecting actions, fails most trajectories and now and then sends the wrong wire transfer. As 2025–2026 moved agents from demo to production, [[Concept - Agentic Deployment Risk]] became the new blocker class. Reliability compounds against you, errors become deeds instead of text, and every tool you add widens the attack surface. Hence "give the agent more autonomy" usually lowers the success rate.

## The mechanism

Three multipliers turn ordinary model unreliability into a deployment blocker.

### 1. Compounding error over trajectories

If each step succeeds independently with probability $p$, an $n$-step task succeeds at $p^n$:

$$P_{success} = p^n$$

| per-step $p$ | 5 steps | 10 steps | 20 steps |
|---|---|---|---|
| 0.99 | 95% | 90% | 82% |
| 0.95 | 77% | 60% | **36%** |
| 0.90 | 59% | 35% | 12% |

A "95% reliable" model, excellent for single-turn chat, finishes a 20-step task end-to-end only ~36% of the time. Autonomy *exponentiates* the reliability requirement. It's [[Concept - The Capability-Reliability Gap]] with the exponent written out, and it's the main reason open-ended multi-step agents stall while narrow ones ship. Independence is a simplification: errors correlate, and a good agent recovers from some. The direction still holds, and matches how sharply success falls with task length.

### 2. Action blast radius

A chat error produces wrong *text*, which a human can ignore. An agent error produces a wrong *deed*: an email sent, a row deleted, a payment issued, a `rm` executed. The cost of a mistake goes from "reread it" to "unwind a side effect," and some side effects can't be unwound. So the security bar for an agent that *acts* is categorically higher than for one that *chats* (see [[Concept - Enterprise AI Security Exposure]]).

### 3. Injection surface

Any agent that reads untrusted content (a webpage, an email, a document, a tool result) can be hijacked by instructions planted in it. Simon Willison's **lethal trifecta** names the danger zone: *access to private data* + *exposure to untrusted content* + *ability to communicate externally*. An agent with all three can be steered into exfiltrating the very data it was trusted with. Each tool adds a channel for untrusted content, so capability and attack surface grow together. See [[Concept - Prompt Injection]] and [[Concept - Model Context Protocol (MCP)]].

## In practice

METR's time-horizon work (metr.org, 19 Mar 2025; *Time Horizon 1.1*, Jan 2026) finds the task length agents complete at 50% reliability doubled roughly every 7 months (≈196 days) over 2019–2025, speeding up to ~3–4 months in the 2024–2025 window. The best model (Claude Opus 4.6) reached a ~12-hour 50%-time-horizon by early 2026 (E2, single-lab methodology, TH1.1; see [[Concept - METR Time Horizons]]). Note the anchor: **50% reliability**. A 50%-reliable multi-hour agent is a research marvel and a production liability. Production lives in the tail, and the tail is where compounding bites.

In mid-2026 agents work where the three multipliers are contained:

- **Coding agents backed by tests/CI.** The environment checks each step cheaply, failures get caught, and version control makes changes reversible. This is the standout production category (see [[Deep Dive - Agentic Coding in Production]]).
- **Tightly scoped support/workflow flows.** Bounded action sets (look up an order, issue a refund up to $X), human approval above a threshold, everything logged.

They stall on open-ended "do my job" autonomy over irreversible, hard-to-verify actions with broad tool access. Those are the demos that impress and the deployments that get pulled without announcement, filling the [[Lore - Failed Enterprise AI Deployments]] ledger.

## Failure modes

- **Silent trajectory drift.** The agent takes a wrong turn at step 3 and confidently builds ten more steps on it. The final output looks plausible and is wrong. Catching it takes trajectory-level evaluation, not single-turn scoring, which makes it a hard case of [[Concept - The Evaluation Gap]] (path-dependent outcomes, sparse ground truth). See [[Gotchas - Agents in Production]].
- **Injection-driven action.** The agent reads a malicious email/webpage and runs the attacker's instructions. Fix: instruction/data separation, least-privilege tool scoping, and breaking the lethal trifecta (remove external comms *or* private-data access *or* untrusted input).
- **Oversight-cost collapse.** The more you have to review each action, the less the agent saves; [[Concept - The Verification Tax]] scales with autonomy. An agent you have to fully babysit has negative ROI even when it's usually right.
- **Reversibility assumed, not verified.** Teams design happy-path agents and find out in production that step 14 has no undo. Nobody asks "which actions are irreversible?" until an incident does.

## The non-obvious

**Bounded autonomy wins in production, and "add more tools/agency" usually makes reliability *worse*.** Instinct says a more capable agent deserves more freedom, but every added tool multiplies the trajectory space (lowering $p^n$ through more steps and branch points) and opens another untrusted-content channel. The deployments that survive go the other way: a small trusted action set, human approval on anything irreversible, cheap verification on every step, a hard scope boundary. Maximal agency is a demo aesthetic. Bounded autonomy is the production one.

It's also why the honest read on agent timelines (see [[Deep Dive - Bubble or Boom]]) treats capability headroom and *deployable* reliability as different curves, and enterprises buy the second. Frontier progress on the first can even become a blocker. A more capable model that isn't more *reliable per step* tempts teams into longer trajectories that compound harder.

## Connections

- [[Concept - The Capability-Reliability Gap]] — the underlying gap; agentic risk is that gap raised to the $n$-th power over a trajectory.
- [[Concept - Enterprise AI Security Exposure]] — action blast radius and the lethal trifecta make the security bar for agents far higher than for chat.
- [[Concept - Prompt Injection]] — the mechanism by which untrusted content hijacks an acting agent.
- [[Concept - Model Context Protocol (MCP)]] — each connected tool adds capability and an untrusted-content channel simultaneously.
- [[Concept - The Verification Tax]] — oversight cost scales with autonomy, undercutting the ROI of more agency.
- [[Concept - The Evaluation Gap]] — trajectory-level, path-dependent outcomes resist single-turn evaluation.
- [[Deep Dive - The Agent Loop]] — the loop internals that generate the multi-step trajectories this note reasons about.
- [[Gotchas - Agents in Production]] — the concrete pitfalls that follow from these mechanisms.
- [[Deep Dive - Agentic Coding in Production]] — the standout domain where cheap verification and reversibility make agents work.
- [[Concept - METR Time Horizons]] — the capability trend; note it measures 50% reliability, not the production tail.
- [[Deep Dive - Bubble or Boom]] — capability headroom vs deployable reliability are different curves; agentic risk is why.
- [[Concept - The Pilot-to-Production Gap]] — agentic autonomy is where the demo-to-prod cliff is steepest.
- [[Lore - Failed Enterprise AI Deployments]] — the graveyard that over-scoped autonomy keeps feeding.

## Sources

- Willison, S. (2025) — *The lethal trifecta for AI agents* (simonwillison.net). Names the private-data + untrusted-content + external-comms danger zone (E2, practitioner framing, widely adopted).
- METR (2025–2026) — *Measuring AI Ability to Complete Long Tasks* (19 Mar 2025) and *Time Horizon 1.1* (Jan 2026). 50%-reliability task horizon doubling ~7 months (≈196 days; ~3–4 months post-2024), best model ~12 hrs by early 2026 (E2, single-lab).
- Becker et al. (2025) — METR productivity RCT (arXiv:2507.09089). Grounds the oversight-cost/verification-tax link for AI-assisted work.
- MIT NANDA (2025) — *The GenAI Divide: State of AI in Business 2025*. Context: ~95% of pilots show no measurable P&L, with open-ended workflow fit as the barrier (E2).
