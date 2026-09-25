---
tags: [concept, domain/evaluation, level/unicorn]
aliases: [format sensitivity, prompt lottery, FormatSpread, prompt format variance]
summary: "Semantically-equivalent formatting changes swing benchmark scores by many points and can flip model rankings at fixed weights."
---
> **One-paragraph hook:** Change a colon to a parenthesis. Change "Answer:" to "answer:". Put a newline where a space was. None of these change what the prompt means, and all of them can move a benchmark score by several points, sometimes by dozens. Worse, the format that flatters model X can penalize model Y, so a single-format evaluation can *invert the ranking* between two models at fixed weights and fixed data, on top of adding noise. A lot of irreproducible leaderboard results come down to this. The reported gap between two models is frequently smaller than the gap either model shows across trivial reformattings of the same benchmark, and almost nobody reports that spread.

## The mechanism

A language model doesn't consume "the question." It consumes a specific token sequence, and its output distribution depends on that sequence, including every separator, capitalization and whitespace choice a human reads straight past. Semantically equivalent formats produce *different token sequences*, and nothing guarantees invariance across them because nothing in pretraining or post-training enforced it.

The standard measurement is **FormatSpread** (Sclar et al. 2023/2024, "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design"). They defined a space of semantically equivalent format variations (separator choice, spacing, casing of cue words, option delimiters, field ordering) and searched it cheaply with a bandit-style search, avoiding brute force over the combinatorial space, to measure the *spread* in accuracy one model shows across formats. What they found:

- Accuracy spreads reach **up to ~76 points** on some tasks. **5–10+ points is common** even on mainstream benchmarks.
- **The best format differs per model.** There's no universal good format to standardize on. Comparing two models under one fixed format may put one near its ceiling and the other near its floor.
- All of the variation comes from **spurious features**: separators (`:` vs `)` vs newline), casing of the "Answer" cue, spacing, option delimiters, field ordering, few-shot separators. No competent human would consider any of them meaningful.

Few-shot ordering is a second axis that compounds the first (covered in [[Concept - Few-Shot Example Selection and Ordering]]). Lu et al. (2022), "Fantastically Ordered Prompts and Where to Find Them," showed that the *order* of in-context exemplars alone can take a model from near-random to near-SOTA on the same task with the same examples. The cause is majority-label and recency bias: if exemplar labels cluster, or a particular label sits last, predictions skew toward it. They also showed you can *select* a good ordering without labels, using the model's own prediction entropy over a probing set as a proxy for ordering quality. Mizrahi et al. (2024), "State of What Art? A Call for Multi-Prompt LLM Evaluation," took the point up a level. Single-template evaluation is unreliable, and paraphrasing the *instruction* (not only the format) produces enough variance that single-template leaderboard rankings can be artifacts.

Tokenization makes it worse. Formatting controls whitespace and leading-space handling, which changes the logprobs being compared in log-likelihood scoring: `" A"` and `"A"` are different tokens with different probabilities. That's a [[Concept - Byte-Pair Encoding]]-level effect, and it ties format sensitivity to [[Concept - Answer Scoring and Normalization]]. Format sets the token sequence, scoring turns its probabilities into a number, and both move the result. This spurious-token sensitivity is the benign end of a spectrum whose pathological end is [[Lore - Glitch Tokens]].

Format also interacts with elicitation. A format that suppresses [[Concept - Chain-of-Thought and Why It Works]] (forcing an immediate answer token, for example) can crater a reasoning model's measured capability, so "format" and "how much reasoning the prompt permits" are tangled together.

## In practice

Think of it as a prompt lottery: **single-format evaluation is a coin flip, and a leaderboard position can be a format artifact instead of a capability difference.** Treat format as a variance source to measure or control, the way [[Concept - Statistical Rigor in Model Evaluation]] treats seeds and few-shot choice. This is the format-specific case of "report your error bars." Three defensible protocols, in increasing rigor:

1. **Fix one carefully audited format and disclose it.** The minimum bar. Eyeball the fully rendered prompt, use it for every model, and state it. Cheap and honest, but you're reporting a point estimate on a distribution.
2. **Evaluate under the model's own chat template.** For instruct models the [[Concept - Prompt Formatting and Sensitivity]] rule from the prompting domain applies: running an instruct model outside its native template silently costs it 10–20 points. The template is the correct format, and using it removes the largest single format error.
3. **Report a distribution over formats (FormatSpread).** Sample the format space and report mean and spread, so the reader can see whether your claimed gap survives reformatting.

