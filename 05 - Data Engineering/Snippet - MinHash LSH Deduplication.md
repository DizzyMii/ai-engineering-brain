---
tags: [snippet, domain/data-engineering, level/advanced]
aliases: [MinHash LSH, near-duplicate detection]
summary: "Runnable MinHash + LSH banding pipeline that near-deduplicates documents via shingling, signatures, and union-find clustering."
---

# Snippet - MinHash LSH Deduplication

**What it does:** near-deduplicates a small document set. It shingles each document into word 5-grams, computes 128-permutation MinHash signatures, builds an LSH index with explicit (bands, rows) banding, queries for near-duplicate candidates, and clusters transitively connected candidates with union-find so one representative per cluster survives. That shingle → signature → band → cluster pipeline is one stage of the full [[Deep Dive - The Pretraining Data Pipeline]], here run single-machine and in-memory instead of distributed.

**Dependencies:** `datasketch` (tested against 1.6.x; `pip install datasketch`), Python 3.10+.

**Expected output:** the printed banding threshold, then one line per cluster: the two near-duplicate documents grouped together, the unrelated one alone.

```python
"""
Near-dedup a tiny corpus with MinHash + LSH banding, then cluster
transitively-connected near-duplicates with union-find and keep one
representative per cluster.

Dependencies: datasketch (pip install datasketch), Python 3.10+
"""

from datasketch import MinHash, MinHashLSH

# ---- 1. demo corpus: docs 0 and 1 are a near-dup pair (one word changed),
#         doc 2 is unrelated -------------------------------------------------
DOCS = [
    "the quick brown fox jumps over the lazy dog near the river bank",
    "the quick brown fox leaps over the lazy dog near the river bank",
    "quantum computers use superposition to explore many states at once",
]


def shingle(text: str, k: int = 5) -> set[str]:
    """Word-level k-shingles. More robust to whitespace/HTML noise than
    character shingles at web-corpus scale, at the cost of needing longer
    documents to produce enough shingles."""
    words = text.split()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def minhash_signature(shingles: set[str], num_perm: int) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for sh in shingles:
        m.update(sh.encode("utf8"))
    return m


# ---- 2. build the LSH index with explicit banding --------------------------
NUM_PERM, BANDS, ROWS = 128, 20, 6
assert BANDS * ROWS == NUM_PERM

# (b, r) sets the S-curve: P(candidate) ~ 1 - (1 - s^r)^b.
# This is the standard closed-form approximation of the 50%-crossover
# threshold, not an exact solve -- always sanity-check against a held-out
# labeled pair before trusting it in production.
approx_threshold = (1 / BANDS) ** (1 / ROWS)
print(f"Signature threshold from banding: {approx_threshold:.3f} "
      f"(approx (1/b)^(1/r) with b={BANDS}, r={ROWS})")

lsh = MinHashLSH(threshold=approx_threshold, num_perm=NUM_PERM)
signatures = {}
for i, doc in enumerate(DOCS):
    sig = minhash_signature(shingle(doc), NUM_PERM)
    signatures[i] = sig
    lsh.insert(str(i), sig)

# ---- 3. query candidate near-dup pairs and build a graph -------------------
edges = []
for i, sig in signatures.items():
    for j_str in lsh.query(sig):
        j = int(j_str)
        if j > i:
            edges.append((i, j))

# ---- 4. union-find clusters transitively-connected near-dups ---------------
# NOTE: near-duplication is NOT transitive (A~B and B~C does not imply A~C),
# so this step can chain-merge weakly-related documents into one cluster --
# a real over-merging failure mode, not just a theoretical one.
parent = list(range(len(DOCS)))


def find(x: int) -> int:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a: int, b: int) -> None:
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb


for i, j in edges:
    union(i, j)

clusters: dict[int, list[int]] = {}
for i in range(len(DOCS)):
    clusters.setdefault(find(i), []).append(i)

for cid, members in enumerate(clusters.values()):
    print(f"Cluster {cid}: {members}")
```

Representative output:
```
Signature threshold from banding: 0.807 (approx (1/b)^(1/r) with b=20, r=6)
Cluster 0: [0, 1]
Cluster 1: [2]
```

## Why it's written this way

- **Word-level 5-grams instead of character-level.** Web documents carry HTML/whitespace noise, and character shingles are more sensitive to it. Word shingles match what production pipelines shingle on. The cost: a document needs enough words to produce any shingles at all.
- **128 permutations as 20 bands x 6 rows.** This lands near the ~0.8 [[Concept - Vector Norms and Distances|Jaccard similarity]] threshold that [[Concept - Deduplication at Scale]] cites as typical for web-corpus dedup. Fewer permutations save memory and compute but widen the S-curve's dead zone, so you get more false negatives and false positives near the threshold.
- **LSH for candidate generation, not brute-force all-pairs comparison.** At n=3 the overhead is invisible. At n=10^9 documents it's the whole reason dedup is tractable: brute-force Jaccard is O(n^2) and doesn't fit any reasonable wall-clock budget. LSH banding is the hashing-based sibling of graph-based approximate-nearest-neighbor indexes like [[Concept - HNSW]]. Both exist to avoid the same all-pairs comparison.
- **Union-find for transitive clustering, flagged as risky.** A chain A~B, B~C can leave A and C dissimilar under direct comparison, so you need clustering to decide which documents count as "the same". That same transitivity causes over-merging in production dedup runs. The union-find here is in-memory and single-machine; real corpora need a distributed union-find over a per-band external shuffle instead of a single Python dict.
- **Not shown: ordering relative to other pipeline stages.** In production this stage runs before [[Concept - Quality Filtering for Pretraining Data|quality filtering]] scores documents, so classifier compute isn't spent scoring duplicates that dedup would have removed anyway.

## Connections
- [[Concept - Deduplication at Scale]] — this snippet makes concrete the MinHash+LSH banding math that concept describes abstractly; production pipelines replace the in-memory union-find here with a distributed shuffle-and-join.
- [[Concept - Semantic Deduplication]] — MinHash only catches lexical near-dups; when paraphrases or translations need catching too, this is the next escalation.
- [[Concept - Quality Filtering for Pretraining Data]] — dedup and quality filtering are ordered pipeline stages; scoring before dedup wastes compute rescoring documents this snippet would have already clustered away.
- [[Deep Dive - The Pretraining Data Pipeline]] — this snippet implements one stage of that larger orchestrated pipeline.
- [[Concept - Vector Norms and Distances]] — Jaccard similarity, which MinHash estimates, is one of the family of similarity/distance measures that concept surveys.
- [[Concept - HNSW]] — LSH and HNSW are the two dominant approximate-similarity-search families; the banding here is the hashing-based alternative to HNSW's graph-based approach.
