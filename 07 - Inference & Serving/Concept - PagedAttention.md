---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [paged attention, block-based KV cache]
summary: "Virtual-memory-style paging of the KV cache into fixed blocks, cutting KV waste from 60-80% to under 4% and enabling continuous batching."
---

> **One-paragraph hook:** Before 2023, every serving stack reserved one contiguous [[Concept - KV Cache]] buffer of `max_seq_len` per request, because attention kernels assumed contiguous K,V memory — and most of that reservation sat empty. PagedAttention (Kwon et al., SOSP 2023) applies the operating-system idea of virtual memory to the KV cache: split it into fixed-size blocks, place them anywhere in physical GPU memory, and index them with a per-request page table. It is the single change that made high-concurrency LLM serving economically viable.

## The mechanism

A request's KV cache grows one token at a time and its final length is unknown in advance. Pre-PagedAttention systems dealt with this the naive way: allocate a buffer sized for the worst case (`max_seq_len`) up front, contiguous in memory, because the attention kernel needs to read K and V as a contiguous array. Two kinds of waste follow immediately:

- **Internal fragmentation** — a request that generates 200 tokens still holds a buffer reserved for, say, 4096, and the unused tail is wasted for the request's entire lifetime.
- **External fragmentation** — as requests of different reserved sizes complete and free their buffers, the freed regions leave holes too small or oddly shaped to satisfy the next allocation, even though total free memory would be sufficient.

The vLLM paper measured this at **60-80% of the KV memory region wasted** in contemporary stacks — meaning the effective batch size, and therefore GPU utilization, was capped far below what the hardware could support.

PagedAttention's fix is a direct transplant of OS virtual memory:

1. Partition each request's KV cache into fixed-size **blocks** (16 tokens is the common default).
2. Allocate physical blocks **on demand** as the sequence grows, from anywhere in a shared physical block pool — no contiguity requirement.
3. Maintain a per-request **block table**: a mapping from *logical* block index (0, 1, 2, … in generation order) to *physical* block address in GPU memory.
4. The attention kernel, instead of reading one contiguous span, walks the block table and **gathers** K,V from scattered physical blocks.

```
Request A (logical view)          Physical GPU memory (block pool)
 block 0 -> physical block 7      ┌────┬────┬────┬────┬────┬────┬────┐
 block 1 -> physical block 2      │ B2 │ B5 │ B9 │ B7 │ B1 │ B4 │ B8 │  ...
 block 2 -> physical block 9      └────┴────┴────┴────┴────┴────┴────┘
                                     ^ blocks allocated to different
Request B (logical view)              requests interleave freely;
 block 0 -> physical block 5           none needs to be contiguous
 block 1 -> physical block 1           with the rest of its own sequence
```

This is exactly the OS relationship between a process's virtual address space and physical page frames — logical block index is the "virtual page number," the block table is the "page table," and the physical block pool is "physical memory." Blocks are freed the instant a request completes and immediately become available to any other request, so there is no fragmentation-by-construction: waste is bounded by internal fragmentation *within the last, partially-filled block* of each sequence — at most (block_size − 1) tokens of unused space per request, driving total waste under 4%.

## In practice

Block size trades off two costs directly: smaller blocks (e.g. 16) mean less internal fragmentation but more block-table entries and more per-step gather overhead in the kernel; larger blocks reduce that overhead but waste more of the last block. 16 tokens has become the de facto default across engines that implement this design.

Because blocks are just pointers into a shared pool, PagedAttention gets **copy-on-write sharing for free**: if two sequences share a logical prefix (beam-search candidates, or two requests with an identical system prompt), their block tables can point at the *same* physical blocks for the shared region, and only fork (copy) a block once one sequence writes past the point of divergence. This sharing mechanism is exactly what [[Concept - Automatic Prefix Caching]] builds on to skip prefill for repeated prompts — prefix caching is PagedAttention's block-table trick applied *across* requests instead of only within one.

The paging model is also the enabling substrate for [[Concept - Continuous Batching]]: iteration-level scheduling needs to admit a brand-new request into a running batch mid-flight, which means allocating KV for it *right now* without waiting for a contiguous region to free up. Contiguous allocation and per-iteration admission are fundamentally incompatible; paged allocation makes admission an O(1) block-table update. This is why PagedAttention and continuous batching shipped together in [[Breakdown - vLLM]] and are treated as a single package in most engines since.

