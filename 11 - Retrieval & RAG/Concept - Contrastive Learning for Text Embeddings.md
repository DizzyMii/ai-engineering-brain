---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [InfoNCE, contrastive loss for embeddings]
summary: "The InfoNCE training objective that pulls matching query-document pairs together and pushes everything else apart, making cosine similarity a valid ranking signal."
---
> **One-paragraph hook:** A raw transformer encoder's output vectors aren't retrieval-ready. Nothing in masked-language-modeling pretraining makes "how do I cancel my subscription" land geometrically close to "terminating your plan." Contrastive learning is the training objective that fixes it: pull known matching pairs together and push everything else apart, until cosine distance in the resulting space means relevance. It's the mechanism behind every dual-encoder in [[Concept - Embedding Models]], and it's far more sensitive to batch size and negative quality than to architecture.

## The mechanism

The workhorse loss is **InfoNCE**, which is [[Concept - Entropy and Cross-Entropy|cross-entropy]] over a [[Concept - Softmax|softmax]] of similarities:

$$\mathcal{L} = -\log \frac{\exp(\text{sim}(q, d^+) / \tau)}{\sum_{i} \exp(\text{sim}(q, d_i) / \tau)}$$

Here $d^+$ is the one positive document for query $q$, the denominator sums over the positive plus every negative $d_i$ in the pool, and $\text{sim}$ is typically cosine similarity on L2-normalized vectors. Temperature $\tau$ (commonly 0.01–0.05) scales the logits before the softmax. Low $\tau$ sharpens the distribution and pushes harder for confident separation, at the risk of instability or representation collapse. High $\tau$ flattens it and leaves the model a weak, indecisive gradient.

**In-batch negatives** make this tractable at scale for free. In a batch of $B$ (query, document) pairs, each query's positive is its paired document and every *other* document in the batch is a negative, with no extra forward passes since they're already embedded. That's why embedding training uses batches far larger than typical fine-tuning, **1k to 32k+**. InfoNCE's denominator is a Monte Carlo estimate of the full-corpus softmax partition function, and the estimate's bias and variance improve directly with more negatives. Empirically, a bigger batch is a more reliable lever than a smarter loss or a bigger encoder.

Two engineering tricks make huge batches feasible. **Cross-device negative gathering** uses [[Concept - All-Reduce and Collective Operations|all-gather]] to collect embeddings from every GPU in the job, so the negative pool is per-device batch size times device count, and no device has to hold the whole batch in activation memory. **GradCache** decouples the memory-bound backward pass from the huge effective batch by recomputing and chunking gradients. You can train with an effective batch of tens of thousands even though no single forward-backward pass at that size would fit in GPU memory.

E5, BGE and GTE share a **two-stage recipe**. Stage one is large-scale weakly supervised contrastive pretraining on billions of naturally occurring pairs (title–body, forum question–answer, mined web pairs) to teach broad semantic alignment. Stage two is supervised fine-tuning on labeled retrieval datasets (MS MARCO, NLI) with curated [[Concept - Hard Negative Mining|hard negatives]] to sharpen task-specific discrimination. Stage one gets you a reasonable embedding space cheaply. Stage two makes it competitive for retrieval.

**Alignment and uniformity** (Wang & Isola, 2020) is the geometric view of what InfoNCE optimizes asymptotically. *Alignment*: positive pairs map to nearby points. *Uniformity*: embeddings spread evenly over the hypersphere instead of collapsing into a small region. The two pull against each other. Push uniformity too hard and related concepts drift apart; push alignment too hard and distinct concepts collapse together. $\tau$ is the implicit knob between them. A badly trained embedding space usually fails visibly on one of these two measurable axes, so they work as a practical diagnostic.

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

L2-normalization is required. $\tau$ is tuned assuming similarities live in $[-1, 1]$, so skipping normalization silently rescales the effective temperature and can destabilize training in ways that look like a $\tau$ bug. Production temperatures typically sit in the 0.01–0.05 band. Batch sizes scale with available multi-GPU capacity, and cross-device gathering is standard practice, not an optimization reserved for frontier labs. What comes out of this pipeline is the set of models in [[Concept - Embedding Models]]: E5, BGE, GTE and the decoder-based embedders all train on some variant of this objective. The same InfoNCE machinery applied across image and text encoders trains [[Concept - CLIP and Contrastive Vision-Language Training|CLIP]]. [[Concept - Matryoshka Representation Learning|Matryoshka Representation Learning]] extends the objective at training time by nesting the loss at several truncated dimensions, so one model produces embeddings usable at several sizes.

## Failure modes

- **Temperature miscalibration.** Too low collapses the loss toward degenerate solutions or destabilizes training with sharp gradients. Too high leaves embeddings under-separated, and retrieval quality plateaus low while training looks normal: the loss curve is fine, downstream recall isn't.
- **In-batch-negative plateau.** Once the model separates obviously unrelated pairs, in-batch negatives stop giving useful gradient. Most of the batch is trivially easy, loss keeps falling on the easy majority, and the hard cases that matter for real retrieval get no signal. [[Concept - Hard Negative Mining]] exists to solve this.
- **Anisotropic collapse.** Too little uniformity pressure (few effective negatives, or temperature too high) leaves the embedding space in a narrow cone instead of spread over the hypersphere, the geometric pathology described in [[Concept - Embedding Space Geometry]].
- **Silent normalization bugs.** Forgetting to L2-normalize before computing similarity throws no error. It changes the effective temperature and the calibration of every downstream similarity threshold.

## The non-obvious

The industry pours engineering into *making the batch bigger* (GradCache, cross-device all-gather, gradient checkpointing tuned for embedding training) and comparatively little into fancier losses. That follows from the math. InfoNCE's denominator samples a softmax over the entire corpus, and the sample's bias shrinks with sample size. A team that spends a month tuning $\tau$ and encoder architecture at batch size 256 will typically see less retrieval gain than a team that scales the same setup to batch size 8k.

Alignment/uniformity gives a second lesson. Since the two properties fight each other, "add more negatives" and "raise temperature" aren't independent knobs: moving one changes what the other effectively optimizes. Retuning $\tau$ after any batch-size change belongs to the same experiment.

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
