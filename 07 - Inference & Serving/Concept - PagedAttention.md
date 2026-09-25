---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [paged attention, block-based KV cache]
summary: "Virtual-memory-style paging of the KV cache into fixed blocks, cutting KV waste from 60-80% to under 4% and enabling continuous batching."
---

> **One-paragraph hook:** Before 2023, every serving stack reserved one contiguous [[Concept - KV Cache]] buffer of `max_seq_len` per request, because attention kernels assumed contiguous K,V memory. Most of that reservation sat empty. PagedAttention (Kwon et al., SOSP 2023) applies the operating-system idea of virtual memory to the KV cache: split it into fixed-size blocks, place them anywhere in physical GPU memory, and index them with a per-request page table. It is the single change that made high-concurrency LLM serving economically viable.

## The mechanism

A request's KV cache grows one token at a time, and nobody knows its final length in advance. Pre-PagedAttention systems handled this the naive way. They allocated a worst-case buffer (`max_seq_len`) up front, contiguous in memory, because the attention kernel reads K and V as a contiguous array. That causes two kinds of waste:

- **Internal fragmentation.** A request that generates 200 tokens still holds a buffer reserved for, say, 4096, and the unused tail is wasted for the request's whole lifetime.
- **External fragmentation.** As requests with different reserved sizes finish and free their buffers, the freed regions leave holes too small or oddly shaped for the next allocation, even when total free memory would be enough.

The vLLM paper measured **60-80% of the KV memory region wasted** in contemporary stacks. Effective batch size, and with it GPU utilization, was capped far below what the hardware could handle.

The fix is a direct transplant of OS virtual memory:

1. Partition each request's KV cache into fixed-size **blocks** (16 tokens is the common default).
2. Allocate physical blocks **on demand** as the sequence grows, from anywhere in a shared physical block pool. No contiguity required.
3. Keep a per-request **block table** mapping *logical* block index (0, 1, 2, … in generation order) to *physical* block address in GPU memory.
4. The attention kernel walks the block table and **gathers** K,V from scattered physical blocks instead of reading one contiguous span.

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

The mapping is the OS one: logical block index is the "virtual page number," the block table is the "page table," and the block pool is "physical memory." A finished request's blocks go straight back to the pool for any other request, so fragmentation can't build up. The only waste left is internal fragmentation *inside the last, partially filled block* of each sequence: at most (block_size − 1) unused tokens per request, which keeps total waste under 4%.

## In practice

Block size is a trade between two costs. Smaller blocks (e.g. 16) waste less of the last block but mean more block-table entries and more per-step gather overhead in the kernel. Larger blocks cut that overhead and waste more of the last block. 16 tokens has become the de facto default in engines that implement this design.

Since blocks are just pointers into a shared pool, **copy-on-write sharing comes free**. If two sequences share a logical prefix (beam-search candidates, or two requests with the same system prompt), their block tables can point at the *same* physical blocks for the shared region and only fork (copy) a block once one sequence writes past the divergence point. [[Concept - Automatic Prefix Caching]] builds on this to skip prefill for repeated prompts. Prefix caching is the same block-table trick applied *across* requests instead of within one.

Paging is also what [[Concept - Continuous Batching]] runs on. Iteration-level scheduling has to admit a new request into a running batch mid-flight, so it needs KV for that request *right now*, with no wait for a contiguous region to free up. Contiguous allocation can't do per-iteration admission; paged allocation turns it into an O(1) block-table update. That's why the two shipped together in [[Breakdown - vLLM]] and most engines have treated them as one package since.

The cost shows up in the kernel. A fused, contiguous-KV attention kernel (the kind [[Deep Dive - FlashAttention]] popularized) streams K,V linearly through SRAM with predictable access. A paged kernel first resolves the block table, then gathers from scattered addresses. That's less cache-friendly, and historically it ran somewhat slower per FLOP than the best fused contiguous kernels. Engines accept the tax on purpose: the memory win (2-4x more concurrent requests) outweighs the modest per-kernel slowdown at realistic batch sizes, and vendors have since shipped custom paged-attention CUDA/Triton kernels that close most of the gap. The [[Concept - GPU Memory Hierarchy]] explains why. Paging exists to put as much scarce HBM capacity as possible into *useful* KV instead of reservation slack, because HBM capacity, not FLOPs, usually limits concurrency (see [[Reference - Memory Math for Transformers]]).

## Failure modes

- **Cross-request KV corruption.** A block-table bookkeeping bug (a stale pointer, a block freed and reassigned while still referenced) silently mixes one request's key/value data into another's attention. You see inexplicable garbage output on a request that otherwise looks fine. It's one of the nastier bug classes to chase because the corruption is data-dependent and intermittent.
- **Block-size mistuning.** Blocks that are too small add per-step lookup and gather overhead, visible as higher inter-token latency under load. Blocks that are too large silently bring back the internal fragmentation the design exists to remove, raising effective KV-per-token cost and lowering achievable concurrency.
- **Paged kernel latency regression.** PagedAttention has historically trailed the best fused, contiguous-memory kernel on raw per-step latency. If you benchmark against a hand-tuned contiguous baseline and see a regression, check that you're comparing memory-efficiency-adjusted throughput (the metric that matters) and not raw single-request kernel time.

## The non-obvious

The surprise is how old and boring the idea is. LLM serving had put real effort into kernel micro-optimization while losing 60-80% of memory to an allocation problem operating systems solved in the 1960s-70s. The lesson practitioners draw (covered at length in [[Lore - The KV Cache Fragmentation Crisis]]): when a system feels compute-bound, ask whether the bottleneck is actually in the *memory management layer*. If the allocator, not the arithmetic, is where the waste lives, a systems-level fix can dwarf any amount of kernel tuning.

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
