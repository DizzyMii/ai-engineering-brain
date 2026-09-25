---
tags: [snippet, domain/agents, level/advanced]
aliases: [FastMCP example, MCP server example]
summary: "A minimal runnable MCP server exposing one Tool and one Resource over stdio using the official Python SDK's FastMCP."
---
# Snippet - Building an MCP Server

**What it does:** a minimal [[Concept - Model Context Protocol (MCP)|MCP]] server exposing one Tool (`get_forecast`, a model-controlled action) and one Resource (`weather://stations`, application-controlled data) over the stdio transport, using the official Python SDK's `FastMCP` interface. **Dependencies:** `mcp>=1.2.0` (`pip install "mcp[cli]"`), Python 3.10+. **Expected output:** a connected MCP client (e.g. Claude Desktop, or `mcp dev mcp_server.py` for the SDK's inspector) lists one tool and one resource. Calling `get_forecast("94103")` returns a plain-text forecast string, and reading the resource returns a static station list.

```python
"""
Minimal MCP server: one Tool (model-controlled action) and one Resource
(application-controlled data), served over stdio.

Run directly:      python mcp_server.py
Inspect it live:    mcp dev mcp_server.py
Register in a host (e.g. Claude Desktop's claude_desktop_config.json):
    "weather-demo": { "command": "python", "args": ["/abs/path/mcp_server.py"] }
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-demo")

# Stand-in for a real upstream API call.
_FORECASTS = {
    "94103": "San Francisco: 62F, fog clearing by 11am",
    "10001": "New York: 71F, clear",
}
_STATIONS = ["94103 - SF Downtown", "10001 - NYC Midtown"]


@mcp.tool()
def get_forecast(zip_code: str) -> str:
    """Get today's weather forecast for a US ZIP code.

    Use this when the user asks about current or today's weather for a
    specific US location. Do NOT use this for multi-day forecasts or
    non-US locations (not supported by this server).

    Args:
        zip_code: 5-digit US ZIP code, e.g. "94103".
    """
    forecast = _FORECASTS.get(zip_code)
    if forecast is None:
        # Model-readable guidance, not a stack trace: tells the model what
        # to try next instead of just failing.
        return f"No forecast for ZIP {zip_code}. Supported ZIPs: {list(_FORECASTS)}."
    return forecast


@mcp.resource("weather://stations")
def list_stations() -> str:
    """Static list of weather stations this server knows about."""
    return "\n".join(_STATIONS)


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

## Why it's written this way

- **Typed signatures, no hand-written schema.** `zip_code: str` is enough for FastMCP to derive the JSON Schema the model sees. It's the same schema contract behind [[Concept - Tool Use and Function Calling]] in general, and on the model side [[Concept - Constrained Decoding|grammar-constrained decoding]] guarantees the emitted call matches it. FastMCP just automates the definition side. Writing the schema separately from the function invites drift, which this avoids.
- **The docstring is the model-facing contract.** Everything the model knows about `get_forecast` (when to call it, when not to, the ZIP format) comes from that docstring. The model never reads source code to resolve a vague description. It's the most important text in the file, and [[Checklist - Agent Tool Definition Review]] asks the same of any tool definition, MCP or not.
- **A Tool and a Resource side by side, on purpose.** `get_forecast` is model-controlled: the LLM decides when to call it. `weather://stations` is application-controlled data the host can pull into context without the model asking. Making everything a "tool" throws away the distinction MCP's primitive set is built on.
- **Errors return a string.** An unhandled exception in a tool handler either crashes the server process or reaches the model as an opaque error. A plain-text explanation lets the model self-correct next turn (try a supported ZIP) instead of stalling.
- **No tracing in this minimal example.** Production MCP servers should emit a trace span per tool call for [[Concept - LLM Observability and Tracing|observability]]; it's left out here to keep the core mechanics visible.
- **stdio, not Streamable HTTP.** stdio suits a local dev server the host launches as a subprocess. To serve this remotely to multiple concurrent clients, swap `transport="stdio"` for `transport="streamable-http"`; nothing else changes. The snippet is also deliberately unsandboxed and framework-minimal. Read [[Checklist - Sandboxing an Agent]] before giving a server like this real filesystem or network-capable tools. And if someone else wrote this file, its docstrings would be attacker-controlled text the calling agent trusts by default: the MCP-specific case of [[Concept - The Lethal Trifecta for Agents]].

## Connections

- [[Concept - Model Context Protocol (MCP)]] — the client/server architecture, primitive set, and transport choices this snippet implements a minimal instance of.
- [[Concept - Tool Use and Function Calling]] — the underlying schema-in/structured-call-out mechanics that FastMCP's typed-signature derivation automates.
- [[Checklist - Agent Tool Definition Review]] — the review discipline the docstring in this file needs to pass before shipping.
- [[Checklist - Sandboxing an Agent]] — this snippet has no isolation of its own; a server like this granted real filesystem or network tools needs that checklist applied around it.
- [[Concept - The Lethal Trifecta for Agents]] — if this server were third-party, its tool descriptions would be attacker-controlled text the calling agent trusts by default.
- [[Concept - Constrained Decoding]] — the decoder-side mechanism that guarantees the model's call actually matches the JSON Schema this file generates.
- [[Concept - LLM Observability and Tracing]] — production MCP servers should emit a trace span per tool call; this minimal example deliberately omits it to keep the mechanics visible.

## Sources

- Model Context Protocol Python SDK documentation — `FastMCP` tool/resource registration and typed-signature schema derivation.
- Anthropic (Nov 2024) — "Introducing the Model Context Protocol." The primitive set (Tools/Resources/Prompts) this snippet demonstrates two of.
