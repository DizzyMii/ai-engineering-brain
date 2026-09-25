---
tags: [ladder, domain/home, level/surface]
aliases: [Zero to Inference Engineer, LLM serving learning path, inference engineer roadmap, serving engineering ladder]
summary: "Ordered surface-to-unicorn walk to deploy, tune, and debug production LLM serving: KV cache, batching, quantization, kernels, war stories."
---

# Ladder - Zero to Inference Engineer

From the arithmetic substrate to running, tuning and debugging production LLM serving. It's for someone who can read a training loop but has never had to explain why a GPU sits at 5% utilization mid-decode. Twenty-four steps, each building on the last. First the numeric primitives, then the model you're serving, then the serving core (request lifecycle, KV cache, batching, quantization, cost), which is the job itself. After that comes the hardware lens that explains *why* the core behaves as it does, then the advanced techniques and tuning discipline that separate a working deployment from a good one, then the economics that turn serving into a budget line. It closes on the war stories serving engineers tell each other. Read each note for the one thing named under it; if you can answer the self-test, move on. By the end you should be able to look at a serving config and predict, without benchmarking, whether it's memory-bound or compute-bound, roughly what it costs per million tokens, and where it breaks first under load. This ladder covers the serving-and-hardware slice of the Engineering Wing. For the full 25-domain map, including the training and post-training work it takes as given, start at [[Home]].

---

## Act I: The Substrate (the arithmetic every layer above assumes)

**1. [[Concept - Matrix Multiplication as the Atom of Deep Learning]]**
The number that explains slow decode before you open a serving codebase. Speed depends on arithmetic intensity (FLOPs/bytes), not FLOP count. A batch-1 matrix-vector product, which is what every decode-step matmul in LLM inference is, does about 1 FLOP per byte read and lands at roughly 0.3% of an H100's peak throughput. Same operation, same silicon, 300x apart on shape alone. Batching, quantization and KV cache sizing all follow from this.
*Self-test:* Why does the same H100, running the same operation (a matmul), leave 99.7% of its peak FLOPs idle during single-stream decode?

**2. [[Concept - Floating Point for Deep Learning]]**
The exponent-vs-mantissa tradeoff behind every serving memory budget. bf16 keeps fp32's full 8-bit exponent range but truncates to 7 mantissa bits, so a 70B model costs exactly 140 GB of weights in bf16 (2 bytes/param) versus 280 GB in fp32. Tensor cores multiply in low precision but accumulate in fp32, because a matmul's rounding error grows with the square root of its reduction length. Every "does it fit on the GPU" question starts here.
*Self-test:* A 70B model's weight footprint differs by exactly 2x between bf16 and fp32. Why does that ratio matter more for serving than for training?

**3. [[Concept - Softmax]]**
Softmax is a numerical-stability landmine dressed as a two-line formula. Naive exponentiation overflows fp16 past a logit of about 11.09, and trained LMs routinely produce logits in the 10–30 range, so an unstabilized softmax NaNs on the first real batch. It runs once per row of the attention score matrix (N times per head, per layer). The online variant of the same trick, with a running max and sum, is the numerical basis of FlashAttention.
*Self-test:* A trained model's raw logits routinely exceed 11. Why does that specific number threaten a naive fp16 softmax?

---

## Act II: The Model You're Serving (architecture, not training)

**4. [[Deep Dive - The Transformer]]**
The skeleton every serving engine assumes: a stack of pre-norm residual blocks, each reading from and writing to one shared `d_model`-wide residual stream, with causal masking as the trick that made training (and the parameter-count math) tractable. The widely quoted `12·n_layers·d_model²` parameter formula is an approximation. It comes out 30–90% wrong on a GQA or MoE model, and most production models are one or the other. Check a config's actual KV-head count and FFN width before you trust a back-of-envelope estimate.
*Self-test:* Why does the `12·n_layers·d_model²` parameter-count formula go 30–90% wrong on a GQA or MoE model specifically?

**5. [[Concept - Attention Mechanism]]**
The operation whose cost model dominates serving at long context. `Q, K, V` projections; scores scaled by `1/sqrt(d_head)` to keep pre-softmax variance near 1 regardless of head dimension; a causal mask that zeroes future positions before the softmax. The `QK^T` and `AV` matmuls both cost `O(N²·d)` time, and the naive score matrix costs `O(N²)` memory. That figure motivates FlashAttention, the KV cache and every long-context architecture trick downstream.
*Self-test:* What breaks if you scale attention scores by `1/sqrt(d_model)` instead of `1/sqrt(d_head)`?

