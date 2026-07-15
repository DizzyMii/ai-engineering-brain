---
tags: [concept, domain/agents, level/frontier]
aliases: [error compounding, p^n decay]
summary: "Why long agent runs fail more: per-step error compounds exponentially (p^n), and only detection-and-recovery beats it."
---

# Concept - Long-Horizon Agency and Error Compounding

> **One-paragraph hook:** Give an agent a task that takes 20 correct steps in a row, and a model that's right 95% of the time per step still fails it roughly two times out of three — the single number "per-step accuracy" hides an exponential decay that is the real reason long autonomous runs are so much harder than short ones.

## The mechanism

Model an n-step task as n sequential decisions, each independently correct with probability $p$. If a single wrong step derails the whole task — a common enough assumption for tasks with hard dependencies, where a bad file edit early on corrupts everything downstream — the probability the whole run succeeds is

$$P(\text{success}) \approx p^n$$

The decay is brutal even for good-looking per-step numbers: $p = 0.95, n = 20 \Rightarrow p^n \approx 0.36$; push to $n = 50$ and it drops under 8%. This is the mechanism behind why the 2023 wave of autonomous agents — [[Lore - The AutoGPT Explosion]] chief among them — mostly failed on real multi-hour goals: GPT-4-era per-step reliability was nowhere near high enough for the horizons users were pointing it at, so the compounding math simply won.

The independence assumption cuts both ways, and both cuts matter. Errors are often *correlated*, not independent — one wrong belief formed at step 3 (misreading a file, misunderstanding the goal) gets acted on consistently and "correctly" for the next 20 steps, which is worse than $p^n$ predicts, because the agent isn't rolling n independent dice, it's rolling one bad die and then playing out its consequences faithfully. But detection-and-recovery capability works in the opposite direction and can dominate: an agent that notices step 3 was wrong and backs out breaks the naive multiplication entirely, because the step that would have doomed the run gets corrected rather than compounded. This is the single most important practical fact in the whole area: **an agent with lower raw per-step $p$ but real error-detection beats a higher-$p$ agent that can't tell when it's off track**, because detection turns a multiplicative failure process into something closer to a random walk with a restoring force.

There's also a threshold-effect flavor to this that echoes [[Concept - The Emergent Abilities Debate]]: the underlying per-step reliability $p$ can improve smoothly across model generations while the *task-completable* horizon $n$ it unlocks moves in sharp jumps, because $p^n$ is exponentially sensitive near $p \approx 1$ — a small rise in $p$ can unlock a task class that was previously essentially unreachable.

## In practice

METR's 2025 paper on [[Concept - METR Time Horizons]] ("Measuring AI Ability to Complete Long Tasks") operationalizes horizon length directly: instead of reporting accuracy on a fixed task set, it measures the task duration (in human-expert-hours) at which a model's success rate crosses 50%, then tracks how that duration moves across model generations. The headline finding: frontier models' 50%-success time horizon has been roughly doubling every ~7 months, moving from tasks measured in minutes toward tasks on the order of hours by 2026 *(as of 2026)* — a far more decision-relevant number for "can I trust this agent on task X" than a static benchmark percentage, and it is the direct empirical successor to the $p^n$ intuition, converting it into a trackable capability curve. This complements the general difficulty of scoring agents at all — see [[Concept - Agent Evaluation Challenges]] for why a single success-rate number undersells how much reliability, not just capability, drives real-world usability.

The practical mitigations all attack one of the two levers in the formula — raise $p$, or shrink the effective $n$ per unrecoverable segment:
- **Checkpoints and verification between steps** (tests, lint, a sanity re-read) convert a long unverified chain into a series of shorter chains with recovery points.
- **Decomposition into shorter, independently verifiable subtasks** ([[Concept - Task Decomposition and Planning]]) directly shrinks $n$ for the segment that must go right unsupervised.
- **Human-in-the-loop gates** at high-risk junctures cap downside without capping the whole run's autonomy.
- **Better tools and prompts that raise per-step $p$ directly** — the same "invest in the interface" lesson coding agents learned the hard way.
- **Reflection mechanisms** ([[Concept - Reflection and Self-Correction]]) are the model-side analogue of detection-and-recovery, though they only help when there's an external signal to reflect against, not pure self-critique.

## Failure modes

The signature failure is the **death spiral**: an agent goes slightly off-track, its subsequent reasoning rationalizes the wrong state as correct rather than flagging it, and each further step is built on the bad foundation — by the time the transcript is long enough for a human to notice, dozens of turns of wasted or actively harmful work have accumulated. This is the long-run instance of the loop and drift failures cataloged in [[Gotchas - Agents in Production]]. Detection works better as monitoring for stalled-progress signals (repeated similar tool calls, a todo list that stops shrinking) than as waiting for the final outcome to reveal itself.

## The non-obvious

The industry's read on this has flipped the emphasis from "make the model smarter" to "make the model notice when it's wrong" — which is exactly the bet behind [[Concept - Trained vs Prompted Agents]]: RL-training a model on long agentic rollouts teaches recovery behavior directly into the weights (learning *when* to backtrack, not just how), rather than relying on a hand-written reflection prompt bolted onto a frozen model. The AutoGPT era used essentially the same scaffolding loop that works reasonably well on 2025-26 models — the scaffold didn't fundamentally change; the per-step $p$ and recovery capability of the underlying model did.

## Connections
- [[Concept - Reflection and Self-Correction]] — the model-side mechanism for detect-and-recover that breaks the naive $p^n$ decay.
- [[Concept - Agent Evaluation Challenges]] — why a single success-rate score can't capture the reliability-over-horizon story this note describes.
- [[Lore - The AutoGPT Explosion]] — the historical case study of what happens when users point $p^n$-limited models at hours-long horizons.
- [[Gotchas - Agents in Production]] — the death-spiral failure signature and its detection in a running system.
- [[Concept - Task Decomposition and Planning]] — shrinking the unsupervised segment length is a direct lever on the compounding formula.
- [[Concept - Trained vs Prompted Agents]] — training recovery behavior into the model rather than scaffolding it on top.
- [[Concept - The Emergent Abilities Debate]] — the same smooth-metric/sharp-threshold shape shows up when $p^n$ crosses a usability cliff as $n$ grows.
- [[Concept - METR Time Horizons]] — the empirical measurement this note's math predicts and explains.

## Sources
- METR (2025) — "Measuring AI Ability to Complete Long Tasks." Defines the 50%-success time-horizon metric and reports the ~7-month doubling trend.
- Yao et al. (2022) and the AutoGPT/BabyAGI repos (2023) — the empirical substrate for why early scaffolded agents hit the $p^n$ wall at real-world horizons.
