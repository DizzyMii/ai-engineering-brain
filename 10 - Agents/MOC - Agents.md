---
tags: [moc, domain/agents, level/surface]
aliases: []
summary: "Map of the Agents domain: the control loop, tool use, planning, memory, multi-agent orchestration, and failure modes of autonomous LLMs."
---

# MOC - Agents

This domain owns everything that turns a language model from a text-completion engine into a system that acts: the control loop that lets a model decide its own next step, the tool-calling interface that lets it touch the outside world, and the planning, memory, and multi-agent machinery needed once a task outgrows a single turn. It matters because agents fail differently than chat models — errors compound multiplicatively across long horizons, tool access turns a hallucination into a real side effect, and the combination of private-data access, untrusted content, and an exfiltration channel (the Lethal Trifecta) turns a helpful agent into a data breach. The notes here run from the bare definition of an agent through the ReAct loop and tool schemas every framework wraps, into the harder advanced problems — context rot over long runs, when multiple agents beat one, sandboxing before granting real access — and out to the frontier question of whether agents should be prompted or trained for the job. Read this domain before shipping anything that calls a tool without a human in the loop.

## Start here

- **Surface** → [[Concept - What Is an LLM Agent]] — the definition everything else assumes: an agent directs its own control flow and tool use; a workflow is code that directs the LLM.
- **Core** → [[Deep Dive - The Agent Loop]] — the full walkthrough of act → observe → repeat that every framework, from a 65-line script to a heavyweight orchestrator, is a variation on.
- **Advanced** → [[Concept - Context Engineering for Agents]] — keeping a long-running agent's context window usable once compaction, offload, and sub-agent isolation become necessary.
- **Frontier** → [[Concept - Trained vs Prompted Agents]] — the current research edge: RL-training the model itself for tool use and recovery instead of steering a frozen model with scaffolding.
- **Unicorn** → [[Lore - The Devin Demo and the SWE-bench Reality Gap]] — the cautionary tale that separates a polished agent demo from a reliable one; read before trusting any agent benchmark claim.

## Foundations

- [[Concept - What Is an LLM Agent]] — the load-bearing distinction: an agent is an LLM that dynamically directs its own control flow and tool use, not code that scripts it.
- [[Deep Dive - The Agent Loop]] — model emits an action, the harness executes it, the observation returns, repeat until a stop condition — the shape under every agent framework.
- [[Concept - The ReAct Pattern]] — interleaving Thought/Action/Observation in one generation stream keeps reasoning grounded in real tool feedback instead of drifting into hallucination.
- [[Reference - Agent Framework Landscape]] — lookup matrix of the major 2026 frameworks by control paradigm, multi-agent support, persistence, and lock-in.

## Tool use and function calling

- [[Concept - Tool Use and Function Calling]] — schemas define the interface, the model emits structured calls, the harness executes and returns results — the mechanism under every "agent."
- [[Snippet - A Minimal ReAct Loop]] — a complete ~65-line tool-use agent: schemas, dispatch, id matching, error handling, and the stop condition, no framework required.
- [[Playbook - Building a Tool-Use Agent from Scratch]] — the end-to-end procedure for building a tool-use agent directly on a provider API, from tool schemas to a hardened loop.
- [[Checklist - Agent Tool Definition Review]] — pre-flight review for any tool exposed to an agent: naming, description, parameters, returns, errors, and safety gating.
- [[Gotchas - Tool Use and Function Calling]] — malformed args, tool-selection degradation, id mismatches, ordering bugs, oversized results, and injection via tool output.

## Protocols and interop

- [[Concept - Model Context Protocol (MCP)]] — the open JSON-RPC protocol that standardizes how apps expose tools, data, and prompts to LLMs, collapsing M×N integrations to M+N.
- [[Snippet - Building an MCP Server]] — a minimal runnable MCP server exposing one Tool and one Resource over stdio using the official Python SDK's FastMCP.

## Planning, reasoning, and reliability

- [[Concept - Task Decomposition and Planning]] — plan-then-execute versus interleaved decision-making, and the named methods behind how agents break a goal into ordered subtasks.
- [[Concept - Reflection and Self-Correction]] — agents that critique and revise their own outputs are reliable only when the critique is grounded in an external signal, not pure introspection.
- [[Concept - Search and Backtracking in Agents]] — explicit tree search over trajectories (Tree of Thoughts, LATS) versus why most production agents stay greedy and never backtrack.
- [[Concept - Long-Horizon Agency and Error Compounding]] — why long runs fail more often: per-step error compounds as p^n, and only detection-and-recovery beats the exponent.
- [[Concept - Trained vs Prompted Agents]] — the shift from steering a frozen model with prompt scaffolding to RL-training the model itself for tool use, recovery, and long horizons.

