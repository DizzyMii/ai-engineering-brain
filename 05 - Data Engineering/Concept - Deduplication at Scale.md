---
tags: [concept, domain/data-engineering, level/advanced]
aliases: [dedup, near-deduplication, MinHash, MinHash-LSH]
summary: "Removing exact and near-duplicate text at web scale — hashing, suffix arrays, and MinHash-LSH — and why granularity is the real knob."
---

# Concept - Deduplication at Scale

> **One-paragraph hook:** Common Crawl is full of the same content over and over — mirrored articles, boilerplate legal pages, templated product listings, the same viral post scraped from a dozen aggregators. Left in, duplicates don't just waste training compute; they get memorized. Lee et al. (2021), "Deduplicating Training Data Makes Language Models Better," showed that near-deduplication cuts verbatim memorized emission by roughly an order of magnitude, reduces train/test overlap, and improves perplexity — making dedup one of the highest return-on-effort operations in the entire [[Deep Dive - The Pretraining Data Pipeline]].

## The mechanism

Deduplication operates at three granularities, cheapest and crudest to most expensive and precise.

**Exact dedup** hashes whole documents and drops repeats — trivial, but only catches byte-identical copies. A step up is **ExactSubstr**: build a suffix array over the entire corpus and remove any exactly repeated span of 50+ tokens, regardless of what document it's embedded in. This catches templated boilerplate (navigation chrome, legal disclaimers, copy-pasted paragraphs) that exact whole-document hashing misses because it's surrounded by different unique text.

**Fuzzy near-dedup via MinHash + LSH** is where most of the engineering effort goes, because most real-world duplication is *near*-duplication — the same article with a different ad banner, a reposted blog with one paragraph edited. The pipeline:

1. **Shingle** each document into overlapping n-grams (typically 5-grams of words).
2. **MinHash** the shingle set: apply $k$ independent hash-permutations to the shingle set and keep the minimum hash value under each permutation as one coordinate of a $k$-dimensional signature ($k$ is usually 128–256). The fraction of matching coordinates between two signatures is an unbiased estimator of Jaccard similarity, $J(A,B) = |A \cap B| / |A \cup B|$ — this is the entire trick that turns an $O(n^2)$ all-pairs similarity problem into a fixed-size fingerprint comparison.
3. **LSH-band** the signature: split the $k$ hash values into $b$ bands of $r$ rows each ($b \times r = k$), and treat two documents as a *candidate pair* if they match exactly on all $r$ rows in at least one band. For true Jaccard similarity $s$, the probability that two documents become a candidate pair is

$$P(\text{candidate}) = 1 - \left(1 - s^r\right)^b$$

which is an S-curve in $s$ — sharply separating pairs above a target similarity from pairs below it. The steepness and location of that curve is set entirely by $(b, r)$; the approximate 50%-detection crossover is $\left(\tfrac{1}{b}\right)^{1/r}$. For example, 128 hashes split as $b{=}13$ bands of $r{=}10$ rows each ($130 \approx 128$) gives a crossover near $(1/13)^{1/10} \approx 0.77$ — close to the ~0.7–0.8 Jaccard threshold most open pipelines target. Get $(b, r)$ wrong and you either keep obvious near-duplicates (threshold too high) or start merging genuinely distinct documents that just happen to share a lot of common phrasing (threshold too low).
4. **Cluster** candidate pairs with union-find (connected components): any two documents linked by a chain of candidate-pair edges end up in the same cluster, and only one representative per cluster survives.

## In practice

Distributed dedup at corpus scale is a giant shuffle-and-join, not a simple filter pass: candidate pairs have to be generated across the whole corpus, and the union-find step is a global operation that doesn't parallelize cleanly — a small number of "hub" documents (viral templates, extremely common boilerplate) can match thousands of others and blow up memory on whichever worker handles that band. Real numbers: SlimPajama deduped RedPajama's 1.2T tokens down to 627B (roughly 49.6% removed) — essentially half a trillion-token corpus was duplicate content by volume. Tooling has converged on `text-dedup` and HuggingFace's DataTrove for running this at scale.

Granularity is a real design choice, not a technicality: document-level, paragraph-level, and exact-substring dedup catch different things and produce different downstream corpora, and the right choice interacts with how the corpus will later be [[Concept - Data Mixtures|mixed]] and [[Concept - Training Set Decontamination|decontaminated]].

