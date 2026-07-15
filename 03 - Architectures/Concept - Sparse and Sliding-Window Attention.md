---
tags: [concept, domain/architectures, level/advanced]
aliases: [SWA, sliding-window attention, local attention, sparse attention]
summary: "Restricting which positions attend to which — sliding windows, strided patterns, global+local — to cut attention's O(N²) cost."
---
> **One-paragraph hook:** Full [[Concept - Attention Mechanism]] lets every token look at every other token, which is exactly why it costs `O(N²)`. Sparse and sliding-window attention keep the same softmax-lookup mechanism but restrict the *set* of positions each query is allowed to see — a fixed local window, a strided pattern, or a small set of global tokens — trading some long-range recall for a cost that scales linearly (or near-linearly) with sequence length. This is the architectural lever that lets Mistral 7B advertise a 4096-token attention cost per layer while still reasoning over much longer contexts, and it's the direct ancestor of every "efficient attention" pattern that predates the SSM/linear-attention wave.

## The mechanism

**Sliding-window attention (local attention).** Instead of the full causal mask (attend to all `j ≤ i`), restrict each query at position `i` to a band: attend only to positions `j` with `i - w + 1 ≤ j ≤ i`, for window size `w`. The mask goes from a full lower-triangular matrix to a banded diagonal strip of width `w`. Per-token cost drops from `O(N)` to `O(w)`, and total layer cost from `O(N²d)` to `O(Nwd)`. Mistral 7B (Jiang et al. 2023) uses `w = 4096`: layer `k`'s window still only covers 4096 tokens directly, but because layer `k`'s output already mixed in information from layer `k-1`'s window, a token's *effective* receptive field grows with depth — after `L` layers, information can in principle propagate `L·w` tokens back, exactly the way a stack of dilated convolutions grows its receptive field with depth. This is the same math as [[Concept - Convolutional Neural Networks]] receptive-field growth, imported into attention.

**Global + local (Longformer, BigBird).** Longformer (Beltagy et al. 2020) keeps the sliding window as the default pattern but adds a small number of *global* tokens (task-specific, e.g. `[CLS]` for classification or the question tokens in QA) that attend to — and are attended to by — every position, full-`N` cost for just those few tokens. BigBird (Zaheer et al. 2020) adds a third ingredient, random attention edges between otherwise-unconnected positions, and proves the resulting sparse graph is a universal approximator of sequence functions and Turing-complete, provided the graph has small diameter — the random edges are what keep any two positions reachable in a small number of hops even though most local structure is windowed.

**Strided / factorized attention.** The Sparse Transformer (Child et al. 2019) factorizes full attention into two cheaper heads: one attends to the previous `l` positions (local, same as sliding window), the other attends to every `l`-th position going back (strided). Composing the two patterns across layers lets information reach any position in `O(√N)` hops instead of one hop, reducing total complexity from `O(N²)` to `O(N√N)`.

```text
Full causal:        Sliding window (w=3):    Strided (stride=3):
█░░░░░               █░░░░░                    █░░░░░
██░░░░               ██░░░░                    █░█░░░
███░░░               ███░░░                    ██░█░░
████░░               ▓███░░   ← only last w    █░█░█░
█████░               ░▓███░                    ██░█░█
██████               ░░▓███                    █░█░█░█
```

## In practice

Mistral 7B pairs `w = 4096` sliding-window attention with a **rolling-buffer KV cache**: instead of storing a growing list of past keys/values, the cache is a fixed-size ring buffer of `w` slots indexed by `position mod w`, so cache memory is constant regardless of sequence length rather than growing linearly like standard [[Concept - KV Cache]] — a large serving-memory win at long context, at the cost of the model only ever *directly* seeing the last `w` tokens per layer. Longformer sizes the window per layer, using smaller windows (e.g. 512) in early layers and larger ones (e.g. 2048) in later layers, mirroring the coarse-to-fine receptive-field growth pattern in CNNs. BigBird's block-sparse implementation is designed around TPU tiling, processing the window/random/global pattern in fixed-size blocks rather than token-by-token to keep hardware utilization high.

Because a sliding window bounds the KV cache to `w` tokens per layer, it also bounds attention's *serving* memory cost independent of how long a conversation runs — the tradeoff is explicit and is the first thing [[Decision - Choosing a Sequence Mixer]] asks about: do you need exact long-range recall, or is a bounded local window (plus depth-driven propagation) good enough? StreamingLLM (Xiao et al. 2023) showed that a naive rolling window alone is not enough for indefinite generation: you must additionally keep the first few tokens permanently in the cache (the "attention sink," see [[Concept - Attention Sinks]]) or quality collapses the moment those tokens are evicted, even though a purely recency-based window "should" be sufficient by the receptive-field argument.

