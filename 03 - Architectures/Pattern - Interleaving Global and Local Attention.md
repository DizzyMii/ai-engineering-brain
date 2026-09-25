---
tags: [pattern, domain/architectures, level/frontier]
aliases: [local-global attention, sliding-window global interleave, alternating attention, mixed local global attention]
summary: "Alternate cheap local sliding-window layers with a minority of global layers to bound KV cache while keeping long-range recall."
---

# Pattern - Interleaving Global and Local Attention

> **Problem:** full attention in every layer costs `O(N²)` compute and a KV cache that grows linearly with context in *every* layer. Making every layer local (sliding-window) throws away exact long-range recall. **Solution shape:** make most layers local and add a minority of full-context global layers. The model keeps long-range mixing, and the KV cache is dominated by the few global layers.

## Context & forces

The forces are recall, compute, and KV-cache memory at serve time. Memory is what drives 2024–2025 designs.

- **Full attention** ([[Concept - Attention Mechanism]]) gives exact recall over the whole context but costs `O(N²·d)` per layer. Worse for serving, it keeps a per-layer [[Concept - KV Cache]] of `2·n_layers·n_kv_heads·d_head·N` elements. At long `N` and high batch, the cache fills the GPU before the weights do.
- **Sliding-window (local) attention** ([[Concept - Sparse and Sliding-Window Attention]]) caps each token's attention to the previous `w` tokens, so per-layer cache is bounded by `w` instead of `N`. Information more than `w` away is reachable only by hopping through depth, which degrades exact copy/retrieval.
- You don't need long-range mixing in every layer. A few global layers move information across the full context; the local majority does the cheap within-window work. It's the attention-side cousin of the SSM/attention split in [[Concept - Hybrid SSM-Attention Architectures]]: cheap majority plus a few expensive recall layers, with a different cheap primitive.

## The pattern

Stack local (sliding-window) layers and insert a global (full-context) layer every `k` layers. Only the global layers hold a full-length KV cache.

```mermaid
flowchart TB
    subgraph S["Decoder stack — 5:1 local:global (Gemma 3 pattern)"]
        direction TB
        L1["L1 local · w=1024 · KV≤w"]
        L2["L2 local · KV≤w"]
        L3["L3 local · KV≤w"]
        L4["L4 local · KV≤w"]
        L5["L5 local · KV≤w"]
        G6["L6 GLOBAL · full ctx · KV=N"]
        L7["L7 local · KV≤w  ..."]
        L1 --> L2 --> L3 --> L4 --> L5 --> G6 --> L7
    end
    style G6 fill:#c1666b,stroke:#000,color:#fff
```

Receptive field grows two ways. Within a run of local layers, depth stacks windows (`L` local layers reach `~L·w`). Each global layer resets reach to the entire context in one hop. So the model never has a blind spot longer than one global-layer interval.

The KV-cache payoff for 40 layers, context `N = 32k`, window `w = 1k`:

```
All-global:   40 layers × 32k  = 1,280k KV "rows" / token-dim
5:1 mix:      ~7 global × 32k + 33 local × 1k = 224k + 33k ≈ 257k
              → ~5× smaller KV cache, same context length
```

That multiplier is why the pattern exists: for most of the stack, memory goes from linear in context to near-constant.

## Implementation notes

- **Ratio and window are the main knobs.** Gemma 2 used a **1:1** local:global interleave with a **4096** window. Gemma 3 moved to **5:1** with a **1024** window specifically to shrink the KV cache further for long-context serving. More global layers buys retrieval at the price of cache; the ratio is where you spend your memory budget.
- **Placement:** periodic (every `k`-th layer is global) is the common choice. A few designs front-load or back-load global layers. Periodic keeps KV-paging bookkeeping simplest.
- **Global and local layers can use different RoPE settings.** Gemma 3, for instance, uses a larger [[Concept - Rotary Position Embeddings (RoPE)]] base on the global layers, which must span the full context, than on the local layers, which only ever rotate within `w`. Assume one base for all layers and a port breaks silently.
- **Attention sinks interact with the window.** Streaming-style local attention destabilizes unless it retains the first few tokens. The [[Concept - Attention Sinks]] phenomenon is why StreamingLLM keeps a few "sink" tokens alongside the sliding window.
- **Kernel support is the hidden cost.** [[Deep Dive - FlashAttention]] and mature serving stacks handle uniform full or uniform sliding-window attention well. A *mixed* per-layer pattern needs the engine to track two cache geometries and dispatch the right masked kernel per layer. That's real engineering work, not a config flag.

