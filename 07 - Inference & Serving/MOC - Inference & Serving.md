---
tags: [moc, domain/inference-serving, level/surface]
aliases: []
summary: "Map of Inference & Serving: request lifecycle, KV cache, batching, quantization, speculative decoding, and the engines that run them."
---
# MOC - Inference & Serving

This domain covers everything after a model is trained and someone sends it a request: tokenization, prefill, decode, sampling, and streaming a response back inside a latency and dollar budget. Training happens once; serving happens on every request, forever. A 2x gain in tokens-per-dollar here compounds across a company's whole query volume in a way no training-time optimization can match.

Most of the tricks follow from one split. Prefill is parallel and compute-bound, decode is sequential and memory-bandwidth-bound, and the thing usually rationed is the GPU's HBM capacity, not its FLOPs. The notes follow that constraint through the KV cache (the memory hog), batching and scheduling (sharing a GPU across concurrent requests), quantization and speculative decoding (buying back bandwidth and latency), and the frameworks that implement all of it: vLLM, SGLang, TensorRT-LLM, llama.cpp.

**Start here, by level:**
- **Surface:** [[Concept - The Inference Request Lifecycle]]: the end-to-end path of a generation request (tokenize, prefill, decode loop, sample, detokenize, stream). Every other note here zooms into one leg of it.
- **Core:** [[Concept - KV Cache]]: caching per-token K/V turns O(N²) attention recompute into O(N) reads, and its memory footprint is the one number that caps how many requests you can serve at once.
- **Advanced:** [[Concept - PagedAttention]]: the virtual-memory-style paging fix that cut KV cache waste from 60-80% to under 4%. vLLM, SGLang and most modern engines run on it.
- **Frontier:** [[Concept - Prefill-Decode Disaggregation]]: prefill and decode on separate GPU pools linked by a KV transfer, so each phase hits its own latency SLO instead of fighting over one batch.
- **Unicorn:** [[Lore - The KV Cache Fragmentation Crisis]]: why PagedAttention had to be invented. Memory lost to fragmentation, not compute, capped GPU-served concurrency for years before anyone framed it as an OS problem.

## The request lifecycle and its economics
- [[Concept - The Inference Request Lifecycle]] — the path a generation request takes end-to-end: tokenize, prefill, decode loop, sample, detokenize, stream.
- [[Concept - Prefill and Decode Phases]] — prefill is parallel and compute-bound, decode is sequential and memory-bandwidth-bound. This split shapes all LLM serving design.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — how TTFT, TPOT, and throughput trade off, and how to derive dollars-per-million-tokens from GPU price and decode throughput.
- [[Reference - Inference Performance Math]] — formula and metric sheet: KV cache bytes, decode step time, max batch, TTFT/TPOT/throughput/goodput, and cost per token.

## Sampling and decoding
- [[Concept - Sampling and Decoding Parameters]] — how raw logits become one token each step: penalties, temperature, truncation, and why identical params disagree across serving stacks.
- [[Snippet - Sampling from Logits]] — reference implementation of the logits-to-token pipeline: repetition penalty, temperature, top-k/top-p/min-p, softmax, multinomial draw.
- [[Concept - Advanced Samplers (min-p, Mirostat, DRY)]] — the community sampler zoo beyond temperature/top-p (min-p, Mirostat, DRY, XTC): how each works and the folklore on when it helps.
- [[Concept - Constrained Decoding]] — masking invalid tokens' logits each decode step so generation must conform to a JSON schema, regex, or CFG. A guarantee, not a hope.
- [[Concept - Token Healing]] — fixing prompts that end mid-token: back up and re-constrain so the model re-chooses the natural BPE merge at the boundary.
- [[Concept - Streaming Detokenization]] — reassembling correct UTF-8 text from a streamed token-ID sequence, where multi-byte characters and stop strings straddle token boundaries.
- [[Concept - Nondeterminism in LLM Inference]] — why temperature 0 isn't deterministic on a real server: FP non-associativity, batch-variant kernels, and how batch-invariant kernels fix it.

## The KV cache and memory management
- [[Concept - KV Cache]] — caching per-token K/V turns O(N²) attention recompute into O(N) reads; its memory footprint caps serving concurrency.
- [[Concept - PagedAttention]] — virtual-memory-style paging of the KV cache into fixed blocks, cutting KV waste from 60-80% to under 4% and enabling continuous batching.
- [[Concept - Automatic Prefix Caching]] — reusing already-computed KV blocks across requests that share a leading prefix, so shared system prompts and chat history skip prefill entirely.
- [[Concept - KV Cache Quantization]] — quantizing the KV cache (not the weights) to fit more context or concurrency, and why keys and values need different treatment.
- [[Concept - KV Cache Offloading and Compression]] — tiering KV cache across HBM/CPU/NVMe, or evicting low-value tokens, once context no longer fits in GPU memory.
- [[Lore - The KV Cache Fragmentation Crisis]] — how LLM serving wasted 60-80% of GPU memory to KV fragmentation until PagedAttention reframed it as an OS paging problem.

