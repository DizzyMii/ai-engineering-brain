---
tags: [reference, domain/esoterica, level/unicorn]
aliases: [architecture numerology, transformer magic constants, magic numbers]
summary: "Lookup table of the magic constants in transformer design — FFN ratios, head dims, vocab padding, RoPE bases, Adam betas, divisibility rules — and the mechanical reason for each."
---

# Reference - Architecture Numerology

The recurring numeric constants copied config-to-config across transformer families, with the mechanical reason each one holds. Values marked *(as of 2026)* are lineage conventions, not laws.

## FFN expansion ratio

| Variant | Ratio | Effective params | Used by |
|---|---|---|---|
| Vanilla (ReLU/GELU MLP) | $d_\text{ff} = 4\,d_\text{model}$ | $8\,d_\text{model}^2$ (two projections) | GPT-2/3, BERT, original Transformer |
| Gated (SwiGLU/GeGLU) | $d_\text{ff} \approx \tfrac{8}{3}\,d_\text{model} \approx 2.67\times$ | $8\,d_\text{model}^2$ (three projections) | PaLM, Llama, most 2023+ LLMs |

The real invariant is **FFN params $\approx 8\,d_\text{model}^2$**, not "4×". Gated units have three weight matrices (gate, up, down) instead of two, so the width is cut to $\tfrac{8}{3}$ to keep the parameter count and FLOPs matched to the 4× baseline. Rounding: the $\tfrac{8}{3}$ result is then rounded to a hardware-friendly multiple (Llama-2-7B: $d_\text{ff}=11008$, a multiple of 256).

## Head dimension

| Constant | Typical value | Why |
|---|---|---|
| `head_dim` | 64 or 128 | MMA tile alignment[^mma] + softmax stability |
| relation | `head_dim × n_heads = d_model`[^gqa] | partition of the model width |

128 is favored at scale: [[Deep Dive - FlashAttention|FlashAttention]] and [[Concept - Tensor Cores|tensor cores]] want the head dim as a multiple of the matrix-multiply tile (8/16), and 128 balances kernel efficiency against the $1/\sqrt{d_h}$ softmax scaling — too-large $d_h$ inflates raw logit variance and feeds [[Concept - Attention Entropy Collapse|attention entropy collapse]].

[^mma]: MMA = the warp-level Matrix-Multiply-Accumulate instruction on NVIDIA tensor cores; its operand tiles are 8/16 wide, so dims that aren't multiples leave the systolic array partially idle.
[^gqa]: With GQA/MQA the key/value heads are fewer than query heads, so it is `head_dim × n_query_heads = d_model` with `n_kv_heads` separate.

## Vocabulary padding

| Constant | Value | Effect |
|---|---|---|
| Pad vocab to multiple of | 64 or 128 | embedding/unembedding GEMM tiles cleanly |
| Canonical example | GPT-2 $50257 \to 50304$ | measurable nanoGPT speedup, identical loss |

$50304 = 128 \times 393$. The extra rows are never-predicted padding tokens; the win is that the last tile of the $[\,d_\text{model} \times V\,]$ output projection is full instead of half-empty. Karpathy's nanoGPT documents this as free throughput.

## Aspect ratio (depth vs width)

| Constant | Heuristic target | Note |
|---|---|---|
| $d_\text{model} / n_\text{layers}$ | ~100–256 | Kaplan et al. 2020: weak dependence on shape at fixed params |

Most families sit in a narrow band. Too deep-and-thin is unstable to train (gradient/signal propagation); too wide-and-shallow underperforms at fixed budget. Shape is a second-order knob compared to total parameters and tokens — see [[Deep Dive - The Transformer|the transformer]] for the block structure this parameterizes.

## RoPE base θ

| Base θ | Regime | Model |
|---|---|---|
| 10000 | original / short context | GPT-NeoX, Llama 1–2 |
| 500000 | native long context | Llama 3 |
| $10^6+$ | extended long context | many long-context variants *(as of 2026)* |

