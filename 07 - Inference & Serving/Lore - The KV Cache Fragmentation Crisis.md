---
tags: [lore, domain/inference-serving, level/unicorn]
aliases: [PagedAttention origin story, KV fragmentation crisis]
summary: "How LLM serving wasted 60-80% of GPU memory to KV fragmentation until PagedAttention reframed it as an OS paging problem."
---
> **How the whole field wasted most of its most expensive resource, GPU memory, for over a year by working on the wrong problem in the wrong layer, until a Berkeley systems group noticed it was a textbook operating-systems bug in disguise.**

## What happened

Through 2022 and into early 2023, every mainstream LLM serving stack made the same design decision. HuggingFace `generate`, NVIDIA FasterTransformer and the earliest TGI all did it: when a request arrived, they **pre-allocated one contiguous block of GPU memory big enough for the [[Concept - KV Cache]] of `max_seq_len` tokens.** That's the *maximum the request might ever* generate, not what it would actually generate. The reason was the attention kernels of the day, which assumed a sequence's keys and values lived in one contiguous, tightly strided buffer. Nobody had a kernel that could gather K,V from scattered locations yet.

The consequence was brutal and hard to see. Real requests are short and vary wildly: a chat turn might be 40 tokens against a 2048-token reservation. The buffer sat **mostly empty for the request's whole lifetime** (internal fragmentation). When requests of different sizes finished and freed their buffers, they left oddly sized holes that no new contiguous reservation could fit into (external fragmentation). The vLLM paper later measured it: **60–80% of the KV memory region was wasted.** On an 80 GB H100 with maybe ~20 GB left for KV after weights, four-fifths of *that* went to fragmentation.

Memory is what limits how many requests you can batch (see [[Reference - Memory Math for Transformers]] and the [[Concept - GPU Memory Hierarchy]]). Wasting it **capped batch sizes at a fraction of what the silicon could hold**, which throttled throughput and left GPUs costing tens of thousands of dollars idle mid-decode. The field was leaving most of its serving capacity on the floor and mostly didn't realize the loss had one fixable cause. Everyone assumed the bottleneck was *compute*, so teams chased the symptom with faster attention kernels and tuned batch heuristics.

Then the Berkeley Sky Computing Lab group (Woosuk Kwon, Zhuohan Li, Ying Sheng, Lianmin Zheng, Siyuan Zhuang, Cody Yu, Joseph Gonzalez, Hao Zhang, Ion Stoica and collaborators) looked at the fragmentation and saw **the problem operating systems solved in the 1960s with virtual memory and paging.** A process doesn't get one contiguous slab of physical RAM. It gets fixed-size *pages* scattered across physical memory, indexed by a per-process *page table* that maps virtual → physical addresses. Apply that to the KV cache. Chop each sequence's KV into fixed-size **blocks** (16 tokens is the common default), let blocks live *anywhere* in GPU memory, and keep a per-request **block table** mapping logical block index → physical block. Allocate blocks on demand as the sequence grows and free them the moment it finishes. That's [[Concept - PagedAttention]], and it shipped in [[Breakdown - vLLM]] (Kwon et al., SOSP 2023).

The effect was immediate. Waste fell from 60–80% to **under 4%.** Throughput went up **~2–4× overnight** on the same hardware, because the freed memory held far more concurrent sequences. That same property lets [[Concept - Continuous Batching]] admit new requests mid-flight without pre-reserving their memory. Within roughly a year, essentially every serious engine (TensorRT-LLM, TGI, SGLang and the rest) had re-standardized on paged KV. Contiguous-buffer serving was legacy almost as soon as the paper landed.

## The lesson

The mechanical lesson transfers well: **the limit on LLM serving was memory *management*, not compute or kernel micro-optimization.** For over a year the field put its effort into the layer it was comfortable in (CUDA kernels, math, batching heuristics) while the waste sat one level up, in how memory was *allocated*. A fifty-year-old systems idea, imported wholesale, beat a year of kernel speedup attempts because the bottleneck was in a layer nobody serving LLMs was looking at.

The move worth generalizing is the reframe. Fragmentation of a resource with variable lifetime and variable size is a solved problem in operating systems. When an ML system wastes a resource it can't seem to pack tightly, ask whether the OS people already fixed it. The KV cache turned out to be process memory, and the answer was paging. A lot of the era's wasted GPU spend (see [[Concept - Cost Engineering for LLM Applications]]) came from this one bug, and better bookkeeping fixed it, not better math.

## Evidence status

**Well-documented and verified.** The 60–80% waste figure, the block-table design and the throughput numbers are all in the peer-reviewed SOSP 2023 paper ("Efficient Memory Management for Large Language Model Serving with PagedAttention"), backed up by the open-source vLLM codebase and the authors' public talks. The OS-paging framing is the paper's own analogy, not a narrative added later. One soft edge: the "2–4×" throughput gain depends on model, hardware and workload. It's a real, reproduced range, not a universal constant.

## Connections
- [[Concept - PagedAttention]] — the mechanism this story produced; the block-table/paging design in full technical detail.
- [[Breakdown - vLLM]] — the system that introduced PagedAttention and carried the re-standardization across the field.
- [[Concept - KV Cache]] — the data structure whose fragmentation is the entire subject of this crisis.
- [[Concept - GPU Memory Hierarchy]] — why wasted HBM is so costly, and why memory (not FLOPs) caps serving concurrency.
- [[Concept - Continuous Batching]] — the technique whose full power was unlocked once paged KV removed the pre-reservation requirement.
- [[Reference - Memory Math for Transformers]] — the formulas that quantify how much the fragmentation was actually costing.
- [[Concept - Cost Engineering for LLM Applications]] — the economic frame: the crisis was, at bottom, wasted GPU capex, and paging was the single biggest fix.

## Sources
- Kwon et al. (2023) — "Efficient Memory Management for Large Language Model Serving with PagedAttention," SOSP 2023. Source of the 60–80% waste measurement, the paging design, and the throughput gains.
- The vLLM open-source project — the reference implementation and public documentation corroborating the numbers.
