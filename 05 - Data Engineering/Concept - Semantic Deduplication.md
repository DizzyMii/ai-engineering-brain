---
tags: [concept, domain/data-engineering, level/frontier]
aliases: [SemDeDup, D4]
summary: "Deduplicating by embedding-space meaning rather than lexical overlap - catching paraphrases and near-duplicates MinHash cannot see."
---

> **One-paragraph hook:** [[Concept - Deduplication at Scale]] catches documents that share surface text — near-identical strings, templated boilerplate, repeated spans. It is blind to two documents that say the same thing in different words: a paraphrase, a machine translation, a reformatted press release syndicated across a hundred news sites with every sentence reworded. Semantic deduplication closes that gap by comparing documents in embedding space instead of token space, and the headline result — SemDeDup removing roughly half a corpus with no quality loss — is one of the cleaner "less data, same quality" findings in the pretraining-data literature.

## The mechanism

**SemDeDup** (Abbas et al. 2023) works in three steps: embed every document with a pretrained encoder (see [[Concept - Embedding Models]]), cluster the embeddings with k-means, and within each cluster remove documents whose embedding is above a cosine-similarity threshold to a nearby point (a cluster centroid or nearest neighbor), keeping one representative from each tight semantic cluster. The clustering step is what makes this tractable at corpus scale — comparing every document to every other document directly would be quadratic, so k-means first partitions the corpus into semantically coherent buckets, and the expensive pairwise-similarity check only has to run *within* each bucket, the same locality trick that makes lexical near-dup search practical via LSH banding in [[Snippet - MinHash LSH Deduplication]].

**D4** (Tirumala et al. 2023) composes three passes rather than one: MinHash lexical dedup first (cheap, catches the obvious case), then SemDeDup (catches semantic redundancy MinHash misses), then a **diversify** step that prunes *dense* regions of the embedding space using self-supervised-learning prototypes — actively thinning over-represented topics rather than just removing exact redundancy. This targets two distinct problems at once: documents that are near-copies of each other, and documents that are merely over-represented as a *topic* even without being pairwise near-duplicates.

## In practice

SemDeDup applied to C4 removed roughly **50% of the corpus** with no loss — and in some evaluations a measurable gain — in downstream performance, along with faster convergence from training on the smaller, less redundant pool; a similar result held on LAION image data, suggesting the effect isn't specific to text. D4 trained faster and to a better final result than either the raw corpus or MinHash-only deduplication, because it removes redundancy that lexical dedup structurally cannot see and separately corrects for topic over-representation that dedup alone doesn't address. Semantic dedup sits on a broader spectrum of "which examples actually matter" techniques alongside perplexity- and loss-based data pruning and per-example memorization scoring — the frontier question isn't just "is this document a duplicate" but "does this document carry marginal training signal at all."

## Failure modes

The dominant cost is computational: semantic dedup requires a forward pass of an embedding model over the **entire corpus** — trillions of tokens — plus large-scale k-means clustering over the resulting vectors, which is dramatically more expensive than MinHash's hash-and-band approach. In practice this means semantic dedup is often run on a subsample of the corpus, or with a smaller/cheaper encoder than you'd use for a production retrieval system, trading embedding quality for throughput. A weaker encoder is also the direct cause of the main quality failure: if the encoder can't distinguish topically-similar-but-substantively-different documents, it merges them into the same cluster and over-prunes, quietly deleting content that a lexical dedup pass would have correctly kept. Detection is the same discipline used everywhere else in the pipeline — measure downstream eval impact on a held-out ablation, don't trust the dedup rate or clustering diagnostics as a proxy for quality.

## The non-obvious

The embedding model **is** the definition of "duplicate" here — there is no ground truth independent of the encoder's notion of similarity, unlike exact-hash dedup where "duplicate" is unambiguous. This means the similarity threshold has to be ablation-validated per corpus and per encoder choice, exactly the same lesson [[Breakdown - FineWeb and FineWeb-Edu]] learned the hard way about quality classifiers: a filter's internal confidence score is not evidence of its real-world effect, only a held-out downstream comparison is.

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
