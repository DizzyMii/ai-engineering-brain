---
tags: [concept, domain/post-training, level/core]
aliases: [KD, distillation, model distillation]
summary: "Transferring capability from a teacher model to a smaller or cheaper student via soft targets or teacher-generated training data."
---

# Concept - Knowledge Distillation
> **One-paragraph hook:** Knowledge distillation compresses or transfers capability from a teacher model into a student by training the student to match the teacher's outputs. That can mean its temperature-softened output distribution (classic Hinton-style distillation) or, in modern LLM practice, just its generated text. The second form dominates because most useful teachers are API-only black boxes: you can sample them but not look inside.

## The mechanism

There are two families. **Logit/soft-label distillation** (Hinton, Vinyals, and Dean 2015): given input $x$, the teacher produces logits softened by temperature $T$, $p_i = \text{softmax}(z_i/T)$, and the student learns to match this distribution via KL divergence, usually blended with ordinary hard-label cross-entropy:

$$\mathcal{L} = \alpha \cdot T^2 \cdot \text{KL}(p_{teacher,T} \| p_{student,T}) + (1-\alpha)\cdot \text{CE}(y_{hard}, p_{student})$$

The $T^2$ factor corrects for the $1/T^2$ shrink in gradient magnitude that temperature-softening introduces. Without it, high-$T$ soft targets barely move the student. "Dark knowledge" is the relative probability mass the teacher puts on *wrong* classes. A teacher that's 90% confident in "cat" but spreads the remaining 10% mostly over "dog," not "airplane," tells the student far more than the hard label does.

**Sequence-level KD** (Kim and Rush 2016) trains the student with ordinary [[Concept - Supervised Fine-Tuning (SFT)]] cross-entropy on teacher-*generated* sequences: sampled hard targets instead of matched soft distributions. All it needs is samples. No shared vocabulary, no logit access, no aligned tokenizer between teacher and student. That's why it's now the dominant LLM-era approach.

## In practice

The practical fork is white-box distillation (needs teacher logits and vocabulary alignment) versus black-box (API samples only, so distillation degenerates to SFT on the teacher's completions). Most practitioners run black-box: Alpaca (52K instructions distilled from GPT-3.5 completions), Vicuna (trained on real ShareGPT conversations), and Orca (reasoning traces distilled from GPT-4 explanations).

Modern named examples:

- DistilBERT (Sanh et al. 2019): 40% smaller than BERT, retains ~97% of GLUE performance using the blended soft+hard loss.
- Gemma-2/3: distilled from larger siblings in the same model family.
- Llama-3.2 1B/3B: distilled from the 8B/70B models via logit distillation plus pruning.
- [[Breakdown - DeepSeek-R1]]: distilled into a whole family of Qwen and Llama checkpoints via SFT on roughly 800K R1-generated reasoning traces. Those models beat larger non-reasoning models on math and code benchmarks purely from imitating R1's chain-of-thought, with no RL training of their own.

On-policy distillation / GKD (Agarwal et al. 2024) lets the student generate, and the teacher scores or corrects the student's own rollouts, often using reverse KL instead of forward KL. It goes straight at the exposure-bias mismatch described below.

## Failure modes

- **Capability ceiling.** The student can't exceed the teacher's knowledge or skill on a given task. Distillation compresses capability; it doesn't create any.
- **Hallucination and bias inheritance.** The student picks up the teacher's confabulations, refusal patterns and stylistic tics along with the correct behavior. Sequence-level KD has no way to separate "correct" from "teacher-typical."
- **Exposure bias in offline sequence-KD.** A student trained only on teacher-generated prefixes has never conditioned on its own errors. The first time it drifts slightly at inference, it's generating from an out-of-distribution context and mistakes compound. GKD/on-policy distillation exists to fix this.
- **Licensing exposure.** Several commercial API terms of service explicitly restrict using outputs to train competing models. It's a legal constraint, not a technical one, and it has complicated real distillation efforts.

## The non-obvious

Sequence-level KD isn't really a separate algorithm from plain [[Concept - Supervised Fine-Tuning (SFT)]]. The only difference is where the demonstrations came from: a bigger model instead of humans. So every SFT gotcha (loss masking, chat-template mismatch, overfitting to surface phrasing, format lock-in) applies unmodified. It also means most things labeled "distillation" in 2024–2026 open-model releases are SFT on model-generated data, not the temperature-softened KL formulation Hinton described. If you only have API access, the classic soft-label loss is the wrong tool: you can't KL-match logits you can't see.

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
