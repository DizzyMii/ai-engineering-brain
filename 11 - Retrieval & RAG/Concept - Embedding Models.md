---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [text embedders, dense retrievers, bi-encoders]
summary: "Dual-encoder transformers trained to map text into a vector space where retrieval relevance becomes geometric proximity."
---
> **One-paragraph hook:** Every [[Concept - Semantic Search]] system is only as good as the model that turns text into vectors. Embedding models are not general-purpose language models pressed into a new job — they're transformers specifically trained, via a contrastive objective, to place relevant query-document pairs close together and everything else far apart. Choosing one wrong (or using it wrong) is the single highest-leverage mistake in a retrieval stack, because it silently caps the recall ceiling every downstream component — reranker, prompt, generator — is fighting against.

## The mechanism

The standard architecture is a **dual encoder** (also called a bi-encoder): a transformer encoder processes the query and the document *independently*, each producing a sequence of token representations that gets **pooled** into a single fixed-size vector — mean pooling over all tokens, the `[CLS]` token for BERT-style encoders, or the last token's hidden state for decoder-based embedders — followed by L2 normalization. Crucially, the query and document never attend to each other; they're embedded separately and compared afterward by dot product or cosine, which is exactly what makes documents pre-computable and indexable offline. This is the structural opposite of a cross-encoder [[Concept - Rerankers|reranker]], which concatenates query and document into one forward pass so every token can attend to every other token — far more accurate, but requiring one forward pass per candidate, with nothing precomputable.

The vector's dimensionality $d$ is a direct cost knob: common sizes run 384 (MiniLM-class), 768, 1024, up through 1536 (OpenAI's `text-embedding-3-large`) and 4096 for decoder-LLM-based embedders. Storage cost is simply $N \times d \times 4$ bytes for $N$ vectors in fp32 — a corpus of 10M chunks at $d=1024$ is roughly 40 GB of raw vectors before any index overhead. Higher $d$ is not automatically better: it buys representational capacity but costs storage, index memory, and search latency linearly, and much of that capacity goes unused unless the model was actually trained to fill it (see [[Concept - Matryoshka Representation Learning]] for training objectives that make truncation graceful instead of destructive).

Most modern embedders require an **instruction or prefix format** at inference time that reflects how they were trained: E5 expects literal `"query: "` and `"passage: "` prefixes on the respective inputs, BGE uses natural-language instruction strings prepended to queries. This isn't cosmetic — it's asymmetric conditioning baked into training, and omitting it silently degrades recall with no error thrown, arguably the single most common production bug in retrieval stacks.

## In practice

The 2026 model landscape splits into a few lineages: **E5 / multilingual-E5** (Microsoft), **BGE and BGE-M3** (BAAI), **GTE** (Alibaba), **Nomic-embed** (open weights, 8k context — long relative to the 512-token limit of older BERT-based encoders), **Jina v3**, and the API-only options — OpenAI's `text-embedding-3-small/large`, Voyage, Cohere `embed v3`, Gemini embedding. The open-vs-API tradeoff is the usual one: API models need no GPU and get free upgrades, open models let you self-host, fine-tune, and avoid per-token cost at high query volume.

Model selection typically starts from **MTEB** (Massive Text Embedding Benchmark, Muennighoff et al. 2022), roughly 56 datasets spanning 7 task types (retrieval, classification, clustering, reranking, STS, and more) with a public leaderboard. The trap: MTEB rank is a noisy proxy for your task, and leaderboard overfitting is real — models get tuned against MTEB's specific datasets, so a top-10 MTEB rank does not reliably predict recall on your domain's jargon, document structure, or query style. Build your own eval set (see [[Concept - RAG Evaluation]]) before trusting a leaderboard position.

A distinct and growing lineage uses **decoder LLMs as embedders**: E5-mistral, gte-Qwen, and LLM2Vec (which retrofits bidirectional attention onto a causal decoder, then contrastively fine-tunes it). These models leverage far larger pretraining and often top MTEB, at the cost of being multi-billion-parameter models to serve for what a 100M-parameter BERT-class encoder used to do — a real latency and GPU-memory tax for marginal retrieval gains in many domains.

**Domain shift is the silent killer**: a general-purpose embedder trained on web text degrades on legal, medical, or code-heavy corpora, where jargon and identifiers it never saw in training get embedded into the wrong neighborhood. The fix is either in-domain contrastive fine-tuning (see [[Concept - Contrastive Learning for Text Embeddings]]) or reaching for a domain-specific model outright — `voyage-code`, `jina-code` for source code retrieval.

## Failure modes

- **Prefix/instruction omission**: halves recall with zero visible error; only caught by a deliberate A/B recall test comparing correctly-formatted vs raw input.
- **Domain jargon blind spot**: recall on in-domain rare terms (drug names, legal citations, function signatures) is much worse than aggregate MTEB-style benchmarks suggest, because those benchmarks skew toward general web-style text.
- **Dimension bloat without benefit**: reaching for the largest available embedding model "to be safe" inflates storage and search latency without a matched recall gain — dimension should be chosen against your eval set, not by reflex.
- **Serving cost surprise with decoder-based embedders**: swapping a 100M-parameter BERT-class encoder for a 7B-parameter LLM2Vec-style model multiplies embedding latency and GPU cost by 10-50x for indexing throughput, an easy budget miss if benchmarked only on accuracy.

## The non-obvious

MTEB leaderboard position is a marketing number more than an engineering one. Because the benchmark is public and static, model developers can and do tune training data mixtures toward MTEB's specific 56 datasets, producing leaderboard gains that don't transfer — the retrieval-equivalent of overfitting to a test set that everyone can see. The practitioners who get burned are the ones who pick a model by MTEB rank alone and only discover the domain-shift gap after shipping; the ones who don't get burned build a 50-100 query golden set from their own corpus in the first afternoon and re-run it against every embedder candidate before committing to one.

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
