---
tags: [concept, domain/architectures, level/core]
aliases: [FFN, MLP block, SwiGLU, GEGLU, ReGLU, GLU]
summary: "The position-wise sublayer holding most of a block's parameters, and the gated SwiGLU-style variants that replaced the plain two-layer MLP."
---
> **One-paragraph hook:** Every transformer block has two sublayers: attention, which mixes information across positions, and the feed-forward network (FFN), which processes each position independently and holds the majority of the block's parameters and FLOPs. Since 2020 almost every frontier model has swapped the vanilla two-matrix FFN for a gated variant like SwiGLU — a change that adds a third weight matrix, consistently improves quality per parameter, and whose adoption is a good case study in "empirically works, theoretically unexplained."

## The mechanism

The vanilla FFN is a position-wise two-layer MLP, structurally identical to a [[Concept - The Multilayer Perceptron]] applied independently to every token in the sequence:

$$y = W_2 \, \text{act}(W_1 x + b_1) + b_2$$

with hidden width $d_{ff}$ conventionally $4 \times d_{model}$ (the original Transformer's choice). Because it processes each position in isolation — no cross-token mixing, that's [[Concept - Attention Mechanism]]'s job — its parameter count per block is roughly $2 \cdot d_{ff} \cdot d_{model} = 8 d_{model}^2$ at the conventional 4x ratio, versus attention's roughly $4 d_{model}^2$ for QKVO projections. The FFN typically holds about two-thirds of a block's parameters and FLOPs.

Activation choice evolved: ReLU in the original Transformer, then GELU (BERT, GPT-2/3 — a smooth approximation, $x \cdot \Phi(x)$, chosen for better gradient behavior than ReLU's hard kink), then SiLU/Swish ($x \cdot \sigma(x)$), which became the default paired with gating.

**GLU variants** (Shazeer 2020, "GLU Variants Improve Transformer") add a gate: instead of one activated branch, compute an elementwise product of an activated branch and a separate linear (ungated) branch, then project down:

$$\text{SwiGLU}(x) = \big(\text{SiLU}(xW_1) \odot xW_3\big) W_2$$

GEGLU and ReGLU swap in GELU or ReLU for the activated branch. The ablations in Shazeer's paper show a consistent perplexity improvement over vanilla ReLU/GELU FFNs at matched compute, and the pattern has held up across every major open-weight model family since.

```
        x
       / \
   W1 x   W3 x
     |      |
  SiLU(·)   |
     \     /
   elementwise ⊙
        |
       W2
        |
      +residual
```

**Parameter matching**: a GLU FFN has *three* weight matrices ($W_1, W_3 \in \mathbb{R}^{d_{model} \times d_{ff}}$, $W_2 \in \mathbb{R}^{d_{ff} \times d_{model}}$) instead of two, so at the same $d_{ff}$ it costs 50% more parameters and FLOPs than the vanilla version. To keep total params/FLOPs comparable to a plain 4x FFN, LLaMA scales $d_{ff}$ down to roughly $\frac{8}{3} d_{model}$, then rounds up to a hardware-friendly multiple (e.g., a multiple of 256) for clean GEMM tiling. Concretely: LLaMA-2 7B has $d_{model}=4096$; a vanilla 4x FFN would use $d_{ff}=16384$, while LLaMA-2's actual GLU $d_{ff}$ is 11008 — close to $\frac{8}{3}\times 4096 \approx 10922$, rounded to a friendly value.

## In practice

SwiGLU ships in LLaMA/LLaMA-2/LLaMA-3, PaLM, and Mistral/Mixtral; GeGLU ships in Gemma and Gemma 2. Bias terms ($b_1, b_2$) are dropped in nearly all modern FFN implementations — empirically harmless, and it saves parameters plus a small amount of compute and memory traffic.

The **FFN-as-key-value-memory** view (Geva et al. 2021, "Transformer Feed-Forward Layers Are Key-Value Memories") is the standard interpretability bridge: treat each row of $W_1$ as a "key" — a pattern detector that fires when the input resembles some direction — and the corresponding column of $W_2$ as the "value" written into the [[Concept - The Residual Stream]] when that key fires:

$$y = \sum_i \text{act}(k_i \cdot x) \, v_i, \quad k_i = \text{row}_i(W_1), \; v_i = \text{col}_i(W_2)$$

This framing is exactly what underlies neuron-level interpretability work asking "what does hidden unit $i$ represent," and connects directly to [[Concept - Superposition]]: with $d_{ff}$ often 4–8x larger than $d_{model}$, the FFN is one of the two places (along with the residual stream itself) where superposed, polysemantic features are most studied.

## Failure modes

Because the FFN carries roughly two-thirds of a block's parameters and FLOPs, it is precisely the sublayer that [[Concept - Mixture of Experts Architecture]] sparsifies — if you're chasing more capacity per active FLOP, the FFN is where the leverage is, which is why virtually every MoE architecture replaces the FFN (never the attention sublayer) with experts.

A concrete porting bug: assuming the vanilla $d_{ff} = 4 d_{model}$ convention when writing inference code for a GLU-based checkpoint. Because GLU models use a scaled-down $d_{ff}$ (the 8/3 rule above), hardcoding the wrong ratio either produces a shape mismatch (loud failure) or, more dangerously if you're loading weights by position rather than by name, silently misassigns which matrix is $W_1$ vs $W_3$ — garbage output with no error.

Activation-choice interacts with numerics: SwiGLU's unbounded gate branch can produce a wider dynamic range of activations than a plain GELU FFN, which matters when choosing tile/block scaling factors under [[Concept - Mixed Precision Training]] — an FFN that trained cleanly in bf16 can show larger quantization error under aggressive fp8 schemes if the gate branch's outlier activations aren't handled with per-tile rather than per-tensor scales.

## The non-obvious

The "why 4x expansion" and "why SwiGLU specifically" defaults that nearly every frontier LLM inherits are largely empirical folklore, not derived from theory. Shazeer's own 2020 paper is explicit that it offers "no explanation" for why the SwiGLU/GEGLU family outperforms plain GELU — the paper reports the ablation result and stops there. That a one-page empirical note with no mechanistic theory became a load-bearing architectural default across nearly every open-weight LLM since 2022 is a useful reminder that a surprising amount of transformer architecture is "we tried it and it worked," not first-principles design (folklore, weakly sourced: some practitioners retroactively explain the gate as an implicit per-neuron soft feature-selection mechanism analogous to attention within the FFN — a plausible-sounding story, but a post-hoc rationalization rather than the original justification).

## Connections

- [[Concept - Attention Mechanism]] — the other transformer sublayer: attention mixes across positions, the FFN processes within one; the two are complementary halves of every block.
- [[Concept - The Residual Stream]] — the shared bus every FFN sublayer writes into; the FFN-as-memory framing is literally "what gets written here."
- [[Concept - Mixture of Experts Architecture]] — the sparsification of exactly this sublayer, since the FFN is where most of a block's capacity lives.
- [[Deep Dive - The Transformer]] — the full block this sublayer is half of, alongside attention.
- [[Concept - RMSNorm and LayerNorm]] — the normalization that sits directly before the FFN input in a pre-norm block.
- [[Concept - Superposition]] — why the FFN's wide hidden layer is a natural place to look for polysemantic, superposed features.
- [[Concept - Mixed Precision Training]] — the gate branch's dynamic range directly affects fp8/low-precision quantization choices.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the FFN's two or three GEMMs are the dominant matmul cost in a transformer block at typical sequence lengths.
- [[Concept - The Multilayer Perceptron]] — the FFN is structurally an MLP applied position-wise; this is the prerequisite mental model.

## Sources
- Vaswani et al. (2017) — "Attention Is All You Need": the original ReLU-based FFN and 4x expansion convention.
- Shazeer (2020) — "GLU Variants Improve Transformer": introduces SwiGLU/GEGLU/ReGLU, with an explicit admission of no theoretical explanation.
- Geva et al. (2021) — "Transformer Feed-Forward Layers Are Key-Value Memories": the interpretability framing of $W_1$/$W_2$ as keys and values.
- Touvron et al. (2023) — LLaMA: the practical 8/3-ratio $d_{ff}$ rescaling to parameter-match a vanilla 4x FFN.
