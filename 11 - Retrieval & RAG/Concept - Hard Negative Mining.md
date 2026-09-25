---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [ANCE mining, hard negatives]
summary: "Selecting semantically-close-but-wrong training negatives to sharpen retrieval embeddings — and the false-negative trap that silently ruins it."
---
> **One-paragraph hook:** [[Concept - Contrastive Learning for Text Embeddings|Contrastive training]] needs negatives, and random or in-batch negatives stop giving useful gradient once a model gets decent. What's left is either obviously wrong or, worse, secretly right. Hard negative mining finds documents close enough to fool the model. Its central trap is that "close enough to fool the model" and "actually relevant but unlabeled" are often the same document. Mine too aggressively without guarding against that and you train the model to push real answers away from real questions.

## The mechanism

Random and in-batch negatives are cheap but run out. Once a model separates obviously unrelated pairs (a tax-law query against a cat-adoption document), those pairs sit far apart and add almost nothing to the InfoNCE gradient. The loss's exponential weighting means the *hardest* negatives, the closest and most confusable, dominate the signal, and random sampling from a large corpus rarely turns them up. The model plateaus because the negatives stopped being informative, with plenty left to learn.

**Mining** fixes this. Run the current retriever over the training queries, either [[Concept - BM25 and Lexical Retrieval|BM25]] as a cheap first pass or the model's own current embeddings, and take the top-ranked documents that *aren't* the labeled gold answer as candidate hard negatives. They're lexically or semantically close, plausible, and wrong, which is the signal in-batch negatives can't reliably supply. **ANCE** (Xiong et al., 2020, Approximate Nearest Neighbor Negative Contrastive Estimation) goes further. It refreshes the mining index asynchronously from the model's *own current checkpoint* during training instead of a fixed initial retriever, so negatives get harder as the model does, and what it trains on tracks what confuses it at inference.

The **false-negative catastrophe** is built into the method. Datasets like MS MARCO label sparsely: typically one relevant document per query, though many other documents in the corpus are relevant too. A "hard negative" from the top of a BM25 or dense ranking is often an *unlabeled true positive*. Training then pushes a relevant document away from its query, poisoning the very gradient the technique is supposed to sharpen. The symptom is counterintuitive and easy to misdiagnose. Recall **plateaus or gets worse** as mining gets more aggressive, which seems backwards until you see that harder mining surfaces the documents most likely to be unlabeled positives.

**Denoising** (RocketQA, Qu et al., 2021) attacks this two ways. Sample candidate negatives from a rank window *below* the very top (e.g. ranks 30–100, not 1–10), since top-ranked unlabeled documents are the likeliest false negatives. And run a cross-encoder over the candidate pool to relabel or drop anything it scores as relevant before it's used as a negative.

The modern standard skips the binary hard/negative call. A [[Concept - Rerankers|cross-encoder]] teacher's continuous relevance score becomes a soft label for [[Concept - Knowledge Distillation|distillation]] into the bi-encoder student. A mislabeled "negative" the teacher scores as moderately relevant then contributes a small, calibrated loss instead of a maximal push-apart. Most state-of-the-art embedders use this soft-labeling approach as of 2026.

**Hardness curriculum** matters too. Maximally hard negatives from the first step destabilize an undertrained model, whose similarity estimates can't yet tell "hard but wrong" from "actually right." So the number of negatives per positive (commonly 4–32) and the rank window they come from are usually scheduled or tuned, not maxed out immediately. It's the [[Concept - Data Curriculum and Ordering|curriculum principle]] from other training pipelines, applied to negative difficulty instead of example difficulty.

```
query -> BM25/dense retrieve top-K -> exclude labeled gold -> candidate negatives
                                            |
                          sample from rank window (e.g. 30-100, not 1-10)
                                            |
                          cross-encoder relabel/filter false negatives
                                            |
                          remaining negatives -> InfoNCE training batch
```

## In practice

Production embedding-training pipelines typically mix 4–32 mined hard negatives per positive with the standard in-batch negatives. BM25-mined negatives are a cheap stage-one source. Model-mined (ANCE-style) negatives are harder and cost more, because the corpus has to be re-indexed periodically with the model's current weights. Cross-encoder relabeling adds a real cost, one extra forward pass per candidate, but it's standard in the training recipes behind [[Concept - Embedding Models|E5, BGE, and GTE]]-lineage models. The payoff is a measurable jump in downstream [[Concept - Semantic Search]] recall over a model trained on in-batch negatives alone.

## Failure modes

- **Recall plateaus or regresses as mining gets harder.** The instinct is to mine harder still, which makes false-negative contamination worse. Audit a sample of mined negatives with a cross-encoder before deciding the model needs more difficulty.
- **Early-training instability.** Maximally hard negatives fed to an undertrained model give noisy, sometimes divergent gradients. Ramp hardness up over training with a curriculum; don't mine at full difficulty from step zero.
- **Stale mined negatives.** Negatives mined once from an initial retriever stop being hard once the model outgrows them, and training slides back toward the in-batch plateau it was meant to escape. Re-mine periodically (ANCE-style).
- **Single-source blind spots.** Mining only from BM25 misses the near-synonym and paraphrase confusions a dense retriever struggles with, and the reverse holds too. Mixing lexical and dense-mined negatives covers both.
- **Geometric fallout from contamination.** Training poisoned by false negatives does more than stall a metric. It visibly distorts the embedding space, producing the anisotropy and collapse pathologies in [[Concept - Embedding Space Geometry]]. A sudden shift in the random-pair similarity distribution after a training run is a useful early tripwire.

## The non-obvious

The biggest practical risk is picking negatives that are secretly right, more than picking ones that are too easy. When recall regresses after adding hard negatives, the natural response is to mine harder, which is backwards: harder mining surfaces documents ranked even closer to the query, and those are *more* likely to be unlabeled true positives. The fix is almost always denoising (rank-window sampling, cross-encoder relabeling). Folklore, weakly sourced: several practitioners report that switching to cross-encoder-distilled soft labels makes explicit false-negative filtering largely unnecessary in practice. A mislabeled "negative" that's actually relevant earns a moderate teacher score and a proportionate loss, where a hard-label setup would apply the maximal binary push-apart. The soft label absorbs the labeling noise instead of amplifying it.

## Connections

- [[Concept - Contrastive Learning for Text Embeddings]] — the loss this mining strategy feeds; hard negatives are the raw material for a non-trivial InfoNCE denominator.
- [[Concept - Embedding Models]] — the production embedding models whose training recipes depend on exactly this technique.
- [[Concept - Rerankers]] — the cross-encoder used both as the false-negative filter and as the distillation teacher for soft-labeled mining.
- [[Concept - BM25 and Lexical Retrieval]] — the cheap, standard first-pass source of candidate hard negatives.
- [[Concept - Knowledge Distillation]] — the general technique that cross-encoder-to-bi-encoder soft labeling is a specific instance of.
- [[Concept - Semantic Search]] — the retrieval quality this training technique ultimately exists to improve.
- [[Concept - Data Curriculum and Ordering]] — the general principle behind scheduling negative hardness rather than maximizing it from step zero.
- [[Concept - Embedding Space Geometry]] — false-negative-poisoned training shows up visibly as geometric pathology in the resulting embedding space.

## Sources

- Xiong et al. (2020) — Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval (ANCE). Introduced model-refreshed asynchronous hard negative mining.
- Qu et al. (2021) — RocketQA: An Optimized Training Approach to Dense Passage Retrieval for Open-Domain Question Answering. The rank-window sampling and cross-encoder denoising recipe.
