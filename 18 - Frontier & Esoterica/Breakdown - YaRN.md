---
tags: [breakdown, domain/esoterica, level/advanced]
aliases: [YaRN, Yet another RoPE extensioN, NTK-by-parts]
summary: "RoPE context-extension method that became the community default: wavelength-aware (NTK-by-parts) interpolation plus a closed-form attention-temperature correction."
---

# Breakdown - YaRN

> YaRN ("Yet another RoPE extensioN", Peng et al., Nov 2023) is the method most open-weight long-context checkpoints reach for when they need to push a [[Concept - Rotary Position Embeddings (RoPE)|RoPE]]-based model from its trained context (e.g. 4k) out to 64k–128k. It extends Llama-family models with roughly **10× fewer tokens** and **~2.5× fewer training steps** than plain Position Interpolation, and it does so with two ideas that are individually small and together became a de-facto standard baked into many released long-context models. It matters because it is the concrete, productized form of the [[Concept - RoPE Extrapolation and Context Extension|RoPE-extension theory]].

## The headline numbers

- **Extension range:** Llama 2 7B/13B extended to **64k and 128k** context; the released YaRN checkpoints were among the first widely-used 128k open models.
- **Efficiency:** ~**10×** fewer tokens and ~**2.5×** fewer steps than Position Interpolation (Chen et al. 2023) to reach comparable long-context perplexity.
- **Fine-tune budget:** on the order of **400 steps** on long documents after the frequency rescale — sometimes usable with *no* fine-tuning where NTK-aware alone leaves a residual gap.
- **Parameter cost of the temperature trick:** **zero** — it is a scalar multiply on $q$ and $k$ at inference.

## How it actually works

RoPE rotates each 2D slice $i$ of the query/key by angle $m\theta_i$ at position $m$, with frequencies $\theta_i = \text{base}^{-2i/d}$, $\text{base}=10000$. The wavelength of slice $i$ is $\lambda_i = 2\pi/\theta_i = 2\pi\cdot\text{base}^{2i/d}$: low-$i$ slices spin fast (short wavelength, encode *local* order), high-$i$ slices spin slowly (long wavelength, encode *global* position). Extrapolating to positions $m$ beyond training pushes the slow slices into rotation angles they never saw, and attention degrades.

Position Interpolation's blunt fix is to divide every position by the scale factor $s = L_\text{target}/L_\text{train}$, squeezing all angles back in range. The problem: it compresses the *fast* slices too, blurring the fine local ordering the model relies on.

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

1. **NTK-by-parts: interpolate by wavelength, not uniformly.** This is the core. Each RoPE slice is classified by how many turns it completes within the *original* context, $r_i = L_\text{train}/\lambda_i$. Slices that turn many times (fast, local) are left untouched to preserve local resolution; slices that barely turn (slow, global) are fully interpolated because those are the genuinely out-of-range ones; a linear ramp bridges the middle. This is a refinement of the [[Concept - RoPE Extrapolation and Context Extension|NTK-aware]] "raise the base θ" trick, made per-dimension and principled. It directly beats uniform PI, which destroys high-frequency positional signal.
2. **Attention temperature scaling — the free entropy correction.** Lengthening the context changes the expected magnitude of attention logits and therefore the [[Concept - Softmax|softmax]] entropy: more keys, flatter distribution, weaker recall. YaRN multiplies $q$ and $k$ by a constant factor $1/\sqrt{t} = 0.1\ln(s) + 1$ (empirically tuned for Llama), which sharpens the logits just enough to restore the *pre-extension* attention entropy. It is one line, adds no parameters, and is what lets YaRN work with minimal or no fine-tuning where NTK-aware alone leaves a small perplexity gap. Mechanistically it is the same "control the attention entropy" lever that shows up in training stability work on [[Concept - Attention Entropy Collapse|entropy collapse]] — here used to *raise* entropy back to healthy rather than prevent it crashing.
3. **Dynamic YaRN.** Switch the scale factor $s$ based on the *actual* sequence length at inference, so a 2k prompt keeps full-resolution RoPE and only long prompts pay the interpolation cost — no fixed penalty on short contexts.

## What it got wrong / what's dated

- **Base-θ pretraining ate its lunch.** The blunt production answer turned out to be "just pretrain with a larger base": Llama 3 uses $\theta = 500{,}000$, and some long-context variants use $10^6+$. When you train long-context natively, more slices already have short-enough wavelengths to generalize, and YaRN becomes an *adaptation* tool rather than the primary path. See the RoPE-base row in [[Reference - Architecture Numerology|the numerology table]].
- **Search-based methods reach further.** LongRoPE (Ding et al. 2024) evolutionary-searches per-dimension rescale factors to hit 2M tokens, beyond YaRN's hand-derived taxonomy.
- **Two-regime evaluation is mandatory and often skipped.** Over-large $s$ silently degrades short-context and needle-retrieval quality; you must eval *both* the extended and the original regime, which the [[Playbook - Extending a Model's Context Window|extension playbook]] enforces.

## What to steal

- The **wavelength taxonomy** — decide which RoPE dims to touch by counting turns-per-context — transfers to any positional-scaling scheme.
- The **closed-form temperature correction** $0.1\ln(s)+1$ is a cheap, general fix whenever an intervention changes attention-logit scale; internalize "if you change context length, you changed softmax entropy, so correct it."
- The habit of separating *frequency* handling from *entropy* handling: they are orthogonal levers, and most botched extensions get the first right and forget the second, yielding flat-looking attention and weak long-range recall. When choosing among methods, this is the [[Decision - Choosing a Context Extension Method|context-extension decision]] in miniature; it composes with distributed schemes like [[Concept - Ring Attention and Extreme Context|ring attention]] for truly extreme windows.

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
