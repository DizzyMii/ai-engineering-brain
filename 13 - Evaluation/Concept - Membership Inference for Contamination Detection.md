---
tags: [concept, domain/evaluation, level/frontier]
aliases: [MIA, membership inference attack, Min-K% Prob]
summary: "Black-box methods for detecting whether text was in training data — and why most barely beat random once distribution shift is controlled."
---
> **One-paragraph hook:** [[Concept - Benchmark Contamination]] explains why contamination happens and why it's hard to prevent. This note takes the narrower, harder question: can you *prove* after the fact that a specific piece of text was in a specific model's training data, with nothing but black-box access to logits or generations? The methods are clever and the math is real. But the field's own most-cited 2024 finding is that most of them barely beat random once you control for the confound every naive setup has: the "seen" and "unseen" text usually differ in more than membership.

## The mechanism

Membership inference attacks (MIA) rest on a simple intuition. Gradient descent pushes loss down harder on training examples than on held-out examples with similar surface statistics, so a model should assign systematically higher likelihood (lower loss, lower perplexity) to text it has seen. The hard part is building a detector that isn't fooled by the fact that *some text is just easier to predict than other text*, whether or not it was in the training set.

**Min-K% Prob** (Shi et al. 2023) is the standard baseline. Averaging log-probability over every token dilutes the signal, since most tokens in any text are easy regardless of membership. So it looks only at the k% of tokens the model finds *least* likely:

$$\text{Min-K\%}(x) = \frac{1}{|E|}\sum_{x_i \in E} \log p(x_i \mid x_{<i}), \qquad E = \text{bottom-}k\%\text{ of tokens by } \log p(x_i \mid x_{<i})$$

Memorization should show most clearly on a text's *hardest* tokens: ones a model with no memory of the sequence would struggle to predict, but a model that trained on this exact sequence has partly memorized. Averaging only over those tokens gives a less noisy signal than whole-sequence perplexity. **Min-K%++** refines this by z-scoring each candidate token's log-probability against the model's own predictive distribution at that position, normalizing by the mean and variance of $\log p(\cdot \mid x_{<i})$ over the vocabulary. That controls for positions that are inherently high- or low-entropy regardless of membership, and the signal comes out cleaner than raw Min-K% Prob.

Other detectors make different trade-offs. The **perplexity/zlib ratio**, from Carlini et al.'s training-data-extraction work, divides model perplexity by the text's zlib-compressibility, so repetitive or low-entropy strings don't look memorized when they aren't. **DE-COP** (Duarte et al. 2024) skips likelihood entirely. It builds multiple-choice items where one option is the verbatim original passage and the distractors are paraphrases, then checks whether the model prefers the verbatim option above chance. That avoids some of the calibration problems of raw log-probability comparisons. **Guided prompting** (Golchin & Surdeanu 2023) feeds the model the first part of a suspected benchmark item and asks for the rest; an implausibly exact completion is the signal. The **Oren et al. (2023) exchangeability test** ("Proving Test Set Contamination in Black-Box Language Models") is the most statistically principled. Many benchmarks are stored and released in a fixed, non-random canonical order, and a model trained on that ordered sequence shows detectably non-exchangeable log-probabilities across the canonical order compared with a random shuffle. It's set up as a proper hypothesis test with a p-value, not a threshold-tuned heuristic.

## In practice

Using any of these means computing a per-item score over a sample of suspect text and comparing the score distribution against a labeled "member" (known training-set) and "non-member" (known held-out) split, usually reported as an AUC. Shi et al.'s own evaluation benchmark, **WikiMIA**, splits Wikipedia articles into a "seen" set from before a model's training cutoff and an "unseen" set from after it. Keep that construction in mind for the failure mode below. These methods work on **verbatim, rare, high-entropy strings**: a full contest math problem statement, a distinctive block of code, a long literary quote, text unusual enough that predicting it well without having seen it is implausible. They reliably fail on **paraphrased, translated or distributionally common text**. Those are the leakage vectors [[Concept - Benchmark Contamination]] identifies as hardest to catch, and the ones Yang et al.'s rephrasing result showed also defeat naive n-gram decontamination.

## Failure modes

**The core confound: member/non-member splits differ in more than membership.** Most MIA evaluations build the "member" set from known-old training data and the "non-member" set from more recently published text; WikiMIA's pre-/post-cutoff construction is the textbook case. A detector can then post a high AUC by picking up *any* systematic difference between old and new text (vocabulary shift, topic drift, changes in writing style) without detecting memorization at all. **Symptom:** a detector shows strong separation on its own benchmark, and the AUC collapses when member and non-member text are matched for date and topic. **Detection:** Duan et al. (2024), "Do Membership Inference Attacks Work on LLMs?", ran that control and found most methods barely beat random once temporal and distributional confounds were removed. Maini et al. (2024) made the same point from another direction: "blind" baselines that never look at the model, using only a text's publication date or surface features, rival the reported accuracy of full MIA detectors. That's direct evidence the detectors are substantially reading distribution shift, not membership.

**Consequence:** as of 2026, no black-box contamination detector is reliable enough to trust as a standalone verdict. Canary strings and strict release-date discipline (see [[Concept - Benchmark Contamination]]) stay the durable defenses because they don't depend on any detector's calibration.

## The non-obvious

In most published evaluations, the intuitive story ("lower loss means the model has seen it") is a distribution-shift artifact in a memorization costume. The most useful sanity check on any contamination-detection claim isn't the AUC. Ask whether the member and non-member sets came from the same time period and topic distribution. If not, the AUC measures dataset drift, and the detector would report similar numbers against a model that had never seen either set. The same MIA machinery also underlies privacy auditing of differential-privacy guarantees (from Shokri et al.'s original MIA framing through Carlini et al.'s extraction attacks). It's one methodology with two applications, and the confound bites both: a privacy audit with a badly matched control group overstates protection just as a contamination detector with a badly matched control group overstates leakage.

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
