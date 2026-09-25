---
tags: [concept, domain/prompting-context, level/frontier]
aliases: [format sensitivity, FormatSpread]
summary: "Trivial formatting choices — a separator, casing, spacing — can swing accuracy by tens of points, with no format universally best."
---
> **One-paragraph hook:** Swap a colon for a newline between a field and its value and a model's accuracy on the same task with the same exemplars can move by dozens of percentage points. That's more than the reported gap between competing frontier models on many leaderboards. Prompt formatting is a hidden hyperparameter that most teams never tune, version or report, so a good share of the field's benchmark comparisons are format-conditioned without saying so.

## The mechanism

A model doesn't see "a field named X with value Y" as a semantic structure. It sees tokens, and different renderings of the same logical content are different token sequences. Two effects stack. First, formatting moves tokenization boundaries. `" word"` and `"word"` are different tokens under [[Concept - Byte-Pair Encoding]], so a leading space before a label changes which vocabulary entries the model conditions on. In pathological cases this runs into under-trained or anomalous vocabulary entries (see [[Lore - Glitch Tokens]]). Second, and more important, different formats put the sequence in different regions of the training distribution. A JSON rendering with double quotes might look like thousands of post-training examples, while an equivalent YAML-style rendering of the same content looks like almost none. The model pattern-completes against whatever part of its training data the surface form most resembles; it isn't reasoning about the content abstractly.

Sclar et al. (2023), *"Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design"* (usually called **FormatSpread**), measured it. With task and few-shot exemplars fixed and only surface formatting varied (separator characters, casing, spacing between field and value, field order), accuracy swung by as much as roughly 76 percentage points on some model/task pairs. No format was best across models. One that maximized accuracy on one model family could be mediocre or harmful on another. There's no correct format to memorize, only formats to measure per model.

## In practice

Structure still helps on net. Anthropic recommends explicit XML tags (`<document>`, `<instructions>`, `<data>`) for Claude because tagged structure reduces instruction/data bleed and makes output easier to parse, and markdown or JSON structure generally makes clear what role each input segment plays. The discipline is to pick **one** format, evaluate it properly under [[Concept - Prompt Evaluation and Versioning]], and version it. Hand-tuning formatting per example gives you a prompt that looks polished on your dev set and is fragile everywhere else. Consistency matters inside a prompt too. The [[Concept - In-Context Learning]] mechanism is itself format-sensitive, so few-shot exemplars need the same delimiters and labels as the live query, or the model copies the mismatch instead of the task.

For practitioners the sharper problem is eval reproducibility. A benchmark score for model X on task Y with template A doesn't guarantee the same score under template B, so be suspicious of single-format capability comparisons between models. Where you can, report a spread across a few reasonable format variants instead of a point estimate, and fold that spread into your confidence bounds via [[Concept - Statistical Rigor in Model Evaluation]]. A leaderboard gap smaller than the format-induced variance is noise dressed up as a ranking.

## Failure modes

- **Silent benchmark inflation or deflation.** A lab (or a competitor) reports a number with a template that happens to favor its model and doesn't disclose that format sensitivity is doing part of the work. Detection: re-run the eval under two or three independently reasonable format variants and see whether the ranking holds.
- **Few-shot vs. live-query format drift.** Exemplars in one format, the query in another. The model copies whichever pattern is most locally consistent, often not the one you meant. Detection: diff the rendered exemplar and query strings character by character; eyeballing isn't enough.
- **Formatting treated as a security boundary.** Wrapping untrusted content in delimiter tags is a useful hint that reduces instruction/data bleed, but against [[Concept - Prompt Injection]] it's a weak mitigation with no security guarantee. Content inside the delimiters can still steer the model, so never rely on formatting alone to separate trusted instructions from untrusted data.
- **Format goes stale across model upgrades.** A template hand-tuned for one model version can silently underperform after a provider-side model swap, because the new version's post-training distribution, and so which surface forms it resembles, has moved. Detection: the same regression testing that catches any prompt drift, gated on model version changes.

## The non-obvious

Since reported eval numbers are format-conditioned, prompt format is an undisclosed hyperparameter behind a large share of published model comparisons. The FormatSpread magnitude (up to ~76 points) is far bigger than most gaps treated as real capability differences between frontier models. The habit to build: when your own eval numbers move after what felt like a harmless formatting tweak, check the format before concluding the model's capability changed. [[Concept - Prompt Format Sensitivity in Evaluation]] documents the same mechanism at the benchmark-methodology level, seen from the evaluator's side of the table instead of the prompt engineer's.

## Connections
- [[Concept - Byte-Pair Encoding]] — the tokenization layer where formatting changes physically become different token sequences, the root cause of format sensitivity.
- [[Lore - Glitch Tokens]] — the pathological extreme where a formatting-induced tokenization boundary lands on an anomalous, under-trained vocabulary entry.
- [[Concept - Statistical Rigor in Model Evaluation]] — the discipline needed to tell a real capability gap from a format-induced variance artifact.
- [[Concept - Prompt Injection]] — the attack class that delimiter-based formatting weakly mitigates but never fully prevents.
- [[Concept - Prompt Evaluation and Versioning]] — the fix: freeze and version one format rather than re-tuning it ad hoc per example.
- [[Concept - Chat Templates and Special Tokens]] — the adjacent, model-mandatory formatting layer (the chat template itself) that this note's format-choice sensitivity sits on top of.
- [[Concept - In-Context Learning]] — few-shot demonstrations are themselves format-sensitive, and mismatched exemplar/query formatting is a direct failure mode of both.
- [[Concept - Prompt Format Sensitivity in Evaluation]] — the same phenomenon studied as a benchmark-methodology problem: how format choice silently conditions reported leaderboard numbers.

## Sources
- Sclar et al. (2023) — "Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design" (FormatSpread). The central empirical result: up to ~76-point accuracy swings from trivial formatting changes, no universally best format.
- Anthropic — Claude prompting documentation recommending XML-tag structuring for reducing instruction/data bleed (real system guidance, as of 2026).