## Batching and scheduling
- [[Concept - Continuous Batching]] — iteration-level scheduling that re-forms the decode batch every step so short requests never idle a GPU slot waiting on a straggler.
- [[Concept - Chunked Prefill]] — slicing long prefills into token-budget chunks interleaved with decode tokens so a new request's prefill can't stall everyone else's inter-token latency.
- [[Concept - Prefill-Decode Disaggregation]] — running prefill and decode on separate GPU pools, linked by a KV cache transfer, so each phase hits its own latency SLO.

## Speculative decoding
- [[Concept - Speculative Decoding]] — a cheap draft model proposes several tokens; the target model verifies them in one pass via rejection sampling, cutting latency losslessly at low batch.
- [[Concept - Self-Drafting Speculative Decoding (Medusa, EAGLE, Lookahead)]] — speculative decoding without a second model: extra heads, predicted hidden states, or Jacobi iteration draft tokens from the target itself.
- [[Snippet - Speculative Decoding Verification]] — reference implementation of speculative decoding's accept/reject + residual-resample rule, with an empirical proof of losslessness.

## Quantization
- [[Concept - Post-Training Quantization Formats]] — the landscape of formats (GPTQ, AWQ, GGUF k-quants, fp8) used to compress a trained model's weights for inference, and where each loses quality.
- [[Concept - FP8 and Low-Precision Inference]] — hardware-native FP8 and FP4 inference formats: layouts, scaling recipes, and the GPU-generation gating tying precision to your fleet.
- [[Decision - Choosing a Quantization Method]] — weight and KV-cache precision are two independent axes; default fp8+fp8 on Hopper+, drop to AWQ int4 weights when you need more headroom.
- [[Gotchas - Quantization Quality Loss]] — six ways quantized models lose real capability while perplexity looks fine, from proxy-metric traps to hardware precision gating.

## Specialized serving workloads
- [[Concept - MoE Inference and Expert Parallelism]] — serving MoE models by sharding experts across GPUs with all-to-all routing. Cheap in compute per token, expensive in memory and communication.
- [[Concept - Multi-LoRA Serving]] — serving thousands of LoRA adapters over one shared base model via batched heterogeneous-adapter kernels and adapter paging, not N deployments.

## Serving frameworks and engines
- [[Decision - Choosing an Inference Serving Framework]] — how to pick among vLLM, SGLang, TensorRT-LLM, llama.cpp, and TGI for a given hardware and workload; vLLM is the default.
- [[Breakdown - vLLM]] — how vLLM works: PagedAttention plus iteration-level scheduling, and the V1 rewrite defaulting to chunked prefill.
- [[Breakdown - SGLang and RadixAttention]] — SGLang's radix-tree KV cache and compressed-FSM decoding win on shared-prefix, agentic, and structured-output serving workloads.
- [[Breakdown - TensorRT-LLM]] — NVIDIA's ahead-of-time compiled inference engine: peak Hopper/Blackwell throughput traded for build rigidity and slow day-0 support.
- [[Lore - The llama.cpp Insurgency]] — how Georgi Gerganov's dependency-free C++ engine put frontier models on laptops and grew the quant folklore the field runs on.

## Operating in production
- [[Checklist - Pre-Production Inference Readiness]] — pre-flight verification list before an LLM serving deployment takes real traffic: correctness, capacity, reliability, and observability.
- [[Playbook - Tuning an LLM Serving Deployment]] — the ordered procedure to take a model, GPU, and SLO and produce a tuned serving config: baseline, find the knee, tune the knobs, diagnose.
- [[Gotchas - LLM Serving in Production]] — seven pitfalls that bite real LLM deployments, from throughput collapse to silent nondeterminism, ordered by how much pain they cause.

## Adjacent domains
- [[MOC - Hardware & Systems]] — the HBM bandwidth, interconnect, and GPU generation facts that this domain's memory and quantization math treats as fixed constraints.
- [[MOC - Training at Scale]] — the parallelism strategies (tensor, pipeline, expert) that MoE and multi-GPU serving repurpose from the training side of the stack.
- [[MOC - Fine-Tuning]] — LoRA adapters are trained there and served here; multi-LoRA serving only exists because fine-tuning produces cheap, swappable deltas.
- [[MOC - Production & Ops]] — this domain tunes the engine; that one keeps it alive under real traffic with monitoring, rollout, and incident response.
