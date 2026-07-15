---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [S-LoRA, Punica, LoRA multiplexing, adapter serving]
summary: "Serving thousands of LoRA adapters over one shared base model via batched heterogeneous-adapter kernels and adapter paging, not N deployments."
---

> **One-paragraph hook:** A [[Deep Dive - LoRA|LoRA adapter]] is typically 0.1-1% of the base model's size, so a business that fine-tunes one adapter per customer or per task faces a stark choice: deploy N nearly-identical full copies of a 70B model, or find a way to serve N tiny adapters against one shared base. Multi-LoRA serving is the engineering that makes the second option work at batch scale — hundreds to thousands of adapters, each request potentially hitting a different one, sharing a single base model's weights and [[Concept - KV Cache|KV cache]] infrastructure. Without it, per-customer fine-tuning is an accounting nightmare; with it, it's the default way SaaS products personalize an LLM.

## The mechanism

The problem [[Concept - Continuous Batching|continuous batching]] already solves — packing heterogeneous requests into one GPU-filling iteration — gets a second dimension of heterogeneity here: a batch of B requests may target B *different* adapters. The shared base-model matmul, `xW0`, is identical for everyone and batches trivially. The adapter contribution,

$$
y = xW_0 + \frac{\alpha}{r}\, x B A
$$

