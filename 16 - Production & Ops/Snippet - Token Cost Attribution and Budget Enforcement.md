---
tags: [snippet, domain/production-ops, level/advanced]
aliases: []
summary: "Runnable snippet: count tokens, price a call by exact model id, and atomically enforce a per-tenant LLM budget in Redis."
---
# Snippet - Token Cost Attribution and Budget Enforcement

> **What it does:** wraps a model call with (1) a pre-flight cost reservation checked atomically against a per-tenant monthly budget, (2) authoritative post-call cost computed from the provider's own usage object, and (3) attribution metadata suitable for OTel span attributes / cost-dashboard labels. **Dependencies:** `redis` 5.x (redis-py, sync client, talking to Redis 6+ for `INCRBYFLOAT` + Lua scripting), `tiktoken` 0.7+ (pre-flight estimate only — never for billing). **Expected output:** a rejected call prints `tenant=acme call blocked: budget exhausted ($0.11 remaining, need $0.34)`; an accepted call prints `tenant=acme real_cost=$0.0184` after reconciliation.

This assumes the theory in [[Concept - Cost Engineering for LLM Applications]] and the atomic-limit pattern from [[Concept - Rate Limiting and Quota Design]]; this snippet is the concrete implementation of both for the cost axis specifically. It's the kind of enforcement layer a gateway product like [[Breakdown - LiteLLM]] ships built-in — worth reading if you'd rather not run this yourself — but the mechanics are the same either way.

```python
"""
Token cost attribution + atomic per-tenant budget enforcement for LLM calls.
"""
import time
import tiktoken
import redis

# --- Pricing map: keyed by the EXACT dated model snapshot id, never a floating
# alias (see the "why" section — this is the single most common cost bug). ---
# All figures are $ per token, converted from the usual $/1M quotes, and the
# cached-input column applies the ~90% cached-input discount from prompt caching.
PRICING = {
    "gpt-4o-2024-08-06":        {"in": 2.50e-6, "out": 10.00e-6, "cached_in": 0.25e-6},
    "claude-sonnet-4-20250514": {"in": 3.00e-6, "out": 15.00e-6, "cached_in": 0.30e-6},
    "gpt-4o-mini-2024-07-18":   {"in": 0.15e-6, "out": 0.60e-6,  "cached_in": 0.015e-6},
}

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Atomic reserve-and-check as a single Lua script (runs server-side, atomically)
# so N concurrent replicas can't all read "under budget" and all commit at once.
_RESERVE_LUA = r.register_script("""
local key = KEYS[1]
local reserve = tonumber(ARGV[1])
local cap = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local spent = tonumber(redis.call('GET', key) or '0')
if spent + reserve > cap then
    return {0, tostring(cap - spent)}   -- rejected: {ok=0, remaining}
end
local new_total = redis.call('INCRBYFLOAT', key, reserve)
redis.call('EXPIRE', key, ttl)
return {1, tostring(new_total)}         -- accepted: {ok=1, running_total}
""")


class BudgetExceededError(RuntimeError):
    pass


def estimate_cost(model: str, input_text: str, max_tokens: int) -> float:
    """Pre-flight estimate ONLY, used to size the reservation before the call.
    tiktoken approximates non-OpenAI tokenizers (e.g. Claude's), so treat this
    as a conservative upper bound, not a billing figure."""
    enc = tiktoken.get_encoding("cl100k_base")
    input_tokens = len(enc.encode(input_text))
    p = PRICING[model]
    return input_tokens * p["in"] + max_tokens * p["out"]


def actual_cost(model: str, usage: dict) -> float:
    """Authoritative cost from the provider-returned usage object — this, not
    the tokenizer estimate, is what you bill and put on a dashboard."""
    p = PRICING[model]
    cached = usage.get("cached_tokens", 0)
    billable_in = usage["input_tokens"] - cached
    return billable_in * p["in"] + cached * p["cached_in"] + usage["output_tokens"] * p["out"]


def reserve_budget(tenant: str, month: str, amount: float, monthly_cap: float) -> tuple[bool, float]:
    key = f"budget:{tenant}:{month}"
    ttl = 40 * 24 * 3600  # outlive the calendar month; cheap insurance against clock skew
    ok, remaining = _RESERVE_LUA(keys=[key], args=[amount, monthly_cap, ttl])
    return bool(int(ok)), float(remaining)


def reconcile_budget(tenant: str, month: str, reserved: float, actual: float) -> None:
    """Reservations are sized to max_tokens (a worst case); true up the delta so
    a chatty prompt with a short answer doesn't permanently eat its reservation."""
    delta = actual - reserved
    if delta != 0:
        r.incrbyfloat(f"budget:{tenant}:{month}", delta)


def call_with_budget(tenant: str, model: str, prompt: str, max_tokens: int,
                      monthly_cap: float, metadata: dict) -> dict:
    month = time.strftime("%Y-%m")
    reserved = estimate_cost(model, prompt, max_tokens)
    ok, remaining = reserve_budget(tenant, month, reserved, monthly_cap)
    if not ok:
        raise BudgetExceededError(
            f"tenant={tenant} call blocked: budget exhausted "
            f"(${remaining:.2f} remaining, need ${reserved:.2f})"
        )

    response = call_provider(model, prompt, max_tokens)  # your SDK call goes here

    real = actual_cost(model, response["usage"])
    reconcile_budget(tenant, month, reserved, real)

    span_attrs = {
        "gen_ai.request.model": model,
        "gen_ai.usage.input_tokens": response["usage"]["input_tokens"],
        "gen_ai.usage.output_tokens": response["usage"]["output_tokens"],
        "cost.usd": real,
        **metadata,  # tenant, user, feature, trace_id
    }
    print(f"tenant={tenant} real_cost=${real:.4f}")
    return {"response": response, "cost_usd": real, "span_attrs": span_attrs}


def call_provider(model: str, prompt: str, max_tokens: int) -> dict:
    """Stand-in for openai.chat.completions.create(...) / anthropic.messages.create(...)."""
    return {"text": "...", "usage": {"input_tokens": 812, "output_tokens": 340, "cached_tokens": 0}}


if __name__ == "__main__":
    meta = {"tenant": "acme", "user": "u_123", "feature": "chat", "trace_id": "tr_9f"}
    call_with_budget("acme", "gpt-4o-2024-08-06", "explain zero-copy deserialization" * 20,
                      max_tokens=500, monthly_cap=50.00, metadata=meta)
```

