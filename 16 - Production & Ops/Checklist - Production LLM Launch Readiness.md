---
tags: [checklist, domain/production-ops, level/advanced]
aliases: [LLM launch checklist, prod readiness review]
summary: "Pre-flight checks across observability, cost, resilience, safety, quality, and rollout before an LLM feature ships to production."
---
# Checklist - Production LLM Launch Readiness

Run every item below before an LLM feature goes live, and again before any change to the model, prompt, or inference config ships — per [[Concept - LLMOps]], any one of those three is a deploy. Each group maps to a class of incident this checklist exists to prevent before it happens rather than after; see "Why these items" below.

## Observability

- [ ] Every trace captures the exact model snapshot id (not a floating alias), the prompt template version/hash, and the full inference config (temperature, `max_tokens`, tools) — see [[Concept - LLM Observability and Tracing]].
- [ ] Token counts (input/output) and computed cost are attached to every span, sourced from the provider's usage object, not a local tokenizer estimate.
- [ ] Dashboards exist for p50/p99 latency, error rate, and cost/request, wired to a page-able alert channel.
- [ ] Your own request ID and the provider's request-id/`system_fingerprint` header are both logged so a support ticket can be correlated back to a trace.

## Cost

- [ ] `max_tokens` is capped on every call path — no unbounded generation, per [[Concept - Cost Engineering for LLM Applications]].
- [ ] A per-tenant/per-user monthly budget is enforced atomically before the call, not reconciled only after the invoice arrives (see [[Snippet - Token Cost Attribution and Budget Enforcement]] for a reference implementation).
- [ ] A cost-per-request baseline is established with anomaly alerting on deviation (e.g., 3x the trailing 7-day median).
- [ ] Caching (semantic and/or prompt-prefix) is enabled everywhere it is semantically safe to do so.

## Resilience

- [ ] Connect, time-to-first-token, and overall/stream-idle timeouts are set independently, per [[Pattern - Resilient LLM Request Handling]].
- [ ] Retries are limited to transient/idempotent failures, use exponential backoff with full jitter, and have a hard attempt cap.
- [ ] A provider/model fallback chain is configured and has actually been exercised end to end, not just written into a config file.
- [ ] A circuit breaker trips on a sustained error-rate threshold to the primary provider.
- [ ] A per-feature kill switch/flag exists and can disable the feature without a code deploy.
- [ ] A graceful-degradation path (a smaller model, a cached response, a static fallback message) is defined for when every upstream option fails.

## Safety & compliance

- [ ] PII redaction runs on prompt/completion content before it is logged or stored, per [[Concept - PII Redaction and Data Retention]].
- [ ] Prompt-injection and jailbreak guardrails are active on the request path — not a documented future task; see [[Concept - Prompt Injection]].
- [ ] A zero-data-retention endpoint or a signed DPA is in place with the provider if your data-handling policy requires it.
- [ ] Inbound rate limits are set to bound abuse and cost amplification from a single caller.

## Quality & eval

- [ ] An offline eval suite (see [[Deep Dive - Designing an Eval Harness]]) passes an agreed quality threshold before this version ships.
- [ ] A canary or shadow-traffic plan is written down with explicit rollback trigger thresholds, per [[Concept - Model Deployment Patterns for LLMs]].
- [ ] A regression eval runs automatically in CI on every prompt/model/config change.
- [ ] User feedback capture (thumbs up/down, regenerate) is wired into telemetry, not just the UI.

## Rollout

- [ ] The model is pinned to a dated snapshot id in every environment — never a floating alias.
- [ ] The N-1 (previous) version stays warm and reachable via an instant alias/router flip for rollback.
- [ ] An incident runbook for this feature exists and is linked from the on-call rotation — see [[Playbook - Incident Response for LLM Systems]].
- [ ] A named on-call owner is assigned before launch, not after the first incident.

## Why these items

- **Pinned dated snapshots, not floating aliases.** Floating aliases have repointed under teams overnight, silently changing formatting and refusal behavior with zero deploy on their side — see [[Lore - When the Model Changed Under You]] for the documented cases. A launch that skips this check finds out from a user complaint, not a dashboard.
- **Atomic per-tenant budget enforcement, checked before the call.** Per-replica counters race under concurrency and undercount; a single misbehaving tenant can blow through a monthly cap before anyone notices a spike, and the first signal without this check is the invoice.
- **Retry jitter plus a circuit breaker.** Synchronized blind retries have turned a transient provider 429 blip into a self-inflicted 20x bill and an outage that outlasted the original blip by hours.
- **PII redaction on logs, not opt-in later.** Full-payload observability logging silently captures prompts and completions — including anything a user pasted in — unless someone explicitly redacts before the first deploy; retrofitting redaction after logs already contain PII doesn't undo the exposure.
- **Warm N-1 rollback, not "redeploy if it breaks."** The alternative to a warm standby is redeploying under incident pressure, which turns an outage that an alias flip would end in seconds into one that runs for the length of a full deploy cycle.
- **A canary/shadow plan with explicit thresholds, not "we'll watch it."** Without a quantitative rollback trigger, a genuine quality regression reads as noise against non-deterministic output variance until it has already reached 100% of traffic — see [[Concept - Production Monitoring and Drift Detection]] for why proxy-metric monitoring needs a stated threshold to be actionable at all.

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
