---
tags: [gotchas, domain/inference-serving, level/core]
aliases: [LLM serving pitfalls, production inference gotchas]
summary: "Seven pitfalls that bite real LLM deployments, from throughput collapse to silent nondeterminism, ordered by how much pain they cause."
---

# Gotchas - LLM Serving in Production

## 1. Throughput collapse under memory pressure

**Symptom:** the service was fine at moderate load, then as concurrency rises throughput doesn't just plateau — it *falls*, and TPOT (time-per-output-token) spikes non-linearly. Requests that were streaming smoothly start stalling for hundreds of milliseconds at a time.
**Cause:** `max_num_seqs` (or an equivalent concurrency cap) is set higher than the [[Concept - KV Cache]] budget actually supports. As live sequences accumulate, the KV cache fills, and the scheduler starts **preempting** running requests — evicting their KV blocks to free room for others, then recomputing the evicted prefill (or swapping it to host memory and back) once room reopens. Every preemption throws away already-completed compute and redoes it, so the GPU spends cycles on recomputation instead of forward progress. This is the serving-side mirror of the fragmentation problem [[Concept - PagedAttention]] solved for allocation — you can allocate perfectly efficiently and still run out of the resource.
**Fix:** lower `max_num_seqs` (or the per-iteration token budget) so the KV budget covers the worst-case concurrent context length with margin, or raise the fraction of [[Concept - GPU Memory Hierarchy|HBM]] reserved for KV (e.g. vLLM's `gpu-memory-utilization`). If neither leaves enough headroom, shrink `max_model_len` or move to a KV-quantized cache (see [[Concept - KV Cache Quantization]]) to fit more tokens per byte.
**Detection:** graph preemption/recompute count alongside throughput — a preemption counter that turns positive at exactly the point throughput bends over is the unambiguous signature. Don't rely on latency alone; it's a downstream symptom of an upstream memory-accounting problem.

## 2. Chat-template / tokenizer mismatch degrades quality silently

**Symptom:** the model answers, the server never errors, smoke tests pass — but quality is subtly worse than the same weights served elsewhere: slightly off-topic completions, ignored system instructions, or degraded instruction-following that nobody can quite pin down.
**Cause:** the rendered prompt doesn't match what the model was fine-tuned on. The two classic variants: the wrong chat template (a Llama-3 template applied to a Qwen checkpoint, or a stale template cached from an earlier model version), and a doubled BOS token — added once by the tokenizer's own `add_bos_token` and again by the template string, so the model sees `<s><s>System: ...` instead of `<s>System: ...`. Neither crashes; both push the model off-distribution from what it was trained to expect.
**Fix:** render a prompt through the exact serving path and diff it byte-for-byte against the model card's reference template before shipping; assert BOS appears exactly once. Pin the template as an immutable artifact alongside the model weights, not as a mutable config default.
**Detection:** this is the hardest gotcha to detect from the *outside* — output looks plausible, so smoke tests miss it. The only reliable detection is a template diff test in CI plus a small fixed eval set whose expected answers are sensitive to instruction-following; a quality regression on that set with unchanged weights points straight here.

## 3. Runaway generation from misconfigured stop handling

**Symptom:** a fraction of requests generate all the way to `max_tokens` on every call, driving up latency and burning tokens (and money) for no reason — or conversely, output truncates one character early, or a stop string leaks visibly into the response.
**Cause:** stop conditions are checked three ways — EOS token id, `max_tokens`, and stop strings — and stop strings are matched against **detokenized text**, not token ids, because a stop sequence like `"\n\n"` or `"</tool>"` can straddle a token boundary (see [[Concept - Streaming Detokenization]]). A missing or wrong EOS id (common after a fine-tune that changes the special-token set without updating the serving config) means the model never signals "done," so every request rides to the `max_tokens` ceiling — a slow, expensive failure that looks like normal traffic in aggregate metrics. A stop-string matcher that doesn't buffer enough trailing text either misses the match (leaks the stop string into the visible output) or trims one character too many.
**Fix:** verify the EOS id being checked matches the model's actual EOS token (diff the tokenizer config against the model card), and test stop strings that deliberately straddle a token boundary, not just ones that align with single tokens.
**Detection:** a histogram of output lengths with an anomalous spike exactly at `max_tokens` is the signature of missing EOS; a stop-string integration test using adversarial multi-token boundaries catches the other half.

## 4. Streaming corruption from unbuffered multi-byte characters

**Symptom:** streamed responses show flickering replacement-character glyphs (`�`), broken emoji, or garbled CJK text that "fixes itself" a moment later, or spacing errors (missing or doubled spaces) at token boundaries in the streamed text — even though the final, complete response (if you wait for it) is correct.
**Cause:** byte-level BPE tokens are byte sequences, not characters, so a single emoji or CJK glyph frequently spans 2-4 tokens. A naive incremental decoder that decodes each new token id independently and emits it immediately will, at some point, try to decode a partial UTF-8 sequence and get garbage — see [[Concept - Streaming Detokenization]] for the full mechanism, including the SentencePiece meta-space marker that causes the spacing variant of this bug.
**Fix:** buffer incomplete multi-byte sequences and only flush complete UTF-8 code points to the client; this is table-stakes correctness in every mature serving framework, but custom or hand-rolled streaming code (a thin wrapper around a raw generate loop) gets it wrong constantly.
**Detection:** stream a prompt guaranteed to produce CJK or emoji output and watch for replacement characters in the raw SSE payload — this bug is invisible in a non-streaming eval and only shows up under real streaming traffic, which is why it survives into production so often.

## 5. Prefix-cache correctness busts and cross-tenant leakage

**Symptom:** [[Concept - Automatic Prefix Caching]] hit rate is much lower than expected given how similar prompts are, TTFT doesn't improve the way capacity planning assumed — or, in the worse case, a security review flags that response timing differs measurably based on whether *another tenant's* prompt happens to share a prefix with the current one.
**Cause:** prefix matching is on exact token IDs, so a single differing token near the **front** of the prompt (a timestamp, a request id, a per-user field injected early in the system prompt) busts every downstream block's hash and forces full recompute — put variable content anywhere but the front and the cache still helps; put it first and it never fires. The leakage variant: a naive cache shared globally across tenants makes a request measurably faster when its prefix already exists in the cache, which is a timing side channel that reveals whether another tenant has sent that exact prefix before.
**Fix:** reorder prompt construction so static content (system prompt, tool schema, few-shot exemplars) comes first and variable content (user turn, timestamps, ids) comes last; scope prefix caches per tenant or per API key in any multi-tenant deployment.
**Detection:** track cache hit rate against a synthetic workload with a known-shareable prefix — a hit rate far below the shareable fraction means something at the front is varying; a timing-based tenant-isolation test (does response latency for tenant A's request depend on tenant B's prior traffic) catches the leakage case.

## 6. Latency jitter from prefill stalling the decode batch

**Symptom:** inter-token latency for existing streaming requests is smooth, then periodically spikes for one or two steps, correlated with new requests joining the batch — visible as periodic stutter across many concurrent users rather than a single bad request.
**Cause:** in plain [[Concept - Continuous Batching]], admitting a request with a long prompt runs its entire [[Concept - Prefill and Decode Phases|prefill]] as one forward pass sharing the same iteration as every decoding request; because prefill is a large compute-bound pass, it monopolizes the GPU for that iteration and every decoding request's token for that step arrives late. At long context this compounds — prefill scales with roughly $O(P^2)$ in the attention term, so a big prompt makes one iteration disproportionately slow.
**Fix:** enable [[Concept - Chunked Prefill]] so long prefills are sliced into a bounded per-iteration token budget and interleaved with in-flight decode tokens instead of monopolizing an iteration; tune the budget down for smoother decode or up for faster prefill depending on which side of the SLO is under pressure.
**Detection:** plot per-step TPOT and correlate spikes against request-admission events in the scheduler log; jitter that lines up with new-request arrivals (rather than being uniformly distributed) is the tell, distinct from the steady-state degradation of gotcha #1.

## 7. Silent nondeterminism breaks evals and caching

**Symptom:** the exact same request, same seed, same `temperature=0`, produces a different token stream on two different calls — or an eval suite that scores a model on Monday gives a measurably different number on Tuesday with no code change.
**Cause:** "temperature 0 means deterministic" is true of the math and false of the server. GPU kernel reductions (matmul, attention, norm) sum in a data- and batch-dependent order, and floating-point addition is not associative, so identical logical inputs can produce different bit patterns depending on what else is in the batch at that moment — see [[Concept - Nondeterminism in LLM Inference]] for the full mechanism, including why batch-variant kernels (not just atomic-add races) are the dominant cause.
**Fix:** if you need reproducibility for evals or caching, either accept it's approximate and cache by prompt+params rather than expecting byte-identical output, or move to batch-invariant kernels at a measured throughput cost — most production stacks choose the former and control nondeterminism where it actually bites (golden-set evals, cache keys) rather than eliminating it everywhere.
**Detection:** run the identical request N times under realistic concurrent load (not in isolation) and diff outputs; if isolated calls are stable but load-concurrent calls aren't, batch-variance is confirmed as the cause rather than a code bug.

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
