---
tags: [concept, domain/inference-serving, level/unicorn]
aliases: [batch nondeterminism, temperature 0 nondeterminism, reproducible inference, batch-invariant kernels]
summary: "Why temperature 0 isn't deterministic on a real server: FP non-associativity, batch-variant kernels, and how batch-invariant kernels fix it."
---
> **One-paragraph hook:** "Set temperature to 0 and the model is deterministic" is true of the *math* and false of the *server*. Send the identical prompt twice at `T=0` and you can get different tokens; worse, the same request can decode differently depending on what *other* requests happened to be in its batch. This isn't sampler randomness — it's floating-point non-associativity interacting with GPU kernels whose reduction order changes with batch shape. It quietly breaks eval reproducibility, corrupts semantic caches keyed on "deterministic" outputs, and destabilizes RL training when the rollout engine and the trainer disagree on the same weights.

## The mechanism

Greedy decoding picks $\arg\max_i z_i$ over the logit vector, which is deterministic *given the logits*. The nondeterminism is upstream: **the logits themselves are not bit-identical across runs.**

**Root cause 1 — floating-point non-associativity.** In finite precision, $(a + b) + c \neq a + (b + c)$ because each addition rounds. A matmul, an attention softmax, or a LayerNorm reduces thousands of products into one sum, and on a GPU that sum is computed by many threads reducing in *parallel* — the order in which partial sums combine is a function of the kernel's tiling, the number of thread blocks, `atomicAdd` timing, and split-K strategy. Different order → different rounding → logits that differ in the last few bits. Almost always harmless — until two candidate tokens are near-tied, where a sub-ULP difference **flips the argmax** and the whole continuation diverges from that point.

**Root cause 2 — batch-variance (the dominant one).** The 2025 analysis *"Defeating Nondeterminism in LLM Inference"* (Horace He and collaborators, Thinking Machines) sharpened the field's understanding: run-to-run on a *fixed* batch is usually already deterministic. The real culprit is that **kernels change their reduction strategy as a function of batch size and shape.** cuBLAS/cuDNN pick different algorithms per problem shape; FlashAttention selects different split-K partitions; a GEMM tiles differently at batch 1 vs batch 32. So your request's numerics depend on *how many other requests are in the batch with it* — and under [[Concept - Continuous Batching]] that composition changes every iteration based on unrelated concurrent load. The same prompt lands in a different-shaped batch each time and gets slightly different logits. The reframing matters: it's not "the GPU is random," it's "your request's arithmetic is contextual."

**Other contributors:** `atomicAdd`-based reductions (nondeterministic accumulation order), cuBLAS/cuDNN autotuning that reselects algorithms per shape, FlashAttention split-K variants (see [[Deep Dive - FlashAttention]]), [[Concept - Chunked Prefill]] chunk boundaries changing how a prefill is summed, and MoE routing whose expert assignment shifts under batching. Each perturbs the reduction and can flip a near-tie.

**The fix — batch-invariant kernels.** Force every reduction to combine in the *same order regardless of batch shape*: a fixed reduction tree, no atomic accumulation, a single algorithm choice per op independent of size. He et al. shipped batch-invariant kernels (matmul, attention, norm) demonstrating bit-identical output across batch sizes. The cost is throughput: you forgo the fastest shape-specialized kernel and some split-K parallelism, so you pay perhaps tens of percent for reproducibility.

## In practice

Most production serving **accepts** nondeterminism — the throughput cost of batch-invariance isn't worth it for chat — and instead controls it *only where it bites*:

- **Evals.** Leaderboard and regression scores that assume `T=0` reproducibility are flaky; a model can score differently across runs with no code change. Fix by pinning batch size, using deterministic kernels for the eval harness, and reporting variance (see [[Concept - Statistical Rigor in Model Evaluation]]) rather than a single point.
- **RL fine-tuning.** The sharp one: in [[Concept - GRPO and RL with Verifiable Rewards]] and similar, an *inference engine* generates rollouts while a *training framework* computes gradients on the same weights. If the two compute logits with different reductions, the sampled action's logprob under the trainer ≠ its logprob under the sampler — a hidden importance-weight mismatch that biases the policy gradient and destabilizes training. Batch-invariant (or at least engine-consistent) kernels are the clean fix; this is a real, repeatedly-rediscovered footgun.
- **Caching.** Semantic caches keyed on "identical prompt → identical output at `T=0`" get silent misses/inconsistencies when the same input decodes two ways.

Determinism flags exist (`torch.use_deterministic_algorithms`, fixed cuBLAS workspace, disabling TF32/autotuning) but they only cover single-process, fixed-shape execution — they do **not** by themselves make you invariant to batch composition on a live server.

## Failure modes

- **Flaky regression tests** at `T=0` that "randomly" fail on unchanged code — the classic symptom of assuming greedy = reproducible.
- **Unreproducible benchmark numbers** that shift by fractions of a point run-to-run, wrongly attributed to the model instead of the harness.
- **RL divergence / entropy collapse** traced to a sampler-vs-trainer logprob gap rather than a hyperparameter.
- **Cache inconsistency** where a "cache hit" returns a different completion than the cached one, breaking downstream assumptions.

Detection: run the same prompt N times at `T=0` under varying concurrent load and diff the token streams; if outputs diverge only under load, you're seeing batch-variance, not sampler randomness.

## The non-obvious

The insight that reorganizes everything: **a single kernel with fixed inputs and fixed batch shape is deterministic — the randomness enters through the *batch*, which is a property of the serving system, not the model.** People chase this as if the GPU rolls dice; it doesn't. The floating-point layer is deterministic *for a given reduction order*, and the reduction order is chosen by shape-specialized kernels for speed. So nondeterminism is the price of the very optimizations (autotuning, split-K, dynamic batching) that make serving fast — reproducibility and peak throughput are in genuine tension, and the "temperature 0 is deterministic" folklore quietly assumed a batch size of one that no real server runs. This is the applied face of the same phenomenon documented for training in [[Concept - Floating Point for Deep Learning]]; the serving version is nastier only because the batch — and thus the reduction order — changes continuously under production traffic.

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
