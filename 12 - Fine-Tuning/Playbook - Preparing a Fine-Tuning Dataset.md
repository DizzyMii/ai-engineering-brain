---
tags: [playbook, domain/fine-tuning, level/core]
aliases: []
summary: "End-to-end procedure for sourcing, sizing, formatting, and validating a fine-tuning dataset before training starts."
---

> **Goal:** build a training set that reliably teaches the target behavior without contaminating evals, blowing up on a template mismatch, or teaching the model to reproduce its own instructions. **When to run this:** before every [[Concept - Supervised Fine-Tuning (SFT)]] job — full fine-tune, [[Deep Dive - LoRA]], or QLoRA — never after. **Prerequisites:** a concrete definition of what "success" looks like for the target behavior, the exact tokenizer/chat template of the base model you're targeting, and a held-out eval set carved out before you touch training data.

## Steps

1. **Write the target behavior as a spec, not a vibe.** Action: for each input type the model will see in production, write the exact desired output shape (schema, tone, refusal boundary, citation format). Expected observation: you can point to a concrete example and say "this is right" or "this is wrong" without hedging. Deviation: if you can't write the spec in one sitting, the behavior isn't well-defined yet and no amount of data will fix that — go define it first.

2. **Hand-write ~10 gold examples before sourcing anything else.** Action: write ten (input, ideal output) pairs by hand, covering the median case and two edge cases. Expected observation: writing them surfaces ambiguity in your own spec — formatting inconsistencies, unclear boundary cases. Deviation: if the ten examples don't converge on a consistent format, your annotators (human or model) won't converge either; fix the spec before scaling.

3. **Decide sourcing strategy and size for quality, not volume.** Action: choose hand-writing, [[Concept - Knowledge Distillation]] from a stronger model, or mining production logs; pull ~10-50x your target count before filtering. Expected observation: after filtering you land somewhere in the 500-1,000 excellent-example range for most instruction/behavior fine-tunes — LIMA (Zhou et al. 2023, "Less Is More for Alignment") reached strong instruction-following alignment from exactly 1,000 curated, diverse examples on top of a strong base, no RLHF involved. Deviation: if you find yourself reaching for 100k+ scraped examples to hit a metric, that's a signal the examples are low-quality, not that you need more of them — quality beats quantity by a wide margin at fine-tuning scale.

4. **Near-deduplicate the pool.** Action: run near-dedup (MinHash or embedding-similarity clustering, see [[Concept - Deduplication at Scale]]) across the candidate pool before final selection. Expected observation: the pool shrinks and near-duplicate clusters collapse to one representative each. Deviation: skipping this lets a handful of templated examples dominate the gradient and teaches the model to memorize the template's incidental quirks instead of the general behavior.

5. **Format every example in the base model's exact chat template.** Action: render every example through the tokenizer's `apply_chat_template` (or equivalent) for the specific base checkpoint you're fine-tuning, including its real special tokens (see [[Concept - Chat Templates and Special Tokens]]). Expected observation: rendered text matches what the base model saw during its own instruction tuning — same role tags, same turn delimiters. Deviation: a mismatched template (ChatML markup on a Llama-3-formatted base, or vice versa) is the single most common silent failure in fine-tuning (see [[Gotchas - Fine-Tuning Data and Chat Templates]]) — the model doesn't error, it just never learns where a turn ends.

6. **Mask the prompt in the loss.** Action: zero out the loss on every token that isn't part of the target completion (mechanics owned by [[Concept - Loss Masking and Sequence Packing]]). Expected observation: the loss curve reflects prediction quality on the answer tokens only. Deviation: if you train on the full sequence including your own instructions, the model partially learns to *generate* instructions rather than *follow* them — a subtle failure that shows up as the model echoing or paraphrasing your system prompt at inference.

7. **Balance coverage: edge cases, refusals, and a replay slice.** Action: explicitly include boundary cases, examples that should be refused, and mix in 5-30% general-instruction data pulled from the base model's original SFT distribution (or a public equivalent) as replay. Expected observation: the dataset's behavior distribution matches production, not just the happy path. Deviation: a dataset that's 100% target-task with zero replay data is exactly the setup that produces [[Concept - Catastrophic Forgetting]] — the model gets great at the new task and forgets how to have a normal conversation.

