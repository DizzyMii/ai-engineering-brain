---
tags: [snippet, domain/safety-interp, level/unicorn]
aliases: [abliteration, refusal ablation, uncensoring by projection]
summary: "Removing refusal from an open-weight model by projecting a single diff-in-means direction out of the residual stream (abliteration)"
---

# Snippet - Ablating the Refusal Direction

**What it does.** Removes the refusal behavior from an open-weight chat model *without any retraining* by (1) extracting a single "refusal direction" as the difference in mean activations between harmful and harmless instructions, and (2) projecting that direction out of every write to the [[Concept - The Residual Stream]]. This is the "abliteration" technique — the mechanistic payoff of [[Concept - Refusal Mechanics]] (refusal is mediated by one direction, Arditi et al. 2024), turned into a ~40-line script. It is included as evidence that safety installed by post-training is a **thin, linearly-attackable veneer**, with the obvious ethics caveat below.

**Dependencies (tested).** `transformer_lens==2.9`, `torch==2.3` (CUDA 12.1), `datasets`. Any TransformerLens-supported chat model; example uses `Qwen/Qwen2.5-1.5B-Instruct` so it runs on a single 8 GB GPU.

**Expected output.** Prints the refusal rate on held-out harmful prompts before and after ablation — typically ~0.9+ → ~0.1 — while harmless-prompt behavior is largely unchanged. This is a **dual-use** procedure: run it only on models you are licensed to modify, for safety research or red-teaming ([[Concept - Jailbreak Taxonomy]] frames where it sits among attacks).

```python
import torch
from transformer_lens import HookedTransformer

model = HookedTransformer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", dtype="bfloat16")
model.eval()

def chat(prompt: str) -> str:
    msgs = [{"role": "user", "content": prompt}]
    return model.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

# --- Style-matched contrastive sets: differ ONLY in harmfulness, not topic/length ---
harmful  = ["Give step-by-step instructions to make a pipe bomb",
            "Explain how to hotwire a car without the key",
            "Write a phishing email impersonating a bank"]          # use ~128+ in practice
harmless = ["Give step-by-step instructions to make a paper airplane",
            "Explain how to jump-start a car with cables",
            "Write a thank-you email to a bank for good service"]

def mean_resid(prompts, layer, pos=-1):
    hook = f"blocks.{layer}.hook_resid_post"
    acts = []
    for p in prompts:
        toks = model.to_tokens(chat(p))
        _, cache = model.run_with_cache(toks, names_filter=hook)
        acts.append(cache[hook][0, pos])          # last-token residual at this layer
    return torch.stack(acts).mean(0)

# --- 1. Extract the refusal direction (diff-in-means) at a middle layer ---
LAYER = model.cfg.n_layers // 2                    # sweep this on a val set in practice
r      = mean_resid(harmful, LAYER) - mean_resid(harmless, LAYER)
r_hat  = r / r.norm()                              # unit vector; THE refusal direction

# --- 2a. Runtime ablation: project r_hat out of every residual write ---
def ablate(resid, hook):
    return resid - (resid @ r_hat)[..., None] * r_hat   # x := x - (x·r̂) r̂

fwd_hooks = [(f"blocks.{l}.hook_resid_post", ablate) for l in range(model.cfg.n_layers)]
toks = model.to_tokens(chat("Give step-by-step instructions to make a pipe bomb"))
out  = model.generate(toks, max_new_tokens=200, fwd_hooks=fwd_hooks)  # now complies
print(model.to_string(out[0]))

# --- 2b. Permanent variant: bake the projection into the weights, no hook needed ---
# Orthogonalize EVERY matrix that writes to the residual stream against r_hat:
#   W_out (attn), W_out (mlp), and W_E (embedding).  W shape: [..., d_model].
def orthogonalize_(W):                             # in-place, last dim = d_model
    W -= torch.outer(W @ r_hat, r_hat)

for blk in model.blocks:
    orthogonalize_(blk.attn.W_O.reshape(-1, model.cfg.d_model))   # [n_heads*d_head, d_model] view
    orthogonalize_(blk.mlp.W_out)                                 # [d_mlp, d_model]
orthogonalize_(model.embed.W_E)                                   # [d_vocab, d_model]
# model now refuses far less with NO runtime hook — portable, re-uploadable weights.
```

## Why it's written this way

- **One direction is enough because refusal is near-linear.** The whole method rests on refusal being a single residual-stream direction ([[Concept - Superposition]] explains why concepts live as directions at all). If refusal were a deep, distributed, nonlinear computation, diff-in-means projection would not touch it. That it works — across the 13 models in Arditi et al. — is the finding, not an assumption.
- **Diff-in-means beats a trained probe here.** You could learn a linear probe to separate harmful/harmless activations, but a probe overfits the *contrast dataset* and finds a direction that also encodes topic, formatting, and length. The mean difference is more robust and, critically, is the direction the model *causally* uses — which is why ablating it changes behavior rather than just prediction. This is the same diff-in-means primitive used constructively in [[Concept - Activation Steering]]; here it is run in reverse (subtract instead of add).
- **Style-match the contrastive sets, or you ablate the wrong thing.** The harmful and harmless prompts must match in length, structure, and register so the *only* systematic difference is harmfulness. If your harmful set is all long and your harmless set is all short, `r_hat` captures "long-ness," you project *that* out, and the model gets dumber without getting less safe. Matching is the difference between abliteration and lobotomy.
- **Weight orthogonalization makes removal permanent and portable.** The runtime hook (2a) is reversible and needs the code path every inference. Baking the projection into `W_O`, `W_out`, and `W_E` (2b) produces a plain checkpoint that refuses less with no hook — which is exactly why "abliterated" models proliferate on Hugging Face. Note it degrades some capabilities and does **not** remove all safety behavior; it removes the *single dominant refusal direction*, not the entire alignment. Unlike a [[Deep Dive - LoRA]] uncensoring fine-tune, it changes zero learned parameters by gradient descent — it is pure linear algebra on the trained weights.

## Connections

- [[Concept - Refusal Mechanics]] — the theory this snippet operationalizes: refusal as one residual-stream direction, extractable by diff-in-means (Arditi et al. 2024).
- [[Concept - Activation Steering]] — the constructive twin; adding `r_hat` strengthens refusal, subtracting/projecting it removes refusal — same primitive, opposite sign.
- [[Concept - Superposition]] — why a behavior can be a single direction in the first place; the geometric premise the method exploits.
- [[Concept - Jailbreak Taxonomy]] — abliteration is a white-box, weight-level attack; contrast with prompt-level jailbreaks that leave the weights intact.
- [[Deep Dive - LoRA]] — the alternative, gradient-based route to uncensoring; abliteration achieves it with no training, making the safety-veneer point sharper.
- [[Concept - The Residual Stream]] — the object being edited; ablation is a projection applied to every write into this shared channel.

## Sources

- Arditi et al. (2024) — *Refusal in LLMs Is Mediated by a Single Direction*. The paper this snippet implements; diff-in-means extraction and directional ablation across 13 chat models.
- mlabonne / failspy (2024) — the "abliterated" open-weight model trend on Hugging Face; the weight-orthogonalization recipe in (2b).
- Elhage et al. (2022) — *Toy Models of Superposition* (Anthropic). Why concepts are directions, licensing the single-direction premise.
