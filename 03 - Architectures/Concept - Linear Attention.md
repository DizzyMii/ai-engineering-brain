---
tags: [concept, domain/architectures, level/frontier]
aliases: [linear transformers, kernelized attention, fast-weight attention, linear-time attention]
summary: "Attention reformulated via kernel feature maps to run in O(N) — mathematically a fast-weight RNN, trading softmax's exact recall for constant-memory inference."
---
> **One-paragraph hook:** Softmax [[Concept - Attention Mechanism]] costs `O(N²)` for a specific reason: the exponential in softmax can't be factored, so the full score matrix has to exist before you can normalize it. Swap exact softmax normalization for a kernel approximation and matrix-multiplication associativity lets you reorder the computation into `O(N)`. It also shows that "linear attention" is the same object as a recurrent network with a matrix-valued hidden state, which ties it back to [[Concept - Recurrent Networks and the LSTM]] and forward to [[Concept - State Space Models and Mamba]].

## The mechanism

For each query `i`, standard attention computes `output_i = Σ_j softmax(q_i·k_j) v_j`. The `exp()` inside softmax applies elementwise to each score, and normalizing needs the sum over *all* `j` before any output exists. That dependency forces you to materialize the full `[N, N]` score matrix, and it's the entire source of the quadratic cost.

**The kernel trick.** Replace `exp(q·k)` with a factorizable approximation `φ(q)·φ(k)` for some feature map `φ: ℝ^d → ℝ^m`. Then:

$$
\text{output}_i = \frac{\sum_j \big(\phi(q_i)\cdot\phi(k_j)\big)\, v_j}{\sum_j \phi(q_i)\cdot\phi(k_j)} = \frac{\phi(q_i)\cdot \Big(\sum_j \phi(k_j)\, v_j^\top\Big)}{\phi(q_i)\cdot\sum_j \phi(k_j)}
$$

Now `φ(q_i)` doesn't have to meet each `k_j` separately before the sum. You accumulate `S = Σ_j φ(k_j) v_j^⊤` (a `d×d_v` matrix) and `z = Σ_j φ(k_j)` (a `d`-vector) once, causally, as running sums, and each query does a single `φ(q_i) · S` lookup. Cost goes from `O(N²d)` to `O(Nd²)`, linear in sequence length.

**The recurrent view (Katharopoulos et al. 2020).** Written causally, this is a recurrence with a *matrix-valued* hidden state:

$$
S_t = S_{t-1} + \phi(k_t)\, v_t^\top, \qquad z_t = z_{t-1} + \phi(k_t), \qquad \text{output}_t = \frac{\phi(q_t)\, S_t}{\phi(q_t)\cdot z_t}
$$

`S_t` accumulates key-value outer products. These are the "fast weights" of Schmidhuber's 1992 fast-weight programmers, back again. Its size (`d × d_v`) stays fixed however long the sequence gets, so per-step inference memory is `O(1)`, the same asymptotic win as an SSM's fixed-size state.

**Feature maps.** Performer (Choromanski et al. 2020) uses random Fourier-style positive orthogonal features (FAVOR+) to build an *unbiased* estimator of the true softmax kernel. Of the linear-attention variants, it's the closest to a principled approximation of standard attention. Simpler practical versions use `elu(x) + 1` or `ReLU(x)` as `φ`, picked mainly because they guarantee non-negativity, so the implied "attention weights" still read as a weighted average.

```text
Quadratic form:                    Linear form:
  S = Q Kᵀ        [N,N]              S = Σ_j φ(k_j) v_jᵀ   [d,d_v]  (running sum)
  A = softmax(S)                     z = Σ_j φ(k_j)         [d]      (running sum)
  out = A V        [N,d_v]           out_i = φ(q_i)·S / (φ(q_i)·z)
  cost: O(N²d), O(N²) memory         cost: O(N d²), O(d·d_v) memory per step
```

## In practice

