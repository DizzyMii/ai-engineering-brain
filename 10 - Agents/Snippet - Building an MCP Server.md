---
tags: [snippet, domain/agents, level/advanced]
aliases: [FastMCP example, MCP server example]
summary: "A minimal runnable MCP server exposing one Tool and one Resource over stdio using the official Python SDK's FastMCP."
---
# Snippet - Building an MCP Server

**What it does:** a minimal [[Concept - Model Context Protocol (MCP)|MCP]] server exposing one Tool (`get_forecast`, a model-controlled action) and one Resource (`weather://stations`, application-controlled data) over the stdio transport, using the official Python SDK's `FastMCP` interface. **Dependencies:** `mcp>=1.2.0` (`pip install "mcp[cli]"`), Python 3.10+. **Expected output:** a connected MCP client (e.g. Claude Desktop, or `mcp dev mcp_server.py` for the SDK's inspector) lists one tool and one resource; calling `get_forecast("94103")` returns a plain-text forecast string; reading the resource returns a static station list.

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

- **Typed signatures instead of a hand-written schema.** `zip_code: str` is enough for FastMCP to derive the JSON Schema the model sees — the same schema-generation contract that underlies [[Concept - Tool Use and Function Calling]] generally, and the same [[Concept - Constrained Decoding|grammar-constrained decoding]] on the model side that guarantees the emitted call actually matches it, just automated on the definition side. Hand-writing the schema separately from the function is exactly the drift risk this avoids.
- **The docstring is the model-facing contract, not a comment.** Everything the model knows about `get_forecast` — when to call it, when not to, what the ZIP format is — comes from that docstring; there is no source code the model reads to disambiguate a vague one. This is the single highest-leverage line in the file, and the same discipline [[Checklist - Agent Tool Definition Review]] demands of any tool definition, MCP or not.
- **A Tool and a Resource side by side, deliberately.** `get_forecast` is model-controlled (the LLM decides when to call it); `weather://stations` is application-controlled data the host can pull into context without the model asking. Conflating the two — making everything a "tool" — loses the distinction MCP's primitive set is built around.
- **Errors return a string, not a raised exception.** An unhandled exception in a tool handler either crashes the server process or surfaces as an opaque error to the model; returning a plain-text explanation lets the model self-correct (try a supported ZIP) on the next turn instead of stalling.
- **No tracing in this minimal example.** Production MCP servers should emit a trace span per tool call for [[Concept - LLM Observability and Tracing|observability]]; this file omits it to keep the core mechanics visible.
- **stdio, not Streamable HTTP.** stdio is the right transport for a local dev server launched as a subprocess by the host; swapping `transport="stdio"` for `transport="streamable-http"` is the only change needed to serve this remotely to multiple concurrent clients. And this snippet stays deliberately unsandboxed and framework-minimal — see [[Checklist - Sandboxing an Agent]] before granting a server like this real filesystem or network-capable tools, and note that a third-party version of this same file would make its docstrings attacker-controlled text the calling agent trusts by default, the MCP-specific instance of [[Concept - The Lethal Trifecta for Agents]].

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
