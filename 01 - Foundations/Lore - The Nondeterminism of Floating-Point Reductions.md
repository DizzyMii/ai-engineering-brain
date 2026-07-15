---
tags: [lore, domain/foundations, level/unicorn]
aliases: [FP nondeterminism, reduction nondeterminism, bitwise reproducibility, non-associative addition]
summary: "Identical code on identical hardware doesn't reproduce bit-for-bit — because parallel float reductions sum in scheduler-dependent order."
---

# Lore - The Nondeterminism of Floating-Point Reductions

> **What happened / The lesson / Evidence status.** The story of why "I ran the exact same script twice and got different numbers" is not a bug report — it is floating-point arithmetic behaving exactly as specified.

## What happened

Every few months a new engineer files the same ticket. *"I set the seed. I fixed the data order. Same GPU, same container, same commit. The loss curves still diverge after a few hundred steps. Something is corrupting my run."* Nothing is corrupting the run. The reduction order is.

The mechanism is one line long: **floating-point addition is not associative.** Under round-to-nearest, $(a+b)+c \neq a+(b+c)$ in general, because each `+` rounds its result to the nearest representable value and the two groupings round at different points. Classic example in fp32: $(1.0 + 10^{-8}) + (-1.0)$ rounds the $10^{-8}$ away and gives $0$, while $1.0 + (10^{-8} + (-1.0))$ keeps it and gives $\approx 10^{-8}$. A sum of a million numbers has a million-way choice of association, and every association can land on different bits — this is the same [[Gotchas - Numerical Stability|catastrophic-cancellation and summation-error]] family that haunts variance and softmax.

Now put that sum on a GPU. A reduction over 10,000 elements is not a sequential loop; it is thousands of threads accumulating in a tree whose *shape and finishing order depend on the runtime scheduler.* Two launches of the identical kernel on identical inputs interleave their partial sums differently, round differently, and hand you different bits. The seed never entered into it — it never touched the reduction.

The GPU makes this worse in specific, nameable places:

- **`atomicAdd`.** Any op that scatters gradients through atomic accumulation — `scatter_add`, `index_add`, embedding-table backward, `bincount`, some pooling and convolution backward kernels — sums contributions in *hardware-arbitrary* order. Same math, different rounding, every launch.
- **cuDNN autotuning.** With `torch.backends.cudnn.benchmark = True`, cuDNN times several algorithms on the first call and picks the fastest; a different pick (or a different input shape) means a numerically different kernel. It is *faster* and *less reproducible* by design.
- **Collective order.** Across data-parallel ranks, the order in which partial gradients arrive and combine in an all-reduce is itself nondeterministic — see [[Concept - All-Reduce and Collective Operations]] — so multi-GPU runs stack another layer of reduction jitter on top of the single-GPU one.

Then there are the *silent-change footguns*, the ones that turn a reproducible pipeline non-reproducible without anyone editing the model:

- **TF32.** When the A100/Ampere generation landed (2020), NVIDIA made TF32 (10 mantissa bits, ~$10^{-3}$ relative precision) the *default* math mode for fp32 matmuls and convolutions. Overnight, people comparing new runs to old ones saw results shift by ~$10^{-3}$ and assumed they had introduced a bug. PyTorch later flipped the matmul default back to full fp32 (1.12), which shifted numbers *again* for anyone who had adapted. The knobs — `torch.backends.cuda.matmul.allow_tf32`, `torch.backends.cudnn.allow_tf32` — are the ones to check first when "the numbers moved after an upgrade."
- **`-ffast-math` / `-Ofast`.** These let the compiler *reassociate* floating-point sums (assuming associativity that does not hold) and quietly enable flush-to-zero of [[Concept - Subnormal Numbers and Gradual Underflow|subnormals]]. That can change not just the last bit but the *stability* of a computation.

And the punchline every engineer eventually meets: **setting a seed does not make CUDA reductions deterministic.** The seed fixes the random *draws*; it does nothing about the *order* in which the resulting floats get added.

## The lesson

Bitwise reproducibility is a *choice you pay for*, not a default you inherit.

The mechanistic takeaway: nondeterminism here is not randomness in the algorithm — it is *order-dependence of a rounding-lossy operation* exposed by parallelism. Fix the order and you fix the bits. PyTorch exposes exactly that: `torch.use_deterministic_algorithms(True)` forces deterministic kernel choices (and *errors out* on ops like `atomicAdd`-based scatter that have no deterministic implementation), `torch.backends.cudnn.deterministic = True` with `benchmark = False` pins cuDNN, and `CUBLAS_WORKSPACE_CONFIG=:4096:8` gives cuBLAS a fixed workspace so its reductions don't vary. The cost is real: deterministic kernels are slower (sometimes materially), some ops have *no* deterministic variant at all, and you lose autotuning.

