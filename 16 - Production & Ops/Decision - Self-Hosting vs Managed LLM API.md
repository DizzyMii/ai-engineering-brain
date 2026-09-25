---
tags: [decision, domain/production-ops, level/frontier]
aliases: [build vs buy for LLM inference, on-prem LLM serving, self-hosted inference]
summary: "Choosing a managed LLM API vs serving open-weights models on your own GPUs, decided by a GPU-utilization breakeven calculation."
---
# Decision - Self-Hosting vs Managed LLM API

> Default for the 80% case: **start on a managed API. Move to self-hosting only when volume is high and steady enough to keep GPUs busy most of the time, compliance forces on-prem, or you need an open/custom model with no closed-frontier equivalent.** The naive version compares $/token. The actual decision is a bet on utilization, and idle GPUs are how teams lose it.

## Decision flow

```mermaid
flowchart TD
    A[New or growing LLM workload] --> B{Data residency /\ncompliance requires on-prem?}
    B -->|Yes| G[Self-host]
    B -->|No| C{Need open weights, a\ncustom fine-tune, or many\nLoRA adapters with no\nclosed-frontier equivalent?}
    C -->|Yes| G
    C -->|No| D{Is volume high AND\nsteady/predictable\n(not spiky)?}
    D -->|No| E[Managed API]
    D -->|Yes| F{Can you sustain\n~40-60%+ GPU\nutilization?}
    F -->|No, bursty peaks| H[Hybrid: self-host a warm\nbaseline, burst-overflow to API]
    F -->|Yes, steady or batch/offline| G
    E --> I{Hitting provider rate-limit\nceilings or need burst capacity?}
    I -->|Yes| H
    I -->|No| E
```

The tree comes down to one question: **will the GPUs you'd buy or rent stay busy?** The other criteria (compliance, model choice, rate limits) either force the answer outright or feed into whether you can sustain that utilization.

## Tradeoff matrix

| Criterion | Managed API | Self-hosted (own/rented GPUs) | Hybrid |
|---|---|---|---|
| $/M tokens at low/bursty volume | Lowest; pay only for what you use | Highest; idle GPUs bill 24/7 regardless of traffic | Managed API absorbs the burst; baseline stays cheap |
| $/M tokens at high, steady volume | Fixed per-token rate, no ceiling on savings | Lowest, once utilization clears the breakeven floor | Baseline gets self-host economics, overflow pays API rate |
| Latency / tail control | Shared multi-tenant infra; you don't control the queue | Full control over batching, hardware and colocation | Full control on the baseline path only |
| Data residency / compliance | Depends on provider ZDR/DPA terms, see [[Concept - PII Redaction and Data Retention]] | Full control; data never leaves your infra | Route by sensitivity: PII on-prem, rest to API |
| Model choice | Whatever the provider ships | Any open-weights model, any custom fine-tune, any number of fine-tuned variants sharing a GPU fleet (see [[Concept - GPU Orchestration on Kubernetes]]) | Both, at the cost of running two paths |
| Ops burden | ~Zero; the provider runs the fleet | Real: serving-engine tuning, GPU fleet health, on-call | Both burdens, each at smaller scale |
| Time to first token in production | Hours (an API key) | Weeks (procurement, serving-stack setup per [[Breakdown - vLLM]], load testing) | Managed API ships first; self-host baseline added later |
| Rate-limit ceiling | Bounded by your provider tier | None beyond your own hardware | API ceiling only bites on the overflow path |

**The breakeven math.** Worth memorizing:

$$
\$/\text{M tokens}_{\text{self-host}} = \frac{\text{GPU }\$/\text{hr}}{\text{tokens/hr throughput} \times \text{utilization}} \times 10^6
$$

