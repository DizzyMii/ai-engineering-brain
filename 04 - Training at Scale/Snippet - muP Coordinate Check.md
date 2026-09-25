---
tags: [snippet, domain/training-at-scale, level/frontier]
aliases: [muP coord check, coordinate check, mup coordinate check]
summary: "Runnable check that a muP implementation keeps activation coordinates O(1) across model widths at init and after a few steps."
---

# Snippet - muP Coordinate Check

**What it does:** builds the same MLP at several widths, applies [[Concept - muP and Hyperparameter Transfer|muP]] scaling (fan-in init, per-layer LR, output multiplier), runs a few AdamW steps on an *identical* batch and seed, then prints each layer's mean absolute activation per width. With correct muP those magnitudes stay roughly constant across width (flat rows). Standard parametrization (SP) makes them fan out. It's the most reliable test that a muP implementation is wired correctly: a wrong multiplier passes unit tests and fails here.

**Dependencies:** `torch>=2.1` (CPU is fine).

**Expected output:** two tables. muP rows are ~flat left to right. SP's `fc2`/`logits` rows grow with width, most visibly *after* the update steps.

```python
import torch, torch.nn as nn, torch.nn.functional as F

BASE_WIDTH = 128
D_IN, D_OUT = 64, 8
WIDTHS = [128, 256, 512, 1024, 2048]
LR, STEPS = 1e-2, 5

class MLP(nn.Module):
    def __init__(self, width, mup=True):
        super().__init__()
        self.mup = mup
        self.width_mult = width / BASE_WIDTH          # relative width vs the proxy
        self.fc1 = nn.Linear(D_IN, width, bias=False)  # input / embedding-like
        self.fc2 = nn.Linear(width, width, bias=False) # hidden
        self.fc3 = nn.Linear(width, D_OUT, bias=False) # readout
        self._init()

    @torch.no_grad()
    def _init(self):
        # fan-in Gaussian init => preactivations are O(1) at every width
        self.fc1.weight.normal_(0, D_IN ** -0.5)
        self.fc2.weight.normal_(0, self.fc2.in_features ** -0.5)
        if self.mup:
            self.fc3.weight.zero_()                     # muP: readout initialised to 0
        else:
            self.fc3.weight.normal_(0, self.fc3.in_features ** -0.5)

    def forward(self, x):
        h1 = F.relu(self.fc1(x))
        h2 = F.relu(self.fc2(h1))
        logits = self.fc3(h2)
        if self.mup:
            logits = logits / self.width_mult          # muP: 1/width output multiplier
        self.acts = {"fc1": h1, "fc2": h2, "logits": logits}
        return logits

def param_groups(model):
    if not model.mup:
        return [{"params": model.parameters(), "lr": LR}]   # SP: one global LR
    m = model.width_mult
    return [
        {"params": model.fc1.parameters(), "lr": LR},       # input: constant LR
        {"params": model.fc2.parameters(), "lr": LR / m},   # hidden: LR / width
        {"params": model.fc3.parameters(), "lr": LR / m},   # readout: LR / width
    ]

def run(mup):
    print(f"\n{'muP' if mup else 'standard param (SP)'} - mean |activation| by width")
    print(f"{'layer':8}" + "".join(f"{w:>9}" for w in WIDTHS))
    rows = {"fc1": [], "fc2": [], "logits": []}
    for w in WIDTHS:
        torch.manual_seed(1234)                             # init RNG identical per width
        model = MLP(w, mup=mup)
        g = torch.Generator().manual_seed(0)
        x = torch.randn(64, D_IN, generator=g)              # SAME batch at every width
        y = torch.randn(64, D_OUT, generator=g)
        opt = torch.optim.AdamW(param_groups(model), betas=(0.9, 0.95), weight_decay=0.0)
        for _ in range(STEPS):
            opt.zero_grad()
            F.mse_loss(model(x), y).backward()
            opt.step()
        with torch.no_grad():
            model(x)                                        # refresh acts after the steps
        for k in rows:
            rows[k].append(model.acts[k].abs().mean().item())
    for k, vals in rows.items():
        print(f"{k:8}" + "".join(f"{v:9.3f}" for v in vals))

run(mup=True)
run(mup=False)
```

Representative output (numbers vary by seed/BLAS; what matters is *flat vs fanning*):

```
muP - mean |activation| by width
layer         128      256      512     1024     2048
fc1         0.40     0.40     0.40     0.40     0.40
fc2         0.31     0.31     0.30     0.30     0.30
logits      0.05     0.05     0.05     0.05     0.05

standard param (SP) - mean |activation| by width
layer         128      256      512     1024     2048
fc1         0.40     0.40     0.40     0.40     0.40
fc2         0.34     0.41     0.52     0.71     1.02
logits      0.18     0.33     0.61     1.14     2.16
```

## Why it's written this way

**Zero readout init, output divided by `width_mult`.** These two muP rules make the *output* width-invariant. Drop either one and the `logits` row fails first, because the output-layer update scales with width. `fc1` (fan-in init) looks fine under both parametrizations; muP doesn't earn its keep at the input layer.

**Per-layer Adam LR through param groups** (hidden and readout at `LR/m`, input constant). This is the mechanism muP encodes. The SP branch uses a single global LR on purpose. That's the bug muP fixes, and it's why the SP rows fan out only after `opt.step()` runs.

**Same batch and seed at every width.** Width has to be the only variable, or you can't pin divergence on the parametrization instead of noise. The data generator is seeded separately from the init so the batch is byte-identical across widths.

**Measure at step 0 *and* after a few steps.** Init can look width-invariant while the *updates* blow up; a wrong LR exponent only shows up under optimization. Reading coordinates after ~5 steps is what catches a broken implementation, so this script prints the post-step state. In production you'd use `mup.set_base_shapes` instead of hand-rolling the three rules, but the check is the same.

## Connections

- [[Concept - muP and Hyperparameter Transfer]] — this snippet is the empirical verifier for that concept's scaling rules; the check is muP's own correctness test.
- [[Concept - AdamW at Scale]] — the per-layer LR groups and `betas=(0.9, 0.95)` mirror how the optimizer is actually configured at scale.
- [[Concept - Learning Rate Schedules for Pretraining]] — muP's whole payoff is that the peak LR transferred from the proxy needs no re-tuning at the target width.
- [[Concept - Backpropagation]] — the coordinate magnitudes being measured are exactly the forward activations whose gradients backprop must keep O(1); a down-link to the prerequisite.
- [[Concept - Attention Logit Stabilization (QK-Norm and Soft-Capping)]] — muP replaces the `1/sqrt(d)` attention scale with `1/d`; QK-norm/soft-capping is the alternative family for keeping attention logits well-scaled, and the same coordinate logic applies.
