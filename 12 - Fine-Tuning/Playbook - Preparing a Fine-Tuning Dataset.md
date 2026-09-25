---
tags: [playbook, domain/fine-tuning, level/core]
aliases: []
summary: "End-to-end procedure for sourcing, sizing, formatting, and validating a fine-tuning dataset before training starts."
---

> **Goal:** build a training set that reliably teaches the target behavior without contaminating evals, breaking on a template mismatch, or teaching the model to reproduce its own instructions. **When to run this:** before every [[Concept - Supervised Fine-Tuning (SFT)]] job (full fine-tune, [[Deep Dive - LoRA]], or QLoRA), never after. **Prerequisites:** a concrete definition of success for the target behavior, the exact tokenizer/chat template of the base model you're targeting, and a held-out eval set carved out before you touch training data.

## Steps

1. **Write the target behavior as a spec.** Action: for each input type the model will see in production, write the exact desired output shape (schema, tone, refusal boundary, citation format). Expected observation: you can point at a concrete example and say "right" or "wrong" without hedging. Deviation: if you can't write the spec in one sitting, the behavior isn't defined yet and no amount of data will fix that. Define it first.

2. **Hand-write ~10 gold examples before sourcing anything else.** Action: write ten (input, ideal output) pairs by hand, covering the median case and two edge cases. Expected observation: writing them exposes ambiguity in your own spec, such as formatting inconsistencies and unclear boundary cases. Deviation: if your ten examples don't settle on a consistent format, your annotators (human or model) won't either. Fix the spec before scaling.

3. **Pick a sourcing strategy and size for quality, not volume.** Action: choose hand-writing, [[Concept - Knowledge Distillation]] from a stronger model, or mining production logs, and pull ~10-50x your target count before filtering. Expected observation: after filtering, most instruction/behavior fine-tunes land somewhere in the 500-1,000 excellent-example range. LIMA (Zhou et al. 2023, "Less Is More for Alignment") reached strong instruction-following alignment from exactly 1,000 curated, diverse examples on a strong base, with no RLHF. Deviation: if you're reaching for 100k+ scraped examples to hit a metric, that's a sign the examples are low-quality, not that you need more of them. At fine-tuning scale quality beats quantity by a wide margin.

4. **Near-deduplicate the pool.** Action: run near-dedup (MinHash or embedding-similarity clustering, see [[Concept - Deduplication at Scale]]) across the candidate pool before final selection. Expected observation: the pool shrinks and near-duplicate clusters collapse to one representative each. Deviation: skip this and a handful of templated examples dominate the gradient, teaching the model the template's incidental quirks instead of the general behavior.

5. **Format every example in the base model's exact chat template.** Action: render every example through the tokenizer's `apply_chat_template` (or equivalent) for the specific base checkpoint, with its real special tokens (see [[Concept - Chat Templates and Special Tokens]]). Expected observation: rendered text matches what the base model saw in its own instruction tuning, with the same role tags and turn delimiters. Deviation: a mismatched template (ChatML markup on a Llama-3-formatted base, or vice versa) is the most common silent failure in fine-tuning (see [[Gotchas - Fine-Tuning Data and Chat Templates]]). Nothing errors; the model just never learns where a turn ends.

6. **Mask the prompt in the loss.** Action: zero out the loss on every token outside the target completion (mechanics in [[Concept - Loss Masking and Sequence Packing]]). Expected observation: the loss curve reflects prediction quality on answer tokens only. Deviation: train on the full sequence, including your own instructions, and the model partly learns to *generate* instructions as well as *follow* them. It's subtle, and it shows up as the model echoing or paraphrasing your system prompt at inference.

7. **Balance coverage: edge cases, refusals, and a replay slice.** Action: include boundary cases and examples that should be refused, and mix in 5-30% general-instruction data from the base model's original SFT distribution (or a public equivalent) as replay. Expected observation: the dataset's behavior distribution matches production, not only the happy path. Deviation: a dataset that's 100% target task with zero replay is the classic setup for [[Concept - Catastrophic Forgetting]]. The model gets great at the new task and forgets how to hold a normal conversation.

8. **Split train/eval and dedup train against eval.** Action: carve out a held-out eval slice before any augmentation, then near-dedup the training set against the eval slice and any public benchmark you plan to report (see [[Concept - Benchmark Contamination]]). Expected observation: zero near-duplicate overlap between train and eval. Deviation: any overlap inflates your held-out metric, and you won't find out until the fine-tune underperforms its eval score in production.

9. **Read 50 fully tokenized, fully formatted samples end to end.** Action: decode 50 final training examples exactly as the trainer will consume them, with special tokens rendered, the loss mask visible, and no silent truncation. Expected observation: every sample ends with the correct EOS, no answer is cut off, and nothing leaked from the eval set. Deviation: skip this and you may find out after a full training run that 20% of your "formatted" examples were silently truncated to a stale max-length setting.

## Verification
- Re-decode a random 1% sample of the final tokenized dataset and check chat-template correctness, EOS placement and loss-mask boundaries by eye.
- Do a 50-100 step smoke-training run and confirm loss drops from its initial value. A flat loss at this stage means the mask or template is broken, not that the model is "hard to train."
- Confirm dataset size and class/behavior balance match the spec from step 1 (e.g., refusals are 5-15% of the set, not 0% or 50%).
- Confirm zero train/eval overlap via the near-dedup check from step 8.

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
