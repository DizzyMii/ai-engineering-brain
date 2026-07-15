---
tags: [concept, domain/prompting-context, level/frontier]
aliases: [format sensitivity, FormatSpread]
summary: "Trivial formatting choices — a separator, casing, spacing — can swing accuracy by tens of points, with no format universally best."
---
> **One-paragraph hook:** Swap a colon for a newline between a field and its value, and a model's accuracy on the exact same task and exemplars can move by dozens of percentage points — larger than the reported gap between competing frontier models on many leaderboards. Prompt formatting isn't cosmetic. It's a hidden hyperparameter that most teams never tune, never version, and never report — which means a good chunk of the field's benchmark comparisons are quietly format-conditioned without saying so.

## The mechanism

A model never sees "a field named X with value Y" as a semantic structure — it sees a token sequence, and different renderings of the same logical content produce genuinely different token sequences. Two effects compound here. First, tokenization boundaries shift with formatting: `" word"` and `"word"` are different tokens under [[Concept - Byte-Pair Encoding]], so something as small as a leading space before a label changes which vocabulary entries the model is actually conditioning on — in pathological cases this interacts with under-trained or anomalous vocabulary entries (see [[Lore - Glitch Tokens]]). Second, and more consequentially, different formats land the token sequence in different regions of the training distribution: a JSON-with-double-quotes rendering of a task might closely resemble thousands of post-training examples, while a superficially equivalent YAML-style rendering of the identical content might resemble almost none — the model isn't reasoning about the content abstractly, it's pattern-completing against whatever region of its training data the exact surface form most resembles.

Sclar et al. (2023), *"Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design"* (widely known as **FormatSpread**), measured this directly: holding the task and few-shot exemplars fixed and varying only surface-level formatting — separator characters, casing conventions, spacing between a field and its value, field ordering — accuracy swung by as much as roughly 76 percentage points on some model/task pairs. Critically, no single format was universally best across models: a format that maximized accuracy on one model family could be mediocre or actively harmful on another, so there is no "correct" format to memorize and reuse — only formats to measure per model.

## In practice

Structure still helps on net, even given this sensitivity: Anthropic recommends explicit XML tags (`<document>`, `<instructions>`, `<data>`) for Claude specifically because tagged structure reduces instruction/data bleed and improves parseability of the output, and markdown or JSON structuring more generally clarifies which role each input segment plays. The practical discipline is to fix **one** format, evaluate it properly under [[Concept - Prompt Evaluation and Versioning]], and version it — rather than hand-tuning formatting per example, which produces a prompt that looks polished on your dev set and is fragile everywhere else. The same consistency requirement applies within a prompt, not just across prompts: the [[Concept - In-Context Learning]] mechanism is itself format-sensitive, so few-shot exemplars must use identical delimiters and labels to the live query, or the model imitates the mismatch rather than the task.

The eval-reproducibility implication is the sharper practitioner concern: a reported benchmark number for model X on task Y using template A does not guarantee the same score under template B, so single-format capability comparisons between models should be treated with real suspicion. Where possible, report a spread across a handful of reasonable format variants rather than a single point estimate, and factor that spread into your confidence bounds via [[Concept - Statistical Rigor in Model Evaluation]] — a leaderboard gap smaller than the format-induced variance isn't a real capability difference, it's noise wearing a ranking.

## Failure modes

- **Silent benchmark inflation or deflation.** A lab (or a competitor) reports a number using a format template that happens to favor their model, without disclosing that format sensitivity is doing part of the work. Detection: re-run the eval under two or three independently reasonable format variants and check whether the ranking survives.
- **Few-shot/live-query format drift.** Exemplars formatted one way, the actual query formatted another — the model imitates whichever pattern is most locally consistent, often not the one you intended. Detection: diff the rendered exemplar and query strings character-for-character, not just eyeball them.
- **Formatting mistaken for a security boundary.** Wrapping untrusted content in delimiter tags is a real, useful hint that reduces instruction/data bleed, but it is a weak, non-security mitigation against [[Concept - Prompt Injection]] — content inside the delimiters can still steer the model, so never rely on formatting alone to separate trusted instructions from untrusted data.
- **Format staleness across model upgrades.** A template hand-tuned against one model version can silently underperform after a provider-side model swap, because the new version's post-training data distribution — and therefore which surface forms it resembles — has shifted. Detection: the same regression-testing discipline that catches any prompt drift, gated on model version changes.

## The non-obvious

Because reported eval numbers are format-conditioned, prompt format is effectively an undisclosed hyperparameter behind a large share of published model comparisons — and the FormatSpread magnitude (up to ~76 points) dwarfs most of the gaps that get treated as meaningful capability differences between frontier models. The practitioner-grade habit this creates: when your own eval numbers move after what felt like a harmless formatting tweak, check the format before concluding the model's capability changed. This is exactly the phenomenon that [[Concept - Prompt Format Sensitivity in Evaluation]] documents at the benchmark-methodology level — it's the same mechanism, just viewed from the evaluator's side of the table rather than the prompt engineer's.

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