**6. [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]]**
A lineage that exists to shrink one number. KV cache size grows with head count as well as `d_model`, and MQA, GQA and MLA each attack the head term differently. LLaMA-2 70B's GQA (8 KV-head groups against 64 query heads) cuts the cache 8x at near-MHA quality. DeepSeek's MLA compresses K/V into a shared ~512-dim latent, roughly 4x smaller than GQA again, but it has to cache a small slice of RoPE dimensions uncompressed: RoPE's position-dependent rotation doesn't commute with a low-rank compression built around content.
*Self-test:* Why can't you apply RoPE directly to MLA's compressed latent vector the way you'd apply it to a normal per-head key?

---

## Act III: The Serving Core (the request lifecycle and its economics)

**7. [[Concept - The Inference Request Lifecycle]]**
The state machine that every optimization in this domain targets one stage of: tokenize → prefill (one parallel pass over the prompt) → decode loop (one sequential pass per output token) → sample → detokenize → stop-check. Time-to-first-token is queue wait plus prefill compute. Inter-token latency is dominated by decode re-reading the whole weight matrix from HBM every step. A stream that pauses then bursts has a scheduling problem, not a compute one: the request sat behind another request's prefill.
*Self-test:* A user reports the stream "pauses then bursts." Is that a compute problem or a scheduling problem, and how do you tell?

**8. [[Concept - Prefill and Decode Phases]]**
The asymmetry that shapes every serving system. Prefill is compute-bound (intensity scales with prompt length, MFU 40–50%). Decode is memory-bandwidth-bound almost independent of model size (single-stream MFU often under 5%). Worked number: a 70B model in fp16 on an H100 takes about 42 ms per decode token, under 25 tokens/second, because each step re-reads ~140 GB of weights from ~3.35 TB/s HBM. Batching fixes it because it raises decode's arithmetic intensity roughly in proportion to batch size at almost no extra HBM cost.
*Self-test:* Why does doubling a GPU's HBM bandwidth roughly halve decode latency but barely touch prefill throughput?

**9. [[Concept - KV Cache]]**
More than model weights, this data structure caps how many users a GPU can serve. Caching K,V turns `O(N²)` recompute into `O(N)` reads at a cost of `2·layers·kv_heads·d_head·seq_len·batch·bytes_per_elem`. Worked number: Llama-3-70B costs ~0.31 MB per token, so a single 128K-context sequence eats ~43 GB, the same order as the model's own weights. On an 80 GB H100, 140 GB of bf16 weights already forces two GPUs, and whatever HBM is left (commonly ~20 GB/GPU) is the *entire* KV budget. That budget caps concurrency. FLOPs don't.
*Self-test:* Two models have wildly different parameter counts but the same layer/head/head-dim configuration. Why might their serving-concurrency ceilings be surprisingly close?

**10. [[Concept - Sampling and Decoding Parameters]]**
A pipeline everyone assumes is standardized, and it isn't: logits → repetition penalties → temperature → top-k/top-p truncation → softmax → draw. Temperature divides logits *before* the exponential, so its effect is exponential, not linear. No spec fixes the order these transforms run in, so identical `{temperature, top_p}` values aren't guaranteed to give the same output distribution across vLLM, TGI, llama.cpp and a hosted API. Even `T=0` isn't bitwise-deterministic on a real server, which breaks eval harnesses and semantic caches built on "deterministic" outputs.
*Self-test:* You migrate a prompt with the same temperature and top_p from one serving stack to another and output quality shifts. What should you rule out before blaming the model or quantization?

**11. [[Concept - Continuous Batching]]**
The change that took LLM serving from "acceptable" to "production-grade." Iteration-level scheduling re-decides batch membership after every decode step. The old way ran a fixed batch until its longest straggler finished. Reported gains are roughly 2–23x throughput over static batching: the low end on uniform-length workloads, the high end on chat and agent traffic where output length varies wildly. It needs to admit a new request's KV mid-flight without a pre-reserved contiguous buffer, and that's why it comes as a package with paged KV allocation.
*Self-test:* Why does continuous batching's speedup depend on output-length variance? Why would it help far less on a workload where every response is the same length?

**12. [[Concept - Post-Training Quantization Formats]]**
The fork that decides what a quantization format buys you. Weight-only formats (GPTQ, AWQ) save memory and HBM bandwidth but not FLOPs, since the matmul still runs in bf16 after dequantization. W8A8/fp8 schemes quantize activations too and do cut FLOPs. GPTQ corrects each layer's error with a Hessian-based per-column update; AWQ protects the ~1% of activation channels that are empirically "salient." The trap: under 1% WikiText perplexity increase is typical at 4-bit, but perplexity is a weak proxy. One dropped JSON brace in a tool call wrecks that task while barely moving next-token log-loss.
*Self-test:* A quantized model shows a clean WikiText perplexity number. Why is that necessary but nowhere near sufficient to ship it to production?

