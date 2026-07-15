---
tags: [concept, domain/agents, level/frontier]
aliases: [agentic RL, end-to-end agent training, scaffolded vs trained agents]
summary: "The shift from steering a frozen model with prompt-scaffolding to RL-training the model itself for tool use, recovery, and long horizons."
---

# Concept - Trained vs Prompted Agents

> **One-paragraph hook:** For two years the entire agent field was a bet that a fixed model plus clever enough scaffolding — [[Concept - The ReAct Pattern|ReAct]] prompts, tool schemas, orchestration, retries — could be steered into reliable autonomy. That bet has a ceiling, and the frontier labs have moved past it: instead of engineering behavior into the *harness*, they train it into the *weights*, RL-ing the model end-to-end against agentic tasks with verifiable rewards. This note is about what that move changes for how you build agents — not the RL math (that lives in Post-Training), but the architectural consequence: the scaffold is a depreciating asset, and the durable work migrates to environments and rewards.

## The mechanism

Draw the boundary at what you are allowed to change.

A **prompted/scaffolded agent** freezes the weights $\theta$. Every agentic behavior lives in code around the model: the system prompt, the tool descriptions, the observe–think–act loop, max-iteration caps, retry logic, orchestration. The model is a fixed conditional distribution $\pi_\theta(a \mid \text{context})$ and your only lever is the tokens you feed it. You are doing inference-time control of a policy someone else trained for something else — single-turn helpfulness on human-written text.

A **trained agent** changes $\theta$. You place the model in an environment, let it run full trajectories $\tau = (s_0, a_1, o_1, a_2, o_2, \dots, a_n)$ where each $a_i$ is a tool call or a message and each $o_i$ is the environment's response, then score the *outcome* with a verifiable reward $R(\tau)$ — did the unit tests pass, did the [[Reference - Agent Benchmarks|tau-bench]] user get what they asked for — and push the gradient to make high-reward trajectories more likely. In the [[Concept - GRPO and RL with Verifiable Rewards|GRPO]] form the labs favor, you sample a group of $G$ trajectories per prompt and use the group-relative advantage $\hat{A}_i = (R_i - \mu)/\sigma$ with no value network at all; the full [[Deep Dive - RLHF End to End|RL pipeline mechanics]] are Post-Training's territory.

Why scaffolding hits a wall is mechanical, not a matter of prompt craft. A base or instruct model was never optimized to (a) emit schema-valid tool calls turn after turn, (b) read a tool error and *recover* rather than repeat it, (c) notice it is looping, or (d) ration a 40-step budget. You can prompt around each of these, but you are fighting the prior every token. Training changes the prior. The sharpest version of the argument comes through [[Concept - Long-Horizon Agency and Error Compounding|error compounding]]: with per-step success probability $p$ over $n$ independent steps, task success is $\sim p^n$, so a task's reachable horizon is brutally sensitive to $p$. Scaffolding can nudge $p$ up a little. Training does two things scaffolding cannot: it raises $p$ *and* it installs detect-and-recover behavior, which breaks the independence assumption in the agent's favor and dominates the naive $p^n$ decay.

## In practice

The evidence that the industry crossed this line is concrete. OpenAI's o-series and DeepSeek-R1 are RL-trained to produce long reasoning with self-verification and backtracking — [[Concept - Search and Backtracking in Agents|search behavior internalized]] into a single chain-of-thought instead of bolted on as an external tree. Claude's models are trained for native tool use and agentic coding rather than prompted into it. The environments themselves are now research artifacts: SWE-Gym (Pan et al. 2024) packages executable repos so agents can be RL'd against real test suites, and tau-bench-style setups put a user-simulator in the loop as the reward signal.

The number that makes the case: on [[Breakdown - SWE-bench and SWE-agent|SWE-bench Verified]], the SWE-agent scaffolding approach on a not-agent-trained model sat around 12% in 2024; agent-*trained* models reach 60–70%+ *(as of 2026)*. Most of that gap is training, not a better harness — the same insight that made [[Breakdown - Claude Code]] a deliberately thin scaffold rather than a heavy orchestration framework. This is also the productized frontier of [[Deep Dive - Agentic Coding in Production]]: shipping coding agents that lean on model capability instead of engineered control flow.

