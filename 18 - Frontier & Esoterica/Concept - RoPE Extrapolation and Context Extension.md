---
tags: [concept, domain/esoterica, level/advanced]
aliases: [RoPE scaling, context window extension, position interpolation]
summary: "Why RoPE rotation angles beyond the trained context length are out-of-distribution, and the interpolation/NTK/theta tricks that fix it."
---
> **One-paragraph hook:** Rotary embeddings encode position by rotating query/key vectors, and that rotation is only ever trained up to some maximum position — push a model past its trained context and the rotation angles walk into territory it has literally never seen, so attention degrades sharply rather than gracefully. Every "128k context" or "1M context" release since 2023 is really a story about which frequency-rescaling trick was used to route around this, and picking the wrong one silently wrecks short-context quality while claiming to fix long-context.

## The mechanism
[[Concept - Rotary Position Embeddings (RoPE)]] (Su et al. 2021) encodes the position $m$ of a token by rotating each 2D slice of the query/key vector by angle $m\theta_i$, where $\theta_i = \text{base}^{-2i/d}$ for dimension pair $i$ of $d$ total dimensions, base $=10000$ by default. Low-index dims have high frequency (short wavelength, encode fine-grained local order); high-index dims have low frequency (long wavelength, encode coarse global position). Because post-rotation attention scores depend only on relative position $m-n$, RoPE is elegant and cheap — but the rotation angles for positions past the training length $L_\text{train}$ are out-of-distribution: gradient descent only ever shaped attention logits to behave sensibly for angles it actually saw, and nothing forces graceful behavior outside that range. Extrapolation is not free; scores degrade sharply, not gracefully.

The fix family works by keeping the *effective* angles in-distribution at inference:

- **Position Interpolation** (Chen et al. 2023): linearly rescale every position by $L_\text{train}/L_\text{target}$ before applying RoPE, so no angle exceeds what was seen in training. Requires ~1000 fine-tuning steps because it compresses *all* frequencies uniformly, including the high-frequency dims that encode fine local order — squeeze those and local token-adjacency resolution blurs.
- **NTK-aware scaling** (folklore from r/LocalLLaMA, bloc97 2023, later formalized): instead of scaling positions, scale the base $\theta$ up. Low-index (high-frequency) dims have short wavelength and are barely perturbed by a bigger base; high-index (low-frequency) dims get stretched the most. This unevenly protects the dims that carry local order and often needs little or no fine-tuning.
- **NTK-by-parts**: formalizes the NTK-aware intuition with an explicit wavelength criterion — dims whose wavelength already exceeds $L_\text{train}$ get fully interpolated, dims well inside the trained range are left untouched, and a ramp interpolates the middle band. This wavelength taxonomy is the conceptual core productized as [[Breakdown - YaRN]].
- **Base-theta retraining**: the blunt production answer — pretrain with a larger base from the start. Llama 3 uses $\theta=500000$ (versus the original 10000); some long-context variants push past $10^6$. A larger base pushes more dimensions into "long wavelength relative to context" territory, so more of the position encoding generalizes natively with no inference-time trick at all.
- **LongRoPE** (Ding et al. 2024) evolutionary-searches per-dimension rescale factors rather than using a hand-derived wavelength rule, reaching context windows past 2M tokens.

## In practice
Production choice depends on whether you're extending an existing checkpoint or training long-context from scratch. Extending Llama-family checkpoints to 64k–128k with minimal compute is the domain of [[Breakdown - YaRN]], which composes NTK-by-parts rescaling with an attention-temperature correction — a fix for the same logit-magnitude sensitivity that shows up as [[Concept - Attention Entropy Collapse]] during training — and typically needs only ~400 fine-tuning steps. Labs training natively for long context skip the trick entirely and just set a large base $\theta$ during pretraining, which is why "raise theta" shows up over and over as the production default rather than any of the cleverer interpolation schemes. See [[Playbook - Extending a Model's Context Window]] for the operational sequence and [[Decision - Choosing a Context Extension Method]] for picking among PI, NTK-aware, YaRN, and native long-base pretraining given a compute budget. Once positions generalize to the target length, actually computing and serving attention over that many tokens without blowing device memory is a separate problem — the domain of [[Concept - Ring Attention and Extreme Context]] on the compute side and [[Concept - KV Cache]] growth on the memory side.

## Failure modes
The signature failure is a **perplexity cliff**: loss stays flat out to the extension boundary, then jumps discontinuously past it — a sign the rescale under-covers the target length. A second, more insidious failure is **degraded short-context quality**: any method that touches high-frequency dims (uniform PI, over-aggressive NTK scale factors) blurs local positional resolution, so the *original* context range gets worse even as long-context improves — you must eval both regimes, not just the new one. Needle-in-a-haystack tests often "pass near the ends but fail mid-context," because attention entropy and recall degrade non-uniformly across a long window even when aggregate perplexity looks fine; see [[Gotchas - Long-Context Failure Modes]] for the full symptom catalog.

## The non-obvious
The frequency-domain reasoning generalizes: any positional scheme built from multiple frequency bands has some dims encoding "am I next to this token" and others encoding "roughly where in the document am I" — a context-extension trick that treats all dims identically is implicitly betting those two jobs don't need different treatment. They do. NTK-by-parts and YaRN's win over plain Position Interpolation is entirely this distinction, discovered as community folklore (bloc97's NTK-aware post) *before* it was formalized in a paper — one of the cleaner cases in this vault of practitioner tinkering outrunning the literature. A related interaction: RoPE-based extension must preserve early positions or the [[Concept - Attention Sinks]] mechanism drifts, since sink tokens rely on a stable low-position representation that frequency rescaling can perturb if applied carelessly.

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
