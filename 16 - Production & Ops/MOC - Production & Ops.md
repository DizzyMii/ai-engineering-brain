---
tags: [moc, domain/production-ops, level/surface]
aliases: []
summary: "Map of Production & Ops: deploying, observing, costing, routing, and keeping LLM-backed systems alive under real traffic."
---
# MOC - Production & Ops

This domain covers what happens once an LLM-backed application is live and taking real traffic. How it's deployed and rolled back. How it stays observable and inside its cost and latency budgets. How it degrades when a provider has a bad day, and how drift, PII exposure and quota abuse get caught before they turn into incidents. LLMOps breaks most of the assumptions it inherits from MLOps. The model is usually a frozen third-party dependency called over HTTP, so what changes week to week is the prompt and the gateway/routing/caching layer around it, and operational risk moves from training pipelines to runtime resilience. Almost every note here comes back to three facts: providers change models under you without asking, requests are nondeterministic even at temperature 0, and cost, latency and quality all move together once you touch caching, routing or batching. The notes run from day-one launch readiness to the incident runbook you reach for at 3am.

**Start here, by level:**
- **Surface:** [[Concept - LLMOps]]: why LLMOps is MLOps rebuilt around a frozen third-party model and a versioned prompt, with ship cycles in hours, not weeks.
- **Core:** [[Concept - Model Deployment Patterns for LLMs]]: shadow, canary and blue-green rollout for model/prompt/config changes, and what gates them when there's no ground-truth label.
- **Advanced:** [[Concept - GPU Orchestration on Kubernetes]]: device plugin semantics, MIG/time-slicing/MPS and gang scheduling, the internals under every autoscaled inference deployment.
- **Frontier:** [[Decision - Self-Hosting vs Managed LLM API]]: the GPU-utilization breakeven that decides between running your own fleet and staying on a managed API, and when that answer flips.
- **Unicorn:** [[Gotchas - LLM Production Operations]]: hard-won pitfalls of running LLM apps in production, ordered by how much pain each causes.

## Orientation and lifecycle
- [[Concept - LLMOps]] — MLOps rebuilt around a frozen third-party model and a versioned prompt, with ship cycles in hours, not weeks.
- [[Concept - Model Lifecycle and Versioning]] — how the model+prompt+config triple is pinned, promoted, rolled back and retired as providers move the ground under it.
- [[Concept - Model Deployment Patterns for LLMs]] — shadow, canary and blue-green rollout for model/prompt/config changes, with no ground-truth label to gate on.
- [[Checklist - Production LLM Launch Readiness]] — pre-flight checks across observability, cost, resilience, safety, quality and rollout before an LLM feature ships.

## Observability, reliability, and incident response
- [[Concept - LLM Observability and Tracing]] — traces, spans, tokens, cost and quality scores for every LLM call, so agentic pipelines can be debugged in production.
- [[Reference - OpenTelemetry GenAI Semantic Conventions]] — lookup for OpenTelemetry's `gen_ai.*` span names, attributes and metrics for vendor-neutral LLM instrumentation (Experimental, 2026).
- [[Concept - Production Monitoring and Drift Detection]] — catching quality and behavior drift with no ground-truth label: proxy signals, canary probes, change detection.
- [[Concept - Nondeterminism in Production LLM Serving]] — why identical requests diverge even at temperature 0 (batch-dependent floating-point reductions) and what that does to operations.
- [[Pattern - Resilient LLM Request Handling]] — layered client-side resilience for LLM API calls: split timeouts, jittered retries, hedging, circuit breakers, fallback chains.
- [[Playbook - Incident Response for LLM Systems]] — symptom-to-lever runbook for provider outages, latency/cost spikes and silent quality regressions.
- [[Reference - LLM Production SLOs and Latency Budgets]] — the latency/SLO targets and budget breakdowns teams actually hold for LLM apps by use case, which rarely get written down.
- [[Gotchas - LLM Production Operations]] — pitfalls of running LLM apps in production: gateways, caching, cost, versioning, retries, streaming, provider quirks.
- [[Lore - When the Model Changed Under You]] — war stories of provider model drift, silent alias updates and deprecations breaking production, and what each teaches.

## Traffic, routing, and cost
- [[Concept - LLM Gateways and Routing]] — a proxy between app code and model providers that puts keys, load balancing, fallback, caching and cost tracking behind one API.
- [[Concept - Model Routing and Cascades]] — sending each request to a cheap or strong model, via cascades or learned routers, to cut cost at matched quality.
- [[Concept - Rate Limiting and Quota Design]] — why LLM rate limits have to count tokens and concurrency, not requests, and how to enforce them globally and fairly.
- [[Concept - Semantic Caching]] — caching LLM responses by embedding similarity instead of exact match, trading a tuned cosine threshold for skipped model calls.
- [[Concept - Cost Engineering for LLM Applications]] — modeling and controlling the marginal $/request of an LLM app: pricing asymmetry, cost drivers, caching/routing levers, attribution.
- [[Snippet - Token Cost Attribution and Budget Enforcement]] — runnable: count tokens, price a call by exact model id, and atomically enforce a per-tenant LLM budget in Redis.

## Infrastructure, capacity, and hosting decisions
- [[Concept - GPU Orchestration on Kubernetes]] — scheduling and sharing GPUs for LLM inference on Kubernetes: device plugin semantics, MIG/time-slicing/MPS, gang scheduling, cold starts.
- [[Concept - Autoscaling LLM Inference]] — why CPU-based HPA fails for LLM serving, and scaling replicas on queue depth, KV-cache occupancy and a cold-start-aware policy.
- [[Concept - LLM Load Testing and Capacity Planning]] — token-aware load testing and SLO-driven capacity sizing for LLM endpoints: TTFT/TPOT, the latency knee, Little's Law.
- [[Decision - Self-Hosting vs Managed LLM API]] — managed LLM API vs open-weights models on your own GPUs, decided by a GPU-utilization breakeven calculation.

## Data governance and compliance
- [[Concept - PII Redaction and Data Retention]] — where PII leaks through an LLM stack, how redaction and pseudonymization work, and why deletion has to reach caches and vector stores.

## Tooling breakdowns
- [[Breakdown - LiteLLM]] — how LiteLLM's SDK, Router and Proxy put 100+ LLM providers behind one OpenAI-compatible API with fallback and cost tracking.
- [[Breakdown - Langfuse]] — how Langfuse implements the trace/observation/session/score model at volume: async ClickHouse-backed ingestion and versioned prompts.

## Adjacent domains
- [[MOC - Inference & Serving]] — that domain tunes the serving engine; this one keeps it alive, affordable and observable under production traffic.
- [[MOC - Hardware & Systems]] — the GPU memory, interconnect and device facts that orchestration and autoscaling here take as fixed constraints.
- [[MOC - Agents]] — the agentic pipelines whose multi-step traces this domain's observability tooling captures and debugs.
