---
tags: [ladder, domain/home, level/surface]
aliases: [Zero to Inference Engineer, LLM serving learning path, inference engineer roadmap, serving engineering ladder]
summary: "Ordered surface-to-unicorn walk to deploy, tune, and debug production LLM serving: KV cache, batching, quantization, kernels, war stories."
---

# Ladder - Zero to Inference Engineer

A guided walk from the arithmetic substrate to running, tuning, and debugging production LLM serving — for someone who can read a training loop but has never had to explain why a GPU sits at 5% utilization mid-decode. Twenty-four steps, ordered so the story compounds: the numeric primitives first, then the model you're actually serving, then the serving core — the request lifecycle, KV cache, batching, quantization, cost — that is the job itself, then the hardware lens that explains *why* the serving core behaves the way it does, then the advanced techniques and the tuning discipline that separate a working deployment from a good one, then the economics that make serving a budget line and not just an engineering problem, closing on the war stories serving engineers actually tell each other. Read each note for the one thing named under it; if you can answer the self-test, you got the point and can move on. By the end you should be able to look at a serving config and predict, without benchmarking, whether it's memory-bound or compute-bound, roughly what it costs per million tokens, and where it breaks first under load. This ladder covers the serving-and-hardware slice of the Engineering Wing specifically; for the full 25-domain map, including the training and post-training work this one takes as a given, start at [[Home]].

---

## Act I — The Substrate (the arithmetic every layer above assumes)

**1. [[Concept - Matrix Multiplication as the Atom of Deep Learning]]**
Extract the number that explains why decode is slow before you ever open a serving codebase: arithmetic intensity (FLOPs/bytes) decides speed, not FLOP count, and a batch-1 matrix-vector product — every decode-step matmul in LLM inference — does about 1 FLOP per byte read, landing at roughly 0.3% of an H100's peak throughput. Same operation, same silicon, 300x apart purely on shape. Everything from batching to quantization to KV cache sizing is downstream of this one fact.
*Self-test:* Why does the exact same H100, running the exact same operation (a matmul), spend 99.7% of its peak FLOPs idle during single-stream decode?

**2. [[Concept - Floating Point for Deep Learning]]**
Extract the exponent-vs-mantissa tradeoff that sets every serving memory budget: bf16 keeps fp32's full 8-bit exponent range but truncates to 7 mantissa bits, which is why a 70B model costs exactly 140 GB of weights in bf16 (2 bytes/param) versus 280 GB in fp32. Tensor cores multiply in low precision but accumulate in fp32, because a matmul's rounding error grows with the square root of its reduction length. This is the number every "does it fit on the GPU" question starts from.
*Self-test:* A 70B model's weight footprint differs by exactly 2x between bf16 and fp32 — why does that ratio matter more for serving than it does for training?

**3. [[Concept - Softmax]]**
Extract why softmax is a numerical-stability landmine, not a two-line formula: naive exponentiation overflows fp16 past a logit value of about 11.09, and trained LMs routinely produce logits in the 10–30 range, so an unstabilized softmax NaNs on the first real batch. It runs once per row of the attention score matrix — N times per head, per layer — which is why the online (running max-and-sum) variant of this same trick is the numerical foundation FlashAttention is built on.
*Self-test:* A trained model's raw logits routinely exceed 11 — why does that specific number threaten a naive fp16 softmax?

---

## Act II — The Model You're Serving (architecture, not training)

**4. [[Deep Dive - The Transformer]]**
Extract the skeleton every serving engine assumes: a stack of pre-norm residual blocks, each reading from and writing to one shared `d_model`-wide residual stream, with causal masking as the trick that made training (and the parameter-count math) tractable. The widely quoted `12·n_layers·d_model²` parameter formula is a convenient approximation, not a law — it comes out 30–90% wrong the moment you meet a GQA or MoE model, which is most production models. Always check a config's actual KV-head count and FFN width before trusting a back-of-envelope estimate.
*Self-test:* Why does the `12·n_layers·d_model²` parameter-count formula go 30–90% wrong on a GQA or MoE model specifically?

