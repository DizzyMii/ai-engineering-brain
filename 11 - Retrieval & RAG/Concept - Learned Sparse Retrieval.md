---
tags: [concept, domain/retrieval-rag, level/frontier]
aliases: [SPLADE, neural sparse retrieval, learned sparse embeddings]
summary: "Neural models that emit sparse, vocabulary-indexed weight vectors, serving on ordinary inverted indexes while learning term expansion and semantics."
---
> **One-paragraph hook:** [[Concept - BM25 and Lexical Retrieval|BM25]] scales cheaply because it scores over a sparse, vocabulary-sized representation on an inverted index — but its term weights are static statistics (IDF, term frequency) with no learned semantics. [[Concept - Semantic Search|Dense retrieval]] has learned semantics but pays for it with an opaque, dense vector that needs an approximate-nearest-neighbor index and offers no per-term explanation of *why* a document matched. Learned sparse retrieval, led by SPLADE, tries to have both: a neural model that still outputs a sparse, vocabulary-indexed vector — so it serves on the same battle-tested inverted-index infrastructure as BM25 — but whose weights are learned end-to-end and include *term expansion*, adding relevant vocabulary the original text never used.

## The mechanism

SPLADE (Formal et al. 2021) reuses a BERT-style masked-language-model (MLM) head — the same head used for masked-token pretraining — as a term-importance predictor instead of discarding it after pretraining. For each input token position $i$, the MLM head produces a distribution of logits $h_{ij}$ over the entire vocabulary $V$ (what token *could* plausibly appear there). SPLADE aggregates across all token positions in the document with a max, then squashes with a log-saturating ReLU to keep values non-negative and bounded:

$$
w_j = \max_{i \in \{1,\dots,N\}} \log\big(1 + \text{ReLU}(h_{ij})\big), \qquad j \in V
$$

The result is one vector $w \in \mathbb{R}^{|V|}$ per document (and per query), the size of the entire tokenizer vocabulary (~30k for BERT-style tokenizers), where most entries are exactly zero. Nonzero entries include both the document's literal terms *and* semantically related terms the MLM head predicts as plausible in context — this is the **term expansion** that fixes vocabulary mismatch (a document about "myocardial infarction" gets nonzero weight on "heart attack") while the representation stays sparse enough to index.

Sparsity is not free — an unregularized model would activate a large fraction of the vocabulary and lose the efficiency BM25-style indexing depends on — so SPLADE adds a **FLOPS regularizer**, an $L_1$-style relaxation on the *expected* number of floating-point operations a query against this index would cost:

$$
\mathcal{L}_{\text{FLOPS}} = \sum_{j \in V} \bar{w}_j^2, \qquad \bar{w}_j = \frac{1}{B}\sum_{i=1}^{B} w_j^{(i)}
$$

averaged over a training batch of size $B$. Its weight relative to the contrastive ranking loss is a direct dial on the index-size-versus-effectiveness tradeoff: crank it up and the model activates fewer terms (cheaper, more BM25-like); crank it down and it activates more (better recall, heavier index).

## In practice

Because the output vector is sparse and vocabulary-indexed, SPLADE serves on the same postings-list inverted-index infrastructure as BM25 — Lucene, Anserini — rather than requiring [[Concept - HNSW|HNSW]] or another ANN structure, so it inherits BM25's scaling story to billions of documents while adding learned semantics on top. Compared to BM25 on out-of-domain [[Concept - BM25 and Lexical Retrieval|BEIR]] evaluation, learned sparse weights plus expansion consistently beat static IDF-based scoring; compared to dense embedders, SPLADE avoids the domain-shift collapse dense models suffer out-of-domain and, because every activated term has a name and a weight, it's directly inspectable — you can print the top-weighted terms for a query or document and see *why* something matched, something a 1024-dimensional dense vector cannot offer.

