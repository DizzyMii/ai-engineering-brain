---
tags: [concept, domain/safety-interp, level/advanced]
aliases: [causal tracing, causal mediation analysis, resample ablation]
summary: "Swapping cached activations between clean and corrupted runs to causally localize which model component produces a behavior."
---
> **One-paragraph hook:** Reading intermediate activations tells you what a component might be doing. It can't tell you whether the model actually uses it. Activation patching answers that causal question: take a component's activation from one run, splice it into another, and measure how far the output moves. It's the workhorse of mechanistic interpretability because you never have to guess what a neuron "means." You intervene and watch what happens, the logic of a randomized experiment applied to a forward pass.

## The mechanism

Run the model twice on a minimal-pair prompt. The **clean** prompt produces the behavior of interest; the **corrupted** prompt differs in exactly one variable and doesn't. Cache every intermediate activation from the clean run. Then rerun the corrupted prompt, overwrite one chosen component with its cached clean value (a specific `(layer, position)` in the residual stream, an attention head's output, an MLP's activation), and see whether the output shifts back toward clean. If patching that one component recovers most of the clean-vs-corrupted gap, the component is causally implicated.

The test comes in two mirror-image versions that answer different questions:
- **Denoising**: start from the corrupted run and patch in the clean value at one component. Is this component's clean activation *sufficient* to restore clean behavior?
- **Noising**: start from the clean run and patch in the corrupted value at one component. Is its normal activation *necessary*, so that corrupting it alone breaks the behavior?

They can disagree. A component can be sufficient when restored but not necessary when removed, if other components cover for its absence. That's the confound discussed below.

The metric matters as much as the intervention. Use the **logit difference** between the correct token and a specific incorrect one, not raw probability. It's linear in the unembedding, so effects at different components add instead of interacting through a softmax, and it's less noisy across prompts. Normalize against the clean and corrupted baselines so scores compare across components and models:

$$\text{score} = \frac{\text{diff}_{\text{patched}} - \text{diff}_{\text{corrupted}}}{\text{diff}_{\text{clean}} - \text{diff}_{\text{corrupted}}}$$

A score of 0 means the patch changed nothing (still behaves corrupted); 1 means it fully recovers clean behavior. Sweep it over every `(layer, position)` and you get the classic patching heatmap.

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

Meng et al. 2022 ("ROME", *Locating and Editing Factual Associations in GPT*) popularized this as **causal tracing**. Patching localized factual recall ("The Eiffel Tower is in ___") to a narrow band of mid-layer MLPs. Because the localization was causal and not merely correlational, the same site could then be *edited* with a rank-one weight update to change the fact. Patching diagnoses, and once it has localized something, it gives you a place to operate.

Two refinements matter at scale. **Path/edge patching** (Goldowsky-Dill et al. 2023) patches along one computational edge, e.g. only the query input a head reads from a given upstream component, instead of a component's whole output. That isolates which *path* carries the effect when several could. **Attribution patching** (Nanda 2023) replaces the one-forward-pass-per-component sweep with a linear approximation: cache activations and gradients on one corrupted forward+backward pass, then estimate every component's patching effect as $\nabla_a \, \text{metric}(a_{\text{corrupted}}) \cdot (a_{\text{clean}} - a_{\text{corrupted}})$. Two passes instead of thousands makes whole-model attribution tractable on large models. It's wrong wherever the metric is nonlinear in that activation, so use it to triage components for exact patching, not as the final answer.

## In practice

The standard workflow: pick a task with a clean minimal-pair corruption (the [[Snippet - Activation Patching with Hooks|IOI task]], which swaps the indirect-object name and nothing else, is the usual example). Sweep patches over `resid_pre` at every layer and position for a coarse map, then drill into `attn_out`/`z` at the hot spots for head-level attribution. That's how [[Concept - Induction Heads]] and the IOI circuit's name-mover heads were first pinned down, turning "the model seems to copy names" into a testable claim about specific heads at specific layers.

Corruption design is the whole experiment. A sloppy corruption (swapping in an unrelated sentence) changes many variables at once, patching lights up everywhere, and you learn nothing. A minimal pair that changes only the variable under test is what makes the localization mean something.

## Failure modes

- **Symptom:** no single component shows a large effect, though the behavior is clearly real and reproducible. **Cause:** the "hydra effect." McGrath et al. 2023 documented that ablating one component triggers immediate compensation from downstream backup heads, so single-component patching understates importance. **Detection:** patch *sets* of components together and compare with the sum of individual effects. A large gap signals redundancy.
- **Symptom:** denoising and noising disagree about whether a component matters. **Cause:** with redundant paths, sufficiency and necessity really are different questions. A component can restore behavior when added back (sufficient) without being required (not necessary), because something else already covered for it. **Detection:** report both directions. Disagreement is information, not a bug to average away.
- **Symptom:** the "circuit" from one prompt pair doesn't replicate on a slightly different prompt. **Cause:** patching is a per-input causal test, and one pair can pick up idiosyncrasies (a token's frequency, an accidental correlation) instead of the general mechanism. **Detection/fix:** average scores over many prompt pairs with the same structure before trusting a localization.

## The non-obvious

Attribution patching's two-pass trick matters more than it looks. It took causal localization from a research-grade exercise costing hours of compute (ROME's original tracing) to something cheap enough to run at every layer, position and prompt in a notebook. Patching went from an experiment a paper reports once to a routine diagnostic, and that's why it became the field's default first move.

The method also has a hidden precondition. It only works because the residual stream is a *linear*, shared read/write channel, the same property behind the [[Concept - The Logit Lens|logit lens]] and [[Concept - Activation Steering|activation steering]]. Break that linearity with heavy nonlinear mixing between a component's read and write, and patching turns to noise. That's one reason interpretability tooling lags architectures that deliberately add nonlinear cross-layer interactions.

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
