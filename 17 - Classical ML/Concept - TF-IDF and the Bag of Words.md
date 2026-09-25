---
tags: [concept, domain/classical-ml, level/surface]
aliases: [TF-IDF, bag of words, BoW, term frequency-inverse document frequency]
summary: "Sparse count-based text representation weighting terms by frequency and rarity; still a near-free, strong baseline for classification and retrieval."
---

# Concept - TF-IDF and the Bag of Words

> Bag-of-words and TF-IDF turn a document into a sparse vector of weighted term counts. You lose word order and get something that trains in milliseconds, needs no GPU and is fully interpretable. Next to transformer embeddings it looks like a relic, but as of 2026 it's still the right first thing to try for text classification, keyword retrieval, and anywhere you want a near-free filter before paying for an LLM call.

## The mechanism

Bag-of-words represents a document $d$ as a vector over the vocabulary, each coordinate the count of that term in $d$. Order is gone: "dog bites man" and "man bites dog" give the same vector. N-grams (bigrams, trigrams) win back some local order by treating adjacent word pairs/triples as vocabulary items, at the price of a combinatorial blow-up. A vocabulary of 50k unigrams can turn into millions of bigram+trigram features.

Raw counts overweight ubiquitous words ("the", "is") that carry no discriminative signal. TF-IDF fixes that with a two-part weight:

$$w(t,d) = \text{tf}(t,d) \times \log\frac{N}{\text{df}(t)}$$

where $\text{tf}(t,d)$ is the term's frequency in document $d$, $N$ the corpus size, and $\text{df}(t)$ the number of documents containing $t$. Common variants: sublinear TF, $1 + \log(\text{tf})$, damps the effect of a term appearing 50 times instead of 5; smoothed IDF, $\log\frac{1+N}{1+\text{df}(t)} + 1$, avoids division by zero for terms in every document. The intuition is simple. A term frequent in this document and rare across the corpus tells you about *this* document. A term that appears everywhere (low IDF) tells you nothing.

TF-IDF vectors are then L2-normalized and compared by cosine similarity, the standard measure of how alike two documents' term distributions are. Normalization removes scale, so it doesn't care about document length.

The hashing trick (feature hashing, Weinberger et al., 2009) swaps the stored vocabulary-to-index map for a hash function that sends any token straight to one of $2^k$ fixed buckets. Memory is constant whatever the vocabulary size, there's no vocabulary-building pass over the corpus, and it streams: you can hash a token you've never seen without retraining. Collisions (two tokens in one bucket) are mostly harmless at reasonable bucket counts, since the noise averages out across a downstream linear model's weights.

## In practice

Feed cosine-normalized TF-IDF vectors into a linear classifier (logistic regression or a linear SVM) and you still have a legitimate top baseline for text classification. Training takes milliseconds on a CPU, inference is a sparse dot product, and you can read every weight to see which terms pushed the decision and by how much. In regulated or debugging-heavy settings that interpretability is a decisive advantage over an opaque embedding model.

Where it still wins in 2026:
- **Cold-start / low-data classification.** TF-IDF + a linear model needs no pretraining corpus and works with a few hundred labeled examples, where a fine-tuned embedding model would overfit or need far more data.
- **Keyword-heavy retrieval.** BM25, TF-IDF's probabilistic successor, is still the sparse half of every serious hybrid search stack (see [[Concept - Hybrid Search and Reciprocal Rank Fusion]]), because dense embeddings systematically underweight exact keyword, entity and code-token matches.
- **Cheap routing and guardrails.** A TF-IDF classifier making a keep/reject or route-A/route-B call before an LLM is invoked costs essentially nothing and catches the easy 80% of cases, leaving the hard 20% for the expensive model (see [[Concept - Cost Engineering for LLM Applications]]).

## Failure modes

- **Vocabulary explosion with n-grams.** Going from unigrams to bigrams+trigrams on a large corpus can multiply the feature space 10-100x. Without a min-document-frequency cutoff or the hashing trick, memory and training time blow up.
- **Domain shift breaks learned term weights.** A classifier built on IDF statistics from one corpus (news, say) degrades silently on another (medical notes) because the rarity structure has shifted. "Positive" and "negative" mean different things there and show up at different frequencies.
- **Mistaking surface overlap for meaning.** TF-IDF cosine measures shared vocabulary, not semantic relatedness. Two sentences about the same event in different words score low. Two sentences sharing nouns with opposite meaning ("the drug cures the disease" vs. "the drug causes the disease") can score high. Dense embeddings were built to fix that limitation.

## The non-obvious

People keep relearning that a tuned TF-IDF + linear SVM baseline is embarrassingly hard to beat on many real classification tasks. Jumping straight to a fine-tuned transformer without running it is a common way to spend a week finding out you gained two points of F1 for a hundred times the latency and cost. Compute the TF-IDF number first, then justify every added unit of complexity against it.

On the retrieval side the folklore is sharper. Hybrid search practitioners have found that dropping the sparse (BM25/TF-IDF) leg and trusting embeddings alone kills recall on exact terms without anyone noticing: product SKUs, error codes, proper nouns, and numbers a dense model has learned to treat as roughly interchangeable with their semantic neighbors.

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
