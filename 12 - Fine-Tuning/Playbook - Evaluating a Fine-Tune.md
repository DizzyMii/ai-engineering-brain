---
tags: [playbook, domain/fine-tuning, level/advanced]
aliases: []
summary: "How to verify a fine-tune actually improved the model net of forgetting, overfitting, and judge bias before shipping it."
---

> **Goal:** decide whether a fine-tune is a net win (task gain minus capability regression minus diversity loss) instead of trusting one flattering metric. **When to run this:** every time a [[Playbook - Preparing a Fine-Tuning Dataset]] run produces a checkpoint, before it ships. **Prerequisites:** a held-out task eval set that never touched training, the base model for comparison, and a fixed prompt/inference config so comparisons are apples to apples.

## Steps

1. **Pick the right baseline before touching the fine-tuned model.** Action: run the base model on the same held-out set with the SAME prompt and few-shot examples the fine-tune is meant to replace, not a zero-shot strawman. Expected observation: a real number for "what we'd get without fine-tuning." Deviation: a good prompt frequently beats a mediocre fine-tune outright (see [[Decision - Fine-Tuning vs RAG vs Prompting]]). Skip this step and you can ship a fine-tune that's a regression against a five-minute prompt change.

2. **Score the task metric on a held-out set with a confidence interval.** Action: evaluate on data never seen in training and compute a CI (bootstrap or binomial, per [[Concept - Statistical Rigor in Model Evaluation]]). Expected observation: a metric plus interval, e.g. "72% ± 4%." Deviation: a bare point estimate on a few hundred examples routinely produces "improvements" that are noise. A 3-point gain with a 6-point CI is not a result.

3. **Run the catastrophic-forgetting regression suite before AND after.** Action: probe general capability (an MMLU subset, open-ended chat quality, format-following on unrelated tasks, refusal behavior) on the base and fine-tuned checkpoints (mechanism in [[Concept - Catastrophic Forgetting]]). Expected observation: two numbers you can subtract. Deviation: a fine-tune that gains 5 points on-task and drops 15 points on general capability is net-negative, however good the headline metric looks. This is the most common way teams fool themselves.

4. **Evaluate several checkpoints and pick by held-out metric, not training loss.** Action: keep checkpoints from each epoch (1, 2, 3) and run the full eval suite on each instead of assuming more training is better. Expected observation: the held-out metric often peaks before training loss bottoms out. Eval-loss vs. train-loss divergence is the overfitting signal. Deviation: shipping the final-epoch checkpoint by default is how overfit models, worse on held-out data than the epoch-1 checkpoint, end up in production.

5. **If you use LLM-as-judge, control for its known biases.** Action: run randomized-order pairwise comparison (fine-tuned vs. base output, position randomized) instead of independent absolute scoring (mechanism in [[Concept - LLM-as-Judge]]). Expected observation: a win rate with position balanced across both orders. Deviation: judges show position bias, verbosity bias (longer answers score higher regardless of quality) and self-preference bias (a judge favors outputs in its own family's style). Zheng et al. (2023, "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena") documented all three. An un-randomized single-order judge run will silently favor whichever model answers second, or whichever answer is longer. For how reliable the judge itself is as an instrument, see [[Concept - Meta-Evaluation of LLM Judges]].

6. **Check behavioral robustness under distribution shift.** Action: sample the fine-tuned model at non-zero temperature on out-of-distribution and mildly adversarial variants of the target task (sampling mechanics in [[Concept - Sampling and Decoding Parameters]]), and separately re-run refusal probes (mechanism in [[Concept - Refusal Mechanics]]). Expected observation: the target format holds up outside the exact training distribution, and refusals on harmful requests haven't degraded. Deviation: diversity collapsing to near-identical completions across samples is mode collapse from over-narrow training data. A drop in refusal rate on the safety probes is a silent safety regression that a task-only eval will never show.

7. **Compute the ship gate.** Action: combine the numbers from steps 2, 3, and 6 into one decision, net = task gain − capability regression − diversity-loss penalty, against a threshold agreed beforehand. Expected observation: a clear ship/no-ship call, with data and config logged for reproducibility. Deviation: shipping on the task metric alone, with no threshold agreed in advance, is how a team rationalizes a fine-tune after the fact.

## Verification
- The ship decision reproduces from a logged config: same dataset hash, same base model revision, same eval harness (see [[Deep Dive - Designing an Eval Harness]]), same seed where feasible.
- The regression-suite numbers and the task metric are both reported with intervals.
- At least one human spot-check of 20-30 outputs confirms the automated metric isn't rewarding a degenerate strategy (e.g., always refusing, always outputting the most common label).

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Task metric up, but production complaints increase | Capability regression not measured, or held-out set too narrow | Re-run the full regression suite (step 3); widen the eval set |
| Metric improves every epoch but qualitative outputs degrade | Overfitting to training-set quirks, eval-loss/train-loss divergence unchecked | Compare per-epoch checkpoints on held-out data (step 4), roll back |
| LLM-judge says fine-tune wins big, humans disagree | Judge bias (position, verbosity, self-preference) uncontrolled | Randomize order, control length, spot-check with humans (step 5) |
| Fine-tune "improves" a benchmark suspiciously fast | Train/eval contamination from dataset prep, see [[Concept - Benchmark Contamination]] | Re-run near-dedup between train and eval sets |
| Outputs become repetitive/generic under sampling | Mode collapse from an over-narrow or over-repeated training set | Diversify data, reduce epochs, check with temperature sampling (step 6) |
| Refusal rate drops on safety probes post-FT | Fine-tuning data taught the model to comply more broadly than intended | Add refusal examples to training data (see [[Playbook - Preparing a Fine-Tuning Dataset]]), re-run safety probes |

## Connections
- [[Playbook - Preparing a Fine-Tuning Dataset]] — supplies the held-out eval set and dataset hash this playbook verifies against.
- [[Concept - Catastrophic Forgetting]] — the mechanism behind the regression suite in step 3.
- [[Decision - Fine-Tuning vs RAG vs Prompting]] — the baseline comparison in step 1 is this decision playing out empirically.
- [[Concept - Statistical Rigor in Model Evaluation]] — owns the confidence-interval machinery used in step 2.
- [[Deep Dive - Designing an Eval Harness]] — the infrastructure this playbook assumes exists to run steps 2-6 repeatably.
- [[Concept - LLM-as-Judge]] — owns the judge mechanism and bias catalog used in step 5.
- [[Concept - Meta-Evaluation of LLM Judges]] — the frontier question of how much to trust the judge itself, relevant whenever step 5 is load-bearing.
- [[Concept - Benchmark Contamination]] — the failure this playbook's held-out discipline exists to prevent.
- [[Concept - Sampling and Decoding Parameters]] — owns the temperature/sampling mechanics used in step 6's robustness check.
- [[Concept - Refusal Mechanics]] — owns the mechanism behind the safety-regression check in step 6.

## Sources
- Zheng et al. (2023) — "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." Documents position, verbosity, and self-preference bias in LLM judges — the basis for step 5's randomization requirement.
