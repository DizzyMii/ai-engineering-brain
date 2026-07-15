---
tags: [concept, domain/retrieval-rag, level/frontier]
aliases: [MRL, Matryoshka embeddings, nested embeddings]
summary: "Training embeddings so every leading prefix of the vector is itself a valid embedding, giving one model many operating points on cost vs accuracy."
---
> **One-paragraph hook:** A standard [[Concept - Embedding Models|embedding model]] spreads meaning roughly evenly across all $d$ dimensions, so slicing off the last half of the vector to save memory produces garbage — you can't cheaply downgrade a 1024-dim embedding to 256 dims after the fact. Matryoshka Representation Learning trains the model differently: information is front-loaded so the *first* $m$ dimensions of the vector are themselves a usable, if slightly less accurate, embedding for any $m$ you choose. One model, trained once, gives you a dial between storage/latency and accuracy instead of a single fixed point — the nested-doll structure the name describes.

## The mechanism

Ordinary contrastive training (see [[Concept - Contrastive Learning for Text Embeddings]]) applies the loss once, to the full $d$-dimensional output vector. MRL (Kusupati et al. 2022) instead applies the *same* loss function simultaneously at a set of nested prefix lengths $\mathcal{M} = \{m_1, m_2, \dots, d\}$ — typically powers of two like $\{64, 128, 256, 512, 1024\}$ — and sums the losses:

$$
\mathcal{L}_{\text{MRL}} = \sum_{m \in \mathcal{M}} c_m \cdot \mathcal{L}\big(f(x)_{1:m},\ y\big)
$$

where $f(x)_{1:m}$ denotes truncating the embedding to its first $m$ coordinates before computing similarity, and $c_m$ are (often uniform) per-scale weights. For a retrieval embedder, $\mathcal{L}$ is the same InfoNCE contrastive objective used in ordinary training — it's just evaluated $|\mathcal{M}|$ times per batch, once per truncation length, and backpropagated jointly. Because the *first* $m$ coordinates are forced to work well as a standalone embedding for every $m$ in the training set — including the smallest — gradient pressure pushes the most discriminative information toward the low-index end of the vector, the same qualitative effect PCA gives you post-hoc on a *fixed* representation, except MRL learns it end-to-end as part of the representation itself rather than projecting after the fact.

The training cost overhead is small (a handful of extra loss terms per batch, no extra forward passes) but it is a deliberate training-time choice — you cannot retrofit MRL onto an already-trained model by fine-tuning on nested losses expecting the same graceful degradation a from-scratch MRL run gives you, because the ordinary model was never pushed to concentrate information at the front.

## In practice

**Adaptive retrieval** is the payoff pattern: do a cheap first pass with a heavily truncated embedding (say 64-256 dims) against a small, fast [[Concept - HNSW|HNSW]] or flat index to pull a shortlist of a few hundred to a thousand candidates, then re-embed (or look up cached full-dimension vectors for) that shortlist and rescore with the full $d$ dimensions for the final top-$k$. This mirrors the two-stage shortlist-then-rescore pattern used in IVFPQ and DiskANN, except the compression axis is *dimension count* rather than *quantization bits* — and the two compound (see below).

Truncation must be paired with L2-renormalization: slicing a vector to its first $m$ coordinates changes its norm, and cosine similarity computed on an un-renormalized truncated vector is subtly wrong even though nothing errors — always renormalize after truncating, before computing similarity.

Storage math makes the case concretely: OpenAI's text-embedding-3-large ships at 3072 dimensions natively but exposes a `dimensions` parameter (2024) that truncates down to as low as 256 with graceful degradation rather than collapse — a 12x reduction in per-vector storage ($3072/256$) for a real but small accuracy cost, and OpenAI reported the 256-dim truncation still outperformed their previous-generation ada-002 model running at its full, un-truncated 1536 dimensions. Nomic-embed, mixedbread's mxbai models, and Jina v3 are also trained with MRL and expose the same truncate-on-demand behavior; this is now close to a default expectation for a new embedding release rather than a novelty.

## Failure modes

- **Truncating a non-MRL model expecting graceful degradation**: slicing an ordinary embedder's output and hoping for the same behavior — information isn't front-loaded, so quality collapses far faster than the MRL curve suggests it should. Detect by sweeping recall@k across truncation levels on your eval set before assuming any embedder supports this.
- **Forgetting to renormalize post-truncation**: cosine similarity computed on a truncated-but-not-renormalized vector produces a plausible-looking but systematically wrong ranking, with no exception thrown — a genuinely silent bug. Detect by checking that truncated-vector norms are ~1.0 after your truncation code path runs.
- **Choosing a truncation dimension without an eval sweep**: the optimal cutoff is corpus- and query-dependent; a cutoff that looks fine on easy queries can regress specifically on hard, fine-grained queries where the extra dimensions carried the discriminating signal — a regression that a coarse aggregate metric can hide.
- **Stacking truncation and quantization blind**: MRL dimension truncation and int8/binary [[Concept - Embedding Quantization|quantization]] compound multiplicatively (e.g., 512-dim + int8 is roughly an 8x compression over full fp32), but each individually-tolerable error source can combine into a bigger-than-expected quality drop — evaluate the *combined* configuration you'll actually run in production, not each compression axis in isolation.

## The non-obvious

The thing that trips people up is treating MRL as "a smaller embedding model" when it's really "one model with an ordered basis." The practical implication: you don't need to decide your storage budget at training time or even at indexing time — the same stored 1024-dim vectors serve a cheap 64-dim shortlist pass *and* a full-precision rescore pass, because both are just different prefixes of the same number. That's a fundamentally different operational shape than choosing between "the small model" and "the big model" as separate artifacts to deploy, evaluate, and keep in sync — MRL collapses what used to be a model-selection decision into a runtime slicing decision, which is why it shows up as an API parameter (`dimensions=256`) rather than a separate model name.

## Connections
- [[Concept - Embedding Models]] — the down-link prerequisite: MRL is a training-time modification to the standard dual-encoder recipe, not a different architecture.
- [[Concept - Contrastive Learning for Text Embeddings]] — the base InfoNCE objective MRL applies at every nested prefix length simultaneously.
- [[Concept - Embedding Quantization]] — the up-link: MRL's dimension truncation compounds with bit-level quantization for multiplicative compression, and both feed the same shortlist-then-rescore serving pattern.
- [[Concept - Semantic Search]] — truncated embeddings still need correct cosine/dot-product handling; renormalization after truncation is the gotcha specific to this note.
- [[Concept - HNSW]] — the ANN index that benefits most directly from a smaller-dimension shortlist pass, trading index size and query latency for a rescore step.
- [[Reference - Vector Database Landscape]] — several production vector stores now expose MRL-aware truncation alongside their own quantization options.
- [[Concept - Embeddings as Learned Representations]] — the general representation-learning idea (Neural Networks domain) that MRL specializes with an explicit multi-scale training objective.
- [[Concept - Post-Training Quantization Formats]] — the inference-serving analog (Inference & Serving domain) of trading precision for cost that MRL applies along the dimension axis instead of the bit-width axis.

## Sources
- Kusupati et al. (2022) — Matryoshka Representation Learning. Introduces the nested-loss training objective and the adaptive-retrieval shortlist-then-rescore pattern.
- OpenAI (2024) — New embedding models and API updates (text-embedding-3 family). First major API-level exposure of MRL truncation via a `dimensions` parameter, with the ada-002-at-1536 comparison.
