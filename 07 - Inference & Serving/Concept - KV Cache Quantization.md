---
tags: [concept, domain/inference-serving, level/frontier]
aliases: [KV quantization, KV cache quant, KIVI]
summary: "Quantizing the KV cache (not the weights) to fit more context or concurrency, and why keys and values need different treatment."
---
> **One-paragraph hook:** At long context and high batch, the [[Concept - KV Cache]] — not the model weights — is the memory ceiling, so halving its precision is often a bigger practical win than quantizing weights at all. But naively applying the same recipe you'd use for weights breaks quietly: keys and values have different statistical structure and need different quantization axes to survive below 8 bits.

## The mechanism

Recall the KV cache's memory formula: bytes = 2 × n_layers × n_kv_heads × head_dim × seq_len × batch × bytes_per_elem. Every lever in that formula except the last one is an architecture decision baked in at training time — [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] (GQA/MQA/MLA) already did the work of shrinking n_kv_heads or replacing K,V with a compressed latent. `bytes_per_elem` is the one lever still available at serve time, and it's a pure multiplier: dropping fp16 (2 bytes) to fp8 (1 byte) halves KV memory outright; int4 (~0.5 byte effective, plus per-group scale overhead) roughly quarters it. Unlike [[Concept - Post-Training Quantization Formats|weight quantization]], which mostly saves memory and bandwidth without touching FLOPs (weight-only int4 still dequantizes to bf16 inside the matmul), KV quantization saves bandwidth too: less K,V is read from HBM on every decode step, and decode is memory-bandwidth-bound by construction, so this is a direct latency lever as well as a capacity lever.

The complication is that keys and values are not statistically interchangeable. Keys feed the attention dot-product (`Q·K^T`) and develop large **per-channel** outliers — certain dimensions of the key vector carry disproportionate magnitude across most tokens, a pattern that a single per-tensor scale destroys. Values are consumed as a weighted sum (`softmax(scores)·V`) and are comparatively well-behaved *within a token* but vary more **across tokens**. KIVI (Liu et al. 2024) is the scheme that took this asymmetry seriously: quantize keys **per-channel** (one scale shared down the time axis, for each feature dimension) and values **per-token** (one scale shared across the feature axis, for each timestep) — respecting each tensor's actual axis of variation instead of applying one blanket recipe to both.

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

Getting this asymmetry right is what lets KIVI push to **2-bit KV** with modest quality loss — a naive symmetric, per-tensor scheme collapses well before that.

There's a second structural sensitivity: the first handful of tokens in a sequence act as [[Concept - Attention Sinks]], absorbing a disproportionate share of attention mass regardless of their semantic content. Quantizing sink tokens as coarsely as the rest of the sequence damages output far more than quantizing an arbitrary mid-sequence token, so schemes that keep the first few positions in higher precision (or unquantized) recover quality cheaply — a small, targeted exception rather than a global precision bump.

## In practice

Both [[Breakdown - vLLM]] and [[Breakdown - TensorRT-LLM]] expose fp8 KV cache as a serving flag (`--kv-cache-dtype fp8` in vLLM) for roughly 2x KV capacity at near-lossless quality on Hopper-generation GPUs and newer — see [[Concept - FP8 and Low-Precision Inference]] for the format itself. This is treated as close to a free lunch in 2026 deployments: turn it on, get double the context or double the concurrency at the same VRAM budget, with quality loss usually below what shows up in standard evals. Int4 KV is the more aggressive option, reserved for extreme-context deployments or genuinely memory-desperate fleets, since its quality risk is materially higher and needs task-level validation, not just a perplexity check.

The kernel cost is real but small: the attention kernel can no longer read K,V directly — it must dequantize on the fly for every dot-product, adding compute and kernel complexity in exchange for the memory and bandwidth win. This is a straightforward trade in the decode phase, since decode has spare compute (it's bandwidth-bound) precisely because of the memory-bandwidth asymmetry [[Concept - Prefill and Decode Phases]] describes — the dequant cost is close to free where it matters most.

## Failure modes

Quality cliffs on long-context retrieval — needle-in-haystack accuracy, multi-hop reasoning over a long document — appear well before perplexity moves, which means the standard proxy metric used to sanity-check [[Concept - Post-Training Quantization Formats|weight quantization]] (see [[Gotchas - Quantization Quality Loss]]) is even less trustworthy here: KV quant errors compound across every subsequent attention computation that reads the corrupted cache, so a small per-token error can silently degrade the model's ability to locate information dozens of thousands of tokens back. Detection requires an actual long-context retrieval eval at your target context length, run before and after enabling KV quant — not a WikiText perplexity diff. Two specific missteps recur: quantizing the attention-sink tokens as coarsely as everything else, and using symmetric (zero-centered) quantization on keys whose outlier channels are not zero-centered — both cause disproportionate degradation relative to their apparent bit-width savings.

## The non-obvious

Most quantization effort in the field still defaults to the weights, because that's the number everyone quotes ("a 4-bit 70B model"). But the crossover point where the KV cache dwarfs weight memory arrives faster than intuition suggests: weight memory is fixed regardless of context length, while KV memory grows linearly with it, so at long enough context (tens of thousands of tokens, easily reached by agent transcripts or RAG-stuffed prompts) the cache — not the weights — is where the VRAM actually goes. Teams that quantize weights aggressively and leave the KV cache at fp16 are often optimizing the wrong line item for their actual workload. The second non-obvious point is the K/V asymmetry itself: it's tempting to assume "quantize the cache" means one recipe applied uniformly, and that assumption is exactly what caps naive schemes around 4-8 bits while axis-aware schemes like KIVI reach 2 bits with the same quality budget.

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
