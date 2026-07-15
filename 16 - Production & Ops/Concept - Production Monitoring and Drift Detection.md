---
tags: [concept, domain/production-ops, level/frontier]
aliases: [drift detection, model monitoring, LLM drift, canary probing, PSI]
summary: "Detecting quality and behavior drift in production LLM systems with no ground-truth label: proxy signals, canary probes, change detection."
---

# Concept - Production Monitoring and Drift Detection

> **One-paragraph hook:** In classical ML you monitor drift against labels — accuracy fell, alert. In production LLM systems there is no label: nobody tells you the answer was wrong, the "model" is often a third-party API that can change under you, and every output is non-deterministic so no single sample is signal. Monitoring therefore becomes the art of watching *proxy* behavioral signals for a *distribution* shift, running a fixed canary probe to isolate model change from input change, and doing statistical change-detection that doesn't fire on noise. Teams that skip it discover regressions from angry users instead of dashboards.

## The mechanism

**Monitor proxy signals, because there is no ground truth.** You cannot measure correctness online, so you track behavioral surrogates whose *distributions* move when quality moves:

- **Output shape:** length distribution (token count), JSON/schema-valid rate, format-conformance rate.
- **Model behavior:** refusal/decline rate, tool-call error rate, empty/truncated-completion rate, `finish_reason` mix.
- **System:** latency (TTFT/TPOT), cost per request, cache-hit rate.
- **Human-in-the-loop:** thumbs-down rate, regeneration rate, human-escalation/handoff rate — the closest thing to a label you get for free.

These come off your traces ([[Concept - LLM Observability and Tracing]]) and each is a time series you can put a detector on.

**Distinguish the drift *source*, because each has a different fix:**

| Source | Signature | Fix |
|---|---|---|
| Silent provider model update | canary diff moves with model id *pinned* | pin dated snapshot / migrate ([[Lore - When the Model Changed Under You]]) |
| Your prompt/config deploy | step change at deploy time | roll back; gate with eval ([[Concept - Prompt Evaluation and Versioning]]) |
| Input-distribution shift | input embeddings drift, outputs follow | it's a data change, not a model bug |
| RAG-corpus change | retrieval hit-rate / context shifts | re-index / re-eval retrieval |
| Cache pollution | hit-similarity distribution degrades | purge / re-key the cache |

**Canary probing isolates model drift from everything else.** Run a *fixed* golden set of prompts on a schedule (hourly/daily) against the live endpoint and diff each output against a stored baseline — by embedding similarity and/or an LLM judge. Because the input is held constant, a canary shift can *only* mean the model/backend changed. This catches a silent provider update even when the model id string is pinned (the provider swapped hardware or a system default). It is the one signal that cleanly separates "the model changed" from "the traffic changed."

**Statistical change-detection, not single-sample alarms.** Outputs are non-deterministic, so you alert on a windowed distribution shift, never one sample:

- **Population Stability Index (PSI)** for a metric binned against a baseline:
$$\text{PSI} = \sum_i (a_i - e_i)\,\ln\frac{a_i}{e_i}$$
  where $e_i$ = baseline fraction in bin $i$, $a_i$ = current fraction. Classical thresholds: $<0.1$ no shift, $0.1\text{–}0.25$ moderate, $>0.25$ significant. Standard tool for length/refusal-rate distribution shift.
- **CUSUM** control chart to catch small *persistent* shifts faster than a Shewhart chart: $S_t = \max(0,\, S_{t-1} + (x_t - \mu_0 - k))$, alarm when $S_t > h$. Ideal for a slow quality creep that a threshold alert would miss.

See [[Concept - Statistical Rigor in Model Evaluation]] for why the window and the confidence interval, not the point estimate, are what you act on.

```
proxy metrics ─┐
canary diffs  ─┼─▶ windowed detector ─▶ change? ─▶ classify source ─▶ page/rollback
online judge  ─┘   (PSI / CUSUM /         │no
                    control chart)         └─▶ update baseline
```

**Online eval as a first-class signal.** Run an async LLM judge ([[Concept - LLM-as-Judge]]) on sampled live traffic and track the score *trend* — with the caveat that the judge itself can drift (a provider update to the judge model shifts your quality metric with zero change to the system under test), so version-pin and periodically re-validate the judge ([[Concept - Meta-Evaluation of LLM Judges]]).

## In practice

Wire proxy metrics as first-class dashboards sliced by prompt version and model id (so a regression bisects to a deploy). Cadence: real-time alerts on latency/error/cost, hourly-to-daily windows for behavioral distributions, scheduled canary runs. Tooling: Langfuse / Arize Phoenix for LLM traces and online scores; Evidently and WhyLabs bring classical drift statistics (PSI, distribution tests) to the proxy metrics. This monitoring is the sensor that gates [[Concept - Model Deployment Patterns for LLMs]] (canary/shadow rollout) and trips [[Playbook - Incident Response for LLM Systems]].

## Failure modes

- **Alert fatigue from noise.** Treating [[Concept - Nondeterminism in Production LLM Serving]] as signal — alerting on single samples — trains the team to ignore the pager. *Fix:* windowed detectors with tuned thresholds; alert on distributions.
- **No stored baseline.** You notice something feels off but have nothing to diff against, so you can't tell drift from your imagination. *Fix:* snapshot a golden baseline at every known-good release.
- **Monitoring latency but never quality.** The SRE dashboards are green while output quality quietly rots, because nobody put a quality signal on a chart.
- **Misattributing input drift as model drift.** A new user segment shifts inputs; you "fix" the model/prompt and make it worse. *Fix:* the fixed-input canary — if the canary is stable, the model didn't move, so look at inputs.

## The non-obvious

**Only a constant-input probe can attribute drift; production metrics alone cannot.** Every proxy metric on live traffic is a convolution of two moving things — the input distribution and the model's behavior. When refusal rate jumps, you genuinely cannot tell from that number whether the model got more cautious or your users started asking edgier questions. The single highest-leverage piece of monitoring is therefore the boring one: a fixed golden prompt set replayed on a schedule. Holding the input constant collapses the ambiguity — any movement is now unambiguously the model/backend. Teams over-invest in fancy live-traffic dashboards and under-invest in the canary, then spend an incident arguing about causation they could have designed away. And the second-order trap: your *judge* is also a model, so an online-eval score drop can mean the system regressed **or** the judge did — a monitoring system that doesn't version-pin and canary its own judge will eventually chase a phantom regression that was really a silent update to the grader.

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
