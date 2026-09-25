---
tags: [playbook, domain/prompting-context, level/core]
aliases: [structured output, JSON mode, schema-constrained generation]
summary: "End-to-end procedure for valid, schema-conforming LLM output: mechanism choice, prompting, decoding, and a bounded validate-repair loop."
---
# Playbook - Reliable Structured Output

> **Goal:** get an LLM to emit valid, schema-conforming JSON (or another structured format) reliably enough to build a pipeline on, which is a higher bar than "usually works in the demo." **When to run this:** whenever a downstream system (a database write, a function dispatch, a UI render) parses the model's output in code. **Prerequisites:** a concrete schema (JSON Schema, a pydantic/zod model, or a fully populated typed example), a parser, and a holdout set of representative inputs to measure against.

## Steps

1. **Pick a mechanism that matches your reliability bar.**
   Action: rank the four mechanisms by strength and take the cheapest one that fits your error budget. From weakest to strongest:
   (a) Plain prompt plus a described schema. Needs no API support and works on any model, but gives only ~85-98% valid JSON depending on model and schema complexity.
   (b) Provider-native structured output (OpenAI's `response_format` with a `json_schema`, Anthropic's forced [[Concept - Tool Use and Function Calling|tool use]]). The provider enforces the shape server-side, which gets syntactic validity close to 100%.
   (c) Grammar-constrained decoding ([[Concept - Constrained Decoding]]). Invalid tokens are masked at every decoding step, so output is syntactically valid *by construction*, not by training. It's the strongest guarantee available.
   (d) Tool/function calling used purely as a JSON transport, forcing one named tool. Generation goes through whatever tool-call machinery the model got the most post-training on. Most production teams reach for this first, since it's robust and every framework supports it.
   Expected observation: the error budget picks the tier. A one-off internal script can live with (a). A customer-facing pipeline that fails loudly on a bad parse wants (b) or (d). A system with no repair loop at all (an embedded agent, a single-shot batch job) wants the hard guarantee of (c).
   What deviation means: grammar-constrained decoding on a low-stakes prototype costs setup time and risks content distortion (see Tradeoffs below) for a guarantee you don't need yet.

2. **Write the prompt so compliance is the easiest path.**
   Action: put the exact schema in the prompt (paste the real JSON Schema, or a fully populated typed example of the target object) and include one or two few-shot outputs in the identical format. If the API allows it, prefill the assistant turn with the opening brace ([[Snippet - Prefilling the Assistant Turn]]). The model then continues an already-open turn ([[Concept - Chat Templates and Special Tokens]]) instead of deciding from scratch whether to explain itself first.
   Expected observation: with prefill, the first token back is whatever follows `{`, with no "Sure, here's the JSON:" preamble to strip.
   What deviation means: if you still get preamble after prefilling, the provider probably doesn't support raw assistant-turn continuation (OpenAI's chat API doesn't; Anthropic's Messages API does). Fall back to `response_format` or tool calling plus a hard "output only the JSON object, no commentary" instruction, and strip fences defensively anyway.

3. **Set decoding parameters for your mechanism.**
   Action: under prompt-only or provider JSON mode (tiers a/b), keep [[Concept - Sampling and Decoding Parameters|temperature]] low (0-0.3). Sampling noise is the only thing between you and a clean parse. Under grammar-constrained decoding (tier c) you can safely raise temperature for content diversity, because the constraint guarantees syntactic validity whatever token the sampler picks.
   Expected observation: under tiers (a)/(b), the malformed-output rate drops measurably as temperature drops. Under tier (c) it stays flat, because failures there are never syntactic.
   What deviation means: occasional broken JSON at high temperature under tier (a) is expected, not a model bug. Lower the temperature or move up a tier; don't retry blind.

4. **Validate, and repair on failure, with a cap.**
   Action: parse the raw response against your schema with pydantic (Python) or zod (TypeScript). On a parse failure, make a second call with the original malformed output and the literal parser error, and ask the model to fix only what's broken. Cap total repair attempts (two is a common default) so a pathological input can't loop forever.
   Expected observation: a single-shot valid-parse rate of 85-98% typically rises to 99%+ after one bounded repair pass, at the cost of one extra round trip for the failing minority.
   What deviation means: if more than a small fraction of traffic hits the repair cap, the schema or prompt is under-specified. Fix Step 2 instead of raising the cap.

## Verification

Track the *measured* valid-parse rate on a holdout set of representative inputs, not a few examples you eyeballed while writing the prompt. Log it per prompt version along with field-level accuracy ([[Concept - Prompt Evaluation and Versioning]]). An object that parses cleanly but has a hallucinated field, a wrong enum value, or a null where a real value belonged is a silent failure schema validation never catches. Parseability is necessary but not sufficient. You need both numbers before you trust the pipeline in production.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Output wrapped in ` ```json ... ``` ` fences | Chat-trained habit of formatting code as markdown | Instruct "no code fences" and strip them defensively before parsing anyway ([[Gotchas - Prompt Formatting and Tokenization]]) |
| Trailing comma before a closing `}`/`]` | Model copies a common but invalid JSON pattern from training data | Strip trailing commas with a regex pre-pass, or fall back to a lenient parser |
| Missing or silently hallucinated fields | Schema under-specified, or few-shot examples didn't cover that field | Add explicit per-field descriptions and a "use null if absent" instruction |
| Enum value drift ("Yes" instead of `true`, an invented category) | Allowed values weren't listed verbatim in the prompt | List every allowed enum value literally in the schema text, beyond its type |
| Unescaped quotes inside string values | Model doesn't reliably escape embedded quotes itself | Ask for explicit escaping, and run a JSON-repair library as a pre-parse pass before failing the record |
| Object truncated at `max_tokens` | Output limit below the schema's actual token footprint | Raise `max_tokens` well above the largest expected object, or stream, detect truncation and retry with a higher cap |

## Tradeoffs

Constrained decoding (tier c) guarantees syntax and never semantics. The grammar forces a well-formed object with the right field names, and the model can still fill the fields with wrong or hallucinated *values*. Squeezing the token distribution onto a grammar path can also measurably distort content quality and log-probabilities compared with unconstrained generation. Tool calling (tier d) is the most robust in practice because it uses the model's dedicated tool-call post-training, but it adds a round trip of latency and, on some providers, a small cost premium over a raw completion. Don't default to the heaviest mechanism. Pick the cheapest tier that clears the reliability bar you measured under Verification.

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
