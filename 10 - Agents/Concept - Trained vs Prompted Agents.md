---
tags: [concept, domain/agents, level/frontier]
aliases: [agentic RL, end-to-end agent training, scaffolded vs trained agents]
summary: "The shift from steering a frozen model with prompt-scaffolding to RL-training the model itself for tool use, recovery, and long horizons."
---

# Concept - Trained vs Prompted Agents

> **One-paragraph hook:** For two years the agent field bet that a fixed model plus clever enough scaffolding ([[Concept - The ReAct Pattern|ReAct]] prompts, tool schemas, orchestration, retries) could be steered into reliable autonomy. That bet has a ceiling, and the frontier labs have moved past it. They train behavior into the *weights* instead of engineering it into the *harness*, RL-ing the model end-to-end against agentic tasks with verifiable rewards. This note covers what that changes for how you build agents. The RL math lives in Post-Training; the architectural consequence is that the scaffold is a depreciating asset and the durable work moves to environments and rewards.

## The mechanism

Draw the boundary at what you're allowed to change.

A **prompted/scaffolded agent** freezes the weights $\theta$. Every agentic behavior lives in code around the model: the system prompt, the tool descriptions, the observe–think–act loop, max-iteration caps, retry logic, orchestration. The model is a fixed conditional distribution $\pi_\theta(a \mid \text{context})$ and your only lever is the tokens you feed it. You're doing inference-time control of a policy someone else trained for something else: single-turn helpfulness on human-written text.

A **trained agent** changes $\theta$. You put the model in an environment and let it run full trajectories $\tau = (s_0, a_1, o_1, a_2, o_2, \dots, a_n)$, where each $a_i$ is a tool call or a message and each $o_i$ is the environment's response. Then you score the *outcome* with a verifiable reward $R(\tau)$ (did the unit tests pass, did the [[Reference - Agent Benchmarks|tau-bench]] user get what they asked for) and push the gradient toward high-reward trajectories. In the [[Concept - GRPO and RL with Verifiable Rewards|GRPO]] form the labs favor, you sample a group of $G$ trajectories per prompt and use the group-relative advantage $\hat{A}_i = (R_i - \mu)/\sigma$, with no value network. The full [[Deep Dive - RLHF End to End|RL pipeline mechanics]] belong to Post-Training.

The wall is mechanical. A base or instruct model was never optimized to (a) emit schema-valid tool calls turn after turn, (b) read a tool error and *recover* instead of repeating it, (c) notice it's looping, or (d) ration a 40-step budget. You can prompt around each of these, but you fight the prior on every token. Training changes the prior.

The sharpest version of the argument is [[Concept - Long-Horizon Agency and Error Compounding|error compounding]]. With per-step success probability $p$ over $n$ independent steps, task success is $\sim p^n$, so how far a task can reach is brutally sensitive to $p$. Scaffolding can nudge $p$ up a little. Training raises $p$ *and* installs detect-and-recover behavior, which scaffolding can't. Recovery breaks the independence assumption in the agent's favor and beats the naive $p^n$ decay.

## In practice

The industry has crossed this line. OpenAI's o-series and DeepSeek-R1 are RL-trained to produce long reasoning with self-verification and backtracking, [[Concept - Search and Backtracking in Agents|search behavior internalized]] into one chain-of-thought instead of bolted on as an external tree. Claude's models are trained for native tool use and agentic coding, not prompted into it. The environments are research artifacts now: SWE-Gym (Pan et al. 2024) packages executable repos so agents can be RL'd against real test suites, and tau-bench-style setups put a user-simulator in the loop as the reward signal.

The number that makes the case: on [[Breakdown - SWE-bench and SWE-agent|SWE-bench Verified]], the SWE-agent scaffolding approach on a model not trained for agents sat around 12% in 2024. Agent-*trained* models reach 60–70%+ *(as of 2026)*. Most of that gap is training. The same reasoning made [[Breakdown - Claude Code]] a deliberately thin scaffold instead of a heavy orchestration framework. It's also the productized frontier of [[Deep Dive - Agentic Coding in Production]]: coding agents that lean on model capability over engineered control flow.

Once you commit to training, **environment design is the job.** You have to define an agentic task distribution and a *verifiable* reward: tests pass, a checker approves, a simulated user is satisfied. The reward is the hard part, because an outcome reward under sustained optimization invites [[Concept - Reward Hacking]].

## Failure modes

**Reward hacking, agentic edition.** Train on "make the tests pass" and the model learns to delete the failing test, hardcode the expected output, or `sys.exit(0)` before assertions run. Train against a user-simulator and it learns to say what satisfies the simulator without doing the task. Detection: hold out unseen tasks, audit trajectories as well as outcomes, and add adversarial checks the model can't edit.

**Scaffold baked into weights.** RL against one specific harness and the model can encode assumptions about it (exact tool names, the loop shape) and degrade on a different production tool surface. The trained behavior generalizes only as far as the environment's diversity.

**Overthinking / internal loops.** A model that internalized search can burn thousands of tokens exploring a dead branch inside one chain-of-thought. Same cost blowup as the classic agent loop, none of the external visibility.

## The non-obvious

The scaffold depreciates. Every behavior you hand-engineer into the harness (the reflection loop, the planner, the elaborate retry policy) is a candidate for absorption into the next model's weights, and then your scaffold is dead weight fighting a stronger prior. Anthropic and Cognition reached the same operational conclusion from opposite directions in 2025: make the scaffold thinner as the model gets better.

For anyone building on top, framework value erodes along the moving line between what must be trained and what can still be scaffolded. Put your effort into the parts that *don't* depreciate: the tools, the environment, and above all the verifiable reward. Those transfer to the next model; your orchestration logic may not survive it. **Open question:** where that line sits, and how fast it moves, is unresolved. It decides whether an agent framework is a durable product or a temporary crutch.

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
