---
tags: [concept, domain/inference-serving, level/unicorn]
aliases: [batch nondeterminism, temperature 0 nondeterminism, reproducible inference, batch-invariant kernels]
summary: "Why temperature 0 isn't deterministic on a real server: FP non-associativity, batch-variant kernels, and how batch-invariant kernels fix it."
---
> **One-paragraph hook:** "Set temperature to 0 and the model is deterministic" holds for the *math* and fails for the *server*. Send the identical prompt twice at `T=0` and you can get different tokens. Worse, the same request can decode differently depending on which *other* requests happened to share its batch. The sampler isn't the source. Floating-point non-associativity interacts with GPU kernels whose reduction order changes with batch shape. The result breaks eval reproducibility, corrupts semantic caches keyed on "deterministic" outputs, and destabilizes RL training when the rollout engine and the trainer disagree on the same weights.

## The mechanism

Greedy decoding picks $\arg\max_i z_i$ over the logit vector, which is deterministic *given the logits*. The problem is upstream: **the logits themselves are not bit-identical across runs.**

### Root cause 1: floating-point non-associativity

In finite precision, $(a + b) + c \neq a + (b + c)$, because each addition rounds. A matmul, an attention softmax, or a LayerNorm reduces thousands of products into one sum. GPU threads compute that sum in *parallel*, and the combination order depends on the kernel's tiling, the number of thread blocks, `atomicAdd` timing, and split-K strategy. Different order, different rounding, logits that differ in the last few bits. Almost always harmless. When two candidate tokens are near-tied, though, a sub-ULP difference **flips the argmax** and the whole continuation diverges from there.

### Root cause 2: batch-variance (the dominant one)

The 2025 analysis *"Defeating Nondeterminism in LLM Inference"* (Horace He and collaborators, Thinking Machines) showed that run-to-run on a *fixed* batch is usually already deterministic. What varies: **kernels change their reduction strategy as a function of batch size and shape.** cuBLAS/cuDNN pick different algorithms per problem shape, FlashAttention picks different split-K partitions, and a GEMM tiles differently at batch 1 vs batch 32. Your request's numerics therefore depend on *how many other requests share its batch*, and under [[Concept - Continuous Batching]] that composition changes every iteration with unrelated concurrent load. Same prompt, differently shaped batch, slightly different logits. The GPU isn't random; your request's arithmetic depends on its context.

### Other contributors

`atomicAdd`-based reductions (nondeterministic accumulation order), cuBLAS/cuDNN autotuning that reselects algorithms per shape, FlashAttention split-K variants (see [[Deep Dive - FlashAttention]]), [[Concept - Chunked Prefill]] chunk boundaries that change how a prefill is summed, and MoE routing whose expert assignment shifts under batching. Each one perturbs the reduction and can flip a near-tie.

### The fix: batch-invariant kernels

Make every reduction combine in the *same order regardless of batch shape*: a fixed reduction tree, no atomic accumulation, one algorithm choice per op independent of size. He et al. shipped batch-invariant kernels (matmul, attention, norm) with bit-identical output across batch sizes. The cost is throughput: without the fastest shape-specialized kernel and some split-K parallelism, you pay perhaps tens of percent.

## In practice

Most production serving **accepts** nondeterminism, since batch-invariance costs more throughput than it's worth for chat, and controls it *only where it bites*:

- **Evals.** Leaderboard and regression scores that assume `T=0` reproducibility are flaky; a model can score differently across runs with no code change. Pin batch size, use deterministic kernels in the eval harness, and report variance (see [[Concept - Statistical Rigor in Model Evaluation]]) instead of a single point.
- **RL fine-tuning.** This is the sharp one. In [[Concept - GRPO and RL with Verifiable Rewards]] and similar setups, an *inference engine* generates rollouts while a *training framework* computes gradients on the same weights. If the two use different reductions, the sampled action's logprob under the trainer ≠ its logprob under the sampler. That's a hidden importance-weight mismatch that biases the policy gradient and destabilizes training. Batch-invariant (or at least engine-consistent) kernels are the clean fix, and people keep rediscovering this footgun.
- **Caching.** Semantic caches keyed on "identical prompt → identical output at `T=0`" get silent misses and inconsistencies when the same input decodes two ways.

Determinism flags exist (`torch.use_deterministic_algorithms`, fixed cuBLAS workspace, disabling TF32/autotuning), but they only cover single-process, fixed-shape execution. On their own they do **not** make you invariant to batch composition on a live server.

## Failure modes

- **Flaky regression tests** at `T=0` that "randomly" fail on unchanged code, the classic symptom of assuming greedy = reproducible.
- **Unreproducible benchmark numbers** that shift by fractions of a point run-to-run and get blamed on the model instead of the harness.
- **RL divergence / entropy collapse** traced to a sampler-vs-trainer logprob gap, not a hyperparameter.
- **Cache inconsistency**, where a "cache hit" returns a different completion than the cached one and breaks downstream assumptions.

To detect it, run the same prompt N times at `T=0` under varying concurrent load and diff the token streams. If outputs diverge only under load, it's batch-variance, not sampler randomness.

## The non-obvious

**A single kernel with fixed inputs and fixed batch shape is deterministic. The randomness comes in through the *batch*, which belongs to the serving system, not the model.** People chase this as if the GPU rolls dice. It doesn't: floating point is deterministic *for a given reduction order*, and shape-specialized kernels pick that order for speed. Nondeterminism is the price of the same optimizations (autotuning, split-K, dynamic batching) that make serving fast. Reproducibility and peak throughput are in real tension, and the "temperature 0 is deterministic" folklore assumed a batch size of one that no real server runs. [[Concept - Floating Point for Deep Learning]] documents the same phenomenon for training. The serving version is nastier only because the batch, and with it the reduction order, changes continuously under production traffic.

## Connections
- [[Concept - Floating Point for Deep Learning]] — non-associativity of FP addition is the substrate; this note is its serving-time consequence.
- [[Concept - Sampling and Decoding Parameters]] — clarifies that `T=0`/greedy removes *sampler* randomness but not the numeric variance underneath it.
- [[Concept - Continuous Batching]] — the mechanism that makes batch composition (and thus reduction order) vary every iteration under load.
- [[Concept - Chunked Prefill]] — chunk-boundary placement is one of the kernel-shape variables that perturbs reductions.
- [[Concept - GRPO and RL with Verifiable Rewards]] — where sampler-vs-trainer logprob mismatch from nondeterminism becomes a training-stability bug.
- [[Concept - Statistical Rigor in Model Evaluation]] — why single-point `T=0` eval numbers are untrustworthy and variance must be reported.
- [[Deep Dive - FlashAttention]] — split-K and tiling choices in attention kernels are a concrete source of batch-dependent reduction order.
- [[Gotchas - LLM Serving in Production]] — where silent nondeterminism shows up as flaky evals and cache-key mismatches in real deployments.
- [[Lore - The Nondeterminism of Floating-Point Reductions]] — the foundational war story of the same FP-reduction phenomenon that this note applies to inference.
- [[Concept - Nondeterminism in Production LLM Serving]] — the production-ops sibling covering how to detect, budget for, and live with this at the fleet level.

## Sources
- He et al. (2025) — "Defeating Nondeterminism in LLM Inference" (Thinking Machines). Identifies batch-variance as the dominant cause and ships batch-invariant matmul/attention/norm kernels achieving bit-identical output.
- Standard numerical-analysis result: floating-point addition is non-associative under IEEE-754 rounding; parallel GPU reductions therefore depend on combination order.
