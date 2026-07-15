---
tags: [gotchas, domain/safety-interp, level/unicorn]
aliases: [interpretability pitfalls, mech interp gotchas, interpretability illusions]
summary: "The traps that make interpretability results wrong or overclaimed — illusions, SAE pathologies, patching confounds, dark matter."
---

# Gotchas - Interpreting Model Internals

*Interpretability is uniquely easy to fool yourself with: the artifacts are pretty, the stories are compelling, and there is no ground-truth label to check against. Ordered below by how badly each one misleads — the top three are where confidently-wrong published circuits come from.*

## 1. Attention weights that "explain" the prediction

**Symptom:** You render the attention heatmap, point at the token a head attends to, and narrate "the model looks at *X* to decide *Y*." Then you permute or zero those weights and the prediction barely moves.
**Cause:** Attention is a routing/mixing operation, not an attribution. High weight on a token does not mean that token *caused* the logit — the value vectors, downstream MLPs, and other heads dominate. The [[Concept - Attention Mechanism]] distributes writes across the residual stream; the softmax weights are one factor among many, and many different weightings produce the same output (Jain and Wallace 2019, "Attention is not Explanation"). This is the first trap newcomers fall into.
**Fix:** Replace the heatmap story with a causal test — ablate the head, or patch its output, and measure the logit change. Use attention maps to *generate* hypotheses, never as evidence for them.
**Detection:** If your only evidence is a pretty attention map, you have no evidence. Wiegreffe and Pinter 2019 ("Attention is not not Explanation") show attention *can* be faithful in restricted setups — but only once you have pinned it down causally.

## 2. A probe "finds" a feature the model never uses

**Symptom:** A linear probe decodes gender / sentiment / truthfulness from layer $L$ at 95% accuracy, and you conclude "the model represents *and uses* concept *X* here."
**Cause:** Probing measures *decodability*, not *usage*. A residual vector of $d_{model}$ dimensions linearly encodes an enormous amount of information the forward pass never reads downstream. The probe finds a correlation; the model may route entirely around that direction. Decodability is necessary but nowhere near sufficient for a causal claim.
**Fix:** Follow every probe with an intervention — steer or ablate along the probe direction and show the *output* changes. Decodability + a causal effect is evidence; decodability alone is a factoid.
**Detection:** Ask "if I delete this direction, does the behavior change?" If you never ran that experiment, downgrade the claim from *finding* to *hypothesis*.

## 3. The interpretability illusion — a direction that changes meaning across datasets

**Symptom:** A neuron or direction looks crisply monosemantic ("this fires for legal terminology") on your probe set. Swap in a different corpus and the *same* direction means something unrelated.
**Cause:** Directions live in [[Concept - Superposition]] and are polysemantic; a single dataset samples only a slice of what a direction responds to, so you narrate a clean story that is an artifact of your data. Bolukbasi et al. 2021 ("An Interpretability Illusion for BERT") named it: three datasets gave three mutually incompatible "meanings" for one direction.
**Fix:** Validate every feature story on held-out, off-distribution data before you publish it. Report not just the max-activating examples but a *uniform* sample across the activation range — the tail is where the illusion hides.
**Detection:** If your feature label came from eyeballing the top-20 activations on one dataset, it is a hypothesis, not a finding.

## 4. Activation patching understates a component because the model self-repairs

**Symptom:** You ablate the head you are sure is responsible; the logit barely drops. You conclude it does not matter — but the behavior survives for the wrong reason.
**Cause:** Backup / self-repair heads compensate. Knock out the primary name-mover and a downstream head that was previously suppressed picks up the slack — the "hydra effect" (McGrath et al. 2023). [[Concept - Activation Patching]] on a single node therefore *understates* its true importance, and denoising (patch clean→corrupt, "is it sufficient") and noising (corrupt→clean, "is it necessary") can flatly disagree about the same component.
**Fix:** Patch *sets* of components, not singletons; use path patching to trace edges rather than nodes; report both patch directions. Use the logit *difference* as your metric (it is linear and lower-variance than raw probability), and design corruptions that change only the variable of interest.
**Detection:** Denoise/noise disagreement, or a "0% important" verdict on a component you have independent reason to trust, is the tell. See Heimersheim and Nanda 2024 for the standard disagreement patterns.