## Why it's written this way

- **Bill from `usage`, estimate only pre-flight.** `tiktoken` doesn't match every provider's tokenizer — it's a close approximation for OpenAI models and a rough guess for anything else — so treating an estimate as the invoice figure silently mis-bills every non-OpenAI call. The provider's returned token counts are the only authoritative number; see [[Gotchas - LLM Production Operations]] for this exact mistake as a recurring incident.
- **One atomic Lua script, not `GET` then `INCR`.** A naive "check remaining, then increment" from application code has a race window: two concurrent requests can both read "under budget" before either writes, and both commit — the classic TOCTOU bug, and the reason [[Concept - Rate Limiting and Quota Design]] insists on an atomic op for any distributed limit. Running the check-and-increment as a single Redis-side script closes that window regardless of how many app replicas are calling it.
- **Reserve on `max_tokens`, reconcile to actual.** You don't know the true output length until generation finishes, so the only way to gate *before* the call is to reserve pessimistically against the ceiling and true up afterward. This is the same reserve-then-reconcile shape used for token-based rate limiting, applied to dollars instead of request slots.
- **Pricing keyed by the exact dated snapshot id.** `"gpt-4o"` is a floating alias that can repoint to a different-priced model without any deploy on your side (see [[Concept - Model Lifecycle and Versioning]]); keying the pricing map — and therefore every cost dashboard — on the dated id is what keeps cost attribution correct across a silent provider-side model swap.

## Connections

- [[Concept - Cost Engineering for LLM Applications]] — the cost model and levers this snippet turns into enforcement code.
- [[Concept - Rate Limiting and Quota Design]] — the same atomic-Redis-counter pattern applied to request/token throughput instead of dollars.
- [[Concept - LLM Gateways and Routing]] — where this kind of per-key budget enforcement typically lives in a production stack (as a gateway feature, not app-level code).
- [[Concept - Byte-Pair Encoding]] — the tokenization mechanism `tiktoken` implements, and why it only approximates a non-OpenAI provider's actual tokenizer.
- [[Breakdown - LiteLLM]] — a real gateway that ships a maintained pricing map and mid-flight budget enforcement equivalent to this snippet, if you'd rather not run it yourself.
- [[Concept - Prompt Caching]] — the source of the cached-input discount tier modeled separately in the pricing map.
- [[Concept - Model Routing and Cascades]] — the next lever once budget enforcement is in place: routing cheap queries to a cheaper model instead of just capping spend on the expensive one.
- [[Gotchas - LLM Production Operations]] — catalogs this exact bug (billing from a local tokenizer estimate instead of provider usage) alongside the other cost-incident patterns this snippet is designed to prevent.
- [[Concept - Model Lifecycle and Versioning]] — why the pricing map (and every join to it) has to be keyed on the dated snapshot id, not a floating alias.

## Sources
- Provider API documentation (OpenAI, Anthropic) for the `usage` object shape and dated-snapshot pricing (as of 2026, volatile — verify current figures before using in production).