**13. [[Concept - Latency, Throughput, and Cost in LLM Serving]]**
The identity that turns a GPU price into dollars per million tokens: `$/1M output tokens = (GPU $/hr / 3600) / aggregate decode tokens/sec × 10^6`. That's roughly $0.28/M on an H100 at $2.50/hr sustaining 2,500 tok/s. It also explains why hosted APIs price output tokens 3–5x above input: decode's memory-bound serialization costs more than prefill's cheap compute-bound parallelism, and the price passes that straight through. It's not a business-model choice. The counterintuitive part: speculative decoding, the usual first reach for latency, can *reduce* aggregate throughput at high batch, because verification competes for FLOPs a compute-saturated GPU doesn't have spare.
*Self-test:* Why could enabling speculative decoding fleet-wide, regardless of current batch size, make a service slower in aggregate even though every individual request's benchmark looks faster?

---

## Act IV: The Hardware Lens (why the serving core behaves as it does)

**14. [[Concept - GPU Memory Hierarchy]]**
The four-tier pyramid every kernel is staged against: registers (~256 KB/SM, ~1 cycle) → shared memory/L1 (~228 KB/SM on Hopper, ~20–30 cycles) → L2 (~50 MB on H100, ~200 cycles) → HBM3 (80 GB at ~3.35 TB/s on H100, ~400–800 cycles). Across that span capacity grows roughly 1000x and bandwidth drops roughly 1000x. The whole chip's fast memory adds up to well under 100 MB against 80,000 MB of HBM, smaller than a single server CPU's L3 cache. Nothing moves data down this pyramid automatically the way a CPU cache would. The kernel author does it by hand, tile by tile.
*Self-test:* A single modern server CPU's L3 cache can rival an entire H100's on-chip fast memory. What does that imply about how GPU kernels must be written compared to CPU code?

**15. [[Concept - The Roofline Model]]**
One division tells you what's worth optimizing: arithmetic intensity `I = FLOPs / bytes moved from HBM`, and attainable throughput is `min(peak FLOPs, I × bandwidth)`. On an H100 the ridge point is roughly 295 FLOP/byte, so every byte loaded from HBM has to be reused about 300 times before the tensor cores stop starving. Decode sits far left of the ridge regardless of model size. That's the hardware-level reason for what Act III showed empirically about decode being memory-bound.
*Self-test:* A kernel sits well below the memory roof at its measured arithmetic intensity. Does that mean it's compute-bound, and if not, what else could explain the gap?

**16. [[Deep Dive - FlashAttention]]**
The algorithm that made "exact and fast" compatible. It tiles Q, K, V through SRAM and computes softmax online with a running max and sum, rescaling the accumulated output by `e^(m_old - m_new)` whenever a new tile shows a larger max, so the full N×N score matrix never touches HBM. It does strictly *more* FLOPs than a naive implementation, recomputing the score matrix in the backward pass instead of storing it, yet runs 2–4x faster wall-clock because attention is memory-bound. FlashAttention-3 reaches roughly 75% of H100's tensor-core peak with asynchronous TMA copies and warp specialization.
*Self-test:* FlashAttention's backward pass does strictly more FLOPs than a version that cached the score matrix. Why is it still faster in wall-clock time?

---

## Act V: Advanced Serving (from working to tuned)

**17. [[Concept - PagedAttention]]**
A memory-management bug fix that became the industry standard. Instead of reserving one contiguous `max_seq_len` buffer per request, PagedAttention splits KV into fixed-size blocks (16 tokens by default), puts them anywhere in a shared physical pool, and indexes them per request through a block table. That's the same virtual-to-physical page mapping an OS uses. Measured KV waste fell from 60–80% to under 4%, and prefix caching later reused the same block-table sharing across requests instead of only within one.
*Self-test:* What OS-level concept does a PagedAttention "block table" correspond to, and why does that correspondence eliminate external fragmentation by construction?

**18. [[Concept - Speculative Decoding]]**
Spends decode's idle compute instead of its idle bandwidth. A cheap draft model proposes several tokens ahead, and the target model verifies them all in one forward pass at roughly the cost of generating one token. A rejection-sampling rule (accept with probability `min(1, p_target/p_draft)`, resample from the normalized positive residual on rejection) guarantees the output distribution is mathematically identical to sampling from the target alone. Typical wins are 2–3x latency reduction at low batch. The same mechanism can *reduce* throughput at high batch, since verification FLOPs compete with useful decode work once the GPU is compute-saturated.
*Self-test:* Why is the acceptance rule designed so that a weak, badly matched draft model costs you speed but never correctness?

