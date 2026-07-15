---
tags: [gotchas, domain/foundations, level/advanced]
aliases: [NaN debugging, numerical pitfalls, float bugs]
summary: "How floating-point arithmetic silently corrupts a run — overflow, cancellation, log(0), flushed gradients — and how to catch each early."
---

# Gotchas - Numerical Stability

Every entry here is a way [[Concept - Floating Point for Deep Learning]] betrays you without raising an exception. Ordered by how much cumulative pain each causes in practice. The recurring theme: floating-point error is *silent* — the run keeps going, the numbers just stop meaning anything. Format-specific constants (max values, epsilons, subnormal ranges) live in [[Reference - Floating Point Formats]].

## 1. Loss goes NaN a few steps after logits start growing

**Symptom:** Training proceeds normally, logit magnitudes creep up, then the loss prints `nan` and never recovers. Often blamed on the learning rate; often actually the [[Concept - Softmax]].
**Cause:** `exp(x)` overflows to `inf` at $x \gtrsim 88.7$ in fp32 ($\ln(3.4 \times 10^{38})$) and at $x \gtrsim 11.09$ in fp16 ($\ln 65504$). One oversized logit makes the softmax numerator `inf`, `inf/inf = nan`, and the NaN backpropagates into every parameter in one step.
**Fix:** Never exponentiate raw logits. Subtract the row max first — the log-sum-exp identity is algebraically exact, so this costs nothing. Runnable version: [[Snippet - The Log-Sum-Exp Trick]]. Compute cross-entropy *from logits* (`F.cross_entropy`, `log_softmax`), never `log(softmax(x))`.
**Detection:** Assert `torch.isfinite(logits).all()` on a schedule; log `logits.abs().max()` — it trends up for many steps before the blow-up, giving you early warning. `torch.autograd.set_detect_anomaly(True)` localizes the producing op (at 2–10× slowdown; use for the repro, not for the run).

## 2. Variance comes out negative, then sqrt turns it into NaN

**Symptom:** A normalization layer, running statistic, or metric produces NaN on data that looks perfectly healthy — typically data with a large mean and small spread.
**Cause:** Catastrophic cancellation. The one-pass formula $\mathrm{Var}(x) = E[x^2] - (E[x])^2$ subtracts two nearly equal large numbers. If $|\mu| \approx 100$ and $\sigma \approx 0.01$, the true variance ($10^{-4}$) is ~$10^{8}$ times smaller than the terms being subtracted — in fp32 (eps $\approx 1.19 \times 10^{-7}$) essentially every significant bit cancels, and rounding can leave a *negative* result. `sqrt` of that is NaN.
**Fix:** Welford's online algorithm (Welford 1962) or a two-pass computation (mean first, then $E[(x-\mu)^2]$). Guard `sqrt(max(var, 0))` as a last line of defense, but treat a triggered guard as a bug report, not a fix.
**Detection:** Unit-test statistics code with adversarial inputs: `x = 1e4 + torch.randn(n) * 1e-2`. The one-pass formula fails this test in fp32; Welford passes.

## 3. `-inf` loss from log(0), or NaN from sqrt of a slightly negative number

**Symptom:** Loss is `-inf` or `nan` on specific batches; eval crashes on one example; a mixture-model or attention-mask path dies intermittently.
**Cause:** A probability that underflowed to exactly 0.0 fed into `log` ($\log 0 = -\infty$), or a variance that cancellation pushed to $-10^{-9}$ fed into `sqrt`. Common carriers: clamped probabilities, `log(1 - p)` when $p \to 1$, masked softmax rows where every entry is $-\infty$ (the row sums to 0).
**Fix:** Stay in log-space end to end — compute $\log p$ directly from logits and never materialize $p$. Use `log1p` for $\log(1+x)$ with small $x$. For masked rows, handle the all-masked case explicitly rather than relying on the arithmetic to work out.
**Detection:** Check the *inputs* to every `log`, `sqrt`, and `rsqrt` in custom code. An assertion `(p > 0).all()` before a `log` is cheap and names the failing batch.

## 4. Normalization blows up on low-variance activations — eps in the wrong place