(where $A \in \mathbb{R}^{r\times d}$, $B \in \mathbb{R}^{d\times r}$ are the low-rank adapter matrices for *that request's* adapter and $\alpha/r$ is its scaling), is where naive implementations fall apart: looping per-request over the batch to apply each one's own $A$, $B$ serially turns a single fused kernel call into B tiny, latency-bound matmuls, destroying GPU utilization exactly the way static batching destroyed it for base-model decode.

S-LoRA (Sheng et al., 2023) and Punica (Chen et al., 2023) both fix this with the same core idea: a **batched, segmented gather-matmul kernel** (Punica calls its version SGMV — Segmented Gather Matrix-Vector multiplication) that, in one kernel launch, groups the batch by which adapter each row uses and applies each adapter's $A$, $B$ to its own rows without a Python-level loop or a kernel-launch-per-adapter. The base matmul $xW_0$ and the batched adapter correction run as two fused GPU operations regardless of how many distinct adapters are present in the batch, restoring the amortization that makes batching worth doing in the first place.

Memory is the second axis. Each adapter is small — for a 70B model with rank 16 applied to attention and MLP projections, an adapter is commonly tens of MB, versus ~140 GB for the base weights in fp16 — but thousands of them add up, and not every adapter fits in HBM at once. **Adapter paging** treats this like a cache: hot adapters (recently or frequently requested) stay resident in GPU memory, cold ones are swapped out to host RAM, and a request for a currently-cold adapter triggers a prefetch before it can be scheduled into a batch. The *working set* of concurrently active adapters, not the total adapter count on disk, is what actually consumes VRAM.

## In practice

[[Breakdown - vLLM|vLLM]] ships multi-LoRA as a first-class serving mode: adapters are registered against a base model, requests specify which adapter to use, and the SGMV-style batched kernel and paging live under the hood. This is the mechanism that makes "one base model, one adapter per enterprise customer" or "one base model, one adapter per task type" economically viable instead of requiring N full model deployments — a 0.1-1% marginal memory cost per customer instead of a 100% one.

Throughput has a real dependence on *adapter diversity within a batch*, not just adapter count: a batch where every request happens to share one adapter amortizes the base matmul as well as a plain dense-model batch would, while a batch with B requests each hitting a different adapter pays more for adapter I/O and gets less benefit from kernel fusion. This is why request routing that clusters same-adapter traffic together (rather than round-robining blindly across adapters) measurably improves throughput — it's a scheduling lever, not just a kernel one.

**Merged adapters** — folding $BA$ directly into $W_0$ to produce a standalone dense checkpoint — are faster to serve per-request (no adapter kernel at all) but sacrifice the entire point of multiplexing: you're back to one full model copy per adapter. Merging makes sense for a single dominant adapter served at very high, stable volume; multi-LoRA serving makes sense the moment you have many adapters with unpredictable per-request routing.

## Failure modes

- **Rank/config mismatch.** An adapter trained with rank 32 served against a runtime configured for rank 16 (or a different set of target modules) either errors loudly or, worse, silently applies a truncated/misaligned correction that degrades output without an obvious signal — validate adapter metadata against the serving config at load time, not at request time.
- **Base-revision drift.** An adapter fine-tuned against one checkpoint of the base model and served against a different (even lightly updated) checkpoint produces low-quality output that looks like a model regression rather than an adapter incompatibility — pin base model hash alongside every adapter's metadata.
- **Adapter-set VRAM thrash.** When the working set of actively-requested adapters exceeds the paging budget, the server spends its time evicting and reloading adapters instead of serving, and the symptom is throughput collapse that looks identical to a KV-cache capacity problem but is actually an adapter-cache capacity problem — check adapter cache hit rate before assuming it's [[Concept - KV Cache|KV]] pressure.
- **Throughput degradation under high adapter diversity.** As the number of distinct adapters hit per batch rises, base-matmul amortization falls and adapter-gather overhead rises; a load test that only exercises one or two adapters will not reveal this and will overestimate production throughput.

## The non-obvious

The number that governs multi-LoRA serving performance isn't "how many adapters do we have deployed" — it's the **working set of adapters actively hit within a scheduling window**. A platform with 5,000 registered adapters but traffic that clusters heavily onto 20 of them at any given moment behaves, performance-wise, like a 20-adapter deployment, not a 5,000-adapter one. This reframes the engineering problem from "how do we serve more adapters" (a memory/paging question) to "how do we route traffic to concentrate adapter reuse within a batch" (a scheduling question) — and the latter often buys more throughput than any kernel-level optimization, because it directly increases base-matmul amortization, which is the thing continuous batching was built to maximize in the first place.

## Connections
- [[Deep Dive - LoRA]] — the training-time mechanism (low-rank adapter matrices, rank/alpha) that this note's serving-time batching kernels operate over.
- [[Concept - QLoRA]] — a common way adapters arrive in the first place (quantized-base fine-tuning); the resulting adapter still serves the same way once trained, decoupling training-time quantization choice from serving-time multiplexing.
- [[Concept - DoRA]] — a LoRA variant (weight-decomposed adaptation) whose extra magnitude parameter changes what the batched adapter kernel has to fuse; serving infrastructure built only for plain LoRA's $BA$ correction needs to be extended, not assumed compatible, for adapter families like this one.
- [[Concept - KV Cache]] — the other major per-request memory consumer in the same batch; multi-LoRA serving and KV paging compete for the same HBM budget and are tuned together.
- [[Concept - Continuous Batching]] — the iteration-level scheduling this note's adapter-batching kernels plug into; multi-LoRA serving is continuous batching with a second axis of per-request heterogeneity.
- [[Breakdown - vLLM]] — the reference serving engine that ships batched multi-LoRA (SGMV-style kernels plus adapter paging) as a production feature.
- [[Decision - Fine-Tuning vs RAG vs Prompting]] — the upstream decision that determines whether an organization ends up with many small adapters to serve at all.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — the cost model multi-LoRA serving is optimizing against: N adapters at ~1% marginal memory cost each versus N full model deployments.
- [[Concept - GPU Memory Hierarchy]] — the HBM-vs-host-memory hierarchy that adapter paging (hot adapters resident, cold adapters swapped) exploits, mirroring how the KV cache itself is managed.

## Sources
- Sheng et al. (2023) — *S-LoRA: Serving Thousands of Concurrent LoRA Adapters*. Introduces unified paging of adapter weights between GPU and host memory alongside batched adapter computation.
- Chen et al. (2023) — *Punica: Multi-Tenant LoRA Serving*. Introduces the Segmented Gather Matrix-Vector multiplication (SGMV) kernel for applying heterogeneous adapters within one batched GPU kernel call.
- Hu et al. (2021) — *LoRA: Low-Rank Adaptation of Large Language Models*. The adapter formulation ($BA$ low-rank correction) that all multi-LoRA serving systems batch over.
