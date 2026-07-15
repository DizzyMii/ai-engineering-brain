---
tags: [moc, domain/training-at-scale, level/surface]
aliases: []
summary: "Map of LLM pretraining at scale: parallelism, precision, optimizers, tokenization, and why large runs diverge."
---

# MOC - Training at Scale

This domain owns the mechanics of turning a dataset and an architecture into trained weights once neither the model nor the data fits on one GPU: how work and state get sharded across thousands of accelerators (data/tensor/pipeline/sequence/expert parallelism), how precision and optimizer choices trade throughput against numerical stability, how raw text becomes the token stream a model actually consumes, and how a multi-week run is monitored, checkpointed, and rescued when it silently diverges. It matters because a pretraining run is a single, enormously expensive, largely irreversible bet — DeepSeek-V3 trained a 671B-parameter MoE on 14.8T tokens for roughly $5.6M, and the gap between a well-composed 3D parallelism layout and a naive one is the gap between that number and multiples of it. Sitting between [[MOC - Architectures]] (what you're training) and [[MOC - Data Engineering]] (what you're training on), this is where FLOPs, HBM bytes, and interconnect bandwidth become the real constraints on the job. It's also where folklore substitutes for theory more than anywhere else in the vault — beta2=0.95, the rewind-skip-lower-LR loss-spike recipe — precisely because so few organizations have ever run a job at this scale and shared what broke.

## Start here