The cost of the design lives in the kernel. A fused, contiguous-KV attention kernel (the kind [[Deep Dive - FlashAttention]] popularized) can stream K,V linearly through SRAM with predictable memory access; a paged kernel must first resolve the block table and then gather from scattered addresses, which is less cache-friendly and historically ran somewhat slower per FLOP than the best fused contiguous kernels. Engines pay this tax deliberately — the memory win (2-4x more concurrent requests) dominates the modest per-kernel slowdown at realistic batch sizes, and vendors have since shipped custom paged-attention CUDA/Triton kernels that close most of the gap. The [[Concept - GPU Memory Hierarchy]] context matters here: the whole point of paging is to maximize how much of scarce HBM capacity goes to *useful* KV rather than reservation slack, since HBM capacity — not FLOPs — is usually the binding constraint on concurrency (see [[Reference - Memory Math for Transformers]]).

## Failure modes

- **Cross-request KV corruption.** A bug in block-table bookkeeping — a stale pointer, a block freed and reassigned while still referenced — silently mixes one request's key/value data into another's attention computation. This shows up as bizarre, unexplainable garbage output for a request that otherwise looks fine, and it is one of the nastier classes of bugs to chase down because the corruption is data-dependent and intermittent.
- **Block-size mistuning.** Too small a block size adds per-step block-table lookup and kernel-gather overhead that shows up as elevated inter-token latency under load; too large a block size silently reintroduces the internal fragmentation the whole design exists to eliminate, inflating the effective KV-per-token cost and lowering achievable concurrency.
- **Paged kernel latency regression.** Compared to the best fused, contiguous-memory attention kernel, PagedAttention historically trailed on raw per-step latency — teams benchmarking against a hand-tuned contiguous baseline and seeing a regression should check whether they're comparing memory-efficiency-adjusted throughput (the real metric) rather than raw single-request kernel time.

## The non-obvious

The genuinely surprising part isn't the paging idea itself — it's *how old and boring* the underlying insight is. LLM serving had spent real effort on kernel micro-optimization while leaving 60-80% of memory on the table to an allocation-strategy problem operating systems solved in the 1960s-70s. The lesson practitioners take from this (documented at length in [[Lore - The KV Cache Fragmentation Crisis]]) is to periodically ask, when a system feels compute-bound, whether the real bottleneck is actually in the *memory management layer* rather than the kernel — because a systems-level fix can dwarf any amount of kernel tuning if the allocator, not the arithmetic, is where the waste lives.

## Connections
- [[Concept - KV Cache]] — PagedAttention is a memory-management scheme *for* the KV cache; you cannot understand the fix without the problem it fixes.
- [[Breakdown - vLLM]] — the system that introduced PagedAttention and shipped it as the default KV allocator.
- [[Concept - Continuous Batching]] — depends on paged, on-demand KV allocation to admit new requests mid-iteration; the two techniques are a matched pair.
- [[Concept - Automatic Prefix Caching]] — reuses PagedAttention's copy-on-write block sharing across requests, not just within one.
- [[Concept - GPU Memory Hierarchy]] — the HBM capacity constraint that makes eliminating KV waste worth a custom allocator and kernel in the first place.
- [[Lore - The KV Cache Fragmentation Crisis]] — the origin story: how bad the pre-2023 waste was and how the OS-paging analogy fixed it field-wide within about a year.
- [[Deep Dive - FlashAttention]] — the fused contiguous-memory attention kernel design that PagedAttention's gather-based kernel trades some raw speed against for its memory win.
- [[Reference - Memory Math for Transformers]] — the formulas for KV bytes/token that quantify exactly how much memory paging recovers.
- [[Concept - Attention Mechanism]] — the computation PagedAttention's kernel must still correctly perform, now over scattered physical blocks instead of a contiguous span.

## Sources
- Kwon et al. (2023) — *Efficient Memory Management for Large Language Model Serving with PagedAttention* (SOSP 2023). Introduces PagedAttention and the vLLM system; measures 60-80% KV waste in prior systems and the reduction to under 4%.
