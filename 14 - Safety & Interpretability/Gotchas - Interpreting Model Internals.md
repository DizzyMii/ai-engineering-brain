---
tags: [gotchas, domain/safety-interp, level/unicorn]
aliases: [interpretability pitfalls, mech interp gotchas, interpretability illusions]
summary: "The traps that make interpretability results wrong or overclaimed — illusions, SAE pathologies, patching confounds, dark matter."
---

# Gotchas - Interpreting Model Internals

*Interpretability makes it unusually easy to fool yourself. The artifacts are pretty, the stories are compelling, and there's no ground-truth label to check against. These are ordered by how badly each one misleads; the top three are where confidently wrong published circuits come from.*

## 1. Attention weights that "explain" the prediction

**Symptom:** You render the attention heatmap, point at the token a head attends to, and narrate "the model looks at *X* to decide *Y*." Then you permute or zero those weights and the prediction barely moves.
**Cause:** Attention routes and mixes; it doesn't attribute. High weight on a token doesn't mean that token *caused* the logit, because value vectors, downstream MLPs and other heads dominate. The [[Concept - Attention Mechanism]] spreads writes across the residual stream, the softmax weights are one factor among many, and many different weightings give the same output (Jain and Wallace 2019, "Attention is not Explanation"). It's the first trap newcomers fall into.
**Fix:** Swap the heatmap story for a causal test: ablate the head or patch its output and measure the logit change. Use attention maps to *generate* hypotheses, never as evidence for them.
**Detection:** If your only evidence is a pretty attention map, you have no evidence. Wiegreffe and Pinter 2019 ("Attention is not not Explanation") show attention *can* be faithful in restricted setups, but only once you've pinned it down causally.

## 2. A probe "finds" a feature the model never uses

**Symptom:** A linear probe decodes gender / sentiment / truthfulness from layer $L$ at 95% accuracy, and you conclude "the model represents *and uses* concept *X* here."
**Cause:** Probing measures *decodability*, not *usage*. A residual vector of $d_{model}$ dimensions linearly encodes a huge amount of information the forward pass never reads downstream. The probe finds a correlation, and the model may route entirely around that direction. Decodability is necessary for a causal claim and nowhere near sufficient.
**Fix:** Follow every probe with an intervention. Steer or ablate along the probe direction and show the *output* changes. Decodability plus a causal effect is evidence; decodability alone is trivia.
**Detection:** Ask "if I delete this direction, does the behavior change?" If you never ran that experiment, downgrade the claim from *finding* to *hypothesis*.

## 3. The interpretability illusion: a direction that changes meaning across datasets

**Symptom:** A neuron or direction looks cleanly monosemantic ("fires for legal terminology") on your probe set. Swap in a different corpus and the *same* direction means something unrelated.
**Cause:** Directions live in [[Concept - Superposition]] and are polysemantic. One dataset samples only a slice of what a direction responds to, so the clean story you tell is an artifact of your data. Bolukbasi et al. 2021 ("An Interpretability Illusion for BERT") named it: three datasets gave three mutually incompatible "meanings" for one direction.
**Fix:** Validate every feature story on held-out, off-distribution data before publishing. Report a *uniform* sample across the activation range alongside the max-activating examples, since the illusion hides in the tail.
**Detection:** If the feature label came from eyeballing the top-20 activations on one dataset, it's a hypothesis, not a finding.

## 4. Activation patching understates a component because the model self-repairs

