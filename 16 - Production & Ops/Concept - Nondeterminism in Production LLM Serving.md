---
tags: [concept, domain/production-ops, level/unicorn]
aliases: [serving nondeterminism, batch invariance, temperature-0 nondeterminism, batch-invariant kernels]
summary: "Why identical requests diverge even at temperature 0 — batch-dependent floating-point reductions — and the operational fallout."
---

# Concept - Nondeterminism in Production LLM Serving

> **One-paragraph hook:** You set `temperature=0`, expecting greedy decoding to be a pure function of the input. It isn't. Send the exact same request to a production endpoint twice and you can get two different completions — not because of sampling, but because the *numerics* of the forward pass depend on what else was in the GPU batch when your request happened to land. This breaks golden-file tests, makes the [[Concept - Semantic Caching|semantic cache]] lossy by construction, and can make an incident literally impossible to reproduce. Understanding the mechanism tells you which reproducibility fights are winnable and which you should stop picking.

## The mechanism

Greedy decoding selects $\arg\max_i z_i$ over the logit vector $z$. That looks deterministic. The non-determinism enters one level down, in how $z$ is computed.

Floating-point addition is **not associative**: $(a+b)+c \neq a+(b+c)$ in general, because each `+` rounds. A matmul or a normalization reduction sums thousands of terms, and the GPU is free to sum them in whatever order its tiling, split-K, and reduction strategy dictate. Change that order and the low bits of every logit change:

$$z = \sum_{k=1}^{d} w_k x_k \quad\text{— the value of the sum depends on the accumulation order the kernel chose.}$$

That perturbation is tiny — often below $2^{-10}$ relative. It only matters at the argmax. If the top two logits are separated by $\delta = z_{(1)} - z_{(2)}$ and reordering perturbs logits by up to $\epsilon$, then whenever $\delta < 2\epsilon$ the argmax can **flip** to a different token. Over a 128k-token vocabulary and hundreds of decode steps, near-ties are common — especially at low-entropy positions where the model is "sure" but two near-synonyms are essentially tied. One flip diverges the autoregressive sequence from that token onward, so a sub-ULP wobble becomes a completely different paragraph.

The load-bearing insight — sharpened by Thinking Machines Lab's 2025 post *Defeating Nondeterminism in LLM Inference* — is that the usual folk explanation ("concurrency + non-deterministic atomics") is mostly wrong for the forward pass. The real culprit is **lack of batch invariance**. The same request produces different math depending on the batch it is served in, because kernel reduction strategy is chosen by tensor *shape*:

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

Layered on top of the batch-invariance problem are the secondary sources: non-deterministic GPU atomics in a few kernels, cuBLAS/attention kernel autotuning selecting different kernels by shape, [[Concept - Mixture of Experts Architecture|MoE]] expert routing shifting under batching, tensor-parallel all-reduce order across GPUs, and — at the provider level — load balancing that silently spreads your traffic across model minor-versions and hardware generations (an H100 and an H200 do not produce bit-identical results).

## In practice

Thinking Machines showed that swapping in **batch-invariant** RMSNorm, matmul, and attention kernels makes serving bitwise-deterministic — the same request returns identical tokens regardless of batch. The catch is throughput: forcing a fixed reduction strategy forgoes the fastest shape-specialized kernel, and their unoptimized deterministic vLLM config ran on the order of ~2x slower before attention-kernel work narrowed the gap. Most production systems decline to pay that, so they live with the variance.

Provider `seed` parameters (OpenAI's `seed` plus the `system_fingerprint` in the response) pin the sampling RNG and reduce variance, but they do **not** guarantee reproducibility — they can't control the batch you land in. Usefully, a *changed* `system_fingerprint` for the same model id is a signal that the backend config changed under you, which ties directly into [[Concept - Production Monitoring and Drift Detection|drift detection]]. See the sibling note [[Concept - Nondeterminism in LLM Inference]] for the kernel/hardware view at the serving layer, and [[Concept - Sampling and Decoding Parameters|sampling parameters]] for what `temperature`, `top_p`, and `seed` actually control.

Operationally this reshapes several things:
- **Testing:** you cannot assert exact-string equality. Use semantic or property assertions (schema-valid, contains-key-facts, judge-passes) with retries.
- **Caching:** the [[Concept - Semantic Caching|semantic cache]] is inherently lossy — two "identical" runs it dedups may have differed anyway, which is usually fine but must be a conscious call.
- **Evals:** a single sample is noise. Report over $n$ samples with confidence intervals; see [[Concept - Statistical Rigor in Model Evaluation|statistical rigor in evaluation]].
- **Incident forensics:** you may never reproduce the exact bad output, so log the full completion — not just the inputs and a seed. This is also why [[Pattern - Resilient LLM Request Handling|resilient request handling]] treats a retry as a *fresh* generation, not a replay.

## Failure modes

- **Golden-file tests that flake forever.** Symptom: a snapshot test passes locally, fails in CI ~5% of the time. Cause: exact-match on a non-deterministic output. Fix: property assertions; never `assert output == golden`.
- **"It worked in staging."** Symptom: behavior differs between staging and prod on the same model id and prompt. Cause: different batch sizes / load / GPU generation. Detection: log `system_fingerprint` and the serving hardware; compare.
- **Seed cargo-culting.** Symptom: a fixed `seed` "stopped reproducing" after a date. Cause: a provider backend change (new `system_fingerprint`) — the seed was never a cross-backend guarantee. Detection: alert on `system_fingerprint` changes.
- **Reproduction rabbit holes.** Engineers burn a day trying to reproduce one bad output that is genuinely unreproducible. The fix is cultural: log outputs, and stop trying to bisect a single sample.

## The non-obvious

The thing practitioners learn the hard way: **temperature 0 does not mean deterministic, and it never promised to.** The determinism you lost was never a property of the sampler — it was an unstated assumption about the numerics underneath, and that assumption is false the moment your request shares a GPU with anyone else's. The corollary is a mindset shift: treat every LLM call as a *draw from a distribution*, even at `temp=0`. Your tests, caches, evals, and SLOs should all be statistical. Teams that internalize this stop filing "flaky output" bugs and start reporting rates and intervals — which is the only honest way to talk about a system whose output depends on the traffic of strangers.

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
