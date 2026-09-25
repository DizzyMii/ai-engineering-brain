---
tags: [breakdown, domain/esoterica, level/advanced]
aliases: [YaRN, Yet another RoPE extensioN, NTK-by-parts]
summary: "RoPE context-extension method that became the community default: wavelength-aware (NTK-by-parts) interpolation plus a closed-form attention-temperature correction."
---

# Breakdown - YaRN

> YaRN ("Yet another RoPE extensioN", Peng et al., Nov 2023) is what most open-weight long-context checkpoints use to push a [[Concept - Rotary Position Embeddings (RoPE)|RoPE]]-based model from its trained context (e.g. 4k) out to 64k–128k. It extends Llama-family models with roughly **10× fewer tokens** and **~2.5× fewer training steps** than plain Position Interpolation. It does it with two ideas, each small on its own, that together became a de facto standard baked into many released long-context models. It's the concrete, productized form of the [[Concept - RoPE Extrapolation and Context Extension|RoPE-extension theory]].

## The headline numbers

- **Extension range:** Llama 2 7B/13B extended to **64k and 128k** context. The released YaRN checkpoints were among the first widely used 128k open models.
- **Efficiency:** ~**10×** fewer tokens and ~**2.5×** fewer steps than Position Interpolation (Chen et al. 2023) for comparable long-context perplexity.
- **Fine-tune budget:** on the order of **400 steps** on long documents after the frequency rescale. Sometimes it's usable with *no* fine-tuning, where NTK-aware alone leaves a residual gap.
- **Parameter cost of the temperature trick:** **zero**. It's a scalar multiply on $q$ and $k$ at inference.

## How it actually works

RoPE rotates each 2D slice $i$ of the query/key by angle $m\theta_i$ at position $m$, with frequencies $\theta_i = \text{base}^{-2i/d}$, $\text{base}=10000$. Slice $i$ has wavelength $\lambda_i = 2\pi/\theta_i = 2\pi\cdot\text{base}^{2i/d}$. Low-$i$ slices spin fast (short wavelength, *local* order). High-$i$ slices spin slowly (long wavelength, *global* position). Extrapolating to positions $m$ past training pushes the slow slices into rotation angles they never saw, and attention degrades.

Position Interpolation's blunt fix divides every position by the scale factor $s = L_\text{target}/L_\text{train}$, squeezing all angles back into range. But it compresses the *fast* slices too, blurring the fine local ordering the model depends on.

YaRN's forward path:

```
scale factor  s = L_target / L_train
for each RoPE dimension i:
    wavelength λ_i = 2π · base^(2i/d)
    r_i = L_train / λ_i          # how many full turns fit in original context

    if r_i > β:        # short wavelength (many turns) -> LOCAL, leave alone
        θ'_i = θ_i
    elif r_i < α:      # long wavelength (few turns) -> GLOBAL, fully interpolate
        θ'_i = θ_i / s
    else:              # in-between -> linear ramp between the two
        θ'_i = interp(θ_i, θ_i/s, ramp(r_i))

# attention temperature (applied to q,k at inference):
factor = 0.1 * ln(s) + 1        # = 1/sqrt(t), grows slowly with s
q, k   = q * factor, k * factor
```

```
 RoPE dims sorted by wavelength →
 ┌───────────────┬───────────────────┬───────────────────┐
 │  short λ      │     ramp band      │      long λ       │
 │ (fast/local)  │  (α ≤ r_i ≤ β)     │  (slow/global)    │
 │  leave as-is  │  blend as-is↔/s    │  fully divide /s  │
 └───────────────┴───────────────────┴───────────────────┘
         then multiply q,k by (0.1·ln s + 1)  ← entropy fix
```

## The clever parts

