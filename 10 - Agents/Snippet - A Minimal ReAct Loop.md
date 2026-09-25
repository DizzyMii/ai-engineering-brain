---
tags: [snippet, domain/agents, level/core]
aliases: []
summary: "A complete ~65-line tool-use agent loop: schemas, dispatch, id matching, error handling, and the stop condition."
---

# Snippet - A Minimal ReAct Loop

**What it does:** the core mechanics of the [[Deep Dive - The Agent Loop|agent loop]] (call the model, dispatch tool calls, append results, repeat until the model stops calling tools) against two toy tools, a calculator and a stubbed web search. It pairs with [[Concept - Tool Use and Function Calling]] and the [[Playbook - Building a Tool-Use Agent from Scratch]]. Read those for the mechanism and the procedure, and this file for the ~65 lines that run.

**Dependencies:** `anthropic>=0.40` (`pip install anthropic`). Auth via `export ANTHROPIC_API_KEY=sk-ant-...`.

**Expected output:**
```text
[turn 1] tool_use: calculator({"expression": "47 * 12"})
[turn 1] tool_result: 564
[turn 2] tool_use: web_search({"query": "population of Fresno"})
[turn 2] tool_result: approximately 545,000 (stub result for 'population of Fresno')
47 * 12 is 564. Fresno's population is roughly 545,000.
```

```python
"""
Minimal ReAct-style tool-use loop against the Anthropic API.

Dependencies: anthropic>=0.40  (pip install anthropic)
Auth: export ANTHROPIC_API_KEY=sk-ant-...
"""

import json
from anthropic import Anthropic

client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
MODEL = "claude-sonnet-4-5"
MAX_ITERATIONS = 10

TOOLS = [
    {
        "name": "calculator",
        "description": (
            "Evaluate a basic arithmetic expression. Use when the user needs a "
            "numeric computation. Do not use for symbolic math or unit conversion."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "e.g. '47 * 12'"}
            },
            "required": ["expression"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web and return a short text snippet. Use for factual "
            "lookups you don't already know. Do not use for arithmetic."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "search query text"}
            },
            "required": ["query"],
        },
    },
]


def calculator(expression: str) -> str:
    try:
        # eval() is fine for a toy demo; never do this on untrusted input in prod --
        # sandbox real tool execution (see Checklist - Sandboxing an Agent).
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"error: could not evaluate '{expression}': {e}"


def web_search(query: str) -> str:
    # Stub. A real implementation calls a search API and returns real snippets.
    return f"approximately 545,000 (stub result for '{query}')"


HANDLERS = {"calculator": calculator, "web_search": web_search}


def run_agent(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    for turn in range(1, MAX_ITERATIONS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if not tool_calls:
            # No tool_use block this turn -> the model is done.
            return next(b.text for b in response.content if b.type == "text")

        tool_results = []
        for call in tool_calls:
            handler = HANDLERS.get(call.name)
            try:
                result = (
                    handler(**call.input)
                    if handler
                    else f"error: unknown tool '{call.name}'"
                )
            except Exception as e:
                result = f"error: {e}"
            print(f"[turn {turn}] tool_use: {call.name}({json.dumps(call.input)})")
            print(f"[turn {turn}] tool_result: {result}")
            tool_results.append(
                {"type": "tool_result", "tool_use_id": call.id, "content": str(result)}
            )
        messages.append({"role": "user", "content": tool_results})

    return "error: hit max_iterations without a final answer"


if __name__ == "__main__":
    print(run_agent("What's 47 * 12, and roughly what's the population of Fresno?"))
```

## Why it's written this way

- **Id matching is required.** Every `tool_result` carries `tool_use_id=call.id`. Get it wrong (say, zip results to calls by position instead of by id) and the Anthropic API rejects the next turn outright, or a more permissive provider silently attaches the wrong result to the wrong call. [[Concept - Tool Use and Function Calling]] explains why the harness, not the model, owns this bookkeeping.
- **Errors become tool-result text, never exceptions.** `calculator` and the dispatch loop both catch and stringify failures. A raised exception kills the whole run; an error string lets the model read the failure and retry with corrected arguments. That's how in-loop self-correction works at all.
- **`MAX_ITERATIONS` is a hard circuit breaker.** Without it, a model rationalizing a failing calculator call (see [[Gotchas - Tool Use and Function Calling]]) burns tokens indefinitely. Ten iterations is generous for a two-tool task; production agents tune this to the task's real expected step count.
- **The stop condition checks content type.** The loop exits when a turn contains no `tool_use` blocks. It doesn't scan generated text for a phrase like "I'm done," because text-based stop detection is the brittle-parsing failure that native tool calling replaced (see [[Concept - The ReAct Pattern]] on the original text-parsed implementation).

## Connections
- [[Deep Dive - The Agent Loop]] -- the full theory (termination logic, context accumulation, evolution) this snippet is the minimal runnable instance of.
- [[Concept - Tool Use and Function Calling]] -- the schema/id/`tool_choice` mechanics this code implements directly.
- [[Concept - The ReAct Pattern]] -- the thought-action-observation lineage this loop descends from, now with native calls instead of parsed text.
- [[Playbook - Building a Tool-Use Agent from Scratch]] -- the step-by-step procedure this snippet is the worked answer to.
- [[Gotchas - Tool Use and Function Calling]] -- the failure catalog (malformed args, id mismatches, loops) each design decision above defends against.
- [[Concept - Constrained Decoding]] -- the decoder-level mechanism that makes `call.input` reliably schema-valid JSON in the first place.
- [[Playbook - Reliable Structured Output]] -- the general technique this snippet specializes for the tool-call case.
- [[Concept - What Is an LLM Agent]] -- the baseline anatomy (model + tools + loop + termination) this file is a literal implementation of.

## Sources
- Yao et al. (2022) -- "ReAct: Synergizing Reasoning and Acting in Language Models." The origin of the thought-action-observation loop this snippet implements with native tool calls instead of parsed `Action:` text lines.
