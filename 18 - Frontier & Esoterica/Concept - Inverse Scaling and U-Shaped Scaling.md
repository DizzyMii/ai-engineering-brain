---
tags: [concept, domain/esoterica, level/frontier]
aliases: [inverse scaling, U-shaped scaling, the Inverse Scaling Prize]
summary: "Tasks where bigger models get monotonically worse, and the cases where the largest models reverse the trend into a U-shape."
---
> **One-paragraph hook:** [[Concept - Scaling Laws|Scaling laws]] made "bigger is better" feel like a law of nature. Then the Inverse Scaling Prize found eleven tasks where accuracy *falls* monotonically as models grow, and follow-up work showed some of those curves turn back up at the very largest scale — a valley, not a slope. This matters far beyond curiosities: if capability-versus-scale can be non-monotone, you cannot forecast a large model's behavior by extrapolating a small model's trend, which quietly undermines both the emergent-abilities debate and any safety argument of the form "bigger is more capable, therefore more predictable."

## The mechanism
McKenzie et al. 2023 ("Inverse Scaling: When Bigger Isn't Better", reporting the Inverse Scaling Prize) collected tasks where larger models score *worse*, evaluated across the GPT-3, Gopher/Chinchilla, and other model families. Eleven tasks won prizes; the flavor:
- **Redefine Math** — "Redefine $\pi$ as 462. What is the first digit of $\pi$?" Larger models cling to the memorized value and refuse the redefinition.
- **NeQA / Resisting Correction** — negated multiple-choice questions ("Which is *not* a mammal?"); bigger models answer as if the negation weren't there.
- **Hindsight Neglect** — judging whether a bet was worth taking; large models over-rely on whether the outcome happened to be good rather than the expected value.
- **Memo Trap** — "Write a phrase that ends with a word other than the famous one"; the strong prior toward the famous quote overrides the instruction.
- **Modus Tollens** — "If P then Q; not Q; therefore…?"; larger models get this valid inference *worse*.
- **Pattern-Match Suppression** — the correct answer requires breaking an obvious surface pattern the model has learned to complete.

The authors sort the causes into **four categories**, and they are the useful mental model:
1. **Strong prior overriding the instruction** — the model "knows" $\pi = 3.14\ldots$ so hard that a local redefinition can't move it (Redefine Math, Memo Trap).
2. **Imitation of undesirable training-data patterns** — the corpus contains the failure mode, and scale makes the model imitate it *better* (Hindsight Neglect).
3. **Distractor tasks** — an easier sub-task embedded in the prompt that the model latches onto instead of the real one.
4. **Unwanted few-shot pattern-matching** — the few-shot examples induce a spurious pattern the model over-applies, ignoring the actual question.

The through-line: scale reliably improves the model at *something*, but on adversarially-constructed prompts that pit a strong prior or an easy distractor against the actual instruction, "better at the prior" is worse at the task. Inverse scaling is partly a **measure of prior strength**, which grows with scale.

## In practice
The trend is not the end of the story. Wei et al. 2023 ("Inverse Scaling Can Become U-Shaped") re-ran several of these tasks up to PaLM-540B / U-PaLM and found the curves **turn back up** at the largest scale: accuracy goes down, bottoms out, then recovers. The interpretation is that the smallest models ignore the distractor (they can't even see it), mid-size models are captured by it (they see the easy sub-task and take the bait), and only the largest models have the capacity to notice *and suppress* the distractor and answer the real question. The "inverse scaling" regime was the descending wall of a valley.

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

Two levers change the picture without changing the weights:
- **Chain-of-thought flips several inverse-scaling tasks to positive scaling.** Add "let's think step by step" and Modus Tollens / negation tasks recover — see [[Concept - Chain-of-Thought and Why It Works]]. This is strong evidence that the failure is often an **inability to allocate the right computation** in a single forward pass, not a missing capability. Given the compute, the model can do it.
- **Post-training changes the sign.** RLHF strengthens instruction-following on some tasks but *also* strengthens instruction-*priors* and sycophancy on others, so a base-model inverse-scaling curve does not necessarily survive alignment — see [[Lore - The Sycophancy Problem]] and [[Concept - Sycophancy]], and note that [[Concept - Mode Collapse in RLHF]] is a further non-monotonicity introduced by post-training rather than by scale.

Measurement discipline matters here as much as anywhere: many of these tasks are multiple-choice or exact-match, and the same metric-artifact concerns that dominate the emergence debate apply — evaluate with proper uncertainty (see [[Concept - Statistical Rigor in Model Evaluation]]) before declaring a monotone trend.

## Failure modes
- **Extrapolating a small-model trend to a frontier model.** The single most dangerous move: a task that looks like clean positive (or negative) scaling at 1B–70B can reverse at 500B+. Detection: never fit a scaling trend on fewer than three well-separated scales, and treat any monotone extrapolation across an order of magnitude of scale as a hypothesis, not a forecast.
- **Reading inverse scaling as a capability ceiling.** It usually isn't — CoT or more scale often erases it. If you conclude "models fundamentally can't do X" from a zero-shot inverse-scaling curve, test with test-time compute before believing it.
- **Confounding prior-strength with the task.** Because these tasks are built to pit a prior against an instruction, an inverse-scaling result partly measures how strong the prior got — which is a statement about the training distribution, not a defect you can "fix" by scaling.
- **Assuming base-model trends transfer post-alignment.** RLHF can flip the sign; measure on the actually-deployed (aligned) checkpoint.

## The non-obvious
Inverse scaling is best read not as "bigger is dumber" but as **"the direct, zero-shot readout is not the model's capability."** The tasks reveal a gap between what a model *can* compute given enough steps and what it *does* compute in one forward pass under a strong prior — and both chain-of-thought and further scaling close that gap. This reframes the whole monotonicity question: capability-versus-scale being non-monotone is largely an artifact of *how* you elicit the capability, which is the same lesson as the metric-artifact side of the [[Concept - The Emergent Abilities Debate]]. The practical upshot for anyone forecasting or safety-casing a frontier model: a monotone scaling assumption is unsafe in *both* directions. You cannot assume a capability that's absent at small scale stays absent (emergence), and you cannot assume a trend visible at small scale continues (inverse scaling can U-turn). The honest position is that the elicitation method and the metric are load-bearing, and a bare "we tested it at 7B and it was fine" transfers almost nothing to 500B — this is the measurement problem catalogued in [[Reference - Open Problems in LLM Engineering]].

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