## Memory and context management

- [[Concept - Agent Memory Systems]] — how agents persist state past the context window: episodic/semantic/procedural stores, scored retrieval, and the hard write-policy problem.
- [[Concept - Context Engineering for Agents]] — managing what actually sits in the context window across a long run: compaction, offload, sub-agent isolation, cache-friendly layout.

## Multi-agent systems

- [[Concept - Multi-Agent Orchestration]] — coordinating multiple LLM agents via topology and message-passing buys parallelism and context isolation at a steep token-cost multiplier.
- [[Pattern - Orchestrator-Worker Agents]] — a lead agent decomposes an open-ended task at runtime and spawns isolated-context worker subagents, then synthesizes their findings.
- [[Decision - Single-Agent vs Multi-Agent]] — default to single-agent with strong context engineering; split only once parallelism gains are proven against the token-cost multiplier.
- [[Breakdown - Anthropic's Multi-Agent Research System]] — orchestrator plus parallel Claude subagents with isolated context beat a single agent by ~90% at roughly 15x the token cost.

## Workflow patterns and framework choice

- [[Pattern - Agentic Workflow Building Blocks]] — Anthropic's five composable orchestration patterns (chaining, routing, parallelization, evaluator-optimizer) that solve most tasks short of a full autonomous agent.
- [[Decision - Choosing an Agent Framework]] — how to choose among the raw provider SDK and the major agent frameworks in 2026, and why raw SDK is the correct default.

## Computer use

- [[Concept - Computer Use and GUI Grounding]] — agents that perceive screenshots and emit clicks and keystrokes to drive a real GUI, bottlenecked by mapping pixels to the correct coordinate.

## Production, safety, and security

- [[Gotchas - Agents in Production]] — production failure modes ordered by pain: injection exfiltration, infinite loops, cost/context blowups, silent tool failures.
- [[Checklist - Sandboxing an Agent]] — pre-flight hardening before granting an agent real tool access: isolation, egress allowlisting, least privilege, approval gates, audit, kill switch.
- [[Concept - The Lethal Trifecta for Agents]] — private-data access plus untrusted content plus an exfiltration channel equals a data breach; how to break a leg of the triangle.

## Evaluation and benchmarks

- [[Concept - Agent Evaluation Challenges]] — why scoring agents is harder than scoring single turns: trajectories, non-determinism, cost, and attribution break single-number scores.
- [[Reference - Agent Benchmarks]] — lookup matrix of agent capability benchmarks across coding, web, general-assistant, tool-use, and computer-use, with approximate SOTA as of 2026.
- [[Breakdown - SWE-bench and SWE-agent]] — how SWE-bench grades coding agents on real GitHub issues, and how SWE-agent's interface design beat naive tool use.

## Real systems

- [[Breakdown - Claude Code]] — Anthropic's terminal coding agent: one main loop, a curated tool set, grep-not-embeddings code search, and a deliberately thin scaffold.

## Folklore and history

- [[Lore - The AutoGPT Explosion]] — the spring-2023 AutoGPT/BabyAGI mania, and why the first autonomous-agent wave failed: per-step reliability too low for the horizon it attempted.
- [[Lore - The Devin Demo and the SWE-bench Reality Gap]] — Cognition's 2024 Devin launch, its 13.86% SWE-bench claim, and the teardown that split the polished demo from real-world reliability.
- [[Lore - Agent Prompt-Engineering Folklore]] — agent prompting tricks sorted into mechanism versus cargo cult: recitation, error-as-observation, tool_choice forcing, the reflection tax.

## Adjacent domains

- [[MOC - Prompting & Context]] — context engineering and prompt formatting are the substrate every agent loop runs on; this domain's context-rot and compaction problems start there.
- [[MOC - Retrieval & RAG]] — agentic retrieval and tool-based search are the same problem viewed from opposite domains; multi-step retrieval is a special case of the agent loop.
- [[MOC - Evaluation]] — general eval methodology (metrics, judges, statistical power) that agent evaluation's trajectory and non-determinism problems build on top of.
- [[MOC - AI in Software Engineering]] — Claude Code and SWE-bench are this domain's concrete, high-stakes proving ground: coding agents are the applied test case for everything here.
