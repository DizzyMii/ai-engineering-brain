---
tags: [concept, domain/architectures, level/frontier]
aliases: [linear transformers, kernelized attention, fast-weight attention, linear-time attention]
summary: "Attention reformulated via kernel feature maps to run in O(N) — mathematically a fast-weight RNN, trading softmax's exact recall for constant-memory inference."
---
> **One-paragraph hook:** Softmax [[Concept - Attention Mechanism]] costs `O(N²)` for a specific reason: the exponential in softmax can't be factored, so the score matrix has to be fully materialized before you can normalize it. Drop the exact softmax normalization for a kernel approximation, and matrix-multiplication associativity lets you reorder the computation into `O(N)` — and, as a bonus, reveals that "linear attention" is exactly the same object as a recurrent network with a matrix-valued hidden state, closing the loop back to [[Concept - Recurrent Networks and the LSTM]] and forward to [[Concept - State Space Models and Mamba]].

## The mechanism

Standard attention computes, for each query `i`: `output_i = Σ_j softmax(q_i·k_j) v_j`. The `exp()` inside softmax is applied elementwise to each score, and normalization requires the sum over *all* `j` before any output can be produced — that dependency is what forces materializing the full `[N, N]` score matrix and is the entire source of the quadratic cost.

**The kernel trick.** Replace `exp(q·k)` with a factorizable approximation `φ(q)·φ(k)` for some feature map `φ: ℝ^d → ℝ^m`. Then:

$$
\text{output}_i = \frac{\sum_j \big(\phi(q_i)\cdot\phi(k_j)\big)\, v_j}{\sum_j \phi(q_i)\cdot\phi(k_j)} = \frac{\phi(q_i)\cdot \Big(\sum_j \phi(k_j)\, v_j^\top\Big)}{\phi(q_i)\cdot\sum_j \phi(k_j)}
$$

Because `φ(q_i)` no longer needs to interact with each `k_j` independently before summing, the sums `S = Σ_j φ(k_j) v_j^⊤` (a `d×d_v` matrix) and `z = Σ_j φ(k_j)` (a `d`-vector) can be accumulated once — causally, as running sums — and each query then does a single `φ(q_i) · S` lookup. Total cost drops from `O(N²d)` to `O(Nd²)`, linear in sequence length.

**The recurrent view (Katharopoulos et al. 2020).** Written causally, this is exactly a recurrence with a *matrix-valued* hidden state:

$$
S_t = S_{t-1} + \phi(k_t)\, v_t^\top, \qquad z_t = z_{t-1} + \phi(k_t), \qquad \text{output}_t = \frac{\phi(q_t)\, S_t}{\phi(q_t)\cdot z_t}
$$

`S_t` accumulates outer products of keys and values — the "fast weights" of Schmidhuber's 1992 fast-weight programmers, resurrected here — and its size (`d × d_v`) is fixed regardless of how long the sequence gets, giving `O(1)` per-step inference memory, the same asymptotic win as an SSM's fixed-size state.

**Feature maps.** Performer (Choromanski et al. 2020) uses random Fourier-style positive orthogonal features (FAVOR+) to construct an *unbiased* estimator of the true softmax kernel — the closest linear-attention variant to a principled approximation of standard attention. Simpler practical variants use `elu(x) + 1` or `ReLU(x)` as `φ`, chosen mainly to guarantee non-negativity so the implied "attention weights" stay interpretable as a weighted average.

```text
Quadratic form:                    Linear form:
  S = Q Kᵀ        [N,N]              S = Σ_j φ(k_j) v_jᵀ   [d,d_v]  (running sum)
  A = softmax(S)                     z = Σ_j φ(k_j)         [d]      (running sum)
  out = A V        [N,d_v]           out_i = φ(q_i)·S / (φ(q_i)·z)
  cost: O(N²d), O(N²) memory         cost: O(N d²), O(d·d_v) memory per step
```

## In practice

Linear attention shows up wherever constant-memory, high-throughput long-context inference matters more than exact recall: streaming generation, long-audio and genomics-scale sequences, and any setting where a growing [[Concept - KV Cache]] is the binding serving constraint. Pure linear attention is rarely deployed on its own, though — modern variants add a learned or fixed **decay** term to keep the state from drifting or growing unbounded. Gated Linear Attention (GLA, Yang et al. 2023) makes the decay data-dependent: `S_t = diag(α_t) S_{t-1} + φ(k_t) v_t^⊤`. RetNet (Sun et al. 2023) uses a fixed, per-head exponential decay instead — the "retention" mechanism — trading flexibility for having three exactly equivalent computational forms (parallel, recurrent, and chunkwise), letting the same model train in parallel and serve as a cheap recurrence. DeltaNet (Yang et al. 2024) replaces the pure additive state update with a delta-rule-style correction, improving associative-recall quality specifically.

The connection to SSMs isn't just an analogy: Mamba-2's **State Space Duality** (Dao & Gu 2024) shows that structured SSMs and linear attention with the right decay structure are the same underlying computation viewed through two different algorithms — the SSM's sequential scan and the chunked linear-attention matmul are dual ways of computing the identical operator. That's the formal reason [[Concept - State Space Models and Mamba]] and linear attention keep converging in the recent literature rather than being treated as unrelated efficiency tricks.

