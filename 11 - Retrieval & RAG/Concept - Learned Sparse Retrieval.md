---
tags: [concept, domain/retrieval-rag, level/frontier]
aliases: [SPLADE, neural sparse retrieval, learned sparse embeddings]
summary: "Neural models that emit sparse, vocabulary-indexed weight vectors, serving on ordinary inverted indexes while learning term expansion and semantics."
---
> **One-paragraph hook:** [[Concept - BM25 and Lexical Retrieval|BM25]] scales cheaply because it scores a sparse, vocabulary-sized representation on an inverted index, but its term weights are static statistics (IDF, term frequency) with no learned semantics. [[Concept - Semantic Search|Dense retrieval]] has learned semantics and pays for them with an opaque dense vector that needs an approximate-nearest-neighbor index and can't say per term *why* a document matched. Learned sparse retrieval, led by SPLADE, tries for both. A neural model still outputs a sparse, vocabulary-indexed vector, so it runs on the same proven inverted-index infrastructure as BM25, but its weights are learned end to end and include *term expansion*: relevant vocabulary the original text never used.

## The mechanism

SPLADE (Formal et al. 2021) keeps the BERT-style masked-language-model (MLM) head from pretraining and uses it to predict term importance. For each input position $i$, the MLM head produces logits $h_{ij}$ over the whole vocabulary $V$, i.e. which tokens *could* plausibly appear there. SPLADE takes the max across all positions in the document, then applies a log-saturating ReLU to keep values non-negative and bounded:

$$
w_j = \max_{i \in \{1,\dots,N\}} \log\big(1 + \text{ReLU}(h_{ij})\big), \qquad j \in V
$$

You get one vector $w \in \mathbb{R}^{|V|}$ per document (and per query), as long as the tokenizer vocabulary (~30k for BERT-style tokenizers), with most entries exactly zero. The nonzero entries cover the document's literal terms *and* related terms the MLM head predicts as plausible in context. This **term expansion** fixes vocabulary mismatch (a document about "myocardial infarction" gets weight on "heart attack") while the representation stays sparse enough to index.

Sparsity has to be enforced. An unregularized model would light up a large fraction of the vocabulary and lose the efficiency BM25-style indexing relies on. So SPLADE adds a **FLOPS regularizer**, an $L_1$-style relaxation of the *expected* number of floating-point operations a query against the index would cost:

$$
\mathcal{L}_{\text{FLOPS}} = \sum_{j \in V} \bar{w}_j^2, \qquad \bar{w}_j = \frac{1}{B}\sum_{i=1}^{B} w_j^{(i)}
$$

averaged over a training batch of size $B$. Its weight against the contrastive ranking loss directly sets the index-size-versus-effectiveness tradeoff. Turn it up and the model activates fewer terms (cheaper, closer to BM25). Turn it down and it activates more (better recall, heavier index).

## In practice

The output is sparse and vocabulary-indexed, so SPLADE runs on the same postings-list infrastructure as BM25 (Lucene, Anserini). Like BM25, it needs no [[Concept - HNSW|HNSW]] or other ANN structure. It inherits BM25's scaling to billions of documents and adds learned semantics on top. On out-of-domain [[Concept - BM25 and Lexical Retrieval|BEIR]] evaluation, learned sparse weights plus expansion consistently beat static IDF scoring. Against dense embedders, SPLADE avoids the out-of-domain collapse dense models suffer, and because every activated term has a name and a weight, you can inspect it: print the top-weighted terms for a query or document and see *why* something matched. A 1024-dimensional dense vector can't give you that.

The wider sparse-neural family includes DeepImpact and uniCOIL, which learn term weights without full expansion, and doc2query/docTTTTTquery, which generates plausible queries a document would answer, appends them to its text, and indexes the result with ordinary BM25. There, expansion is a preprocessing step instead of part of the scoring function. In hybrid pipelines (see [[Concept - Hybrid Search and Reciprocal Rank Fusion]]), SPLADE increasingly replaces or complements the lexical arm next to a dense arm. The argument is that SPLADE alone already captures much of what BM25-plus-dense fusion was after, with one index instead of two.

## Failure modes

- **Query latency creeps above BM25.** Expansion makes documents and queries activate more vocabulary terms than raw text, so postings lists get longer and per-query latency rises above plain BM25 on the identical index type. Budget for it; "sparse" doesn't mean "as fast as BM25."
- **Semantic drift from bad expansion.** The MLM head sometimes activates topically plausible but contextually wrong terms (expanding "python" the snake into programming-language terms, or the reverse), polluting the index with false-positive matches. Audit the top-activated expansion terms on a sample of documents. The inspectability that's normally SPLADE's advantage becomes your debugging tool.
- **Mistuned regularization.** Too much FLOPS penalty collapses the model toward near-BM25 behavior, which defeats the point of training it. Too little lets index size and query latency balloon toward dense territory while staying harder to serve than a proper ANN index. There's no universal FLOPS weight; sweep it against both effectiveness and measured index size on your corpus.
- **Training isn't free the way BM25 is.** BM25 needs no training data. SPLADE needs the same contrastive/distillation training setup as dense embedders (see [[Concept - Hard Negative Mining]]), and teams expecting a training-free upgrade over BM25 get surprised by the MLOps overhead.

## The non-obvious

The name "FLOPS regularizer" misleads if you read it as a training-efficiency trick. It has nothing to do with training cost. It's a proxy for *query-time* inverted-index cost: during training it penalizes activation patterns dense enough to make the resulting index expensive to query, before any query ever runs. So SPLADE's central move is optimizing a target serving cost directly in the loss function. That's a different engineering approach from making embeddings sparse and hoping they're fast, and different again from pruning a dense model into something sparse-ish after the fact.

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