The broader sparse-neural family includes DeepImpact and uniCOIL (learn term weights without full expansion) and doc2query/docTTTTTquery (generate plausible queries the document would answer, append them to the document text, then index the expanded text with ordinary BM25 — expansion as a preprocessing step rather than baked into the scoring function). In hybrid pipelines (see [[Concept - Hybrid Search and Reciprocal Rank Fusion]]), SPLADE is increasingly used as a drop-in replacement for, or complement to, the lexical arm alongside a dense arm — the argument being that SPLADE alone already captures much of what BM25-plus-dense-fusion was trying to buy, at one index instead of two.

## Failure modes

- **Query-time latency creep versus BM25**: term expansion means both documents and queries activate more vocabulary terms than raw text would, so postings lists get longer and per-query latency rises above plain BM25 even though the index type is identical — budget for this rather than assuming "sparse means as fast as BM25."
- **Semantic drift from bad expansion**: the MLM head occasionally activates topically plausible but contextually wrong terms (expanding "python" the snake into programming-language terms, or vice versa), polluting the index with false-positive matches; detect via manual audits of top-activated expansion terms on a sample of documents, the same inspectability that's normally SPLADE's advantage becomes the debugging tool.
- **Regularization mistuned**: too much FLOPS penalty collapses the model toward near-BM25 behavior (defeating the point of training it at all); too little makes index size and query latency balloon toward dense-embedding territory while still being harder to serve than a proper ANN index. There's no universal FLOPS weight — it has to be swept against both effectiveness and measured index size on your corpus.
- **Training is not free like BM25**: unlike BM25, which needs zero training data, SPLADE needs the same contrastive/distillation training infrastructure as dense embedders (see [[Concept - Hard Negative Mining]]) — teams expecting a training-free upgrade over BM25 are surprised by the MLOps overhead.

## The non-obvious

The FLOPS regularizer's name is misleading if you think of it as a training-efficiency trick — it has nothing to do with how expensive training is. It's a proxy for *query-time* inverted-index cost, penalizing the model during training for producing the kind of dense-ish activation pattern that would make the resulting index expensive to query, long before any query is ever run against it. That reframes SPLADE's central design decision: it isn't "make embeddings sparse and hope it's fast," it's "directly optimize for a target serving cost as part of the loss function," which is a fundamentally different engineering move than post-hoc pruning a dense model down to something sparse-ish.

## Connections
- [[Concept - BM25 and Lexical Retrieval]] — the down-link prerequisite: SPLADE serves on the same inverted-index infrastructure and directly targets BM25's static-weight limitation.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — SPLADE increasingly substitutes for or complements the lexical arm in hybrid pipelines.
- [[Concept - Semantic Search]] — the dense alternative SPLADE trades interpretability and index-type simplicity against, at some query-latency cost.
- [[Concept - Late Interaction and ColBERT]] — another middle-ground architecture between pure lexical and pure dense, using token-level MaxSim instead of vocabulary-sparse weighting.
- [[Concept - Embedding Models]] — the dual-encoder training machinery (contrastive loss, hard negatives) SPLADE reuses despite its very different output representation.
- [[Reference - Vector Database Landscape]] — most vector databases now support SPLADE-style sparse vectors alongside dense ones for hybrid serving.
- [[Concept - Sparse Autoencoders]] — the same $L_1$-style sparsity-inducing regularization principle over an overcomplete basis, applied to interpretability instead of retrieval (Safety & Interpretability domain).
- [[Concept - Activation Functions]] — the log-saturating ReLU nonlinearity that turns raw MLM logits into bounded, sparsity-friendly term weights (Neural Networks domain).
- [[Concept - Embedding Space Geometry]] — the up-link: SPLADE's sparse, per-term-inspectable representation sidesteps the anisotropy and hubness pathologies that silently degrade dense embedding spaces.

## Sources
- Formal et al. (2021) — SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking. Introduces the MLM-head-as-term-weighter architecture and the FLOPS regularizer.
- Nogueira & Lin (2019, docTTTTTquery lineage) — document expansion by query prediction, the preprocessing-based alternative to end-to-end learned sparse weighting.
