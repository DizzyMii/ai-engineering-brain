---
tags: [moc, domain/agents, level/surface]
aliases: []
summary: "Map of the Agents domain: the control loop, tool use, planning, memory, multi-agent orchestration, and failure modes of autonomous LLMs."
---

# MOC - Agents

This domain covers what turns a language model from a text-completion engine into a system that acts: the control loop that lets a model pick its own next step, the tool-calling interface that lets it touch the outside world, and the planning, memory and multi-agent machinery you need once a task outgrows a single turn. Agents fail differently from chat models. Errors compound multiplicatively over long horizons, tool access turns a hallucination into a real side effect, and private-data access plus untrusted content plus an exfiltration channel (the Lethal Trifecta) turns a helpful agent into a data breach. The notes run from the bare definition of an agent, through the ReAct loop and the tool schemas every framework wraps, into the harder problems (context rot over long runs, when several agents beat one, sandboxing before granting real access), and out to the frontier question of whether agents should be prompted or trained. Read this domain before shipping anything that calls a tool without a human in the loop.

## Start here

- **Surface** → [[Concept - What Is an LLM Agent]] — the definition everything else assumes: an agent directs its own control flow and tool use; a workflow is code that directs the LLM.
- **Core** → [[Deep Dive - The Agent Loop]] — the full act → observe → repeat walkthrough. Every framework, from a 65-line script to a heavyweight orchestrator, is a variation on it.
- **Advanced** → [[Concept - Context Engineering for Agents]] — keeping a long-running agent's context window usable once you need compaction, offload and sub-agent isolation.
- **Frontier** → [[Concept - Trained vs Prompted Agents]] — the current research edge: RL-training the model itself for tool use and recovery instead of steering a frozen model with scaffolding.
- **Unicorn** → [[Lore - The Devin Demo and the SWE-bench Reality Gap]] — the cautionary tale of a polished agent demo versus a reliable one. Read it before trusting any agent benchmark claim.

## Foundations

- [[Concept - What Is an LLM Agent]] — the core distinction: an agent is an LLM that dynamically directs its own control flow and tool use, not code that scripts it.
- [[Deep Dive - The Agent Loop]] — the model emits an action, the harness executes it, the observation comes back, repeat until a stop condition. The shape under every agent framework.
- [[Concept - The ReAct Pattern]] — interleaving Thought/Action/Observation in one generation stream keeps reasoning grounded in real tool feedback so it doesn't drift into hallucination.
- [[Reference - Agent Framework Landscape]] — lookup matrix of the major 2026 frameworks by control paradigm, multi-agent support, persistence, and lock-in.

## Tool use and function calling

- [[Concept - Tool Use and Function Calling]] — schemas define the interface, the model emits structured calls, the harness executes and returns results. The mechanism under every "agent."
- [[Snippet - A Minimal ReAct Loop]] — a complete ~65-line tool-use agent with schemas, dispatch, id matching, error handling and the stop condition. No framework required.
- [[Playbook - Building a Tool-Use Agent from Scratch]] — building a tool-use agent directly on a provider API, from tool schemas to a hardened loop.
- [[Checklist - Agent Tool Definition Review]] — pre-flight review for any tool exposed to an agent: naming, description, parameters, returns, errors, and safety gating.
- [[Gotchas - Tool Use and Function Calling]] — malformed args, tool-selection degradation, id mismatches, ordering bugs, oversized results, and injection via tool output.

## Protocols and interop

- [[Concept - Model Context Protocol (MCP)]] — the open JSON-RPC protocol that standardizes how apps expose tools, data and prompts to LLMs, collapsing M×N integrations to M+N.
- [[Snippet - Building an MCP Server]] — a minimal runnable MCP server exposing one Tool and one Resource over stdio with the official Python SDK's FastMCP.

## Planning, reasoning, and reliability

- [[Concept - Task Decomposition and Planning]] — plan-then-execute versus interleaved decision-making, and the named methods agents use to break a goal into ordered subtasks.
- [[Concept - Reflection and Self-Correction]] — self-critique makes agents more reliable only when it's grounded in an external signal. Pure introspection doesn't cut it.
- [[Concept - Search and Backtracking in Agents]] — explicit tree search over trajectories (Tree of Thoughts, LATS), and why most production agents stay greedy and never backtrack.
- [[Concept - Long-Horizon Agency and Error Compounding]] — why long runs fail more often: per-step error compounds as p^n, and only detection-and-recovery beats the exponent.
- [[Concept - Trained vs Prompted Agents]] — the move from steering a frozen model with prompt scaffolding to RL-training the model itself for tool use, recovery and long horizons.

