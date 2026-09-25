---
tags: [snippet, domain/esoterica, level/unicorn]
aliases: [softmax1, softmax_1, quiet attention, ghost softmax, Attention Is Off By One]
summary: "Drop-in softmax_1 (+1 in the denominator) that lets attention heads attend to nothing, plus a demo of how it de-pressurizes sinks."
---

# Snippet - Softmax-Off-By-One (Quiet Attention)

> **What it does:** implements `softmax_1`, the "+1 in the denominator" attention variant that gives a head a way to attend to *nothing*, as a three-line drop-in. It then demonstrates the mechanism on an "unsure" query and measures the real [[Concept - Attention Sinks|attention sink]] it's meant to relieve on GPT-2. **Deps:** `torch>=2.0`, `transformers>=4.40` (`pip install torch transformers`). **Expected output:** the unsure query leaks ~0.9 of its mass to the phantom null key under `softmax_1`, while ordinary [[Concept - Softmax|softmax]] forces it to sum to exactly 1. On GPT-2 several layers park 0.3–0.8 of their mean attention mass on token 0.

```python
"""
softmax_1 ("quiet attention" / "off-by-one softmax"), after Evan Miller 2023.
The change: give the softmax an implicit always-present null key with logit 0,
so a head that has nothing to say can send its mass there instead of a real token.
"""
import torch
import torch.nn.functional as F

# --- The whole idea, in three lines --------------------------------------
def softmax_1(logits, dim=-1):
    # softmax_1(x)_i = exp(x_i) / (1 + Σ_j exp(x_j))
    # == ordinary softmax over the logits with a phantom 0-logit ("null key")
    #    appended, then that column dropped. F.softmax does the max-subtraction,
    #    so the "+1" becomes exp(0 - max) = e^{-max} in the denominator --
    #    numerically safe even when logits are large over a long sequence.
    z = torch.cat([logits, torch.zeros_like(logits[..., :1])], dim=dim)
    return F.softmax(z, dim=dim)[..., :-1]

# --- 1. Mechanism: an "unsure" query, where nothing is worth attending to ---
unsure = torch.tensor([-4.0, -5.0, -6.0, -4.5])
p, p1 = F.softmax(unsure, -1), softmax_1(unsure, -1)
print("unsure  softmax   sum=%.3f  %s" % (p.sum(),  [round(x, 3) for x in p.tolist()]))
print("unsure  softmax_1 sum=%.3f  %s   (null key absorbed %.3f)"
      % (p1.sum(), [round(x, 3) for x in p1.tolist()], 1 - p1.sum()))

# --- 2. Contrast: a "confident" query where one key dominates ---------------
#     Both agree closely -> softmax_1 is a no-op when a head is sure of itself.
conf = torch.tensor([8.0, -2.0, -3.0, 0.0])
print("conf    softmax   sum=%.3f" % F.softmax(conf, -1).sum())
print("conf    softmax_1 sum=%.3f   (null key absorbed %.3f)"
      % (softmax_1(conf, -1).sum(), 1 - softmax_1(conf, -1).sum()))

# --- 3. The sink is real: measure it on a pretrained model ------------------
from transformers import AutoModelForCausalLM, AutoTokenizer
tok = AutoTokenizer.from_pretrained("gpt2")
model = AutoModelForCausalLM.from_pretrained("gpt2", attn_implementation="eager",
                                             output_attentions=True).eval()
ids = tok("The quick brown fox jumps over the lazy dog.", return_tensors="pt")
with torch.no_grad():
    attn = model(**ids).attentions                # tuple[layers] of [1, heads, q, k]
print("\nmean attention mass parked on token 0 (the sink), per layer:")
for L, a in enumerate(attn):
    sink = a[0, :, 1:, 0].mean().item()           # queries after pos 0, mass on key 0
    print(f"  layer {L:2d}: {sink:.2f}")
```

## Why it's written this way