An illustrative order-of-magnitude example (as of 2026, not a benchmark result): an H100 at roughly \$2-3/hr, sustaining on the order of a few thousand output tokens/sec aggregate under [[Concept - Continuous Batching]] for a mid-sized open-weights model, comes out well under \$1/M output tokens at high utilization. At 20% utilization (the classic "we run it because we bought it" outcome) the same math is 4-5x worse, and a small, cheap managed model at roughly \$0.1-0.6/M output (see [[Concept - Cost Engineering for LLM Applications]]) wins outright. The picture flips hardest at the frontier end. A frontier-class API model at \$10-75/M output lets an equivalent-capability self-hosted open model pay off at a much lower utilization floor, because the API is so much more expensive per token to begin with.

## The details that flip the decision

- **Batch and offline workloads are the strongest self-host case.** Work that can be queued and processed continuously keeps utilization near 100% trivially, so the breakeven math favors self-hosting even at moderate total volume. There's no idle time to pay for.
- **Data residency and compliance override the cost math.** On-prem requirements (financial, health, government data), or provider data-handling terms that don't clear your bar, force self-hosting whatever the utilization. [[Concept - PII Redaction and Data Retention]] says what the alternative (ZDR endpoints, signed DPAs, regional residency) handles and where it falls short.
- **Provider rate-limit ceilings force the decision when volume is bursty but bounded.** A workload that sometimes needs more throughput than your tier allows can't "pay more" past a hard TPM/RPM ceiling. Self-hosting or a hybrid burst-overflow path becomes mandatory, whatever the steady-state cost.
- **Hidden self-host costs routinely eat the projected savings.** GPU-failure mean-time-to-repair, autoscaling cold starts on a fresh replica, the engineering work to actually reach the throughput the breakeven math assumed, and the ongoing cost of tracking new model releases are all real line items the naive \$/token comparison leaves out. This is the "we saved on tokens but hired an infra team and ran cards at 20%" failure, and it's the modal way this decision goes wrong in practice.
- **Hybrid is usually the mature end state.** It isn't a compromise. Self-host a steady baseline and overflow bursts to a managed API; route by data sensitivity (PII on-prem, everything else to the API); or run a cascade, with a cheap self-hosted model first and escalation to a frontier API model only when needed ([[Concept - Model Routing and Cascades]]). None of these commit you to one side permanently.

## Connections

- [[Concept - Cost Engineering for LLM Applications]] — the per-token cost model that self-hosting's breakeven math has to beat.
- [[Concept - Model Routing and Cascades]] — the hybrid pattern of cascading a self-hosted cheap model into an API frontier model, capturing most of the cost win without an all-or-nothing bet.
- [[Concept - GPU Orchestration on Kubernetes]] — the operational reality (scheduling, sharing, cold-start weight loading) behind the "ops burden" row of the tradeoff matrix.
- [[Concept - LLM Load Testing and Capacity Planning]] — how you actually find the sustained-throughput number the breakeven math depends on, rather than guessing it.
- [[Concept - PII Redaction and Data Retention]] — the compliance criteria that can force self-hosting regardless of what the utilization math says.
- [[Decision - Fine-Tuning vs RAG vs Prompting]] — a related build-vs-buy decision one layer up the stack; a custom fine-tune is one of the strongest model-choice reasons to self-host in the first place.
- [[Breakdown - vLLM]] — the serving engine that determines the actual tokens/hr throughput on the self-host side of the breakeven formula.
- [[Concept - Continuous Batching]] — the serving-side mechanism that determines how close to the theoretical peak throughput the self-host breakeven math can actually reach.
- [[Reference - Memory Math for Transformers]] — the VRAM math that determines which GPU count and class a given model even fits on before throughput is a question.
- [[Gotchas - LLM Production Operations]] — the operational pitfall catalog that documents several of the hidden self-host costs cited above from real incidents.

## Sources
This is a distilled practitioner cost/ops framework rather than a single citable result; the throughput and GPU-cost figures are order-of-magnitude cloud GPU pricing and open-weights serving benchmarks (as of 2026, volatile — re-derive at decision time rather than trusting a cached number), and the mechanism behind the self-host throughput side is covered in [[Breakdown - vLLM]] and [[Reference - Memory Math for Transformers]].