**Symptom:** Activations explode out of a [[Concept - RMSNorm and LayerNorm]] layer, but only for some inputs (padding-heavy sequences, dead channels, embedding rows that are nearly constant). Or: a ported model is subtly wrong — logits differ from the reference by ~1e-3 everywhere.
**Cause:** $1/\sqrt{\mathrm{var} + \epsilon}$ is exquisitely sensitive to $\epsilon$ when the variance is tiny. Too small an $\epsilon$ turns a near-constant activation vector into a huge output. Separately, $\frac{1}{\sqrt{\mathrm{var} + \epsilon}}$ and $\frac{1}{\sqrt{\mathrm{var}} + \epsilon}$ are *different functions* — both appear in the wild, and porting weights between implementations that disagree yields a model that is almost-but-not-quite right.
**Fix:** Standard $\epsilon$ is $10^{-5}$ to $10^{-6}$ (PyTorch LayerNorm defaults to 1e-5; Llama-family RMSNorm uses 1e-5/1e-6 depending on generation — copy the reference model's value exactly). Keep the eps *inside* the sqrt unless matching an implementation that does otherwise.
**Detection:** Monitor per-layer activation RMS; a layer whose output norm spikes on specific inputs is an eps problem. When porting, diff intermediate activations against the reference, not just final logits.

## 5. fp16 training silently stops learning, or dies at 65504

**Symptom:** In fp16 [[Concept - Mixed Precision Training]]: loss plateaus early (gradients flushed to zero) or hits NaN mid-run (activation overflow). The same code in fp32 works.
**Cause:** fp16 has 5 exponent bits: max finite 65504, min normal $6.1 \times 10^{-5}$, subnormals down to $\sim 6 \times 10^{-8}$ (see [[Concept - Subnormal Numbers and Gradual Underflow]] for why the subnormal band may itself be flushed to zero by FTZ hardware modes). Real gradient distributions sit substantially below $6 \times 10^{-5}$; real attention logits and losses exceed 65504.
**Fix:** Loss scaling — multiply the loss by $S$ (typically $2^{10}$–$2^{16}$) before backward, unscale before the optimizer step; dynamic scaling automates the tuning. Full history and mechanism: [[Lore - Loss Scaling and the fp16 Underflow Crisis]]. Or sidestep the entire class by using bf16 ([[Breakdown - bfloat16]]), which is why almost everyone did.
**Detection:** Dynamic loss scalers keep an inf/NaN-gradient counter and a current-scale value — log both. A scale that keeps halving means recurring overflow; a gradient-norm curve that goes suspiciously quiet means underflow.

## 6. Sums lose precision at scale and differ run-to-run

**Symptom:** A large reduction (mean over a big batch, gradient all-reduce, sum over vocab) is inaccurate versus a fp64 reference, and produces *different bits* across identical reruns or after a batch-size change.
**Cause:** Floating-point addition is not associative: $(a+b)+c \neq a+(b+c)$ under rounding. Naive left-to-right summation of $N$ values accumulates error up to $O(N \cdot \epsilon)$ worst case, $O(\sqrt{N}\,\epsilon)$ typically; in bf16 (eps $\approx 7.8 \times 10^{-3}$) a running sum stops absorbing new terms once the accumulator is ~128× larger than the increments. Parallel reductions sum in scheduler-dependent order, so the rounding — and the answer — changes per run. Full story: [[Lore - The Nondeterminism of Floating-Point Reductions]].
**Fix:** Accumulate in fp32 (or fp64 for metrics that matter); use pairwise/tree reduction ($O(\log N \cdot \epsilon)$ error) or Kahan compensated summation ($O(\epsilon)$, at 4× the adds) for long serial sums.
**Detection:** Compare the reduction against a fp64 reference on a fixed input. If two identical runs disagree in the last bits, you have an order-dependent reduction — decide whether you care before it shows up in a repro attempt.

## 7. One NaN poisons the whole model within a step

**Symptom:** *Everything* is NaN — every weight, every activation — and the last checkpoint before it happened looks fine.
**Cause:** NaN is absorbing: any op touching a NaN emits NaN, and [[Concept - Backpropagation]] spreads one NaN activation into every upstream gradient in a single backward pass. One bad op (an `inf - inf`, a `0/0`, gotchas 1–5 above) converts the model to garbage in one optimizer step. Bonus trap: `NaN != NaN`, so naive equality checks, sorting, and comparisons silently misbehave.
**Fix:** There is no fix after the fact — restore from checkpoint. The engineering is in *containment*: finite-value checks on the loss before stepping (skip the step if non-finite, as dynamic loss scalers do), frequent checkpoints, and gradient clipping to bound the blast radius of a near-overflow.
**Detection:** Bisect the forward pass with `torch.isfinite` hooks on module outputs to find the first producing op; anomaly mode does this automatically for backward. The op that *produces* the NaN is usually several layers upstream of where you first observe it.

## 8. The bf16 model is fine but its statistics are garbage

**Symptom:** Training in bf16 is stable, yet the perplexity metric drifts from a fp32 eval of the same checkpoint; the softmax over a 128k vocab misbehaves; a mean over millions of tokens is visibly wrong.
**Cause:** bf16 has ~2–3 decimal digits of precision (7 mantissa bits). Any long reduction — softmax denominator, LayerNorm statistics, the loss mean, a corpus-level metric — executed natively in bf16 loses the tail of the sum (gotcha 6 at its nastiest). Frameworks keep the *matmuls* in bf16 but the *reductions* in fp32 for exactly this reason; custom kernels and hand-rolled metrics often forget.
**Fix:** All reductions in fp32, even in a bf16 model: softmax, norm statistics, loss computation, metric accumulators. This is the discipline FlashAttention-style kernels follow internally (bf16 inputs, fp32 running max and sum).
**Detection:** Run the metric path once in fp64 and diff. If a "quality regression" appears only after a kernel or eval-harness change, suspect the reduction dtype before the model.

## Connections

- [[Snippet - The Log-Sum-Exp Trick]] — the runnable fix for gotchas 1 and 3; the single most reused stability technique in ML.
- [[Concept - Floating Point for Deep Learning]] — the representation-level mechanism (range vs precision, relative spacing) every gotcha here reduces to.
- [[Reference - Floating Point Formats]] — the exact constants (max, min normal, eps, subnormal floor) you need when diagnosing which threshold was crossed.
- [[Concept - Subnormal Numbers and Gradual Underflow]] — the arcana beneath gotcha 5: the band where fp16 gradients die, and the FTZ/DAZ modes that kill them faster.
- [[Lore - The Nondeterminism of Floating-Point Reductions]] — gotcha 6 expanded into its war stories: why identical runs differ bit-for-bit and what determinism costs.
- [[Lore - Loss Scaling and the fp16 Underflow Crisis]] — the historical episode where gotcha 5 nearly killed low-precision training, and the invention that saved it.
- [[Breakdown - bfloat16]] — the format designed to delete gotcha 5 wholesale by spending bits on exponent range.
- [[Concept - RMSNorm and LayerNorm]] — the layer where gotcha 4's eps-placement trap lives; porting mismatches originate here.
- [[Concept - Mixed Precision Training]] — the training recipe that institutionalizes the fixes: low-precision matmuls, fp32 reductions, master weights, loss scaling.
- [[Concept - Softmax]] — the operation implicated in gotchas 1, 3, and 8; its stable form is the canonical example of this whole catalog.
- [[Concept - Backpropagation]] — the propagation machinery that turns one bad value into a fully poisoned model (gotcha 7).

## Sources

- Goldberg (1991) — *What Every Computer Scientist Should Know About Floating-Point Arithmetic.* The canonical treatment of rounding, cancellation, and why these bugs are silent.
- Higham (2002) — *Accuracy and Stability of Numerical Algorithms.* Error bounds for summation and variance algorithms; the source for the $O(N\epsilon)$ vs $O(\log N \cdot \epsilon)$ claims.
- Welford (1962) — *Note on a method for calculating corrected sums of squares and products.* The online variance algorithm that fixes gotcha 2.
- Kahan (1965) — *Further remarks on reducing truncation errors.* Compensated summation.
- Micikevicius et al. (2017) — *Mixed Precision Training.* Documents the fp16 gradient-underflow measurements and the loss-scaling remedy behind gotcha 5.
