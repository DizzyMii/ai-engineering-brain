---
tags: [gotchas, domain/evaluation, level/advanced]
aliases: []
summary: "Implementation traps that make one model score differently across harnesses: chat templates, acc_norm, few-shot format, tokenizer quirks."
---

A benchmark harness turns a dataset and a model into a number, and every step has an unmarked knob that changes the number without changing the model. None of these bugs throw an exception. The harness runs, prints a score, and the score is wrong, or right for the wrong reason, or not comparable to the number in someone else's paper. Ordered by how much pain each causes in practice.

## 1. Instruct model without its chat template (or the reverse): 10-20 point swings

**Symptom:** Same weights, same benchmark, and your harness's number disagrees by ten-plus points with one reported elsewhere for the identical checkpoint. No code bug, no data change.
**Cause:** Instruction-tuned models are trained on a specific token sequence around every turn: role tags, BOS/EOS placement, a system-prompt slot. That sequence is part of the [[Deep Dive - Designing an Eval Harness]] request pipeline. Feed a chat-tuned model raw few-shot text instead of what it saw in SFT/RLHF and you're evaluating it off-distribution, and it degrades like any model on out-of-distribution input. Push a base model *through* a chat template and you get the opposite failure: role tokens it was never trained to parse.
**Fix:** Take the model's own chat template from its tokenizer config (e.g. `tokenizer.apply_chat_template`) instead of hand-rolling a prompt string. Never assume one "Instruction:\n{q}\nAnswer:" format carries across model families.
**Detection:** Print the fully rendered prompt string the harness sends. It's the most useful debugging step on this list. Compare it by eye with the chat format in the model card.

## 2. Comparing a log-likelihood number to a generated-and-parsed number

**Symptom:** Two "MMLU" numbers that should match differ by several points, and neither harness has an obvious bug.
**Cause:** [[Concept - Answer Scoring and Normalization]] separates two measurement regimes. One scores the log-probability the model assigns to each option (cloze/log-likelihood scoring). The other lets the model generate free text and parses an answer out. They're different experiments on the same benchmark and aren't guaranteed to rank models the same way. A paper reporting one and a leaderboard reporting the other aren't comparable, even though both say "MMLU."
**Fix:** State which regime you used, and compare only numbers from the same regime.
**Detection:** Look for `output_type: loglikelihood` vs `generate_until` in the task config. Most harnesses, lm-evaluation-harness included, expose it once you know to look.

## 3. acc vs acc_norm silently reorders models by 5-10 points

**Symptom:** Two runs of the same harness on the same model give different HellaSwag or ARC accuracy, depending on a flag you didn't realize you were setting.
**Cause:** Raw option log-likelihood ("acc") favors shorter completions, since a shorter string accumulates fewer per-token log-probability penalties. "acc_norm" divides by completion length (byte length, in lm-evaluation-harness) to correct for it. The original paper often doesn't say which normalization it used, so "acc_norm" isn't one well-defined quantity across harnesses. The two variants can differ by 5-10 points and change which model wins.
**Fix:** Report the variant at every step. When comparing against a published number, match the exact variant as well as the benchmark name.
**Detection:** Run the eval with both `acc` and `acc_norm`. If the ranking flips, your headline number is an artifact of normalization.

## 4. Few-shot count, exemplar leakage and exemplar order move the score more than the model does

**Symptom:** Same model, benchmark and harness, two runs that were supposed to be identical, different accuracy.
**Cause:** A shot count that doesn't match the paper you're comparing against; exemplars accidentally drawn from the benchmark's own test split (leakage); or, the largest and least intuitive, exemplar *ordering*. [[Concept - Prompt Format Sensitivity in Evaluation]] documents spreads up to ~76 points from semantically equivalent formatting changes, and exemplar order alone can take a model from near-random to near-SOTA without changing exemplar content.
**Fix:** Version-pin the shot count, the exemplar set and its order. Draw exemplars only from a held-out split, never from the test set being scored.
**Detection:** Re-run with a different exemplar order and look at the variance. If it's bigger than the delta you want to report between two models, the comparison isn't meaningful yet.

