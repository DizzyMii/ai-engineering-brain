---
tags: [concept, domain/production-ops, level/unicorn]
aliases: [serving nondeterminism, batch invariance, temperature-0 nondeterminism, batch-invariant kernels]
summary: "Why identical requests diverge even at temperature 0 — batch-dependent floating-point reductions — and the operational fallout."
---

# Concept - Nondeterminism in Production LLM Serving

> **One-paragraph hook:** You set `temperature=0` and expect greedy decoding to be a pure function of the input. It isn't. Send the same request to a production endpoint twice and you can get two different completions. Sampling has nothing to do with it: the *numerics* of the forward pass depend on what else was in the GPU batch when your request landed. That breaks golden-file tests, makes the [[Concept - Semantic Caching|semantic cache]] lossy by construction, and can make an incident literally impossible to reproduce. Knowing the mechanism tells you which reproducibility fights you can win and which to stop picking.

## The mechanism

Greedy decoding selects $\arg\max_i z_i$ over the logit vector $z$. That looks deterministic. The nondeterminism comes in one level down, in how $z$ gets computed.

Floating-point addition is **not associative**: $(a+b)+c \neq a+(b+c)$ in general, because each `+` rounds. A matmul or normalization reduction sums thousands of terms, and the GPU sums them in whatever order its tiling, split-K and reduction strategy dictate. Change the order and the low bits of every logit change:

$$z = \sum_{k=1}^{d} w_k x_k \quad\text{— the value of the sum depends on the accumulation order the kernel chose.}$$

The perturbation is tiny, often below $2^{-10}$ relative, and it only matters at the argmax. If the top two logits are separated by $\delta = z_{(1)} - z_{(2)}$ and reordering moves logits by up to $\epsilon$, then whenever $\delta < 2\epsilon$ the argmax can **flip** to a different token. Across a 128k-token vocabulary and hundreds of decode steps, near-ties are common, especially at low-entropy positions where the model is "sure" but two near-synonyms are essentially tied. One flip changes the autoregressive sequence from that token on, and a sub-ULP wobble becomes a completely different paragraph.

The usual folk explanation is "concurrency + non-deterministic atomics". For the forward pass that's mostly wrong, a point Thinking Machines Lab sharpened in its 2025 post *Defeating Nondeterminism in LLM Inference*. The main cause is **lack of batch invariance**. Kernel reduction strategy is chosen by tensor *shape*, so the same request does different math depending on the batch it's served in:

```text
# Same request, two batch compositions:
logits_A = forward(req, batch=[req])                       # batch size 1
logits_B = forward(req, batch=[req, other1, ..., other7])  # batch size 8

# RMSNorm reduces over a different layout, matmul picks a different
# split-K / tile, attention reduces over a different number of KV blocks
#   -> logits_A and logits_B differ in the low bits
#   -> argmax can differ -> different completion for the SAME req
```

Your output depends on your neighbors' traffic. Under [[Concept - Continuous Batching|continuous batching]], batch composition is a nondeterministic function of concurrent load, so run-to-run variance is baked in even on identical hardware with a fixed model.

Secondary sources sit on top of that: non-deterministic GPU atomics in a few kernels, cuBLAS/attention autotuning picking different kernels by shape, [[Concept - Mixture of Experts Architecture|MoE]] expert routing shifting under batching, tensor-parallel all-reduce order across GPUs, and, at the provider level, load balancing that silently spreads your traffic across model minor-versions and hardware generations. An H100 and an H200 don't produce bit-identical results.

## In practice

Thinking Machines showed that swapping in **batch-invariant** RMSNorm, matmul and attention kernels makes serving bitwise-deterministic: the same request returns identical tokens whatever the batch. The price is throughput. Forcing a fixed reduction strategy gives up the fastest shape-specialized kernel, and their unoptimized deterministic vLLM config ran on the order of ~2x slower before attention-kernel work narrowed the gap. Most production systems won't pay that, so they live with the variance.