**5. [[Concept - Attention Mechanism]]**
Extract the operation whose cost model dominates serving at long context: `Q, K, V` projections, scores scaled by `1/sqrt(d_head)` to keep pre-softmax variance near 1 regardless of head dimension, and a causal mask that zeroes out future positions before the softmax. Both the `QK^T` and `AV` matmuls cost `O(N²·d)` time, and naively the score matrix costs `O(N²)` memory — the exact number that motivates FlashAttention, the KV cache, and every long-context architecture trick downstream.
*Self-test:* What specifically breaks if you scale attention scores by `1/sqrt(d_model)` instead of `1/sqrt(d_head)`?

**6. [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]]**
Extract the lineage that exists purely to shrink one number: KV cache size grows with head count, not just `d_model`, so MQA, GQA, and MLA each attack the head term differently. LLaMA-2 70B's GQA (8 KV-head groups against 64 query heads) is an 8x cache cut at near-MHA quality; DeepSeek's MLA compresses K/V into a shared ~512-dim latent for roughly 4x smaller than GQA again, but must cache a small slice of RoPE dimensions uncompressed, because RoPE's position-dependent rotation doesn't commute with a low-rank compression built around content.
*Self-test:* Why can't you apply RoPE directly to MLA's compressed latent vector the way you'd apply it to a normal per-head key?

---

## Act III — The Serving Core (the request lifecycle and its economics)

**7. [[Concept - The Inference Request Lifecycle]]**
Extract the state machine every optimization in this domain attacks one stage of: tokenize → prefill (one parallel pass over the prompt) → decode loop (one sequential pass per output token) → sample → detokenize → stop-check. Time-to-first-token is queue wait plus prefill compute; inter-token latency is dominated by decode re-reading the entire weight matrix from HBM every step. A stream that visibly pauses then bursts is a scheduling symptom, not a compute one — it means the request sat behind another request's prefill.
*Self-test:* A user reports the stream "pauses then bursts" — is that a compute problem or a scheduling problem, and how do you tell the difference?

**8. [[Concept - Prefill and Decode Phases]]**
Extract the asymmetry that shapes every serving system's design: prefill is compute-bound (intensity scales with prompt length, MFU 40–50%), decode is memory-bandwidth-bound almost independent of model size (single-stream MFU often under 5%). Worked number: a 70B model in fp16 on an H100 costs about 42 ms per decode token — under 25 tokens/second — because that step just re-reads ~140 GB of weights from ~3.35 TB/s HBM. Batching is the fix precisely because it raises decode's arithmetic intensity roughly in proportion to batch size at almost no extra HBM cost.
*Self-test:* Why does doubling a GPU's HBM bandwidth roughly halve decode latency but barely touch prefill throughput?

**9. [[Concept - KV Cache]]**
Extract the data structure that, more than model weights, caps how many users a GPU can serve: caching K,V turns `O(N²)` recompute into `O(N)` reads, at a cost of `2·layers·kv_heads·d_head·seq_len·batch·bytes_per_elem`. Worked number: Llama-3-70B costs ~0.31 MB per token, so one 128K-context sequence alone eats ~43 GB — on the same order as the model's own weights. On an 80 GB H100, 140 GB of bf16 weights already forces two GPUs, and whatever HBM survives (commonly ~20 GB/GPU) is the *entire* KV budget that actually caps concurrency, not FLOPs.
*Self-test:* Two models have wildly different parameter counts but the same layer/head/head-dim configuration — why might their serving-concurrency ceilings be surprisingly close?

