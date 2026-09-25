---
tags: [snippet, domain/architectures, level/advanced]
aliases: [MoE router snippet, top-2 gating code, sparse MoE layer from scratch]
summary: "Runnable top-2 token-choice MoE FFN layer: gate, softmax, renormalized top-2 selection, weighted combine, and an expert-load histogram."
---

# Snippet - Top-2 MoE Routing Layer

**What it does:** implements a dense-compute top-2 token-choice [[Concept - Mixture of Experts Architecture|MoE]] FFN layer: a linear gate, softmax, top-2 selection, renormalization of the selected weights, and a weighted combination of expert outputs. The routing math matches [[Breakdown - Mixtral 8x7B]]'s FFN sublayer, written as a reference "loop over every expert" instead of the scatter/gather dispatch [[Concept - MoE Inference and Expert Parallelism|production systems]] use for efficiency. It also logs a per-expert token-count histogram, since that's the first number to check whenever an MoE layer misbehaves.

**Dependencies:** `torch >= 2.0` (CPU is fine).

**Expected output** (seeded, `torch==2.x` CPU; exact counts can shift a little across major torch versions because the RNG stream isn't guaranteed stable, but the imbalance itself is the point, see [[Gotchas - Mixture of Experts]]):
```text
output shape: torch.Size([64, 32])
expert token counts: [12, 13, 15, 11, 18, 30, 17, 12]
load imbalance (max/mean): 1.88
```

```python
"""
Snippet - Top-2 MoE Routing Layer

A minimal, dense-compute (not scatter/gather) top-2 token-choice MoE FFN
layer: linear gate -> softmax -> top-2 -> renormalize -> weighted sum of
expert outputs. This is the reference math behind Concept - Mixture of
Experts Architecture and Breakdown - Mixtral 8x7B's FFN sublayer.
Production systems replace the "run every expert, mask the rest" loop
below with scatter/gather dispatch across expert-parallel devices (see
Concept - MoE Inference and Expert Parallelism) -- the math is identical,
only the compute layout changes.

Dependencies: torch>=2.0 (CPU is fine)
Expected output (seeded; counts can shift slightly across major torch
versions, the imbalance itself is the point -- there is no load-balance
loss in this snippet):
    output shape: torch.Size([64, 32])
    expert token counts: [12, 13, 15, 11, 18, 30, 17, 12]
    load imbalance (max/mean): 1.88
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class Expert(nn.Module):
    """One expert: a small FFN, structurally identical to a dense block's FFN."""

    def __init__(self, d_model: int, d_ff: int):
        super().__init__()
        self.w1 = nn.Linear(d_model, d_ff, bias=False)
        self.w2 = nn.Linear(d_ff, d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.w2(F.gelu(self.w1(x)))


class Top2MoE(nn.Module):
    def __init__(self, d_model: int, d_ff: int, n_experts: int):
        super().__init__()
        self.n_experts = n_experts
        self.gate = nn.Linear(d_model, n_experts, bias=False)
        self.experts = nn.ModuleList(Expert(d_model, d_ff) for _ in range(n_experts))

    def forward(self, x: torch.Tensor):
        # x: [tokens, d_model]. Gate stays in whatever precision x arrives
        # in here, but production code keeps this softmax in fp32 even in
        # a bf16 model -- see Gotchas - Mixture of Experts, gotcha 6.
        logits = self.gate(x)                              # [tokens, n_experts]
        gate_all = F.softmax(logits, dim=-1)
        top_vals, top_idx = gate_all.topk(2, dim=-1)         # [tokens, 2] each

        # Renormalize the two selected weights to sum to 1. Without this,
        # output scale depends on how much probability mass fell OUTSIDE
        # the top-2 -- which varies token to token -- and silently drifts
        # the magnitude this sublayer contributes to the residual stream.
        # A commonly omitted step.
        top_vals = top_vals / top_vals.sum(dim=-1, keepdim=True)

        out = torch.zeros_like(x)
        load = torch.zeros(self.n_experts, dtype=torch.long)

        # Dense reference form: loop over every expert, mask the tokens
        # that selected it. Production dispatch instead SORTS tokens by
        # chosen expert and gathers them into per-expert contiguous
        # batches (Concept - MoE Inference and Expert Parallelism) --
        # identical math, no wasted compute on masked-out tokens, at the
        # cost of an all-to-all communication step when experts live on
        # different devices (Concept - Tensor and Pipeline Parallelism).
        for e in range(self.n_experts):
            for slot in range(2):
                mask = top_idx[:, slot] == e
                if mask.any():
                    weight = top_vals[mask, slot : slot + 1]
                    out[mask] += weight * self.experts[e](x[mask])
                    load[e] += mask.sum()

        return out, load


if __name__ == "__main__":
    torch.manual_seed(0)
    n_tokens, d_model, d_ff, n_experts = 64, 32, 64, 8

    moe = Top2MoE(d_model=d_model, d_ff=d_ff, n_experts=n_experts)
    x = torch.randn(n_tokens, d_model)
    out, load = moe(x)

    print(f"output shape: {out.shape}")
    assert out.shape == (n_tokens, d_model)
    assert load.sum().item() == n_tokens * 2   # top-2 -> 2 assignments/token

    print(f"expert token counts: {load.tolist()}")
    imbalance = load.float().max() / load.float().mean()
    print(f"load imbalance (max/mean): {imbalance:.2f}")
    # With zero balancing pressure -- no aux loss, a single untrained
    # forward pass -- the histogram is already uneven. That's the seed of
    # the routing-collapse dynamic in Gotchas - Mixture of Experts #1, not
    # a bug in this snippet: nothing here is pushing load toward uniform.
```

## Why it's written this way

**Top-2 renormalization gets its own commented line** instead of being folded into the combine step. It's the correctness detail most often left out of hand-rolled routers. Skipping it is easy because the model still "works", just with a token-dependent output scale that distorts training.

**The dense mask-and-loop form is on purpose.** A real expert-parallel implementation gathers tokens per expert and dispatches across devices for efficiency. This snippet computes every expert and masks what wasn't selected, because in that form you can read correctness straight off the code, and it's the right first implementation to match numerically before optimizing (see [[Playbook - Numerically Matching a Reference Implementation]]).

**The load histogram is a return value**, so nobody has to bolt it on later. In production MoE, per-expert token counts are the most useful health signal you can log. A spiky histogram is the earliest visible symptom of routing collapse, well before it shows up in loss (see [[Gotchas - Mixture of Experts]]).

**The expert module mirrors a dense [[Concept - Feed-Forward Networks and GLU Variants|FFN]] block** instead of a simplified stand-in. MoE sparsifies this sublayer, and keeping the same shape (`w1` up-project, activation, `w2` down-project) makes the parameter comparison against a dense model direct: $N$ experts at this size cost roughly $N\times$ one dense FFN's parameters, while forward compute per token stays at 2 experts' worth.

## Connections
- [[Concept - Mixture of Experts Architecture]] — the full mechanism (routing granularity, capacity, shared experts) this snippet implements the top-2 slice of.
- [[Gotchas - Mixture of Experts]] — gotcha 1 (routing collapse) and gotcha 6 (gate renormalization/precision) are exactly what this snippet's load histogram and renormalization line are written to surface and prevent.
- [[Breakdown - Mixtral 8x7B]] — the real system whose FFN sublayer this snippet's routing math reproduces, at a toy scale (8 experts, top-2, no capacity limit).
- [[Breakdown - DeepSeek-V3 Architecture]] — the fine-grained-plus-shared-expert evolution of this same top-2 idea, at 256 routed experts with an always-on shared expert this snippet omits for simplicity.
- [[Concept - Feed-Forward Networks and GLU Variants]] — the dense sublayer this MoE layer sparsifies; the `Expert` module here is structurally that block.
- [[Concept - Tensor and Pipeline Parallelism]] — where the dense-loop-vs-dispatch tradeoff noted in the code becomes a real distributed-systems decision once experts live on different devices.
- [[Concept - MoE Inference and Expert Parallelism]] — the production-serving counterpart to this reference implementation: same math, scatter/gather dispatch instead of a masked loop.
- [[Snippet - Scaled Dot-Product Attention from Scratch]] — the sibling reference snippet for the other transformer sublayer; both are meant to be read as the "un-optimized but correct" baseline before reaching for a fused or dispatch-optimized kernel.
- [[Playbook - Numerically Matching a Reference Implementation]] — the procedure for proving a dense-reference layer like this one (or its dispatch-optimized replacement) is numerically identical to the system it's meant to reproduce.

## Sources
- Fedus, Zoph, Shazeer (2021) — Switch Transformer. The top-1 routing ancestor of this top-2 design, and the source of the capacity-factor convention referenced in the code comments.
- Lepikhin et al. (2020) — GShard. Popularized top-2 expert-parallel routing at scale.
- Jiang et al. (2024) — "Mixtral of Experts." The real top-2-of-8 system this snippet's router directly mirrors.
