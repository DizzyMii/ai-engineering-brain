---
tags: [concept, domain/architectures, level/core]
aliases: [FFN, MLP block, SwiGLU, GEGLU, ReGLU, GLU]
summary: "The position-wise sublayer holding most of a block's parameters, and the gated SwiGLU-style variants that replaced the plain two-layer MLP."
---
> **One-paragraph hook:** A transformer block has two sublayers. Attention mixes information across positions; the feed-forward network (FFN) processes each position on its own and holds most of the block's parameters and FLOPs. Since 2020 almost every frontier model has replaced the vanilla two-matrix FFN with a gated variant like SwiGLU. The change adds a third weight matrix and consistently improves quality per parameter, and its adoption is a good case study in "empirically works, theoretically unexplained."

## The mechanism

The vanilla FFN is a position-wise two-layer MLP, the same shape as a [[Concept - The Multilayer Perceptron]] applied separately to every token in the sequence:

$$y = W_2 \, \text{act}(W_1 x + b_1) + b_2$$

Hidden width $d_{ff}$ is conventionally $4 \times d_{model}$ (the original Transformer's choice). There's no cross-token mixing here; that's [[Concept - Attention Mechanism]]'s job. Per block the FFN costs roughly $2 \cdot d_{ff} \cdot d_{model} = 8 d_{model}^2$ parameters at the conventional 4x ratio, against roughly $4 d_{model}^2$ for attention's QKVO projections. So the FFN typically holds about two-thirds of a block's parameters and FLOPs.

The activation changed over time. The original Transformer used ReLU. BERT and GPT-2/3 used GELU, a smooth approximation ($x \cdot \Phi(x)$) picked for better gradient behavior than ReLU's hard kink. Then came SiLU/Swish ($x \cdot \sigma(x)$), which became the default once paired with gating.

**GLU variants** (Shazeer 2020, "GLU Variants Improve Transformer") add a gate. You compute an activated branch and a separate linear (ungated) branch, multiply them elementwise, then project down:

$$\text{SwiGLU}(x) = \big(\text{SiLU}(xW_1) \odot xW_3\big) W_2$$

GEGLU and ReGLU put GELU or ReLU in the activated branch instead. Shazeer's ablations show a consistent perplexity improvement over vanilla ReLU/GELU FFNs at matched compute, and that has held up in every major open-weight model family since.

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

**Parameter matching.** A GLU FFN has *three* weight matrices ($W_1, W_3 \in \mathbb{R}^{d_{model} \times d_{ff}}$, $W_2 \in \mathbb{R}^{d_{ff} \times d_{model}}$), so at the same $d_{ff}$ it costs 50% more parameters and FLOPs than the vanilla FFN. To stay comparable to a plain 4x FFN, LLaMA shrinks $d_{ff}$ to roughly $\frac{8}{3} d_{model}$ and rounds up to a hardware-friendly multiple (e.g., a multiple of 256) so the GEMMs tile cleanly. Example: LLaMA-2 7B has $d_{model}=4096$. A vanilla 4x FFN would use $d_{ff}=16384$; LLaMA-2's actual GLU $d_{ff}$ is 11008, close to $\frac{8}{3}\times 4096 \approx 10922$ after rounding.

## In practice

SwiGLU ships in LLaMA/LLaMA-2/LLaMA-3, PaLM, and Mistral/Mixtral. GeGLU ships in Gemma and Gemma 2. Nearly all modern FFN implementations drop the bias terms ($b_1, b_2$). That's empirically harmless and saves parameters plus a little compute and memory traffic.

The standard interpretability bridge is the **FFN-as-key-value-memory** view (Geva et al. 2021, "Transformer Feed-Forward Layers Are Key-Value Memories"). Each row of $W_1$ is a "key", a pattern detector that fires when the input resembles some direction. The matching column of $W_2$ is the "value" written into [[Concept - The Residual Stream]] when that key fires:

$$y = \sum_i \text{act}(k_i \cdot x) \, v_i, \quad k_i = \text{row}_i(W_1), \; v_i = \text{col}_i(W_2)$$

Neuron-level interpretability work ("what does hidden unit $i$ represent?") rests on this framing, and it ties straight into [[Concept - Superposition]]. With $d_{ff}$ often 4–8x larger than $d_{model}$, the FFN is one of the two places (the residual stream is the other) where superposed, polysemantic features get studied most.

## Failure modes

The FFN carries roughly two-thirds of a block's parameters and FLOPs, which makes it the sublayer [[Concept - Mixture of Experts Architecture]] sparsifies. If you want more capacity per active FLOP, the FFN is where you get it. Virtually every MoE architecture swaps the FFN for experts and never touches the attention sublayer.

A common porting bug: assuming the vanilla $d_{ff} = 4 d_{model}$ convention when writing inference code for a GLU-based checkpoint. GLU models use a scaled-down $d_{ff}$ (the 8/3 rule above). Hardcode the wrong ratio and you get either a shape mismatch, which fails loudly, or, if you load weights by position instead of by name, a silent mix-up of $W_1$ and $W_3$. That one produces garbage output with no error.

Activation choice also interacts with numerics. SwiGLU's unbounded gate branch can produce a wider dynamic range of activations than a plain GELU FFN, which matters when you pick tile/block scaling factors under [[Concept - Mixed Precision Training]]. An FFN that trained cleanly in bf16 can show larger quantization error under aggressive fp8 schemes unless the gate branch's outlier activations get per-tile scales instead of per-tensor ones.

## The non-obvious

The "4x expansion" and "SwiGLU specifically" defaults that nearly every frontier LLM inherits are mostly empirical folklore, not theory. Shazeer's 2020 paper says outright that it offers "no explanation" for why the SwiGLU/GEGLU family beats plain GELU; it reports the ablation and stops. A one-page empirical note with no mechanistic theory became a default across nearly every open-weight LLM since 2022. A surprising amount of transformer architecture is "we tried it and it worked" and not first-principles design. (Folklore, weakly sourced: some practitioners explain the gate after the fact as an implicit per-neuron soft feature-selection mechanism, like attention inside the FFN. It sounds plausible, but it's a post-hoc rationalization and wasn't the original justification.)

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
