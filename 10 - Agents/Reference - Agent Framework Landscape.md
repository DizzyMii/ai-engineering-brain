---
tags: [reference, domain/agents, level/surface]
aliases: [agent SDK comparison, agent framework comparison]
summary: "Lookup matrix of the major agent frameworks as of 2026: control paradigm, multi-agent support, persistence, and lock-in."
---
*(as of 2026. This table churns quarterly; verify current framework names/APIs before betting a production stack on any row.)*

## Framework matrix

| Framework | Control paradigm | Multi-agent | Streaming | Human-in-the-loop | State/checkpoint persistence | Provider lock-in | Language | Best-fit use case |
|---|---|---|---|---|---|---|---|---|
| LangGraph | Explicit graph/state machine | Yes (subgraphs, supervisor patterns) | Yes | Native interrupt/resume | Durable, built-in checkpointing | None (any model provider) | Python, JS | Long-running or resumable workflows needing explicit branching and replay |
| OpenAI Agents SDK | Agent loop + handoffs (Swarm successor) | Yes (handoff/transfer semantics) | Yes | Guardrail hooks | Session-based, lighter-weight | OpenAI-leaning | Python, JS | Provider-native multi-agent handoffs with minimal ceremony |
| Anthropic Claude Agent SDK | Agent loop, native tool use + extended thinking | Via subagents | Yes | Permission/approval hooks | Session-based | Anthropic-leaning | Python, TS | Building on Claude's native agentic loop (same substrate as Claude Code) |
| CrewAI | Role-based "crews" of agents with tasks | Yes, core abstraction | Partial | Limited | Basic | None | Python | Quick-to-stand-up role-play multi-agent teams |
| AutoGen / AG2 | Conversational multi-agent (agents message each other) | Yes, core abstraction | Partial | Yes (human proxy agent) | Basic | None | Python | Research-style multi-agent conversation and debate patterns |
| LlamaIndex Workflows | Event-driven steps over a graph | Yes | Yes | Yes | Yes | None | Python, TS | Event-driven pipelines, esp. RAG-heavy agents |
| Hugging Face smolagents | Code-as-action (model emits Python, not JSON) | Limited | Partial | Limited | Basic | None | Python | Minimal-overhead agents where code actions beat JSON tool calls |
| Pydantic AI | Typed agent with schema-validated outputs | Limited | Yes | Yes | Basic | None | Python | Type-safe structured output as the primary contract |
| DSPy | Declarative program + compiler/optimizer (not a runtime loop) | N/A (orthogonal) | N/A | N/A | N/A | None | Python | Optimizing prompts/weights of modules that other frameworks then run |
| Google ADK | Agent Development Kit, graph + multi-agent | Yes | Yes | Yes | Yes | Google-leaning | Python, Java | Google-ecosystem-native agent deployment (Vertex AI) |
| Raw provider SDK (no framework) | Whatever you write | Manual | Manual | Manual | Manual | Tied to chosen provider | Any | A single tool-use loop with 1-3 tools (see the note below) |

## Code-as-action vs JSON tool calls

Most rows above have the model emit one JSON tool call per action (see [[Concept - Tool Use and Function Calling]]), which the harness parses and executes. smolagents and the broader CodeAct line have the model emit a Python snippet that runs directly, so one action can chain several operations (call a tool, inspect the result, call another) without a model round-trip per step. That cuts latency and token overhead for multi-step actions. It also means running arbitrary generated code, so a real sandbox is mandatory (see [[Checklist - Sandboxing an Agent]]).

## DSPy is orthogonal

DSPy doesn't compete with the other rows on control paradigm because it isn't a runtime loop. It's a compiler that optimizes the prompts (or weights) of the modules inside an agent program. You can wrap a LangGraph node, a CrewAI task, or a raw tool-use loop in a DSPy module and let it tune that module's prompt against a metric. DSPy answers "what should the prompt say"; the other frameworks answer "what runs when."

## The raw-API baseline

For a single agent with one to three tools and a bounded task, a framework frequently costs more debugging time than it saves. A hand-rolled loop on the raw provider SDK (see [[Playbook - Building a Tool-Use Agent from Scratch]]) is often the correct 2026 default. Adopt a framework once a concrete need appears: explicit state/branching, durable resume, or heavy multi-agent coordination. LangGraph or Google ADK if you need durable checkpointing; the OpenAI Agents SDK or Claude Agent SDK if you want provider-native handoffs and guardrails without building them.

## Volatility warning

This table is a snapshot. In the last two years alone, OpenAI's Swarm (experimental) was superseded by the Agents SDK, the MCP transport layer moved from HTTP+SSE to Streamable HTTP in the 2025 spec revision (see [[Concept - Model Context Protocol (MCP)]]), and several frameworks aren't listed here at all, since rows come and go with real adoption. Every "best-fit" claim is date-stamped to 2026; re-verify before a production commitment. The choose-one logic, including what flips the default, lives in [[Decision - Choosing an Agent Framework]].

## Connections
- [[Concept - Tool Use and Function Calling]] — the request/response mechanics every framework in this table sits on top of, whether it's exposed as JSON tool calls or code-as-action.
- [[Decision - Choosing an Agent Framework]] — the decision flow and tradeoff matrix that this table only feeds; this note describes, that note decides.
- [[Playbook - Building a Tool-Use Agent from Scratch]] — the raw-API baseline row spelled out step by step, for when no framework is the right call.
- [[Concept - Model Context Protocol (MCP)]] — several frameworks in this table (Claude Agent SDK, ADK, LangGraph integrations) consume MCP servers as their tool source rather than defining tools natively.
- [[Checklist - Sandboxing an Agent]] — mandatory reading before adopting the code-as-action row, since executing model-generated code without isolation is a direct path to host compromise.
- [[Reference - Model Genealogy]] — framework choice is entangled with model/provider choice; this cross-domain reference tracks the model side of that coupling.
- [[Concept - Cost Engineering for LLM Applications]] — heavier frameworks (durable state, multi-agent) carry real token and infrastructure cost that belongs in the same budget conversation as framework choice.
