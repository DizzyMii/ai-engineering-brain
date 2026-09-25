---
tags: [concept, domain/data-engineering, level/frontier]
aliases: [SemDeDup, D4]
summary: "Deduplicating by embedding-space meaning rather than lexical overlap - catching paraphrases and near-duplicates MinHash cannot see."
---

> **One-paragraph hook:** [[Concept - Deduplication at Scale]] catches documents that share surface text: near-identical strings, templated boilerplate, repeated spans. It can't see two documents that say the same thing in different words, like a paraphrase, a machine translation, or a press release syndicated across a hundred news sites with every sentence reworded. Semantic deduplication compares documents in embedding space instead of token space to close that gap. The headline result, SemDeDup removing roughly half a corpus with no quality loss, is one of the cleaner "less data, same quality" findings in the pretraining-data literature.

## The mechanism

**SemDeDup** (Abbas et al. 2023) has three steps. Embed every document with a pretrained encoder (see [[Concept - Embedding Models]]). Cluster the embeddings with k-means. Within each cluster, remove documents whose embedding is above a cosine-similarity threshold to a nearby point (a cluster centroid or nearest neighbor), keeping one representative from each tight semantic cluster. Clustering is what makes this tractable at corpus scale. Comparing every document to every other would be quadratic, so k-means first partitions the corpus into semantically coherent buckets and the expensive pairwise check runs only *within* each bucket. Lexical near-dup search uses the same locality trick via LSH banding in [[Snippet - MinHash LSH Deduplication]].

**D4** (Tirumala et al. 2023) composes three passes. MinHash lexical dedup goes first (cheap, catches the obvious case), then SemDeDup (catches semantic redundancy MinHash misses), then a **diversify** step that prunes *dense* regions of the embedding space using self-supervised-learning prototypes, thinning over-represented topics on top of removing exact redundancy. That targets two separate problems: documents that are near-copies of each other, and documents that are over-represented as a *topic* without being pairwise near-duplicates.

## In practice

On C4, SemDeDup removed roughly **50% of the corpus** with no loss in downstream performance (a measurable gain in some evaluations) and faster convergence from training on the smaller, less redundant pool. A similar result held on LAION image data, which suggests the effect isn't text-specific. D4 trained faster and to a better final result than either the raw corpus or MinHash-only dedup. It removes redundancy lexical dedup can't see, and it separately corrects topic over-representation that dedup alone doesn't touch. Semantic dedup belongs to a broader family of "which examples actually matter" techniques, alongside perplexity- and loss-based data pruning and per-example memorization scoring. At the frontier the question has moved from "is this document a duplicate" to "does this document carry marginal training signal at all."

## Failure modes

The dominant cost is compute. Semantic dedup needs a forward pass of an embedding model over the **entire corpus** (trillions of tokens) plus large-scale k-means over the resulting vectors, which is dramatically more expensive than MinHash's hash-and-band approach. So in practice it's often run on a subsample of the corpus, or with a smaller, cheaper encoder than a production retrieval system would use, trading embedding quality for throughput. That weaker encoder directly causes the main quality failure. If it can't tell topically-similar-but-substantively-different documents apart, it merges them into one cluster and over-prunes, silently deleting content a lexical dedup pass would have kept. Detection works the same as everywhere else in the pipeline: measure downstream eval impact on a held-out ablation. Don't trust the dedup rate or clustering diagnostics as a proxy for quality.

## The non-obvious

Here the embedding model **is** the definition of "duplicate." With exact-hash dedup, "duplicate" is unambiguous; with semantic dedup there's no ground truth independent of the encoder's notion of similarity. The similarity threshold therefore has to be ablation-validated per corpus and per encoder. [[Breakdown - FineWeb and FineWeb-Edu]] learned the same lesson the hard way about quality classifiers: a filter's internal confidence score isn't evidence of its real-world effect. Only a held-out downstream comparison is.

## Connections
- [[Concept - Deduplication at Scale]] — the lexical/exact-match sibling this note extends; semantic dedup catches what MinHash structurally cannot.
- [[Concept - Embedding Models]] — supplies the vector representations SemDeDup clusters and thresholds on; encoder quality directly bounds dedup quality.
- [[Snippet - MinHash LSH Deduplication]] — the same locality-partitioning trick (bucket first, compare within-bucket) that makes both MinHash-LSH and SemDeDup's clustering step tractable at scale.
- [[Concept - Quality Filtering for Pretraining Data]] — a parallel filtering stage; both share the failure mode of a proxy score not matching real downstream impact.
- [[Concept - Data Curriculum and Ordering]] — semantic dedup interacts with repetition budgets: pruning near-duplicates changes how much genuinely-distinct content is available to repeat.
- [[Deep Dive - The Pretraining Data Pipeline]] — where a semantic dedup pass would sit relative to lexical dedup, filtering, and decontamination in the full stage graph.
- [[Concept - Clustering and Dimensionality Reduction]] — the k-means machinery both SemDeDup and D4's diversify step depend on.
- [[Concept - HNSW]] — an alternative approximate-nearest-neighbor structure for the same "find similar embeddings at scale" problem, used in retrieval rather than corpus curation.
- [[Gotchas - Pretraining Data Pipelines]] — the operational lesson that a dedup method's internal metric (dup rate, cluster tightness) is not a substitute for measuring actual downstream effect.

## Sources
- Abbas et al. (2023) — SemDeDup: Data-efficient learning at web-scale through semantic deduplication. Introduced the embed-cluster-threshold pipeline and the ~50%-removal-with-no-loss result on C4 and LAION.
- Tirumala et al. (2023) — D4: Improving LLM Pretraining via Document De-Duplication and Diversification. Combined lexical dedup, semantic dedup, and an explicit diversify step to outperform either alone.
