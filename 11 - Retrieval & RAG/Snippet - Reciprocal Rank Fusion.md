---
tags: [snippet, domain/retrieval-rag, level/core]
aliases: [RRF]
summary: "A complete, runnable Python implementation of Reciprocal Rank Fusion for merging BM25 and dense retrieval result lists."
---
# Snippet - Reciprocal Rank Fusion

> **What it does:** Fuses two or more already-ranked lists of document IDs (e.g. a BM25 result list and a dense-retrieval result list) into a single ranking, using Reciprocal Rank Fusion (Cormack, Clarke & Buettcher 2009) — see [[Concept - Hybrid Search and Reciprocal Rank Fusion]] for the mechanism this implements.
> **Dependencies:** none beyond the Python 3.9+ standard library (`collections.defaultdict`).
> **Expected output:** on the worked example below, the fused ranking is `doc2, doc1, doc3, doc4` — see the inline comment for the hand-verified per-document math.

```python
"""
Reciprocal Rank Fusion (RRF) — merges multiple ranked lists of document IDs
into one fused ranking, without ever comparing raw relevance scores across
systems (e.g. BM25's unbounded scores vs. cosine similarity in [-1, 1]).
"""

from collections import defaultdict
from typing import Optional, Sequence


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]],
    k: int = 60,
    weights: Optional[Sequence[float]] = None,
) -> list[tuple[str, float]]:
    """
    Fuse multiple ranked lists of doc IDs into one ranking.

    ranked_lists: e.g. [bm25_doc_ids, dense_doc_ids, ...], each already
                  sorted best-first. A doc need not appear in every list.
    k:            RRF's damping constant. k=60 is the value used in the
                  original paper and has become the de facto default: it
                  flattens the curve enough that being rank 1 vs. rank 2
                  in a single list doesn't dominate the fused score, while
                  still rewarding docs that rank consistently well across
                  lists over docs that rank #1 in exactly one list.
    weights:      optional per-list weight (e.g. trust dense over lexical,
                  or vice versa); defaults to equal weight 1.0 per list.

    Returns (doc_id, fused_score) pairs sorted descending by fused score.
    """
    if weights is None:
        weights = [1.0] * len(ranked_lists)
    assert len(weights) == len(ranked_lists), "one weight per ranked list"

    scores: dict[str, float] = defaultdict(float)
    for ranked_list, weight in zip(ranked_lists, weights):
        # rank is 1-indexed on purpose — see "Why it's written this way" below
        for rank, doc_id in enumerate(ranked_list, start=1):
            scores[doc_id] += weight * (1.0 / (k + rank))

    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)


if __name__ == "__main__":
    bm25_results = ["doc1", "doc2", "doc4", "doc3"]   # lexical arm, best-first
    dense_results = ["doc2", "doc3", "doc1"]          # dense arm; doc4 wasn't retrieved

    fused = reciprocal_rank_fusion([bm25_results, dense_results], k=60)
    for doc_id, score in fused:
        print(f"{doc_id}: {score:.5f}")

    # Expected output (hand-verifiable):
    # doc2: 0.03252   (bm25 rank 2 -> 1/62 = 0.01613) + (dense rank 1 -> 1/61 = 0.01639)
    # doc1: 0.03227   (bm25 rank 1 -> 1/61 = 0.01639) + (dense rank 3 -> 1/63 = 0.01587)
    # doc3: 0.03175   (bm25 rank 4 -> 1/64 = 0.01563) + (dense rank 2 -> 1/62 = 0.01613)
    # doc4: 0.01587   (bm25 rank 3 -> 1/63 = 0.01587) + (absent from dense -> 0)
```

## Why it's written this way

- **Fusing ranks, not scores, is the whole point.** BM25 scores are unbounded and corpus-dependent; cosine similarity lives in $[-1, 1]$. Adding them directly is invalid without fragile per-query score normalization. By discarding the raw scores and working only with each document's *position* in each list, RRF sidesteps the normalization problem entirely — it is scale-free by construction, which is why it needs no per-corpus tuning.
- **`k=60` is folklore, not derivation.** It comes straight from the original paper's empirical sweep, not a principled formula. It's large enough that the difference between rank 1 and rank 2 in one list ($\frac{1}{61}$ vs. $\frac{1}{62}$, a 1.6% relative gap) doesn't swamp a document that ranks consistently well across multiple lists — the entire value of fusion is rewarding cross-system agreement over single-system extremity.
- **`defaultdict(float)` accumulation is $O(\text{total results across all lists})$.** Each list is streamed through exactly once, adding a contribution per document; there's no pairwise comparison between lists, no sort-then-merge — just a running sum keyed by doc ID, which is why this scales to fusing many result lists (RAG-Fusion's multi-query case) without a combinatorial blowup.
- **Rank starts at 1, not 0 — this is a real bug people ship.** If you enumerate from 0, the top-ranked document in every list gets weight $\frac{1}{k+0} = \frac{1}{60}$ instead of $\frac{1}{61}$. Because $\frac{1}{k+r}$ is most convex near $r=0$, the gap between rank-0 and rank-1 weighting is proportionally the *largest* gap on the whole curve — using a 0-indexed rank silently overweights the very top result relative to the published formula and defeats the damping the $k$ constant exists to provide. It also means your `k=60` isn't actually the paper's `k=60` anymore; it behaves like `k=59`.

## Connections

- [[Concept - Hybrid Search and Reciprocal Rank Fusion]] — the retrieval-fusion concept this snippet implements the core formula for.
- [[Concept - BM25 and Lexical Retrieval]] — the typical source of one of the two ranked lists being fused, the lexical arm.
- [[Concept - Semantic Search]] — the typical source of the other ranked list, the dense arm.
- [[Concept - Rerankers]] — RRF's fused top-N is usually fed into a cross-encoder rerank pass next, not returned directly as the final answer.
- [[Concept - Query Transformation for Retrieval]] — RAG-Fusion generates N query paraphrases and RRF-fuses their N retrieved lists, extending this exact function beyond the two-list case.
- [[Snippet - The Log-Sum-Exp Trick]] — a sibling case of a small, numerically-careful trick that sidesteps a scale/overflow problem by changing representation rather than by normalizing (Foundations domain).
- [[Concept - Bagging and Random Forests]] — the classical-ML analogue: combining many weak, differently-biased predictors by aggregating their votes rather than trusting any single one's raw output scale (Classical ML domain).
