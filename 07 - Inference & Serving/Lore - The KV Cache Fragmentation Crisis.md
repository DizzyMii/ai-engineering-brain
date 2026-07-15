---
tags: [lore, domain/inference-serving, level/unicorn]
aliases: [PagedAttention origin story, KV fragmentation crisis]
summary: "How LLM serving wasted 60-80% of GPU memory to KV fragmentation until PagedAttention reframed it as an OS paging problem."
---
> **The war story of how the whole field wasted most of its most expensive resource — GPU memory — for over a year, because everyone was solving the wrong problem in the wrong layer, until a Berkeley systems group noticed it was a textbook operating-systems bug in disguise.**

## What happened

Through 2022 and into early 2023, every mainstream LLM serving stack made the same quiet decision. HuggingFace `generate`, NVIDIA FasterTransformer, the earliest TGI — each of them, when a request arrived, **pre-allocated one contiguous block of GPU memory large enough to hold the [[Concept - KV Cache]] for `max_seq_len` tokens.** Not the tokens the request would actually generate — the *maximum it might ever* generate. They did this because the attention kernels of the day assumed the keys and values for a sequence lived in one contiguous, tightly-strided buffer; a kernel that could gather K,V from scattered locations didn't exist yet.

The consequence was brutal and invisible. Real requests are short and wildly variable — a chat turn might be 40 tokens, the reservation 2048. So the reserved buffer sat **mostly empty for the request's entire lifetime** (internal fragmentation), and when requests of different sizes finished and freed their buffers, they left oddly-sized holes that no new request's contiguous reservation could fit into (external fragmentation). The vLLM paper later measured it precisely: **60–80% of the KV memory region was wasted.** On an 80 GB H100 where, after weights, maybe ~20 GB is left for KV, four-fifths of *that* evaporated to fragmentation.

Memory is the binding constraint on how many requests you can batch (see [[Reference - Memory Math for Transformers]] and the [[Concept - GPU Memory Hierarchy]]), so wasting it wasn't an accounting nuisance — it directly **capped batch sizes to a fraction of what the silicon could hold**, which throttled throughput, which left tens-of-thousands-of-dollars GPUs sitting idle mid-decode. The entire field was leaving most of its serving capacity on the floor, and largely didn't realize the loss had a single fixable cause. Teams chased the symptom — writing faster attention kernels, tuning batch heuristics — because everyone assumed the bottleneck was *compute*.

Then the Berkeley Sky Computing Lab group — Woosuk Kwon, Zhuohan Li, Ying Sheng, Lianmin Zheng, Siyuan Zhuang, Cody Yu, Joseph Gonzalez, Hao Zhang, Ion Stoica and collaborators — looked at the fragmentation and recognized it as **exactly the problem operating systems solved in the 1960s with virtual memory and paging.** A process doesn't get one contiguous slab of physical RAM; it gets fixed-size *pages* scattered across physical memory, indexed by a per-process *page table* that maps virtual → physical addresses. Do the same to the KV cache: chop each sequence's KV into fixed-size **blocks** (16 tokens is the common default), let blocks live *anywhere* in GPU memory, and keep a per-request **block table** mapping logical block index → physical block. Allocate blocks on demand as a sequence actually grows; free them the instant it finishes. This is [[Concept - PagedAttention]], and it shipped in [[Breakdown - vLLM]] (Kwon et al., SOSP 2023).

The result was immediate and total. Waste dropped from 60–80% to **under 4%.** Throughput jumped **~2–4× overnight** for the same hardware, because the freed memory could now hold far more concurrent sequences — which is also precisely what makes [[Concept - Continuous Batching]] able to admit new requests mid-flight without pre-reserving their memory. Within roughly a year, essentially the entire ecosystem — TensorRT-LLM, TGI, SGLang, every serious engine — had re-standardized on paged KV. Contiguous-buffer serving became legacy almost the moment the paper landed.

## The lesson

The mechanical lesson is precise and transferable: **the binding constraint on LLM serving was memory *management*, not compute or kernel micro-optimization.** For over a year the field poured effort into the layer it was comfortable in — CUDA kernels, math, batching heuristics — while the actual waste sat one level up, in how memory was *allocated*. A fifty-year-old systems idea, imported wholesale, beat a year of attempted kernel speedups because the bottleneck was in a layer nobody serving LLMs was looking at.

The generalizable move is the *reframe*: fragmentation of a variable-lifetime, variable-size resource is a solved problem in operating systems, and "this looks like something the OS people already fixed" is a heuristic worth reaching for whenever an ML system wastes a resource it can't seem to pack tightly. The KV cache turned out to be process memory; the answer was paging. Much of the wasted GPU spend of the era — see [[Concept - Cost Engineering for LLM Applications]] — was this one bug, and it was fixed not by better math but by better bookkeeping.

## Evidence status

**Well-documented and verified.** The 60–80% waste figure, the block-table design, and the throughput numbers are all in the peer-reviewed SOSP 2023 paper ("Efficient Memory Management for Large Language Model Serving with PagedAttention"), corroborated by the open-source vLLM codebase and by the authors' public talks. The OS-paging framing is the paper's own stated analogy, not a retrofitted narrative. The one soft edge: the exact "2–4×" throughput gain depends on model, hardware, and workload — it's a real, reproduced range, not a single universal constant.

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
