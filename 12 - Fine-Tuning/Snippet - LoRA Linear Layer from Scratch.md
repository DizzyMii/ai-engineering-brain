---
tags: [snippet, domain/fine-tuning, level/advanced]
aliases: [LoRALinear, LoRA from scratch]
summary: "Minimal PyTorch LoRA-wrapped Linear: zero-init identity start, alpha/r scaling, merge/unmerge for zero serving cost."
---
# Snippet - LoRA Linear Layer from Scratch

> **What it does:** wraps a frozen `nn.Linear` with a trainable rank-$r$ update $W' = W + \frac{\alpha}{r}BA$, then folds it back in with `merge()` to prove LoRA has zero inference cost. **Dependencies:** `torch>=2.1` (tested on 2.3; CPU or CUDA), Python 3.10+. **Expected output:** a trainable-param line (~0.78% for a 4096×4096 layer at $r=16$) and a before/after-merge max error near `1e-6`.

The whole point of [[Deep Dive - LoRA]] fits in ~40 lines of PyTorch. If you can write this from memory you understand the three things that trip people up in real configs: why the adapter starts as an exact no-op, why `alpha/r` is *not* the learning rate, and why merging makes serving free.

```python
import math
import torch
import torch.nn as nn


class LoRALinear(nn.Module):
    """Frozen nn.Linear + trainable low-rank update: W' = W + (alpha/r) * B @ A."""

    def __init__(self, base: nn.Linear, r: int = 8, alpha: int = 16, dropout: float = 0.0):
        super().__init__()
        self.base = base
        for p in self.base.parameters():
            p.requires_grad_(False)                    # freeze W (and bias): no grad, no optimizer state

        in_f, out_f = base.in_features, base.out_features
        self.scaling = alpha / r                       # a fixed update multiplier, NOT the optimizer LR
        self.dropout = nn.Dropout(dropout)

        self.A = nn.Parameter(torch.empty(r, in_f))    # down-projection (r, in)
        self.B = nn.Parameter(torch.zeros(out_f, r))   # up-projection (out, r) == 0  ->  dW = 0 at step 0
        nn.init.kaiming_uniform_(self.A, a=math.sqrt(5))  # same init peft / the paper use for A
        self.merged = False

    def forward(self, x):
        out = self.base(x)                             # frozen W x (+ b)
        if self.merged:
            return out                                 # delta already folded into base.weight
        delta = (self.dropout(x) @ self.A.T) @ self.B.T   # dropout on the INPUT to A
        return out + delta * self.scaling

    @torch.no_grad()
    def merge(self):
        if not self.merged:
            self.base.weight += (self.B @ self.A) * self.scaling   # fold dW into W
            self.merged = True

    @torch.no_grad()
    def unmerge(self):
        if self.merged:
            self.base.weight -= (self.B @ self.A) * self.scaling
            self.merged = False


if __name__ == "__main__":
    torch.manual_seed(0)
    base = nn.Linear(4096, 4096, bias=False)
    layer = LoRALinear(base, r=16, alpha=32)           # alpha = 2r convention

    trainable = sum(p.numel() for p in layer.parameters() if p.requires_grad)
    total = sum(p.numel() for p in layer.parameters())
    print(f"trainable: {trainable:,} / {total:,}  ({100 * trainable / total:.3f}%)")

    x = torch.randn(2, 128, 4096)
    # B = 0 -> the wrapped layer is EXACTLY the frozen base at init. This is the correctness check.
    assert torch.equal(layer(x), base(x)), "LoRA must be a no-op before training"

    with torch.no_grad():                              # fake a trained adapter so B != 0
        layer.B.normal_(0, 0.02)

    y_before = layer(x)
    layer.merge()
    y_after = layer(x)
    max_err = (y_before - y_after).abs().max().item()
    print(f"max |unmerged - merged|: {max_err:.2e}")   # only float rounding, ~1e-6
    assert max_err < 1e-4
```

