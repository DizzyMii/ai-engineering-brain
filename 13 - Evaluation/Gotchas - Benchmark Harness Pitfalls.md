---
tags: [gotchas, domain/evaluation, level/advanced]
aliases: []
summary: "Implementation traps that make one model score differently across harnesses: chat templates, acc_norm, few-shot format, tokenizer quirks."
---

A benchmark harness turns a dataset and a model into a number, and every step of that pipeline has an unmarked knob that silently changes the number without changing the model. None of these bugs throw an exception — the harness runs, prints a score, and the score is simply wrong, or right for the wrong reason, or incomparable to the number in someone else's paper. Ordered by how much pain each one causes in practice.

## 1. Running an instruct model without its chat template (or vice versa) swings scores 10-20 points

**Symptom:** Same weights, same benchmark, but the number your harness produces disagrees by ten-plus points with a number reported elsewhere for the identical checkpoint — no code bug, no data change.
**Cause:** Instruction-tuned models are trained on a specific token sequence wrapping every turn — role tags, BOS/EOS placement, a system-prompt slot — as part of the [[Deep Dive - Designing an Eval Harness]] request pipeline. Feed a chat-tuned model raw few-shot text instead of the exact sequence it saw during SFT/RLHF and you're evaluating it off-distribution, the same way any model degrades on out-of-distribution input. Run a base (non-chat) model *through* a chat template and you get the opposite failure: spurious role tokens the model was never trained to parse.
**Fix:** Pull the model's own chat template from its tokenizer config (e.g. `tokenizer.apply_chat_template`) rather than hand-rolling a prompt string; never assume one "Instruction:\n{q}\nAnswer:" format transfers across model families.
**Detection:** Print the fully rendered prompt string the harness actually sends to the model — the single highest-value debugging step on this whole list — and diff it by eye against the model card's documented chat format.

## 2. Comparing a log-likelihood number to a generated-and-parsed number

**Symptom:** Two "MMLU" numbers that should be comparable differ by several points and neither harness has an obvious bug.
**Cause:** [[Concept - Answer Scoring and Normalization]] distinguishes two entirely different measurement regimes: scoring the log-probability the model assigns to each option (cloze/log-likelihood scoring) versus letting the model generate free text and parsing an answer out of it. These are different experiments run over the same benchmark, and they are not guaranteed to rank models identically — a paper reporting one and a leaderboard reporting the other are not comparable numbers even though both say "MMLU."
**Fix:** State which regime you used, and only compare numbers reported under the same regime.
**Detection:** Check the harness's task config for `output_type: loglikelihood` vs `generate_until` — most harnesses (lm-evaluation-harness included) expose this explicitly once you know to look for it.

## 3. acc vs acc_norm silently reorders models by 5-10 points

**Symptom:** Two runs of the same harness on the same model report different accuracy for HellaSwag or ARC depending on a flag you didn't realize you were setting.
**Cause:** Raw option log-likelihood ("acc") is biased toward shorter completions, because a shorter string simply accumulates fewer per-token log-probability penalties. "acc_norm" divides by completion length (byte length, in lm-evaluation-harness) to correct for that bias. Which normalization the original paper used is often unstated, so "acc_norm" is not a single well-defined quantity across harnesses — the two variants can differ 5-10 points and change which model wins.
**Fix:** Report which variant you used at every step; when comparing against a published number, match the exact variant, not just the benchmark name.
**Detection:** Re-run the same eval with both `acc` and `acc_norm` — if the model ranking flips between them, your headline number is an artifact of the normalization choice, not the model.

## 4. Few-shot count, exemplar leakage, and exemplar order move the score more than the model does

**Symptom:** The same model, same benchmark, same harness reports different accuracy across two runs that were supposed to be identical.
**Cause:** Wrong shot count relative to the paper you're comparing against; exemplars accidentally drawn from the benchmark's own test split (leakage); or — the largest and least intuitive effect — exemplar *ordering*. [[Concept - Prompt Format Sensitivity in Evaluation]] documents spreads up to ~76 points from semantically-equivalent formatting changes, and exemplar order alone can move a model from near-random to near-SOTA with zero change to exemplar content.
**Fix:** Fix and version-pin the shot count, the exact exemplar set, and its order; draw exemplars only from a held-out split, never from the test set being scored.
**Detection:** Re-run the eval with a different exemplar order and check the resulting variance — if it's larger than the delta you're trying to report between two models, the comparison isn't meaningful yet.

## 5. Answer-extraction regex misses valid formats and silently undercounts

**Symptom:** A generation-based eval reports a lower score than manual spot-checking of the same transcripts suggests it should.
**Cause:** The parser looks for one answer shape ("The answer is (C)") and the model just as validly writes "C.", "c)", or restates the option text instead of the letter. [[Concept - Multiple-Choice Symbol Binding and Position Bias]] covers the deeper issue that letter-emission and answer-knowledge aren't the same capability — but at the harness level this is simpler: a narrow regex fails to match a correct answer and scores it as wrong.
**Fix:** Use a multi-pattern parser that accepts the common valid variants, and manually audit a random sample of "wrong" answers before trusting the aggregate.
**Detection:** Manually read 20-30 items the harness marked incorrect; if several are visibly correct in substance, the extraction logic — not the model — is the bug.

## 6. Generation truncated before the chain-of-thought reaches its answer

**Symptom:** A model that should benefit from chain-of-thought scores worse on a CoT-prompted eval than on a direct-answer version of the same benchmark.
**Cause:** A stop sequence or `max_new_tokens` budget tuned for short direct answers cuts a longer reasoning trace off before it reaches the final-answer span the parser looks for, especially on math/reasoning tasks where CoT length varies widely per item.
**Fix:** Set generation length budgets generously for CoT-style prompts, sized against the longest legitimate trace you expect, not the median one.
**Detection:** Check the fraction of generations that hit the max-token cutoff rather than a natural stop token — a high hit-rate on that counter is a silent scoring problem, not a model problem.

## 7. Batch nondeterminism and leading-space tokenization flip individual scores

**Symptom:** Re-running the identical eval config on the identical checkpoint produces a slightly different score run to run, or a model's MCQ accuracy looks implausibly close to the random baseline on a task it should handle easily.
**Cause:** Batch composition and padding interact with floating-point reduction order inside matmul kernels to produce small logit differences across runs — rarely enough to flip a real answer, but a genuine source of nondeterminism at the margin. Separately, [[Concept - Byte-Pair Encoding]] tokenizers frequently encode " A" (leading space) and "A" as different token IDs, so scoring the wrong one of the two silently compares the log-probability of a token the option template never actually produces — a scoring bug that looks exactly like a capability gap. Related tokenizer pathologies, including the barely-trained tokens documented in [[Lore - Glitch Tokens]], produce near-arbitrary logits and are a similar silent-corruption vector when one lands inside a prompt template.
**Fix:** Pin batch size and disable nondeterministic kernel paths for eval runs where reproducibility matters; verify which exact token ID the harness scores against by decoding it back to text.
**Detection:** Sanity-check the random baseline on a 4-way MCQ task — if the harness reports meaningfully below 25% on a model that isn't badly broken, suspect a scoring or tokenization bug before suspecting the model.

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