Larger base pushes more [[Concept - Rotary Position Embeddings (RoPE)|RoPE]] dimensions to have wavelengths shorter than the target context, so they generalize instead of extrapolating out-of-distribution. It is the single most common context-extension knob — "just raise theta" — and the blunt alternative to [[Concept - RoPE Extrapolation and Context Extension|frequency-rescaling methods]] like YaRN.

## Optimizer folklore constants

| Constant | LLM value | Deviates from default because |
|---|---|---|
| Adam $\beta_1$ | 0.9 | (unchanged) |
| Adam $\beta_2$ | **0.95** | 0.999's second-moment memory (~1000 steps) is too long at LLM batch sizes; 0.95 (~20 steps) tracks faster |
| Adam $\varepsilon$ | 1e-8 (sometimes 1e-6) | copied lineage-to-lineage; placement (in/out of sqrt) matters and is rarely re-derived |
| Weight decay | 0.1 | decoupled ([[Concept - Adam and AdamW|AdamW]]); load-bearing for generalization |
| Gradient clip | 1.0 | caps loss-spike blast radius |
| Warmup | ~2000 steps, or 0.1–1% of total | stabilizes Adam's high-variance early second moment |
| z-loss coeff | ~1e-4 | keeps output logits from drifting; softmax normalization regularizer |

The betas are the tell: the framework default $(0.9, 0.999)$ is a vision/small-batch inheritance, and labs quietly switched $\beta_2$ to 0.95 for LLMs. This is documented folklore — see [[Lore - Hyperparameter Folklore]] for the war stories behind these numbers.

## Divisibility rules (silent-slowdown avoidance)

| Must divide | By | Failure if violated |
|---|---|---|
| $d_\text{model}$ | $n_\text{heads}$ | can't reshape into heads |
| $d_\text{model}$, $n_\text{heads}$ | tensor-parallel degree | uneven shard, padding or crash |
| $d_\text{ff}$, vocab | 128 (or 64) | ragged last GEMM tile, wasted tensor-core throughput |
| batch × seq | MMA tile | partial-tile launches, lower MFU |

The unifying rule: **align every dimension to a power-of-two-ish tile so the hardware's systolic array stays full.** A model that trains "mysteriously slow" often has one dimension off a tile boundary. The byte-level consequences of these choices are in [[Reference - Memory Math for Transformers|the memory-math reference]]; the soft-cap constants ($t\approx 50/30$) referenced above are detailed in the attention-stability note.

## Connections
- [[Reference - Memory Math for Transformers]] — the byte accounting that these divisibility and width constants feed into.
- [[Concept - Tensor Cores]] — the MMA tile sizes that make padding/divisibility matter at all.
- [[Deep Dive - The Transformer]] — the architecture whose dimensions these constants parameterize.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the base-θ construction the RoPE row scales.
- [[Concept - Adam and AdamW]] — the optimizer whose β/ε/weight-decay conventions are tabulated here.
- [[Concept - RoPE Extrapolation and Context Extension]] — why raising θ extends context, the mechanism behind the RoPE-base row.
- [[Deep Dive - FlashAttention]] — the kernel whose MMA-tile appetite dictates the head-dim and divisibility choices.
- [[Concept - Attention Entropy Collapse]] — why over-large head dims (raw logit variance) feed the entropy runaway the soft-cap constants guard against.
- [[Lore - Hyperparameter Folklore]] — the narrative behind why these specific numbers stuck.

## Sources
- Kaplan et al. (2020) — *Scaling Laws for Neural Language Models*. Weak dependence of loss on depth/width shape at fixed params.
- Shazeer (2020) — *GLU Variants Improve Transformer*. Source of the $\tfrac{8}{3}$ gated-FFN width convention.
- Karpathy — *nanoGPT*. The $50257\to50304$ vocab-padding speedup, documented in code.
- Su et al. (2021) — *RoFormer (RoPE)*. The base-θ frequency construction.
