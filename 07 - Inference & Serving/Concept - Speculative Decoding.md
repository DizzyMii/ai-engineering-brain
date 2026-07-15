---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [spec decode, draft-and-verify decoding]
summary: "A cheap draft model proposes several tokens; the target model verifies them in one pass via rejection sampling, cutting latency losslessly at low batch."
---

> **One-paragraph hook:** [[Concept - Prefill and Decode Phases|Decode is memory-bandwidth-bound]] — each step re-reads the entire weight matrix from HBM to produce a single token, leaving most of the GPU's compute idle. Speculative decoding exploits that idle compute: a small, cheap draft model proposes several tokens ahead, and the expensive target model checks all of them in one parallel forward pass — the same cost as generating one token, roughly. A provably lossless acceptance rule decides which proposed tokens survive, so the output distribution is mathematically identical to sampling from the target model alone, just faster.

## The mechanism

The key observation is the same asymmetry that drives the rest of inference: at low batch size, decode's arithmetic intensity is far below the compute roofline, so a decode step has *spare FLOPs* even though it's fully using its share of HBM bandwidth. Verifying `k` extra tokens in the same forward pass that would otherwise produce one token is nearly free in wall-clock time, because the bottleneck (reading weights from HBM) is paid once regardless of how many token positions you score.

The draft-and-verify loop (Leviathan et al. 2023; Chen et al. 2023):

1. A small **draft model** autoregressively proposes `k` tokens, cheaply, one at a time — it's small enough that this is fast even done sequentially.
2. The **target model** runs a single forward pass over all `k` proposed tokens (plus the existing context) at once, producing target-model probabilities `p` at each of the `k+1` positions (`k` proposed + 1 "next" position past them).
3. Starting from the first position, accept or reject each drafted token using a rejection-sampling rule that compares the target's probability `p(x)` to the draft's probability `q(x)` for the same token `x`.
4. Stop at the **first rejection**; everything accepted before it is kept, the rejected token is replaced by a resampled token, and generation continues from there. If *all* `k` tokens are accepted, a **bonus token** is sampled directly from the target's distribution at position `k+1` — free, because the target model already computed it.

The acceptance rule is what makes this lossless rather than an approximation:

$$
\text{accept } x \text{ with probability } \min\left(1, \frac{p_{\text{target}}(x)}{p_{\text{draft}}(x)}\right)
$$

On rejection, the replacement token is drawn not from `p` directly but from the **normalized positive residual**:

$$
p_{\text{residual}}(x) = \frac{\max(0,\; p_{\text{target}}(x) - p_{\text{draft}}(x))}{\sum_{x'} \max(0,\; p_{\text{target}}(x') - p_{\text{draft}}(x'))}
$$

This specific pairing of accept-rule and residual-resample algebraically reconstitutes exactly `p_target` regardless of what `q` (the draft distribution) was — a proof-carrying form of [[Concept - KL Divergence|divergence-aware]] importance correction. The practical implication: you can use *any* draft model, however crude, and never change the statistical properties of the output. A bad draft only costs you speed, never correctness. See [[Snippet - Speculative Decoding Verification]] for the runnable version of this rule, including an empirical check that the sampled-token histogram matches sampling from `p` directly.

## In practice

Speedup is approximately the expected number of accepted tokens per target forward pass, which is governed by the **acceptance rate** `α` (how often the draft agrees with the target) and the cost ratio between draft and target. A well-matched, cheap draft (e.g., a distilled ~1B model drafting for a 70B target) typically delivers **2-3x wall-clock latency reduction** on the decode loop — a real, measured win, not a theoretical one, and it costs nothing in output quality because of the losslessness guarantee above.

Draft choices in practice:
- A **separately trained small model** in the same family (fast, but needs its own training/maintenance pipeline and tokenizer parity with the target).
- A **distilled same-family model**, explicitly trained via [[Concept - Knowledge Distillation]] to track the target's distribution as closely as possible — the closer `q` tracks `p`, the higher `α`, the more tokens accepted per pass.
- **n-gram / prompt-lookahead drafts** — no model at all, just pattern-matching against the prompt or recent generation, cheap and surprisingly effective for repetitive or structured text (e.g. code, or text quoting the prompt back).

The critical caveat every practitioner learns the hard way: **this is a low-batch, latency-regime optimization, not a throughput one.** The entire mechanism depends on decode having spare compute to spend on verification — that spare compute only exists when the GPU is memory-bandwidth-bound, i.e., at low-to-moderate batch size. At high batch, the GPU is already compute-saturated (see [[Concept - The Roofline Model]]); verifying `k` rejected-more-often tokens per sequence, multiplied across a large batch, burns real FLOPs that were otherwise going to useful decode throughput, and speculative decoding can **reduce** aggregate throughput rather than improve it. This is exactly the tension covered in [[Concept - Latency, Throughput, and Cost in LLM Serving]]: speculative decoding is a lever labs pull for low-QPS, latency-critical paths (interactive chat, agent tool loops where TPOT dominates UX) — not for bulk, high-concurrency batch serving where raw throughput is the metric that matters.

## Failure modes

- **Low acceptance from a mismatched draft.** If the draft's distribution diverges meaningfully from the target's — out-of-domain text, a different sampling temperature applied to one but not the other, or a draft that's simply too weak — `α` collapses, and every rejection wastes the draft's own compute *and* fails to reduce the number of target passes needed, so you pay two models' worth of cost for little or no speedup. Detection: monitor mean accepted-tokens-per-verification-pass directly; a value close to 1 means speculative decoding is providing near-zero benefit and should be disabled or reconfigured.
- **Silent tokenizer/template mismatch.** If the draft and target were trained with different tokenizers or chat templates, token IDs at the same textual position can refer to different strings, corrupting the entire alignment between `q` and `p` — acceptance rate tanks and the bug looks like "the draft model is just bad" rather than a plumbing error. Always verify draft/target share a tokenizer before diagnosing acceptance-rate problems any other way.
- **Extra HBM for two resident models.** The draft model, however small, still occupies VRAM and competes with [[Concept - KV Cache|KV cache]] budget for the same GPU — on a tightly memory-constrained deployment this can shrink usable concurrency enough to offset the latency win, especially if the draft also needs its own KV cache maintained in lockstep with the target's.
- **Deploying it at the wrong operating point.** The single most common mistake is enabling speculative decoding fleet-wide without checking current batch size — a service that's fine at low QPS can see aggregate throughput regress the moment traffic pushes batch size into the compute-bound region; detection is watching whether enabling spec decode correlates with a throughput *drop* under load, and gating it dynamically on measured batch size or QPS.

## The non-obvious

The counterintuitive part isn't the algorithm — it's that speculative decoding is a **free lunch that stops being free** past a specific, measurable point (the batch size where the GPU crosses from memory-bound to compute-bound), and that crossover point is workload- and hardware-specific, not a fixed constant. Teams that treat "enable spec decode" as a universal win rather than a batch-size-conditional one end up quietly regressing their own aggregate throughput in production while latency-per-request still *looks* better in isolated benchmarks — the benchmark that validates spec decode (single-stream latency) is structurally different from the metric it can silently damage (fleet throughput at saturation), and only measuring the first is how the regression goes unnoticed.

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
