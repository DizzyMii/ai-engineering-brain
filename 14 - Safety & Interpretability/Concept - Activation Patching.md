---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [causal tracing, causal mediation analysis, resample ablation]
summary: "Swapping cached activations between clean and corrupted runs to causally localize which model component produces a behavior."
---
> **One-paragraph hook:** Reading intermediate activations tells you what a component might be doing; it can't tell you whether the model actually uses it. Activation patching answers the causal question directly: take a component's activation from one run and splice it into another, then measure how much the output moves. It's the workhorse of mechanistic interpretability precisely because it doesn't require guessing what a neuron "means" — you just intervene and watch the consequence, the same logic as a randomized experiment applied to a forward pass.

## The mechanism

Run the model twice on a minimal-pair prompt: a **clean** prompt that produces the behavior of interest, and a **corrupted** prompt that differs in exactly one variable and does not. Cache every intermediate activation from the clean run. Then run the corrupted prompt again, but at one chosen component — a specific `(layer, position)` in the residual stream, an attention head's output, an MLP's activation — overwrite it with the cached clean value, and observe whether the output shifts back toward the clean behavior. If patching in that one component recovers most of the clean-vs-corrupted gap, that component is causally implicated.

There are two mirror-image versions of this test, and they answer different questions:
- **Denoising** — start from the corrupted run, patch in the clean value at one component. Asks: is this component's clean activation *sufficient* to restore clean behavior?
- **Noising** — start from the clean run, patch in the corrupted value at one component. Asks: is this component's normal activation *necessary* — does corrupting it alone break the behavior?

These can disagree. A component can be sufficient-when-restored but not necessary-when-removed if other components compensate for its absence — which is exactly the confound discussed below.

The metric matters as much as the intervention. Use **logit difference** between the correct and a specific incorrect token, not raw probability — it's linear in the unembedding, so effects at different components add rather than interacting through a softmax nonlinearity, and it's less noisy across prompts. Normalize against the clean and corrupted baselines so patching scores are comparable across components and models:

$$\text{score} = \frac{\text{diff}_{\text{patched}} - \text{diff}_{\text{corrupted}}}{\text{diff}_{\text{clean}} - \text{diff}_{\text{corrupted}}}$$

A score of 0 means the patch changed nothing (still behaves corrupted); 1 means it fully recovers clean behavior. Sweeping this over every `(layer, position)` produces the classic patching heatmap.

```
CLEAN RUN            CORRUPTED RUN                 PATCHED RUN
"...John gave         "...John gave                 "...John gave
 a drink to [Mary]"    a drink to [John]"             a drink to [???]"
      │                      │                              │
 cache every            forward pass                  forward pass, but
 activation                                          overwrite ONE component
      │                                                with the CACHED
      └──────────────────────────────────────────────► CLEAN value
                                                              │
                                                    metric shift ⇒ that
                                                  component is causally
                                                       implicated
```

Meng et al. 2022 ("ROME" — *Locating and Editing Factual Associations in GPT*) popularized this under the name **causal tracing**: patching localized factual recall (e.g., "The Eiffel Tower is in ___") to a narrow band of mid-layer MLPs, and — because the localization was causal, not just correlational — the same site could then be *edited* with a rank-one weight update to change the fact. Patching is diagnosis and, once localized, a lever for surgery.

Two refinements matter at scale. **Path/edge patching** (Goldowsky-Dill et al. 2023) patches along one specific computational edge — e.g., only the query input a head reads from a given upstream component — rather than a component's total output, isolating which *path* carries the effect when multiple paths could. **Attribution patching** (Nanda 2023) replaces the expensive one-forward-pass-per-component sweep with a linear approximation: cache activations and gradients on a single corrupted forward+backward pass, then estimate every component's patching effect analytically as $\nabla_a \, \text{metric}(a_{\text{corrupted}}) \cdot (a_{\text{clean}} - a_{\text{corrupted}})$. Two passes instead of thousands makes whole-model attribution tractable on large models — at the cost of being wrong wherever the metric is nonlinear in that activation, so it's used to triage components for exact patching, not as a final answer.

## In practice

