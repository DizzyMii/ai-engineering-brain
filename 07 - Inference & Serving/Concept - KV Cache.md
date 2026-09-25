---
tags: [concept, domain/inference-serving, level/core]
aliases: [KV cache, key-value cache]
summary: "Caching per-token K/V turns O(N²) attention recompute into O(N) reads — and its memory footprint caps serving concurrency."
---
> **One-paragraph hook:** The KV cache is the most important data structure in LLM serving, ahead of the model weights and the scheduler. It's what makes autoregressive generation tractable at all. Once you understand its memory math, "how many concurrent users can this GPU serve" turns out to be a question about bytes per token, not FLOPs.

## The mechanism

Under a causal mask, token `t`'s key and value projections (`K_t = x_t W_K`, `V_t = x_t W_V`) never change once computed. [[Concept - Attention Mechanism]]'s causal mask guarantees position `t` never attends to future positions, so K and V for every past token can be computed once and reused forever.

Without caching, generating token `N+1` means recomputing attention over all `N` prior tokens from scratch, an `O(N^2)` total cost across a full generation. With caching, each decode step computes a query for only the *new* token and attends over the cached K,V of everything before it. The per-step cost becomes `O(N)` (a read, not a recompute), and the total generation cost is `O(N^2)` amortized as `N` cheap `O(N)` steps instead of `N` increasingly expensive `O(N^2)` recomputations. [[Concept - The Inference Request Lifecycle]]'s prefill/decode split rests on this: prefill fills the cache in one shot, and every decode step after that is a read-and-append.

```
step t:      Q_t  (new query, 1 token)
                │
                ▼
     attend over  [ K_1 V_1 | K_2 V_2 | ... | K_t-1 V_t-1 ]   ← all cached, no recompute
                │
                ▼
     compute K_t, V_t  →  append to cache
                │
                ▼
     step t+1 repeats, cache now has t entries
```

**Memory formula.** The cache stores both K and V, for every layer, every KV head and every position, at some byte width:

$$\text{bytes} = 2 \times n_{\text{layers}} \times n_{\text{kv\_heads}} \times d_{\text{head}} \times \text{seq\_len} \times \text{batch} \times \text{bytes\_per\_elem}$$

Worked example, Llama-3-70B (80 layers, 8 KV heads via grouped-query attention, `d_head=128`, fp16 → 2 bytes/elem):

$$2 \times 80 \times 8 \times 128 \times 2 = 327{,}680 \text{ bytes/token} \approx 0.31\text{ MB/token}$$

One 128K-context sequence costs `327{,}680 \times 131{,}072 \approx 43 \text{ GB}` of KV cache alone. That's the same order of magnitude as the model weights.

## In practice

GQA/MQA are the biggest lever on this number. [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] covers sharing K,V across query heads: Llama-3-70B's 8 KV heads against 64 query heads is an 8x cache reduction versus naive multi-head attention with one KV head per query head, so a *training*-time architecture decision lands directly on the serving-time memory bill. DeepSeek's Multi-Head Latent Attention (MLA, in DeepSeek-V2/V3) goes further: it stores a compressed low-rank latent in place of full per-head K,V and cuts the cache far more than GQA alone.

Cache size grows linearly with both sequence length and batch. The total live KV footprint at any moment is `per_token_bytes × Σ(seq_len over all live requests)`, a sum that changes every scheduling iteration as [[Concept - Continuous Batching]] admits and evicts sequences.

In practice the KV cache limits capacity more than the model weights do. A 70B model at fp16 needs ~140 GB just for weights, so on 80 GB H100s you need two GPUs. Whatever HBM is left after weights and framework overhead (commonly on the order of ~20 GB per GPU) is the whole KV budget, and that number sets max concurrent requests and max context length, far more than the GPU's FLOPs do. Full worked formulas (KV bytes/token across model families, decode step time, max concurrent tokens given VRAM) are in [[Reference - Inference Performance Math]] and its companion [[Reference - Memory Math for Transformers]]. The tuning knobs that trade this budget against throughput are in [[Playbook - Tuning an LLM Serving Deployment]].

