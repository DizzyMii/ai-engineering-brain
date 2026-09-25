---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [spec decode, draft-and-verify decoding]
summary: "A cheap draft model proposes several tokens; the target model verifies them in one pass via rejection sampling, cutting latency losslessly at low batch."
---

> **One-paragraph hook:** [[Concept - Prefill and Decode Phases|Decode is memory-bandwidth-bound]]. Each step re-reads the whole weight matrix from HBM to produce one token, and most of the GPU's compute sits idle. Speculative decoding spends that idle compute. A small, cheap draft model proposes several tokens ahead, and the expensive target model checks all of them in one parallel forward pass, at roughly the cost of generating one token. A provably lossless acceptance rule decides which proposed tokens survive, so the output distribution is mathematically identical to sampling from the target alone. It's just faster.

## The mechanism

It rests on the same asymmetry as the rest of inference. At low batch size, decode's arithmetic intensity is far below the compute roofline, so a decode step has *spare FLOPs* even while it fully uses its share of HBM bandwidth. Scoring `k` extra tokens in the forward pass that would otherwise produce one is nearly free in wall-clock time, because the bottleneck (reading weights from HBM) is paid once no matter how many positions you score.

The draft-and-verify loop (Leviathan et al. 2023; Chen et al. 2023):

1. A small **draft model** proposes `k` tokens autoregressively, one at a time. It's small enough that doing this sequentially is still fast.
2. The **target model** runs one forward pass over all `k` proposed tokens plus the existing context, producing target probabilities `p` at each of the `k+1` positions (`k` proposed + 1 "next" position past them).
3. From the first position on, each drafted token is accepted or rejected by a rejection-sampling rule that compares the target's probability `p(x)` with the draft's probability `q(x)` for that token `x`.
4. Generation stops at the **first rejection**. Everything accepted before it is kept, the rejected token is replaced by a resampled one, and decoding continues from there. If *all* `k` tokens pass, a **bonus token** is sampled straight from the target's distribution at position `k+1`. It's free because the target already computed it.

The acceptance rule is what makes this lossless instead of approximate:

$$
\text{accept } x \text{ with probability } \min\left(1, \frac{p_{\text{target}}(x)}{p_{\text{draft}}(x)}\right)
$$

On rejection, the replacement token comes from the **normalized positive residual**, not from `p` directly:

$$
p_{\text{residual}}(x) = \frac{\max(0,\; p_{\text{target}}(x) - p_{\text{draft}}(x))}{\sum_{x'} \max(0,\; p_{\text{target}}(x') - p_{\text{draft}}(x'))}
$$

Together, the accept rule and the residual resample reconstruct `p_target` algebraically, whatever `q` (the draft distribution) was. It's a proof-carrying form of [[Concept - KL Divergence|divergence-aware]] importance correction. In practice that means *any* draft model, however crude, leaves the output statistics unchanged. A bad draft costs speed and never correctness. [[Snippet - Speculative Decoding Verification]] has the runnable version, including an empirical check that the sampled-token histogram matches sampling from `p` directly.

## In practice

Speedup is approximately the expected number of accepted tokens per target forward pass. That depends on the **acceptance rate** `α` (how often the draft agrees with the target) and on the draft/target cost ratio. A well-matched cheap draft, say a distilled ~1B model drafting for a 70B target, typically gives a **2-3x wall-clock latency reduction** on the decode loop. That's a measured win, and the losslessness guarantee means output quality doesn't move.

Draft options:
- A **separately trained small model** in the same family. Fast, but it needs its own training and maintenance pipeline, and tokenizer parity with the target.
- A **distilled same-family model**, trained with [[Concept - Knowledge Distillation]] to track the target's distribution as closely as possible. The closer `q` tracks `p`, the higher `α` and the more tokens accepted per pass.
- **n-gram / prompt-lookahead drafts.** No model, just pattern-matching against the prompt or recent output. Cheap and surprisingly effective on repetitive or structured text such as code, or text that quotes the prompt back.

The caveat people learn the hard way: **this optimizes latency at low batch, and it isn't a throughput technique.** It depends on decode having spare compute for verification, and that only exists while the GPU is memory-bandwidth-bound, meaning low-to-moderate batch size. At high batch the GPU is already compute-saturated (see [[Concept - The Roofline Model]]). Verifying `k` tokens per sequence, rejected more often, across a large batch burns FLOPs that would have gone to useful decode, and speculative decoding can **reduce** aggregate throughput. That's the tension in [[Concept - Latency, Throughput, and Cost in LLM Serving]]. Labs pull this lever for low-QPS, latency-critical paths (interactive chat, agent tool loops where TPOT dominates UX), not for bulk high-concurrency serving where raw throughput is the metric.

## Failure modes

- **Low acceptance from a mismatched draft.** When the draft's distribution drifts meaningfully from the target's (out-of-domain text, a sampling temperature applied to one model and not the other, or a draft that's just too weak), `α` collapses. Each rejection wastes the draft's compute *and* doesn't cut the number of target passes, so you pay for two models and get little or no speedup. Monitor mean accepted tokens per verification pass directly. A value near 1 means spec decode is doing almost nothing and should be disabled or reconfigured.
- **Silent tokenizer/template mismatch.** If draft and target use different tokenizers or chat templates, token IDs at the same textual position can mean different strings, which wrecks the alignment between `q` and `p`. Acceptance tanks and it looks like "the draft model is bad" when it's a plumbing error. Confirm the two share a tokenizer before you diagnose acceptance problems any other way.
- **Extra HBM for two resident models.** The draft, however small, takes VRAM from the same [[Concept - KV Cache|KV cache]] budget. On a tightly memory-constrained deployment that can shrink usable concurrency enough to cancel the latency win, especially if the draft keeps its own KV cache in lockstep with the target's.
- **Running it at the wrong operating point.** The most common mistake is turning spec decode on fleet-wide without checking batch size. A service that's fine at low QPS can lose aggregate throughput once traffic pushes batch size into the compute-bound region. Watch whether enabling it correlates with a throughput *drop* under load, and gate it dynamically on measured batch size or QPS.

## The non-obvious

The algorithm isn't the surprise. The surprise is that speculative decoding is a **free lunch that stops being free** past a measurable point: the batch size where the GPU crosses from memory-bound to compute-bound. That crossover depends on workload and hardware; it isn't a constant. Teams that treat spec decode as a universal win instead of a batch-size-conditional one end up regressing aggregate throughput in production while per-request latency still *looks* better in isolated benchmarks. The benchmark that validates it (single-stream latency) measures something different from the metric it can damage (fleet throughput at saturation). Measure only the first and the regression goes unnoticed.

## Connections
- [[Concept - Self-Drafting Speculative Decoding (Medusa, EAGLE, Lookahead)]] — the family of methods that get proposal tokens from the target model's own computation instead of a separate draft model, removing the second-model memory/tokenizer overhead.
- [[Snippet - Speculative Decoding Verification]] — the runnable implementation of the accept/residual-resample rule this note derives.
- [[Concept - Prefill and Decode Phases]] — the compute-bound/memory-bound asymmetry that creates the spare decode-time compute speculative decoding spends.
- [[Concept - Sampling and Decoding Parameters]] — the target distribution `p` that verification samples from is exactly the temperature/top-p-adjusted distribution this note covers.
- [[Concept - Knowledge Distillation]] — the technique used to train a draft model whose distribution tracks the target closely enough for a useful acceptance rate.
- [[Concept - Latency, Throughput, and Cost in LLM Serving]] — the batch-dependent latency-vs-throughput trade-off that determines whether speculative decoding helps or hurts a given deployment.
- [[Concept - The Roofline Model]] — the compute-vs-bandwidth-bound framework that explains exactly why the technique works at low batch and backfires at high batch.
- [[Concept - KL Divergence]] — the distributional-distance concept underlying why acceptance rate depends on how close the draft and target distributions are.

## Sources
- Leviathan et al. (2023) — *Fast Inference from Transformers via Speculative Decoding*. Introduces the draft-verify loop with the modified-rejection-sampling acceptance rule and proves losslessness.
- Chen et al. (2023) — *Accelerating Large Language Model Decoding with Speculative Sampling*. Concurrent, independent formulation of the same core algorithm from DeepMind.
