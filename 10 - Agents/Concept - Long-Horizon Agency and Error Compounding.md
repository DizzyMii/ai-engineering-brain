---
tags: [concept, domain/agents, level/frontier]
aliases: [error compounding, p^n decay]
summary: "Why long agent runs fail more: per-step error compounds exponentially (p^n), and only detection-and-recovery beats it."
---

# Concept - Long-Horizon Agency and Error Compounding

> **One-paragraph hook:** Give an agent a task that needs 20 correct steps in a row, and a model that's right 95% of the time per step still fails roughly two times out of three. "Per-step accuracy" hides an exponential decay, and that decay is the main reason long autonomous runs are so much harder than short ones.

## The mechanism

Treat an n-step task as n sequential decisions, each independently correct with probability $p$. If one wrong step derails the whole task (a common enough assumption for tasks with hard dependencies, where a bad early file edit corrupts everything after it), the whole run succeeds with probability

$$P(\text{success}) \approx p^n$$

The decay is harsh even for per-step numbers that look good. $p = 0.95, n = 20 \Rightarrow p^n \approx 0.36$, and at $n = 50$ it's under 8%. That's why the 2023 wave of autonomous agents, [[Lore - The AutoGPT Explosion]] above all, mostly failed on real multi-hour goals. GPT-4-era per-step reliability was nowhere near high enough for the horizons people pointed it at, and the compounding math won.

The independence assumption fails in both directions, and both matter. Errors are often *correlated*. One wrong belief formed at step 3 (a misread file, a misunderstood goal) gets acted on consistently and "correctly" for the next 20 steps. That's worse than $p^n$ predicts: the agent isn't rolling n independent dice, it's rolling one bad die and faithfully playing out the consequences. Detection and recovery push the other way and can dominate. An agent that notices step 3 was wrong and backs out breaks the naive multiplication, because the step that would have sunk the run gets corrected before it compounds. It's the most important practical fact in this area: **an agent with lower raw per-step $p$ and real error detection beats a higher-$p$ agent that can't tell when it's off track.** Detection turns a multiplicative failure process into something closer to a random walk with a restoring force.

There's also a threshold effect that echoes [[Concept - The Emergent Abilities Debate]]. Per-step reliability $p$ can improve smoothly across model generations while the *completable* horizon $n$ moves in sharp jumps, because $p^n$ is exponentially sensitive near $p \approx 1$. A small rise in $p$ can open up a class of tasks that was essentially out of reach before.

## In practice

METR's 2025 paper on [[Concept - METR Time Horizons]] ("Measuring AI Ability to Complete Long Tasks") measures horizon length directly. Instead of accuracy on a fixed task set, it finds the task duration (in human-expert hours) at which a model's success rate crosses 50%, then tracks how that duration moves across model generations. The headline: frontier models' 50%-success time horizon has been roughly doubling every ~7 months, from tasks measured in minutes toward tasks on the order of hours by 2026 *(as of 2026)*. For "can I trust this agent on task X", that's far more useful than a static benchmark percentage, and it's the empirical successor to the $p^n$ intuition, turned into a capability curve you can track. It also ties into the general difficulty of scoring agents; [[Concept - Agent Evaluation Challenges]] explains why a single success rate undersells how much reliability, beyond capability, drives real-world usability.

The mitigations all pull one of the formula's two levers: raise $p$, or shrink the effective $n$ of each unrecoverable segment.
- **Checkpoints and verification between steps** (tests, lint, a sanity re-read) turn one long unverified chain into several shorter chains with recovery points.
- **Decomposition into shorter, independently verifiable subtasks** ([[Concept - Task Decomposition and Planning]]) directly shrinks $n$ for the stretch that has to go right unsupervised.
- **Human-in-the-loop gates** at high-risk points cap the downside without capping the whole run's autonomy.
- **Better tools and prompts that raise per-step $p$**, the same "invest in the interface" lesson coding agents learned the hard way.
- **Reflection mechanisms** ([[Concept - Reflection and Self-Correction]]) are the model-side version of detection and recovery. They only help when there's an external signal to reflect against; pure self-critique doesn't do it.

## Failure modes

The signature failure is the **death spiral**. The agent drifts slightly off track, its later reasoning rationalizes the wrong state as correct instead of flagging it, and each step builds on the bad foundation. By the time the transcript is long enough for a human to notice, dozens of turns of wasted or harmful work have piled up. It's the long-run version of the loop and drift failures in [[Gotchas - Agents in Production]]. Detection works better as monitoring for stalled-progress signals (repeated similar tool calls, a todo list that stops shrinking) than as waiting for the final outcome.

## The non-obvious

The industry has shifted emphasis from "make the model smarter" to "make the model notice when it's wrong". That's the bet behind [[Concept - Trained vs Prompted Agents]]: RL training on long agentic rollouts puts recovery behavior into the weights (learning *when* to backtrack, as well as how), instead of relying on a hand-written reflection prompt bolted onto a frozen model. The AutoGPT era used essentially the same scaffolding loop that works reasonably well on 2025-26 models. The scaffold barely changed. The underlying model's per-step $p$ and recovery ability did.

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
