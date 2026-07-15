---
tags: [playbook, domain/prompting-context, level/core]
aliases: [structured output, JSON mode, schema-constrained generation]
summary: "End-to-end procedure for valid, schema-conforming LLM output: mechanism choice, prompting, decoding, and a bounded validate-repair loop."
---
# Playbook - Reliable Structured Output

> **Goal:** get an LLM to emit valid, schema-conforming JSON (or another structured format) at a reliability you can build a pipeline on top of — not "usually works in the demo." **When to run this:** any time a downstream system — a database write, a function dispatch, a UI render — parses the model's output programmatically. **Prerequisites:** a concrete schema (JSON Schema, a pydantic/zod model, or a fully-populated typed example), a parser, and a holdout set of representative inputs to measure against.

## Steps

1. **Choose a mechanism sized to your reliability bar.**
   Action: rank the four available mechanisms by strength and pick the cheapest one that clears your error budget. Weakest to strongest: (a) plain prompt + described schema — no API support required, works on any model, but only ~85-98% valid-JSON rate depending on model and schema complexity; (b) provider-native structured output (OpenAI's `response_format` with a `json_schema`, Anthropic's forced [[Concept - Tool Use and Function Calling|tool use]]) — the provider enforces the shape server-side, pushing syntactic validity close to 100%; (c) grammar-constrained decoding ([[Concept - Constrained Decoding]]) — masks invalid tokens at every decoding step so output is syntactically valid *by construction*, not by training, the strongest guarantee available; (d) tool/function calling used purely as a JSON transport, forcing a single named tool — routes generation through whatever tool-call machinery the model was most heavily post-trained on, and is what most production teams reach for first because it's both robust and framework-supported everywhere.
   Expected observation: your error budget picks the tier. A one-off internal script tolerates (a); a customer-facing pipeline that fails loudly on a bad parse wants (b) or (d); a system with no repair loop available at all (an embedded agent, a single-shot batch job) wants the hard guarantee of (c).
   What deviation means: reaching for grammar-constrained decoding on a low-stakes prototype means paying setup cost and content-distortion risk (see Tradeoffs below) for a guarantee you don't need yet.

2. **Construct the prompt to make compliance the path of least resistance.**
   Action: state the exact schema in the prompt (paste the real JSON Schema, or a fully-populated typed example of the target object), include one or two few-shot output examples in the identical target format, and — if the API supports it — prefill the assistant turn with the opening brace ([[Snippet - Prefilling the Assistant Turn]]) so the model continues an already-open turn ([[Concept - Chat Templates and Special Tokens]]) instead of deciding from scratch whether to explain itself first.
   Expected observation: with prefill, the first token you get back is whatever follows `{` — no "Sure, here's the JSON:" preamble to strip.
   What deviation means: if preamble still appears after prefilling, the provider likely doesn't support raw assistant-turn continuation (OpenAI's chat API does not; Anthropic's Messages API does) — fall back to `response_format`/tool-calling plus a hard "output only the JSON object, no commentary" instruction, and strip fences defensively regardless.

3. **Set decoding parameters for the mechanism you picked.**
   Action: under prompt-only or provider-JSON-mode reliability (tiers a/b), keep [[Concept - Sampling and Decoding Parameters|temperature]] low (0-0.3) — sampling noise is the only thing standing between you and a clean parse. Under grammar-constrained decoding (tier c), you can safely run a higher temperature for content diversity, because the constraint machinery guarantees syntactic validity regardless of which token the sampler ends up picking.
   Expected observation: malformed-output rate drops measurably as temperature drops under tiers (a)/(b); it stays flat under tier (c) because the failure mode there is never syntactic.
   What deviation means: sporadic broken JSON at high temperature under tier (a) is expected behavior, not a model bug — either lower temperature or move up a tier rather than retrying blind.

