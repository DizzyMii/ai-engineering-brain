---
tags: [concept, domain/production-ops, level/frontier]
aliases: [drift detection, model monitoring, LLM drift, canary probing, PSI]
summary: "Detecting quality and behavior drift in production LLM systems with no ground-truth label: proxy signals, canary probes, change detection."
---

# Concept - Production Monitoring and Drift Detection

> **One-paragraph hook:** Classical ML monitors drift against labels: accuracy fell, alert. Production LLM systems have no label. Nobody tells you the answer was wrong, the "model" is often a third-party API that can change under you, and every output is non-deterministic, so no single sample is signal. Monitoring becomes three jobs: watch *proxy* behavioral signals for a *distribution* shift, run a fixed canary probe to separate model change from input change, and use statistical change detection that doesn't fire on noise. Teams that skip it hear about regressions from angry users instead of dashboards.

## The mechanism

### Proxy signals

You can't measure correctness online, so you track behavioral surrogates whose *distributions* move when quality moves:

- **Output shape:** length distribution (token count), JSON/schema-valid rate, format-conformance rate.
- **Model behavior:** refusal/decline rate, tool-call error rate, empty/truncated-completion rate, `finish_reason` mix.
- **System:** latency (TTFT/TPOT), cost per request, cache-hit rate.
- **Human-in-the-loop:** thumbs-down rate, regeneration rate, human-escalation/handoff rate. This is the closest thing to a label you get for free.

All of these come off your traces ([[Concept - LLM Observability and Tracing]]), and each is a time series you can put a detector on.

### Where the drift came from

Each source has a different fix:

| Source | Signature | Fix |
|---|---|---|
| Silent provider model update | canary diff moves with model id *pinned* | pin dated snapshot / migrate ([[Lore - When the Model Changed Under You]]) |
| Your prompt/config deploy | step change at deploy time | roll back; gate with eval ([[Concept - Prompt Evaluation and Versioning]]) |
| Input-distribution shift | input embeddings drift, outputs follow | it's a data change, not a model bug |
| RAG-corpus change | retrieval hit-rate / context shifts | re-index / re-eval retrieval |
| Cache pollution | hit-similarity distribution degrades | purge / re-key the cache |

### Canary probes

Run a *fixed* golden set of prompts against the live endpoint on a schedule (hourly/daily) and diff each output against a stored baseline, by embedding similarity, an LLM judge, or both. The input is held constant, so a canary shift can *only* mean the model or backend changed. It catches a silent provider update even when the model id string is pinned (the provider swapped hardware or a system default). No other signal cleanly separates "the model changed" from "the traffic changed."

### Change detection over windows

Outputs are non-deterministic, so alert on a windowed distribution shift and never on one sample.

- **Population Stability Index (PSI)** for a metric binned against a baseline:
$$\text{PSI} = \sum_i (a_i - e_i)\,\ln\frac{a_i}{e_i}$$
  where $e_i$ = baseline fraction in bin $i$, $a_i$ = current fraction. Classical thresholds: $<0.1$ no shift, $0.1\text{–}0.25$ moderate, $>0.25$ significant. The standard tool for length or refusal-rate distribution shift.
- **CUSUM** control chart, which catches small *persistent* shifts faster than a Shewhart chart: $S_t = \max(0,\, S_{t-1} + (x_t - \mu_0 - k))$, alarm when $S_t > h$. Good for a slow quality creep a threshold alert would miss.

[[Concept - Statistical Rigor in Model Evaluation]] explains why you act on the window and the confidence interval, not the point estimate.

```
proxy metrics ─┐
canary diffs  ─┼─▶ windowed detector ─▶ change? ─▶ classify source ─▶ page/rollback
online judge  ─┘   (PSI / CUSUM /         │no
                    control chart)         └─▶ update baseline
```

### Online eval

Run an async LLM judge ([[Concept - LLM-as-Judge]]) on sampled live traffic and track the score *trend*. The judge can drift too: a provider update to the judge model shifts your quality metric with zero change to the system under test. Version-pin it and re-validate it periodically ([[Concept - Meta-Evaluation of LLM Judges]]).

