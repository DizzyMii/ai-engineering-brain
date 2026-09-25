---
tags: [playbook, domain/production-ops, level/core]
aliases: []
summary: "Symptom-to-lever incident runbook for LLM systems: provider outages, latency/cost spikes, and silent quality regressions."
---

> **Goal:** detect, triage and mitigate the LLM-specific incidents classical SRE runbooks don't cover (provider outages, latency spikes, cost spikes, quality regressions) before they become multi-hour outages or five-figure bill surprises. **When to run this:** an alert fires on error rate, p99 latency, cost/req or a golden-set quality diff, or a user/support escalation says "the bot got dumb" or "answers changed." **Prerequisites:** the levers in [[Checklist - Production LLM Launch Readiness]] are already wired: pinned model snapshots, a gateway with fallback, per-tenant budgets, and a stored golden set to diff against.

## Steps

1. **Classify the symptom.** Look at four signals together: error rate (429/5xx), latency (TTFT and TPOT split out), cost/req, and any quality complaint. → *Expected:* one signal dominates and points to a branch below. → *Deviation:* if all four spike at once, suspect a full provider outage before an app-side bug, and check the provider status page first. Check the pitfall signatures in [[Gotchas - LLM Production Operations]] before diagnosing from scratch; most incidents are one of a known handful.

2. **Elevated 429/5xx from the provider → fail over.** Trigger gateway failover to a secondary provider or deployment. That's what the fallback chain and circuit breaker in [[Pattern - Resilient LLM Request Handling]] are for. → *Expected:* error rate drops within one health-check interval (typically 10-30s). → *Deviation:* if failover doesn't bring the error rate down, the fallback deployment is degraded too, or the breaker is wired to the wrong upstream. Check breaker state as well as the primary.

3. **Latency spike → split TTFT from TPOT first.** A TTFT spike points to prefill/queueing (check queue depth, concurrent requests, provider status). A TPOT spike points to decode-side saturation or a model swap on the provider's side. → *Expected:* the split tells you whether the fix is capacity (add replicas; see [[Concept - Autoscaling LLM Inference]]) or a provider-side event (wait or fail over). → *Deviation:* if both rise identically, suspect network/gateway-hop latency, not the model.

4. **Cost spike → check tokens/req before assuming abuse.** Pull tokens/req for the affected window. If it jumped, look for a retry storm (duplicate request IDs), a [[Concept - Prompt Injection|prompt-injection]] token-amplification attack (an injected instruction telling the model to repeat text or loop), or one tenant's traffic dominating. → *Expected:* one of the three explains most of the delta. → *Deviation:* if tokens/req is flat but call volume spiked, it's a traffic/capacity incident, not a cost-engineering one.

5. **Quality complaint → diff against the golden set now.** Run the stored golden-set prompts against the live endpoint and diff outputs (embedding similarity or an [[Concept - LLM-as-Judge|LLM-as-judge]] score) against the last known-good baseline. Then line up the divergence timestamp with your own deploy log and, where visible, the provider's response `system_fingerprint`/model id. → *Expected:* the divergence matches either your own [[Concept - Model Lifecycle and Versioning|prompt/config deploy]] (roll it back) or no deploy on your side, which means the provider changed something under you (see [[Lore - When the Model Changed Under You]]). → *Deviation:* the golden set shows no divergence but real users still complain. The golden set doesn't cover the failing input segment; widen it after the incident.

6. **Safety incident → contain before you diagnose.** Flip the per-feature kill switch, tighten or add guardrails, and block the offending input pattern at the gateway. Preserve full traces and request IDs for the affected window before sampled retention ages them out. The postmortem and any compliance review will need that evidence.

7. **Apply the matching mitigation lever.** Every branch above ends in one of: gateway failover, degrading to a smaller/cheaper model ([[Concept - Model Routing and Cascades|routing to an alternate model]]), cache-only/static-fallback mode, raising or lowering rate limits, or a feature kill switch. Use the narrowest lever that stops the bleeding. A full kill switch is the last resort.

## Verification

