---
tags: [concept, domain/fine-tuning, level/advanced]
aliases: [catastrophic interference]
summary: "Fine-tuning on narrow data erodes broad pretrained capabilities; PEFT, replay data, low LR, and KL penalties are the standard defenses."
---

# Concept - Catastrophic Forgetting

> **One-paragraph hook:** nothing in fine-tuning preserves what the base model already knew how to do. Gradient descent on a narrow objective will happily trade general capability for on-task gain if that lowers the loss fastest. A fine-tune that gains 5 points on the target metric while silently dropping 15 points of general chat quality or instruction-following is a loss, one that never showed up on the dashboard you were watching. That's catastrophic forgetting, and every fine-tuning project needs a plan to detect it as well as a plan to measure the target.

## The mechanism

Training minimizes $L_{\text{new}}(\theta)$ on the fine-tuning distribution, with no term constraining behavior on the pretraining or instruction-tuning distribution. The pretrained solution sits in some region of parameter space that supports many capabilities at once, often described as a broad, relatively flat basin after large-scale pretraining. Fine-tuning gradients come entirely from the new, narrow dataset, and nothing in the objective limits how far they push $\theta$ out of that basin. Old behavior has no protection: $L_{\text{old}}(\theta)$ can rise arbitrarily as long as $L_{\text{new}}(\theta)$ falls. The classic, often-cited example: fine-tune a chat model purely on a narrow classification task (say, sentiment labels) and it "forgets" how to hold an open-ended conversation, producing label-shaped completions even on prompts unrelated to the task.

How much it forgets depends less on step count than on how far the fine-tuning distribution sits from the pretraining/instruction mixture. A fine-tune on a stylistic variant of chat, still broadly in-distribution for an instruction-tuned model, barely forgets even after many steps. A fine-tune on a narrow, structurally different task (pure classification, pure code completion, a rigid output schema) can measurably degrade general chat in a few hundred steps at an ordinary learning rate. Domain distance matters more than training duration.

## In practice

- **Always eval base capabilities before and after.** Run general-knowledge probes (a slice of [[Breakdown - MMLU]]-style questions), open-ended chat quality and refusal behavior on the same prompts pre- and post-fine-tune. This regression check is the core of the ship gate in [[Playbook - Evaluating a Fine-Tune]]. A fine-tune with a positive on-task gain but a negative net (task gain minus capability regression) shouldn't ship.
- **PEFT forgets less by construction.** Biderman et al. 2024 ("LoRA Learns Less and Forgets Less") show that [[Deep Dive - LoRA]], by freezing the base and routing the update through a small, capacity-limited channel, ends up measurably closer to the pretrained solution than full fine-tuning at matched on-task performance. LoRA acts as an implicit regularizer against forgetting. It's the same constraint discussed in [[Concept - Why LoRA Underperforms Full Fine-Tuning]]: the low capacity that caps how much LoRA can *learn* also limits how much it can *forget*.
- **Standard mitigations**, roughly in order of how often teams use them. Lower the learning rate and cut epochs (1–3, not the "just run it for 10" instinct from small-model classical ML). Add replay/rehearsal: mix 5–30% general instruction data into the fine-tuning set so the gradients keep seeing the original distribution, the same [[Concept - Data Mixtures]] logic used in pretraining. Use PEFT instead of full fine-tuning. Add a KL penalty that pulls the fine-tuned policy back toward the base model, the same [[Concept - KL Divergence]] machinery [[Deep Dive - RLHF End to End]] uses to bound policy drift during RL. Elastic-weight-consolidation-style per-parameter penalties exist in the broader continual-learning literature but see little LLM use: tracking per-parameter importance at LLM scale is expensive, and PEFT buys most of the same protection more cheaply.
- **Continued pretraining is the sharpest version of the problem.** Naively resuming next-token training on a narrow domain corpus at the original peak learning rate wrecks general ability fast. Ibrahim et al. 2024 ("Simple and Scalable Strategies to Continually Pre-train LLMs") show that re-warming and re-decaying the learning-rate schedule, plus a replay fraction of the original pretraining mixture, recovers most of the lost general capability. The replay ratio is the knob that matters most in that recovery, more than the exact LR schedule shape.

## Failure modes

- **Symptom: rising confidence and narrowing output on out-of-domain prompts.** Lower entropy and a shrinking effective vocabulary or format on prompts unrelated to the fine-tuning task are an early sign of forgetting, visible before any benchmark score drops. Check specifically on prompts that look nothing like the training data.
- **Symptom: format/mode collapse.** Over-training on one narrow output format (a fixed JSON schema, a rigid response template) can collapse generation diversity even on prompts that don't call for that format. It's related to the broader generalization phenomena in [[Concept - Double Descent]] around how narrow objectives reshape a model's output distribution.
- **Detection: evaluate every checkpoint, not only the last.** Forgetting is often non-monotonic across epochs. Run the regression suite from [[Playbook - Evaluating a Fine-Tune]] at epoch 1, 2, and 3 and it frequently shows checkpoint 1 beating checkpoint 3 on net value, even though checkpoint 3 has the best training loss.
- **Silent failure:** teams that track only the on-task metric don't see forgetting until a user reports the model "got dumber" in production. The fix is procedural. Run the before/after base-capability comparison as a release gate, the same discipline covered in [[Concept - Supervised Fine-Tuning (SFT)]] workflows.

## The non-obvious

"Use a low learning rate and few epochs" is necessary but not sufficient. Teams that tune only those two knobs and skip replay data solve half the problem. Domain distance dominates step count: two fine-tunes with identical loss curves and step counts can forget at completely different rates depending on how far the fine-tuning data sits from the base model's training mixture. So the replay-data composition (what fraction of general instruction data goes back in, and how representative it is of the original distribution) deserves as much engineering attention as the optimizer hyperparameters. It's frequently what separates a fine-tune that ships from one that quietly regresses production quality.

## Connections
- [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — the flip side of the same regularization story: what limits forgetting also limits learning capacity.
- [[Concept - What Fine-Tuning Can and Cannot Teach]] — forgetting is the downside risk of the same "fine-tuning reshapes $p(y|x)$" mental model.
- [[Deep Dive - LoRA]] — the frozen-base-plus-small-update mechanism that makes PEFT forget measurably less than full fine-tuning.
- [[Playbook - Evaluating a Fine-Tune]] — the operational procedure for actually measuring forgetting before shipping a fine-tune.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the most common training regime in which this pathology first shows up.
- [[Deep Dive - RLHF End to End]] — RLHF's KL-to-base-policy term is the same anti-forgetting mechanism generalized to the RL setting.
- [[Concept - KL Divergence]] — the mathematical tool used to bound drift away from the base model's distribution.
- [[Concept - Data Mixtures]] — the replay-ratio knob that determines how much forgetting a given fine-tune incurs.
- [[Concept - Double Descent]] — a related generalization phenomenon relevant to how narrow-objective training reshapes model behavior.

## Sources
- Biderman et al. (2024) — "LoRA Learns Less and Forgets Less." Direct empirical comparison of forgetting between LoRA and full fine-tuning.
- Ibrahim et al. (2024) — "Simple and Scalable Strategies to Continually Pre-train LLMs." LR re-warming plus replay fraction as the fix for continued-pretraining forgetting.
- Kirkpatrick et al. (2017) — "Overcoming Catastrophic Forgetting in Neural Networks." The foundational continual-learning framing (Elastic Weight Consolidation) that named the problem this note addresses in the LLM fine-tuning context.
