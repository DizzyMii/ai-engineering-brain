---
tags: [concept, domain/evaluation, level/unicorn]
aliases: [format sensitivity, prompt lottery, FormatSpread, prompt format variance]
summary: "Semantically-equivalent formatting changes swing benchmark scores by many points and can flip model rankings at fixed weights."
---
> **One-paragraph hook:** Change a colon to a parenthesis. Change "Answer:" to "answer:". Put a newline where a space was. None of these change the *meaning* of a prompt, and all of them can move a benchmark score by several points — sometimes by dozens. Worse, the format that flatters model X can penalize model Y, so a single-format evaluation doesn't just add noise, it can *invert the ranking* between two models at fixed weights and fixed data. This is the tribal knowledge behind a large fraction of irreproducible leaderboard results: the reported gap between two models is frequently smaller than the gap either model shows across trivial reformattings of the same benchmark, and almost nobody reports that spread.

## The mechanism

A language model does not consume "the question." It consumes a specific token sequence, and its output distribution is a function of that exact sequence — including every separator, capitalization, and whitespace choice that a human reads straight through. Semantically-equivalent formats produce *different token sequences*, and the model has no guarantee of invariance across them because nothing in pretraining or post-training enforced it.

**FormatSpread** (Sclar et al. 2023/2024, "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design") is the definitive measurement. They defined a space of semantically-equivalent format variations — separator choice, spacing, casing of cue words, option delimiters, field ordering — and searched it (cheaply, via a bandit-style search rather than brute force over the combinatorial space) to measure the *spread* in accuracy a single model shows across formats. The findings that make this a unicorn topic:

- Accuracy spreads reach **up to ~76 points** on some tasks; **5–10+ points is common** even on mainstream benchmarks.
- The **best format differs per model.** So there is no universal "good format" you can standardize on, and comparing two models under one fixed format is comparing them at a point that may be near one model's ceiling and near the other's floor.
- The variation comes entirely from **spurious features** — separators (`:` vs `)` vs newline), the casing of the "Answer" cue, spacing, option delimiters, field ordering, few-shot separators — none of which a competent human would consider meaningful.

**Few-shot ordering is a second, compounding axis** (the province of [[Concept - Few-Shot Example Selection and Ordering]]). Lu et al. (2022), "Fantastically Ordered Prompts and Where to Find Them," showed that the *order* of in-context exemplars alone can move a model from near-random to near-SOTA on the same task with the same examples. The mechanism is majority-label bias and recency bias: if the exemplars' labels cluster, or a particular label sits last, the model's prediction skews toward it. They also showed you can *select* a good ordering without labels by using the model's own prediction entropy over a probing set as a proxy for ordering quality. Mizrahi et al. (2024), "State of What Art? A Call for Multi-Prompt LLM Evaluation," pushed the same point up a level: evaluating on a single instruction template is unreliable, and paraphrasing the *instruction* (not just the format) produces enough variance that single-template leaderboard rankings can be artifacts.

**Interaction with tokenization.** The whitespace and leading-space handling that formatting controls changes the very logprobs being compared in log-likelihood scoring — `" A"` vs `"A"` are different tokens with different probabilities. This is a [[Concept - Byte-Pair Encoding]]-level effect, and it ties format sensitivity directly to [[Concept - Answer Scoring and Normalization]]: format determines the token sequence, scoring determines how its probabilities become a number, and both move the result. The same spurious-token sensitivity is the benign end of the spectrum whose pathological end is [[Lore - Glitch Tokens]].

Format sensitivity also interacts with elicitation: a format that suppresses [[Concept - Chain-of-Thought and Why It Works]] (e.g., forcing an immediate answer token) can crater a reasoning model's measured capability, so "format" and "how much reasoning the prompt permits" are entangled.

## In practice

The "prompt lottery" framing is the practical takeaway: **single-format evaluation is a coin flip, and a leaderboard position can be a format artifact rather than a capability difference.** The mature practitioner treats format as a variance source to be measured or controlled, exactly as [[Concept - Statistical Rigor in Model Evaluation]] treats seeds and few-shot choice — this note is the format-specific instance of the general "report your error bars" discipline. Three defensible protocols, in increasing rigor:

1. **Fix one carefully-audited format and disclose it.** The minimum bar. Eyeball the fully-rendered prompt, use it for every model, and state it. Cheap and honest, but you are reporting a point estimate on a distribution.
2. **Evaluate under the model's own chat template.** For instruct models, the [[Concept - Prompt Formatting and Sensitivity]] rule from the prompting domain applies: running an instruct model outside its native template silently tanks it by 10–20 points, so the template *is* the correct format and using it removes the largest single format error.
3. **Report a distribution over formats (FormatSpread).** Sample the format space and report the mean and spread, so the reader sees whether your claimed gap survives reformatting.

The one thing you must never do is quietly pick the format that flatters your model and report the single number — that is the format-level version of the gaming catalogued in [[Concept - Goodhart's Law in Model Evaluation]]. This is a first-order concern for anyone building a real suite; see [[Deep Dive - Designing an Eval Harness]] for where format and template application live in the pipeline.

## Failure modes

**Symptom:** two harnesses report a 6-point gap between models A and B in opposite directions. **Cause:** each harness uses a different fixed format, and the best format differs per model, so the ranking flipped on formatting alone. **Detection:** run both models across a shared sample of formats; if the sign of the delta is not stable across formats, neither single-format number is a valid ranking.

**Symptom:** few-shot accuracy is wildly unstable run-to-run with the "same" examples. **Cause:** exemplar ordering (Lu et al. 2022) — majority-label or recency bias from the specific permutation. **Detection:** shuffle exemplar order across several seeds and report the spread; a large spread means the shot ordering, not the model, is moving the score.

**Symptom:** an instruct model scores far below its reputation on a standard benchmark. **Cause:** the harness applied a plain-text format instead of the model's chat template. **Detection:** print the fully-rendered prompt and confirm the template's special tokens and turn structure are present.

## The non-obvious

Why this is unicorn knowledge: **format variance frequently dwarfs the reported gap between two models, yet almost nobody measures or reports it.** A paper announces model A beats model B by 3 points; both models individually swing 8 points across trivial reformattings; the "3-point win" is therefore inside the format noise and may reverse under a different (equally arbitrary) format the authors didn't try. The deep discomfort is that there is no ground-truth "neutral" format — every format is a specific point in a space where different models peak at different points, so even a well-intentioned single-format eval is measuring "model performance *at this arbitrary point*," not "model performance." The only fully honest number is a distribution, and the field's persistent reporting of point estimates is why so many leaderboard results fail to reproduce. Format sensitivity, symbol/position bias (see [[Concept - Multiple-Choice Symbol Binding and Position Bias]]), and scoring normalization are three faces of the same underlying fact — a benchmark score is a property of the *(model, format, scoring)* triple, and quoting it as a property of the model alone is the original sin of LLM evaluation.

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
