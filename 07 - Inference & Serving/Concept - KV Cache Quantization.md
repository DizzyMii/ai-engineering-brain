---
tags: [concept, domain/inference-serving, level/frontier]
aliases: [KV quantization, KV cache quant, KIVI]
summary: "Quantizing the KV cache (not the weights) to fit more context or concurrency, and why keys and values need different treatment."
---
> **One-paragraph hook:** At long context and high batch, the memory ceiling is the [[Concept - KV Cache]], not the model weights, so halving its precision is often a bigger practical win than quantizing weights at all. Reusing the recipe you'd apply to weights breaks quietly, though. Keys and values have different statistical structure and need different quantization axes to survive below 8 bits.

## The mechanism

The KV cache's memory formula: bytes = 2 × n_layers × n_kv_heads × head_dim × seq_len × batch × bytes_per_elem. Every term but the last is an architecture decision fixed at training time; [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] (GQA/MQA/MLA) already shrank n_kv_heads or replaced K,V with a compressed latent. `bytes_per_elem` is the one lever left at serve time, and it's a pure multiplier. Going from fp16 (2 bytes) to fp8 (1 byte) halves KV memory. Int4 (~0.5 byte effective, plus per-group scale overhead) roughly quarters it.

[[Concept - Post-Training Quantization Formats|Weight quantization]] mostly saves memory and bandwidth without touching FLOPs (weight-only int4 still dequantizes to bf16 inside the matmul). KV quantization saves bandwidth too: less K,V is read from HBM on every decode step, and decode is memory-bandwidth-bound by construction. So it's a latency lever as well as a capacity lever.

The catch is that keys and values aren't statistically interchangeable. Keys feed the attention dot-product (`Q·K^T`) and develop large **per-channel** outliers: certain dimensions of the key vector carry outsized magnitude across most tokens, and a single per-tensor scale destroys that pattern. Values are consumed as a weighted sum (`softmax(scores)·V`). They're comparatively well-behaved *within a token* but vary more **across tokens**. KIVI (Liu et al. 2024) built its scheme around this asymmetry. It quantizes keys **per-channel** (one scale shared down the time axis for each feature dimension) and values **per-token** (one scale shared across the feature axis for each timestep), following each tensor's own axis of variation.

```
Keys — one scale per channel (column), shared across all cached tokens:
          d0     d1     d2   ...  d_head
  t0  [ s_d0·i  s_d1·i  s_d2·i ... ]
  t1  [ s_d0·i  s_d1·i  s_d2·i ... ]   ← same scale reused down each column
  ...

Values — one scale per token (row), shared across all feature dims:
          d0     d1     d2   ...
  t0  [ s_t0·i  s_t0·i  s_t0·i ...]   ← one scale per row
  t1  [ s_t1·i  s_t1·i  s_t1·i ...]
```

With the asymmetry handled, KIVI gets to **2-bit KV** with modest quality loss. A naive symmetric, per-tensor scheme collapses well before that.

There's a second sensitivity. The first handful of tokens in a sequence act as [[Concept - Attention Sinks]] and absorb a disproportionate share of attention mass whatever their semantic content. Quantizing sink tokens as coarsely as the rest damages output far more than quantizing an arbitrary mid-sequence token. Keeping the first few positions in higher precision (or unquantized) recovers quality cheaply, and it's a small targeted exception, with no global precision bump needed.

## In practice

[[Breakdown - vLLM]] and [[Breakdown - TensorRT-LLM]] both expose fp8 KV cache as a serving flag (`--kv-cache-dtype fp8` in vLLM), giving roughly 2x KV capacity at near-lossless quality on Hopper-generation GPUs and newer. The format itself is covered in [[Concept - FP8 and Low-Precision Inference]]. In 2026 deployments it's treated as close to a free lunch: turn it on and get double the context or double the concurrency at the same VRAM budget, with quality loss usually below what standard evals pick up. Int4 KV is the aggressive option, kept for extreme-context deployments or memory-desperate fleets. Its quality risk is materially higher and needs task-level validation; a perplexity check isn't enough.

The kernel cost is real but small. The attention kernel can't read K,V directly anymore and has to dequantize on the fly for every dot-product, which adds compute and kernel complexity in exchange for the memory and bandwidth win. In decode that's an easy trade. Decode is bandwidth-bound and has spare compute, because of the memory-bandwidth asymmetry described in [[Concept - Prefill and Decode Phases]], so the dequant cost is close to free where it matters most.

## Failure modes

Quality cliffs on long-context retrieval (needle-in-haystack accuracy, multi-hop reasoning over a long document) show up well before perplexity moves. Perplexity is already a weak sanity check for [[Concept - Post-Training Quantization Formats|weight quantization]] (see [[Gotchas - Quantization Quality Loss]]), and it's even less trustworthy here. KV quant errors compound across every later attention computation that reads the corrupted cache, so a small per-token error can silently degrade the model's ability to find information dozens of thousands of tokens back. To detect it, run a real long-context retrieval eval at your target context length before and after enabling KV quant. A WikiText perplexity diff won't do it.

Two missteps recur: quantizing the attention-sink tokens as coarsely as everything else, and using symmetric (zero-centered) quantization on keys whose outlier channels aren't zero-centered. Both cause degradation out of proportion to their apparent bit-width savings.

## The non-obvious

Most quantization effort in the field still goes to the weights, because that's the number everyone quotes ("a 4-bit 70B model"). The point where the KV cache dwarfs weight memory arrives sooner than intuition suggests. Weight memory is fixed regardless of context length; KV memory grows linearly with it. At long enough context (tens of thousands of tokens, easily reached by agent transcripts or RAG-stuffed prompts) the VRAM goes to the cache. Teams that quantize weights aggressively and leave the KV cache at fp16 are often optimizing the wrong line item for their workload.

The K/V asymmetry is the second surprise. It's tempting to read "quantize the cache" as one recipe applied uniformly. That assumption caps naive schemes around 4-8 bits, while axis-aware schemes like KIVI reach 2 bits on the same quality budget.

## Connections
- [[Concept - KV Cache]] — the resource being compressed; the memory formula this note's `bytes_per_elem` lever operates on.
- [[Concept - Post-Training Quantization Formats]] — the weight-quantization sibling; contrast bandwidth-only savings there against bandwidth-and-capacity savings here.
- [[Concept - Attention Sinks]] — cross-domain (18) grounding: the reason the first few cached tokens need special-cased higher precision.
- [[Concept - KV Cache Offloading and Compression]] — the complementary lever (drop or tier tokens instead of shrinking their precision); the two compose.
- [[Concept - FP8 and Low-Precision Inference]] — the hardware format most production KV quantization actually uses.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — cross-domain (03) grounding: the architecture-level lever (fewer KV heads, compressed latents) that KV quantization compounds with.
- [[Gotchas - Quantization Quality Loss]] — the general pitfall (perplexity as a weak proxy) sharpened here by compounding attention errors.
- [[Reference - Memory Math for Transformers]] — cross-domain (08) grounding: the fuller memory reference this note's formula is one entry in.
- [[Lore - The llama.cpp Insurgency]] — the community that pioneered aggressive, informally-benchmarked quantization culture and shipped quantized KV cache options (`--cache-type-k`/`-v`) well ahead of most production stacks.

## Sources
- Liu, Z. et al. (2024) — *"KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache."* The per-channel-key / per-token-value asymmetric scheme this note's mechanism section is built around.
- Xiao, G. et al. (2023) — *"Efficient Streaming Language Models with Attention Sinks."* Establishes the attention-sink phenomenon that motivates keeping the first few cached tokens at higher precision.