The standard workflow: pick a task with a clean minimal-pair corruption (the [[Snippet - Activation Patching with Hooks|IOI task]] — swap the indirect-object name and nothing else — is the canonical example), sweep patches over `resid_pre` at every layer and position for a coarse map, then drill into `attn_out`/`z` at the hot spots for head-level attribution. This is exactly how [[Concept - Induction Heads]] and the IOI circuit's name-mover heads were first pinned down, turning "the model seems to copy names" into a specific, testable claim about specific heads at specific layers.

Corruption design is not incidental — it's the whole experiment. A sloppy corruption (swapping in an unrelated sentence) confounds many variables at once and patching lights up broadly, telling you nothing. A minimal-pair corruption that changes exactly the variable under test is what makes the localization meaningful.

## Failure modes

- **Symptom:** patching shows no single component with a large effect, even though the behavior is clearly real and reproducible. **Cause:** the "hydra effect" — McGrath et al. 2023 documented that ablating one component triggers immediate compensation from downstream backup heads, so single-component patching understates true importance. **Detection:** patch *sets* of components together and compare against the sum of individual effects; a large gap is the signature of redundancy.
- **Symptom:** denoising and noising give contradictory answers about whether a component matters. **Cause:** sufficiency and necessity are genuinely different questions when the circuit has redundant paths — a component can restore behavior when added back (sufficient) without being required in the first place (not necessary) because something else already covered for it. **Detection:** report both directions, not just one; disagreement is itself informative, not a bug to average away.
- **Symptom:** the "circuit" found on one prompt pair doesn't replicate on a slightly different prompt. **Cause:** patching is a per-input causal test — a single pair can pick up idiosyncrasies (a particular token's frequency, an accidental correlation) rather than the general mechanism. **Detection/fix:** average patching scores over many prompt pairs with the same structure before trusting a localization.

## The non-obvious

Attribution patching's two-pass trick is a bigger deal than it looks: it converts causal localization from a research-grade, hours-of-compute exercise (ROME's original tracing) into something cheap enough to run at every layer, every position, every prompt, in a notebook — the difference between "an experiment a paper reports once" and "a diagnostic you run routinely," which is what turned patching into the field's default first move rather than a specialty technique. The whole method also has a hidden precondition worth stating plainly: it only works because the residual stream is a *linear*, shared read/write channel — the same property that makes the [[Concept - The Logit Lens|logit lens]] and [[Concept - Activation Steering|activation steering]] work. Break that linearity (heavy nonlinear mixing between a component's read and write) and patching degrades into noise, which is one reason interpretability tooling lags architectures that deliberately introduce nonlinear cross-layer interactions.

## Connections
- [[Snippet - Activation Patching with Hooks]] — the runnable TransformerLens implementation of exactly this clean/corrupted/patch protocol on the IOI task.
- [[Concept - Induction Heads]] — patching is the tool that discovered and causally validated induction heads as responsible for in-context copying.
- [[Deep Dive - Mechanistic Interpretability]] — patching is the primary causal-intervention method in the broader toolkit this deep dive surveys.
- [[Concept - The Logit Lens]] — the cheaper, purely observational cousin: read a provisional guess before reaching for patching's causal test.
- [[Concept - Attribution Graphs]] — the 2025 generalization of patching from single components to full causal graphs over transcoder features.
- [[Gotchas - Interpreting Model Internals]] — catalogs the hydra effect and faithfulness pitfalls that complicate patching results in practice.
- [[Concept - Backpropagation]] — attribution patching's speedup is literally one backward pass repurposed for causal attribution instead of a parameter update.
- [[Concept - The Residual Stream]] — patching only localizes cleanly because the residual stream is a linear, shared channel every component reads from and writes to.

## Sources
- Meng, Bau, Andonian, Belinkov (2022) — "Locating and Editing Factual Associations in GPT" (ROME). Introduces causal tracing and connects localization to a rank-one weight edit.
- Goldowsky-Dill, MacLeod, Sato, Arora (2023) — "Localizing Model Behavior with Path Patching." Introduces edge-level patching to isolate specific computational paths.
- Nanda (2023) — "Attribution Patching: Activation Patching At Industrial Scale." Introduces the gradient-based linear approximation for whole-model attribution in two passes.
- McGrath, Rahtz, Kramár, Mikulik, Legg (2023) — "The Hydra Effect: Emergent Self-repair in Language Model Computations." Documents backup-head compensation that confounds single-component patching.