## In practice

Put the proxy metrics on dashboards sliced by prompt version and model id, so a regression bisects to a deploy. Cadence: real-time alerts on latency, errors and cost; hourly-to-daily windows for behavioral distributions; scheduled canary runs. For tooling, Langfuse and Arize Phoenix handle LLM traces and online scores, and Evidently and WhyLabs bring classical drift statistics (PSI, distribution tests) to the proxy metrics. This monitoring is the sensor that gates [[Concept - Model Deployment Patterns for LLMs]] (canary/shadow rollout) and trips [[Playbook - Incident Response for LLM Systems]].

## Failure modes

- **Alert fatigue from noise.** Treating [[Concept - Nondeterminism in Production LLM Serving]] as signal, i.e. alerting on single samples, trains the team to ignore the pager. *Fix:* windowed detectors with tuned thresholds; alert on distributions.
- **No stored baseline.** Something feels off but there's nothing to diff against, so you can't tell drift from your imagination. *Fix:* snapshot a golden baseline at every known-good release.
- **Monitoring latency but never quality.** The SRE dashboards stay green while output quality rots, because nobody charted a quality signal.
- **Blaming the model for input drift.** A new user segment shifts inputs; you "fix" the model or prompt and make it worse. *Fix:* the fixed-input canary. If it's stable, the model didn't move, so look at inputs.

## The non-obvious

**Only a constant-input probe can attribute drift. Production metrics alone can't.** Every proxy metric on live traffic mixes two moving things, the input distribution and the model's behavior. When refusal rate jumps, that number can't tell you whether the model got more cautious or your users started asking edgier questions. So the most valuable piece of monitoring is the boring one: a fixed golden prompt set replayed on a schedule. With the input held constant, any movement is the model or backend. Teams over-invest in live-traffic dashboards, under-invest in the canary, and then spend an incident arguing about causation they could have designed away.

The second-order trap: your *judge* is also a model. An online-eval score drop can mean the system regressed **or** the judge did. A monitoring setup that doesn't version-pin and canary its own judge will eventually chase a phantom regression that was a silent update to the grader.

## Connections
- [[Concept - LLM Observability and Tracing]] — the telemetry layer that produces every signal this note detects on; monitoring is the analysis tier over that raw capture.
- [[Lore - When the Model Changed Under You]] — the war stories that justify canary probing; silent provider drift is the headline threat.
- [[Concept - Statistical Rigor in Model Evaluation]] — supplies the windowing, confidence-interval, and significance discipline that keeps drift alerts from firing on noise.
- [[Concept - LLM-as-Judge]] — the online-eval scorer that turns quality into a trackable metric on sampled traffic.
- [[Concept - Meta-Evaluation of LLM Judges]] — because the judge drifts too; you must monitor the monitor.
- [[Concept - Model Deployment Patterns for LLMs]] — canary/shadow rollouts consume these drift signals as their automatic-rollback gates.
- [[Playbook - Incident Response for LLM Systems]] — a drift alert is often the first trigger of the runbook; this note is its detection front-end.
- [[Concept - Prompt Evaluation and Versioning]] — distinguishing a prompt-deploy regression from provider drift requires versioned prompts tied to eval scores.
- [[Concept - Nondeterminism in Production LLM Serving]] — the reason single-sample monitoring is meaningless and why detectors must be distributional.

## Sources
- Chen, Zaharia & Zou (2023) — *How Is ChatGPT's Behavior Changing over Time?* Empirical demonstration of silent snapshot drift; methodologically debated but the motivating case.
- Karnin, Lin et al. / AWS (2020) — *PSI and population-stability monitoring* as productionized in SageMaker Model Monitor; the classical drift-stat lineage borrowed here.
- Page, E. S. (1954) — *Continuous Inspection Schemes* (CUSUM). The change-detection algorithm for catching small persistent shifts.
