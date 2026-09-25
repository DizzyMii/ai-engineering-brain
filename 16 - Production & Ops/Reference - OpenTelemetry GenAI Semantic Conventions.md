---
tags: [reference, domain/production-ops, level/advanced]
aliases: [OTel GenAI, GenAI Semantic Conventions, gen_ai.* attributes]
summary: "Lookup for OpenTelemetry's gen_ai.* span names, attributes, and metrics for vendor-neutral LLM instrumentation (Experimental, 2026)."
---

*(as of 2026 — spec status: Experimental, actively evolving. Pin the semconv version your instrumentation targets; attribute names change between releases.)*

## Span naming and kind

| Span name pattern | Example | Span kind |
|---|---|---|
| `chat {model}` | `chat gpt-4o-2024-08-06` | CLIENT |
| `text_completion {model}` | `text_completion claude-sonnet-4-20250514` | CLIENT |
| `embeddings {model}` | `embeddings text-embedding-3-large` | CLIENT |
| `execute_tool {tool_name}` | `execute_tool get_weather` | INTERNAL |

LLM-provider-call spans are `CLIENT` and wrap the outbound network call to the provider. Tool-execution spans are `INTERNAL` because they run in-process and never cross a service boundary.

## Core request attributes

| Attribute | Meaning | Example value |
|---|---|---|
| `gen_ai.system` | Provider/backend identifier | `openai`, `anthropic`, `aws.bedrock` |
| `gen_ai.request.model` | Requested model id, as sent | `gpt-4o-2024-08-06` |
| `gen_ai.request.temperature` | Sampling temperature | `0.7` |
| `gen_ai.request.top_p` | Nucleus sampling parameter | `1.0` |
| `gen_ai.request.max_tokens` | Requested output token cap | `4096` |

## Response attributes

| Attribute | Meaning | Example value |
|---|---|---|
| `gen_ai.response.model` | Model id that actually served the request¹ | `gpt-4o-2024-08-06` |
| `gen_ai.response.id` | Provider-assigned response/request id | `chatcmpl-abc123` |
| `gen_ai.response.finish_reasons` | Why generation stopped | `["stop"]`, `["length"]`, `["tool_calls"]` |

¹ Not always the same as `gen_ai.request.model`: a floating alias or a provider-side reroute can serve a different snapshot from the one requested. Diffing the two is a cheap, spec-native drift-detection signal (see [[Lore - When the Model Changed Under You]]).

## Token usage (span attributes)

| Attribute | Meaning | Billing-authoritative? |
|---|---|---|
| `gen_ai.usage.input_tokens` | Prompt/input tokens consumed | Yes; use this, not a local tokenizer estimate |
| `gen_ai.usage.output_tokens` | Completion/output tokens generated | Yes |

These two fields are the span-level source of truth for cost. [[Concept - Cost Engineering for LLM Applications]] has the pricing math that uses them.

## Prompt/completion content capture

| Mechanism | Default | Notes |
|---|---|---|
| `gen_ai.prompt` / `gen_ai.completion` (legacy attribute form) | — | Superseded; large text as indexed attributes broke cardinality assumptions |
| Span **events** carrying prompt/completion content | **OFF by default** | Opt-in, because full-payload capture is a PII/privacy liability, see [[Concept - PII Redaction and Data Retention]] |

## Metrics

| Metric | Type | Dimensions |
|---|---|---|
| `gen_ai.client.token.usage` | Histogram | `gen_ai.system`, `gen_ai.request.model`, token type (input/output) |
| `gen_ai.client.operation.duration` | Histogram | `gen_ai.system`, `gen_ai.request.model`, operation name |

The duration histogram feeds TTFT/TPOT-style latency breakdowns in [[Concept - Latency, Throughput, and Cost in LLM Serving]]. The token-usage histogram feeds cost dashboards directly, next to the span-level attributes above.

## Instrumentation and stability

| Aspect | Status (as of 2026) |
|---|---|
| Spec maturity | **Experimental**; attribute names and span shapes still change between semconv releases |
| Popular emitters | OpenLLMetry (Traceloop), OpenInference (Arize) |
| Popular consumers | [[Breakdown - Langfuse]], Arize Phoenix, Traceloop backends |
| Agent/tool-span coverage | Actively being extended (as of 2026). Don't assume a stable schema for multi-step agent traces yet; see [[Gotchas - Agents in Production]] |

While the spec is Experimental, treat a semconv version upgrade as a breaking change for any dashboard or alert built on raw attribute names. Prefer instrumentation libraries that abstract the names over hand-rolled `gen_ai.*` string literals scattered through application code.

## Connections

- [[Concept - LLM Observability and Tracing]] — this note is the wire-level attribute vocabulary for the trace/span data model that note describes conceptually.
- [[Breakdown - Langfuse]] — a concrete backend that ingests these conventions directly, alongside its own richer trace/observation data model.
- [[Concept - PII Redaction and Data Retention]] — the reason prompt/completion content capture defaults to off in this spec.
- [[Concept - Cost Engineering for LLM Applications]] — consumes `gen_ai.usage.*` as the authoritative token counts for cost computation.
- [[Gotchas - Agents in Production]] — agent/tool-span coverage in this spec is immature, which is exactly where agent observability breaks down first.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — the `gen_ai.client.operation.duration` histogram is the raw material for the TTFT/TPOT metrics that note defines.
- [[Concept - Production Monitoring and Drift Detection]] — a diff between `gen_ai.request.model` and `gen_ai.response.model` is a cheap, spec-native drift signal this note's monitoring feeds on.

## Sources
- OpenTelemetry GenAI Special Interest Group (2024-2026, ongoing) — the `gen_ai.*` semantic conventions this reference tabulates, Experimental status as of 2026.
- OpenLLMetry (Traceloop) and OpenInference (Arize) instrumentation library documentation (as of 2026) — the emitter implementations that populate these conventions in practice.
- Langfuse ingestion documentation (as of 2026) — a concrete consumer mapping these conventions onto its own trace/observation model.
