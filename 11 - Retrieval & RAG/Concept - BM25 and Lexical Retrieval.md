---
tags: [concept, domain/retrieval-rag, level/core]
aliases: [BM25, Okapi BM25, lexical search, sparse retrieval, TF-IDF successor]
summary: "BM25 scores documents by saturating term frequency and weighting by rarity — the decades-old baseline that still wins on exact match."
---
> **One-paragraph hook:** Before you reach for an embedding model, you already have a retrieval algorithm running in production somewhere: BM25 powers Elasticsearch, Lucene, and every "search" box built before 2020. It is the direct statistical descendant of [[Concept - TF-IDF and the Bag of Words]], has no training, no drift, no GPU, and on out-of-domain corpora it routinely beats dense retrievers that cost millions to train. Any serious [[Concept - Retrieval-Augmented Generation]] system either uses it directly or has to explain why not.

## The mechanism

BM25 ("Best Match 25") scores a document $d$ against a query $q$ by summing a per-term contribution over the query's terms:

$$\text{BM25}(d, q) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t,d) \cdot (k_1 + 1)}{f(t,d) + k_1 \left(1 - b + b \cdot \frac{|d|}{\text{avgdl}}\right)}$$

Three moving parts:

- **$f(t,d)$** — raw term frequency of term $t$ in document $d$.
- **$k_1$** (typically 1.2–2.0) — controls how fast the term-frequency contribution *saturates*. Without saturation, a document that repeats "database" 50 times would score 50x higher than one mentioning it once; BM25 caps the marginal value of additional occurrences, because the 10th occurrence of a word tells you almost nothing the 2nd didn't. As $f(t,d) \to \infty$, the fraction asymptotes to $k_1 + 1$.
- **$b$** (typically 0.75) — length normalization strength. $|d|/\text{avgdl}$ is the document's length relative to the corpus average; $b=1$ fully normalizes by length (penalizing long documents that rack up term counts just by being long), $b=0$ disables normalization entirely.
- **IDF(t)** — inverse document frequency, $\log\left(\frac{N - n_t + 0.5}{n_t + 0.5}\right)$ where $N$ is the corpus size and $n_t$ is the number of documents containing $t$. Rare terms get large positive weight; terms appearing in nearly every document (stopwords) get weight near zero *automatically* — BM25 solves the stopword problem without a stopword list, just from the statistics of the corpus.

Mechanically, this all runs on an **inverted index**: for each term, a postings list of (doc_id, term_frequency) pairs. Scoring a query only touches the postings lists for the query's terms, not the whole corpus — that's $O(\text{query terms} \times \text{postings length})$, not $O(N)$. This is why systems like Lucene and Tantivy scale lexical search to billions of documents on commodity hardware: you never scan documents that don't contain a query term.

```
query = ["invoice", "overdue"]
for term in query:
    postings = inverted_index[term]        # sorted (doc_id, tf) list
    for doc_id, tf in postings:
        score[doc_id] += idf(term) * saturate(tf, doc_len[doc_id], k1, b, avgdl)
return top_k(score)
```

## In practice

- **Where lexical wins outright**: exact-match queries — product SKUs, error codes, part numbers, person names, function/API identifiers, rare technical jargon. An embedding model trained on general web text will happily place "ERR_4471" near "ERR_4470" and "system error" in the same neighborhood; BM25 treats them as completely different tokens unless they literally match. If your users search logs, code, or a product catalog, lexical retrieval is not optional.
- **BM25F** extends the formula to fielded documents (title, body, tags), giving each field its own weight — used heavily in e-commerce and document search where a title match should outrank a body match.
- **BEIR** (Thakur et al. 2021) is the benchmark that made this concrete: across a heterogeneous suite of retrieval tasks (out-of-domain, zero-shot), plain BM25 was competitive with or beat several early dense retrievers that had never seen that domain in training. The lesson that stuck: dense retrievers overfit to their training distribution in ways BM25 structurally cannot, because BM25 has no learned parameters to overfit.
- Production lexical engines: Lucene (and everything built on it — Elasticsearch, OpenSearch, Solr) and Tantivy (Rust, used by Quickwit and some vector-DB hybrid backends). You will not hand-roll an inverted index in production; you'll configure one of these.

## Failure modes

- **Vocabulary mismatch**: a query for "car" against a document that only says "automobile" scores zero contribution from that term. This is the single biggest reason to pair BM25 with dense retrieval — see [[Concept - Hybrid Search and Reciprocal Rank Fusion]].
- **Over-tuned $k_1$/$b$ from a different corpus**: defaults (1.2, 0.75) come from TREC-era news corpora. On very short documents (chat messages, product titles) or very long ones (full books), leaving defaults untouched silently mis-ranks; detect by checking whether increasing $b$ changes ranking order meaningfully on your eval set — if it does, your corpus's length distribution matters and defaults are a guess, not a setting.
- **Stemming/tokenization mismatches**: BM25 operates on tokens, so "run" vs "running" vs "runs" only match if your analyzer stems them. Silent recall loss here looks identical to a vocabulary-mismatch failure and is often misdiagnosed as "we need a better embedder" when the fix is a tokenizer/analyzer change.
- **Numbers and IDs tokenized badly**: default analyzers often split "SKU-4471-B" into three tokens, destroying exact-match precision on the very queries lexical search exists to serve. Check your analyzer's tokenization output on real IDs before trusting BM25 for catalog search.

## The non-obvious

BM25 has zero training and zero embedding drift — there's no re-indexing needed when you swap your LLM, no model to version, and no "the embedding model got deprecated" incident. This also makes it the cheapest arm of any retrieval stack by a wide margin: no GPU inference, no per-query embedding-API cost, a fact worth stating explicitly when justifying architecture to whoever owns [[Concept - Cost Engineering for LLM Applications]]. Teams that go all-in on dense retrieval and then hit a hard deadline for exact-match search (a customer complaining "I searched the exact order number and got nothing") relearn this the hard way. The practical rule of thumb that survives contact with production: BM25 is not a legacy fallback you're migrating away from, it's a permanent complementary signal — the BEIR result is evidence that lexical retrieval's relative advantage *grows*, not shrinks, as you move out-of-domain from whatever your dense retriever was trained on.

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