## 5. Answer-extraction regex misses valid formats and undercounts

**Symptom:** A generation-based eval scores lower than manual spot checks of the same transcripts suggest.
**Cause:** The parser looks for one answer shape ("The answer is (C)"), and the model writes "C.", "c)", or restates the option text instead of the letter, all equally valid. [[Concept - Multiple-Choice Symbol Binding and Position Bias]] covers the deeper issue that emitting a letter and knowing the answer are different capabilities. At the harness level it's simpler: a narrow regex fails to match a correct answer and scores it wrong.
**Fix:** Use a multi-pattern parser that accepts the common valid variants, and hand-audit a random sample of "wrong" answers before trusting the aggregate.
**Detection:** Read 20-30 items the harness marked incorrect. If several are visibly correct in substance, the bug is in extraction.

## 6. Generation truncated before the chain-of-thought reaches its answer

**Symptom:** A model that should gain from chain-of-thought scores worse on a CoT-prompted eval than on a direct-answer version of the same benchmark.
**Cause:** A stop sequence or `max_new_tokens` budget tuned for short direct answers cuts a longer reasoning trace off before the final-answer span the parser wants. Math and reasoning tasks are worst, since CoT length varies widely per item.
**Fix:** Size generation budgets for CoT prompts against the longest legitimate trace you expect, not the median.
**Detection:** Track the fraction of generations that hit the max-token cutoff instead of a natural stop token. A high rate there is a scoring problem, not a model problem.

## 7. Batch nondeterminism and leading-space tokenization flip individual scores

**Symptom:** The identical config on the identical checkpoint gives a slightly different score each run, or a model's MCQ accuracy sits implausibly close to random on a task it should find easy.
**Cause:** Batch composition and padding interact with floating-point reduction order in matmul kernels and produce small logit differences across runs. That rarely flips a real answer, but it's a real source of nondeterminism at the margin. Separately, [[Concept - Byte-Pair Encoding]] tokenizers frequently encode " A" (leading space) and "A" as different token IDs. Score the wrong one and you're comparing the probability of a token the option template never produces, a scoring bug that looks like a capability gap. Related tokenizer pathologies, such as the barely trained tokens in [[Lore - Glitch Tokens]], give near-arbitrary logits and corrupt results the same silent way when one lands in a prompt template.
**Fix:** Pin batch size and turn off nondeterministic kernel paths for evals where reproducibility matters. Decode the token ID the harness scores back to text to check it.
**Detection:** Sanity-check the random baseline on a 4-way MCQ task. If the harness reports meaningfully below 25% on a model that isn't badly broken, suspect scoring or tokenization before the model.

## Connections

- [[Deep Dive - Designing an Eval Harness]] — the constructive request-to-report pipeline this note's pitfalls are the failure modes of; read it to know what "correct" looks like before reading what breaks.
- [[Concept - Answer Scoring and Normalization]] — the theory behind gotchas #2 and #3; this note gives the operational symptom, that note gives the mechanism.
- [[Concept - Prompt Format Sensitivity in Evaluation]] — the deeper measurement (spreads up to ~76 points) behind gotcha #4's ordering effect.
- [[Concept - Multiple-Choice Symbol Binding and Position Bias]] — the capability-vs-scoring distinction underlying gotcha #5's parser failures.
- [[Concept - Byte-Pair Encoding]] — the tokenizer mechanics (Training at Scale domain) behind gotcha #7's leading-space trap.
- [[Lore - Glitch Tokens]] — the tokenizer-pathology war stories (Frontier & Esoterica domain) that compound gotcha #7 when a template happens to include an under-trained token.

## Sources

- Gao, L. et al. — EleutherAI lm-evaluation-harness. The reference implementation most of these pitfalls are documented against; its issue tracker is a living catalogue of exactly these bugs.
- Liang, P. et al. (2022) — Holistic Evaluation of Language Models (HELM). A second reference harness whose independent scenario x metric design surfaces the same cross-harness disagreement.
- HuggingFace (2023) — "What's Going On With the Open LLM Leaderboard?" Documents the real MMLU-number discrepancy across harnesses that motivates this note.
