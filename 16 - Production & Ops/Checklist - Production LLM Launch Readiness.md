---
tags: [checklist, domain/production-ops, level/advanced]
aliases: [LLM launch checklist, prod readiness review]
summary: "Pre-flight checks across observability, cost, resilience, safety, quality, and rollout before an LLM feature ships to production."
---
# Checklist - Production LLM Launch Readiness

Run every item before an LLM feature goes live, and again before any change to the model, prompt or inference config ships. Per [[Concept - LLMOps]], a change to any one of those three is a deploy. Each group maps to a class of incident this checklist is meant to prevent before it happens; "Why these items" below explains each.

## Observability

- [ ] Every trace records the exact model snapshot id (not a floating alias), the prompt template version/hash and the full inference config (temperature, `max_tokens`, tools). See [[Concept - LLM Observability and Tracing]].
- [ ] Token counts (input/output) and computed cost are on every span, taken from the provider's usage object and not a local tokenizer estimate.
- [ ] Dashboards exist for p50/p99 latency, error rate and cost/request, wired to a page-able alert channel.
- [ ] Both your request ID and the provider's request-id/`system_fingerprint` header are logged, so a support ticket can be matched to its trace.

## Cost

- [ ] `max_tokens` is capped on every call path, so nothing generates unbounded ([[Concept - Cost Engineering for LLM Applications]]).
- [ ] A per-tenant/per-user monthly budget is enforced atomically before the call, not only reconciled after the invoice arrives ([[Snippet - Token Cost Attribution and Budget Enforcement]] has a reference implementation).
- [ ] A cost-per-request baseline exists, with anomaly alerts on deviation (e.g., 3x the trailing 7-day median).
- [ ] Caching (semantic and/or prompt-prefix) is on wherever it's semantically safe.

## Resilience

- [ ] Connect, time-to-first-token, and overall/stream-idle timeouts are set independently, per [[Pattern - Resilient LLM Request Handling]].
- [ ] Retries are limited to transient/idempotent failures, use exponential backoff with full jitter, and have a hard attempt cap.
- [ ] A provider/model fallback chain is configured and has been exercised end to end. Written into a config file doesn't count.
- [ ] A circuit breaker trips on a sustained error-rate threshold to the primary provider.
- [ ] A per-feature kill switch/flag exists and can disable the feature without a code deploy.
- [ ] A graceful-degradation path (a smaller model, a cached response, a static fallback message) is defined for when every upstream option fails.

## Safety & compliance

- [ ] PII redaction runs on prompt/completion content before it is logged or stored, per [[Concept - PII Redaction and Data Retention]].
- [ ] Prompt-injection and jailbreak guardrails are live on the request path, not listed as a future task. See [[Concept - Prompt Injection]].
- [ ] A zero-data-retention endpoint or a signed DPA is in place with the provider if your data-handling policy requires it.
- [ ] Inbound rate limits are set to bound abuse and cost amplification from a single caller.

## Quality & eval

- [ ] An offline eval suite (see [[Deep Dive - Designing an Eval Harness]]) passes an agreed quality threshold before this version ships.
- [ ] A canary or shadow-traffic plan is written down with explicit rollback trigger thresholds, per [[Concept - Model Deployment Patterns for LLMs]].
- [ ] A regression eval runs automatically in CI on every prompt/model/config change.
- [ ] User feedback capture (thumbs up/down, regenerate) goes into telemetry as well as the UI.

## Rollout

- [ ] The model is pinned to a dated snapshot id in every environment. Never a floating alias.
- [ ] The N-1 (previous) version stays warm and reachable via an instant alias/router flip for rollback.
- [ ] An incident runbook for this feature exists and is linked from the on-call rotation. See [[Playbook - Incident Response for LLM Systems]].
- [ ] A named on-call owner is assigned before launch, not after the first incident.

## Why these items

- **Pinned dated snapshots, not floating aliases.** Floating aliases have been repointed under teams overnight, silently changing formatting and refusal behavior with no deploy on their side ([[Lore - When the Model Changed Under You]] has the documented cases). Skip this check and you find out from a user complaint, not a dashboard.
- **Atomic per-tenant budget enforcement, checked before the call.** Per-replica counters race under concurrency and undercount. One misbehaving tenant can blow through a monthly cap before anyone notices a spike, and without this check the first signal is the invoice.
- **Retry jitter plus a circuit breaker.** Synchronized blind retries have turned a transient provider 429 blip into a self-inflicted 20x bill and an outage that outlasted the original blip by hours.
- **PII redaction on logs from the start.** Full-payload observability logging silently captures prompts and completions, including anything a user pasted in, unless someone redacts before the first deploy. Adding redaction after the logs already hold PII doesn't undo the exposure.
- **Warm N-1 rollback, not "redeploy if it breaks."** Without a warm standby you redeploy under incident pressure, and an outage an alias flip would end in seconds lasts a full deploy cycle.
- **A canary/shadow plan with explicit thresholds, not "we'll watch it."** Without a quantitative rollback trigger, a real quality regression looks like noise against non-deterministic output variance until it has reached 100% of traffic. [[Concept - Production Monitoring and Drift Detection]] explains why proxy-metric monitoring needs a stated threshold before you can act on it.

## Connections

- [[Concept - LLMOps]] — the reason this checklist has to be re-run on every prompt, model, or config change: any one of the three is a deploy.
- [[Concept - LLM Observability and Tracing]] — the trace/span data model the Observability group's items require to already be wired up.
- [[Playbook - Incident Response for LLM Systems]] — the runbook this checklist's rollout and resilience items feed into once something does go wrong.
- [[Concept - Model Deployment Patterns for LLMs]] — the canary/shadow/blue-green mechanics behind the Quality & eval group's rollout-plan item.
- [[Concept - PII Redaction and Data Retention]] — the mechanism behind the Safety & compliance group's redaction and DPA items.
- [[Concept - Cost Engineering for LLM Applications]] — the cost model and levers behind the Cost group's caps, budgets, and caching items.
- [[Snippet - Token Cost Attribution and Budget Enforcement]] — a reference implementation of the Cost group's atomic per-tenant budget enforcement item.
- [[Pattern - Resilient LLM Request Handling]] — the timeout/retry/circuit-breaker/fallback design behind the entire Resilience group.
- [[Concept - Prompt Injection]] — the threat the Safety & compliance group's guardrail item exists to mitigate.
- [[Deep Dive - Designing an Eval Harness]] — the harness design behind the Quality & eval group's offline-eval and CI-regression items.
- [[Concept - Production Monitoring and Drift Detection]] — the ongoing discipline this one-time checklist hands off to once the feature is live.
- [[Lore - When the Model Changed Under You]] — the war stories behind the pinned-snapshot rollout item, for the reader who wants to know why it's non-negotiable.
- [[Gotchas - LLM Production Operations]] — the recurring incident catalog (retry storms, cache false-hits, reservation throttling) each checklist item is designed to preempt.

## Sources
This checklist is a distilled operational synthesis rather than a single citable result; each item's incident class is documented in its own linked note, most concretely in [[Lore - When the Model Changed Under You]] and [[Gotchas - LLM Production Operations]].