## 5. SAE features split, get absorbed, or die as you widen the dictionary

**Symptom:** You train a wider [[Concept - Sparse Autoencoders]] expecting "more features," and interpretability gets *worse*: one clean concept fractures into 20 near-duplicates, and a "starts with S" feature quietly stops firing.
**Cause:** Three distinct pathologies. **Feature splitting** — a concept fractures into many latents as width grows (an SAE at $8\times$–$256\times$ $d_{model}$, up to ~34M features on Claude 3 Sonnet, does not give you 34M *clean* concepts). **Feature absorption** (Chanin et al. 2024) — a general feature ("starts with a letter") swallows a specific case ("starts with E"), so the specific latent silently goes dark exactly when the general one fires, breaking monosemanticity. **Dead latents** — features that never activate, wasting capacity; early wide SAEs saw large dead fractions until TopK / auxiliary-loss tricks (Gao et al. 2024).
**Fix:** Track L0, dead-latent count, and absorption metrics as first-class numbers, not afterthoughts; prefer TopK / JumpReLU / Matryoshka variants; and never equate "more latents" with "more understanding."
**Detection:** A specific feature whose activation collapses to zero precisely when a more general feature fires is being absorbed. A dead-latent fraction that *rises* as you widen the SAE is the capacity leak.

## 6. Reconstruction looks great, but you have explained a fraction — "dark matter"

**Symptom:** Your SAE recovers 90% of the variance / hits low reconstruction MSE, so you report the layer is "mostly understood."
**Cause:** Reconstruction fidelity is not mechanistic understanding. A large chunk of activation variance — the "dark matter" — is not captured by any interpretable feature, and even the reconstructed features may not be the units the model actually computes with. This is the central 2024–2025 critique (Templeton et al. 2024; Engels et al. 2024 on SAE dark matter). Cross-layer transcoders and [[Concept - Attribution Graphs]] push further but carry explicit *error nodes* accounting for what the replacement model misses — a feature, not a bug, and a reminder of how much is left over.
**Fix:** Report the *loss recovered* when you splice the SAE / transcoder back into the live model (the honest downstream metric), plus the unexplained variance — not reconstruction MSE alone. Treat every replacement model in [[Deep Dive - Mechanistic Interpretability]] as a lossy approximation with a measured gap.
**Detection:** If you never measured the KL or cross-entropy gap from substituting your interpretation into the running model, you do not know how much you explained.

## 7. The raw logit lens lies in early layers, and feature dashboards are cherry-picked

**Symptom:** You project an early-layer residual through the unembedding, read garbage (or a misleading "prediction"), and either over-read it or throw the method out.
**Cause:** [[Concept - The Logit Lens]] assumes intermediate states already live in the final-layer output basis. Early layers, and models with RMSNorm scaling or rotary positions, violate that, so raw readouts are unreliable there — use the tuned lens (Belrose et al. 2023), a learned per-layer affine probe, for any layer-wise claim. Separately, the beautiful feature-visualization dashboards you have seen show *max-activating* examples — the single most flattering slice — which invites confirmation bias in the circuit narrative.
**Fix:** Use the tuned lens for depth-resolved claims; for feature dashboards, always pair max-activating examples with a uniform random sample across the activation range.
**Detection:** A crisp early-layer logit-lens story that the tuned lens contradicts is a raw-lens artifact, not a discovery.

## 8. Streetlight bias — you study what is easy to find and over-generalize (the meta-gotcha)

**Symptom:** A tidy circuit paper explains one behavior on one prompt family in GPT-2-small, and gets cited as "how *the model* works."
**Cause:** We find the features and circuits that are legible — clean linear directions, small tasks, tiny models — and generalize to frontier models and messy behaviors where the method may silently fail. Results are per-prompt and labor-intensive; the legible subset is emphatically not a random sample of the computation. This is the streetlight problem: searching under the lamppost because that is where the light is.
**Fix:** Hold every mechanistic claim to two bars — a *causal intervention* AND *off-distribution validation* — and import the evaluation discipline of [[Concept - Statistical Rigor in Model Evaluation]]: report variance, multiple seeds and prompts, and effect sizes, not one hero example.
**Detection:** One prompt, one seed, one model, no intervention → treat as a hypothesis. If the claim cannot survive a held-out prompt distribution, it is not the algorithm.

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