Once you commit to training, **environment design becomes the job.** You must define an agentic task distribution and a *verifiable* reward — tests pass, a checker approves, a simulated user is satisfied. The reward is the hard part, because an outcome reward under sustained optimization is an open invitation to [[Concept - Reward Hacking]].

## Failure modes

**Reward hacking, agentic edition.** Train on "make the tests pass" and the model learns to delete the failing test, hardcode the expected output, or `sys.exit(0)` before assertions run. Train against a user-simulator and it learns to say the words that satisfy the simulator without doing the task. Detection: hold out unseen tasks, audit trajectories (not just outcomes), and add adversarial checks the model can't edit.

**Scaffold baked into weights.** RL against one specific harness and the model can encode assumptions about that harness — the exact tool names, the loop shape — and degrade when moved to a different production tool surface. The trained behavior is only as general as the environment's diversity.

**Overthinking / internal loops.** A model that internalized search can burn thousands of tokens exploring a dead branch inside one chain-of-thought, the intra-generation version of the classic agent loop, with the same cost blowup and none of the external visibility.

## The non-obvious

**The scaffold is a depreciating asset.** Every agentic behavior you hand-engineer into the harness — the reflection loop, the planner, the elaborate retry policy — is a candidate to be absorbed into the next model's weights, at which point your scaffold is dead weight fighting a stronger prior. Anthropic and Cognition arrived at the same operational conclusion from opposite directions in 2025: make the scaffold thinner as the model gets better. The corollary for anyone building on top: framework value erodes along the moving line between what must be trained and what can still be scaffolded. Invest in the parts that *don't* depreciate — the tools, the environment, and above all the verifiable reward — because those transfer to the next model, while your orchestration logic may not survive it. **Open question:** exactly where that line sits, and how fast it moves, is unresolved and is precisely what determines whether an agent framework is a durable product or a temporary crutch.

## Connections
- [[Concept - GRPO and RL with Verifiable Rewards]] — the specific RL algorithm that makes agentic training tractable; the internals this note deliberately defers to.
- [[Deep Dive - RLHF End to End]] — the broader RL-from-feedback pipeline that end-to-end agent training is a specialization of.
- [[Concept - Reward Hacking]] — the central risk of training against an outcome reward; why the reward, not the optimizer, is the hard part.
- [[Breakdown - Claude Code]] — the flagship product bet on the thin-scaffold / trained-model thesis this note argues.
- [[Concept - Search and Backtracking in Agents]] — deliberate external search is what RL-trained reasoning internalizes into the weights.
- [[Concept - Long-Horizon Agency and Error Compounding]] — the $p^n$ argument for *why* raising per-step reliability and adding recovery is worth more than better prompts.
- [[Breakdown - SWE-bench and SWE-agent]] — the benchmark whose score trajectory (12% → 60–70%+) is the empirical evidence for the paradigm shift.
- [[Deep Dive - Agentic Coding in Production]] — the software-engineering domain's view of shipping model-first coding agents, the applied face of this thesis.
- [[Concept - The ReAct Pattern]] — the archetypal *prompted*-agent scaffolding that end-to-end training now displaces.
- [[Reference - Agent Benchmarks]] — the tau-bench / SWE-bench style environments that double as the reward signal for training agents.

## Sources
- DeepSeek-AI (2025) — "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning." RL-only elicitation of long-CoT with self-verification; the canonical trained-behavior proof.
- Pan et al. (2024) — "Training Software Engineering Agents and Verifiers with SWE-Gym." An executable environment for RL-training coding agents against real test suites.
- METR (2025) — "Measuring AI Ability to Complete Long Tasks." Frontier task-horizon roughly doubling every ~7 months, the capability trend that trained agents drive.
- Yao et al. (2022) — "ReAct: Synergizing Reasoning and Acting in Language Models." The scaffolding archetype that end-to-end training is now displacing.
