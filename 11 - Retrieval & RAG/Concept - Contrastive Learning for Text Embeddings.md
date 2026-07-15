---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [InfoNCE, contrastive loss for embeddings]
summary: "The InfoNCE training objective that pulls matching query-document pairs together and pushes everything else apart, making cosine similarity a valid ranking signal."
---
> **One-paragraph hook:** A raw transformer encoder's output vectors are not retrieval-ready — nothing about masked-language-modeling pretraining guarantees that "how do I cancel my subscription" ends up geometrically close to "terminating your plan." Contrastive learning is the training objective that fixes this: pull known matching pairs together, push everything else apart, until cosine distance in the resulting space actually means relevance. It's the mechanism behind every dual-encoder in [[Concept - Embedding Models]], and it is far more sensitive to batch size and negative quality than to architecture choice.

## The mechanism

The workhorse loss is **InfoNCE**, framed as [[Concept - Entropy and Cross-Entropy|cross-entropy]] over a [[Concept - Softmax|softmax]] of similarities:

$$\mathcal{L} = -\log \frac{\exp(\text{sim}(q, d^+) / \tau)}{\sum_{i} \exp(\text{sim}(q, d_i) / \tau)}$$

where $d^+$ is the one positive document for query $q$, the sum in the denominator ranges over the positive plus every negative $d_i$ in the pool, and $\text{sim}$ is typically cosine similarity on L2-normalized vectors. Temperature $\tau$ (commonly 0.01–0.05) scales the logits before the softmax: low $\tau$ sharpens the distribution and pushes harder toward confident separation (at the risk of instability or representation collapse), high $\tau$ flattens it and leaves the model with a weak, indecisive gradient.

**In-batch negatives** are the free lunch that makes this tractable at scale: for a batch of $B$ (query, document) pairs, every query's own positive is its paired document, and every *other* document in the batch serves as a negative for free — no extra forward passes, since you already embedded them. This is why embedding training uses batch sizes far larger than typical fine-tuning — **1k to 32k+** — because InfoNCE's denominator is a Monte Carlo estimate of the full-corpus softmax partition function, and that estimate's quality (bias and variance) improves directly with more negatives. Bigger batch is, empirically, a more reliable lever than a smarter loss or a bigger encoder.

Two engineering tricks make huge batches feasible. **Cross-device negative gathering**: use [[Concept - All-Reduce and Collective Operations|all-gather]] to collect embeddings across every GPU in a training job, so the effective negative pool is per-device batch size times device count, without each device needing to hold the whole batch in activation memory. **GradCache**: decouples the memory-bound backward pass from the huge effective batch by recomputing/chunking gradients, letting you train with an effective batch of tens of thousands even though no single forward-backward pass at that size would fit in GPU memory.

The standard **two-stage recipe** behind E5, BGE, and GTE: stage one is large-scale weakly-supervised contrastive pretraining over billions of naturally occurring pairs (title–body pairs, forum question–answer pairs, mined web pairs) to teach broad semantic alignment; stage two is supervised fine-tuning on labeled retrieval datasets (MS MARCO, NLI) using curated [[Concept - Hard Negative Mining|hard negatives]] to sharpen task-specific discrimination. Stage one gets you a reasonable embedding space cheaply; stage two is what actually makes it retrieval-competitive.

**Alignment and uniformity** (Wang & Isola, 2020) is the geometric lens for what InfoNCE is asymptotically optimizing: *alignment* (positive pairs map to nearby points) and *uniformity* (embeddings spread evenly across the hypersphere rather than collapsing into a small region). The two properties are in tension — pushing uniformity too hard spreads apart even related concepts, pushing alignment too hard collapses distinct concepts together — and $\tau$ is the implicit knob balancing that tension. A poorly trained embedding space usually fails visibly on one of these two measurable axes, which makes alignment/uniformity a genuinely useful diagnostic rather than just theory.

```
Batch of B pairs -> similarity matrix (B x B)
        d1   d2   d3  ...  dB
   q1 [ .91  .12  .08 ...  .03 ]   <- diagonal is the positive
   q2 [ .10  .88  .15 ...  .07 ]
   q3 [ .06  .09  .93 ...  .11 ]
   ...
   softmax each row over the B columns (temperature tau) -> cross-entropy vs diagonal
```

