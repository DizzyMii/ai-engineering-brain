---
tags: [concept, domain/architectures, level/advanced]
aliases: [SWA, sliding-window attention, local attention, sparse attention]
summary: "Restricting which positions attend to which — sliding windows, strided patterns, global+local — to cut attention's O(N²) cost."
---
> **One-paragraph hook:** Full [[Concept - Attention Mechanism]] lets every token look at every other token, and that's why it costs `O(N²)`. Sparse and sliding-window attention keep the same softmax lookup but restrict the *set* of positions each query can see: a fixed local window, a strided pattern, or a small set of global tokens. You give up some long-range recall and get a cost that scales linearly (or near-linearly) with sequence length. It's the lever that lets Mistral 7B advertise a 4096-token attention cost per layer while still reasoning over much longer contexts, and it's the direct ancestor of every "efficient attention" pattern from before the SSM/linear-attention wave.

## The mechanism

**Sliding-window attention (local attention).** Replace the full causal mask (attend to all `j ≤ i`) with a band: the query at position `i` attends only to positions `j` with `i - w + 1 ≤ j ≤ i`, for window size `w`. The mask shrinks from a full lower triangle to a diagonal strip of width `w`. Per-token cost drops from `O(N)` to `O(w)`, and layer cost from `O(N²d)` to `O(Nwd)`. Mistral 7B (Jiang et al. 2023) uses `w = 4096`. Layer `k`'s window covers only 4096 tokens directly, but layer `k`'s output already mixed in information from layer `k-1`'s window, so a token's *effective* receptive field grows with depth. After `L` layers, information can in principle travel `L·w` tokens back, the same way a stack of dilated convolutions grows its receptive field. It's the receptive-field math of [[Concept - Convolutional Neural Networks]] imported into attention.

**Global + local (Longformer, BigBird).** Longformer (Beltagy et al. 2020) uses the sliding window by default and adds a few *global* tokens (task-specific, e.g. `[CLS]` for classification or the question tokens in QA) that attend to and are attended by every position. Only those few tokens pay full-`N` cost. BigBird (Zaheer et al. 2020) adds random attention edges between otherwise-unconnected positions and proves the resulting sparse graph is a universal approximator of sequence functions and Turing-complete, provided the graph has small diameter. Most of the structure is windowed; the random edges keep any two positions reachable in a few hops.

**Strided / factorized attention.** The Sparse Transformer (Child et al. 2019) splits full attention into two cheaper heads. One attends to the previous `l` positions (local, like a sliding window). The other attends to every `l`-th position going back (strided). Stacked across layers, the two patterns let information reach any position in `O(√N)` hops instead of one, and total complexity falls from `O(N²)` to `O(N√N)`.

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

Mistral 7B pairs its `w = 4096` window with a **rolling-buffer KV cache**. The cache is a fixed-size ring buffer of `w` slots indexed by `position mod w`, so its memory stays constant with sequence length, where a standard [[Concept - KV Cache]] grows linearly. That's a large serving-memory win at long context; the price is that each layer only ever *directly* sees the last `w` tokens. Longformer sizes the window per layer: smaller in early layers (e.g. 512), larger in later ones (e.g. 2048), mirroring coarse-to-fine receptive-field growth in CNNs. BigBird's block-sparse implementation is built around TPU tiling and processes the window/random/global pattern in fixed-size blocks, not token by token, to keep hardware utilization high.

Since the window bounds the KV cache at `w` tokens per layer, attention's *serving* memory is bounded no matter how long a conversation runs. That tradeoff is the first question in [[Decision - Choosing a Sequence Mixer]]: do you need exact long-range recall, or is a bounded local window plus depth-driven propagation good enough? StreamingLLM (Xiao et al. 2023) showed a naive rolling window isn't enough for indefinite generation. You also have to keep the first few tokens permanently in the cache (the "attention sink", see [[Concept - Attention Sinks]]), or quality collapses the moment they're evicted, even though the receptive-field argument says a pure recency window "should" suffice.

## Failure modes

- **Long-range exact-match failure.** Information beyond the window only reaches a token through several layers of indirection. On needle-in-a-haystack or exact-copy tasks with the needle more than `L·w` tokens back, quality falls off a cliff. Sweep needle distance and look for a sharp threshold instead of a smooth curve.
- **Naive window eviction collapse.** A rolling KV cache that evicts the very first tokens once full causes a sudden perplexity spike. Those tokens act as a learned softmax stabilizer (an attention sink); their content doesn't matter. Symptom: generation is fine up to exactly `w` tokens, then degrades sharply. Fix: pin the first `k` tokens permanently in the cache next to the sliding window (StreamingLLM).
- **Ring-buffer indexing bugs.** A `position mod w` cache is easy to get off-by-one at the wrap boundary. It doesn't crash. It silently corrupts which token's KV a slot holds, and generation turns garbled only after the first `w` tokens. Catch it with a unit test that decodes past the window boundary and compares against a non-windowed reference.
- **BigBird's random-edge coverage gaps.** The random pattern is sampled once per position (or per layer) and isn't guaranteed to connect every pair of positions a given downstream task needs. Inputs built adversarially around the random pattern can still fail, even though the average-case theoretical guarantee holds.

## The non-obvious

The headline number is easy to misread. Mistral 7B's 32 layers × 4096-token window give a *theoretical* receptive field of up to ~131k tokens by the final layer. That assumes information propagates cleanly hop by hop through every intervening layer, with each layer's attention and FFN preserving and forwarding the signal instead of overwriting it. In practice the *effective* receptive field for a given piece of information is almost always much shorter than the bound. A 50-layer CNN's nominal receptive field rarely matches its practical one for the same reason: gradient signal along very indirect paths is weak during training, so the model has little incentive to learn to relay information that far. Treat `L·w` as an upper bound on what the architecture allows. Check what the trained model actually does with a distance-swept retrieval probe.

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