Provider `seed` parameters (OpenAI's `seed` plus the `system_fingerprint` in the response) pin the sampling RNG and reduce variance. They do **not** guarantee reproducibility, since they can't control which batch you land in. One useful side effect: a *changed* `system_fingerprint` for the same model id tells you the backend config changed under you, which feeds [[Concept - Production Monitoring and Drift Detection|drift detection]]. The sibling note [[Concept - Nondeterminism in LLM Inference]] covers the kernel/hardware view at the serving layer, and [[Concept - Sampling and Decoding Parameters|sampling parameters]] covers what `temperature`, `top_p` and `seed` actually control.

What this changes operationally:
- **Testing:** you can't assert exact-string equality. Use semantic or property assertions (schema-valid, contains-key-facts, judge-passes) with retries.
- **Caching:** the [[Concept - Semantic Caching|semantic cache]] is inherently lossy. Two "identical" runs it dedups may have differed anyway. That's usually fine, but make it a conscious call.
- **Evals:** one sample is noise. Report over $n$ samples with confidence intervals; see [[Concept - Statistical Rigor in Model Evaluation|statistical rigor in evaluation]].
- **Incident forensics:** you may never reproduce the exact bad output, so log the full completion, not only the inputs and a seed. It's also why [[Pattern - Resilient LLM Request Handling|resilient request handling]] treats a retry as a *fresh* generation and not a replay.

## Failure modes

- **Golden-file tests that flake forever.** A snapshot test passes locally and fails in CI ~5% of the time. Cause: exact match on a non-deterministic output. Fix: property assertions; never `assert output == golden`.
- **"It worked in staging."** Behavior differs between staging and prod on the same model id and prompt. Cause: different batch sizes, load or GPU generation. Detection: log `system_fingerprint` and the serving hardware, then compare.
- **Seed cargo-culting.** A fixed `seed` "stopped reproducing" after some date. Cause: a provider backend change (new `system_fingerprint`); the seed was never a cross-backend guarantee. Detection: alert on `system_fingerprint` changes.
- **Reproduction rabbit holes.** Engineers burn a day trying to reproduce one bad output that can't be reproduced. The fix is cultural: log outputs, and stop trying to bisect a single sample.

## The non-obvious

The lesson people learn the hard way: **temperature 0 does not mean deterministic, and it never promised to.** Determinism was never a property of the sampler. It was an unstated assumption about the numerics underneath, and that assumption is false once your request shares a GPU with anyone else's. So treat every LLM call as a *draw from a distribution*, even at `temp=0`. Tests, caches, evals and SLOs should all be statistical. Teams that accept this stop filing "flaky output" bugs and start reporting rates and intervals, the only honest way to describe a system whose output depends on strangers' traffic.

## Connections
- [[Concept - Semantic Caching]] — the cache is lossy by construction because the "identical" runs it dedups may have differed anyway.
- [[Concept - Sampling and Decoding Parameters]] — clarifies what `temperature`/`seed` actually govern, and why they don't buy determinism.
- [[Concept - Floating Point for Deep Learning]] — the non-associativity of FP addition is the root cause of the logit wobble.
- [[Concept - Continuous Batching]] — the serving mechanism that makes batch composition, and therefore your numerics, load-dependent.
- [[Concept - Mixture of Experts Architecture]] — routing under batching is an additional source of run-to-run divergence.
- [[Concept - Statistical Rigor in Model Evaluation]] — why nondeterminism forces multi-sample evals with confidence intervals.
- [[Concept - Production Monitoring and Drift Detection]] — a changed `system_fingerprint` is both a nondeterminism source and a drift signal.
- [[Pattern - Resilient LLM Request Handling]] — retries are fresh generations, not replays, precisely because of this.
- [[Concept - Nondeterminism in LLM Inference]] — the serving-layer sibling covering kernels and hardware.
- [[Lore - The Nondeterminism of Floating-Point Reductions]] — the foundational war story of why parallel reductions aren't reproducible.
- [[Lore - When the Model Changed Under You]] — distinguishes benign per-request nondeterminism from an actual provider backend change.

## Sources
- Thinking Machines Lab / He et al. (2025) — *Defeating Nondeterminism in LLM Inference*. Argues batch-invariance, not atomics, is the primary cause of run-to-run variance; demonstrates bitwise-deterministic serving via batch-invariant kernels at a throughput cost.
- OpenAI API reference — `seed` and `system_fingerprint`. Documents best-effort reproducibility and the fingerprint as a backend-change signal.
