---
tags: [concept, domain/post-training, level/surface]
aliases: [SFT, instruction tuning, instruction fine-tuning]
summary: "Behavior-cloning a base model on curated (prompt, response) demonstrations via next-token cross-entropy on completions — the first post-training stage."
---

> **One-paragraph hook:** SFT is ordinary supervised learning applied to conversations: next-token cross-entropy, computed only on the assistant's completion tokens, over a curated set of (prompt, response) demonstrations. It's the cheapest, most stable and least glamorous stage of post-training. Every later stage still depends on it, because it fixes the reference policy that preference optimization compares against and the starting distribution everything downstream has to work with.

## The mechanism

Mechanically, SFT is [[Concept - The Training Loop]] pointed at curated conversational data. Forward pass, backward pass and optimizer step are unchanged; only the dataset and the loss mask differ. The objective is the pretraining one (next-token cross-entropy), but over a far smaller curated set of demonstrations, with the loss restricted to completion tokens. [[Concept - Loss Masking and Sequence Packing]] has the bookkeeping. Before any of this, each demonstration is serialized into one token sequence via the model's [[Concept - Chat Templates and Special Tokens]], so a template bug silently corrupts every SFT example downstream.

SFT is an imitation objective computed per example. It teaches format, style and instruction-following, i.e. what a good answer looks like. It has no way to express a comparative judgment like "this answer is better than that one." Preference optimization exists to fill that gap.

The data lineage shows a shift in philosophy. Early instruction tuning (FLAN (Wei et al. 2021), T0, Super-NaturalInstructions) mixed hundreds of NLP tasks behind templated prompts and optimized for broad zero-shot task transfer. Alpaca (52K self-instruct examples), then Vicuna/ShareGPT and OpenHermes, moved toward fewer, more naturalistic multi-turn conversations that look like real chat usage. LIMA (Zhou et al. 2023) went further and gave us the "Superficial Alignment Hypothesis": roughly 1,000 very high-quality, diverse examples were enough to align a strong base model to a competitive standard. That's evidence SFT's job is more about surfacing latent capability correctly than teaching it from scratch.

## In practice

Typical config: 1–3 epochs (past roughly 3 the model starts memorizing instead of generalizing); learning rate in the $1\text{e-}5$ to $2\text{e-}5$ range for full fine-tuning, well below pretraining LRs because the model already sits in a good region of the loss surface and large steps can wreck it; cosine decay; sequence packing for throughput; loss only on completion tokens. The optimizer is almost always [[Concept - Adam and AdamW]].

Updating all weights versus a low-rank subset via [[Deep Dive - LoRA]] is a separate axis from the objective. Full fine-tuning and LoRA minimize the same masked cross-entropy and differ only in which parameters get gradient. That choice is mostly a compute/memory tradeoff, decided in the fine-tuning domain, and isn't an SFT-specific question.

Data hygiene matters more than any hyperparameter. Deduplicate near-identical examples. Decontaminate against eval sets (see [[Concept - Benchmark Contamination]]) so training doesn't silently inflate benchmark numbers. Diversify instruction coverage so the model doesn't overfit to one task shape. When human-written demonstrations can't reach the volume or diversity you need, [[Concept - Synthetic Training Data]] (model-generated instructions, responses, or both) fills the gap. The catch is that synthetic data inherits the generating model's biases and blind spots.

## Failure modes

The most common is overfitting to phrasing. Past the empirical 1–3 epoch ceiling, outputs repeat stock phrases, diversity collapses, and the model memorizes boilerplate instead of the underlying skill. Capability regression (the alignment tax) shows up as the SFT'd model scoring worse than the base checkpoint on unrelated held-out tasks, especially when the SFT mix is narrow.

Format lock-in is subtler. SFT can teach a rigid response shape, like a fixed opening phrase or fixed structure, so strongly that later preference optimization ([[Concept - Direct Preference Optimization (DPO)]] or [[Deep Dive - RLHF End to End]]) spends its budget undoing it before it can improve quality.

## The non-obvious

LIMA-scale results show quality beating quantity, so much of what looks like "SFT modeling work" is really data curation and filtering. Teams that pour engineering into RLHF/DPO tuning while treating SFT data as an afterthought routinely find out, late and expensively, that the quality ceiling was set at the SFT stage. It matters twice over because the SFT checkpoint becomes the frozen reference that KL-regularized preference optimization is anchored to. A garbage or over-fit SFT policy pushes its defects downstream however well later stages are tuned, since those stages are explicitly penalized for drifting far from it.

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
