---
tags: [concept, domain/classical-ml, level/surface]
aliases: [TF-IDF, bag of words, BoW, term frequency-inverse document frequency]
summary: "Sparse count-based text representation weighting terms by frequency and rarity; still a near-free, strong baseline for classification and retrieval."
---

# Concept - TF-IDF and the Bag of Words

> Bag-of-words and TF-IDF turn a document into a sparse vector of weighted term counts, discarding word order in exchange for something that trains in milliseconds, needs no GPU, and is fully interpretable. It reads as a relic next to transformer embeddings, but as of 2026 it remains the correct first thing to try for text classification, keyword retrieval, and any place you need a near-free filter before paying for an LLM call.

## The mechanism

Bag-of-words represents a document $d$ as a vector over the vocabulary, where each coordinate is the count of that term in $d$. Word order is thrown away entirely — "dog bites man" and "man bites dog" produce the identical vector. N-grams (bigrams, trigrams) partially recover local order by treating adjacent word pairs/triples as vocabulary items themselves, at the cost of a combinatorial blow-up in dimensionality: a vocabulary of 50k unigrams can become millions of bigram+trigram features.

Raw counts overweight ubiquitous words ("the", "is") that carry no discriminative signal. TF-IDF fixes this with a two-part weight:

$$w(t,d) = \text{tf}(t,d) \times \log\frac{N}{\text{df}(t)}$$

where $\text{tf}(t,d)$ is the term's frequency in document $d$, $N$ is the corpus size, and $\text{df}(t)$ is the number of documents containing $t$. Common variants: sublinear TF, $1 + \log(\text{tf})$, dampens the effect of a term appearing 50 times instead of 5; smoothed IDF, $\log\frac{1+N}{1+\text{df}(t)} + 1$, avoids division by zero for terms present in every document. The intuition is direct: a term that appears often in this document but rarely across the corpus is informative about *this* document; a term that appears everywhere (low IDF) is informative about nothing.

TF-IDF vectors are then L2-normalized and compared with cosine similarity — the standard measure of "how similar are these two documents' term distributions," invariant to document length because normalization removes the scale.

The hashing trick (feature hashing, Weinberger et al., 2009) replaces the stored vocabulary-to-index mapping with a hash function that maps any token directly to one of $2^k$ fixed buckets. This gives constant memory regardless of vocabulary size, requires no vocabulary-building pass over the corpus, and is streaming-friendly — you can hash a token you've never seen without retraining anything. Collisions (two different tokens landing in the same bucket) are mostly harmless at reasonable bucket counts because the resulting noise averages out across a downstream linear model's weights.

## In practice

Fed into a linear classifier — logistic regression or a linear SVM — cosine-normalized TF-IDF vectors are still a legitimate top baseline for text classification: training completes in milliseconds on a CPU, inference is a sparse dot product, and every weight is directly inspectable (which terms pushed the decision, and by how much). This interpretability is not a consolation prize; in regulated or debugging-heavy settings it's a decisive advantage over an opaque embedding model.

Where it still wins in 2026:
- **Cold-start / low-data classification** — TF-IDF + linear model needs no pretraining corpus and works with a few hundred labeled examples, where a fine-tuned embedding model would overfit or need far more data.
- **Keyword-heavy retrieval** — BM25, TF-IDF's probabilistic successor, remains the sparse half of every serious hybrid search stack (see [[Concept - Hybrid Search and Reciprocal Rank Fusion]]) precisely because exact keyword/entity/code-token matches are things dense embeddings systematically underweight.
- **Cheap routing and guardrails** — a TF-IDF classifier making a keep/reject or route-A/route-B decision before an LLM call is called costs essentially nothing and catches the easy 80% of cases, reserving the expensive model for the hard 20% (see [[Concept - Cost Engineering for LLM Applications]]).

## Failure modes

- **Vocabulary explosion with n-grams.** Moving from unigrams to bigrams+trigrams on a large corpus can multiply the feature space by 10-100x; without a min-document-frequency cutoff or the hashing trick, memory and training time blow up.
- **Domain shift breaks learned term weights.** A classifier trained on IDF statistics from one corpus (say, news) silently degrades when applied to another (say, medical notes) because the rarity structure of terms has shifted — "positive" and "negative" mean something entirely different and appear at different frequencies.
- **Mistaking surface overlap for meaning.** TF-IDF cosine similarity measures shared vocabulary, not semantic relatedness. Two sentences about the same event using different words score low similarity; two sentences sharing common nouns but opposite meaning ("the drug cures the disease" vs. "the drug causes the disease") can score high. This is the exact limitation that motivated dense embeddings.

## The non-obvious

Practitioners repeatedly relearn that a tuned TF-IDF + linear SVM baseline is embarrassingly hard to beat on many real classification tasks, and that skipping straight to a fine-tuned transformer without running this baseline first is a common way to waste a week discovering you gained two points of F1 for a hundred times the latency and cost. The correct engineering instinct is: always compute the TF-IDF baseline number first, then justify every unit of added complexity against it. On the retrieval side, the folklore is sharper still — hybrid search practitioners have found that dropping the sparse (BM25/TF-IDF) leg of retrieval, trusting embeddings alone, quietly kills recall on exact terms: product SKUs, error codes, proper nouns, and numbers that a dense embedding model has learned to treat as roughly interchangeable with their semantic neighbors.

## Connections
- [[Concept - Word2Vec and the Embedding Lineage]] — the direct successor: dense predictive embeddings built to fix TF-IDF's lack of synonymy and semantic generalization.
- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — TF-IDF/BM25 is the sparse retrieval leg fused with dense embedding search in modern hybrid pipelines.
- [[Concept - BM25 and Lexical Retrieval]] — the probabilistic refinement of TF-IDF scoring that is the actual production standard for lexical search.
- [[Concept - Embedding Models]] — the dense, learned alternative representation this note's limits motivate moving toward.
- [[Concept - Cost Engineering for LLM Applications]] — TF-IDF classifiers make a near-free pre-filter or router ahead of an expensive LLM call.
- [[Concept - Entropy and Cross-Entropy]] — IDF's $\log(N/\text{df})$ term is an information-theoretic rarity measure in the same family as entropy.
- [[Concept - Rerankers]] — a typical retrieval pipeline runs TF-IDF/BM25 or embeddings for cheap first-stage recall, then a reranker for precision.
- [[Concept - Learning from Imbalanced Data]] — the linear classifiers TF-IDF feeds inherit all the standard imbalance pitfalls (threshold moving, class weighting) once class skew shows up in text classification.

## Sources
- Weinberger et al. (2009) — *Feature Hashing for Large Scale Multitask Learning*. The hashing trick: fixed-memory, vocabulary-free feature mapping.
- Robertson & Spärck Jones — the probabilistic retrieval line (BM25) that formalized and superseded raw TF-IDF weighting for ranking.
