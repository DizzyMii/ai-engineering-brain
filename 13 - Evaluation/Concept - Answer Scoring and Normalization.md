---
tags: [concept, domain/evaluation, level/unicorn]
aliases: [acc vs acc_norm, acc_norm, log-likelihood scoring, cloze scoring, PMI normalization]
summary: "How log-likelihood vs generation scoring and acc/acc_norm/PMI normalization silently decide which model gets reported as SOTA."
---
> **One-paragraph hook:** two engineers run "the same" MMLU on the same model weights and report numbers 6 points apart. Neither made a mistake. One scored the log-probability of the answer *letter* and the other let the model *generate* and parsed the result. Or one used `acc` and the other `acc_norm`, or their harnesses normalized by bytes vs. tokens. Answer scoring is the layer between a model's raw logits and a benchmark cell. The choices made there are almost never reported, mostly only harness maintainers understand them, and they routinely decide which model gets called "SOTA." This is the arcana that turns a reproducibility problem into a marketing opportunity.

## The mechanism

There are two different scoring regimes. They can rank models differently, so mixing them in one comparison is invalid.

**Regime A: log-likelihood / cloze scoring.** The model never generates. For a multiple-choice item with options $o_1,\dots,o_k$, score each option by the model's conditional log-probability of that option's *text* given the context, and pick the argmax:

$$\hat{i} = \arg\max_i \; \log P(o_i \mid \text{context})$$

EleutherAI's lm-evaluation-harness scores MMLU and HellaSwag this way. It's cheap (one forward pass per option, no sampling) and deterministic. But the raw log-probability of a *sequence* is confounded by length and token frequency, and that's where normalization comes in.

**`acc` vs `acc_norm`.** Longer completions pile up more negative log-probability just by having more tokens, which biases raw `acc` toward shorter options. `acc_norm` divides the sequence log-prob by completion length before the argmax:

$$\hat{i}_{\text{norm}} = \arg\max_i \; \frac{\log P(o_i \mid \text{context})}{\text{len}(o_i)}$$

Here's what bites: lm-eval-harness normalizes by **byte length**, not token length. So `acc_norm` is *not one well-defined quantity*. A paper that normalized by token count and a harness that normalizes by bytes will disagree, and on top of that the [[Concept - Byte-Pair Encoding]] tokenizer's per-model segmentation makes token-length normalization model-dependent. On HellaSwag and ARC-Challenge, `acc` and `acc_norm` routinely differ by 5–10 points and can *reorder* models. The Open LLM Leaderboard deliberately reports `acc_norm` for ARC and HellaSwag but `acc` for MMLU. Change that one config field and the board changes.

**Surface-form competition and PMI.** Holtzman et al. (2021), "Surface Form Competition," found a deeper failure of raw probability: valid answers that happen to be rarer token strings lose to more common paraphrases of a *wrong* answer. "computer" outscores "PC" because it's a higher-probability surface form, not because it's more correct. The fix is to divide out the option's unconditional likelihood, i.e. pointwise mutual information (PMI) / domain-conditional normalization:

$$\text{score}(o_i) = \log \frac{P(o_i \mid \text{context})}{P(o_i \mid \text{null})} = \log P(o_i \mid \text{context}) - \log P(o_i \mid \text{null})$$

The null context is a neutral prefix like "Answer:". The score asks how much the *question* raises this option's probability, which is closer to what you want to measure. All three normalizations sit on the [[Concept - Softmax]] over the vocabulary and the per-token [[Concept - Entropy and Cross-Entropy]] the model assigns. They're different bookkeeping over the same log-probabilities.

**Letter vs full-answer scoring.** You can score the option *symbol* ("A") or the option *text* ("Paris"). They give different rankings. A weak model may "know" the answer in the full-text sense and still fail to emit the right letter, which is the whole subject of [[Concept - Multiple-Choice Symbol Binding and Position Bias]]. Letter-scoring is cheaper and matches how instruct models are prompted, but it understates knowledge in models with weak symbol binding.

**Regime B: generation and parse.** The model produces free text and you extract the answer. Math and code require this, since there's no fixed option set. For math (MATH, GSM8K) you parse the final answer, usually a `\boxed{}` extraction, and check equivalence, ideally with a symbolic engine (sympy) instead of string match. Equivalence checking is where it fails. `1/2` vs `0.5` vs `0.50`, an unsimplified `\frac{2}{4}`, `x+1` vs `1+x` all trip naive matchers and produce **false negatives**. A loose substring match ("the answer is 7" hitting a "7" mid-derivation) produces **false positives**. This regime overlaps with verifier quality in [[Concept - Pass@k and Sampling-Based Evaluation]], where the grader caps everything.

## In practice

