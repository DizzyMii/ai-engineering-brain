---
tags: [concept, domain/evaluation, level/frontier]
aliases: [MIA, membership inference attack, Min-K% Prob]
summary: "Black-box methods for detecting whether text was in training data — and why most barely beat random once distribution shift is controlled."
---
> **One-paragraph hook:** [[Concept - Benchmark Contamination]] explains why contamination happens and why it's hard to prevent; this note is about the narrower, harder question of whether you can *prove* a specific piece of text was in a specific model's training data after the fact, using nothing but black-box access to logits or generations. The methods are clever and the math is real, but the field's own most-cited 2024 finding is that most of them barely beat random once you control for the one confound every naive setup has: the "seen" and "unseen" text usually differ in more than membership.

## The mechanism

Membership inference attacks (MIA) exploit a simple intuition: gradient descent pushes a model's loss down harder on examples it was trained on than on held-out examples with similar surface statistics, so a model should assign systematically higher likelihood — lower loss, lower perplexity — to text it has seen. The question is how to turn that intuition into a detector that isn't fooled by the fact that *some text is just intrinsically easier to predict than other text*, independent of training-set membership.

**Min-K% Prob** (Shi et al. 2023) is the standard baseline. Instead of averaging log-probability over every token — which dilutes the signal, since most tokens in any text are easy regardless of membership — it looks only at the k% of tokens the model finds *least* likely:

$$\text{Min-K\%}(x) = \frac{1}{|E|}\sum_{x_i \in E} \log p(x_i \mid x_{<i}), \qquad E = \text{bottom-}k\%\text{ of tokens by } \log p(x_i \mid x_{<i})$$

The intuition is that memorization shows up most clearly on a text's *hardest* tokens — the ones a model with no memory of the sequence would genuinely struggle to predict, but a model that saw this exact sequence during training has partially memorized anyway. Averaging only over those tokens denoises the signal relative to whole-sequence perplexity. **Min-K%++** refines this by z-scoring each candidate token's log-probability against the model's own predictive distribution at that position — normalizing by the mean and variance of $\log p(\cdot \mid x_{<i})$ over the vocabulary — which controls for tokens that are inherently high- or low-entropy positions regardless of membership, giving a cleaner signal than raw Min-K% Prob.

Other detectors trade off differently: **perplexity/zlib ratio**, from the Carlini et al. training-data-extraction line of work, divides model perplexity by a text's zlib-compressibility to control for intrinsically repetitive or low-entropy strings looking memorized when they aren't. **DE-COP** (Duarte et al. 2024) sidesteps likelihood entirely — it builds multiple-choice items where one option is the verbatim original passage and the distractors are paraphrases, and checks whether the model prefers the verbatim option above chance, which is robust to some of the calibration issues that plague raw log-probability comparisons. **Guided prompting** (Golchin & Surdeanu 2023) feeds the model the first part of a suspected benchmark item and asks it to complete the rest; an implausibly exact completion is the signal. The **Oren et al. (2023) exchangeability test** ("Proving Test Set Contamination in Black-Box Language Models") is the most statistically principled: many benchmarks are stored and released in a fixed, non-random canonical order, and a model trained on that exact ordered sequence shows detectably non-exchangeable log-probabilities across the canonical order versus a randomly shuffled one — framed as a proper hypothesis test with a p-value, not a threshold-tuned heuristic.

## In practice

Applying any of these means computing a per-item score across a sample of suspect text and comparing the score distribution against a labeled "member" (known training-set) and "non-member" (known held-out) split, usually reported as an AUC. Shi et al.'s own evaluation benchmark, **WikiMIA**, is built by splitting Wikipedia articles into a "seen" set from before a model's training cutoff and an "unseen" set from after it — a construction that is directly relevant to the failure mode below. Where these methods genuinely work is on **verbatim, rare, high-entropy strings**: a full contest math problem statement, a distinctive block of code, a long literary quote — text specific and unusual enough that predicting it well is implausible without having seen it. Where they reliably fail is on **paraphrased, translated, or distributionally common text** — exactly the leakage vectors [[Concept - Benchmark Contamination]] identifies as hardest to catch, and exactly what Yang et al.'s rephrasing result showed defeats naive n-gram decontamination too.

## Failure modes

