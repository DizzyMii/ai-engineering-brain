---
tags: [playbook, domain/esoterica, level/advanced]
aliases: [context extension playbook, RoPE extension procedure]
summary: "End-to-end procedure to extend a RoPE model's context window without wrecking short-context quality or blowing the serving budget."
---

# Playbook - Extending a Model's Context Window

> **Goal:** take a RoPE-based model from its trained context length to a target long-context length without silently breaking short-context quality or exceeding the serving memory budget.
> **When to run this:** you need to serve or fine-tune at a context length materially beyond what the base checkpoint was pretrained on, and "just raise `max_position_embeddings`" has not yet been evaluated by anyone.
> **Prerequisites:** a base RoPE checkpoint, a short-context eval suite and perplexity baseline already in hand, a set of genuinely long documents (not concatenated short ones) if fine-tuning is in scope, and either a method already chosen or the willingness to pick one in Step 2 via [[Decision - Choosing a Context Extension Method]].

## Steps

1. **Establish baselines before touching anything.** Record short-context perplexity, your task eval suite, and a positional-sweep needle-in-a-haystack (NIAH) result at the model's current trained length. → Expected: stable, low-variance curves you can compare against later. → If the baseline itself is noisy across repeated runs, fix the eval before extension — without a clean reference you cannot tell a real regression from measurement noise once the model changes.

2. **Pick the extension method against your budget and target length.** For a modest 2-4x extension with little or no compute, use training-free NTK-aware base-θ scaling; for a larger target with a modest fine-tuning budget, use [[Breakdown - YaRN|YaRN]] (NTK-by-parts interpolation plus attention-temperature scaling, on the order of a few hundred fine-tuning steps) — the default choice for most cases; for extreme targets (>512K-2M tokens), plan on native base-θ pretraining or LongRoPE-style search plus [[Concept - Ring Attention and Extreme Context|ring/context-parallel attention]] to fit the memory. See [[Decision - Choosing a Context Extension Method]] for the full tradeoff matrix. → Expected: a named method and a target scale factor, not "we'll just try things." → Choosing plain Position Interpolation here should be a deliberate simplicity tradeoff, not a default — it costs more fine-tuning tokens than YaRN for equal quality because it compresses every RoPE dimension uniformly.

3. **Compute the scale factor and apply the frequency rescale.** Set $s = L_\text{target}/L_\text{train}$ and apply the chosen method's per-dimension rescaling to [[Concept - RoPE Extrapolation and Context Extension|RoPE's rotation frequencies]] — leaving short-wavelength (local-order) dimensions alone and fully interpolating long-wavelength ones if using NTK-by-parts/YaRN. If using YaRN, also multiply $q$ and $k$ by the attention-temperature factor $0.1\ln(s) + 1$, a parameter-free correction that restores pre-extension attention entropy (see [[Breakdown - YaRN]]). → Expected: attention entropy at the new length close to what it was at the old length. → A scale factor applied uniformly across all dimensions is expected to cost more downstream fine-tuning than a wavelength-aware method — that is the known tradeoff of choosing simplicity in Step 2, not a bug here.

4. **Fine-tune on genuinely long, packed documents.** Run a few hundred steps (YaRN-scale extensions) up to a few thousand (larger scale factors) on long documents packed to actually fill the target sequence length — not many short documents concatenated together, which teaches the wrong positional distribution. → Expected: loss decreases smoothly with no spikes. → A loss spike during this fine-tune shares the signature of general [[Concept - Training Stability and Loss Spikes|training instability]] and usually traces back to attention-entropy collapse at the new position range (see [[Concept - Attention Entropy Collapse]]) — treat it as a stop-and-diagnose signal, not something to push through.

5. **Evaluate both regimes, not just the new one.** Re-run the Step 1 short-context suite alongside a positional-sweep NIAH and a multi-needle/aggregation suite (RULER-style) at the target length. → Expected: long-context gains with short-context metrics unchanged within noise. → The failure signature to catch is long-context improvement bought with short-context regression, or a flat aggregate perplexity curve at the target length that hides a mid-context recall collapse — see [[Gotchas - Long-Context Failure Modes]].