So the actual decision is: **does this computation need to be bit-identical, or just statistically identical?** For training, the answer is almost always *statistically*. This reduction jitter is orders of magnitude smaller than [[Concept - Mixed Precision Training|the noise SGD already injects]] through minibatch sampling and bf16 rounding; a healthy training run is *robust* to it, and forcing determinism buys you nothing but a slower run. That is why "we changed the batch size and the loss curve moved" is not alarming — a different batch size means a different reduction tree, a $\sim 10^{-6}$ divergence per step, and chaotic amplification of that tiny seed over thousands of steps. The curves separate; the *model* is fine.

But sometimes bit-identity is the requirement, and then you *must* pay:

- **Debugging.** Bisecting "where did the NaN come from" is impossible if the forward pass isn't reproducible.
- **Regression tests.** A golden-output test that tolerates only exact equality will flap forever without determinism.
- **Eval reproducibility.** Publishing a benchmark number others must reproduce to more than 3 decimals — the province of [[Concept - Statistical Rigor in Model Evaluation]] — needs a pinned numerical stack, which is also why eval reports should quote a CI, not a bare decimal.
- **Audit and compliance.** Security review and provenance ([[Concept - LLM Observability and Tracing]]) sometimes demand that a logged output be exactly re-derivable from logged inputs.

The general rule that falls out: **treat "same numbers twice" as a feature you explicitly enable, and treat any pipeline that silently reassociates floats (fast-math, autotuning, a new default like TF32) as a source of drift to pin down before it costs you a week.**

## Evidence status

- **Verified.** Non-associativity of IEEE-754 addition, `atomicAdd` ordering, cuDNN autotuning behavior, the determinism flags and their costs, and the TF32 default change are all documented in the IEEE-754 standard, the PyTorch reproducibility notes, and NVIDIA's cuDNN/cuBLAS docs (and codified in the community `framework-determinism` work). Solid.
- **Well-attested engineering folklore.** The specific anecdotes — "changed batch size, loss curve moved," "can't match the paper past 3 decimals," "two runs diverged from a bit-identical checkpoint" — are recounted across countless issue trackers and post-mortems, including precision-and-reproducibility pain logged in real large runs like [[Lore - The OPT-175B Logbook]]. Individually unsourced, collectively ubiquitous, and all explained by the one mechanism above. Labeled as folklore.

## Connections

- [[Gotchas - Numerical Stability]] — the parent catalog; reduction nondeterminism is the "summation is not associative" gotcha viewed as a reproducibility problem instead of an accuracy one.
- [[Concept - Floating Point for Deep Learning]] — the rounding model that makes association matter; why every `+` loses information.
- [[Concept - Subnormal Numbers and Gradual Underflow]] — fast-math's other silent effect (flush-to-zero) that changes results alongside reassociation.
- [[Concept - All-Reduce and Collective Operations]] — the multi-GPU layer where combine-order jitter compounds the single-device version.
- [[Concept - Mixed Precision Training]] — the reason the jitter usually doesn't matter: SGD's own noise dwarfs it.
- [[Concept - Statistical Rigor in Model Evaluation]] — why eval numbers need CIs and pinned stacks rather than trust in a reproduced decimal.
- [[Concept - LLM Observability and Tracing]] — where bit-exact reproducibility becomes an audit/provenance requirement rather than a nicety.
- [[Concept - Nondeterminism in LLM Inference]] — the same root cause on the serving side: batch-dependent reduction order makes a fixed prompt at temperature 0 return different tokens across batch sizes.
- [[Lore - The OPT-175B Logbook]] — a real training run whose logbook records the precision/reproducibility struggles this note explains.

## Sources

- IEEE 754-2008/2019 — the floating-point standard; defines round-to-nearest and, by omission of associativity, licenses this entire phenomenon.
- PyTorch Reproducibility documentation — `use_deterministic_algorithms`, `cudnn.deterministic/benchmark`, `CUBLAS_WORKSPACE_CONFIG`, and the explicit warning that seeds do not tame CUDA reductions.
- NVIDIA cuDNN/cuBLAS docs and the `framework-determinism` project (Riach et al.) — atomics, autotuning, and the practical recipe for deterministic GPU training.