**The core confound: member/non-member splits differ in more than membership.** Most MIA evaluation setups build the "member" set from known-old training data and the "non-member" set from more-recently-published text — WikiMIA's pre-/post-cutoff construction is the textbook example. That means the detector can achieve a high reported AUC by picking up on *any* systematic difference between old and new text (vocabulary shift, topic drift, writing-style changes over time) rather than genuine memorization. **Symptom:** a detector reports strong separation on its own benchmark but the AUC collapses when member/non-member text is matched for date and topic. **Detection:** Duan et al. (2024), "Do Membership Inference Attacks Work on LLMs?", ran exactly this control and found most methods barely beat random once temporal and distributional confounds are removed. Maini et al. (2024) sharpened the same point from another angle: simple "blind" baselines that never look at the model at all — using only a text's publication date or surface features — rival the reported accuracy of full MIA detectors, which is direct evidence that the detectors are substantially reading distribution shift, not membership.

**Consequence:** as of 2026, no black-box contamination detector is reliable enough to trust as a standalone verdict. Canary strings and strict release-date discipline (see [[Concept - Benchmark Contamination]]) remain the durable defenses precisely because they don't depend on a detector's calibration at all.

## The non-obvious

The intuitive story — "lower loss means the model has seen it" — is, in most published evaluations, a distribution-shift artifact wearing a memorization costume. The single most useful sanity check for any contamination-detection claim is not "what's the AUC" but "were the member and non-member sets drawn from the same time period and topic distribution?" If they weren't, the AUC is measuring dataset drift, and the detector would report similar numbers even against a model that had never seen either set. This is also why the same MIA machinery underlies both contamination detection and privacy auditing of differential-privacy guarantees (the line of work from Shokri et al.'s original MIA framing through Carlini et al.'s extraction attacks) — one methodology, two different applications, and the confound bites both: a privacy audit with a badly-matched control group overstates protection in exactly the way a contamination detector with a badly-matched control group overstates leakage.

## Connections

- [[Concept - Benchmark Contamination]] — the phenomenon and its non-detection defenses (canaries, release-date discipline) this note's detection methods are trying, and largely failing, to make unnecessary.
- [[Concept - Deduplication at Scale]] — the corpus-hygiene approach (Data Engineering domain) that prevents contamination at the source rather than trying to detect it after training.
- [[Concept - Private and Dynamic Benchmarks]] — the structural alternative: benchmarks designed so membership inference is moot because the test data was never public to begin with.
- [[Concept - Entropy and Cross-Entropy]] — the information-theoretic quantities (Foundations domain) underlying every log-probability-based detector described here.
- [[Concept - Softmax]] — the per-token probability distribution (Neural Networks domain) that Min-K%++'s z-score normalization is computed against.
- [[Lore - Benchmark Scandals]] — concrete incidents (GSM1k, the rephrasing result) where contamination detection, or its absence, became the story.
- [[Concept - Training Set Decontamination]] — the pretraining-pipeline-side defense (Data Engineering domain) that doesn't depend on a downstream detector working at all.
- [[Concept - Statistical Rigor in Model Evaluation]] — a detector's reported AUC needs the same confidence-interval and confound discipline as any other benchmark number; an untiered AUC is exactly the "bare accuracy" sin that note warns against.

## Sources

- Shi, W. et al. (2023) — "Detecting Pretraining Data from Large Language Models." Introduces Min-K% Prob and the WikiMIA benchmark.
- Zhang, J. et al. (2024) — "Min-K%++: Improved Baseline for Detecting Pre-Training Data from Large Language Models." The normalized refinement of Min-K% Prob.
- Duan, M. et al. (2024) — "Do Membership Inference Attacks Work on LLMs?" The reliability critique showing most methods collapse to near-random once temporal/distributional confounds are controlled.
- Maini, P. et al. (2024) — blind-baseline critique showing simple non-model features (e.g. publication date) rival reported MIA detector accuracy, reinforcing the same confound.
- Oren, Y. et al. (2023) — "Proving Test Set Contamination in Black-Box Language Models." The exchangeability-test approach, framed as a formal hypothesis test.
- Duarte, A. et al. (2024) — "DE-COP: Detecting Copyrighted Content in Language Models Training Data." The multiple-choice verbatim-vs-paraphrase detection method.
