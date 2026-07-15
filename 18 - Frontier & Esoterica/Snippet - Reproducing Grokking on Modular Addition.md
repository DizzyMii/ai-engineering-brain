---
tags: [snippet, domain/esoterica, level/advanced]
aliases: [grokking reproduction, modular addition grokking script]
summary: "Runnable PyTorch reproduction of the grokking phase transition on (a+b) mod p, with the exact setup that makes it appear."
---

# Snippet - Reproducing Grokking on Modular Addition

**What it does:** trains a small decoder-only transformer on $(a+b) \bmod p$ — the exact minimal task from Power et al. 2022 that established [[Concept - Grokking]] — and reproduces the delayed-generalization curve: train accuracy saturates within a few hundred to a couple thousand steps while validation accuracy sits at chance ($1/p$) for thousands more steps, then snaps to near-100% within a few hundred steps. The point of running this yourself is to see the delay, not just read about it — the phenomenon is invisible unless you actually wait past where training "looks done."

**Dependencies:** `torch>=2.1` (a single GPU finishes in a few minutes; CPU works but is slower — lower `STEPS` for a quick smoke test). `matplotlib` is optional, only used for the log-x plot at the end.

**Expected output:** a printout every 100 steps of `(train_acc, val_acc)`. With this exact configuration (`frac_train=0.4`, `weight_decay=1.0`, full-batch), train accuracy reaches ~1.0 within roughly the first 500-2,000 steps; validation accuracy stays near $1/p \approx 0.010$ for thousands of steps, then transitions to >0.95 somewhere in the low-thousands-to-~15,000-step range for this seed. This is faster than Power et al.'s original ~$10^5$-step setup because full-batch training and weight decay of 1.0 both accelerate the transition — folklore, weakly sourced beyond the paper's own hyperparameter table: expect real run-to-run variance from a different seed or a different `frac_train`.

```python
"""
Reproduces the grokking phase transition (Power et al. 2022, "Grokking:
Generalization Beyond Overfitting on Small Algorithmic Datasets") on
modular addition: train accuracy hits ~100% early while validation
accuracy sits at chance for thousands of steps, then snaps to ~100%.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(0)
device = "cuda" if torch.cuda.is_available() else "cpu"

# ---- Task: (a + b) mod P. Tokens 0..P-1 are numbers, token P is '='. ----
P = 97
VOCAB, SEQ_LEN, EQ = P + 1, 3, P        # sequence = [a, b, '='] -> predict sum

def make_dataset():
    a, b = torch.meshgrid(torch.arange(P), torch.arange(P), indexing="ij")
    a, b = a.flatten(), b.flatten()
    x = torch.stack([a, b, torch.full_like(a, EQ)], dim=1)   # (P*P, 3)
    y = (a + b) % P                                          # (P*P,)
    return x, y

x, y = make_dataset()
perm = torch.randperm(P * P)
frac_train = 0.4                        # THE key lever: too low -> never groks
n_train = int(frac_train * P * P)
train_idx, val_idx = perm[:n_train], perm[n_train:]
x_train, y_train = x[train_idx].to(device), y[train_idx].to(device)
x_val, y_val = x[val_idx].to(device), y[val_idx].to(device)

# ---- Model: 2-layer decoder-only transformer, width 128 ----
class GrokTransformer(nn.Module):
    def __init__(self, vocab=VOCAB, d_model=128, n_heads=4, n_layers=2, seq_len=SEQ_LEN):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab, d_model)
        self.pos_emb = nn.Embedding(seq_len, d_model)
        layer = nn.TransformerEncoderLayer(
            d_model, n_heads, dim_feedforward=4 * d_model,
            dropout=0.0, activation="gelu", batch_first=True, norm_first=True,
        )
        self.blocks = nn.TransformerEncoder(layer, n_layers)
        self.unembed = nn.Linear(d_model, vocab, bias=False)
        self.register_buffer(
            "causal_mask", nn.Transformer.generate_square_subsequent_mask(seq_len)
        )

    def forward(self, tokens):
        pos = torch.arange(tokens.size(1), device=tokens.device)
        h = self.tok_emb(tokens) + self.pos_emb(pos)
        h = self.blocks(h, mask=self.causal_mask)
        return self.unembed(h)          # (batch, seq, vocab)

model = GrokTransformer().to(device)

# ---- THE hyperparameters that make grokking appear ----
opt = torch.optim.AdamW(model.parameters(), lr=1e-3, betas=(0.9, 0.98), weight_decay=1.0)
STEPS = 20_000

@torch.no_grad()
def accuracy(x_, y_):
    logits = model(x_)[:, -1, :]        # prediction at the '=' position
    return (logits.argmax(-1) == y_).float().mean().item()

history = {"step": [], "train_acc": [], "val_acc": []}
for step in range(STEPS):
    model.train()
    logits = model(x_train)[:, -1, :]   # full-batch: no minibatching, no SGD noise
    loss = F.cross_entropy(logits, y_train)
    opt.zero_grad()
    loss.backward()
    opt.step()

    if step % 100 == 0:
        model.eval()
        tr_acc, va_acc = accuracy(x_train, y_train), accuracy(x_val, y_val)
        history["step"].append(step)
        history["train_acc"].append(tr_acc)
        history["val_acc"].append(va_acc)
        print(f"step {step:6d}  train_acc {tr_acc:.3f}  val_acc {va_acc:.3f}")

# Log-x is essential -- on a linear step axis the transition looks like a
# wall you cannot distinguish from noise near the y-axis.
try:
    import matplotlib.pyplot as plt
    plt.plot(history["step"], history["train_acc"], label="train")
    plt.plot(history["step"], history["val_acc"], label="val")
    plt.xscale("log")
    plt.xlabel("step (log scale)"); plt.ylabel("accuracy"); plt.legend()
    plt.savefig("grokking_curve.png")
except ImportError:
    pass
```

