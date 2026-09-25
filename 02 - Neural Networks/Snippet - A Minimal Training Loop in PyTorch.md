---
tags: [snippet, domain/neural-networks, level/core]
aliases: [minimal PyTorch loop, training loop example]
summary: "A ~45-line runnable PyTorch loop with correct op ordering, nanoGPT-style weight-decay param groups, clipping, and eval hygiene."
---

# Snippet - A Minimal Training Loop in PyTorch

**What it does:** trains a small [[Concept - The Multilayer Perceptron|MLP]] classifier on synthetic Gaussian blobs. It shows correct ordering of [[Concept - The Training Loop]] operations, the weight-decay param-group split, gradient clipping with the grad norm printed, and train/eval mode hygiene. One technique: the loop itself, done right.

**Dependencies:** `torch >= 2.0` (CPU is fine; no other packages).

**Expected output:** train loss starts at $\approx \ln(4) = 1.386$ (uniform over 4 classes; if not, the loss or labels are broken, so check them before blaming the model) and falls below 0.05 by step 200. Val accuracy reaches ~0.95+. Runs in under 10 seconds on a laptop CPU.

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(0)

# --- Synthetic data: 4 Gaussian blobs, deliberately easy to overfit ---
N, D_IN, N_CLASSES = 512, 32, 4
centers = torch.randn(N_CLASSES, D_IN) * 3.0
y = torch.randint(0, N_CLASSES, (N,))
x = centers[y] + torch.randn(N, D_IN)
x_train, y_train, x_val, y_val = x[:384], y[:384], x[384:], y[384:]

model = nn.Sequential(
    nn.Linear(D_IN, 128), nn.GELU(), nn.Dropout(0.1),
    nn.Linear(128, 128), nn.GELU(), nn.LayerNorm(128),
    nn.Linear(128, N_CLASSES),   # raw logits out; no softmax here
)

# --- Weight decay ONLY on matmul weights (dim >= 2): not on biases,
# --- norm gains, or embeddings. Same split as nanoGPT's configure_optimizers.
decay   = [p for p in model.parameters() if p.dim() >= 2]
no_decay = [p for p in model.parameters() if p.dim() < 2]
opt = torch.optim.AdamW(
    [{"params": decay,    "weight_decay": 0.1},
     {"params": no_decay, "weight_decay": 0.0}],
    lr=3e-4, betas=(0.9, 0.95),
)

for step in range(201):
    model.train()                        # dropout ON
    opt.zero_grad(set_to_none=True)      # before backward; grads ACCUMULATE otherwise
    loss = F.cross_entropy(model(x_train), y_train)   # fused log_softmax + NLL
    loss.backward()
    gnorm = nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    opt.step()                           # clip sits between backward and step

    if step % 20 == 0:
        model.eval()                     # dropout OFF (and BN stats frozen, if any)
        with torch.no_grad():            # no graph -> no activation memory
            val_logits = model(x_val)
            val_loss = F.cross_entropy(val_logits, y_val)
            acc = (val_logits.argmax(-1) == y_val).float().mean()
        print(f"step {step:3d}  train {loss.item():.4f}  "
              f"val {val_loss.item():.4f}  acc {acc.item():.3f}  gnorm {gnorm:.2f}")
```

## Why it's written this way

1. **`zero_grad(set_to_none=True)` before `backward()`.** `.backward()` *adds into* `.grad` by design; accumulation is what makes gradient accumulation and RNN-style reuse possible (see [[Concept - Backpropagation]]). Forgetting to zero is the classic silent bug: loss stalls while the grad norm climbs every step. `set_to_none` frees the grad tensors instead of writing zeros. It saves memory and bandwidth and is the PyTorch 2.x default, but code that reads `p.grad` must now handle `None` instead of a zero tensor.
2. **The param-group split.** Decaying LayerNorm gains pulls them toward 0, which fights what the norm layer is for. Decaying biases adds noise with no regularization payoff. Decaying embeddings shrinks rare-token rows that get too few updates to push back. Only the 2-D matmul weights carry `weight_decay=0.1`. The `p.dim() >= 2` test is the whole trick, copied verbatim from nanoGPT.
3. **Clip between `backward()` and `step()`, and print the norm.** `clip_grad_norm_` returns the *pre-clip* global norm. It's the cheapest training-health signal you can log: a spike to 10x baseline predicts a loss spike before the loss shows it. Clipping after `step()` does nothing, and clipping before `backward()` clips stale grads. Under mixed precision you unscale first (see [[Concept - Mixed Precision Training]]).
4. **`model.eval()` AND `torch.no_grad()` are separate mechanisms.** `eval()` flips module *behavior* (Dropout off, BatchNorm uses running stats). `no_grad()` stops autograd from building a graph, so forward activations aren't retained, and those are most of a training step's memory footprint (see [[Reference - Memory Math for Transformers]]). Each alone is a common bug: eval-only leaks memory, no_grad-only evaluates a stochastic model.

The optimizer and betas are deliberate. [[Concept - Adam and AdamW]] with $\beta_2 = 0.95$ is the modern transformer-style default, and decoupled decay is why the param-group split behaves as intended. If a loop like this won't learn, walk [[Playbook - Debugging a Neural Network That Won't Train]] in order instead of tweaking at random. This code already prints step 1 of that playbook (loss at init $\approx \ln C$).

## Connections

- [[Concept - The Training Loop]] — the theory note for every ordering decision this code makes; read it to know *why* the five lines go in this sequence.
- [[Concept - The Multilayer Perceptron]] — the model being trained; the simplest substrate that makes the loop's behavior legible.
- [[Concept - Backpropagation]] — why `.grad` accumulates and what `backward()` actually computes.
- [[Concept - Adam and AdamW]] — the optimizer whose decoupled weight decay makes the param-group split meaningful.
- [[Playbook - Debugging a Neural Network That Won't Train]] — the operational escalation path when this loop's expected output doesn't appear.
- [[Concept - Mixed Precision Training]] — the first thing you add for real workloads, and the reason the clip line grows an unscale step.
- [[Reference - Memory Math for Transformers]] — quantifies the activation memory that `no_grad()` avoids retaining.

## Sources

- Karpathy — nanoGPT (`configure_optimizers`). The canonical public implementation of the decay/no-decay param-group split.
- Loshchilov & Hutter (2019) — Decoupled Weight Decay Regularization. Why AdamW's decay makes the split behave as uniform shrinkage.
