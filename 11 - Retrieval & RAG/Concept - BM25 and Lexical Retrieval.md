---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [BM25, Okapi BM25, lexical search, sparse retrieval, TF-IDF successor]
summary: "BM25 scores documents by saturating term frequency and weighting by rarity — the decades-old baseline that still wins on exact match."
---
> **One-paragraph hook:** Before you reach for an embedding model, you already run a retrieval algorithm in production somewhere: BM25 powers Elasticsearch, Lucene, and every "search" box built before 2020. It descends directly from [[Concept - TF-IDF and the Bag of Words]], needs no training, has no drift, uses no GPU, and on out-of-domain corpora it routinely beats dense retrievers that cost millions to train. Any serious [[Concept - Retrieval-Augmented Generation]] system either uses it or has to explain why not.

## The mechanism

BM25 ("Best Match 25") scores a document $d$ against a query $q$ by summing a per-term contribution over the query's terms:

$$\text{BM25}(d, q) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t,d) \cdot (k_1 + 1)}{f(t,d) + k_1 \left(1 - b + b \cdot \frac{|d|}{\text{avgdl}}\right)}$$

The moving parts:

- **$f(t,d)$**: raw frequency of term $t$ in document $d$.
- **$k_1$** (typically 1.2–2.0) sets how fast the term-frequency contribution *saturates*. Without saturation, a document repeating "database" 50 times would score 50x higher than one mentioning it once. BM25 caps the marginal value of extra occurrences, since the 10th occurrence of a word tells you almost nothing the 2nd didn't. As $f(t,d) \to \infty$, the fraction approaches $k_1 + 1$.
- **$b$** (typically 0.75) is the strength of length normalization. $|d|/\text{avgdl}$ is the document's length relative to the corpus average. $b=1$ normalizes fully by length, penalizing long documents that pile up term counts just by being long; $b=0$ turns normalization off.
- **IDF(t)**, inverse document frequency: $\log\left(\frac{N - n_t + 0.5}{n_t + 0.5}\right)$, where $N$ is the corpus size and $n_t$ the number of documents containing $t$. Rare terms get large positive weight. Terms in nearly every document (stopwords) get weight near zero *automatically*, so BM25 handles stopwords from corpus statistics alone, with no stopword list.

It all runs on an **inverted index**: for each term, a postings list of (doc_id, term_frequency) pairs. A query only touches the postings lists for its own terms, so the cost is $O(\text{query terms} \times \text{postings length})$, not $O(N)$. That's how Lucene and Tantivy scale lexical search to billions of documents on commodity hardware: documents without a query term are never scanned.

```
query = ["invoice", "overdue"]
for term in query:
    postings = inverted_index[term]        # sorted (doc_id, tf) list
    for doc_id, tf in postings:
        score[doc_id] += idf(term) * saturate(tf, doc_len[doc_id], k1, b, avgdl)
return top_k(score)
```

## In practice

- **Where lexical wins outright:** exact-match queries. Product SKUs, error codes, part numbers, person names, function/API identifiers, rare technical jargon. An embedding model trained on general web text will happily put "ERR_4471" next to "ERR_4470" and "system error"; BM25 treats them as different tokens unless they literally match. If your users search logs, code or a product catalog, you need lexical retrieval.
- **BM25F** extends the formula to fielded documents (title, body, tags) with a weight per field. E-commerce and document search use it heavily, since a title match should outrank a body match.
- **BEIR** (Thakur et al. 2021) made the case concrete. Across a heterogeneous suite of out-of-domain, zero-shot retrieval tasks, plain BM25 matched or beat several early dense retrievers that had never seen those domains in training. The lesson that stuck: dense retrievers overfit to their training distribution. BM25 can't: it has no learned parameters to overfit.
- Production lexical engines: Lucene (and everything built on it: Elasticsearch, OpenSearch, Solr) and Tantivy (Rust, used by Quickwit and some vector-DB hybrid backends). You won't hand-roll an inverted index in production; you'll configure one of these.

## Failure modes

- **Vocabulary mismatch.** A query for "car" against a document that only says "automobile" gets nothing from that term. This is the biggest reason to pair BM25 with dense retrieval (see [[Concept - Hybrid Search and Reciprocal Rank Fusion]]).
- **$k_1$/$b$ tuned for a different corpus.** The defaults (1.2, 0.75) come from TREC-era news corpora. On very short documents (chat messages, product titles) or very long ones (full books), untouched defaults silently mis-rank. To check, see whether raising $b$ meaningfully changes ranking order on your eval set. If it does, your corpus's length distribution matters and the defaults are a guess.
- **Stemming/tokenization mismatches.** BM25 works on tokens, so "run", "running" and "runs" only match if your analyzer stems them. The silent recall loss looks just like vocabulary mismatch and often gets misdiagnosed as "we need a better embedder" when the fix is an analyzer change.
- **Numbers and IDs tokenized badly.** Default analyzers often split "SKU-4471-B" into three tokens, which wrecks exact-match precision on the very queries lexical search exists for. Look at your analyzer's output on real IDs before trusting BM25 for catalog search.

## The non-obvious

BM25 has no training and no embedding drift. Swapping your LLM needs no re-index, there's no model to version, and no "the embedding model got deprecated" incident. It's also the cheapest arm of any retrieval stack by a wide margin: no GPU inference, no per-query embedding-API cost. Say so explicitly when justifying architecture to whoever owns [[Concept - Cost Engineering for LLM Applications]]. Teams that go all-in on dense retrieval and then face a hard deadline for exact-match search (a customer complaining "I searched the exact order number and got nothing") relearn this the hard way. The rule that survives production: BM25 is a permanent complementary signal, not a legacy fallback you migrate off. BM25's BEIR result is evidence that lexical retrieval's relative advantage *grows* as you move out-of-domain from whatever your dense retriever was trained on.

## Connections

- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — BM25 is the lexical arm that fusion combines with dense retrieval to cover both exact-match and semantic queries.
- [[Concept - Learned Sparse Retrieval]] — the neural evolution of this idea (SPLADE) keeps the inverted-index efficiency but learns term weights and expansion instead of using static IDF.
- [[Concept - Semantic Search]] — the dense counterpart; understanding where each fails motivates why you need both.
- [[Concept - Rerankers]] — BM25's top-100 is a cheap, high-recall candidate set that a cross-encoder reranker then re-scores for precision.
- [[Concept - RAG Evaluation]] — recall@k on your golden set is how you'd actually detect the vocabulary-mismatch and mistuned-parameter failure modes above.
- [[Reference - Vector Database Landscape]] — several vector databases (Weaviate, Elasticsearch/OpenSearch) ship BM25 natively alongside dense indexes for exactly this reason.
- [[Concept - TF-IDF and the Bag of Words]] — the simpler, prerequisite scoring scheme (Classical ML) that BM25 refines with saturation and length normalization.
- [[Deep Dive - RAG Architectures]] — traces where lexical retrieval sits in the naive-to-advanced RAG pipeline progression.
- [[Concept - Cost Engineering for LLM Applications]] — BM25's zero-inference-cost profile is a first-order input to any RAG cost model (Production & Ops).

## Sources

- Thakur et al. (2021) — BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models. Showed BM25 as a hard, often-winning zero-shot baseline against early dense retrievers.
- Robertson & Zaragoza (2009) — The Probabilistic Relevance Framework: BM25 and Beyond. The canonical reference for the BM25 formula and its probabilistic derivation.
