---
tags: [gotchas, domain/inference-serving, level/core]
aliases: [LLM serving pitfalls, production inference gotchas]
summary: "Seven pitfalls that bite real LLM deployments, from throughput collapse to silent nondeterminism, ordered by how much pain they cause."
---

# Gotchas - LLM Serving in Production

## 1. Throughput collapse under memory pressure

**Symptom:** fine at moderate load, then as concurrency rises throughput *falls* instead of plateauing, and TPOT (time-per-output-token) spikes non-linearly. Requests that were streaming smoothly start stalling for hundreds of milliseconds at a time.
**Cause:** `max_num_seqs` (or an equivalent concurrency cap) is set higher than the [[Concept - KV Cache]] budget can hold. Live sequences pile up, the KV cache fills, and the scheduler starts **preempting** running requests: it evicts their KV blocks to make room, then recomputes the evicted prefill (or swaps it to host memory and back) once space frees up. Each preemption throws away finished compute and redoes it, so the GPU burns cycles on recomputation instead of progress. It's the serving-side mirror of the fragmentation problem [[Concept - PagedAttention]] solved for allocation. You can allocate perfectly and still run out of the resource.
**Fix:** lower `max_num_seqs` (or the per-iteration token budget) so the KV budget covers worst-case concurrent context length with margin, or reserve a larger fraction of [[Concept - GPU Memory Hierarchy|HBM]] for KV (e.g. vLLM's `gpu-memory-utilization`). If that still leaves too little headroom, shrink `max_model_len` or switch to a KV-quantized cache ([[Concept - KV Cache Quantization]]) to fit more tokens per byte.
**Detection:** graph preemption/recompute count next to throughput. A preemption counter that goes positive right where throughput bends over is the unambiguous signature. Latency alone won't tell you; it's a downstream symptom of a memory-accounting problem upstream.

## 2. Chat-template / tokenizer mismatch degrades quality silently

**Symptom:** the model answers, the server never errors, smoke tests pass. Quality is still subtly worse than the same weights served elsewhere: slightly off-topic completions, ignored system instructions, instruction-following that's worse in ways nobody can pin down.
**Cause:** the rendered prompt doesn't match what the model was fine-tuned on. Two classic versions. One is the wrong chat template: a Llama-3 template on a Qwen checkpoint, or a stale template cached from an earlier model version. The other is a doubled BOS token, added once by the tokenizer's own `add_bos_token` and again by the template string, so the model sees `<s><s>System: ...` instead of `<s>System: ...`. Neither crashes. Both push the model off the distribution it was trained on.
**Fix:** before shipping, render a prompt through the exact serving path and diff it byte-for-byte against the model card's reference template, and assert BOS appears exactly once. Pin the template as an immutable artifact next to the weights, not as a mutable config default.
**Detection:** the hardest one here to catch from the *outside*, because output looks plausible and smoke tests miss it. What works is a template diff test in CI plus a small fixed eval set whose answers depend on instruction-following. A regression on that set with unchanged weights points straight here.

## 3. Runaway generation from misconfigured stop handling

**Symptom:** some fraction of requests run all the way to `max_tokens` on every call, pushing up latency and burning tokens (and money) for nothing. Or the reverse: output is cut one character early, or a stop string shows up in the response.
**Cause:** stop conditions are checked three ways: EOS token id, `max_tokens`, and stop strings. Stop strings are matched against **detokenized text**, not token ids, because a sequence like `"\n\n"` or `"</tool>"` can straddle a token boundary (see [[Concept - Streaming Detokenization]]). A missing or wrong EOS id, common after a fine-tune changes the special-token set without an update to the serving config, means the model never signals "done." Every request rides to the `max_tokens` ceiling, a slow, expensive failure that looks like normal traffic in aggregate metrics. A stop-string matcher that buffers too little trailing text either misses the match and leaks the stop string, or trims one character too many.
**Fix:** check that the EOS id being tested matches the model's real EOS token (diff the tokenizer config against the model card). Test stop strings that deliberately straddle a token boundary, not only ones that line up with single tokens.
**Detection:** an output-length histogram with an anomalous spike right at `max_tokens` means missing EOS. A stop-string integration test using adversarial multi-token boundaries catches the other half.

## 4. Streaming corruption from unbuffered multi-byte characters

**Symptom:** streamed responses show flickering replacement glyphs (`�`), broken emoji, or garbled CJK that "fixes itself" a moment later, or missing/doubled spaces at token boundaries. The final complete response, if you wait for it, is correct.
**Cause:** byte-level BPE tokens are byte sequences, not characters, so one emoji or CJK glyph frequently spans 2-4 tokens. A naive incremental decoder that decodes and emits each new token id on its own will eventually try to decode a partial UTF-8 sequence and get garbage. [[Concept - Streaming Detokenization]] has the full mechanism, including the SentencePiece meta-space marker behind the spacing variant.
**Fix:** buffer incomplete multi-byte sequences and flush only complete UTF-8 code points to the client. Every mature serving framework does this as basic correctness. Custom or hand-rolled streaming code (a thin wrapper around a raw generate loop) gets it wrong constantly.
**Detection:** stream a prompt guaranteed to produce CJK or emoji and look for replacement characters in the raw SSE payload. A non-streaming eval can't see this bug, and it only appears under real streaming traffic, so it reaches production often.

## 5. Prefix-cache correctness busts and cross-tenant leakage

**Symptom:** [[Concept - Automatic Prefix Caching]] hit rate is far below what prompt similarity predicts, and TTFT doesn't improve the way capacity planning assumed. In the worse case, a security review finds that response timing differs measurably depending on whether *another tenant's* prompt shares a prefix with the current one.
**Cause:** prefix matching is on exact token IDs. One differing token near the **front** of the prompt (a timestamp, a request id, a per-user field injected early in the system prompt) busts every downstream block's hash and forces full recompute. Variable content anywhere else still lets the cache help; put it first and the cache never fires. The leakage variant: a naive cache shared globally across tenants makes a request measurably faster when its prefix is already cached. That's a timing side channel revealing whether another tenant has sent that exact prefix.
**Fix:** build prompts with static content first (system prompt, tool schema, few-shot exemplars) and variable content last (user turn, timestamps, ids). In any multi-tenant deployment, scope prefix caches per tenant or per API key.
**Detection:** measure hit rate on a synthetic workload with a known shareable prefix. A hit rate far below the shareable fraction means something at the front varies. For leakage, run a timing-based isolation test: does latency for tenant A's request depend on tenant B's earlier traffic?

## 6. Latency jitter from prefill stalling the decode batch

**Symptom:** inter-token latency for in-flight streams is smooth, then spikes for one or two steps whenever new requests join the batch. Many concurrent users see periodic stutter at once; it isn't one bad request.
**Cause:** in plain [[Concept - Continuous Batching]], admitting a long-prompt request runs its whole [[Concept - Prefill and Decode Phases|prefill]] as one forward pass in the same iteration as every decoding request. Prefill is a large compute-bound pass, so it takes over the GPU for that iteration and every decoding request's token for that step is late. Long context makes it worse: prefill scales roughly with $O(P^2)$ in the attention term, so one big prompt makes one iteration disproportionately slow.
**Fix:** turn on [[Concept - Chunked Prefill]]. Long prefills get sliced into a bounded per-iteration token budget and interleaved with in-flight decode tokens. Tune the budget down for smoother decode or up for faster prefill, depending on which side of the SLO is under pressure.
**Detection:** plot per-step TPOT and line up the spikes with request-admission events in the scheduler log. Jitter that tracks new-request arrivals, instead of being spread evenly, is the tell, and it's different from the steady-state degradation of gotcha #1.

## 7. Silent nondeterminism breaks evals and caching

**Symptom:** the same request, same seed, same `temperature=0`, gives a different token stream on two calls. Or an eval that scores a model on Monday gives a measurably different number on Tuesday with no code change.
**Cause:** "temperature 0 means deterministic" is true of the math and false of the server. GPU kernel reductions (matmul, attention, norm) sum in an order that depends on data and batch, and floating-point addition isn't associative. Identical logical inputs can produce different bit patterns depending on what else is in the batch at that moment. [[Concept - Nondeterminism in LLM Inference]] has the full mechanism, including why batch-variant kernels, more than atomic-add races, are the dominant cause.
**Fix:** if evals or caching need reproducibility, either accept it's approximate and cache by prompt+params without expecting byte-identical output, or move to batch-invariant kernels at a measured throughput cost. Most production stacks take the first option and control nondeterminism only where it bites (golden-set evals, cache keys).
**Detection:** send the identical request N times under realistic concurrent load, not in isolation, and diff the outputs. Stable isolated calls plus unstable concurrent ones confirm batch variance, not a code bug.

## Connections
- [[Concept - KV Cache]] — the resource whose exhaustion drives gotcha #1's preemption spiral.
- [[Concept - Continuous Batching]] — the scheduling mechanism whose interaction with prefill produces gotcha #6's jitter.
- [[Concept - Chunked Prefill]] — the direct fix for gotcha #6, trading a tunable budget for smoother decode latency.
- [[Concept - Automatic Prefix Caching]] — the mechanism whose correctness and isolation properties gotcha #5 depends on.
- [[Concept - Streaming Detokenization]] — the deeper mechanism behind gotcha #4's multi-byte corruption and part of gotcha #3's stop-string handling.
- [[Concept - Nondeterminism in LLM Inference]] — the full explanation of gotcha #7, including why it's a batch-variance problem, not just a floating-point curiosity.
- [[Concept - Sampling and Decoding Parameters]] — the surface-level entry point this note assumes; sampling misconfiguration compounds with several gotchas here (notably #3 and #7).
- [[Concept - LLM Observability and Tracing]] — cross-domain (16) grounding for the metrics (preemption count, TPOT, cache hit rate) every detection method here depends on.
- [[Concept - GPU Memory Hierarchy]] — cross-domain (08) grounding for why KV exhaustion in gotcha #1 is a hardware-capacity problem, not just a config mistake.

## Sources
- Kwon et al. (2023) — *Efficient Memory Management for Large Language Model Serving with PagedAttention* (SOSP 2023). Establishes the KV-fragmentation baseline that preemption-under-pressure (gotcha #1) is the runtime analog of.
- Agrawal et al. (2023) — *SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills*. The mechanism behind gotcha #6's fix.
