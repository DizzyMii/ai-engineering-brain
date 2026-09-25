---
tags: [concept, domain/esoterica, level/frontier]
aliases: [inverse scaling, U-shaped scaling, the Inverse Scaling Prize]
summary: "Tasks where bigger models get monotonically worse, and the cases where the largest models reverse the trend into a U-shape."
---
> **One-paragraph hook:** [[Concept - Scaling Laws|Scaling laws]] made "bigger is better" feel like a law of nature. Then the Inverse Scaling Prize found eleven tasks where accuracy *falls* monotonically as models grow, and follow-up work showed some of those curves turn back up at the largest scale. The shape is a valley. If capability versus scale can be non-monotone, you can't forecast a large model's behavior by extrapolating a small model's trend. That undercuts the emergent-abilities debate and any safety argument shaped like "bigger is more capable, therefore more predictable."

## The mechanism
McKenzie et al. 2023 ("Inverse Scaling: When Bigger Isn't Better", reporting the Inverse Scaling Prize) collected tasks where larger models score *worse*, evaluated across GPT-3, Gopher/Chinchilla and other families. Eleven tasks won prizes. A sample:
- **Redefine Math.** "Redefine $\pi$ as 462. What is the first digit of $\pi$?" Larger models cling to the memorized value and ignore the redefinition.
- **NeQA / Resisting Correction.** Negated multiple-choice questions ("Which is *not* a mammal?"). Bigger models answer as if the negation weren't there.
- **Hindsight Neglect.** Judging whether a bet was worth taking. Large models lean on whether the outcome happened to be good instead of the expected value.
- **Memo Trap.** "Write a phrase that ends with a word other than the famous one." The pull toward the famous quote overrides the instruction.
- **Modus Tollens.** "If P then Q; not Q; therefore…?" Larger models do *worse* on this valid inference.
- **Pattern-Match Suppression.** The right answer means breaking an obvious surface pattern the model has learned to complete.

The authors sort the causes into **four categories**, and that's the useful mental model:
1. **Strong prior overriding the instruction.** The model "knows" $\pi = 3.14\ldots$ so firmly that a local redefinition can't move it (Redefine Math, Memo Trap).
2. **Imitating undesirable patterns in the training data.** The corpus contains the failure, and scale makes the model imitate it *better* (Hindsight Neglect).
3. **Distractor tasks.** An easier sub-task in the prompt that the model grabs instead of the real one.
4. **Unwanted few-shot pattern-matching.** The examples induce a spurious pattern the model over-applies, ignoring the actual question.

Scale reliably makes the model better at *something*. On prompts built to pit a strong prior or an easy distractor against the instruction, being better at the prior means being worse at the task. Inverse scaling is partly a **measure of prior strength**, and prior strength grows with scale.

## In practice
The downward trend isn't the whole story. Wei et al. 2023 ("Inverse Scaling Can Become U-Shaped") re-ran several of these tasks up to PaLM-540B / U-PaLM and found the curves **turn back up** at the largest scale: accuracy drops, bottoms out, recovers. Their reading: the smallest models ignore the distractor because they can't even see it, mid-size models see the easy sub-task and take the bait, and only the largest models can notice the distractor *and suppress it* to answer the real question. The "inverse scaling" regime was the descending wall of a valley.

```
accuracy
   high |\                                    /
        | \                                  /
        |  \                                /
        |   \___                      _____/     <- U-shape: largest models recover
        |       \___              ___/
    low |           \____________/  <- inverse-scaling valley (distractor captures the model)
        +-----------------------------------------------> model scale (log FLOPs)
          small            mid-size            frontier
```

Two levers change the picture without touching the weights.

**Chain-of-thought.** It flips several inverse-scaling tasks to positive scaling. Add "let's think step by step" and Modus Tollens and the negation tasks recover (see [[Concept - Chain-of-Thought and Why It Works]]). That's strong evidence the failure is often an **inability to allocate the right computation** in one forward pass. The capability is there; given the compute, the model can do it.