## Why it's written this way

- **Full-batch training plus `weight_decay=1.0`** is the single most load-bearing choice in the script. Full-batch removes SGD noise as a confound so the memorize-then-generalize dynamic is cleanly isolated, and weight decay this high — an order of magnitude above a typical LLM's ~0.1 — is what eventually makes the low-norm generalizing circuit the loss-minimizing solution over the high-norm memorizing one (see [[Concept - Grokking]] for the circuit-efficiency mechanism). Set `weight_decay=0.0` and you will wait far longer, or never see the transition in a practical budget.
- **`frac_train=0.4` is deliberately mid-range.** Too little training data (roughly below 0.2) and the network can memorize indefinitely with no pressure toward the generalizing solution; too much (above ~0.7) and there's barely anything to compress, which also suppresses the effect. If reproducing on a different modulus, sweep this first.
- **Loss and accuracy run on the full train/val sets every step, not minibatched**, which is only tractable because $P=97$ keeps the whole dataset (9,409 pairs) trivially small. This is a deliberate toy-scale choice to make the phenomenon fast and cheap to observe on a single GPU in minutes, not a realistic training regime — see [[Concept - The Training Loop]] for the general forward/loss/backward/step mechanics being specialized here.
- **Logging every 100 steps and plotting on a log-x axis is not cosmetic.** The transition looks like a step-function discontinuity that would be invisible against thousands of flat preceding steps on a linear axis; the entire point of the exercise is to observe the delay itself, which only reads clearly in log-step space.
- **This script reproduces the phenomenon, not the mechanism.** It shows *that* the network delays generalization; it does not show *why*. For the discrete Fourier/trig circuit Nanda et al. found underneath this exact curve, follow [[Concept - Grokking]]; for the general toolkit (progress measures, activation-level circuit analysis) that finds circuits like it, follow [[Deep Dive - Mechanistic Interpretability]].

## Connections
- [[Concept - Grokking]] — the phenomenon and its mechanistic account (the Fourier/trig circuit, circuit efficiency) that this snippet reproduces the outward symptom of.
- [[Concept - Double Descent]] — the sibling phenomenon of test performance moving long after train loss saturates; grokking is the delayed, discontinuous extreme of the same family, and a down-link to the prerequisite concept.
- [[Concept - Adam and AdamW]] — the optimizer whose weight-decay term is the single most load-bearing hyperparameter in this script.
- [[Concept - The Training Loop]] — the general training mechanics this snippet specializes into a full-batch, high-weight-decay configuration; a down-link to the prerequisite.
- [[Concept - Numeracy and Digit Tokenization]] — the same Fourier/trig-feature mechanism the grokked model discovers for modular addition shows up again in how production LLMs represent numbers internally; an up-link to the unicorn-level consequence.
- [[Deep Dive - Mechanistic Interpretability]] — the toolkit (progress measures, circuit analysis) used to find the algorithm this snippet's model learns but does not itself expose.