## Memory and context management

- [[Concept - Agent Memory Systems]] — how agents keep state past the context window: episodic/semantic/procedural stores, scored retrieval, and the hard write-policy problem.
- [[Concept - Context Engineering for Agents]] — managing what sits in the context window over a long run: compaction, offload, sub-agent isolation, cache-friendly layout.

## Multi-agent systems

- [[Concept - Multi-Agent Orchestration]] — coordinating several LLM agents through topology and message-passing buys parallelism and context isolation at a steep token-cost multiplier.
- [[Pattern - Orchestrator-Worker Agents]] — a lead agent decomposes an open-ended task at runtime, spawns isolated-context worker subagents, and synthesizes their findings.
- [[Decision - Single-Agent vs Multi-Agent]] — default to one agent with strong context engineering; split only once parallelism gains are proven against the token-cost multiplier.
- [[Breakdown - Anthropic's Multi-Agent Research System]] — an orchestrator plus parallel Claude subagents with isolated context beat a single agent by ~90% at roughly 15x the token cost.

## Workflow patterns and framework choice

- [[Pattern - Agentic Workflow Building Blocks]] — Anthropic's five composable orchestration patterns (chaining, routing, parallelization, evaluator-optimizer), which handle most tasks short of a full autonomous agent.
- [[Decision - Choosing an Agent Framework]] — picking between the raw provider SDK and the major agent frameworks in 2026, and why raw SDK is the correct default.

## Computer use

- [[Concept - Computer Use and GUI Grounding]] — agents that read screenshots and emit clicks and keystrokes to drive a real GUI. The bottleneck is mapping pixels to the correct coordinate.

## Production, safety, and security

- [[Gotchas - Agents in Production]] — production failure modes ordered by pain: injection exfiltration, infinite loops, cost/context blowups, silent tool failures.
- [[Checklist - Sandboxing an Agent]] — hardening before an agent gets real tool access: isolation, egress allowlisting, least privilege, approval gates, audit, kill switch.
- [[Concept - The Lethal Trifecta for Agents]] — private-data access plus untrusted content plus an exfiltration channel equals a data breach, and how to break a leg of the triangle.

## Evaluation and benchmarks

- [[Concept - Agent Evaluation Challenges]] — why agents are harder to score than single turns: trajectories, non-determinism, cost and attribution all break single-number scores.
- [[Reference - Agent Benchmarks]] — lookup matrix of agent capability benchmarks across coding, web, general-assistant, tool-use and computer-use, with approximate SOTA as of 2026.
- [[Breakdown - SWE-bench and SWE-agent]] — how SWE-bench grades coding agents on real GitHub issues, and how SWE-agent's interface design beat naive tool use.

## Real systems

- [[Breakdown - Claude Code]] — Anthropic's terminal coding agent: one main loop, a curated tool set, grep-not-embeddings code search, and a deliberately thin scaffold.

## Folklore and history

- [[Lore - The AutoGPT Explosion]] — the spring-2023 AutoGPT/BabyAGI mania, and why the first autonomous-agent wave failed: per-step reliability too low for the horizon it attempted.
- [[Lore - The Devin Demo and the SWE-bench Reality Gap]] — Cognition's 2024 Devin launch, its 13.86% SWE-bench claim, and the teardown that separated the polished demo from real-world reliability.
- [[Lore - Agent Prompt-Engineering Folklore]] — agent prompting tricks sorted into mechanism versus cargo cult: recitation, error-as-observation, tool_choice forcing, the reflection tax.

## Adjacent domains

- [[MOC - Prompting & Context]] — context engineering and prompt formatting are the base every agent loop runs on; this domain's context-rot and compaction problems start there.
- [[MOC - Retrieval & RAG]] — agentic retrieval and tool-based search are one problem seen from two domains; multi-step retrieval is a special case of the agent loop.
- [[MOC - Evaluation]] — general eval methodology (metrics, judges, statistical power) that agent evaluation's trajectory and non-determinism problems build on.
- [[MOC - AI in Software Engineering]] — Claude Code and SWE-bench are this domain's concrete, high-stakes proving ground; coding agents are the applied test case for everything here.