## Failure modes

- **Long-range exact-match failure.** Information beyond the window can only propagate through multiple layers of indirection, not directly. On needle-in-a-haystack or exact-copy tasks with the needle placed beyond `L·w` tokens back, quality falls off a cliff rather than degrading gracefully — detect by sweeping needle distance and watching for a sharp threshold rather than a smooth curve.
- **Naive window eviction collapse.** A rolling KV cache that evicts the very first tokens once it fills causes a sudden perplexity spike, because those tokens function as a learned softmax stabilizer (an attention sink), not because of their content. Symptom: generation quality is fine up to exactly `w` tokens generated, then degrades sharply. Fix: pin the first `k` tokens (StreamingLLM) permanently in the cache alongside the sliding window.
- **Ring-buffer indexing bugs.** A rolling-buffer cache indexed by `position mod w` is easy to get off-by-one on at the wrap boundary — the bug silently corrupts which token's KV a given cache slot actually holds rather than crashing, producing garbled generation only past the first `w` tokens. Detect with a unit test that decodes past the window boundary and checks output against a non-windowed reference.
- **BigBird's random-edge coverage gaps.** The random attention pattern is sampled once per position (or per layer) and is not guaranteed to connect every pair of positions that a specific downstream task needs; pathological inputs constructed adversarially around the random pattern can still fail even though the average-case theoretical guarantee holds.

## The non-obvious

The receptive-field math is the whole story, and it's easy to misread the headline number. Mistral 7B's 32 layers × 4096-token window gives a *theoretical* receptive field of up to ~131k tokens by the final layer — but that number assumes information actually propagates cleanly hop by hop through every intervening layer, which requires each layer's attention and FFN to preserve and forward the relevant signal rather than overwrite it. In practice the *effective* receptive field for a specific piece of information is almost always much shorter than the theoretical bound, for the same reason a 50-layer CNN's nominal receptive field rarely equals its practical one: gradient signal for very indirect paths is weak during training, so the model has little incentive to actually learn to relay information that far. Treat the `L·w` number as an upper bound on what's architecturally possible, not a prediction of what the trained model will do — verify empirically with a distance-swept retrieval probe rather than trusting the arithmetic.

## Connections
- [[Concept - Attention Mechanism]] — sparse/windowed attention is the same softmax-lookup formula with a restricted mask; understanding the full-attention baseline is a prerequisite.
- [[Pattern - Interleaving Global and Local Attention]] — the standard fix for local attention's long-range blindness: periodically interleave full-attention layers with local ones.
- [[Concept - Attention Sinks]] — explains *why* naive sliding-window eviction of the first tokens collapses quality, and the StreamingLLM fix.
- [[Deep Dive - FlashAttention]] — the fused kernel that both full and windowed attention are typically implemented on top of; windowing changes which tiles the kernel needs to compute at all.
- [[Concept - KV Cache]] — the memory structure a sliding window directly bounds; this is the serving-cost payoff for the whole technique.
- [[Concept - Context Length Extension]] — a different lever (stretching positional encoding) for the same underlying problem of running past a trained context budget; the two approaches compose.
- [[Concept - Mixture of Experts Architecture]] — a parallel example of restricting a dense `O(N)` operation (here, which experts process a token) to cut cost, the same design pattern applied to the FFN instead of attention.
- [[Decision - Choosing a Sequence Mixer]] — the decision framework that weighs sliding-window attention against full attention, linear attention, and SSMs for a given context-length and recall requirement.

## Sources
- Jiang et al. (2023) — "Mistral 7B." Introduces the 4096-token sliding-window attention with rolling-buffer KV cache used in production.
- Beltagy, Peters, Cohan (2020) — "Longformer: The Long-Document Transformer." Sliding window plus task-specific global tokens.
- Zaheer et al. (2020) — "Big Bird: Transformers for Longer Sequences." Window + random + global attention with a Turing-completeness argument.
- Child, Gray, Radford, Sutskever (2019) — "Generating Long Sequences with Sparse Transformers." Strided/local factorized attention reducing cost to `O(N√N)`.
- Xiao et al. (2023) — "Efficient Streaming Language Models with Attention Sinks" (StreamingLLM). Shows a naive sliding window collapses without pinning the first tokens.