8. **Split train/eval and dedup train against eval.** Action: carve out a held-out eval slice before any augmentation, then near-dedup the training set against both the eval slice and any public benchmark you plan to report against (see [[Concept - Benchmark Contamination]]). Expected observation: zero near-duplicate overlap between train and eval. Deviation: any train/eval overlap inflates your held-out metric, and you won't find out until the fine-tune underperforms in production relative to its eval score.

9. **Manually read 50 fully tokenized, fully formatted samples end to end.** Action: decode 50 final training examples exactly as the trainer will consume them — special tokens rendered, loss mask visible, no silent truncation. Expected observation: every sample ends with the correct EOS, no answer is cut off, and no example leaked from the eval set. Deviation: skipping this step is how teams discover — after a full training run — that 20% of their "formatted" examples were silently truncated to a stale max-length setting.

## Verification
- Re-decode a random 1% sample of the final tokenized dataset and confirm chat-template correctness, EOS placement, and loss-mask boundaries by eye.
- Run a 50-100 step smoke-training run and confirm loss drops from its initial value — a flat loss at this stage means the mask or template is broken, not that the model is "hard to train."
- Confirm dataset size and class/behavior balance match the spec from step 1 (e.g., refusals are 5-15% of the set, not 0% or 50%).
- Confirm zero overlap between train and eval via the near-dedup check from step 8.

## When it goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Loss never drops off its initial value | Loss mask covers the whole sequence, or chat template doesn't match base | Re-render one example by hand, diff against the tokenizer's `apply_chat_template` output |
| Held-out eval looks great, production looks bad | Train/eval contamination, or eval set too similar to train | Re-run near-dedup between train and eval; confirm eval was sourced independently |
| Model generates run-on text, never stops | Missing or duplicated EOS token in formatted examples | Inspect raw token ids of 10 samples, confirm exactly one EOS at the true end |
| Model echoes the instructions back | Prompt tokens not masked out of the loss | Verify the loss-mask array explicitly zeros every prompt token before the completion |
| Model got worse at general chat after fine-tuning | No replay/general-instruction slice in the dataset | Add 10-30% general instruction data and re-run; measure with [[Playbook - Evaluating a Fine-Tune]] |
| Fine-tune memorizes verbatim rather than generalizing | Dataset too small or too repetitive after dedup | Widen sourcing, raise dedup threshold, or reduce epochs |

## Connections
- [[Concept - Supervised Fine-Tuning (SFT)]] — this playbook produces the input to the SFT training step itself.
- [[Deep Dive - LoRA]] — the most common fine-tuning method this dataset feeds; formatting/masking requirements are identical whether the update is full-rank or low-rank.
- [[Playbook - Evaluating a Fine-Tune]] — the eval slice this playbook carves out in step 8 is exactly what that playbook consumes.
- [[Gotchas - Fine-Tuning Data and Chat Templates]] — the detailed pitfall catalog for exactly how steps 5, 6, and 8 fail in practice.
- [[Concept - Chat Templates and Special Tokens]] — owns the mechanics of the template rendering used in step 5.
- [[Concept - Loss Masking and Sequence Packing]] — owns the mechanics of the masking used in step 6.
- [[Concept - Knowledge Distillation]] — one of the three sourcing strategies in step 3.
- [[Concept - Synthetic Training Data]] — the corpus-construction theory behind model-generated sourcing, owned by data engineering.
- [[Concept - Deduplication at Scale]] — owns the algorithm used in step 4 and the train/eval dedup in step 8.
- [[Concept - Benchmark Contamination]] — the failure mode step 8's dedup exists to prevent.

## Sources
- Zhou et al. (2023) — "LIMA: Less Is More for Alignment." 1,000 curated examples matched or beat much larger instruction-tuned models on human preference, establishing the quality-over-quantity default for fine-tuning datasets.