As of 2026, linear attention's practical role is almost always as a component of a hybrid, not a standalone design — see [[Concept - Hybrid SSM-Attention Architectures]] — because pure linear-attention models measurably underperform full attention on tasks requiring precise token-level recall, and a small fraction of full-attention layers restores most of what's lost.

## Failure modes

- **Recall degradation on associative and copy tasks.** Softmax attention produces a near-one-hot, sharp lookup; linear attention's kernel-approximated weighting is comparatively smeared. On synthetic associative-recall benchmarks (retrieve the value paired with a specific earlier key), pure linear-attention models plateau well below equal-size softmax-attention baselines. Detect with a distance-swept associative-recall probe rather than a generic language-modeling perplexity number, which can look deceptively fine.
- **Unbounded state growth without decay.** A plain running-sum state `S_t = S_{t-1} + φ(k_t)v_t^⊤` never forgets — early-sequence contributions keep diluting the effective average as the sequence grows, and the un-normalized state's magnitude can drift over long sequences, causing training instability. This is the single most common bug in a hand-rolled linear-attention implementation: omitting a decay or gating term and being surprised the model degrades at long context despite the "linear" cost looking free.
- **Numerical instability from unbounded feature maps.** Naive positive feature maps (plain `elu(x)+1`) without careful scaling can under/overflow over long accumulation; Performer's random-feature approximation reduces but does not eliminate variance, and approximation error grows with sequence length, which can silently bias outputs rather than crash outright.
- **Quiet quality regression past training length.** Because linear attention's "context" is an exponentially-decayed running summary rather than exact per-token storage, retrieval quality degrades gradually as context grows past what was trained, in contrast to full attention, which tends to fail more abruptly near the trained context boundary — making linear-attention degradation easier to miss in casual evaluation.

## The non-obvious

Rewriting `softmax(QKᵀ)V` as `φ(Q)(φ(K)ᵀV)` looks like a pure computational trick, but it exposes the same tradeoff SSMs make from a completely different starting point: both replace an exact pairwise comparison (a lookup table over every prior token) with a compressed, fixed-size running summary (a "fast weight" matrix) — the only real design choice left is *how much decay to apply to that summary as new information arrives*. That reframes "attention vs. linear attention vs. SSM" from three separate architecture families into one continuous axis: full softmax attention sits at one end (infinite-resolution memory, zero decay, linearly growing cache), a plain uniform running average sits at the other, and RetNet-style fixed decay, GLA-style learned decay, and Mamba's selective decay are all points in between. This is the underlying reason hybrids that mix a small number of full-attention layers with a mostly-linear or mostly-SSM backbone so consistently beat pure designs at any fixed long-context memory budget: the sweet spot on this axis is rarely at either endpoint, and no single fixed decay rate is right for every kind of information a model needs to carry forward. Linear attention is one of the concrete techniques behind that reopening of a question the field had treated as settled — see [[Lore - The Standardization of the Transformer Block]] for how thoroughly pure softmax attention became the assumed default before this axis got reopened.

## Connections
- [[Concept - Attention Mechanism]] — the full-softmax baseline linear attention approximates; understanding why softmax is unfactorizable is the prerequisite for the whole kernel-trick argument.
- [[Concept - State Space Models and Mamba]] — the State Space Duality result shows structured SSMs and linear attention are the same computation viewed two ways.
- [[Concept - Hybrid SSM-Attention Architectures]] — the practical deployment pattern: a few full-attention layers plus a mostly-linear backbone, because pure linear attention loses recall.
- [[Concept - Recurrent Networks and the LSTM]] — linear attention's recurrent form is a fast-weight RNN with a matrix-valued state, the direct mathematical descendant of the gated recurrence this note covers.
- [[Decision - Choosing a Sequence Mixer]] — the decision framework that weighs linear attention against full attention, sliding windows, and SSMs for a given recall/cost tradeoff.
- [[Deep Dive - FlashAttention]] — the fused-kernel approach to making full softmax attention fast, the alternative strategy to changing the math that linear attention represents.
- [[Concept - Induction Heads]] — the mechanistic-interpretability finding of a two-head circuit implementing exact copy/lookup in full attention, which is precisely the capability linear attention's smeared weighting struggles to reproduce.
- [[Concept - KV Cache]] — the growing-memory structure linear attention's constant-size state is designed to eliminate at serving time.
- [[Lore - The Standardization of the Transformer Block]] — the ladder up-link: the history of the field settling on pure softmax attention as the default, the assumption linear attention's kernel trick reopens.

## Sources
- Katharopoulos, Vyas, Pappas, Fleuret (2020) — "Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention." Establishes the kernel-feature-map reformulation and its recurrent equivalence.
- Choromanski et al. (2020) — "Rethinking Attention with Performers." FAVOR+ random-feature approximation of the softmax kernel.
- Sun et al. (2023) — "Retentive Network: A Successor to Transformer for Large Language Models." Fixed exponential decay ("retention") with parallel/recurrent/chunkwise equivalent forms.
- Yang, Wang, Shen, Panda, Kim (2023) — "Gated Linear Attention Transformers with Hardware-Efficient Training." Data-dependent decay for linear attention state.
- Dao, Gu (2024) — "Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality." Formal equivalence between linear attention and structured SSMs (Mamba-2).
- Schmidhuber (1992) — "Learning to Control Fast-Weight Memories." The original fast-weight formulation linear attention's recurrent view rediscovers.
