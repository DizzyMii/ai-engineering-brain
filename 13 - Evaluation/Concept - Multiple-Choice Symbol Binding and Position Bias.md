---
tags: [concept, domain/evaluation, level/unicorn]
aliases: [MCSB, selection bias, option position bias, symbol binding, MCQ position bias]
summary: "Why MCQ scores are confounded by option symbol and position independent of content, and why letter-scoring understates knowledge."
---
> **One-paragraph hook:** Take a multiple-choice question the model gets right, permute the options so the correct answer moves from position C to position A, and the model's answer can flip — not because it changed its mind about the content, but because it has a standing prior toward emitting a particular letter or a particular slot. Multiple-choice scoring quietly assumes two things that are false for real language models: that a model has no positional prior, and that "outputting the letter B" is the same act as "knowing the second option is correct." Both assumptions fail measurably, and they fail *differently across models*, which means MCQ leaderboards are partly ranking the confound rather than the capability.

## The mechanism

Two distinct effects are usually lumped together; they are separate and both real.

**Selection bias / position bias.** Zheng et al. (2023), "Large Language Models Are Not Robust Multiple Choice Selectors," showed that models carry an inherent prior toward specific option IDs — a tendency to pick "A," or the first position, or a particular slot — that is independent of the option's content. Their headline measurement: permuting the option order changes accuracy by **up to ~20+ points** on affected models and benchmarks. Because the prior is systematic, it does not average out over a benchmark; it biases the whole score. They proposed **PriDe** (Debiasing with Prior estimation): estimate each model's positional prior from a small number of permutations, then subtract it out before scoring. Pezeshkpour & Hruschka (2023) found the same fragility from a different angle, reporting very large accuracy gaps from option reordering alone.

**Symbol binding (MCSB).** Robinson & Wingate (2022) named the separate question of whether a model can reliably *associate a letter with its option at all*. There are two ways to pose an MCQ to a model: **cloze/answer scoring** (present the options and score the log-probability of each option's *text*) versus **multiple-choice prompting** (present "A) ... B) ... C) ..." and read off the *symbol* the model emits). A model with weak symbol binding can rank the correct option's text highest under cloze scoring yet fail to output the correct *letter* under multiple-choice prompting — it "knows" the answer but cannot bind it to the symbol. Letter-scoring such a model *understates its knowledge*, and this is the direct link to [[Concept - Answer Scoring and Normalization]]: the choice of letter- vs full-answer scoring is not cosmetic, it interacts with a capability the model may or may not have.

**Where the priors come from.** Mechanistically these are three overlapping sources:

- **Token-level priors.** The tokens `" A"`, `" B"`, `" C"`, `" D"` are not equiprobable a priori — pretraining text has skewed letter-answer distributions, and the model inherits a bias on those specific tokens. This is a [[Concept - Byte-Pair Encoding]]-level effect: leading-space handling (`" A"` vs `"A"`) even changes which token's log-probability you are comparing.
- **Positional bias from format.** Pretraining corpora contain enormous numbers of "the answer is (A)" style exam scrapes with non-uniform answer positions, biasing the model toward certain slots regardless of content — mediated through the [[Concept - Softmax]] over the answer-token logits.
- **Few-shot answer-distribution skew.** If the in-context exemplars' answers cluster on one letter, the model over-predicts that letter on the query — a special case of the exemplar-selection effects in [[Concept - Few-Shot Example Selection and Ordering]] (cross-domain, prompting). Balancing the shots' answer distribution is a required, and usually skipped, control.

## In practice

The effect **interacts with the model being ranked**, which is what makes it pernicious. GPT-4- and Claude-class models are *less* affected but still measurably biased; small and mid-size models are heavily biased. So the confound is not a constant offset you can ignore — it is larger for the weaker models, which means it can compress or distort the *gap* between two models being compared, not just shift both equally.

Standard debiasing, cheapest to most thorough:

- **Cyclic-permutation averaging (circular evaluation).** Score all rotations of the option order and average, so any single-slot prior cancels. Costs $k\times$ forward passes for $k$ options; this is the honest default when you can afford it.
- **PriDe calibration.** Estimate the positional prior from a subsample of permutations and subtract it — most of the debiasing benefit at a fraction of the full-permutation cost.
- **Balanced few-shot answer distribution.** Ensure exemplar answers are spread across letters.
- **Full-answer log-likelihood scoring.** Sidestep symbol binding entirely by scoring option text instead of the emitted letter — though this changes the regime (see [[Concept - Answer Scoring and Normalization]]) and is not comparable to letter-scored numbers.

This is why [[Breakdown - MMLU]] numbers are notoriously irreproducible across harnesses: two harnesses that differ only in option ordering, letter- vs text-scoring, or few-shot answer balance will produce different MMLU scores for the same weights, and [[Gotchas - Benchmark Harness Pitfalls]] lists the leading-space and letter-parsing variants of this as concrete traps. Reach for [[Deep Dive - Designing an Eval Harness]] for where these controls actually live in the pipeline.

## Failure modes

**Symptom:** a model's MMLU score jumps 5–15 points between two harnesses. **Cause:** different option ordering or a different symbol/text scoring choice hitting the model's positional prior. **Detection:** re-run with cyclic-permutation averaging under both harnesses; if the averaged scores agree but the single-order scores didn't, position bias was the cause.

**Symptom:** a small model scores near the random baseline on MCQ but seems to "know" the material in free chat. **Cause:** weak symbol binding — it cannot reliably emit the letter even when it ranks the correct option's text highest. **Detection:** compare cloze/full-answer scoring against letter-scoring; a large gap is the signature, and letter-scoring is undercounting.

**Symptom:** accuracy is suspiciously sensitive to which letter is the "correct" one across the benchmark. **Cause:** few-shot answer-distribution skew or a raw token prior on a specific letter. **Detection:** measure the model's answer-letter distribution against uniform; a spike on one letter means the prior, not the content, is driving predictions.

## The non-obvious

The insight most practitioners miss: **a huge class of "this model is weirdly bad/good at MCQ" results are scoring artifacts, not model facts.** When a leaderboard shows two models close together and one mysteriously ahead on MMLU, the difference is at least as likely to be their differing positional priors under a fixed (un-permuted) option order as it is to be real knowledge — and because the bias is larger for weaker models, the naive score *distorts the gap* rather than shifting both models equally. This is the concrete, mechanical reason "letter accuracy" is a biased proxy for knowledge, and it explains a whole family of contradictory leaderboard results that people reflexively attribute to the model. Position and symbol bias are really the MCQ-specific face of the broader [[Concept - Prompt Format Sensitivity in Evaluation]] problem — trivial, meaning-preserving choices swinging scores at fixed weights. It also connects downward to raw tokenization pathology: the same leading-space and rare-token effects that produce [[Lore - Glitch Tokens]] are what make `" A"` vs `"A"` flip an MCQ verdict — the confound bottoms out in how the answer symbol is tokenized, not in the model's understanding of the question. Report cyclic-permutation-averaged scores or don't quote an MCQ delta at all.

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
