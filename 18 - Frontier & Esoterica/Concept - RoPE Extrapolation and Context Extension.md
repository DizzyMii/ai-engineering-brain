---
tags: [concept, domain/esoterica, level/advanced]
aliases: [RoPE scaling, context window extension, position interpolation]
summary: "Why RoPE rotation angles beyond the trained context length are out-of-distribution, and the interpolation/NTK/theta tricks that fix it."
---
> **One-paragraph hook:** Rotary embeddings encode position by rotating query/key vectors, and the rotation is only trained up to some maximum position. Push a model past its trained context and the angles go somewhere it has literally never seen, so attention degrades sharply instead of gracefully. Every "128k context" or "1M context" release since 2023 comes down to which frequency-rescaling trick got around this, and the wrong one silently wrecks short-context quality while claiming to fix long context.

## The mechanism
[[Concept - Rotary Position Embeddings (RoPE)]] (Su et al. 2021) encodes a token's position $m$ by rotating each 2D slice of the query/key vector by angle $m\theta_i$, where $\theta_i = \text{base}^{-2i/d}$ for dimension pair $i$ of $d$ total dimensions and base $=10000$ by default. Low-index dims have high frequency (short wavelength, fine-grained local order). High-index dims have low frequency (long wavelength, coarse global position). Post-rotation attention scores depend only on relative position $m-n$, which makes RoPE elegant and cheap. But angles for positions past the training length $L_\text{train}$ are out-of-distribution. Gradient descent only shaped the attention logits for angles it saw, and nothing makes behavior outside that range graceful. Extrapolation isn't free: scores degrade sharply.

Every fix keeps the *effective* angles in-distribution at inference.

**Position Interpolation** (Chen et al. 2023) linearly rescales every position by $L_\text{train}/L_\text{target}$ before applying RoPE, so no angle exceeds what training saw. It needs ~1000 fine-tuning steps because it compresses *all* frequencies uniformly, including the high-frequency dims that encode fine local order. Squeeze those and token-adjacency resolution blurs.

**NTK-aware scaling** (folklore from r/LocalLLaMA, bloc97 2023, later formalized) scales the base $\theta$ up and leaves positions alone. High-frequency (low-index) dims have short wavelengths and barely move under a bigger base; low-frequency (high-index) dims stretch the most. The dims that carry local order get protected, and it often needs little or no fine-tuning.

**NTK-by-parts** formalizes that intuition with an explicit wavelength rule. Dims whose wavelength already exceeds $L_\text{train}$ are fully interpolated, dims well inside the trained range are left alone, and a ramp handles the middle band. [[Breakdown - YaRN]] productizes this wavelength taxonomy.

**Base-theta retraining** is the blunt production answer: pretrain with a larger base from the start. Llama 3 uses $\theta=500000$ (versus the original 10000), and some long-context variants go past $10^6$. A larger base puts more dimensions in "long wavelength relative to context" territory, so more of the position encoding generalizes natively with no inference-time trick.

**LongRoPE** (Ding et al. 2024) uses evolutionary search to find per-dimension rescale factors in place of a hand-derived wavelength rule, and reaches context windows past 2M tokens.

## In practice
The choice depends on whether you're extending an existing checkpoint or training long-context from scratch. Extending Llama-family checkpoints to 64k–128k on minimal compute is [[Breakdown - YaRN]]'s job. It combines NTK-by-parts rescaling with an attention-temperature correction (aimed at the same logit-magnitude sensitivity that shows up as [[Concept - Attention Entropy Collapse]] in training) and typically needs only ~400 fine-tuning steps. Labs training natively for long context skip the trick and set a large base $\theta$ in pretraining, which is why "raise theta" keeps showing up as the production default over the cleverer interpolation schemes.

[[Playbook - Extending a Model's Context Window]] has the operational sequence, and [[Decision - Choosing a Context Extension Method]] covers picking among PI, NTK-aware, YaRN and native long-base pretraining for a given compute budget. Once positions generalize to the target length, computing and serving attention over that many tokens without blowing device memory is a separate problem: [[Concept - Ring Attention and Extreme Context]] on the compute side, [[Concept - KV Cache]] growth on the memory side.

## Failure modes
The signature failure is a **perplexity cliff**. Loss stays flat out to the extension boundary, then jumps discontinuously past it, meaning the rescale under-covers the target length.

The sneakier one is **degraded short-context quality**. Any method that touches the high-frequency dims (uniform PI, over-aggressive NTK scale factors) blurs local positional resolution, so the *original* context range gets worse while long context improves. Evaluate both regimes, not only the new one.

Needle-in-a-haystack tests often pass near the ends and fail mid-context, because attention entropy and recall degrade unevenly across a long window even when aggregate perplexity looks fine. [[Gotchas - Long-Context Failure Modes]] has the full symptom catalog.

## The non-obvious
The frequency-domain argument generalizes. Any positional scheme built from several frequency bands has some dims answering "am I next to this token" and others answering "roughly where in the document am I." An extension trick that treats all dims the same is betting those two jobs need the same treatment. They don't. NTK-by-parts and YaRN beat plain Position Interpolation entirely because of this distinction, and the community found it (bloc97's NTK-aware post) *before* any paper formalized it, one of the cleaner cases in this vault of practitioner tinkering outrunning the literature.

A related interaction: RoPE-based extension has to preserve early positions or the [[Concept - Attention Sinks]] mechanism drifts. Sink tokens rely on a stable low-position representation that careless frequency rescaling can perturb.

## Connections
- [[Concept - Rotary Position Embeddings (RoPE)]] — the base construction whose extrapolation failure and fix family this note covers.
- [[Breakdown - YaRN]] — the productized version of NTK-by-parts scaling plus the attention-temperature correction.
- [[Decision - Choosing a Context Extension Method]] — the tradeoff table for picking PI vs NTK-aware vs YaRN vs native long-base pretraining.
- [[Playbook - Extending a Model's Context Window]] — the operational procedure for actually running an extension.
- [[Gotchas - Long-Context Failure Modes]] — the symptom catalog (perplexity cliffs, mid-context recall loss) this note's failure modes feed into.
- [[Concept - Ring Attention and Extreme Context]] — the orthogonal axis of context scaling: distributing the attention computation itself across devices once positions generalize.
- [[Concept - Attention Entropy Collapse]] — the related logit-magnitude instability that YaRN's temperature correction exists to control at extended lengths.
- [[Concept - KV Cache]] — the memory cost that grows linearly with the context you're extending into, and the practical ceiling on how far extension helps without paging or offloading.
- [[Concept - Attention Sinks]] — the position-0 stability mechanism that naive frequency rescaling can silently break.

## Sources
- Su et al. (2021) — RoFormer: Enhanced Transformer with Rotary Position Embedding. The original RoPE construction.
- Chen et al. (2023) — Extending Context Window of Large Language Models via Positional Interpolation. Introduces linear position interpolation.
- Peng et al. (2023) — YaRN: Efficient Context Window Extension of Large Language Models. NTK-by-parts plus attention temperature scaling.
- Ding et al. (2024) — LongRoPE: Extending LLM Context Window Beyond 2 Million Tokens. Evolutionary search over per-dimension rescale factors.
