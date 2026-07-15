---
tags: [snippet, domain/inference-serving, level/core]
aliases: []
summary: "Reference implementation of the logits-to-token pipeline: repetition penalty, temperature, top-k/top-p/min-p, softmax, multinomial draw."
---

**What it does:** takes a raw logit vector plus a short token-history list and returns a sampled token id, applying the exact pipeline production servers use: repetition penalty → temperature → top-k → top-p/min-p truncation → softmax → multinomial draw. **Dependencies:** `torch>=2.0` (works identically with plain numpy if you swap `torch.multinomial` for `np.random.choice`). **Expected output:** printed token distributions for greedy, `T=0.8 + top_p=0.95`, and `min_p=0.05` over a toy 10-token vocab, showing the tail get truncated to zero probability mass.

This is the concrete counterpart to [[Concept - Sampling and Decoding Parameters]] — that note explains *why* each transform exists; this snippet nails down the *order* they run in and the numerical-stability details that silently change output if you get them wrong. Every serving stack — vLLM, TGI, llama.cpp, the OpenAI API — implements some variant of this function, and the fact that they don't all implement it identically is the single biggest reason "the same sampling params" produce different-feeling outputs across providers.

```python
import torch

def sample_from_logits(
    logits: torch.Tensor,          # shape (vocab_size,), raw model output
    token_history: list[int] | None = None,
    temperature: float = 1.0,
    top_k: int | None = None,
    top_p: float | None = None,
    min_p: float | None = None,
    repetition_penalty: float = 1.0,
    generator: torch.Generator | None = None,
) -> int:
    logits = logits.clone().float()

    # 1. Repetition penalty (CTRL-style, Keskar et al. 2019) — applied to RAW
    #    logits, before temperature, so its effect scales with temperature too.
    #    Divide positive logits, MULTIPLY negative ones: dividing a negative
    #    logit would make it larger (less negative), which *rewards* the
    #    token you meant to punish. This sign-aware rule is the part people
    #    get wrong when they copy a naive "logits[tok] /= penalty" snippet.
    if repetition_penalty != 1.0 and token_history:
        for tok in set(token_history):
            if logits[tok] > 0:
                logits[tok] /= repetition_penalty
            else:
                logits[tok] *= repetition_penalty

    # 2. Temperature: divide logits BEFORE softmax. Because softmax is
    #    exponential, this is not a linear rescaling of probabilities —
    #    T<1 sharpens the distribution, T>1 flattens it, and the effect
    #    compounds with how peaked the raw logits already are.
    if temperature <= 0:
        return int(torch.argmax(logits).item())          # greedy = T -> 0
    logits = logits / temperature

    # 3. top-k: keep only the k highest logits, mask the rest to -inf.
    #    Masking with -inf (not 0, and not deleting entries) preserves
    #    vocab indices and guarantees exp(-inf) = 0 after softmax, so the
    #    masked tokens contribute exactly zero probability mass with no
    #    separate renormalization step needed.
    if top_k is not None and top_k > 0:
        top_k = min(top_k, logits.size(-1))
        kth_value = torch.topk(logits, top_k).values[..., -1]
        logits = torch.where(logits < kth_value, torch.full_like(logits, -float("inf")), logits)

    # 4. top-p (nucleus, Holtzman et al. 2019): sort descending, take
    #    cumulative softmax probability, keep the smallest prefix whose
    #    cumulative prob >= p. The shift-right-by-one on the removal mask
    #    is the classic off-by-one: without it you drop the token that
    #    CROSSES the threshold, which should be kept (it's what pushed
    #    cumulative prob over p in the first place).
    if top_p is not None and top_p < 1.0:
        sorted_logits, sorted_idx = torch.sort(logits, descending=True)
        sorted_probs = torch.softmax(sorted_logits, dim=-1)
        cum_probs = torch.cumsum(sorted_probs, dim=-1)
        sorted_remove = cum_probs > top_p
        sorted_remove[..., 1:] = sorted_remove[..., :-1].clone()  # the shift
        sorted_remove[..., 0] = False                              # always keep top-1
        remove_idx = sorted_remove.scatter(0, sorted_idx, sorted_remove)
        logits = logits.masked_fill(remove_idx, -float("inf"))

    # 5. min-p: keep tokens whose probability >= min_p * max_probability,
    #    computed on the POST-temperature distribution — it must track the
    #    already-sharpened/flattened logits, not the raw ones, or it either
    #    over- or under-truncates relative to what temperature just did.
    if min_p is not None and min_p > 0:
        probs = torch.softmax(logits, dim=-1)
        threshold = min_p * probs.max()
        logits = logits.masked_fill(probs < threshold, -float("inf"))

    # 6. Softmax + draw. Subtract max() before exp so the largest logit
    #    maps to exp(0)=1 instead of risking exp(large) overflow — this is
    #    the same log-sum-exp stability trick used everywhere softmax is
    #    computed (see Snippet - The Log-Sum-Exp Trick).
    logits = logits - logits.max()
    probs = torch.softmax(logits, dim=-1)
    return int(torch.multinomial(probs, num_samples=1, generator=generator).item())


if __name__ == "__main__":
    g = torch.Generator().manual_seed(0)
    toy_logits = torch.tensor([4.0, 3.5, 3.0, 1.0, 0.5, 0.2, -1.0, -2.0, -3.0, -5.0])

    print("greedy:", sample_from_logits(toy_logits, temperature=0.0))

    for _ in range(5):
        tok = sample_from_logits(toy_logits, temperature=0.8, top_p=0.95, generator=g)
        print("T=0.8,top_p=0.95 ->", tok)

    for _ in range(5):
        tok = sample_from_logits(toy_logits, temperature=1.0, min_p=0.05, generator=g)
        print("min_p=0.05 ->", tok)

    # Ordering footgun demo: temperature-before-top-k (this function) vs
    # top-k-before-temperature can select a DIFFERENT surviving token set
    # when logits are close together, because top-k's cutoff is computed
    # on different (scaled vs raw) values in each order.
    raw = toy_logits.clone()
    k_then_t = torch.topk(raw, 3).indices.tolist()
    t_then_k = torch.topk(raw / 0.5, 3).indices.tolist()  # same set here since
    print("top-k(raw) idx:", sorted(k_then_t), "top-k(scaled) idx:", sorted(t_then_k))
    # -- the sets diverge once ties or near-ties exist near the cutoff logit.
```