## In practice

L2-normalization is not optional bookkeeping — because $\tau$ is tuned assuming similarities live in $[-1, 1]$, skipping normalization silently rescales the effective temperature and can destabilize training in ways that look like a $\tau$ bug. Typical production temperatures sit in the 0.01–0.05 band; batch sizes scale with available multi-GPU capacity, and cross-device gathering is standard practice rather than an optimization reserved for frontier labs. The output of this whole pipeline is exactly the embedding models cataloged in [[Concept - Embedding Models]] — E5, BGE, GTE, and the decoder-based embedders all train against some variant of this same objective. The identical InfoNCE machinery, applied across image and text encoders instead of within text, is what trains [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]]; and a training-time extension of the same objective — [[Concept - Matryoshka Representation Learning|Matryoshka Representation Learning]] — nests the loss at multiple truncated dimensions so a single model produces embeddings usable at several sizes.

## Failure modes

- **Temperature miscalibration**: too low collapses the loss toward degenerate trivial solutions or destabilizes training with sharp gradients; too high leaves embeddings insufficiently separated and retrieval quality plateaus low despite training running "normally" (loss curve looks fine, downstream recall doesn't).
- **In-batch-negative plateau**: once the model separates obviously unrelated pairs, in-batch negatives stop providing useful gradient — most of the batch is trivially easy, and loss keeps decreasing on the easy majority while the hard cases that matter for real retrieval get no signal. This is the exact problem [[Concept - Hard Negative Mining]] exists to solve.
- **Anisotropic collapse**: insufficient uniformity pressure (low effective negative count, or temperature too high) leaves the embedding space occupying a narrow cone rather than spreading across the hypersphere — the geometric pathology detailed in [[Concept - Embedding Space Geometry]].
- **Silent normalization bugs**: forgetting to L2-normalize before computing similarity doesn't error, it just quietly changes the effective temperature and the calibration of every downstream similarity threshold.

## The non-obvious

The industry's disproportionate engineering investment in *making the batch bigger* — GradCache, cross-device all-gather, gradient checkpointing tuned specifically for embedding training — rather than in fancier loss functions is not fashion, it's math: InfoNCE's denominator is a sampled approximation of a softmax over the entire corpus, and that approximation's bias shrinks directly with sample size. A team that spends a month tuning $\tau$ and encoder architecture while training at batch size 256 will typically get less retrieval-quality improvement than a team that just scales the same setup to batch size 8k. The second non-obvious point follows from alignment/uniformity: because the two properties actively fight each other, "add more negatives" and "increase temperature" are not independent knobs — pushing one changes what the other is effectively optimizing for, so retuning $\tau$ after any batch-size change is not optional, it's part of the same experiment.

## Connections

- [[Concept - Hard Negative Mining]] — the follow-on technique for once in-batch negatives stop providing useful gradient signal.
- [[Concept - Embedding Models]] — the production models this loss trains; the mechanism behind every dual-encoder in that landscape.
- [[Concept - CLIP and Contrastive Vision-Language Training]] — the same InfoNCE machinery applied across image and text modalities instead of within text.
- [[Concept - Softmax]] — InfoNCE is literally cross-entropy over a softmax of similarity scores; the numerical-stability concerns are shared.
- [[Concept - Embedding Space Geometry]] — the geometric pathologies (anisotropy, collapse) that result when this training goes wrong.
- [[Concept - Entropy and Cross-Entropy]] — the loss-function lineage InfoNCE is a direct application of.
- [[Concept - All-Reduce and Collective Operations]] — the collective operation that makes cross-device negative gathering possible at the batch sizes this objective wants.
- [[Concept - Matryoshka Representation Learning]] — a training-time extension layered on top of this same contrastive objective to make embedding prefixes independently useful.

## Sources

- van den Oord, Li & Vinyals (2018) — Representation Learning with Contrastive Predictive Coding. Introduced the InfoNCE loss.
- Wang & Isola (2020) — Understanding Contrastive Representation Learning through Alignment and Uniformity on the Hypersphere. The geometric framing of what contrastive training optimizes.