- **Surface** → [[Concept - Why Models Don't Fit on One GPU]] — the memory arithmetic (params + gradients + optimizer state + activations) that forces every other idea in this domain to exist.
- **Core** → [[Concept - Scaling Laws]] — the power law relating loss to model size, data, and compute that every training budget in this domain is spent against.
- **Advanced** → [[Deep Dive - Anatomy of a Pretraining Run]] — the full lifecycle trace, from sizing through parallelism layout to monitoring and failure recovery.
- **Frontier** → [[Breakdown - DeepSeek-V3 Training]] — a real frontier run that composed fp8, aux-loss-free MoE routing, and DualPipe to hit $5.6M for a 671B model.
- **Unicorn** → [[Lore - The Loss Spike Chronicles]] — OPT-175B, PaLM, GLM-130B, BLOOM: the war stories behind the restart-skip-lower-LR folklore nearly everyone eventually relearns.

## Why distributed training exists

- [[Concept - Why Models Don't Fit on One GPU]] — params, gradients, optimizer states, and activations together exceed one GPU's HBM, which is why sharding and parallelism aren't optional at frontier scale.
- [[Concept - Scaling Laws]] — the power-law relationship between pretraining loss, model size, and data, and the compute-optimal N/D allocation it implies.
- [[Concept - Data-Constrained Scaling Laws]] — how loss scaling changes once unique data runs out, and how compute should shift between repeated epochs, more parameters, and synthetic data.

## Parallelism and distributed systems

- [[Concept - Data Parallelism and ZeRO]] — replicated-model data parallelism plus the ZeRO stages that shard optimizer state, gradients, and parameters to cut redundant per-GPU memory.
- [[Concept - Tensor and Pipeline Parallelism]] — splitting matmuls (tensor parallelism) or layers (pipeline parallelism) across GPUs for models too large for state-sharding alone.
- [[Concept - Fully Sharded Data Parallel (FSDP)]] — PyTorch's native ZeRO-3 implementation: just-in-time all-gather of params and reduce-scatter of grads, made fast by prefetch overlap.
- [[Concept - Sequence and Context Parallelism]] — SP shards TP-replicated norm/dropout activations along sequence for free; CP shards attention itself across ranks for long-context training.
- [[Concept - Expert Parallelism]] — placing MoE experts on different GPUs and paying two all-to-all collectives per layer to dispatch and combine tokens.
- [[Concept - Gradient Accumulation and Microbatching]] — splitting a target batch into microbatches whose gradients sum before one optimizer step, hitting a token budget under fixed GPU memory.
- [[Pattern - 3D Parallelism Composition]] — factoring world size into DP x TP x PP (x CP x EP) and mapping each factor onto hardware topology, since no single dimension scales alone.
- [[Decision - Choosing a Parallelism Strategy]] — how to pick DP/ZeRO, TP, PP, SP, CP, and EP degrees for a model, GPU count, and interconnect — default: FSDP alone until it doesn't fit.
- [[Reference - Parallelism Strategies]] — lookup table of DP, ZeRO/FSDP, TP, PP, SP, CP, and EP: what each shards, its collective, comm cost, and failure mode.
- [[Snippet - FSDP Minimal Setup]] — a minimal runnable FSDP2 training step: per-block fully_shard wrapping, bf16 compute with fp32 reduce, and activation checkpointing.
- [[Breakdown - Megatron-LM]] — how Megatron-LM realizes tensor/sequence/pipeline parallelism via f/g operators, setting the throughput bar for large transformer training.

## Optimizers, precision, and hyperparameters

- [[Concept - AdamW at Scale]] — engineering AdamW for LLM pretraining: decoupled decay, the beta2=0.95 folklore, fused kernels, and the 12 bytes/param it costs.
- [[Concept - Learning Rate Schedules for Pretraining]] — the warmup-plus-decay shapes (cosine, WSD/trapezoidal, inverse-sqrt) that govern how LR moves over a pretraining run.
- [[Concept - Mixed Precision Training]] — training in bf16/fp16 with fp32 master weights and loss scaling to get 2-8x tensor-core throughput without losing numerical stability.
- [[Concept - FP8 Training]] — the E4M3/E5M2 formats, why scaling is the real problem, and how DeepSeek-V3 made 8-bit training production-viable.
- [[Concept - Critical Batch Size]] — the batch size beyond which more data per step stops buying proportionally faster training — a moving target that grows as loss falls.
- [[Concept - Muon Optimizer]] — replaces AdamW's per-coordinate scaling with Newton-Schulz orthogonalized momentum for 2D weight matrices.
- [[Concept - Second-Order Optimizers at Scale]] — Shampoo, SOAP, and Lion trade AdamW's cheap diagonal update for curvature-aware or memory-lean alternatives at LLM scale.
- [[Concept - muP and Hyperparameter Transfer]] — scales init and per-layer LR so hyperparameters tuned on a small model transfer unchanged to a much larger one.
- [[Snippet - muP Coordinate Check]] — a runnable check that a muP implementation keeps activation coordinates O(1) across model widths at init and after a few steps.

## Tokenization

- [[Concept - Byte-Pair Encoding]] — the greedy merge algorithm that turns raw bytes into subword tokens, silently shaping every downstream model capability.
- [[Concept - Tokenizer Training]] — choosing and training an LLM tokenizer: BPE vs unigram LM, vocab-size economics, fertility, and the decisions frozen for the model's life.
- [[Snippet - Training a BPE Tokenizer]] — runnable HuggingFace tokenizers code that trains a byte-level BPE tokenizer with reserved special/FIM tokens and checks round-trip + fertility.
- [[Gotchas - Tokenizers]] — pitfalls that silently corrupt training and eval: add-token traps, normalization drift, double-BOS, digits, glitch tokens.

## Objectives, MoE, and training stability

- [[Concept - Pretraining Objectives]] — the self-supervised objectives that shape LLM pretraining: causal LM, masked LM, span corruption, prefix-LM, and fill-in-the-middle.
- [[Concept - MoE Training and Load Balancing]] — top-k routing collapse, auxiliary load-balance and z-losses, capacity dropping, and DeepSeek's aux-loss-free fix.
- [[Concept - Training Stability and Loss Spikes]] — why pretraining loss suddenly explodes, the stabilizers that prevent it, and the rewind-skip-lower-LR recipe that recovers a run.
- [[Concept - z-loss and Logit Soft-Capping]] — auxiliary-loss and tanh tricks that pin the softmax log-partition near zero to keep pre-softmax logits numerically well-conditioned in bf16.
- [[Concept - Distributed Checkpointing]] — saving and reloading sharded model+optimizer state across thousands of GPUs without stalling training or losing resumability.

## Running and debugging the job

- [[Deep Dive - Anatomy of a Pretraining Run]] — the end-to-end lifecycle of a frontier run: sizing, parallelism layout, the training loop, monitoring, failure recovery, and release.
- [[Checklist - Pre-Launch for a Large Training Run]] — pre-flight checks across config, numerics, data, checkpointing, and observability before committing thousands of GPU-hours.
- [[Gotchas - Distributed Training]] — multi-GPU pitfalls ordered by pain: NCCL hangs, silent gradient desync, non-determinism, uneven shards, mesh misconfiguration.
- [[Playbook - Debugging a Diverging Training Run]] — on-call procedure for a run that spikes, diverges, or NaNs: triage the signature, isolate the cause, then recover or restart.
- [[Reference - LLM Pretraining Hyperparameters]] — sourced hyperparameters of real frontier runs, surfacing folklore constants like beta2=0.95, wd=0.1, and grad clip 1.0.
- [[Lore - The Loss Spike Chronicles]] — war stories of pretraining loss spikes — OPT-175B, PaLM, GLM-130B, BLOOM — and the restart-skip-lower-LR folklore they produced.

## Case studies

- [[Breakdown - DeepSeek-V3 Training]] — how DeepSeek-V3 trained a 671B/37B-active MoE on 14.8T tokens for ~$5.6M via fp8, aux-loss-free routing, and DualPipe.

## Adjacent domains

- [[MOC - Architectures]] — the dense and MoE transformer variants this domain assumes as given and spends its compute budget training.
- [[MOC - Data Engineering]] — the filtering, deduplication, and mixture decisions that determine what's actually in every batch this domain trains on.
- [[MOC - Hardware & Systems]] — the GPUs, interconnect, and roofline math that bound every parallelism and communication tradeoff made here.
- [[MOC - Post-Training]] — where the pretrained checkpoint this domain produces gets adapted into an instruction-following or aligned model.
