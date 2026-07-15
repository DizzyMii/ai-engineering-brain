---
tags: [concept, domain/evaluation, level/unicorn]
aliases: [acc vs acc_norm, acc_norm, log-likelihood scoring, cloze scoring, PMI normalization]
summary: "How log-likelihood vs generation scoring and acc/acc_norm/PMI normalization silently decide which model gets reported as SOTA."
---
> **One-paragraph hook:** Two engineers run "the same" MMLU on the same model weights and report numbers 6 points apart. Neither made a mistake. One scored the log-probability of the answer *letter*, the other let the model *generate* and parsed the result; or one used `acc` and the other `acc_norm`; or their harnesses normalized by bytes vs. tokens. Answer scoring is the layer between a model's raw logits and a benchmark cell, and the choices made there are almost never reported, are understood mostly by harness maintainers, and routinely decide which model is called "SOTA." This is the arcana that turns a reproducibility problem into a marketing opportunity.

## The mechanism

There are two fundamentally different scoring regimes, and they can rank models differently, so mixing them in a comparison is invalid.

**Regime A — log-likelihood / cloze scoring.** Never let the model generate. For a multiple-choice item with options $o_1,\dots,o_k$, score each option by the model's conditional log-probability of that option's *text* given the context, and pick the argmax:

$$\hat{i} = \arg\max_i \; \log P(o_i \mid \text{context})$$

This is how MMLU and HellaSwag are scored in EleutherAI's lm-evaluation-harness. It is cheap (one forward pass per option, no sampling) and deterministic. But raw log-probability of a *sequence* is confounded by length and by token frequency — which is where normalization enters.

**`acc` vs `acc_norm`.** Longer completions accumulate more negative log-probability simply because they have more tokens, biasing raw `acc` toward shorter options. `acc_norm` divides the sequence log-prob by the completion length before the argmax:

$$\hat{i}_{\text{norm}} = \arg\max_i \; \frac{\log P(o_i \mid \text{context})}{\text{len}(o_i)}$$

The subtlety that bites: lm-eval-harness normalizes by **byte length**, not token length. So `acc_norm` is *not one well-defined quantity* — a paper that normalized by token count and a harness that normalizes by bytes will disagree, and the [[Concept - Byte-Pair Encoding]] tokenizer's per-model segmentation makes token-length normalization model-dependent on top of that. On HellaSwag and ARC-Challenge, `acc` and `acc_norm` routinely differ by 5–10 points and can *reorder* models. The Open LLM Leaderboard's deliberate choice to report `acc_norm` for ARC and HellaSwag but `acc` for MMLU is a concrete, load-bearing example: change that one config field and the board changes.

**Surface-form competition and PMI.** Holtzman et al. (2021), "Surface Form Competition," identified a deeper failure of raw probability: valid answers that happen to be rarer token strings lose to more common paraphrases of a *wrong* answer. "computer" outscores "PC" not because it is more correct but because it is a higher-probability surface form. The fix is to divide out the option's unconditional likelihood — pointwise mutual information (PMI) / domain-conditional normalization:

$$\text{score}(o_i) = \log \frac{P(o_i \mid \text{context})}{P(o_i \mid \text{null})} = \log P(o_i \mid \text{context}) - \log P(o_i \mid \text{null})$$

where the null context is a neutral prefix like "Answer:". This asks "how much does the *question* raise this option's probability," which is closer to what you actually want to measure. All three normalizations rest on the [[Concept - Softmax]] over the vocabulary and the per-token [[Concept - Entropy and Cross-Entropy]] the model assigns — normalization is just different bookkeeping over the same log-probabilities.

**Letter vs full-answer scoring.** You can score the option *symbol* ("A") or the option *text* ("Paris"). These give different rankings, and a weak model may "know" the answer in the full-text sense while failing to emit the right letter — the confound that [[Concept - Multiple-Choice Symbol Binding and Position Bias]] is entirely about. Letter-scoring is cheaper and matches how instruct models are prompted, but it understates knowledge in models with weak symbol binding.

**Regime B — generation and parse.** Let the model produce free text, then extract the answer. This is mandatory for math and code, where there is no fixed option set. For math (MATH, GSM8K), you parse the final answer — usually a `\boxed{}` extraction — and check equivalence, ideally with a symbolic engine (sympy) rather than string match. The failure surface here is *equivalence checking*: `1/2` vs `0.5` vs `0.50`, an unsimplified `\frac{2}{4}`, `x+1` vs `1+x` all trip naive matchers, producing **false negatives**; a loose substring match ("the answer is 7" hitting on a "7" that appears mid-derivation) produces **false positives**. This regime overlaps with verifier quality in [[Concept - Pass@k and Sampling-Based Evaluation]], where the grader caps everything.

## In practice

The operational rule is: **pin the scoring method and never compare across regimes.** A generated-and-parsed number and a log-likelihood number for the same benchmark are two different measurements. When you read a leaderboard cell, the questions that actually determine whether it is comparable are: log-likelihood or generation? `acc` or `acc_norm`? byte or token normalization? letter or full-answer? These are precisely the axes [[Deep Dive - Designing an Eval Harness]] tells you to pin, and the ones [[Gotchas - Benchmark Harness Pitfalls]] catalogs as sources of silent cross-harness disagreement. On the constructive side, [[Breakdown - MMLU]] is the canonical case study: its under-specified scoring is *the* reason the same model gets different MMLU numbers from HELM, lm-eval-harness, and the original code.

Concrete magnitudes worth carrying: `acc`↔`acc_norm` swings of 5–10 points on HellaSwag/ARC; letter↔full-answer swings large enough to flip small-model rankings; math equivalence-checker false-negative rates high enough that a few points of a MATH score can be pure grading artifact.

## Failure modes

**Symptom:** your model's MMLU is 4 points below the paper's, same weights. **Cause:** regime or normalization mismatch — you generated and parsed, they scored log-likelihood, or `acc` vs `acc_norm`. **Detection:** dump the exact scoring config from both harnesses and diff; re-run under the paper's stated method before concluding anything.

**Symptom:** a model that is clearly stronger loses on HellaSwag. **Cause:** `acc` vs `acc_norm` disagreement interacting with option-length distribution. **Detection:** report both `acc` and `acc_norm`; if they disagree, the ranking is scoring-artifact-sensitive and neither should be quoted alone.

**Symptom:** a strong reasoning model scores oddly low on MATH. **Cause:** the equivalence checker is rejecting correct-but-unsimplified or differently-formatted answers as wrong. **Detection:** manually audit a sample of graded-incorrect items; a high rate of "actually correct, wrong format" means the grader, not the model, is the bottleneck.

## The non-obvious

The thing practitioners learn the hard way: **`acc_norm` is not a comparable quantity across harnesses, even though everyone treats the label as if it were.** Because one harness normalizes by bytes and another by tokens (and token length depends on the model's own tokenizer), two "acc_norm" numbers can be measuring different things, and the label gives you false confidence that they're aligned. More broadly, the scoring layer is where a benchmark's *social* fact (what counts as correct) gets encoded as a *technical* choice that almost no one reads — which is exactly why it is exploitable: pick the normalization that flatters your model, report the label, omit the config. The defense is boring and total: report the harness, version, regime, normalization, and parser, and treat any unstated axis as a source of unreproducible variance. This sits one layer below [[Concept - Prompt Format Sensitivity in Evaluation]] — format sensitivity is about the prompt the model sees; scoring normalization is about how its output is turned into a number — and the two compound, because whitespace and leading-space handling changes the very logprobs being normalized.

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