6. **Verify the serving-time reality, not just the checkpoint.** Confirm [[Concept - KV Cache|KV-cache]] memory and prefill latency at the target length are affordable on your actual serving hardware, and if KV-cache quantization is part of the deployment, confirm it still passes the long-context recall eval from Step 5, not just a short-prompt smoke test. → Expected: a target length you can actually afford to fill, not just load. → An extended window that OOMs or blows the latency SLO at the advertised length is a checkpoint property on paper, not a shippable capability.

## Verification

The extension is done when: (a) the Step 1 short-context suite and perplexity are unchanged within noise, (b) positional-sweep NIAH is flat with no mid-context dip out to the target length, (c) a multi-needle/aggregation eval shows real capability at the target length rather than single-needle-only success, and (d) prefill latency and KV memory at the target length are inside the serving budget measured on real hardware. Passing only the aggregate perplexity number at the new length is not sufficient — that number can look fine while mid-context recall is badly broken.

## When it goes wrong

| Symptom | Likely cause | Fix / jump to |
|---|---|---|
| Perplexity fine at target length, but mid-context NIAH fails | Uniform interpolation blurred high-frequency (local-order) dims | Step 2/3 → switch to a wavelength-aware method (YaRN/NTK-by-parts) |
| Short-context quality regressed after extension | Scale factor touched dims that should've been left alone, or fine-tuning drifted the model | Step 3 → protect more high-frequency dims; Step 4 → fewer fine-tune steps or lower LR |
| Perplexity cliffs sharply right at the extension boundary | Scale factor too small for the target length, or fine-tuning data never actually reached that length | Step 3 → recompute $s$; Step 4 → check document lengths actually used |
| Loss spikes during long-context fine-tuning | Attention-entropy collapse at the new position range | Step 4 → confirm QK-norm/soft-capping stabilizers are enabled; see [[Concept - Attention Entropy Collapse]] |
| NIAH passes but multi-needle/aggregation fails | NIAH was never testing the capability the workload needs | Step 5 → this is an eval-design gap, not an extension bug; add RULER-style tasks |
| Extension "works" in eval but OOMs or is too slow in serving | KV memory/prefill cost at target length never checked against real hardware | Step 6 → budget KV memory; consider [[Concept - Ring Attention and Extreme Context|ring attention]] for the memory-bound case |

## Connections
- [[Decision - Choosing a Context Extension Method]] — the tradeoff matrix Step 2 draws the method choice from.
- [[Concept - RoPE Extrapolation and Context Extension]] — the mechanism (out-of-distribution rotation angles, frequency rescaling) this playbook's Step 3 operationalizes; a down-link to the prerequisite theory.
- [[Breakdown - YaRN]] — the specific method (NTK-by-parts plus attention temperature) that's the default choice in Step 2 for most extension targets.
- [[Gotchas - Long-Context Failure Modes]] — the failure catalogue this playbook's dual-regime evaluation (Steps 5-6) exists to catch before it reaches production.
- [[Concept - Ring Attention and Extreme Context]] — the memory-scaling primitive Steps 2 and 6 route to for extreme targets; an up-link to the frontier technique for windows past what frequency rescaling alone can reach.
- [[Concept - KV Cache]] — the memory structure whose serving-time cost Step 6 verifies; a down-link to the serving prerequisite.
- [[Concept - Context Rot]] — the domain-09 framing of effective-vs-nominal context length that motivates evaluating "both regimes" rather than trusting the advertised maximum.
- [[Concept - Training Stability and Loss Spikes]] — the general training-instability mechanism a fine-tuning loss spike in Step 4 is an instance of.
- [[Concept - Attention Entropy Collapse]] — the specific instability (softmax collapsing toward one-hot) behind the loss-spike branch of Step 4's failure table.

## Sources
- Peng et al. (2023) — "YaRN: Efficient Context Window Extension of Large Language Models." The NTK-by-parts plus attention-temperature method this playbook's Step 2 default is built around.
- Liu et al. (2023) — "Ring Attention with Blockwise Transformers for Near-Infinite Context." The memory-parallelism primitive Step 6 routes to for extreme targets.
- Chen et al. (2023) — "Extending Context Window of Large Language Models via Positional Interpolation." The baseline method Step 2 evaluates alternatives against.