The rule: **pin the scoring method and never compare across regimes.** A generated-and-parsed number and a log-likelihood number for the same benchmark are two different measurements. When you read a leaderboard cell, what decides whether it's comparable is: log-likelihood or generation? `acc` or `acc_norm`? Byte or token normalization? Letter or full answer? [[Deep Dive - Designing an Eval Harness]] tells you to pin these axes, and [[Gotchas - Benchmark Harness Pitfalls]] catalogs them as sources of silent cross-harness disagreement. [[Breakdown - MMLU]] is the canonical case study: its under-specified scoring is *the* reason the same model gets different MMLU numbers from HELM, lm-eval-harness and the original code.

Magnitudes to remember: `acc`↔`acc_norm` swings of 5–10 points on HellaSwag/ARC; letter↔full-answer swings big enough to flip small-model rankings; math equivalence-checker false-negative rates high enough that a few points of a MATH score can be pure grading artifact.

## Failure modes

**Symptom:** your model's MMLU is 4 points below the paper's, same weights. **Cause:** regime or normalization mismatch. You generated and parsed while they scored log-likelihood, or it's `acc` vs `acc_norm`. **Detection:** dump the exact scoring config from both harnesses and diff them; re-run under the paper's stated method before concluding anything.

**Symptom:** a clearly stronger model loses on HellaSwag. **Cause:** `acc` vs `acc_norm` disagreement interacting with the option-length distribution. **Detection:** report both `acc` and `acc_norm`. If they disagree, the ranking is sensitive to scoring artifacts and neither should be quoted alone.

**Symptom:** a strong reasoning model scores oddly low on MATH. **Cause:** the equivalence checker rejects correct-but-unsimplified or differently formatted answers. **Detection:** hand-audit a sample of items graded incorrect. A high rate of "actually correct, wrong format" means the grader is the bottleneck, not the model.

## The non-obvious

Practitioners learn this the hard way: **`acc_norm` isn't comparable across harnesses, even though everyone treats the label as if it were.** One harness normalizes by bytes and another by tokens (and token length depends on the model's own tokenizer), so two "acc_norm" numbers can measure different things while the shared label makes them look aligned. More broadly, the scoring layer is where a benchmark's *social* fact (what counts as correct) becomes a *technical* choice almost nobody reads. That's what makes it exploitable: pick the normalization that flatters your model, report the label, omit the config. The defense is boring and complete. Report the harness, version, regime, normalization and parser, and treat any unstated axis as unreproducible variance. This sits one layer below [[Concept - Prompt Format Sensitivity in Evaluation]]. Format sensitivity concerns the prompt the model sees; scoring normalization concerns how its output becomes a number. The two compound, because whitespace and leading-space handling change the very logprobs being normalized.

## Connections

- [[Concept - Multiple-Choice Symbol Binding and Position Bias]] — the letter-vs-full-answer scoring choice is the entry point to symbol binding; weak binding makes letter-scoring understate knowledge.
- [[Concept - Prompt Format Sensitivity in Evaluation]] — the sibling arcana one layer up; prompt format changes the logprobs that scoring then normalizes, so the two confounds compound.
- [[Deep Dive - Designing an Eval Harness]] — the harness is where these scoring decisions are configured and must be pinned; this note is the deep detail behind its scoring stage.
- [[Concept - Softmax]] — every log-likelihood score is a softmax over the vocabulary; normalization is bookkeeping over those probabilities.
- [[Concept - Entropy and Cross-Entropy]] — sequence log-probability is summed per-token cross-entropy, the raw material all normalizations reweight (cross-domain, foundations).
- [[Concept - Byte-Pair Encoding]] — token-length normalization is tokenizer-dependent, and byte- vs token-length is a live source of `acc_norm` disagreement (cross-domain, training).
- [[Breakdown - MMLU]] — the canonical benchmark whose under-specified scoring makes it the textbook case of scoring-driven irreproducibility.
- [[Gotchas - Benchmark Harness Pitfalls]] — the operational catalog where `acc` vs `acc_norm` and regime mismatch appear as concrete traps.
- [[Concept - Pass@k and Sampling-Based Evaluation]] — the generation-regime cousin, where verifier and equivalence-checker quality cap the score the same way math grading does here.

## Sources
- Holtzman et al. (2021) — Surface Form Competition: Why the Highest Probability Answer Isn't Always Right. Introduces PMI / domain-conditional normalization.
- Gao et al. — EleutherAI lm-evaluation-harness. The de facto scoring implementation; defines `acc`/`acc_norm` with byte-length normalization and powers the Open LLM Leaderboard.
- Robinson & Wingate (2022) — Leveraging LLMs for Multiple Choice Question Answering. Formalizes letter-scoring (multiple-choice prompting) vs cloze scoring.
- Hendrycks et al. (2021) — MMLU. The benchmark whose scoring ambiguity makes normalization choices consequential.
