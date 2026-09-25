---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [text embedders, dense retrievers, bi-encoders]
summary: "Dual-encoder transformers trained to map text into a vector space where retrieval relevance becomes geometric proximity."
---
> **One-paragraph hook:** Every [[Concept - Semantic Search]] system is only as good as the model that turns text into vectors. Embedding models aren't general-purpose language models pressed into a new job. They're transformers trained with a contrastive objective to put relevant query-document pairs close together and everything else far apart. Picking the wrong one, or using it wrong, is the costliest mistake in a retrieval stack, because it silently caps the recall every downstream component (reranker, prompt, generator) is fighting for.

## The mechanism

The standard architecture is a **dual encoder** (or bi-encoder). A transformer encoder processes the query and the document *independently*. Each produces a sequence of token representations that gets **pooled** into one fixed-size vector (mean pooling over all tokens, the `[CLS]` token for BERT-style encoders, or the last token's hidden state for decoder-based embedders), then L2-normalized. Query and document never attend to each other. They're embedded separately and compared afterward by dot product or cosine, which is what lets you precompute and index documents offline. A cross-encoder [[Concept - Rerankers|reranker]] is the opposite design: it concatenates query and document into one forward pass so every token attends to every other. It's far more accurate but needs one forward pass per candidate and nothing can be precomputed.

Dimensionality $d$ is a direct cost knob. Common sizes are 384 (MiniLM-class), 768, 1024, up to 1536 (OpenAI's `text-embedding-3-large`) and 4096 for decoder-LLM-based embedders. Storage is $N \times d \times 4$ bytes for $N$ vectors in fp32, so 10M chunks at $d=1024$ is roughly 40 GB of raw vectors before index overhead. Higher $d$ isn't automatically better. It buys representational capacity but costs storage, index memory and search latency linearly, and much of that capacity goes unused unless the model was trained to fill it ([[Concept - Matryoshka Representation Learning]] covers training objectives that make truncation graceful instead of destructive).

Most modern embedders need an **instruction or prefix format** at inference that matches how they were trained. E5 expects literal `"query: "` and `"passage: "` prefixes on the respective inputs; BGE prepends natural-language instruction strings to queries. This is asymmetric conditioning baked in during training. Leave it out and recall degrades silently with no error, arguably the most common production bug in retrieval stacks.

## In practice

The 2026 model field splits into a few lineages: **E5 / multilingual-E5** (Microsoft), **BGE and BGE-M3** (BAAI), **GTE** (Alibaba), **Nomic-embed** (open weights, 8k context, long next to the 512-token limit of older BERT-based encoders), **Jina v3**, and the API-only options: OpenAI's `text-embedding-3-small/large`, Voyage, Cohere `embed v3`, Gemini embedding. Open vs. API is the usual tradeoff. API models need no GPU and upgrade for free; open models let you self-host, fine-tune, and avoid per-token cost at high query volume.

Selection typically starts from **MTEB** (Massive Text Embedding Benchmark, Muennighoff et al. 2022): roughly 56 datasets over 7 task types (retrieval, classification, clustering, reranking, STS, and more) with a public leaderboard. The trap is that MTEB rank is a noisy proxy for your task, and leaderboard overfitting is real. Models get tuned against MTEB's specific datasets, so a top-10 rank doesn't reliably predict recall on your domain's jargon, document structure or query style. Build your own eval set (see [[Concept - RAG Evaluation]]) before trusting a leaderboard position.

A separate, growing lineage uses **decoder LLMs as embedders**: E5-mistral, gte-Qwen, and LLM2Vec (which retrofits bidirectional attention onto a causal decoder, then fine-tunes it contrastively). They draw on far larger pretraining and often top MTEB. The price is serving a multi-billion-parameter model for a job a 100M-parameter BERT-class encoder used to do, a real latency and GPU-memory tax for marginal retrieval gains in many domains.

**Domain shift is the silent killer.** A general-purpose embedder trained on web text degrades on legal, medical or code-heavy corpora, where jargon and identifiers it never saw get embedded into the wrong neighborhood. Fix it with in-domain contrastive fine-tuning (see [[Concept - Contrastive Learning for Text Embeddings]]) or use a domain-specific model outright, such as `voyage-code` or `jina-code` for source code retrieval.

## Failure modes

- **Prefix/instruction omission.** Halves recall with no visible error. Only a deliberate A/B recall test of correctly formatted vs. raw input catches it.
- **Domain jargon blind spot.** Recall on rare in-domain terms (drug names, legal citations, function signatures) is much worse than MTEB-style aggregates suggest, since those benchmarks skew toward general web text.
- **Dimension bloat without benefit.** Picking the largest embedding model "to be safe" inflates storage and search latency with no matching recall gain. Choose dimension against your eval set, not by reflex.
- **Serving cost surprise with decoder-based embedders.** Swapping a 100M-parameter BERT-class encoder for a 7B-parameter LLM2Vec-style model multiplies embedding latency and GPU cost by 10-50x for indexing throughput. Easy to miss in the budget if you only benchmarked accuracy.

## The non-obvious

MTEB leaderboard position is more a marketing number than an engineering one. The benchmark is public and static, so developers can and do tune training data mixtures toward its specific 56 datasets, and the gains don't transfer. It's overfitting to a test set everyone can see. The people who get burned pick a model by MTEB rank alone and discover the domain-shift gap after shipping. The ones who don't build a 50-100 query golden set from their own corpus on the first afternoon and run every embedder candidate against it before committing.

## Connections

- [[Concept - Contrastive Learning for Text Embeddings]] — the training objective that actually shapes the vector space this note describes using.
- [[Concept - Hard Negative Mining]] — the technique that determines how sharp/discriminative the trained embedding space becomes.
- [[Concept - Matryoshka Representation Learning]] — a training-time trick that makes the dimension-vs-cost tradeoff gradual instead of all-or-nothing.
- [[Concept - Semantic Search]] — the downstream mechanism these vectors are searched with; this note's prerequisite.
- [[Concept - CLIP and Contrastive Vision-Language Training]] — the same dual-encoder contrastive recipe applied to image-text pairs instead of text-text.
- [[Concept - Rerankers]] — the cross-encoder counterpart that trades precomputability for far higher per-pair accuracy.
- [[Reference - Vector Database Landscape]] — where these vectors get stored and searched at scale.
- [[Concept - Softmax]] — the contrastive loss embedding models train against is a softmax over similarities, underneath the hood.
- [[Concept - RAG Evaluation]] — the only reliable way to check whether an MTEB-leading model actually recalls well on your corpus.

## Sources

- Muennighoff et al. (2022) — MTEB: Massive Text Embedding Benchmark. The de facto standard benchmark suite and leaderboard for comparing embedding models across task types.
- Wang et al. (2022) — Text Embeddings by Weakly-Supervised Contrastive Pre-training. Introduces the E5 family and the query:/passage: prefix convention widely copied since.
