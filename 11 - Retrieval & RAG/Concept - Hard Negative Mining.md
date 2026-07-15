---
tags: [concept, domain/retrieval-rag, level/advanced]
aliases: [ANCE mining, hard negatives]
summary: "Selecting semantically-close-but-wrong training negatives to sharpen retrieval embeddings — and the false-negative trap that silently ruins it."
---
> **One-paragraph hook:** [[Concept - Contrastive Learning for Text Embeddings|Contrastive training]] needs negatives, and random or in-batch negatives run out of useful gradient the moment a model gets decent — everything left is either obviously wrong or, worse, secretly right. Hard negative mining is the technique that finds documents close enough to fool the model, and its central trap is that "close enough to fool the model" and "actually relevant but unlabeled" are often the same document — mine too aggressively without guarding against that and you train the model to push real answers away from real questions.

## The mechanism

Random and in-batch negatives are cheap but self-limiting: once a model separates the obviously unrelated pairs (a tax-law query against a cat-adoption document), those pairs sit far apart in similarity space and contribute almost nothing to the InfoNCE gradient — the loss function's exponential weighting means the *hardest* (closest, most confusable) negatives dominate the signal, and random sampling from a large corpus rarely surfaces them. The model plateaus not because it's done learning, but because the negatives stopped being informative.

**Mining** fixes this directly: run the current retriever — [[Concept - BM25 and Lexical Retrieval|BM25]] as a cheap first pass, or the model's own current embeddings — over the training queries, and take the top-ranked documents that are *not* the labeled gold answer as candidate hard negatives. These are lexically or semantically close, plausible-looking, and wrong — exactly the signal in-batch negatives can't reliably provide. **ANCE** (Xiong et al., 2020 — Approximate Nearest Neighbor Negative Contrastive Estimation) pushes this further by asynchronously refreshing the mining index from the model's *own current checkpoint* during training rather than a fixed initial retriever, so negatives get harder in lockstep with the model — closing the gap between what the model sees during training and what actually confuses it at inference time.

The **false-negative catastrophe** is the mechanism's central failure, and it's structural, not incidental: datasets like MS MARCO label sparsely — typically one relevant document per query even though many other corpus documents are genuinely relevant too. A "hard negative" mined from the top of a BM25 or dense ranking is frequently an *unlabeled true positive*. Training then explicitly pushes a genuinely relevant document away from its query, poisoning the exact gradient direction the whole technique exists to sharpen. The symptom is counterintuitive and easy to misdiagnose: retrieval recall **plateaus or gets worse** as mining is made more aggressive, which looks backwards until you realize harder mining surfaces exactly the documents most likely to be unlabeled positives.

**Denoising** (RocketQA — Qu et al., 2021) addresses this two ways: sample candidate negatives from a rank window *below* the very top (e.g. ranks 30–100 rather than 1–10), since top-ranked-but-unlabeled documents are the ones most likely to be false negatives; and run a cross-encoder over the candidate pool to relabel or filter out documents it scores as actually relevant before they're used as training negatives.

The modern standard sidesteps the binary hard/negative decision entirely: use a [[Concept - Rerankers|cross-encoder]] teacher's continuous relevance score as a soft label for [[Concept - Knowledge Distillation|distillation]] into the bi-encoder student, rather than a hard positive/negative split. A mislabeled "negative" that the teacher scores as moderately relevant then contributes a small, calibrated loss instead of a maximal push-apart — this soft-labeling approach is behind most state-of-the-art embedders as of 2026.

Finally, **hardness curriculum** matters: feeding maximally hard negatives from the very start of training destabilizes an undertrained model (its similarity estimates aren't reliable enough yet to distinguish "hard-but-wrong" from "actually right"), so both the count of negatives per positive (commonly 4–32) and the rank window they're drawn from are typically scheduled or tuned rather than maximized immediately — the same [[Concept - Data Curriculum and Ordering|curriculum principle]] applied elsewhere in training pipelines, specialized here to negative difficulty instead of example difficulty.

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

Production embedding-training pipelines typically mix 4–32 mined hard negatives per positive with the standard in-batch negatives. BM25-mined negatives are a cheap stage-one source; model-mined (ANCE-style) negatives are harder and more expensive, since they require periodically re-indexing the corpus with the model's current weights. Cross-encoder relabeling adds a real cost — one extra forward pass per candidate — but is standard practice in the training recipes behind [[Concept - Embedding Models|E5, BGE, and GTE]]-lineage models, and the entire point of the exercise is a measurable jump in downstream [[Concept - Semantic Search]] recall over a model trained on in-batch negatives alone.

## Failure modes

- **Recall plateaus or regresses as mining gets harder**: the default instinct is "mine even harder," which makes false-negative contamination worse, not better — diagnose with a cross-encoder audit of a sample of mined negatives before concluding the model needs more difficulty.
- **Early-training instability**: maximally hard negatives fed to an undertrained model produce noisy, sometimes divergent gradients; fix with a curriculum that ramps hardness up over training rather than mining at full difficulty from step zero.
- **Stale mined negatives**: negatives mined once from an initial retriever and never refreshed stop being hard once the model outgrows them, silently reverting training to something closer to the in-batch-negative plateau it was meant to fix; fix with periodic (ANCE-style) re-mining.
- **Single-source mining blind spots**: mining only from BM25 misses the near-synonym, paraphrase-level confusions a dense retriever specifically struggles with, and vice versa; mixing lexical and dense-mined negatives covers both failure surfaces.
- **Geometric fallout from contamination**: false-negative-poisoned training doesn't just plateau a metric — it visibly distorts the resulting embedding space, showing up as the anisotropy and collapse pathologies catalogued in [[Concept - Embedding Space Geometry]]; a sudden shift in the similarity-score distribution of random pairs after a training run is a useful early tripwire.

## The non-obvious

The biggest practical risk in hard negative mining isn't picking negatives that are too easy — it's picking ones that are secretly right. When a team sees a recall regression after adding hard negatives, the natural response is to mine even harder, which is exactly backwards: harder mining surfaces documents ranked even closer to the query, which are *more* likely to be unlabeled true positives, not less. The fix is almost always denoising (rank-window sampling, cross-encoder relabeling), not more aggressive mining. Folklore, weakly sourced: several practitioners report that switching to cross-encoder-distilled soft labels makes explicit false-negative filtering largely unnecessary in practice, because a mislabeled "negative" that's actually relevant earns a moderate teacher score and contributes proportionate loss instead of the maximal binary push-apart a hard-label setup would apply — the soft label absorbs the labeling noise instead of amplifying it.

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
