---
tags: [concept, domain/post-training, level/surface]
aliases: [SFT, instruction tuning, instruction fine-tuning]
summary: "Behavior-cloning a base model on curated (prompt, response) demonstrations via next-token cross-entropy on completions — the first post-training stage."
---

> **One-paragraph hook:** SFT is ordinary supervised learning applied to conversations: next-token cross-entropy loss, computed only on the assistant's completion tokens, over a curated set of (prompt, response) demonstrations. It is the cheapest, most stable, and least glamorous stage of post-training — and also the one every later stage depends on, because it fixes the reference policy that preference optimization compares against and the starting distribution everything downstream has to work with.

## The mechanism

SFT is [[Concept - The Training Loop]] unchanged in mechanics, re-pointed at curated conversational data: same forward pass, same backward pass, same optimizer step, just a different dataset and a masked loss. It uses the same objective as pretraining — next-token cross-entropy — but on a far smaller, curated set of demonstrations, with the loss restricted to completion tokens (the exact bookkeeping is in [[Concept - Loss Masking and Sequence Packing]]). Demonstrations are serialized into a single token sequence via the model's [[Concept - Chat Templates and Special Tokens]] before any of this happens, so a template bug corrupts every downstream SFT example silently. Because SFT is an imitation objective computed per-example, it teaches format, style, and instruction-following — what a good answer looks like — but has no mechanism for expressing a comparative judgment like "this answer is better than that one." That gap is what preference optimization exists to fill.

The data lineage traces a shift in philosophy. Early instruction tuning — FLAN (Wei et al. 2021), T0, Super-NaturalInstructions — mixed hundreds of NLP tasks behind templated prompts, optimizing for broad zero-shot task transfer. Alpaca (52K self-instruct examples) and then Vicuna/ShareGPT and OpenHermes moved toward fewer, more naturalistic multi-turn conversations, closer to actual chat usage. LIMA (Zhou et al. 2023) pushed this further and crystallized the "Superficial Alignment Hypothesis": roughly 1,000 extremely high-quality, diverse examples were enough to align a strong base model to a competitive standard, evidence that SFT's job is more about surfacing latent capability correctly than teaching it from scratch.

## In practice

Typical configuration: 1–3 epochs (past roughly 3 the model starts memorizing rather than generalizing), learning rate in the $1\text{e-}5$ to $2\text{e-}5$ range for full fine-tuning — well below pretraining LRs, since the model is already in a good region of the loss landscape and large steps risk destroying it — cosine decay, sequence packing for throughput, and loss computed only on completion tokens. The optimizer is almost always [[Concept - Adam and AdamW]].

Whether to update all weights or a low-rank subset via [[Deep Dive - LoRA]] is a separate axis from the objective described here: full fine-tuning and LoRA both minimize the same masked cross-entropy loss, they differ only in which parameters receive gradient, and the choice is primarily a compute/memory tradeoff decided in the fine-tuning domain rather than an SFT-specific question.

Data hygiene dominates outcomes more than any hyperparameter choice: deduplicate near-identical examples, decontaminate against evaluation sets (see [[Concept - Benchmark Contamination]]) so training doesn't silently inflate benchmark numbers, and diversify instruction coverage so the model doesn't overfit to one task shape. When human-written demonstrations don't scale to the required volume or diversity, [[Concept - Synthetic Training Data]] — model-generated instructions, responses, or both — fills the gap, with the tradeoff that synthetic data inherits the generating model's biases and blind spots.

## Failure modes

Overfitting to phrasing is the most common: past the empirical 1–3 epoch ceiling, outputs start repeating stock phrases, diversity collapses, and the model memorizes boilerplate rather than generalizing the underlying skill. Capability regression (the alignment tax) shows up as the SFT'd model doing worse than the base checkpoint on unrelated held-out tasks, particularly when the SFT mix is narrow. A subtler failure is format lock-in: SFT can teach a rigid response shape (a fixed opening phrase, a fixed structure) so strongly that later preference optimization — [[Concept - Direct Preference Optimization (DPO)]] or [[Deep Dive - RLHF End to End]] — has to spend its budget undoing it rather than improving quality.

## The non-obvious

Because LIMA-scale results show quality dominating quantity, a large share of what looks like "SFT modeling work" is actually data curation and filtering work, and teams that pour their engineering effort into RLHF/DPO tuning while treating SFT data as an afterthought routinely discover — expensively, late — that the quality ceiling was set at the SFT stage, not the preference stage. This matters doubly because the SFT checkpoint becomes the frozen reference model that KL-regularized preference optimization is anchored to: a garbage or over-fit SFT policy propagates its defects downstream no matter how well-tuned later stages are, since those stages are explicitly penalized for drifting far from it.

## Connections

- [[Concept - The Training Loop]] — SFT is the standard supervised training loop, re-pointed at curated conversational data.
- [[Concept - Loss Masking and Sequence Packing]] — the exact mechanics of which tokens carry gradient and how examples are batched efficiently.
- [[Concept - Chat Templates and Special Tokens]] — the serialization format that turns a conversation into the token sequence SFT actually trains on.
- [[Deep Dive - LoRA]] — the parameter-efficient alternative to full-weight SFT when compute or memory is constrained.
- [[Concept - Synthetic Training Data]] — where SFT demonstrations increasingly come from when human-written data doesn't scale.
- [[Deep Dive - RLHF End to End]] — the stage that follows SFT and depends on the SFT checkpoint as its reference and starting policy.
- [[Concept - Adam and AdamW]] — the optimizer used for the SFT weight update, at a much lower learning rate than pretraining.
- [[Concept - Benchmark Contamination]] — the hygiene check that must run against SFT data before training or eval numbers mean anything.
- [[Concept - Direct Preference Optimization (DPO)]] — the stage that sometimes has to undo SFT-induced format lock-in.

## Sources

- Wei et al. (2021) — "Finetuned Language Models Are Zero-Shot Learners" (FLAN). Establishes instruction tuning across many templated tasks.
- Zhou et al. (2023) — "LIMA: Less Is More for Alignment." ~1K curated examples align a strong base model; the Superficial Alignment Hypothesis.
