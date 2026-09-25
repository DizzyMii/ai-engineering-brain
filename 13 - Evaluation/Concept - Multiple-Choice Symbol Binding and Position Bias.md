---
tags: [concept, domain/evaluation, level/unicorn]
aliases: [MCSB, selection bias, option position bias, symbol binding, MCQ position bias]
summary: "Why MCQ scores are confounded by option symbol and position independent of content, and why letter-scoring understates knowledge."
---
> **One-paragraph hook:** take a multiple-choice question the model gets right, permute the options so the correct answer moves from position C to position A, and the answer can flip. The model didn't change its mind about the content; it has a standing prior toward emitting a particular letter or picking a particular slot. MCQ scoring quietly assumes two things that are false for real language models: that a model has no positional prior, and that "outputting the letter B" is the same act as "knowing the second option is correct." Both fail measurably, and they fail *differently across models*, so MCQ leaderboards are partly ranking the confound instead of the capability.

## The mechanism

Two effects usually get lumped together. They're separate, and both are real.

**Selection bias / position bias.** Zheng et al. (2023), "Large Language Models Are Not Robust Multiple Choice Selectors," showed that models carry a built-in prior toward specific option IDs (picking "A," or the first position, or some particular slot) independent of the option's content. Their headline measurement: permuting option order changes accuracy by **up to ~20+ points** on affected models and benchmarks. The prior is systematic, so it doesn't average out over a benchmark; it biases the whole score. They proposed **PriDe** (Debiasing with Prior estimation): estimate each model's positional prior from a few permutations, then subtract it before scoring. Pezeshkpour & Hruschka (2023) found the same fragility from another angle, reporting very large accuracy gaps from option reordering alone.

**Symbol binding (MCSB).** Robinson & Wingate (2022) named the separate question of whether a model can reliably *associate a letter with its option at all*. You can pose an MCQ two ways. **Cloze/answer scoring** presents the options and scores the log-probability of each option's *text*. **Multiple-choice prompting** presents "A) ... B) ... C) ..." and reads off the *symbol* the model emits. A model with weak symbol binding can rank the correct option's text highest under cloze scoring and still fail to output the right *letter* under multiple-choice prompting. It "knows" the answer but can't bind it to the symbol. Letter-scoring such a model *understates its knowledge*. That's the direct link to [[Concept - Answer Scoring and Normalization]]: choosing letter- or full-answer scoring interacts with a capability the model may or may not have.

**Where the priors come from.** Mechanistically, three overlapping sources:

- **Token-level priors.** The tokens `" A"`, `" B"`, `" C"`, `" D"` aren't equiprobable a priori. Pretraining text has skewed letter-answer distributions, and the model inherits a bias on those tokens. It's a [[Concept - Byte-Pair Encoding]]-level effect: leading-space handling (`" A"` vs `"A"`) even changes which token's log-probability you're comparing.
- **Positional bias from format.** Pretraining corpora contain huge numbers of "the answer is (A)" style exam scrapes with non-uniform answer positions, which bias the model toward certain slots regardless of content, via the [[Concept - Softmax]] over the answer-token logits.
- **Few-shot answer-distribution skew.** If the in-context exemplars' answers cluster on one letter, the model over-predicts that letter on the query. It's a special case of the exemplar-selection effects in [[Concept - Few-Shot Example Selection and Ordering]] (cross-domain, prompting). Balancing the shots' answer distribution is a required control, and it's usually skipped.

## In practice

The effect **interacts with the model being ranked**, which is what makes it nasty. GPT-4- and Claude-class models are *less* affected but still measurably biased; small and mid-size models are heavily biased. So the confound isn't a constant offset you can ignore. It's larger for weaker models, which means it can compress or distort the *gap* between two models, not just shift both equally.

Standard debiasing, cheapest to most thorough:

- **Cyclic-permutation averaging (circular evaluation).** Score every rotation of the option order and average, so any single-slot prior cancels. It costs $k\times$ forward passes for $k$ options, and it's the honest default when you can afford it.
- **PriDe calibration.** Estimate the positional prior from a subsample of permutations and subtract it. Most of the debiasing benefit at a fraction of the full-permutation cost.
- **Balanced few-shot answer distribution.** Spread exemplar answers across letters.
- **Full-answer log-likelihood scoring.** Avoid symbol binding by scoring option text instead of the emitted letter. This changes the regime, though (see [[Concept - Answer Scoring and Normalization]]), and the result isn't comparable to letter-scored numbers.