| Model | Layers | KV heads | `d_head` | Bytes/token (fp16) |
|---|---|---|---|---|
| Llama-3-8B | 32 | 8 | 128 | 131,072 (~0.13 MB) |
| Llama-3-70B | 80 | 8 | 128 | 327,680 (~0.31 MB) |
| DeepSeek-V3 (MLA) | 61 | latent, compressed | — | far below a dense-GQA equivalent at the same depth |

## Failure modes

- **Mid-generation OOM.** If the live sequences' cumulative KV outgrows the allocated budget, the server can't conjure more HBM. It has to preempt a request (evict, recompute later), which shows up as a sudden latency spike or a dropped request under load. Watch KV utilization and preemption counts, not just GPU memory percentage.
- **Pre-paging fragmentation.** Before block-based allocation, each request reserved one contiguous buffer sized to `max_seq_len`. That lost enormous amounts of memory to internal fragmentation (most requests generate far fewer tokens than the reserved maximum) and external fragmentation (variable-size holes between allocations). The original vLLM paper's motivating analysis measured 60-80% of the KV region wasted. [[Concept - PagedAttention]] is the direct fix, and [[Lore - The KV Cache Fragmentation Crisis]] is the origin story.
- **Underestimating long-context cost in capacity planning.** Cache size scales linearly with each request's sequence length. Advertise a large max context window, size capacity off short average-case prompts, and the service silently degrades or rejects requests once several users hit the full window at once.

## The non-obvious

Training people think about memory in *parameters*. Serving memory is dominated by *live tokens across all in-flight sequences*. A 70B model and an 8B model with the same KV-cache configuration (same layer count, head count, head dim) cost wildly different amounts to hold in weights but can cost *similar* amounts in KV cache per token. Two models with very different parameter counts can end up with surprisingly close serving-concurrency ceilings if their attention configuration wasn't designed (via GQA/MLA) to shrink the cache. Architecture teams increasingly treat KV-cache size as a design target next to parameter count and training FLOPs.

## Connections
- [[Concept - Prefill and Decode Phases]] — the prerequisite split this note assumes: prefill writes the cache in one pass, decode reads and appends to it every step.
- [[Concept - The Inference Request Lifecycle]] — the request-level loop this cache's populate-then-read pattern is embedded in.
- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — the architecture-level techniques (GQA, MQA, MLA) that are the dominant lever for shrinking this memory formula.
- [[Concept - PagedAttention]] — the block-based memory manager that eliminated the fragmentation this cache's naive allocation caused.
- [[Concept - KV Cache Quantization]] — reducing `bytes_per_elem` in the formula above as a second, orthogonal lever beyond architecture changes.
- [[Reference - Memory Math for Transformers]] — the fuller memory reference this formula is one entry in, alongside weights and activation memory.
- [[Reference - Inference Performance Math]] — the worked per-model, per-GPU numbers this note's formula feeds into.
- [[Concept - GPU Memory Hierarchy]] — the HBM capacity and bandwidth constraints that make this cache's size a hard operational ceiling, not just a cost line item.
- [[Concept - Attention Mechanism]] — the causal-masking property (`K_t, V_t` never change) that is the entire reason caching is valid in the first place.
- [[Concept - Automatic Prefix Caching]] — reusing already-computed KV blocks *across* requests that share a prefix, building directly on this per-request cache.
- [[Concept - Continuous Batching]] — the scheduler whose admit/evict decisions every iteration are what make the live-KV sum change constantly.
- [[Playbook - Tuning an LLM Serving Deployment]] — the operational procedure for trading this cache's budget against throughput and context length.
- [[Lore - The KV Cache Fragmentation Crisis]] — the war story behind why naive KV allocation was untenable at production scale.

## Sources
- Kwon et al. (2023, SOSP) — "Efficient Memory Management for Large Language Model Serving with PagedAttention." Measures the 60-80% fragmentation waste of naive contiguous KV allocation and motivates the memory model this note describes.
- Ainslie et al. (2023) — "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints." The grouped-query attention technique behind the 8x cache reduction cited above.
- DeepSeek-AI (2024) — "DeepSeek-V2" technical report. Introduces Multi-Head Latent Attention (MLA), the compressed-latent KV representation used as the further-reduction example.
