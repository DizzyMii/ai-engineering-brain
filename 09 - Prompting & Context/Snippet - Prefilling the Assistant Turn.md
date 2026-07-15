---
tags: [snippet, domain/prompting-context, level/advanced]
aliases: [assistant prefill, response prefilling, prefill attack]
summary: "Runnable Anthropic example: seeding the assistant turn forces a single enum value and skips preamble, plus the stop-sequence gotcha."
---
# Snippet - Prefilling the Assistant Turn

**What it does:** sends a partial assistant message — `{"sentiment": "` — instead of leaving the assistant turn empty, so the model *continues* the object rather than deciding from scratch whether to explain itself first. This is the concrete mechanism behind Step 2 of [[Playbook - Reliable Structured Output]]: it works because autoregressive continuation is a stronger prior on the model than an instruction telling it to "output only JSON" — the constraint moves out of semantics and into the literal token stream (see [[Concept - Prompt Engineering]]). OpenAI's chat API does **not** support arbitrary assistant-turn prefill — use `response_format`/tool-calling there instead; this technique is Anthropic-Messages-API-specific.

**Dependencies:** `anthropic>=0.40.0`, a valid `ANTHROPIC_API_KEY` in the environment.

**Expected output** (model/version-dependent, illustrative):
```text
{"sentiment": "positive"}
```

```python
"""
Snippet - Prefilling the Assistant Turn

Seeds the assistant's reply with a partial JSON object so the model
continues it rather than starting fresh, and uses a stop_sequence to
freeze generation the instant the one field we want is closed off --
forcing a single enum value with zero preamble or trailing commentary.
See Playbook - Reliable Structured Output for the full validate-and-repair
procedure this technique feeds into.

Dependencies: anthropic>=0.40.0, a valid ANTHROPIC_API_KEY in the environment.
Expected output (model/version-dependent, illustrative):
    {"sentiment": "positive"}
"""

import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

REVIEW = "The battery life is incredible and it charges in ten minutes."
PREFILL = '{"sentiment": "'   # opens the object AND the string value

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=20,
    # Low temperature: no grammar constraint is enforcing structure here,
    # so sampling noise is the only thing that can break the label --
    # see Concept - Sampling and Decoding Parameters.
    temperature=0,
    messages=[
        {
            "role": "user",
            "content": (
                'Classify the sentiment of this review as exactly one of '
                f'"positive", "negative", or "neutral".\n\nReview: {REVIEW}'
            ),
        },
        # The prefill: an OPEN assistant turn, no EOS. The model treats
        # this as text it already committed to and continues it -- it
        # cannot preface the answer with "Sure, the sentiment is..."
        # because that continuation is no longer syntactically available.
        {"role": "assistant", "content": PREFILL},
    ],
    # The API returns only the NEW tokens, and a matched stop_sequence is
    # excluded from the returned text -- so generation halts the instant
    # the model emits the closing quote of the label, before it can add a
    # second field or any trailing prose.
    stop_sequences=['"'],
)

label = response.content[0].text
full_json = PREFILL + label + '"}'
print(full_json)
assert full_json in (
    '{"sentiment": "positive"}',
    '{"sentiment": "negative"}',
    '{"sentiment": "neutral"}',
)
```

**Other uses of the same technique:** forcing the first token of an enum before an adversary or the model itself can hedge; skipping a chain-of-thought preamble when you want the answer only; holding a persona across a long generation by re-seeding it; extracting into a fixed template field by field; seeding a partial reasoning scaffold to steer *how* the model reasons, not just what it outputs.

**Cautions:** the prefill text counts as input tokens on every call, not a free instruction. A careless prefill can strand the model in a syntactically impossible continuation (e.g., prefilling a value that can't legally follow the schema) with no way to recover except discarding the call. Don't prefill past the point where the model actually has to make a decision — over-constraining defeats the purpose. Prefill can also weaken trained safety behavior, since a refusal is itself a completion the model has to *choose* to start, and a prefill that already commits to a compliant-looking opening can suppress that choice (see [[Concept - Refusal Mechanics]]) — use this technique deliberately, and treat prefilled-content review as part of any red-teaming pass, not an afterthought. Reasoning models complicate this further: several restrict or silently strip assistant-turn prefill ahead of a hidden thinking block specifically to stop callers from short-circuiting the reasoning process this way — see [[Concept - Prompting Reasoning Models]] for how prefill and other prompting conventions change once a hidden chain-of-thought sits in the loop.

## Why it's written this way

1. **The full JSON is reconstructed from `PREFILL + label + '"}'`, not read directly off the API response.** A matched `stop_sequence` is excluded from the returned text by the Anthropic API — forgetting to manually re-append the stop string and the prefill prefix is the single most common way this technique silently produces invalid JSON.
2. **Stopping on the closing quote (`"`), not on `}`.** Stopping on `}` only works for a single-field, unnested object; stopping on the first `"` generalizes to forcing exactly one field's value regardless of how many other keys the schema has, which is the more common real use case (classification, single-field extraction).
3. **The prefill is kept to the absolute minimum** — just enough tokens (`{"sentiment": "`) to remove the "should I add preamble" decision point, without dictating the label itself. Over-prefilling (seeding the actual expected answer) would bias or invalidate the classification rather than merely formatting it — the goal is to constrain *shape*, never *content*.
4. **Temperature is pinned to 0.** With no grammar enforcing the label set here (contrast [[Concept - Constrained Decoding]]), decoding determinism is the only thing keeping the model inside the three allowed strings; a higher temperature can and occasionally will produce an out-of-vocabulary label that a downstream enum parser rejects.

## Connections
- [[Playbook - Reliable Structured Output]] — the full procedure this technique is one step of, including the validate-and-repair loop for when prefill alone isn't enough.
- [[Concept - Chat Templates and Special Tokens]] — why leaving the assistant turn open (no EOS) is even possible: it's a property of how chat templates delimit turns.
- [[Concept - Sampling and Decoding Parameters]] — the temperature setting this snippet pins to 0, and why that choice matters more without a grammar constraint.
- [[Concept - Refusal Mechanics]] — the safety-relevant caution: prefill can suppress a refusal the model would otherwise have chosen to emit.
- [[Concept - Prompt Engineering]] — the general principle this snippet is a concrete instance of: steering a frozen model's output distribution by choosing its input, not its weights.
- [[Concept - Constrained Decoding]] — the alternative that enforces the label set at the decoding level instead of relying on temperature-0 determinism.
- [[Concept - Prompting Reasoning Models]] — reasoning models handle, and often restrict, assistant-turn prefill differently once a hidden thinking block sits ahead of the visible completion.

## Sources
- Anthropic — Messages API documentation, "Prefill Claude's response." The canonical description of assistant-turn prefill and its provider-specific availability.
- Willard & Louf (2023) — "Efficient Guided Generation for Large Language Models." The stronger, grammar-level alternative to this prompt-level technique when the label set must be enforced rather than merely encouraged.
