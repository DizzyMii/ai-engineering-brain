---
tags: [snippet, domain/inference-serving, level/advanced]
aliases: [modified rejection sampling, speculative sampling verification]
summary: "Reference implementation of speculative decoding's accept/reject + residual-resample rule, with an empirical proof of losslessness."
---

**What it does:** implements the modified-rejection-sampling rule from [[Concept - Speculative Decoding]]. Given target probs `p` and draft probs `q` over `k` drafted positions plus one bonus position, it accepts drafted tokens one at a time, stops at the first rejection, and resamples the replacement from the normalized positive residual. A second function runs thousands of trials and checks the emitted-token histogram against `p` directly, so the losslessness theorem is demonstrated instead of asserted. **Dependencies:** `numpy>=1.24` only. It's pure probability manipulation with no model, so no tensor framework. **Expected output:** printed mean accepted length (out of `k`) and a passing assertion that the empirical token histogram matches `p` to within a small tolerance.

```python
"""
Speculative decoding verification: the accept/reject + residual-resample
rule that makes draft-then-verify losslessly equivalent to sampling from the
target model alone. See Concept - Speculative Decoding for the derivation.
"""
import numpy as np


def verify_and_resample(p: np.ndarray, q: np.ndarray, draft_ids: np.ndarray,
                         rng: np.random.Generator):
    """
    p:         [k+1, V] target probs at each of the k drafted positions plus
               one bonus position, from a single target forward pass.
    q:         [k, V] draft probs at each of the k drafted positions.
    draft_ids: [k] int, the token ids the draft actually sampled from q.
    rng:       numpy Generator, passed in for reproducibility.

    Returns (emitted, n_accepted): emitted is the list of tokens this call
    produces (n_accepted verified draft tokens plus exactly one replacement
    or bonus token); n_accepted counts only the verified draft tokens.
    """
    k = draft_ids.shape[0]
    emitted = []
    for i in range(k):
        x = draft_ids[i]
        accept_prob = min(1.0, p[i, x] / q[i, x])
        if rng.uniform() <= accept_prob:
            emitted.append(x)
            continue
        # First rejection: resample from the normalized positive residual,
        # NOT from p or q alone -- this is what keeps the result lossless.
        residual = np.clip(p[i] - q[i], 0.0, None)
        residual = residual / residual.sum()
        emitted.append(rng.choice(len(residual), p=residual))
        return emitted, i
    # All k drafted tokens survived -- take the free bonus token from
    # position k, which the target already scored in the same forward pass.
    emitted.append(rng.choice(p.shape[1], p=p[k]))
    return emitted, k


def empirical_distribution_match(vocab_size: int = 8, k: int = 4,
                                  n_trials: int = 200_000, seed: int = 0):
    rng = np.random.default_rng(seed)
    # A fixed target distribution p, and a deliberately imperfect draft q
    # (half p, half unrelated noise) so acceptance is well below 100%.
    p_single = rng.dirichlet(np.ones(vocab_size))
    q_single = 0.5 * p_single + 0.5 * rng.dirichlet(np.ones(vocab_size))
    p = np.tile(p_single, (k + 1, 1))
    q = np.tile(q_single, (k, 1))

    hist = np.zeros(vocab_size)
    accepted_lengths = []
    for _ in range(n_trials):
        draft_ids = rng.choice(vocab_size, size=k, p=q_single)
        emitted, n_acc = verify_and_resample(p, q, draft_ids, rng)
        for tok in emitted:            # every reached position's own outcome
            hist[tok] += 1              # is individually p-distributed -- see below
        accepted_lengths.append(n_acc)

    hist /= hist.sum()
    max_err = np.abs(hist - p_single).max()
    print(f"mean accepted length: {np.mean(accepted_lengths):.2f} / {k}")
    print(f"max |empirical - p| over vocab: {max_err:.4f}")
    assert max_err < 0.01, "empirical distribution does not match target p"


if __name__ == "__main__":
    empirical_distribution_match()
```

## Why it's written this way

- **`min(1, p/q)` with `max(0, p-q)` is the unique pairing that reconstructs `p`, for any `q`.** Check the two cases. When `p(x) >= q(x)`, `min(p,q) = q` and `max(0, p-q) = p-q`, which sum to `p`. When `p(x) < q(x)`, `min(p,q) = p` and `max(0, p-q) = 0`, which again sum to `p`. So `P(emit x) = q(x)·min(1, p(x)/q(x)) + P(reject)·[max(0, p(x)-q(x)) / P(reject)] = min(p(x),q(x)) + max(0, p(x)-q(x)) = p(x)`. The residual's normalizer, `P(reject) = sum_x max(0, q(x)-p(x))`, cancels against the residual's own total mass, `sum_x max(0, p(x)-q(x))`, because both equal the total-variation gap between `p` and `q`.
- **Draft ids come from `q`.** In the test harness, `draft_ids` are sampled from `q_single` directly, as a real draft model would produce them. The `min(1, p/q)` formula only holds conditioned on `x` already being a draw from `q`. Testing against a freshly drawn `x'` that's independent of the draft's own samples would silently invalidate the derivation.
- **The bonus token is free because the target already computed it.** Position `k` in `p` comes from the same forward pass that scored positions `0..k-1`, so sampling it costs nothing extra. Full acceptance of `k` drafted tokens therefore yields `k+1` tokens per target call, not `k`.
- **The empirical check counts *every* reached position's outcome, not only the last token emitted.** This is easy to get wrong. It's tempting to test only `emitted[-1]` per trial, but after a rejection that token is the resampled replacement, and *conditioned on rejection* the resample is drawn from `residual`, not from `p`. Only the *mixture* of the accept and reject branches reconstructs `p` (the identity above). Each position's accept-or-resample decision is that full mixture and is independent of every other position's randomness. So putting every token any trial reaches (accepted draft tokens, a mid-sequence resample, or the bonus) into one histogram converges to `p`. Try it: change the accumulation loop back to `hist[emitted[-1]] += 1` and the assertion fails with an error around 0.2. That's a quick way to see that "the accept/reject mixture equals `p`" describes a full position's decision, not whichever slot a trial happens to end on.

## Connections
- [[Concept - Speculative Decoding]] — the derivation and losslessness proof this code implements verbatim; read it first for why `min(1, p/q)` plus residual resampling is the unique correct pairing.
- [[Concept - Self-Drafting Speculative Decoding (Medusa, EAGLE, Lookahead)]] — verifies proposals the same way regardless of whether they came from a separate draft model, Medusa heads, EAGLE features, or Lookahead's Jacobi candidates; this function is the shared verification core all of them call.
- [[Concept - Sampling and Decoding Parameters]] — `p` and `q` here are exactly the temperature/top-p-adjusted distributions from that pipeline, not raw softmax output.
- [[Concept - KL Divergence]] — cross-domain (01): the family of divergence measures governing why acceptance rate falls as `q` drifts from `p`; the residual term here tracks a total-variation-flavored gap rather than KL, but the intuition — distributional mismatch costs accepted tokens — is the same.
- [[Concept - Softmax]] — cross-domain (02): `p` and `q` are themselves softmax outputs (or softmax-then-truncated per the sampling pipeline), so their own numerical-stability handling composes with this snippet's residual computation.