**Post-training.** RLHF strengthens instruction-following on some tasks but *also* strengthens instruction-*priors* and sycophancy on others, so a base-model inverse-scaling curve doesn't necessarily survive alignment. See [[Lore - The Sycophancy Problem]] and [[Concept - Sycophancy]]; [[Concept - Mode Collapse in RLHF]] is a further non-monotonicity that comes from post-training, not scale.

Measurement discipline matters as much here as anywhere. Many of these tasks are multiple-choice or exact-match, so the metric-artifact concerns that dominate the emergence debate apply. Put proper uncertainty on the results (see [[Concept - Statistical Rigor in Model Evaluation]]) before declaring a monotone trend.

## Failure modes
- **Extrapolating a small-model trend to a frontier model.** The most dangerous move. A task that looks like clean positive (or negative) scaling at 1B–70B can reverse at 500B+. Don't fit a scaling trend on fewer than three well-separated scales, and treat any monotone extrapolation across an order of magnitude as a hypothesis, not a forecast.
- **Reading inverse scaling as a capability ceiling.** It usually isn't; CoT or more scale often erases it. Before concluding "models fundamentally can't do X" from a zero-shot inverse-scaling curve, try test-time compute.
- **Confusing prior strength with the task.** These tasks pit a prior against an instruction, so an inverse-scaling result partly measures how strong the prior got. That says something about the training distribution. It isn't a defect you can "fix" by scaling.
- **Assuming base-model trends survive alignment.** RLHF can flip the sign. Measure on the checkpoint you actually deploy.

## The non-obvious
Read inverse scaling as **"the direct zero-shot readout is not the model's capability,"** and drop the "bigger is dumber" reading. The tasks expose a gap between what a model *can* compute given enough steps and what it *does* compute in one forward pass under a strong prior, and both chain-of-thought and more scale close that gap. So non-monotone capability versus scale is largely an artifact of *how* you elicit the capability, the same lesson as the metric-artifact side of [[Concept - The Emergent Abilities Debate]].

For anyone forecasting or writing a safety case for a frontier model, a monotone scaling assumption is unsafe in *both* directions. A capability absent at small scale may appear (emergence), and a trend visible at small scale may not continue (inverse scaling can U-turn). The result depends heavily on the elicitation method and the metric, and "we tested it at 7B and it was fine" tells you almost nothing about 500B. That's the measurement problem catalogued in [[Reference - Open Problems in LLM Engineering]].

## Connections
- [[Concept - The Emergent Abilities Debate]] — the direct sibling: inverse and U-shaped scaling are the counter-evidence to monotone capability, and both hinge on the same metric/elicitation dependence.
- [[Concept - Scaling Laws]] — the down-link: inverse scaling is the exception that constrains how far you can trust the smooth loss-vs-compute extrapolation to *task* performance.
- [[Concept - Chain-of-Thought and Why It Works]] — CoT flips several inverse-scaling tasks positive, evidence the failure is compute-allocation, not missing capability.
- [[Concept - Statistical Rigor in Model Evaluation]] — you cannot claim a monotone (or non-monotone) scaling trend without proper uncertainty over the few scales you measured.
- [[Concept - Mode Collapse in RLHF]] — another non-monotonicity introduced by *post-training* rather than scale; RLHF can strengthen the very priors that drive some inverse-scaling failures.
- [[Reference - Open Problems in LLM Engineering]] — the up-link into the broader "measurement problem": what a model can do is genuinely hard to pin down, and inverse scaling is one of the sharpest demonstrations.
- [[Lore - The Sycophancy Problem]] — the folklore up-link: sycophancy and instruction-priors that strengthen with RLHF are the post-training face of prior-over-instruction failures.
- [[Concept - Sycophancy]] — the mechanism by which strengthening instruction-priors can push a model to agree with a premise (e.g. a false redefinition) instead of resisting it.

## Sources
- McKenzie, Lyzhov, Pieler, Parrish, Mueller, Prabhu, ... & Perez (2023) — "Inverse Scaling: When Bigger Isn't Better". Reports the Inverse Scaling Prize, the eleven winning tasks, and the four causal categories.
- Wei, Tay, Bommasani, ... (2023) — "Inverse Scaling Can Become U-Shaped". Shows several inverse-scaling curves reverse at PaLM-540B / U-PaLM scale, and that CoT flips several to positive scaling.