Running it prints roughly:

```
trainable: 131,072 / 16,908,288  (0.775%)
max |unmerged - merged|: 3.81e-06
```

Only $r(d_{in}+d_{out}) = 16 \times (4096+4096) = 131{,}072$ parameters are optimized instead of the $d_{in}d_{out} = 16.8\text{M}$ of the dense layer — the [[Concept - Matrix Multiplication as the Atom of Deep Learning|matmul]] $BA$ reconstructs a full-size $\Delta W$ from two thin factors, and the optimizer only ever sees the factors.

## Why it's written this way

- **`B = 0`, `A` = Kaiming — the adapter is an identity at step 0.** Because $\Delta W = BA = 0$ initially, training *starts as exactly the pretrained function*; there is no random perturbation to first recover from. The `torch.equal(layer(x), base(x))` assertion is not decoration — it is the one invariant that catches a botched init (a common mistake is "helpfully" initializing `B` from a normal, which silently injects noise into every forward pass on step 0 and mimics a bad learning rate). Zeroing `A` instead of `B` is mathematically equivalent at init but then the *first* gradient into `B` is identically zero, so the convention is to zero `B`.
- **`scaling = alpha/r` is kept out of the optimizer.** It is a fixed multiplier applied in the forward pass, deliberately separate from the learning rate. This is the single most misunderstood line in LoRA: changing `r` while copying someone else's `alpha` silently rescales every update by $\alpha(1/r_\text{new} - 1/r_\text{old})$, which reads as "my LoRA won't learn" or "my LoRA exploded" — a whole class of bugs catalogued in [[Gotchas - LoRA Fine-Tuning]].
- **Dropout is applied to the *input* of `A`, not the output of the branch.** Per Hu et al. (2021), regularizing $x$ before the rank-$r$ bottleneck is what keeps the adapter from memorizing; dropping the delta *after* the projection would instead just stochastically scale the whole update, a different and weaker regularizer.
- **`merge()` folds $BA$ into `W`, so serving is free.** After merge, the forward is a single dense matmul identical in cost to the base model — this is *the* reason reparameterization LoRA beat sequential adapters for large-scale serving. The catch, made concrete in [[Snippet - QLoRA Fine-Tune Configuration]] and the gotchas note: merging into a **4-bit** base re-rounds $W+\Delta W$ back to NF4 and loses accuracy, so you must dequantize to fp16 *before* merging.

This module is what actually plugs into [[Concept - The Training Loop]]: swap the model's `nn.Linear`s for `LoRALinear`, hand only the `A`/`B` parameters to the optimizer, and the rest of the loop is unchanged. What no amount of clever init or scaling fixes is the intrinsic-rank ceiling in [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — a rank-16 update cannot match full fine-tuning on a large distribution shift no matter how you initialize it.

## Connections
- [[Deep Dive - LoRA]] — the full mechanism (rank/alpha, target modules, initialization, evolution) that this snippet distills to runnable code.
- [[Concept - Matrix Multiplication as the Atom of Deep Learning]] — the $BA$ product is exactly why a rank-$r$ update costs $r(d_{in}+d_{out})$ params, not $d_{in}d_{out}$.
- [[Concept - The Training Loop]] — where this module drops in; only `A`/`B` are registered with the optimizer, the base is frozen.
- [[Snippet - QLoRA Fine-Tune Configuration]] — the production `peft`/`bitsandbytes` version of the same idea, with the 4-bit merge caveat.
- [[Gotchas - LoRA Fine-Tuning]] — the alpha-scaling and merge-precision traps this code is written to make obvious.
- [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — the low-rank ceiling this minimal layer inherits and cannot code its way out of.

## Sources
- Hu et al. (2021) — *LoRA: Low-Rank Adaptation of Large Language Models.* Defines the $B=0$ init, `alpha/r` scaling, dropout-on-input, and the mergeable-at-inference property implemented here.