**10. [[Concept - Sampling and Decoding Parameters]]**
Extract the pipeline everyone assumes is standardized and isn't: logits → repetition penalties → temperature → top-k/top-p truncation → softmax → draw. Temperature divides logits *before* the exponential, so its effect is exponential, not linear — and because no spec pins down the order these transforms apply in, identical `{temperature, top_p}` values are not guaranteed to produce the same output distribution across vLLM, TGI, llama.cpp, and a hosted API. Even `T=0` isn't bitwise-deterministic on a real server, a fact that quietly breaks eval harnesses and semantic caches built on "deterministic" outputs.
*Self-test:* You migrate a prompt with the exact same temperature and top_p from one serving stack to another and output quality shifts — what should you rule out before blaming the model or quantization?

**11. [[Concept - Continuous Batching]]**
Extract the single change that took LLM serving from "acceptable" to "production-grade": iteration-level scheduling re-decides batch membership after every decode step instead of running a fixed batch until its longest straggler finishes, reporting roughly 2–23x throughput over static batching — the low end on uniform-length workloads, the high end on chat and agent traffic where output length varies wildly. It requires admitting a new request's KV mid-flight without a pre-reserved contiguous buffer, which is exactly what makes it a package deal with paged KV allocation.
*Self-test:* Why does continuous batching's speedup depend on output-length variance — why would it help far less on a workload where every response is exactly the same length?

**12. [[Concept - Post-Training Quantization Formats]]**
Extract the fork that decides what a quantization format actually buys you: weight-only formats (GPTQ, AWQ) save memory and HBM bandwidth but not FLOPs, since the matmul still runs in bf16 after dequantization, while W8A8/fp8 schemes quantize activations too and genuinely cut FLOPs. GPTQ corrects each layer's error with a Hessian-based per-column update; AWQ instead protects the ~1% of activation channels that are empirically "salient." The trap: under 1% WikiText perplexity increase is typical at 4-bit, but perplexity is a weak proxy — a single dropped JSON brace in a tool call is catastrophic for that task while barely moving next-token log-loss.
*Self-test:* A quantized model shows a clean WikiText perplexity number — why is that necessary but nowhere near sufficient to ship it to production?

**13. [[Concept - Latency, Throughput, and Cost in LLM Serving]]**
Extract the identity that turns a GPU price tag into dollars per million tokens: `$/1M output tokens = (GPU $/hr / 3600) / aggregate decode tokens/sec × 10^6` — roughly $0.28/M on an H100 at $2.50/hr sustaining 2,500 tok/s. It also explains why hosted APIs price output tokens 3–5x higher than input tokens: it's a direct pass-through of decode's memory-bound serialization versus prefill's cheap compute-bound parallelism, not a business-model choice. The counterintuitive kicker: speculative decoding, the default first reach for latency, can *reduce* aggregate throughput at high batch because verification competes for FLOPs a compute-saturated GPU no longer has spare.
*Self-test:* Why would enabling speculative decoding fleet-wide, without regard to current batch size, risk making a service slower in aggregate even though every individual request's benchmark looks faster?

---

## Act IV — The Hardware Lens (why the serving core behaves the way it does)

**14. [[Concept - GPU Memory Hierarchy]]**
Extract the four-tier pyramid every kernel above it is staged against: registers (~256 KB/SM, ~1 cycle) → shared memory/L1 (~228 KB/SM on Hopper, ~20–30 cycles) → L2 (~50 MB on H100, ~200 cycles) → HBM3 (80 GB at ~3.35 TB/s on H100, ~400–800 cycles). Capacity grows roughly 1000x and bandwidth drops roughly 1000x across that span, and the entire chip's fast-memory budget adds up to well under 100 MB against 80,000 MB of HBM — smaller than a single server CPU's L3 cache. Nothing stages data down this pyramid automatically the way a CPU cache would; a kernel author has to do it explicitly, tile by tile.
*Self-test:* A single modern server CPU's L3 cache alone can rival an entire H100's on-chip fast-memory footprint — what does that imply about how GPU kernels must be written compared to CPU code?

