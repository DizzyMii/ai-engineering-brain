---
tags: [snippet, domain/training-at-scale, level/advanced]
aliases: [FSDP2, fully_shard, torch FSDP]
summary: "A minimal runnable PyTorch FSDP2 training step: per-block fully_shard wrapping, bf16 compute with fp32 reduce, and activation checkpointing."
---

# Snippet - FSDP Minimal Setup

**What it does:** wraps a toy transformer's blocks with PyTorch's FSDP2 (`fully_shard`) API, applies a mixed-precision policy that computes in bf16 but reduces gradients in fp32, adds activation checkpointing per block, and runs one training step — demonstrating the full [[Concept - Fully Sharded Data Parallel (FSDP)]] wiring pattern used by TorchTitan-style trainers.
**Dependencies:** `torch>=2.4` (FSDP2's `fully_shard` composable API), run under `torchrun`. No other libraries required.
**Expected output:** per-step loss printed on rank 0, decreasing across a handful of toy steps; peak allocated memory per GPU roughly `1/world_size` of the single-GPU baseline (checked with `torch.cuda.max_memory_allocated()`).

```python
# train_fsdp2.py — launch with:
#   torchrun --nproc_per_node=8 train_fsdp2.py
import torch
import torch.nn as nn
from torch.distributed.device_mesh import init_device_mesh
from torch.distributed._composable.fsdp import fully_shard, MixedPrecisionPolicy
from torch.distributed.algorithms._checkpoint.checkpoint_wrapper import (
    checkpoint_wrapper,
)

class Block(nn.Module):
    def __init__(self, d_model=4096, d_ff=16384):
        super().__init__()
        self.norm = nn.RMSNorm(d_model)
        self.attn = nn.MultiheadAttention(d_model, num_heads=32, batch_first=True)
        self.mlp = nn.Sequential(nn.Linear(d_model, d_ff), nn.GELU(), nn.Linear(d_ff, d_model))

    def forward(self, x):
        h = self.norm(x)
        a, _ = self.attn(h, h, h, need_weights=False)
        x = x + a
        return x + self.mlp(self.norm(x))

class ToyTransformer(nn.Module):
    def __init__(self, n_layers=24, d_model=4096, vocab=50257):
        super().__init__()
        self.embed = nn.Embedding(vocab, d_model)
        self.blocks = nn.ModuleList(Block(d_model) for _ in range(n_layers))
        self.head = nn.Linear(d_model, vocab, bias=False)

    def forward(self, tokens):
        x = self.embed(tokens)
        for block in self.blocks:
            x = block(x)
        return self.head(x)

def main():
    mesh = init_device_mesh("cuda", (torch.cuda.device_count(),))
    model = ToyTransformer().cuda()

    mp_policy = MixedPrecisionPolicy(
        param_dtype=torch.bfloat16,   # compute in bf16
        reduce_dtype=torch.float32,   # but reduce-scatter gradients in fp32
    )

    # 1. Wrap each transformer block individually — NOT the whole model at once.
    for i, block in enumerate(model.blocks):
        model.blocks[i] = checkpoint_wrapper(block)   # activation checkpointing per block
        fully_shard(model.blocks[i], mesh=mesh, mp_policy=mp_policy)

    # 2. Wrap the root last so it becomes the outermost FSDP unit (embed + head + blocks).
    fully_shard(model, mesh=mesh, mp_policy=mp_policy)

    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(0.9, 0.95), weight_decay=0.1)

    for step in range(5):
        tokens = torch.randint(0, 50257, (2, 2048), device="cuda")
        logits = model(tokens)
        loss = logits.float().mean()   # placeholder loss for a runnable demo
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        if torch.distributed.get_rank() == 0:
            print(f"step {step} loss {loss.item():.4f}")

if __name__ == "__main__":
    main()
```

## Why it's written this way

- **Wrap per block, not the whole model, first.** `fully_shard` applied to a leaf module means only that unit's all-gather has to complete before it runs — wrapping the entire model as one FSDP unit forces a single giant all-gather that can't overlap with anything and peaks at full-model memory during it, defeating the entire point of sharding. The root-level `fully_shard` call at the end just makes the top-level module (embedding, final head, and residual buffers) participate in the same sharding scheme; the per-block calls are what create overlap opportunity.
- **Reduce in fp32, compute in bf16.** `param_dtype=bf16` gets you the throughput of low-precision matmuls (see [[Concept - Mixed Precision Training]]); `reduce_dtype=fp32` is not optional at scale — reducing gradients in bf16 across hundreds of ranks compounds rounding error into a measurable loss-curve difference versus fp32 reduction, and the extra cost is one upcast per bucket, not a real bottleneck.
- **Checkpoint before sharding, in that order.** `checkpoint_wrapper` needs to see the block's real forward/backward to record what to recompute; wrapping it before `fully_shard` keeps the recomputation logic local to the block rather than fighting FSDP's parameter-gather/free lifecycle. This mirrors [[Concept - Data Parallelism and ZeRO|ZeRO-3]]'s own memory-for-compute trade, layered on top of the sharding trade.
- **Sharded state dicts, not full ones, for checkpointing.** This snippet doesn't show the save path, but the corresponding load/save must use `torch.distributed.checkpoint` (DCP) rather than materializing a full unsharded `state_dict()` on rank 0 — see [[Concept - Distributed Checkpointing]] — because gathering a 70B+ model's full fp32 state onto one rank to write it out is exactly the OOM you sharded to avoid in the first place.

## Connections
- [[Concept - Fully Sharded Data Parallel (FSDP)]] — the mechanism (all-gather/free per unit, wrapping-policy granularity, FSDP1 vs FSDP2) that this snippet is a minimal instance of.
- [[Concept - Data Parallelism and ZeRO]] — the ZeRO-3 algorithm FSDP2 realizes; read this first if the sharding logic itself is unfamiliar.
- [[Concept - Distributed Checkpointing]] — the sharded save/load path (DCP) that must pair with this training loop; naive `state_dict()` breaks at scale.
- [[Concept - Mixed Precision Training]] — why `param_dtype=bf16` / `reduce_dtype=fp32` is the standard split and what breaks if you reduce in bf16.
- [[Gotchas - Distributed Training]] — the NCCL hangs, rank desync, and mesh-misconfiguration failures that show up when this exact setup goes wrong across many nodes.
- [[Concept - GPU Memory Hierarchy]] — the HBM budget this per-block wrapping is managing; motivates why wrapping granularity matters at all.
- [[Snippet - A Minimal Training Loop in PyTorch]] — the single-GPU training-loop shape this snippet extends with sharding, mixed precision, and checkpointing.
- [[Concept - Rack-Scale Systems and NVLink Domains]] — determines whether `HYBRID_SHARD` (shard within a node, replicate across nodes) beats `FULL_SHARD` on a given cluster's topology.