Linear attention appears where constant-memory, high-throughput long-context inference matters more than exact recall: streaming generation, long audio, genomics-scale sequences, and any setup where a growing [[Concept - KV Cache]] is what limits serving. Pure linear attention is rarely deployed by itself, though. Modern variants add a learned or fixed **decay** term so the state doesn't drift or grow without bound. Gated Linear Attention (GLA, Yang et al. 2023) makes the decay data-dependent: `S_t = diag(α_t) S_{t-1} + φ(k_t) v_t^⊤`. RetNet (Sun et al. 2023) uses a fixed per-head exponential decay (the "retention" mechanism). It gives up flexibility and gets three equivalent computational forms in return (parallel, recurrent, chunkwise), so the same model trains in parallel and serves as a cheap recurrence. DeltaNet (Yang et al. 2024) swaps the purely additive state update for a delta-rule-style correction, which improves associative-recall quality in particular.

The SSM connection is more than an analogy. Mamba-2's **State Space Duality** (Dao & Gu 2024) shows that structured SSMs and linear attention with the right decay structure are one computation seen through two algorithms: the SSM's sequential scan and the chunked linear-attention matmul compute the identical operator. That's the formal reason [[Concept - State Space Models and Mamba]] and linear attention keep converging in recent papers instead of being filed as unrelated efficiency tricks.

As of 2026, linear attention almost always ships as part of a hybrid (see [[Concept - Hybrid SSM-Attention Architectures]]), not as a standalone design. Pure linear-attention models measurably underperform full attention on tasks that need precise token-level recall, and a small fraction of full-attention layers restores most of what's lost.

## Failure modes

- **Worse recall on associative and copy tasks.** Softmax attention gives a sharp, near-one-hot lookup. Linear attention's kernel-approximated weighting is smeared by comparison. On synthetic associative-recall benchmarks (fetch the value paired with a specific earlier key), pure linear-attention models plateau well below equal-size softmax baselines. Catch it with an associative-recall probe swept over distance. A generic language-modeling perplexity number can look deceptively fine.
- **State grows without bound if there's no decay.** A plain running-sum state `S_t = S_{t-1} + φ(k_t)v_t^⊤` never forgets. Early contributions keep diluting the effective average as the sequence grows, and the un-normalized state's magnitude can drift over long sequences and destabilize training. It's the most common bug in hand-rolled linear attention: no decay or gating term, and then surprise when the model degrades at long context even though the "linear" cost looked free.
- **Numerical instability from unbounded feature maps.** Naive positive feature maps (plain `elu(x)+1`) without careful scaling can under/overflow over long accumulation. Performer's random-feature approximation reduces variance but doesn't eliminate it, and the approximation error grows with sequence length. That can bias outputs silently instead of crashing.
- **Gradual quality loss past training length.** Linear attention's "context" is an exponentially-decayed running summary, not exact per-token storage, so retrieval quality slides gradually as context grows past what was trained. Full attention tends to fail more abruptly near the trained context boundary. The gradual version is easier to miss in casual evaluation.

## The non-obvious

Rewriting `softmax(QKᵀ)V` as `φ(Q)(φ(K)ᵀV)` looks like a computational trick. It actually exposes the tradeoff SSMs make from a completely different starting point. Both replace an exact pairwise comparison (a lookup table over every prior token) with a compressed, fixed-size running summary (a "fast weight" matrix). The one design choice left is *how much to decay that summary as new information arrives*.

Seen that way, attention, linear attention and SSMs stop being three architecture families and become one continuous axis. Full softmax attention is one end: infinite-resolution memory, zero decay, linearly growing cache. A plain uniform running average is the other. RetNet-style fixed decay, GLA-style learned decay and Mamba's selective decay all sit in between. That explains why hybrids mixing a few full-attention layers into a mostly-linear or mostly-SSM backbone so consistently beat pure designs at any fixed long-context memory budget: the sweet spot on this axis is rarely at either end, and no single fixed decay rate suits every kind of information a model has to carry forward. Linear attention is one of the concrete techniques that reopened a question the field had treated as settled. [[Lore - The Standardization of the Transformer Block]] covers how thoroughly pure softmax attention had become the assumed default before that.

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
