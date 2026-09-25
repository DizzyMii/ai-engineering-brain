---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [S-LoRA, Punica, LoRA multiplexing, adapter serving]
summary: "Serving thousands of LoRA adapters over one shared base model via batched heterogeneous-adapter kernels and adapter paging, not N deployments."
---


> **One-paragraph hook:** A [[Deep Dive - LoRA|LoRA adapter]] is typically 0.1-1% of the base model's size. A business that fine-tunes one adapter per customer or per task then has two options: deploy N nearly identical full copies of a 70B model, or serve N tiny adapters against one shared base. Multi-LoRA serving makes the second option work at batch scale. Hundreds to thousands of adapters, each request potentially hitting a different one, share a single base model's weights and [[Concept - KV Cache|KV cache]] infrastructure. Without it, per-customer fine-tuning is an accounting nightmare. With it, it's the default way SaaS products personalize an LLM.

## The mechanism

[[Concept - Continuous Batching|Continuous batching]] already packs heterogeneous requests into one GPU-filling iteration. Here the heterogeneity gets a second dimension: a batch of B requests may target B *different* adapters. The shared base-model matmul, `xW0`, is identical for everyone and batches trivially. The adapter contribution is harder:

$$
y = xW_0 + \frac{\alpha}{r}\, x B A
$$

$A \in \mathbb{R}^{r\times d}$ and $B \in \mathbb{R}^{d\times r}$ are the low-rank matrices for *that request's* adapter, and $\alpha/r$ is its scaling. Naive implementations loop over the batch and apply each request's own $A$, $B$ serially. That turns one fused kernel call into B tiny, latency-bound matmuls and wrecks GPU utilization the same way static batching wrecked it for base-model decode.

S-LoRA (Sheng et al., 2023) and Punica (Chen et al., 2023) fix this the same way, with a **batched, segmented gather-matmul kernel**. Punica calls its version SGMV (Segmented Gather Matrix-Vector multiplication). In one kernel launch it groups the batch by which adapter each row uses and applies each adapter's $A$, $B$ to its own rows, with no Python-level loop and no kernel launch per adapter. The base matmul $xW_0$ and the batched adapter correction run as two fused GPU operations however many distinct adapters the batch contains, which restores the amortization that makes batching worth doing.

Memory is the second axis. Each adapter is small: for a 70B model with rank 16 on attention and MLP projections, an adapter is commonly tens of MB, against ~140 GB for the base weights in fp16. Thousands of them add up, though, and they won't all fit in HBM at once. **Adapter paging** handles this as a cache. Hot adapters (recently or frequently requested) stay resident in GPU memory, cold ones get swapped out to host RAM, and a request for a cold adapter triggers a prefetch before it can be scheduled into a batch. VRAM is consumed by the *working set* of concurrently active adapters, not by the total adapter count on disk.

## In practice

[[Breakdown - vLLM|vLLM]] ships multi-LoRA as a built-in serving mode. You register adapters against a base model, each request names its adapter, and the SGMV-style batched kernel and paging run underneath. That's what makes "one base model, one adapter per enterprise customer" or "one adapter per task type" economically viable without N full model deployments: a 0.1-1% marginal memory cost per customer instead of 100%.

Throughput depends on *adapter diversity within a batch*, and adapter count alone doesn't tell you much. If every request in a batch shares one adapter, the base matmul amortizes as well as in a plain dense-model batch. If B requests each hit a different adapter, you pay more for adapter I/O and get less out of kernel fusion. So routing that clusters same-adapter traffic together, instead of round-robining blindly across adapters, measurably improves throughput. It's a scheduling lever as well as a kernel one.

**Merged adapters** fold $BA$ directly into $W_0$ to produce a standalone dense checkpoint. They're faster to serve per request (no adapter kernel at all) but give up multiplexing entirely: you're back to one full model copy per adapter. Merge when a single dominant adapter is served at very high, stable volume. Use multi-LoRA serving once you have many adapters with unpredictable per-request routing.

## Failure modes

- **Rank/config mismatch.** Serve a rank-32 adapter against a runtime configured for rank 16 (or a different set of target modules) and it either errors loudly or, worse, silently applies a truncated or misaligned correction that degrades output with no obvious signal. Validate adapter metadata against the serving config at load time, not at request time.
- **Base-revision drift.** An adapter fine-tuned against one checkpoint of the base model and served against another (even a lightly updated one) produces low-quality output that looks like a model regression instead of an adapter incompatibility. Pin the base model hash in every adapter's metadata.
- **Adapter-set VRAM thrash.** When the working set of actively requested adapters exceeds the paging budget, the server spends its time evicting and reloading adapters instead of serving. Throughput collapses in a way that looks identical to a KV-cache capacity problem but is an adapter-cache capacity problem. Check the adapter cache hit rate before assuming [[Concept - KV Cache|KV]] pressure.
- **Throughput degradation under high adapter diversity.** As the number of distinct adapters per batch rises, base-matmul amortization falls and adapter-gather overhead rises. A load test that only exercises one or two adapters won't show this and will overestimate production throughput.

## The non-obvious

Multi-LoRA performance is governed by the **working set of adapters actively hit within a scheduling window**, not by how many adapters you have deployed. A platform with 5,000 registered adapters whose traffic clusters heavily onto 20 of them at any moment performs like a 20-adapter deployment, not a 5,000-adapter one. The engineering question then shifts from "how do we serve more adapters" (memory and paging) to "how do we route traffic so adapters get reused within a batch" (scheduling). The routing fix often buys more throughput than any kernel-level optimization, because it directly raises base-matmul amortization, which is what continuous batching was built to maximize.

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
