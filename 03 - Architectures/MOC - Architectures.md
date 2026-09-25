---
tags: [moc, domain/architectures, level/surface]
aliases: []
summary: "Map of the block-level building blocks — attention, MoE, positional encoding, sequence mixers — that set a model's cost and quality."
---

# MOC - Architectures

This domain owns the block diagram: how attention, feed-forward layers, normalization, positional encoding, and their alternatives (state-space models, linear attention, convolutions) are wired into a model that trains and serves. It sits below training procedure and above pure math. The concern is tensor shapes, memory layout, and how each block works; how the weights get learned and the cluster that runs them live elsewhere. Architecture choices set constant factors everywhere downstream. Head geometry decides KV-cache bytes per token, normalization placement decides whether a run at scale diverges, and the sequence-mixer choice trades the quadratic attention wall against recall quality. Most of the field's hard engineering calls (MHA vs. GQA vs. MLA, dense vs. MoE, full attention vs. hybrid SSM) live here, in the notes with the sharpest tradeoff tables.

## Start here

- **Surface** → [[Concept - Encoder-Decoder and Decoder-Only Architectures]] — the taxonomy (encoder-only, encoder-decoder, decoder-only) that tells you which shape the rest of this domain assumes.
- **Core** → [[Deep Dive - The Transformer]] — the full block-by-block walkthrough (attention → FFN → residual → norm, stacked); every other note here extends it or replaces one piece.
- **Advanced** → [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — why every serving-cost-sensitive model since 2023 shares or compresses KV heads, and what it costs in quality.
- **Frontier** → [[Decision - Choosing a Sequence Mixer]] — the live 2025-2026 debate (full attention vs. sliding-window vs. SSM vs. hybrid) written up as a decision with a tradeoff matrix.
- **Unicorn** → [[Breakdown - DeepSeek-V3 Architecture]] — MLA, fine-grained MoE, and multi-token prediction combined in one shipped 671B-parameter system, reverse-engineered.

## Foundations of the transformer block

- [[Deep Dive - The Transformer]] — the reference architecture: multi-head self-attention, position-wise FFN, residual connections, and layer norm, traced end to end with a diagram.
- [[Concept - Attention Mechanism]] — the $\mathrm{softmax}(QK^T/\sqrt{d_k})V$ mechanism itself: why the $\sqrt{d_k}$ scale exists and what happens to the softmax when it's missing.
- [[Concept - Positional Encoding]] — how order gets injected into a permutation-invariant attention operation, from sinusoidal to learned to rotary.
- [[Concept - Encoder-Decoder and Decoder-Only Architectures]] — why nearly every general-purpose LLM since GPT converged on decoder-only despite the encoder-decoder's cross-attention advantages for translation-shaped tasks.
- [[Concept - Feed-Forward Networks and GLU Variants]] — the two-thirds of a transformer's parameters that aren't attention, and why SwiGLU beat plain ReLU MLPs almost everywhere.
- [[Reference - Transformer Architecture Cheat Sheet]] — parameter-count and FLOP formulas by shape, for sizing a model before you've written a line of training code.

## Attention mechanics and variants

- [[Concept - Multi-Head Attention Variants (MHA MQA GQA MLA)]] — the KV-head-sharing spectrum from MHA to MQA to GQA to DeepSeek's low-rank MLA, and the bytes-per-token each saves.
- [[Concept - Rotary Position Embeddings (RoPE)]] — encoding relative position as a rotation in each 2D subspace of the head dimension, and why that makes it trivially compatible with KV caching.
- [[Concept - Sparse and Sliding-Window Attention]] — trading full $O(n^2)$ attention for a fixed local window plus occasional global tokens to break the quadratic memory wall.
- [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]] — why raw attention logits blow up at scale and the two competing fixes (normalizing Q/K, or capping the logits with a tanh) that keep training stable.
- [[Pattern - Interleaving Global and Local Attention]] — alternating local sliding-window layers with occasional full-attention layers to get most of the compute savings without losing long-range recall.
- [[Gotchas - Implementing Attention]] — the causal-mask-off-by-one, dtype-mismatch, and numerically-unstable-softmax bugs that make a from-scratch attention implementation silently wrong.
- [[Snippet - Scaled Dot-Product Attention from Scratch]] — a minimal, runnable reference implementation to numerically check any optimized attention kernel against.
- [[Snippet - RoPE Implementation]] — the rotate-half implementation detail that's easy to get subtly wrong and hard to detect without a reference check.

