---
tags: [lore, domain/foundations, level/unicorn]
aliases: [FP nondeterminism, reduction nondeterminism, bitwise reproducibility, non-associative addition]
summary: "Identical code on identical hardware doesn't reproduce bit-for-bit — because parallel float reductions sum in scheduler-dependent order."
---

# Lore - The Nondeterminism of Floating-Point Reductions

> **What happened / The lesson / Evidence status.** Why "I ran the same script twice and got different numbers" isn't a bug report. It's floating-point arithmetic doing what the spec says.

## What happened

Every few months a new engineer files the same ticket. *"I set the seed. I fixed the data order. Same GPU, same container, same commit. The loss curves still diverge after a few hundred steps. Something is corrupting my run."* Nothing is corrupting the run. The reduction order is.

The mechanism fits in one line: **floating-point addition is not associative.** Under round-to-nearest, $(a+b)+c \neq a+(b+c)$ in general, because each `+` rounds its result to the nearest representable value and the two groupings round at different points. Classic fp32 example: $(1.0 + 10^{-8}) + (-1.0)$ rounds the $10^{-8}$ away and gives $0$, while $1.0 + (10^{-8} + (-1.0))$ keeps it and gives $\approx 10^{-8}$. A sum of a million numbers has a million-way choice of association, and each one can land on different bits. It's the same [[Gotchas - Numerical Stability|catastrophic-cancellation and summation-error]] family that haunts variance and softmax.

Now run that sum on a GPU. A reduction over 10,000 elements isn't a sequential loop. Thousands of threads accumulate in a tree whose *shape and finishing order depend on the runtime scheduler.* Two launches of the same kernel on the same inputs interleave their partial sums differently, round differently, and hand back different bits. The seed never touched the reduction.

The GPU makes this worse in a few specific places:

- **`atomicAdd`.** Any op that scatters gradients through atomic accumulation (`scatter_add`, `index_add`, embedding-table backward, `bincount`, some pooling and convolution backward kernels) sums contributions in *hardware-arbitrary* order. Same math, different rounding, every launch.
- **cuDNN autotuning.** With `torch.backends.cudnn.benchmark = True`, cuDNN times several algorithms on the first call and keeps the fastest. A different pick (or a different input shape) means a numerically different kernel. By design it's *faster* and *less reproducible*.
- **Collective order.** Across data-parallel ranks, the order in which partial gradients arrive and combine in an all-reduce is itself nondeterministic (see [[Concept - All-Reduce and Collective Operations]]). Multi-GPU runs stack that jitter on top of the single-GPU kind.

Then there are the footguns that make a reproducible pipeline non-reproducible without anyone editing the model:

- **TF32.** When the A100/Ampere generation landed (2020), NVIDIA made TF32 (10 mantissa bits, ~$10^{-3}$ relative precision) the *default* math mode for fp32 matmuls and convolutions. Overnight, people comparing new runs to old ones saw results shift by ~$10^{-3}$ and assumed they'd introduced a bug. PyTorch later flipped the matmul default back to full fp32 (1.12), which moved the numbers *again* for anyone who had adapted. When "the numbers moved after an upgrade", check `torch.backends.cuda.matmul.allow_tf32` and `torch.backends.cudnn.allow_tf32` first.
- **`-ffast-math` / `-Ofast`.** These let the compiler *reassociate* floating-point sums (assuming an associativity that doesn't hold) and silently turn on flush-to-zero for [[Concept - Subnormal Numbers and Gradual Underflow|subnormals]]. That can change the *stability* of a computation, beyond the last bit.

Every engineer eventually hits this one: **setting a seed does not make CUDA reductions deterministic.** The seed fixes the random *draws*. It does nothing about the *order* in which the resulting floats get added.

## The lesson

Bitwise reproducibility is something you choose and pay for. You don't get it by default.

Mechanically, the nondeterminism comes from parallelism exposing the *order-dependence of a lossy rounding operation*; the algorithm itself isn't random. Fix the order and you fix the bits. PyTorch gives you the switches. `torch.use_deterministic_algorithms(True)` forces deterministic kernel choices (and *errors out* on ops like `atomicAdd`-based scatter that have no deterministic implementation). `torch.backends.cudnn.deterministic = True` with `benchmark = False` pins cuDNN. `CUBLAS_WORKSPACE_CONFIG=:4096:8` gives cuBLAS a fixed workspace so its reductions don't vary. The cost is real: deterministic kernels are slower (sometimes materially), some ops have *no* deterministic variant, and you lose autotuning.

So the decision is: **does this computation need to be bit-identical, or just statistically identical?** For training it's almost always *statistically*. The reduction jitter is orders of magnitude smaller than [[Concept - Mixed Precision Training|the noise SGD already injects]] through minibatch sampling and bf16 rounding. A healthy run is *robust* to it, and forcing determinism only buys a slower run. So "we changed the batch size and the loss curve moved" isn't alarming. A different batch size means a different reduction tree, a $\sim 10^{-6}$ divergence per step, and chaotic amplification of that tiny seed over thousands of steps. The curves separate; the *model* is fine.

Sometimes bit-identity is the requirement, and then you *must* pay:

- **Debugging.** You can't bisect "where did the NaN come from" if the forward pass isn't reproducible.
- **Regression tests.** A golden-output test that accepts only exact equality will flap forever without determinism.
- **Eval reproducibility.** Publishing a benchmark number others must reproduce to more than 3 decimals (the territory of [[Concept - Statistical Rigor in Model Evaluation]]) needs a pinned numerical stack. It's also why eval reports should quote a CI, not a bare decimal.
- **Audit and compliance.** Security review and provenance ([[Concept - LLM Observability and Tracing]]) sometimes require that a logged output be re-derivable bit for bit from logged inputs.

The general rule: **treat "same numbers twice" as a feature you explicitly enable. Treat anything that silently reassociates floats (fast-math, autotuning, a new default like TF32) as a drift source to pin down before it costs you a week.**

## Evidence status

- **Verified.** Non-associativity of IEEE-754 addition, `atomicAdd` ordering, cuDNN autotuning behavior, the determinism flags and their costs, and the TF32 default change are all documented in the IEEE-754 standard, the PyTorch reproducibility notes and NVIDIA's cuDNN/cuBLAS docs (and codified in the community `framework-determinism` work). Solid.
- **Well-attested engineering folklore.** The specific anecdotes ("changed batch size, loss curve moved", "can't match the paper past 3 decimals", "two runs diverged from a bit-identical checkpoint") show up across countless issue trackers and post-mortems, including the precision-and-reproducibility pain logged in real large runs like [[Lore - The OPT-175B Logbook]]. Individually unsourced, collectively ubiquitous, all explained by the one mechanism above. Labeled as folklore.

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
