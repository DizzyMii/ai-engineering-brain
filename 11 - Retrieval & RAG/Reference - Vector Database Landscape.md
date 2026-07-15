---
tags: [reference, domain/retrieval-rag, level/core]
aliases: [vector DB comparison, vector store comparison, vector database matrix]
summary: "Comparison matrix of production vector search systems by index type, filtering strategy, hybrid support, and hosting model, as of 2026."
---
*(as of 2026 — this table churns yearly; re-verify index support and quantization options before a production commitment. Filtering strategy, not raw ANN speed, is the column that actually decides most real deployments.)*

## System matrix

| System | Index types | Hosting | Filtering strategy | Hybrid (BM25 + dense) | Quantization | Scale ceiling¹ | Cost model |
|---|---|---|---|---|---|---|---|
| pgvector | HNSW, IVFFlat | Self-host / any Postgres | SQL-native (WHERE clauses via standard Postgres planner) | No native fusion; roll your own | halfvec, bit (binary) | ~10M vectors | Postgres compute + storage you already pay for |
| Qdrant | Filterable HNSW | Self-host or SaaS | Payload indexing built into the graph — the strongest filtering story of the group | Native (dense + sparse vectors, RRF) | Scalar (int8), binary, product | Billion-scale (sharded) | Self-host infra or managed-cluster pricing |
| Weaviate | HNSW | Self-host or SaaS | Pre-filter with graph-aware traversal | Native (BM25 + dense, RRF or relativeScore fusion) | PQ, binary (BQ) | Billion-scale (sharded) | Self-host infra or managed-cluster pricing |
| Milvus / Zilliz | IVF, HNSW, DiskANN, GPU (CAGRA) | Self-host (Milvus) or SaaS (Zilliz Cloud) | Post-filter with scalar field indexing; segment-scoped | Native (BM25 sparse + dense, RRF) | Scalar, PQ, binary | Billion-scale, GPU-accelerated | Self-host infra or managed-cluster pricing |
| Pinecone | Proprietary (undisclosed) | SaaS only, serverless | Metadata filtering, single-stage | Native (sparse-dense hybrid indexes) | Managed internally | Billion-scale (serverless) | Per-query + storage, fully managed |
| Vespa | HNSW + custom tensor indexes | Self-host or SaaS | Deep — ranking expressions can combine filters, text, and vector scores in one pass | Native, mature (tensor + text engine) | Scalar, binary | Billion-scale | Self-host infra or managed-cluster pricing |
| Elasticsearch / OpenSearch | Lucene HNSW | Self-host or SaaS | Mature — same filtering as any Lucene query | Native via RRF (BM25 is native Lucene) | Scalar (int8) | Billion-scale (sharded) | Self-host infra or managed-cluster pricing |
| Redis (RediSearch) | HNSW, FLAT | Self-host or SaaS | Secondary-index filtering | Native (BM25 module + vector) | None built-in | Tens of millions | Self-host infra or managed pricing (RAM-priced) |
| Chroma | HNSW | Embedded / self-host (single-node) | Metadata filtering, post-filter | Basic | None built-in | Single-node scale, low millions | Self-host infra; embedded is free |
| LanceDB | IVF-PQ (columnar, Arrow-backed) | Embedded / self-host / object storage | Column-predicate pushdown (SQL-like) | Basic | PQ native | Scales with object storage, not RAM-bound | Object-storage cost (cheap cold tier) |
| FAISS | HNSW, IVF, IVFPQ, ScaNN-adjacent | Library, not a database — no hosting model | None — you build filtering yourself | None — you build fusion yourself | PQ, scalar, binary | Whatever you engineer around it | No hosting cost; engineering cost instead |
| Turbopuffer | LSM-tree + object-storage-backed ANN | SaaS only | Metadata filtering, single-stage | Native | Managed internally | Billion-scale, cold-tier-cheap | Object-storage-based, priced for infrequent-query cold data |

¹ "Scale ceiling" is an order-of-magnitude practical estimate for a single logical index under typical production filtering and update load — not a benchmark number, and not a hard architectural limit for the sharded systems. Verify against your own filter selectivity and update rate; see the footnote below.

## pgvector: the "just use Postgres" default

If Postgres is already in your stack and the corpus is under roughly 10M vectors, pgvector wins on total cost of ownership by a wide margin: no new system to operate, transactional consistency for free, and metadata filtering that's just SQL — no separate filtering DSL to learn, no pre/post-filter tradeoff to reason about because the query planner already handles it. Support for `halfvec` (fp16 storage) and `bit` (binary) quantization narrows the memory gap with purpose-built vector databases. The ceiling is real, though: HNSW build time and index size in Postgres degrade past tens of millions of vectors in ways dedicated vector engines are built to avoid, and pgvector's IVFFlat option needs a `nlist` retuned as the table grows — nobody remembers to do this until recall silently degrades.

