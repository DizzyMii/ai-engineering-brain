---
tags: [reference, domain/production-ops, level/unicorn]
aliases: [SLO, latency budget, SLA, TTFT target, TPOT target, error budget]
summary: "The real latency/SLO targets and budget decompositions teams hold for LLM apps by use case — the tribal numbers rarely written down."
---

# Reference - LLM Production SLOs and Latency Budgets

## Latency targets by use case (as of 2026)

| Use case | TTFT target¹ | TPOT / token rate² | End-to-end feel | Notes |
|---|---|---|---|---|
| Realtime voice | 300–500 ms | ≤ speech rate, ~50–80 ms (≥12–20 tok/s) | must not stall the TTS pipeline | TTFT is the hard constraint; barge-in/turn-taking budget is tighter than chat |
| Interactive chat | < 1 s (good), < 2 s (acceptable) | 20–50 ms (20–50 tok/s) | fluid if streaming | streaming hides total generation time behind reading |
| Coding / autocomplete | 200–500 ms | n/a (short completion) | must beat the keystroke | latency-critical, throughput-trivial |
| Agentic / tool-use | 2–10 s per step | tolerant | seconds per hop acceptable | user expects "thinking"; total = steps × per-step |
| RAG Q&A | < 2–3 s | 20–50 ms | retrieval adds to prefill budget | retrieval + rerank eats 100–400 ms before the model call |
| Batch / async | seconds–minutes | irrelevant | offline | optimize throughput/cost, not latency; Batch API ~50% cheaper |

¹ TTFT = time to first token, including queue wait + prefill. With streaming this is the *perceived* latency.
² TPOT = time per output token (inter-token latency). Token rate = 1/TPOT.

## Token rate vs. perceived speed

| Rate | TPOT | Perception |
|---|---|---|
| ~5–8 tok/s | ~125–200 ms | ≈ human reading speed (~200–300 wpm, 1 tok ≈ 0.75 word); *at* the threshold, feels laggy |
| 20–50 tok/s | 20–50 ms | reads as fluid; output outruns the eye, total generation time is hidden |
| 100+ tok/s | < 10 ms | imperceptibly fast; only matters for non-streamed / programmatic consumers |

**Rule:** below reading speed the stream feels slow *regardless of total latency*. Above it, users only perceive TTFT and total length, so TTFT is the number to defend for interactive UX. (Perceptual thresholds trace to Miller 1968 / Nielsen 1993: 0.1 s = instantaneous, 1 s = flow unbroken, 10 s = attention lost.)

## End-to-end budget decomposition (worked example)

Target: **p95 end-to-end ≤ 2000 ms**, chat with RAG, ~200 output tokens.

| Segment | Budget | Notes |
|---|---|---|
| Client ↔ edge network RTT | 40 ms | geography-dependent; add ~80–150 ms cross-region |
| Gateway / proxy hop | 10 ms | [[Concept - LLM Load Testing and Capacity Planning]] sizes this under load |
| Input guardrail + retrieval | 150 ms | embed + ANN search + rerank |
| Queue wait (at target load) | 80 ms | grows without bound past the latency knee |
| **Prefill → TTFT** | 350 ms | scales with input length (context + retrieved chunks) |
| **Decode** | 500 ms | 200 tokens × 25 ms TPOT |
| Output guardrail / parse / detokenize | 60 ms | streaming detokenization is cheap |
| **Total** | **~1190 ms** | ~810 ms headroom for the tail |
| *Perceived (TTFT budget)* | **~630 ms** | network + gateway + guardrail + queue + prefill; decode is hidden behind reading |

Two lines dominate. **Prefill**: cut it with prompt/[[Concept - KV Cache]] reuse and shorter context. **Decode**: cut it with [[Concept - Speculative Decoding]], a faster GPU, or fewer output tokens. The rest is rounding error unless a hop is broken.

## Throughput / cost anchors (as of 2026, folklore-grade³)

| Model class | Single-stream decode | Batched aggregate (1 GPU/replica) | Concurrency at knee |
|---|---|---|---|
| ~8B, H100, fp16/fp8 | ~100–150 tok/s | ~2,000–5,000+ tok/s | tens–low hundreds |
| ~70B, H100(s), fp8 | ~20–40 tok/s | few hundred – ~1–2k tok/s | tens |
| Frontier hosted API | provider-managed | provider-managed | governed by your TPM/RPM tier, not GPUs |

³ Order-of-magnitude sizing rules of thumb, **not guarantees**. They swing with quantization, context length, [[Concept - Continuous Batching]] settings and silicon generation. Measure your own; see [[Concept - LLM Load Testing and Capacity Planning]].

## Availability targets & error budget

| SLO | Downtime / 30-day month | Downtime / year |
|---|---|---|
| 99.0% | 7.2 h | 3.65 days |
| 99.5% | 3.6 h | 43.8 h |
| 99.9% | 43.2 min | 8.76 h |
| 99.95% | 21.6 min | 4.38 h |
| 99.99% | 4.32 min | 52.6 min |

**Error budget** = $(1 - \text{SLO}) \times \text{period}$. At 99.9% monthly you get **43.2 min** to spend on deploys, provider blips and incidents. Burn it and risky changes freeze ([[Playbook - Incident Response for LLM Systems]] tracks the burn during an incident).

**Provider reality:** major LLM provider APIs have historically run at roughly 99.x% with occasional multi-hour outages. One upstream *cannot* underwrite a 99.9%+ app SLO. Multi-provider fallback buys a higher tier: two independent providers at 99.5% each are only down when both fail at once, which (assuming independence + instant failover) gives $1 - (0.005)^2 = 99.9975\%$. The catch is independence. Shared cloud regions and correlated capacity crunches break it, so discount the compound number. [[Concept - Autoscaling LLM Inference]] and load-test-driven headroom cover the self-inflicted side of the budget.

## Connections
- [[Concept - LLM Load Testing and Capacity Planning]] — how you *measure* these targets and size capacity to hold them; this note is the target, that note is the method.
- [[Playbook - Incident Response for LLM Systems]] — the runbook consumes these SLOs as the thresholds that define "we are in an incident" and the error budget it burns.
- [[Concept - Autoscaling LLM Inference]] — a TTFT-SLO breach is a scaling signal; the availability tier depends on warm-floor headroom.
- [[Concept - KV Cache]] — KV reuse is a primary lever on the prefill/TTFT line of the budget.
- [[Concept - Continuous Batching]] — sets where the latency knee sits, which caps the concurrency the budget assumes.
- [[Concept - Speculative Decoding]] — the main lever for cutting the decode/TPOT line without a bigger GPU.
- [[Concept - The Memory Wall]] — explains *why* TPOT has a hard bandwidth-bound floor these budgets must respect.

## Sources
- Miller, R. B. (1968) — *Response Time in Man-Computer Conversational Transactions*; Nielsen, J. (1993) — *Response Times: The 3 Important Limits*. The 0.1 s / 1 s / 10 s perceptual thresholds behind the chat/voice targets.
- Google SRE Book (Beyer et al. 2016) — SLO and error-budget framing adapted here to LLM availability.