## Failure modes

**Wrong $(b, r)$ silently miscalibrates the whole pass.** Too permissive a banding config keeps obvious near-duplicates in the corpus; too aggressive a config starts merging documents that are topically similar but not actually redundant — a failure mode that's invisible unless you spot-check the clusters directly rather than trusting the dedup rate as a health metric.

**Near-duplication is not transitive, so union-find over-merges.** If document A is a near-dup of B, and B is a near-dup of C, that does not imply A and C are near-duplicates of each other — but connected-components clustering will chain them into one cluster anyway, and one representative is kept for all three. At scale, this produces long transitive chains that quietly delete legitimately distinct documents.

**Global cross-dump dedup can make a corpus worse, not better** — the FineWeb finding (Penedo et al. 2024, see [[Breakdown - FineWeb and FineWeb-Edu]]). Content that's genuinely high-quality tends to get duplicated *more*, not less, across many Common Crawl snapshots — it gets re-syndicated, mirrored, and cited. Deduping globally across all dumps disproportionately strips that high-quality duplicated content while leaving unique low-quality text at full weight relative to the survivors, inverting the intended effect. FineWeb's fix was to dedup within each dump rather than across dumps.

**Hub documents blow up distributed memory.** A single extremely common boilerplate page (a cookie-consent template, a syndicated wire-service article) can generate an enormous number of candidate-pair edges, overwhelming whichever shard of the union-find join it lands on — a scaling failure that only shows up at production data volumes, not on a test corpus.

## The non-obvious

The FineWeb per-dump-vs-global-dedup result is the sharpest lesson in this space: "more deduplication" is not monotonically better, and the standard intuition — dedup removes redundant noise, so more of it is strictly good — is wrong at the corpus level because duplication rate correlates with quality, not just with junk. The only reliable way to know whether a dedup configuration helped is the same discipline used everywhere else in the pipeline: train a small model on each candidate corpus and compare on held-out evals, not trust the raw duplicate-removal percentage as a proxy for quality.

## Connections
- [[Snippet - MinHash LSH Deduplication]] — a complete runnable implementation of the shingle-to-signature-to-banding-to-union-find pipeline described above.
- [[Concept - Semantic Deduplication]] — the frontier extension that catches paraphrases and translations MinHash's lexical shingling structurally cannot see.
- [[Concept - Quality Filtering for Pretraining Data]] — the pipeline-ordering partner: dedup should run before this stage so classifier compute isn't spent scoring duplicates.
- [[Concept - Training Set Decontamination]] — mechanically the same operation (targeted removal by overlap) applied against eval sets instead of the corpus itself.
- [[Concept - Data Mixtures]] — dedup granularity changes each domain's effective surviving size, which is exactly the input the mixture-weighting stage needs to be correct.
- [[Breakdown - FineWeb and FineWeb-Edu]] — the source of the counterintuitive per-dump-vs-global dedup finding this note's Failure modes section leads with.
- [[Deep Dive - The Pretraining Data Pipeline]] — places this stage in the full pipeline and explains why it runs before quality scoring.
- [[Gotchas - Pretraining Data Pipelines]] — catalogues the verbatim-memorization and "global dedup made it worse" failures as production incidents, not just theory.
- [[Concept - HNSW]] — a different approximate-nearest-neighbor structure solving the same "avoid $O(n^2)$ comparisons" problem, used for embedding search rather than lexical fingerprints.
- [[Deep Dive - Anatomy of a Pretraining Run]] — the downstream consumer whose loss curve and memorization behavior directly reflect whether this stage was configured correctly.

## Sources
- Lee et al. (2021) — "Deduplicating Training Data Makes Language Models Better": the primary evidence that near-dedup materially reduces memorized verbatim emission and improves perplexity.
- Broder (1997) — "On the Resemblance and Containment of Documents": the original MinHash construction for estimating Jaccard similarity via minimum hash values.
- Leskovec, Rajaraman & Ullman — "Mining of Massive Datasets," ch. 3: the standard reference for the LSH banding math and the $(b, r)$ threshold-tuning tradeoff used above.
- Soboleva et al. (2023) — SlimPajama technical report: the 1.2T-to-627B RedPajama dedup result cited in In Practice.
- Penedo et al. (2024) — "FineWeb: decanting the web for the finest text data at scale": the per-dump vs. global dedup finding this note treats as its central non-obvious insight.