4. **Validate, and on failure, repair — bounded.**
   Action: parse the raw response against your schema with pydantic (Python) or zod (TypeScript). On a parse failure, issue a second call that includes the original malformed output plus the literal parser-error string, and ask the model to fix only what's broken; cap total repair attempts (two is a common default) so a pathological input can't loop indefinitely.
   Expected observation: single-shot valid-parse rate of 85-98% typically climbs to 99%+ after one bounded repair pass, at the cost of one extra round trip on the failing minority.
   What deviation means: if repair attempts are hitting the cap on more than a small fraction of traffic, the schema or prompt is under-specified — fix Step 2, don't just raise the cap.

## Verification

Track the *measured* valid-parse rate on a holdout set of representative inputs — not a handful of examples eyeballed while writing the prompt. Log it per prompt version alongside field-level accuracy ([[Concept - Prompt Evaluation and Versioning]]): an object that parses cleanly but has a hallucinated field, a wrong enum value, or a null where a real value belonged is a silent failure that schema validation alone never catches. Parseability is necessary, not sufficient — you need both numbers before trusting the pipeline in production.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Output wrapped in ` ```json ... ``` ` fences | Chat-trained habit of formatting code as markdown | Instruct "no code fences," strip them defensively before parsing regardless ([[Gotchas - Prompt Formatting and Tokenization]]) |
| Trailing comma before a closing `}`/`]` | Model imitates a common but invalid JSON pattern from training data | Strip trailing commas with a regex pre-pass, or fall back to a lenient parser |
| Missing or silently hallucinated fields | Schema under-specified, or few-shot examples didn't cover that field | Add explicit per-field descriptions plus a "use null if absent" instruction |
| Enum value drift ("Yes" instead of `true`, an invented category) | Allowed values weren't enumerated verbatim in the prompt | List every allowed enum value literally in the schema text, not just its type |
| Unescaped quotes inside string values | Model doesn't reliably self-escape embedded quotes | Ask for explicit escaping, and run a JSON-repair library as a pre-parse pass before failing the record |
| Truncated object at `max_tokens` | Output limit set below the schema's actual token footprint | Raise `max_tokens` to comfortably exceed the largest expected object, or stream and detect truncation, then retry with a higher cap |

## Tradeoffs

Constrained decoding (tier c) guarantees syntax, never semantics — a grammar forces a well-formed object with correct field names and still lets the model fill fields with wrong or hallucinated *values*, and narrowing the token distribution onto a grammar path can measurably distort content quality and log-probabilities relative to unconstrained generation. Tool-calling (tier d) is the most robust choice in practice because it rides the model's dedicated tool-call post-training, but it adds a round trip's worth of latency and, on some providers, a small cost premium versus a raw completion. Don't default to the heaviest mechanism — pick the cheapest tier that clears the reliability bar measured in Verification above.

## Connections
- [[Concept - Constrained Decoding]] — the grammar-masking algorithm behind tier (c); read it before promising "guaranteed valid" to a stakeholder.
- [[Concept - Sampling and Decoding Parameters]] — the temperature lever Step 3 tunes, and it behaves differently once a grammar constraint is in play.
- [[Concept - Tool Use and Function Calling]] — the mechanism tier (d) repurposes purely as a JSON transport.
- [[Snippet - Prefilling the Assistant Turn]] — the concrete API-level technique Step 2 uses to skip preamble.
- [[Concept - Chat Templates and Special Tokens]] — why assistant prefill works at all: it continues an open turn rather than issuing a new instruction.
- [[Gotchas - Prompt Formatting and Tokenization]] — the catalog of silent formatting failures the branch table above draws from.
- [[Concept - Prompt Evaluation and Versioning]] — how to track valid-parse rate and field accuracy over time instead of trusting a one-off spot check.

## Sources
- OpenAI — "Introducing Structured Outputs in the API" (Aug 2024) — the `response_format`/`json_schema` mechanism behind tier (b) and its reported near-100% syntactic reliability on schema conformance.
- Anthropic — Messages API tool-use documentation — forced single-tool calling as a JSON-transport pattern (tier d).
- Willard & Louf (2023) — "Efficient Guided Generation for Large Language Models" — the token-masking mechanism grammar-constrained decoding (tier c) is built on.
