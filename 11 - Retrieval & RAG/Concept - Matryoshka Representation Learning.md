---
tags: [concept, domain/retrieval-rag, level/frontier]
aliases: [MRL, Matryoshka embeddings, nested embeddings]
summary: "Training embeddings so every leading prefix of the vector is itself a valid embedding, giving one model many operating points on cost vs accuracy."
---
> **One-paragraph hook:** A standard [[Concept - Embedding Models|embedding model]] spreads meaning roughly evenly across all $d$ dimensions, so slicing off the back half of the vector to save memory produces garbage. You can't cheaply downgrade a 1024-dim embedding to 256 dims after the fact. Matryoshka Representation Learning trains the model so information is front-loaded: the *first* $m$ dimensions are themselves a usable, slightly less accurate embedding for any $m$ you pick. One model, trained once, gives you a dial between storage/latency and accuracy in place of a single fixed point. Hence the nested-doll name.

## The mechanism

Ordinary contrastive training (see [[Concept - Contrastive Learning for Text Embeddings]]) applies the loss once, to the full $d$-dimensional output. MRL (Kusupati et al. 2022) applies the *same* loss at a set of nested prefix lengths $\mathcal{M} = \{m_1, m_2, \dots, d\}$, typically powers of two like $\{64, 128, 256, 512, 1024\}$, and sums the results:

$$
\mathcal{L}_{\text{MRL}} = \sum_{m \in \mathcal{M}} c_m \cdot \mathcal{L}\big(f(x)_{1:m},\ y\big)
$$

Here $f(x)_{1:m}$ means truncating the embedding to its first $m$ coordinates before computing similarity, and $c_m$ are (often uniform) per-scale weights. For a retrieval embedder, $\mathcal{L}$ is the usual InfoNCE contrastive objective, evaluated $|\mathcal{M}|$ times per batch (once per truncation length) and backpropagated jointly. The *first* $m$ coordinates have to work as a standalone embedding for every $m$ in the set, including the smallest, so gradient pressure pushes the most discriminative information toward the low-index end. PCA does something qualitatively similar post hoc on a *fixed* representation. MRL learns it end to end as part of the representation.

The training overhead is small (a few extra loss terms per batch, no extra forward passes), but you have to choose it at training time. Fine-tuning an already-trained model on nested losses won't give you the graceful degradation of a from-scratch MRL run, because the original model was never pushed to concentrate information at the front.

## In practice

**Adaptive retrieval** is where it pays off. Do a cheap first pass with a heavily truncated embedding (say 64-256 dims) against a small, fast [[Concept - HNSW|HNSW]] or flat index to pull a shortlist of a few hundred to a thousand candidates. Then re-embed that shortlist (or look up cached full-dimension vectors) and rescore with all $d$ dimensions for the final top-$k$. It's the shortlist-then-rescore pattern from IVFPQ and DiskANN, with *dimension count* as the compression axis in place of *quantization bits*, and the two compound (see below).

Always L2-renormalize after truncating. Slicing a vector to its first $m$ coordinates changes its norm, and cosine similarity on an un-renormalized truncated vector is subtly wrong while nothing errors.

The storage math makes the case. OpenAI's text-embedding-3-large ships at 3072 dimensions but exposes a `dimensions` parameter (2024) that truncates as low as 256 with graceful degradation, not collapse. That's a 12x cut in per-vector storage ($3072/256$) for a real but small accuracy cost, and OpenAI reported that the 256-dim truncation still beat their previous-generation ada-002 at its full 1536 dimensions. Nomic-embed, mixedbread's mxbai models and Jina v3 are also MRL-trained and support the same truncate-on-demand behavior. For a new embedding release it's now close to expected.

## Failure modes

- **Truncating a non-MRL model and expecting graceful degradation.** An ordinary embedder's information isn't front-loaded, so quality collapses far faster than the MRL curve would suggest. Sweep recall@k across truncation levels on your eval set before assuming any embedder supports this.
- **Forgetting to renormalize after truncation.** Cosine similarity on a truncated, un-renormalized vector gives a plausible but systematically wrong ranking and throws nothing, a silent bug. Check that truncated-vector norms are ~1.0 after your truncation code runs.
- **Picking a truncation dimension without an eval sweep.** The best cutoff depends on corpus and queries. One that looks fine on easy queries can regress on hard, fine-grained queries where the extra dimensions carried the discriminating signal, and a coarse aggregate metric can hide that.
- **Stacking truncation and quantization blind.** MRL truncation and int8/binary [[Concept - Embedding Quantization|quantization]] multiply (e.g., 512-dim + int8 is roughly 8x compression over full fp32), but two individually tolerable error sources can combine into a bigger quality drop than expected. Evaluate the *combined* configuration you'll run in production, not each axis alone.

## The non-obvious

People trip up by treating MRL as "a smaller embedding model." It's one model with an ordered basis. You don't have to fix your storage budget at training time or even at indexing time: the same stored 1024-dim vectors serve a cheap 64-dim shortlist pass *and* a full-precision rescore, because both are prefixes of the same numbers. Compare choosing between "the small model" and "the big model" as separate artifacts to deploy, evaluate and keep in sync. MRL turns that model-selection decision into a runtime slicing decision, which is why it ships as an API parameter (`dimensions=256`) instead of a separate model name.

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