Never pick the format that flatters your model and report that single number without saying so. It's the format-level version of the gaming catalogued in [[Concept - Goodhart's Law in Model Evaluation]]. Anyone building a real suite has to deal with this; [[Deep Dive - Designing an Eval Harness]] covers where format and template application sit in the pipeline.

## Failure modes

**Symptom:** two harnesses report a 6-point gap between models A and B, in opposite directions. **Cause:** each harness uses a different fixed format and the best format differs per model, so formatting alone flipped the ranking. **Detection:** run both models across a shared sample of formats. If the sign of the delta isn't stable across formats, neither single-format number is a valid ranking.

**Symptom:** few-shot accuracy swings wildly run to run with the "same" examples. **Cause:** exemplar ordering (Lu et al. 2022), meaning majority-label or recency bias from the specific permutation. **Detection:** shuffle exemplar order across several seeds and report the spread. A large spread means the shot ordering is moving the score, not the model.

**Symptom:** an instruct model scores far below its reputation on a standard benchmark. **Cause:** the harness used a plain-text format instead of the model's chat template. **Detection:** print the fully rendered prompt and confirm the template's special tokens and turn structure are there.

## The non-obvious

**Format variance frequently dwarfs the reported gap between two models, and almost nobody measures or reports it.** A paper says model A beats model B by 3 points. Each model swings 8 points across trivial reformattings, so the "3-point win" sits inside format noise and may reverse under some other, equally arbitrary format the authors didn't try.

The uncomfortable part is that no neutral format exists. Every format is one point in a space where different models peak in different places, so even a well-intentioned single-format eval measures "model performance *at this arbitrary point*." The only fully honest number is a distribution, and the field's habit of reporting point estimates is why so many leaderboard results don't reproduce. Format sensitivity, symbol/position bias ([[Concept - Multiple-Choice Symbol Binding and Position Bias]]) and scoring normalization all come from one fact: a benchmark score belongs to the *(model, format, scoring)* triple. Quoting it as a property of the model alone is the original sin of LLM evaluation.

## Connections

- [[Concept - Answer Scoring and Normalization]] — format determines the token sequence, scoring turns its probabilities into a number; whitespace handling is the shared seam between the two.
- [[Concept - Multiple-Choice Symbol Binding and Position Bias]] — option position/symbol bias is a specific, high-impact instance of format sensitivity in the MCQ setting.
- [[Deep Dive - Designing an Eval Harness]] — where format construction and chat-template application live; this note is the reason those axes must be pinned.
- [[Concept - Prompt Formatting and Sensitivity]] — the prompting-domain sibling (domain 09); the chat-template rule for instruct models is the single largest format error to remove.
- [[Concept - Few-Shot Example Selection and Ordering]] — exemplar ordering is the compounding second axis of format variance (cross-domain, prompting).
- [[Concept - Chain-of-Thought and Why It Works]] — format can suppress or permit reasoning, entangling format sensitivity with elicitation (cross-domain, prompting).
- [[Concept - Byte-Pair Encoding]] — leading-space and separator tokenization is the mechanism by which "spurious" format changes alter the compared logprobs (cross-domain, training).
- [[Concept - Statistical Rigor in Model Evaluation]] — format is a variance source that belongs in your error bars; this note is its format-specific case.
- [[Concept - Goodhart's Law in Model Evaluation]] — quietly picking the flattering format is the format-level version of benchmark gaming.
- [[Lore - Glitch Tokens]] — the pathological end of the spurious-token-sensitivity spectrum this note starts from (cross-domain, esoterica).

## Sources
- Sclar et al. (2023/2024) — Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design (FormatSpread). Measures accuracy spreads up to ~76 points across semantically-equivalent formats and shows the best format is model-dependent.
- Lu et al. (2022) — Fantastically Ordered Prompts and Where to Find Them. Exemplar order alone moves models from near-random to near-SOTA; entropy-based ordering selection.
- Mizrahi et al. (2024) — State of What Art? A Call for Multi-Prompt LLM Evaluation. Single-template evaluation is unreliable; instruction paraphrasing produces ranking-changing variance.