It's also why [[Breakdown - MMLU]] numbers are notoriously irreproducible across harnesses. Two harnesses that differ only in option ordering, letter- vs text-scoring, or few-shot answer balance will produce different MMLU scores for the same weights, and [[Gotchas - Benchmark Harness Pitfalls]] lists the leading-space and letter-parsing variants as concrete traps. [[Deep Dive - Designing an Eval Harness]] shows where these controls live in the pipeline.

## Failure modes

**Symptom:** a model's MMLU score jumps 5–15 points between two harnesses. **Cause:** different option ordering or a different symbol/text scoring choice hitting the model's positional prior. **Detection:** re-run with cyclic-permutation averaging under both harnesses. If the averaged scores agree and the single-order scores didn't, position bias was the cause.

**Symptom:** a small model scores near the random baseline on MCQ but seems to "know" the material in free chat. **Cause:** weak symbol binding; it can't reliably emit the letter even when it ranks the correct option's text highest. **Detection:** compare cloze/full-answer scoring with letter-scoring. A large gap is the signature, and letter-scoring is undercounting.

**Symptom:** accuracy is suspiciously sensitive to which letter is "correct" across the benchmark. **Cause:** few-shot answer-distribution skew or a raw token prior on a specific letter. **Detection:** compare the model's answer-letter distribution with uniform. A spike on one letter means the prior is driving predictions, not the content.

## The non-obvious

Most practitioners miss this: **a huge class of "this model is weirdly bad/good at MCQ" results are scoring artifacts, not facts about the model.** When a leaderboard shows two models close together with one mysteriously ahead on MMLU, the difference is at least as likely to come from their different positional priors under a fixed (un-permuted) option order as from real knowledge. And because the bias is larger for weaker models, the naive score *distorts the gap* instead of shifting both equally. That's the mechanical reason "letter accuracy" is a biased proxy for knowledge, and it explains a whole family of contradictory leaderboard results people reflexively blame on the model. Position and symbol bias are the MCQ-specific face of the broader [[Concept - Prompt Format Sensitivity in Evaluation]] problem, where trivial, meaning-preserving choices swing scores at fixed weights. They also connect down to raw tokenization pathology. The same leading-space and rare-token effects behind [[Lore - Glitch Tokens]] are what make `" A"` vs `"A"` flip an MCQ verdict; the confound bottoms out in how the answer symbol is tokenized, not in the model's understanding of the question. Report cyclic-permutation-averaged scores or don't quote an MCQ delta at all.

## Connections

- [[Concept - Answer Scoring and Normalization]] — the letter-vs-full-answer scoring choice is where symbol binding becomes a scoring decision; the two notes are two views of the same seam.
- [[Concept - Prompt Format Sensitivity in Evaluation]] — position/symbol bias is a specific, high-impact case of the general truth that formatting swings scores at fixed weights.
- [[Deep Dive - Designing an Eval Harness]] — where option permutation, letter parsing, and few-shot balancing controls are actually implemented.
- [[Breakdown - MMLU]] — the benchmark most affected; this confound is a primary reason its numbers don't reproduce across harnesses.
- [[Concept - Softmax]] — the positional and token priors are biases in the softmax over the answer-token logits (cross-domain, neural networks).
- [[Concept - Byte-Pair Encoding]] — leading-space and letter-token segmentation determine which token's probability is compared, so tokenization is upstream of the bias (cross-domain, training).
- [[Concept - Few-Shot Example Selection and Ordering]] — few-shot answer-distribution skew is one source of the positional prior (cross-domain, prompting).
- [[Gotchas - Benchmark Harness Pitfalls]] — the operational catalog listing leading-space handling and letter-parsing as concrete score-flipping traps.
- [[Lore - Glitch Tokens]] — the tokenization-pathology end of the same phenomenon; rare-token and leading-space effects bottom out here (cross-domain, esoterica).

## Sources
- Zheng et al. (2023) — Large Language Models Are Not Robust Multiple Choice Selectors. Measures positional/selection bias (up to ~20+ points from reordering) and introduces PriDe debiasing.
- Robinson & Wingate (2022) — Leveraging LLMs for Multiple Choice Question Answering. Defines multiple-choice symbol binding (MCSB) and cloze vs multiple-choice prompting.
- Pezeshkpour & Hruschka (2023) — Large Language Models Sensitivity to the Order of Options in Multiple-Choice Questions. Independent confirmation of large reordering-induced gaps.
