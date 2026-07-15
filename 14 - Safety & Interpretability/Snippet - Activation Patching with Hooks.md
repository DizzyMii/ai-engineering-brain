---
tags: [snippet, domain/safety-interp, level/advanced]
aliases: [IOI patching, resid_pre patching hook]
summary: "Runnable TransformerLens code that patches GPT-2 small's residual stream on the IOI task to heatmap the name-mover heads."
---

**What it does:** implements [[Concept - Activation Patching]] end to end on the classic IOI (indirect-object identification) task — caches clean-run activations, patches them into a corrupted run at every `(layer, position)`, and renders a heatmap of the normalized logit-difference recovery.
**Dependencies:** `transformer_lens>=1.17`, `torch>=2.2`, `matplotlib` (any recent version). Runs on CPU in well under a minute for GPT-2 small (12 layers, `d_model=768`).
**Expected output:** a `[12, n_pos]` heatmap where the score climbs toward 1 (clean-recovering) at the final token position from around layer 7-9 onward — the late-layer name-mover heads reported in Wang et al. 2022's IOI circuit — and stays near 0 (still corrupted) almost everywhere else.

```python
import torch
import matplotlib.pyplot as plt
from transformer_lens import HookedTransformer

torch.set_grad_enabled(False)

model = HookedTransformer.from_pretrained("gpt2")  # GPT-2 small: 12 layers, d_model=768

# Minimal-pair prompts: the only variable that changes is the identity of the
# second name. Everything else — length, structure, punctuation — is fixed,
# so any metric shift under patching is attributable to that one variable.
clean_prompt = "When John and Mary went to the store, John gave a drink to"
corrupted_prompt = "When John and John went to the store, John gave a drink to"  # Mary -> John

mary_token = model.to_single_token(" Mary")
john_token = model.to_single_token(" John")

clean_tokens = model.to_tokens(clean_prompt)
corrupted_tokens = model.to_tokens(corrupted_prompt)
n_pos = clean_tokens.shape[1]


def logit_diff(logits: torch.Tensor) -> float:
    # Logit difference, not softmax probability: linear in the unembedding,
    # so component-level effects add instead of interacting through softmax.
    final_logits = logits[0, -1]
    return (final_logits[mary_token] - final_logits[john_token]).item()


clean_logits, clean_cache = model.run_with_cache(clean_tokens)
corrupted_logits = model(corrupted_tokens)

clean_diff = logit_diff(clean_logits)
corrupted_diff = logit_diff(corrupted_logits)


def patch_resid_pre(activation, hook, position, cache):
    activation[:, position, :] = cache[hook.name][:, position, :]
    return activation


results = torch.zeros(model.cfg.n_layers, n_pos)

for layer in range(model.cfg.n_layers):
    for position in range(n_pos):
        hook_name = f"blocks.{layer}.hook_resid_pre"
        hook_fn = lambda act, hook, position=position: patch_resid_pre(
            act, hook, position, clean_cache
        )
        patched_logits = model.run_with_hooks(
            corrupted_tokens, fwd_hooks=[(hook_name, hook_fn)]
        )
        patched_diff = logit_diff(patched_logits)
        # Normalized score: 0 = still behaves corrupted, 1 = fully recovers clean.
        results[layer, position] = (patched_diff - corrupted_diff) / (
            clean_diff - corrupted_diff
        )

plt.imshow(results, aspect="auto", cmap="RdBu", vmin=-1, vmax=1)
plt.xlabel("token position")
plt.ylabel("layer")
plt.colorbar(label="patching score (0=corrupted, 1=clean)")
plt.title("Residual-stream patching: IOI logit-diff recovery")
plt.savefig("patching_heatmap.png")
```

## Why it's written this way

- **Patches `resid_pre`, not individual head outputs, for the first pass.** The residual stream is the shared channel every component reads from and writes to, so a `resid_pre` sweep gives a coarse `[layer x position]` map of *where* the relevant computation lives at minimal code complexity; once a hot region shows up, the natural next step (not shown here, to keep this snippet minimal) is to re-run the same loop patching `attn_out`/`z` at just those layers to attribute the effect to specific heads.
- **Normalizes against clean and corrupted baselines.** Dividing by `clean_diff - corrupted_diff` turns an otherwise model- and prompt-specific logit-difference number into a 0-to-1 recovery score that's comparable across layers, prompts, and even different models — without this, a heatmap's raw values are not interpretable at a glance.
- **Uses logit difference, not raw probability, as the metric.** Probability passes through softmax, which is nonlinear and saturates near 0 and 1; logit difference is linear in the unembedding matrix, so it stays well-behaved and additive across the many small patches being compared, which is what makes a clean heatmap possible instead of a noisy one.
- **Runs one prompt pair for clarity, but production analysis should not stop there.** A single minimal pair can pick up an idiosyncrasy of that specific sentence rather than the general mechanism; real circuit-localization work averages this exact procedure over many prompt pairs sharing the same template to wash out per-prompt noise, and reaches for [[Concept - Attribution Graphs|attribution patching]] instead of this per-component loop once the model is too large for a full `layer x position` sweep to be affordable.

## Connections
- [[Concept - Activation Patching]] — the theory and metric design (denoising, corruption choice, confounds) this snippet is a direct implementation of.
- [[Concept - Induction Heads]] — the circuit-discovery methodology this snippet demonstrates is exactly how induction heads and IOI name-mover heads were originally localized.
- [[Deep Dive - Mechanistic Interpretability]] — situates this hands-on example within the field's broader toolkit and research program.
- [[Concept - GPU Memory Hierarchy]] — cross-domain (08) grounding for why caching every layer's activations (`run_with_cache`) is a real memory cost that scales with model size and context length, not a free operation.
- [[Concept - The Logit Lens]] — the cheaper, non-causal alternative to reach for before running a full patching sweep like this one.
- [[Concept - Attention Mechanism]] — cross-domain (03) grounding for what the name-mover heads this heatmap localizes are actually computing via their QK/OV circuits.
- [[Concept - Attribution Graphs]] — the direction to scale this exact idea beyond a small model's tractable `layer x position` sweep.