**19. [[Breakdown - vLLM]]**
Why one open-source engine became the default. It paired PagedAttention with Orca-style iteration-level scheduling, and the block manager's O(1) block-table update is what makes admitting a new request mid-iteration possible. That's why paged KV and continuous batching shipped together and are still treated as a matched pair across the industry. vLLM gives up some raw per-step kernel speed (gathering scattered blocks is less cache-friendly than reading one contiguous span) in exchange for the 2–4x throughput jump from paging and day-0 support for new open models via a scheduler/model-code split.
*Self-test:* Why does vLLM generally trail a hand-compiled TensorRT-LLM engine on raw single-config latency, and why does the project accept that tradeoff?

**20. [[Playbook - Tuning an LLM Serving Deployment]]**
The ordered procedure from "it's slow" to a fixed config. Pin a baseline on a *realistic* traffic trace (not fixed-length synthetic prompts). Sweep concurrency to find the latency "knee." Diagnose what's binding there: KV pressure and preemption count, compute saturation, or raw bandwidth. Then turn the one knob that matches the diagnosis: `gpu-memory-utilization`, `max-num-seqs`, `max-num-batched-tokens`, fp8 KV cache, or prefix caching. Where people trip: throughput mode and latency mode are different configs, never one config that claims both, and every knob change invalidates the previous benchmark.
*Self-test:* Your concurrency sweep shows KV utilization climbing alongside rising preemption count right at the SLO-violating concurrency. Which knob do you reach for first, and why not `max-num-batched-tokens`?

---

## Act VI: Ops and Economics (keeping it alive and affordable)

**21. [[Concept - Cost Engineering for LLM Applications]]**
The base identity of every LLM budget: `cost = n_in·p_in + n_out·p_out`. Output tokens are priced 3–5x input, passing through the serving-side decode-vs-prefill asymmetry, and frontier models run roughly $2.5–15 per million input tokens and $10–75 per million output tokens *(as of 2026)*. In most production apps the main cost driver is resent input: RAG context and conversation history sent again on every call. So an agent loop's total cost grows roughly quadratically in its step count even though each call looks cheap.
*Self-test:* Why does an N-step agent loop's total token cost grow roughly quadratically in N even if each call looks cheap in isolation?

**22. [[Concept - Semantic Caching]]**
This lever skips the model call entirely. Embed the incoming prompt, run an ANN lookup against prior `(prompt, response)` pairs, and return the cached completion if cosine similarity clears a threshold, tuned in production to roughly 0.95–0.97. Since it skips generation, a false hit is the most painful failure mode in the domain. It serves a confidently wrong answer that looks identical to a correct one, and it freezes one sampled generation's variance into a permanent bias for every future near-duplicate query until the entry expires.
*Self-test:* Why is a false hit in a semantic cache categorically worse than a false hit in a KV or prefix cache, even though both are "cache mistakes"?

---

## The unicorn tier: the serving war stories

**23. [[Lore - The KV Cache Fragmentation Crisis]]**
The story behind PagedAttention. From 2022 into early 2023, every mainstream serving stack pre-allocated one contiguous `max_seq_len` buffer per request because attention kernels assumed contiguous K,V. That wasted a measured 60–80% of the KV memory region. Meanwhile the field chased the wrong layer (faster kernels, better batching heuristics) because everyone assumed the bottleneck was compute. Berkeley's Sky Computing Lab saw it was literally the OS paging problem from the 1960s–70s. Waste dropped to under 4%, throughput jumped 2–4x almost overnight, and the field re-standardized within about a year.
*Self-test:* For over a year, serious engineers optimized CUDA kernels and batching heuristics to fix a problem that turned out to be one layer up. What general heuristic does this teach about where to look when an ML system wastes a resource it can't pack tightly?

**24. [[Lore - The llama.cpp Insurgency]]**
Folklore that flowed upward instead of down from a lab. Days after the March 2023 LLaMA leak, Georgi Gerganov pointed his dependency-free `ggml` tensor library at the weights and shipped 4-bit quantization that took LLaMA-7B from ~13 GB to under 4 GB. That fits on a MacBook. "You need a datacenter" became "you need a laptop," for the same memory-bandwidth reason decode is bandwidth-bound everywhere else in this ladder. The quantization culture it started (k-quants and importance matrices, mixed precision per tensor type, calibration against real activations) later flowed into vLLM, SGLang and vendor stacks.
*Self-test:* llama.cpp's 4-bit quantization sped up single-stream token generation by roughly the same factor it shrank the weights. Why does that ratio hold for decode but not the same way for prefill?

---

Where next: [[MOC - Inference & Serving]] maps the rest of domain 07 that this ladder left out (chunked prefill, prefill-decode disaggregation, SGLang, TensorRT-LLM, KV cache quantization). [[MOC - Hardware & Systems]] maps the kernel- and cluster-level detail under Act IV.