## Tradeoffs & when NOT to use

- **Retrieval-heavy or long-range-exact workloads** (needle-in-haystack, long-document QA, code with distant references) may need more global layers. A 5:1 mix trades measurable long-range accuracy for memory. Test on *your* long-context task; passkey retrieval passes far too early.
- **KV-cache paging gets harder.** Two cache geometries per model complicate prefix caching and block allocation in the serving layer ([[Concept - KV Cache]]).
- **When NOT to use:** short-context models (if `N ≲ w` the pattern buys nothing), or a serving stack without mixed-pattern kernel support where the eng cost outweighs the memory win. For a from-scratch long-context model where recall matters most and memory isn't the limit, uniform full attention is still the safe default. If *training* compute is your limit and serving memory isn't, an SSM/linear hybrid or logit-stabilized full attention ([[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]], as in the same Gemma line) may be the better lever.

## Known uses

- **Gemma 2 (Google, 2024):** 1:1 local:global interleave, 4096-token sliding window. The design that popularized the pattern in an open model.
- **Gemma 3 (Google, 2025):** 5:1 local:global, 1024-token window, explicitly to cut long-context KV memory.
- **OpenAI gpt-oss (2025):** alternates full-context and sliding-window (banded) attention layers, echoing GPT-3's original alternating dense/locally-banded scheme.
- **Cohere Command (2025):** interleaves sliding-window layers with periodic full-attention layers for efficient long-context serving.
- **Character.AI inference work (Shazeer's team, 2024):** local sliding-window attention with a small minority of global layers plus cross-layer KV sharing, reported to cut KV cache by ~20× (company engineering blog; treat the exact multiplier as company-claimed).
- **Ancestors:** Longformer (Beltagy et al. 2020) with window + global tokens, and Sparse Transformer (Child et al. 2019) with alternating local/strided factorized attention.

## Connections

- [[Concept - Sparse and Sliding-Window Attention]] — the local primitive this pattern interleaves; the down-link to the sliding-window mechanism and its receptive-field math.
- [[Concept - Attention Mechanism]] — the full-attention baseline the global layers preserve and the pattern economizes on.
- [[Concept - Hybrid SSM-Attention Architectures]] — the same "cheap majority + a few recall layers" idea with SSM/linear layers as the cheap primitive instead of local attention.
- [[Concept - KV Cache]] — the serving-memory term this pattern exists to bound; the payoff calculation lives here.
- [[Deep Dive - FlashAttention]] — the kernel whose mixed-pattern support is the hidden implementation cost.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the per-layer base-θ subtlety (different bases for local vs global layers) that trips up ports.
- [[Concept - Attention Sinks]] — why sliding-window local layers must retain the first tokens to stay stable.
- [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]] — the companion Gemma-line technique for stability; the up-link to the deeper, unicorn-tier tricks shipped alongside this pattern.

## Sources

- Gemma Team (2024) — *Gemma 2 Technical Report.* 1:1 local/global interleave, 4096 window.
- Gemma Team (2025) — *Gemma 3 Technical Report.* 5:1 local/global, 1024 window, explicitly for KV-cache reduction on long context.
- Beltagy et al. (2020) — *Longformer.* Sliding window + global tokens, the direct ancestor.
- Child et al. (2019) — *Generating Long Sequences with Sparse Transformers.* Alternating local/strided factorized attention.
- Character.AI (2024) — *Optimizing AI Inference* (engineering blog). Local/global interleave + cross-layer KV sharing, ~20× KV reduction (company-claimed).