Recovery counts only when **all** of these hold: the error budget has stopped burning, p99 latency is back under [[Reference - LLM Production SLOs and Latency Budgets|SLO]], cost/req is back to its pre-incident baseline, and the golden-set diff score is inside its normal band. "The dashboard looks better" doesn't count. Hold the mitigation through at least one full traffic cycle including peak load before declaring it resolved. LLM incidents, provider-side drift in particular, can be intermittent across the request distribution, and a fix that looks stable off-peak can regress under load.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| 429/5xx spike, single provider | Provider outage or rate-limit ceiling hit | Step 2: gateway failover |
| 429/5xx spike, all providers | Your own retry storm amplifying a blip | Kill the retry loop, add full jitter, check breaker state |
| TTFT up, TPOT flat | Queue depth / undercapacity | Scale replicas ([[Concept - Autoscaling LLM Inference]]) |
| TPOT up, TTFT flat | Decode-side saturation or provider model swap | Check provider status; consider routing to an alternate model |
| Cost/req up, tokens/req flat | Traffic volume increase | Treat as capacity/abuse, not a token-cost bug |
| Cost/req up, tokens/req up | Retry storm, injection loop, or single-tenant abuse | Cap per-tenant tokens ([[Snippet - Token Cost Attribution and Budget Enforcement]]); apply loop-depth limits |
| Golden-set diverges, deploy log shows a change | Your own regression | Roll back the prompt/model/config version |
| Golden-set diverges, no deploy on your side | Silent provider-side model change | Re-verify pinned snapshot; escalate to provider |
| User complaints, golden set clean | Golden set doesn't cover the failing segment | Widen golden set; treat as input-distribution drift ([[Concept - Production Monitoring and Drift Detection]]) |

## Connections

- [[Concept - LLMOps]] — this playbook operationalizes the "observe → iterate" half of the LLMOps loop under incident conditions.
- [[Pattern - Resilient LLM Request Handling]] — supplies the fallback chain, circuit breaker, and retry discipline this playbook triggers in step 2.
- [[Checklist - Production LLM Launch Readiness]] — the pre-wired levers (kill switch, fallback, budgets) this playbook assumes exist before an incident starts.
- [[Concept - Production Monitoring and Drift Detection]] — the proxy signals and canary probing that should have raised the alert triggering this playbook.
- [[Lore - When the Model Changed Under You]] — the war stories behind step 5's "no deploy on your side" branch.
- [[Concept - Prompt Injection]] — the attack behind the token-amplification cost-spike branch in step 4.
- [[Reference - LLM Production SLOs and Latency Budgets]] — defines the latency/error-budget targets Verification checks against.
- [[Gotchas - LLM Production Operations]] — the individual pitfall signatures (retry storms, false cache hits, alias drift) each branch in this playbook is designed to catch.
- [[Concept - LLM-as-Judge]] — the scoring mechanism used to make the golden-set diff in step 5 quantitative rather than eyeballed.
- [[Concept - Autoscaling LLM Inference]] — the fix path when triage isolates a TTFT/capacity problem in step 3.
- [[Concept - Model Routing and Cascades]] — the "degrade to a cheaper/alternate model" lever applied in step 7.
- [[Snippet - Token Cost Attribution and Budget Enforcement]] — the per-tenant cap mechanism applied when step 4 isolates a cost-spike branch.
- [[Concept - Model Lifecycle and Versioning]] — the version triple (model, prompt, config) that step 5's deploy-log correlation depends on.

## Sources
- Chen, L., Zaharia, M., & Zou, J. (2023) — "How Is ChatGPT's Behavior Changing over Time?" — the empirical basis for treating provider-side drift as a real, detectable incident class rather than a hypothetical.
- OpenAI and Azure OpenAI model deprecation/retirement documentation (ongoing, as of 2026) — the sunset-schedule mechanics behind the forced-migration scenario referenced in step 5.
- LiteLLM and Portkey gateway community postmortems (as of 2026) — the fallback/circuit-breaker/kill-switch lever set this playbook draws its "when it goes wrong" table from.