**15. [[Concept - The Roofline Model]]**
Extract the one division that tells you what's even worth optimizing: arithmetic intensity `I = FLOPs / bytes moved from HBM`, and attainable throughput is `min(peak FLOPs, I × bandwidth)`. On an H100 the ridge point sits at roughly 295 FLOP/byte — you must reuse every byte loaded from HBM about 300 times before the tensor cores stop starving. Decode sits pinned far to the left of that ridge point regardless of model size, which is the formal, hardware-level reason behind everything Act III established empirically about decode being memory-bound.
*Self-test:* A kernel sits well below the memory roof at its measured arithmetic intensity — does that necessarily mean it's compute-bound, and if not, what else could explain the gap?

**16. [[Deep Dive - FlashAttention]]**
Extract the algorithm that made "exact and fast" stop being a contradiction: it tiles Q, K, V through SRAM and computes softmax online with a running max and sum, rescaling the accumulated output by `e^(m_old - m_new)` whenever a new tile reveals a larger max, so the full N×N score matrix never touches HBM. It does strictly *more* FLOPs than a naive implementation — it recomputes the score matrix from scratch in the backward pass rather than storing it — yet runs 2–4x faster wall-clock, because attention is memory-bound, not compute-bound. FlashAttention-3 pushes this to roughly 75% of H100's tensor-core peak using asynchronous TMA copies and warp specialization.
*Self-test:* FlashAttention's backward pass does strictly more FLOPs than a version that cached the score matrix — why is it still faster in wall-clock time?

---

## Act V — Advanced Serving (from working to tuned)

**17. [[Concept - PagedAttention]]**
Extract the fix that turned a memory-management bug into the industry standard: instead of reserving one contiguous `max_seq_len` buffer per request, PagedAttention splits KV into fixed-size blocks (16 tokens by default), places them anywhere in a shared physical pool, and indexes them per-request through a block table — the exact virtual-memory-to-physical-page relationship an OS uses. This cut measured KV waste from 60–80% down to under 4%, and its block-table sharing is the same mechanism prefix caching later reuses across requests instead of just within one.
*Self-test:* What OS-level concept does a PagedAttention "block table" directly correspond to, and why does that correspondence eliminate external fragmentation by construction?

**18. [[Concept - Speculative Decoding]]**
Extract the technique that spends decode's idle compute instead of its idle bandwidth: a cheap draft model proposes several tokens ahead, the target model verifies all of them in one forward pass at roughly the cost of generating one token, and a rejection-sampling rule — accept with probability `min(1, p_target/p_draft)`, resample from the normalized positive residual on rejection — guarantees the output distribution is mathematically identical to sampling from the target alone. Typical wins are 2–3x latency reduction at low batch, but the same mechanism can *reduce* throughput at high batch, because verification FLOPs compete with useful decode work once the GPU is already compute-saturated.
*Self-test:* Why is the acceptance rule specifically designed so that a weak, badly-matched draft model costs you speed but never correctness?

**19. [[Breakdown - vLLM]]**
Extract why one open-source engine became the field's default: it paired PagedAttention with Orca-style iteration-level scheduling, and the block manager's O(1) block-table update is precisely what makes admitting a new request mid-iteration possible — the reason paged KV and continuous batching shipped together and are still treated as a matched pair industry-wide. It trades some raw per-step kernel speed (gathering scattered blocks is less cache-friendly than reading one contiguous span) for the 2–4x throughput jump the paging fix delivered and for day-0 support of new open models via a scheduler/model-code split.
*Self-test:* Why does vLLM generally trail a hand-compiled TensorRT-LLM engine on raw single-config latency, and why does the project accept that tradeoff?

**20. [[Playbook - Tuning an LLM Serving Deployment]]**
Extract the ordered procedure that turns "it's slow" into a fixed config: pin a baseline on a *realistic* traffic trace (not fixed-length synthetic prompts), sweep concurrency to find the latency "knee," diagnose what's actually binding there (KV-pressure and preemption count versus compute saturation versus raw bandwidth), then apply the one knob matched to that diagnosis — `gpu-memory-utilization`, `max-num-seqs`, `max-num-batched-tokens`, fp8 KV cache, or prefix caching. The discipline that trips people up: throughput mode and latency mode are different configs, never one config that claims both, and every knob change invalidates the previous benchmark.
*Self-test:* Your concurrency sweep shows KV utilization climbing alongside rising preemption count right at the SLO-violating concurrency — which knob do you reach for first, and why not `max-num-batched-tokens`?