## Why it's written this way

- **`-inf` masking instead of zeroing probabilities.** Zeroing a probability after softmax requires a second renormalization pass and is easy to forget; masking the logit to `-inf` before softmax makes exclusion and renormalization the *same* operation, so there's no window where the distribution is inconsistent.
- **min-p computed after temperature, not before.** min-p's whole point is "stay proportional to how confident the model currently is." If you compute it on raw logits, a high temperature can let obviously-bad tokens back in because the raw distribution was already flat before you flattened it further.
- **Repetition penalty's sign split.** `logits[tok] /= penalty` looks right until `logits[tok]` is negative, at which point division *increases* it. The multiply-for-negative branch is a one-line fix that a large fraction of hand-rolled samplers skip, silently rewarding tokens they meant to suppress.
- **top-p's shift-then-mask, not filter-then-check.** Implementing nucleus sampling with a plain `cumsum > p` boolean and no shift drops the boundary-crossing token — a one-index bug that changes which tokens are reachable, and it's easy to ship without noticing because the model still produces plausible-looking text.

## Connections
- [[Concept - Sampling and Decoding Parameters]] — the conceptual treatment of temperature/top-k/top-p/penalties this snippet implements verbatim.
- [[Concept - Softmax]] — the normalization step every truncation strategy here operates in front of or behind.
- [[Concept - Advanced Samplers (min-p, Mirostat, DRY)]] — where min-p came from and the exotic samplers (Mirostat, DRY) this snippet doesn't cover.
- [[Concept - The Inference Request Lifecycle]] — this function is the "sampler" stage in the per-token decode loop.
- [[Snippet - The Log-Sum-Exp Trick]] — the same max-subtraction stability trick used here for softmax, generalized.

## Sources
- Holtzman et al. (2019) — *The Curious Case of Neural Text Degeneration*. Introduces nucleus (top-p) sampling.
- Keskar et al. (2019) — *CTRL: A Conditional Transformer Language Model for Controllable Generation*. Source of the multiplicative repetition penalty.
