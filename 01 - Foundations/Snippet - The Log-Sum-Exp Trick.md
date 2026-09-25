---
tags: [snippet, domain/foundations, level/core]
aliases: [LSE, logsumexp, stable softmax, log-softmax trick]
summary: "Compute log-sum-exp, log-softmax, and cross-entropy from logits without overflow: subtract the max, stay in log-space."
---

# Snippet - The Log-Sum-Exp Trick

**What it does:** computes $\mathrm{LSE}(x) = \log\sum_i e^{x_i}$, log-softmax, cross-entropy from logits, and softplus in numerically stable form, and shows the naive versions returning `inf`/`NaN` on realistic inputs. It's the most-used stability technique in ML. `exp(x)` overflows to `inf` at $x \approx 88.7$ in fp32 and $x \approx 11.09$ in fp16 (the log of each format's max finite value; see [[Concept - Floating Point for Deep Learning]]). Any naive softmax or [[Concept - Entropy and Cross-Entropy]] computation on real logits is one large activation away from a `NaN` loss.

**The identity:** with $m = \max_i x_i$,

$$\mathrm{LSE}(x) = m + \log\sum_i e^{x_i - m}$$

Factor $e^m$ out of the sum and you get this, so it's algebraically *exact*, with no approximation. After the shift the largest term is $e^0 = 1$ and every other term is $\le 1$, so overflow can't happen. The rest follows: $\log\mathrm{softmax}(x)_i = x_i - \mathrm{LSE}(x)$, and cross-entropy from logits is $\mathrm{LSE}(x) - x_{\text{target}}$.

**Dependencies:** Python ≥ 3.10, PyTorch ≥ 2.0 (CPU is fine).

```python
import torch
import torch.nn.functional as F


def logsumexp_naive(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
    return x.exp().sum(dim=dim).log()          # overflows for x > ~88.7 (fp32)


def softmax_naive(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
    e = x.exp()                                # inf / inf = nan
    return e / e.sum(dim=dim, keepdim=True)


def logsumexp_stable(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
    m = x.amax(dim=dim, keepdim=True)
    # Guard fully-masked rows (all -inf, e.g. attention masks):
    # otherwise (-inf) - (-inf) = nan below. With m=0 the result is a clean -inf.
    m = torch.where(torch.isfinite(m), m, torch.zeros_like(m))
    # Accumulate the reduction in fp32 even for bf16/fp16 inputs.
    s = (x - m).float().exp().sum(dim=dim)
    return (s.log() + m.squeeze(dim).float()).to(x.dtype)


def log_softmax_stable(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
    return x - logsumexp_stable(x, dim=dim).unsqueeze(dim)


def cross_entropy_from_logits(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    # CE = LSE(x) - x_target. Never softmax() then log().
    picked = logits.gather(-1, target.unsqueeze(-1)).squeeze(-1)
    return logsumexp_stable(logits, dim=-1) - picked


def softplus_stable(x: torch.Tensor) -> torch.Tensor:
    # log(1 + exp(x)) = max(x, 0) + log1p(exp(-|x|)) — branchless, exact in both tails.
    return x.clamp_min(0) + torch.log1p((-x.abs()).exp())


if __name__ == "__main__":
    # Logits of ~1000 happen in real life: unscaled scores, a missing
    # 1/sqrt(d) in attention, a reward-model head gone hot.
    logits = torch.tensor([[1000.0, 999.0, 0.0]])

    print("naive  LSE :", logsumexp_naive(logits).item())           # inf
    print("stable LSE :", logsumexp_stable(logits).item())          # 1000.3133
    print("torch  LSE :", torch.logsumexp(logits, dim=-1).item())   # 1000.3133

    print("naive  log-softmax:", softmax_naive(logits).log())       # all nan
    print("stable log-softmax:", log_softmax_stable(logits))
    print("torch  log-softmax:", F.log_softmax(logits, dim=-1))

    target = torch.tensor([1])
    print("stable CE :", cross_entropy_from_logits(logits, target).item())  # 1.3133
    print("torch  CE :", F.cross_entropy(logits, target).item())            # 1.3133

    # Underflow side: exp(-105) = 2.5e-46 is below fp32's smallest subnormal
    # (~1.4e-45), so the naive path forms p=0 and then log(0) = -inf.
    tiny = torch.tensor([[0.0, -105.0]])
    print("naive  underflow:", softmax_naive(tiny).log())           # [0, -inf]
    print("stable underflow:", log_softmax_stable(tiny))            # [0, -105]

    # Fully-masked attention row: must be -inf, not nan.
    masked = torch.full((1, 4), float("-inf"))
    print("masked row LSE:", logsumexp_stable(masked).item())       # -inf

    # Naive softplus: exp(100) = 2.7e43 > fp32 max 3.4e38 -> inf.
    xs = torch.tensor([-100.0, 0.0, 100.0])
    print("stable softplus:", softplus_stable(xs))                  # [0, 0.6931, 100]
```