### The `+1` as a phantom zero-logit key
Writing `softmax_1` as "append a logit of 0, softmax, drop the column" makes it obvious *what* the extra term is: an always-present null key the head can route to. It also inherits `F.softmax`'s max-subtraction for free, so the "+1" correctly becomes `exp(0 − max)` in the denominator. Hand-roll `exp(x) / (1 + exp(x).sum())` without the max shift and it silently overflows to `inf/inf = nan` once logits get large over a long context, which is the regime this trick is supposed to help.

### Only unsure heads change
The two demos are the whole argument. On the confident query one key dominates the denominator, so `1` is negligible next to `Σ exp(x_j)` and `softmax_1 ≈ softmax`. On the unsure query every logit is negative, `Σ exp(x_j)` is small, and the `1` swallows ~0.9 of the mass. `softmax_1` does nothing to sharp heads and gives vague ones an escape valve; it can't blunt attention that already knows where to look. That's why it's a plausible free win, and the mechanistic reason it *might* remove the pressure that produces [[Concept - Massive Activations and Outlier Features|massive activations]] and sinks without hurting real attention.

### Why the GPT-2 measurement uses vanilla softmax
Swapping `softmax_1` in at inference isn't a valid test. GPT-2 built its sink and outlier channels *under* ordinary softmax during training, so the bias lives in the weights as a fixed attention-bias term, not in the runtime normalization. Monkeypatching `softmax_1` into a trained model would change the outputs without demonstrating anything, because the model already spent capacity building the sink. Without a from-scratch training run, the honest move is to *measure the baseline sink* (0.3–0.8 mass on token 0) and show the phenomenon the proposal targets. To test the fix, you have to pretrain with `softmax_1` from step 0.

### A contested hypothesis, reported as one
Evan Miller's own follow-up quantization experiments were mixed, and Gu et al. (2024) found attention sinks still emerge under softmax variants. The competing fix, [[Concept - Attention Sinks|StreamingLLM]]'s dedicated *trained* sink token, provably keeps perplexity flat over millions of tokens; `softmax_1`'s benefit is still ambiguous. The same lever appears in two other places: [[Breakdown - YaRN|YaRN]]'s attention-temperature term, and the learnable per-head sink logits some production models now ship. All three are angles on one question, *where does the leftover softmax mass go?*, and this snippet makes that question concrete without declaring a winner.

## Connections

- [[Concept - Attention Sinks]] — the phenomenon `softmax_1` targets; that note covers StreamingLLM's trained-sink alternative and why sinks form from softmax normalization in the first place.
- [[Concept - Massive Activations and Outlier Features]] — the sink and the outlier are two views of the same implicit-bias mechanism; if `softmax_1` removes the normalization pressure, both should shrink together.
- [[Concept - Softmax]] — the operator being modified (domain 02); the `+1` is a change to its denominator, and the max-subtraction stability trick comes from there.
- [[Concept - Attention Mechanism]] — where this softmax lives (domain 03); the null key is a change to how the attention weights are normalized before the value-weighted sum.
- [[Concept - Post-Training Quantization Formats]] — why this matters downstream (domain 07): sinks and massive activations are what wreck naive INT8/INT4 quantization, so relieving them is a quantization argument as much as a stability one.
- [[Breakdown - YaRN]] — YaRN's attention-temperature scaling is the same "control the leftover softmax mass" lever applied to context extension rather than sinks.

## Sources

- Miller (2023) — *Attention Is Off By One* (blog). Proposes `softmax_1` / "quiet attention" as a fix for outlier weights and attention sinks; reports own quantization follow-ups as mixed.
- Xiao et al. (2023) — *Efficient Streaming Language Models with Attention Sinks* (StreamingLLM). The competing, empirically-validated fix: keep the first few tokens' KV as permanent sink cache, or train a dedicated sink token.
- Gu et al. (2024) — study of when and why attention sinks emerge in LLMs; finds sinks persist under softmax variants, tempering the `softmax_1` claim.