## Qdrant and Weaviate: the filtering-first and hybrid-first specialists

Qdrant's headline feature is filterable HNSW with payload indexing built into the graph structure itself, rather than filtering as an afterthought bolted onto a general ANN index — this is the answer when your queries are "semantically similar AND tenant_id = X AND status = active" and naive pre-filtering would otherwise break graph connectivity (see [[Concept - HNSW]] for why that happens). Weaviate's differentiator is native [[Concept - Hybrid Search and Reciprocal Rank Fusion]] as a first-class query mode — BM25 and dense search fused via RRF or a relative-score method without hand-rolling the fusion pipeline yourself.

## Milvus/Zilliz and Vespa: scale and ranking depth

Milvus's segment architecture (data is written into immutable segments that get merged and indexed independently) plus GPU-accelerated indexes like CAGRA target billion-scale corpora with high write throughput. Vespa is the oldest and most mature of the group — a tensor-and-text ranking engine originally built for large-scale web/ad ranking, where filters, BM25 text scores, and vector similarity can all be combined inside one ranking expression rather than composed as separate fusion stages after the fact.

## Embedded and object-storage-backed: the 2024-2026 cost trend

Chroma and LanceDB target single-node or embedded use — no server to run, good for prototyping or small-corpus applications, with LanceDB's Arrow-based columnar layout giving it strong scan performance for hybrid vector-plus-analytics workloads. FAISS is a library, not a database — no persistence, no filtering, no server; it's the substrate other systems build on, not something you point an application at directly. Turbopuffer and similar object-storage-backed designs are the notable 2024-2026 trend: keep an index over data that lives cheaply in object storage rather than expensive attached RAM/SSD, trading some query latency for a cost structure that makes cold, rarely-queried, very large corpora economically viable in a way RAM-resident HNSW never was.

## Elasticsearch/OpenSearch and Redis: the "already running it" answers

If the org already runs an ELK stack, Elasticsearch/OpenSearch's Lucene-based HNSW plus native BM25 and RRF fusion is usually the pragmatic default — mature filtering, mature operations tooling, and no new system to learn, even if a purpose-built vector database would edge it out on raw ANN latency. Redis via the RediSearch module is the equivalent answer when Redis is already the org's caching/session layer; its RAM-priced cost model caps practical scale lower than the others in this table.

## Footnote: benchmark on your own workload

The single biggest differentiator across this table is metadata filtering strategy, not raw ANN throughput — and it's the dimension public benchmarks like ann-benchmarks systematically fail to capture, because they run on uniform synthetic data with no filters and no updates. A system that tops ann-benchmarks on unfiltered recall@10 can fall over on your actual traffic if your queries are 90% filtered by tenant or date range, or if your corpus has a high delete/update rate that degrades graph-based indexes (see [[Gotchas - Vector Index Tuning]] for the mechanics of why deletes and filters are where indexes actually break). Benchmark candidates against your own filter selectivity, update rate, and query mix before committing — the number on the leaderboard is not the number you will get.

## Connections

- [[Concept - HNSW]] — the dominant in-memory index type across most of this table (Qdrant, Weaviate, Elasticsearch, Redis, pgvector); understand its filtering-interaction failure mode to read the filtering-strategy column correctly.
- [[Concept - IVF and Product Quantization]] — the cluster-and-compress alternative to graph indexes, used by pgvector's IVFFlat, Milvus, and LanceDB for memory-bounded scale.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — the fusion method several rows (Weaviate, Qdrant, Milvus, Elasticsearch) implement natively as a first-class query mode.
- [[Concept - Embedding Quantization]] — the scalar/binary/PQ options in the quantization column are what let these systems fit large corpora into RAM at all.
- [[Reference - Memory Math for Transformers]] — the byte-level accounting (Hardware & Systems) behind why quantization and scale ceilings move together in this table.
- [[Playbook - Building a Production RAG System]] — this matrix is the lookup table that playbook's indexing step points to when choosing a store.
- [[Concept - Semantic Search]] — the retrieval paradigm every system in this table exists to serve; read it first if the index-vs-filter tradeoffs here don't yet make sense.
- [[Concept - Cost Engineering for LLM Applications]] — the cost-model column feeds directly into the same budget conversation as embedding and generation spend.
