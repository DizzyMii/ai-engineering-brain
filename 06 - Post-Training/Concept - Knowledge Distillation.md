---
tags: [concept, domain/post-training, level/core]
aliases: [KD, distillation, model distillation]
summary: "Transferring capability from a teacher model to a smaller or cheaper student via soft targets or teacher-generated training data."
---

# Concept - Knowledge Distillation
> **One-paragraph hook:** Knowledge distillation compresses or transfers capability from a teacher model into a student by training the student to match the teacher's outputs — either its temperature-softened output distribution (classic Hinton-style distillation) or, in modern LLM practice, simply its generated text. The second form dominates because most useful teachers are API-only black boxes you can only sample, not introspect.

## The mechanism

Two families exist. **Logit/soft-label distillation** (Hinton, Vinyals, and Dean 2015): given input $x$, the teacher produces logits softened by temperature $T$, $p_i = \text{softmax}(z_i/T)$, and the student is trained to match this distribution via KL divergence, usually blended with ordinary hard-label cross-entropy:

$$\mathcal{L} = \alpha \cdot T^2 \cdot \text{KL}(p_{teacher,T} \| p_{student,T}) + (1-\alpha)\cdot \text{CE}(y_{hard}, p_{student})$$

The $T^2$ factor corrects for the $1/T^2$ shrink in gradient magnitude that temperature-softening introduces — without it, high-$T$ soft targets barely move the student. "Dark knowledge" is the relative probability mass the teacher places on *wrong* classes: a teacher that's 90% confident in "cat" but spreads the remaining 10% mostly over "dog," not "airplane," tells the student far more than the hard label alone does.

**Sequence-level KD** (Kim and Rush 2016): the student is trained via ordinary [[Concept - Supervised Fine-Tuning (SFT)]] cross-entropy directly on teacher-*generated* sequences — sampled hard targets rather than matched soft distributions. This needs nothing but samples: no shared vocabulary, no logit access, no aligned tokenizer between teacher and student, which is why it's now the dominant LLM-era approach.

## In practice

White-box distillation (needs teacher logits, requires vocabulary alignment) versus black-box (API samples only — distillation degenerates to SFT on the teacher's completions) is the practical fork. Black-box is what most practitioners actually run: Alpaca (52K instructions distilled from GPT-3.5 completions), Vicuna (trained on real ShareGPT conversations), and Orca (reasoning traces distilled from GPT-4 explanations).

Modern named examples: DistilBERT (Sanh et al. 2019 — 40% smaller than BERT, retains ~97% of GLUE performance using the blended soft+hard loss), Gemma-2/3 (distilled from larger siblings within the same model family), Llama-3.2 1B/3B (distilled from the 8B/70B models via logit distillation plus pruning), and [[Breakdown - DeepSeek-R1]] distilled into an entire family of Qwen and Llama checkpoints via SFT on roughly 800K R1-generated reasoning traces — those distilled models beat larger non-reasoning models on math and code benchmarks purely from imitating R1's chain-of-thought, with no RL training of their own.

On-policy distillation / GKD (Agarwal et al. 2024): instead of training only on the teacher's own samples, let the student generate and have the teacher score or correct the student's own rollouts, often using reverse KL rather than forward KL. This directly targets the exposure-bias mismatch below.

## Failure modes

- **Capability ceiling.** The student cannot exceed the teacher's knowledge or skill on a given task — distillation compresses capability, it does not create it.
- **Hallucination and bias inheritance.** The student learns not just correct behavior but the teacher's confabulations, refusal patterns, and stylistic tics, because sequence-level KD has no mechanism to separate "correct" from "teacher-typical."
- **Exposure bias in offline sequence-KD.** A student trained only on teacher-generated prefixes has never conditioned on its own errors during training; the first time it deviates slightly at inference, it's now generating from an out-of-distribution context, and mistakes compound. GKD/on-policy distillation exists specifically to fix this.
- **Licensing exposure.** Several commercial API terms of service explicitly restrict using outputs to train competing models — a legal rather than technical constraint that has complicated real distillation efforts.

## The non-obvious

Sequence-level KD is not really a distinct algorithm from plain [[Concept - Supervised Fine-Tuning (SFT)]] — the only difference is where the demonstrations came from (a bigger model instead of humans). That means every SFT gotcha — loss masking, chat-template mismatch, overfitting to surface phrasing, format lock-in — applies directly and unmodified. It also means most things labeled "distillation" in 2024–2026 open-model releases are just SFT on model-generated data, not the temperature-softened KL formulation Hinton described. Practitioners who reach for the classic soft-label loss when they only have API access are solving the wrong problem entirely: you cannot KL-match logits you cannot see.

## Connections

- [[Concept - Entropy and Cross-Entropy]] — the hard-label term in the classic distillation loss is ordinary cross-entropy against the ground-truth label.
- [[Concept - KL Divergence]] — the soft-target term is a temperature-scaled KL divergence between teacher and student output distributions.
- [[Concept - Softmax]] — temperature softening operates directly on the softmax that produces both the teacher's and the student's output distributions.
- [[Concept - Synthetic Training Data]] — sequence-level KD is a specific case of training on model-generated (synthetic) data.
- [[Breakdown - DeepSeek-R1]] — the highest-profile 2025 distillation event: R1's reasoning traces distilled into a full family of smaller open models.
- [[Concept - Post-Training Quantization Formats]] — distillation and quantization are the two complementary levers for shrinking a deployed model, frequently combined.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — distilling long CoT traces is now a primary path to giving small models reasoning ability without running RL.
- [[Reference - Model Genealogy]] — teacher-to-student distillation relationships are exactly the edges this genealogy reference tracks.
- [[Concept - Supervised Fine-Tuning (SFT)]] — sequence-level distillation is mechanically identical to SFT with teacher-generated completions as the demonstration data.

## Sources

- Hinton, Vinyals, and Dean (2015) — Distilling the Knowledge in a Neural Network. The temperature-softened soft-label formulation and "dark knowledge."
- Kim and Rush (2016) — Sequence-Level Knowledge Distillation. Establishes training on teacher-generated sequences as the dominant LLM-era approach.
- Agarwal et al. (2024) — On-Policy Distillation of Language Models (GKD). Fixes offline sequence-KD's exposure-bias mismatch.