1. **NTK-by-parts: interpolate by wavelength.** This is the core. Each RoPE slice is classified by how many turns it completes within the *original* context, $r_i = L_\text{train}/\lambda_i$. Slices that turn many times (fast, local) stay untouched to keep local resolution. Slices that barely turn (slow, global) are the ones actually out of range, so they're fully interpolated. A linear ramp covers the middle. It refines the [[Concept - RoPE Extrapolation and Context Extension|NTK-aware]] "raise the base θ" trick by doing it per dimension, on a principled basis, and it beats uniform PI, which wipes out high-frequency positional signal.
2. **Attention temperature scaling, a free entropy correction.** A longer context changes the expected size of attention logits and so the [[Concept - Softmax|softmax]] entropy: more keys, flatter distribution, weaker recall. YaRN multiplies $q$ and $k$ by a constant $1/\sqrt{t} = 0.1\ln(s) + 1$ (tuned empirically for Llama), which sharpens the logits just enough to restore the *pre-extension* attention entropy. It's one line with no parameters, and it's what lets YaRN work with little or no fine-tuning where NTK-aware alone leaves a small perplexity gap. Mechanistically it's the same "control attention entropy" lever that shows up in training-stability work on [[Concept - Attention Entropy Collapse|entropy collapse]], used here to *raise* entropy back to a healthy level instead of stopping it from crashing.
3. **Dynamic YaRN.** Set the scale factor $s$ from the *actual* sequence length at inference. A 2k prompt keeps full-resolution RoPE, and only long prompts pay the interpolation cost, so short contexts carry no fixed penalty.

## What it got wrong / what's dated

- **Base-θ pretraining ate its lunch.** The blunt production answer turned out to be "pretrain with a larger base." Llama 3 uses $\theta = 500{,}000$, and some long-context variants use $10^6+$. Train long-context natively and more slices already have wavelengths short enough to generalize, so YaRN becomes an *adaptation* tool instead of the main path. See the RoPE-base row in [[Reference - Architecture Numerology|the numerology table]].
- **Search-based methods go further.** LongRoPE (Ding et al. 2024) uses evolutionary search over per-dimension rescale factors to reach 2M tokens, past YaRN's hand-derived taxonomy.
- **Two-regime evaluation is mandatory and often skipped.** Too large an $s$ silently degrades short-context and needle-retrieval quality. Evaluate *both* the extended and the original regime; the [[Playbook - Extending a Model's Context Window|extension playbook]] enforces this.

## What to steal

- The **wavelength taxonomy** (decide which RoPE dims to touch by counting turns per context) carries over to any positional-scaling scheme.
- The **closed-form temperature correction** $0.1\ln(s)+1$ is a cheap, general fix whenever an intervention changes attention-logit scale. Remember: change context length and you've changed softmax entropy, so correct for it.
- Keep *frequency* handling separate from *entropy* handling. They're independent levers, and most botched extensions get the first right and forget the second, ending up with flat-looking attention and weak long-range recall. Choosing among methods is the [[Decision - Choosing a Context Extension Method|context-extension decision]] in miniature, and YaRN composes with distributed schemes like [[Concept - Ring Attention and Extreme Context|ring attention]] for truly extreme windows.

## Connections
- [[Concept - RoPE Extrapolation and Context Extension]] — the general concept YaRN productizes; read that first for the extrapolation-failure mechanism.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the base construction (θ frequencies, per-slice rotation) YaRN rescales.
- [[Decision - Choosing a Context Extension Method]] — where YaRN sits versus PI, NTK-aware, LongRoPE, and native long-context training.
- [[Playbook - Extending a Model's Context Window]] — the operational procedure that applies YaRN and enforces two-regime evals.
- [[Concept - Attention Entropy Collapse]] — same attention-entropy lever, opposite direction (raise vs prevent-crash).
- [[Gotchas - Long-Context Failure Modes]] — the perplexity cliff, mid-context needle failures, and short-context regressions YaRN can cause if mis-tuned.
- [[Concept - Softmax]] — the entropy the temperature term is engineered to restore.
- [[Concept - Ring Attention and Extreme Context]] — the distributed-attention complement for windows past what frequency rescaling alone reaches.
- [[Reference - Architecture Numerology]] — the RoPE-base and context-scaling constants live in the magic-constants ledger.
- [[Concept - Sampling and Decoding Parameters]] — attention temperature is a distinct knob from sampling temperature; conflating them is a common confusion.
- [[Concept - Context Length Extension]] — the architecture-domain framing of the same extension problem.

## Sources
- Peng et al. (2023) — *YaRN: Efficient Context Window Extension of Large Language Models*. NTK-by-parts + temperature scaling; the 10×-tokens / 2.5×-steps efficiency claims.
- Chen et al. (2023) — *Extending Context Window of LLMs via Position Interpolation*. The uniform-PI baseline YaRN improves on.
- Su et al. (2021) — *RoFormer: Enhanced Transformer with Rotary Position Embedding*. The RoPE construction being rescaled.
- Ding et al. (2024) — *LongRoPE*. Evolutionary per-dim search reaching 2M tokens; the method that reaches past YaRN.