**Expected output** (fp32; trailing digits may vary in the last ulp):

```text
naive  LSE : inf
stable LSE : 1000.313232421875
torch  LSE : 1000.313232421875
naive  log-softmax: tensor([[nan, nan, nan]])
stable log-softmax: tensor([[-3.1326e-01, -1.3133e+00, -1.0003e+03]])
torch  log-softmax: tensor([[-3.1326e-01, -1.3133e+00, -1.0003e+03]])
stable CE : 1.313232421875
torch  CE : 1.313232421875
naive  underflow: tensor([[0., -inf]])
stable underflow: tensor([[   0., -105.]])
masked row LSE: -inf
stable softplus: tensor([  0.0000,   0.6931, 100.0000])
```

Exact reference values: $\mathrm{LSE}([1000, 999, 0]) = 1000 + \log(1 + e^{-1} + e^{-1000}) = 1000.31326\ldots$, and CE against the 999 logit is $1.31326\ldots$

## Why it's written this way

1. **Subtract the max, not the mean.** Only the max guarantees every shifted exponent is $\le 0$. A mean shift still overflows once the spread of logits passes ~88 in fp32. The shift fixes underflow too: the stable path returns $-105$ where the naive one returns $-\inf$, because log-space can hold magnitudes down to roughly $e^{-10^{38}}$ and probabilities can't. It's the top entry in [[Gotchas - Numerical Stability]].
2. **Guard the all-`-inf` row.** Every [[Concept - Attention Mechanism]] implementation masks with $-\infty$ before its row-softmax. If a row is *entirely* masked (padding, causal edge cases), the unguarded version computes $(-\infty) - (-\infty) = \mathrm{NaN}$, and that NaN poisons every gradient through [[Concept - Softmax]]. The `torch.where` costs nothing and turns the bad row into a clean $-\infty$.
3. **Accumulate in fp32.** bf16 has 7 mantissa bits (machine epsilon $\approx 7.8\times10^{-3}$). Sum a 128K-vocabulary row of $\le 1$ terms in bf16 and the tail disappears. Fused log-softmax/cross-entropy kernels do the same `.float()` upcast before the reduction internally. A streaming form of this identity (online softmax) is the core of [[Deep Dive - FlashAttention]].
4. **Never materialize probabilities.** `cross_entropy_from_logits` goes straight from logits to loss. The branchless `softplus` uses `log1p` so small arguments keep full relative precision (`log(1 + eps)` rounds to `0`, `log1p(eps)` returns `eps`). Anything downstream that samples (see [[Concept - Sampling and Decoding Parameters]]) should also get log-probs, not probs that were exponentiated and logged again.

## Connections

- [[Concept - Entropy and Cross-Entropy]] — the loss this code computes; $\mathrm{CE} = \mathrm{LSE}(x) - x_{\text{target}}$ is that note's "always compute from logits" rule made concrete.
- [[Gotchas - Numerical Stability]] — LSE is the fix for the #1 gotcha in that catalog (softmax/exp overflow); read it for the sibling failures (cancellation, log(0), fp16 range).
- [[Concept - Floating Point for Deep Learning]] — the 88.7/11.09 overflow thresholds and the fp32-accumulation rule come straight from each format's exponent and mantissa budget.
- [[Concept - Softmax]] — production softmax and log-softmax layers are this trick fused into one kernel; the gradient simplification `softmax(z) - onehot` only holds if you compute in log-space.
- [[Concept - Attention Mechanism]] — attention is a masked row-softmax over scores; the all-`-inf` row guard here is the padding/causal-mask edge case every implementation must handle.
- [[Deep Dive - FlashAttention]] — its online softmax is this identity computed streamingly, rescaling the running sum as a new block max arrives.
- [[Concept - Sampling and Decoding Parameters]] — temperature, top-p, and repetition penalties all operate on logits/log-probs; leaving log-space early reintroduces the underflow this snippet kills.

## Sources

- Blanchard, Higham & Higham (2021) — "Accurately Computing the Log-Sum-Exp and Softmax Functions." Formal error analysis showing the max-shifted forms are accurate to within a few ulps.
- Milakov & Gimelshein (2018) — "Online normalizer calculation for softmax." The streaming one-pass version of this identity; the direct ancestor of FlashAttention's softmax.