**Symptom:** You ablate the head you're sure is responsible and the logit barely drops. You conclude it doesn't matter, but the behavior survived for the wrong reason.
**Cause:** Backup / self-repair heads compensate. Knock out the primary name-mover and a downstream head that was being suppressed picks up the slack: the "hydra effect" (McGrath et al. 2023). Single-node [[Concept - Activation Patching]] therefore *understates* true importance, and denoising (patch clean→corrupt, "is it sufficient?") and noising (corrupt→clean, "is it necessary?") can flatly disagree about the same component.
**Fix:** Patch *sets* of components, not singletons. Use path patching to trace edges instead of nodes, and report both patch directions. Use logit *difference* as the metric (it's linear and lower-variance than raw probability), and design corruptions that change only the variable of interest.
**Detection:** Denoise/noise disagreement, or a "0% important" verdict on a component you have independent reason to trust, gives it away. Heimersheim and Nanda 2024 cover the standard disagreement patterns.

## 5. SAE features split, get absorbed or die as you widen the dictionary

**Symptom:** You train a wider [[Concept - Sparse Autoencoders]] expecting more features and interpretability gets *worse*. One clean concept fractures into 20 near-duplicates, and a "starts with S" feature stops firing.
**Cause:** Three separate pathologies.
- **Feature splitting:** a concept fractures into many latents as width grows. An SAE at $8\times$–$256\times$ $d_{model}$, up to ~34M features on Claude 3 Sonnet, doesn't give you 34M *clean* concepts.
- **Feature absorption** (Chanin et al. 2024): a general feature ("starts with a letter") swallows a specific case ("starts with E"), so the specific latent goes dark whenever the general one fires, breaking monosemanticity.
- **Dead latents:** features that never activate and waste capacity. Early wide SAEs had large dead fractions until TopK / auxiliary-loss tricks (Gao et al. 2024).

**Fix:** Track L0, dead-latent count and absorption metrics as primary numbers. Prefer TopK / JumpReLU / Matryoshka variants, and never equate more latents with more understanding.
**Detection:** A specific feature whose activation drops to zero whenever a more general feature fires is being absorbed. A dead-latent fraction that *rises* as you widen the SAE is a capacity leak.

## 6. Reconstruction looks great, but you've explained a fraction ("dark matter")

**Symptom:** Your SAE recovers 90% of the variance or hits low reconstruction MSE, so you report the layer as "mostly understood."
**Cause:** Reconstruction fidelity isn't mechanistic understanding. A large chunk of activation variance, the "dark matter," isn't captured by any interpretable feature, and even the reconstructed features may not be the units the model computes with. This is the central 2024–2025 critique (Templeton et al. 2024; Engels et al. 2024 on SAE dark matter). Cross-layer transcoders and [[Concept - Attribution Graphs]] go further but carry explicit *error nodes* for what the replacement model misses. That's a feature, not a bug, and a reminder of how much is left over.
**Fix:** Report the *loss recovered* when you splice the SAE or transcoder back into the live model (the honest downstream metric) plus the unexplained variance, not reconstruction MSE alone. Treat every replacement model in [[Deep Dive - Mechanistic Interpretability]] as a lossy approximation with a measured gap.
**Detection:** If you never measured the KL or cross-entropy gap from substituting your interpretation into the running model, you don't know how much you explained.

## 7. The raw logit lens lies in early layers, and feature dashboards are cherry-picked

**Symptom:** You project an early-layer residual through the unembedding, read garbage (or a misleading "prediction"), and either over-read it or give up on the method.
**Cause:** [[Concept - The Logit Lens]] assumes intermediate states already live in the final-layer output basis. Early layers, and models with RMSNorm scaling or rotary positions, break that assumption, so raw readouts are unreliable there. Use the tuned lens (Belrose et al. 2023), a learned per-layer affine probe, for any layer-wise claim. Separately, the attractive feature-visualization dashboards you've seen show *max-activating* examples, the most flattering slice there is, which invites confirmation bias in the circuit narrative.
**Fix:** Use the tuned lens for depth-resolved claims. For feature dashboards, always pair max-activating examples with a uniform random sample across the activation range.
**Detection:** A crisp early-layer logit-lens story that the tuned lens contradicts is a raw-lens artifact, not a discovery.

## 8. Streetlight bias: you study what's easy to find and over-generalize (the meta-gotcha)

**Symptom:** A tidy circuit paper explains one behavior on one prompt family in GPT-2-small and gets cited as "how *the model* works."
**Cause:** We find the features and circuits that are legible (clean linear directions, small tasks, tiny models) and generalize to frontier models and messy behaviors where the method may silently fail. Results are per-prompt and labor-intensive, and the legible subset is emphatically not a random sample of the computation. It's the streetlight problem: searching under the lamppost because that's where the light is.
**Fix:** Hold every mechanistic claim to two bars, a *causal intervention* AND *off-distribution validation*, and bring in the discipline of [[Concept - Statistical Rigor in Model Evaluation]]: report variance, multiple seeds and prompts, and effect sizes, not one hero example.
**Detection:** One prompt, one seed, one model, no intervention → treat it as a hypothesis. If the claim can't survive a held-out prompt distribution, it isn't the algorithm.

## Connections
- [[Concept - Sparse Autoencoders]] — the tool whose pathologies (splitting, absorption, dead latents, dark matter) generate half of this list.
- [[Concept - Activation Patching]] — the causal method whose self-repair and denoise/noise confounds you must control for before trusting a localization.
- [[Concept - The Logit Lens]] — the cheapest probe and the one most likely to mislead in early layers without the tuned-lens correction.
- [[Concept - Superposition]] — why directions are polysemantic, the root cause of the interpretability illusion.
- [[Deep Dive - Mechanistic Interpretability]] — the parent research program these gotchas exist to keep honest; its replacement models are lossy by construction.
- [[Concept - Attribution Graphs]] — the 2025 circuit-tracing method whose explicit error nodes make "dark matter" measurable rather than hidden.
- [[Concept - Statistical Rigor in Model Evaluation]] — the discipline (variance, seeds, effect sizes) that interp routinely skips in favor of single hero examples.
- [[Concept - Attention Mechanism]] — the substrate behind "attention is not explanation": high attention weight is not a causal attribution.

## Sources
- Jain and Wallace (2019) — "Attention is not Explanation." Permuting attention preserves the prediction; heatmaps are not attributions.
- Wiegreffe and Pinter (2019) — "Attention is not not Explanation." Attention can be faithful, but only under explicit causal constraints.
- Bolukbasi et al. (2021) — "An Interpretability Illusion for BERT." One direction, three datasets, three incompatible meanings.
- McGrath et al. (2023) — "The Hydra Effect." Emergent self-repair confounds single-component ablation.
- Heimersheim and Nanda (2024) — "How to use and interpret activation patching." Denoising vs noising and metric pitfalls.
- Chanin et al. (2024) — "A is for Absorption." Feature absorption silently breaks SAE monosemanticity.
- Gao et al. (2024) — "Scaling and evaluating sparse autoencoders." TopK SAEs and dead-latent mitigation.
- Belrose et al. (2023) — "Eliciting Latent Predictions from Transformers with the Tuned Lens." Corrects the raw logit lens.
- Templeton et al. (2024) — "Scaling Monosemanticity." Reconstruction quality is not the model's true features.
- Engels et al. (2024) — decomposing the "dark matter" of SAEs: large unexplained activation variance remains.
- nostalgebraist (2020) — the original logit lens (LessWrong).