---

## Act VI — Ops and Economics (keeping it alive and affordable)

**21. [[Concept - Cost Engineering for LLM Applications]]**
Extract the base identity every LLM budget is built on: `cost = n_in·p_in + n_out·p_out`, with output tokens priced 3–5x input tokens as a direct pass-through of the serving-side decode-vs-prefill asymmetry, and frontier models running roughly $2.5–15 per million input tokens and $10–75 per million output tokens *(as of 2026)*. The real cost driver in most production apps is resent input — RAG context and conversation history sent again on every call — which is why an agent loop's total cost grows roughly quadratically in its step count even though each individual call looks cheap.
*Self-test:* Why does an N-step agent loop's total token cost grow roughly quadratically in N even if each individual call looks cheap in isolation?

**22. [[Concept - Semantic Caching]]**
Extract the lever that skips the model call entirely rather than speeding it up: embed the incoming prompt, run an ANN lookup against prior `(prompt, response)` pairs, and return the cached completion outright if cosine similarity clears a threshold — tuned in production to roughly 0.95–0.97. Because it skips generation rather than accelerating it, a false hit is the highest-pain failure mode in the whole domain: it serves a confidently wrong answer that looks identical to a correct one, and it freezes one sampled generation's variance into a permanent bias for every future near-duplicate query until the entry expires.
*Self-test:* Why is a false hit in a semantic cache categorically worse than a false hit in a KV or prefix cache, even though both are "cache mistakes"?

---

## The unicorn tier — the serving war stories

**23. [[Lore - The KV Cache Fragmentation Crisis]]**
Extract the tribal knowledge under PagedAttention's origin: through 2022 into early 2023, every mainstream serving stack pre-allocated one contiguous `max_seq_len` buffer per request because attention kernels assumed contiguous K,V, wasting a measured 60–80% of the KV memory region while the entire field kept chasing the wrong layer — faster kernels, better batching heuristics — because everyone assumed the bottleneck was compute. Berkeley's Sky Computing Lab recognized it as literally the OS paging problem from the 1960s–70s; waste dropped to under 4% and throughput jumped 2–4x almost overnight, re-standardizing the field within about a year.
*Self-test:* For over a year, serious engineers optimized CUDA kernels and batching heuristics to fix a problem that turned out to be one layer up — what's the general heuristic this story teaches about where to look when an ML system wastes a resource it can't pack tightly?

**24. [[Lore - The llama.cpp Insurgency]]**
Extract the folklore that flowed upward instead of down from a lab: days after the March 2023 LLaMA leak, Georgi Gerganov pointed his dependency-free `ggml` tensor library at the weights and shipped 4-bit quantization that dropped LLaMA-7B from ~13 GB to under 4 GB — small enough for a MacBook, inverting "you need a datacenter" into "you need a laptop" for the same memory-bandwidth-bound reason decode is bandwidth-bound everywhere else in this ladder. The k-quant and importance-matrix quantization culture it spawned — mixed precision per tensor type, calibration against real activations — later flowed into vLLM, SGLang, and vendor stacks rather than trickling down from one.
*Self-test:* llama.cpp's 4-bit quantization sped up single-stream token generation by roughly the same factor it shrank the weights — why does that specific ratio hold for decode but wouldn't hold the same way for prefill?

---

Where next: [[MOC - Inference & Serving]] maps the rest of domain 07 this ladder had to leave out — chunked prefill, prefill-decode disaggregation, SGLang, TensorRT-LLM, KV cache quantization; [[MOC - Hardware & Systems]] maps the kernel- and cluster-level detail underneath everything in Act IV.