## Mixture of Experts

- [[Concept - Mixture of Experts Architecture]] — routing each token to a sparse subset of expert FFNs so parameter count scales independently of FLOPs per token.
- [[Decision - Dense vs Mixture-of-Experts]] — when the MoE's extra memory, communication, and routing-instability cost is worth the FLOP-efficiency win, with real numbers.
- [[Breakdown - Mixtral 8x7B]] — Mistral's 8-expert, top-2-routed model reverse-engineered: 47B total parameters, ~13B active per token, and what that ratio buys.
- [[Breakdown - DeepSeek-V3 Architecture]] — 671B total / 37B active parameters via fine-grained MoE plus a shared expert, combined with MLA and multi-token prediction.
- [[Gotchas - Mixture of Experts]] — router collapse, expert-capacity overflow, and the load-balancing-loss tuning that keeps every expert in use.
- [[Snippet - Top-2 MoE Routing Layer]] — a minimal runnable top-2 gating and dispatch implementation to check a production MoE layer's routing logic against.

## Sequence mixers beyond attention

- [[Concept - State Space Models and Mamba]] — the selective-scan mechanism that gives Mamba $O(n)$ sequence-length scaling by making the SSM's transition matrices input-dependent.
- [[Concept - Linear Attention]] — reformulating attention without the softmax so the $QK^TV$ product can be computed as $Q(K^TV)$, trading exact softmax attention for linear-time approximations.
- [[Concept - Hybrid SSM-Attention Architectures]] — interleaving a few full-attention layers into an otherwise-SSM stack to recover the in-context recall that pure SSMs lose.
- [[Decision - Choosing a Sequence Mixer]] — full attention vs. sliding-window vs. linear attention vs. SSM vs. hybrid, laid out against the recall-vs-throughput tradeoff each one makes.
- [[Concept - Recurrent Networks and the LSTM]] — the gated-recurrence predecessor to attention, and why its sequential dependency chain is what attention was built to escape.
- [[Concept - Convolutional Neural Networks]] — the sliding-window, weight-shared predecessor architecture, relevant here as the historical baseline sequence and vision mixers are still benchmarked against.

## Stability, scaling, and extension

- [[Concept - Normalization Placement (Pre-Norm, Post-Norm, DeepNorm)]] — why post-norm transformers become untrainable past a few dozen layers and what pre-norm and DeepNorm each do to the residual stream's gradient scale to fix it.
- [[Concept - The Residual Stream]] — the additive channel every sublayer reads from and writes to, and why its growing norm across depth is what normalization placement manages.
- [[Concept - Context Length Extension]] — how models trained at one context length get extended to another via RoPE scaling (linear, NTK-aware, YaRN) without full retraining.
- [[Concept - Multi-Token Prediction]] — predicting several future tokens per forward pass instead of one, and the throughput and quality gains DeepSeek-V3 reported from it.

## Building and verifying an architecture

- [[Checklist - New Architecture Bring-Up]] — the pre-flight checks (shape asserts, gradient checks, overfit-one-batch) that catch an architecture bug before it burns a training run.
- [[Playbook - Numerically Matching a Reference Implementation]] — the step-by-step procedure for proving your reimplementation of a published architecture produces bit-for-bit-comparable outputs.
- [[Lore - The Standardization of the Transformer Block]] — how the field converged on one dominant block shape (pre-norm, RoPE, SwiGLU, GQA) after years of architecture search papers that mostly didn't survive contact with scale.

## Adjacent domains

- [[MOC - Neural Networks]] — the layer primitives (backprop, activations, optimizers) these architectures are built out of, one level down the stack.
- [[MOC - Training at Scale]] — what it takes to get one of these architectures to converge at billions of parameters: parallelism, mixed precision, and the failure modes normalization placement is meant to prevent.
- [[MOC - Inference & Serving]] — where the KV-cache and FLOP tradeoffs baked into an attention or MoE design get cashed out as dollars per million tokens.
- [[MOC - Hardware & Systems]] — the SRAM, HBM, and interconnect constraints that make some of these architectural choices (GQA, sparse attention) look less like taste and more like arithmetic.
