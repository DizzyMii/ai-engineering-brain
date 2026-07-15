---
tags: [concept, domain/fine-tuning, level/advanced]
aliases: [catastrophic interference]
summary: "Fine-tuning on narrow data erodes broad pretrained capabilities; PEFT, replay data, low LR, and KL penalties are the standard defenses."
---

# Concept - Catastrophic Forgetting

> **One-paragraph hook:** Fine-tuning has no built-in mechanism to preserve what the base model already knew how to do — gradient descent on a narrow objective will happily trade away general capability for on-task gain if that's what reduces the loss fastest. A fine-tune that improves a target metric by 5 points while silently dropping 15 points of general chat quality or instruction-following is not a win; it's a cost that never showed up on the dashboard you were watching. Catastrophic forgetting is that failure mode, and every fine-tuning project needs a plan to detect it, not just a plan to measure the thing it's optimizing for.

## The mechanism

Training minimizes $L_{\text{new}}(\theta)$ on the fine-tuning distribution with no term constraining behavior on the pretraining or instruction-tuning distribution. The pretrained solution occupies some region of parameter space that supports many capabilities at once — often described as a broad, relatively flat basin after large-scale pretraining. Fine-tuning gradients are computed entirely from the new, narrow dataset; nothing in the optimization objective bounds how far those gradients are allowed to push $\theta$ out of that basin. There's no conservation law protecting old behavior: $L_{\text{old}}(\theta)$ is free to rise arbitrarily as long as $L_{\text{new}}(\theta)$ falls. The classic, often-cited example: fine-tune a chat model purely on a narrow classification task (say, sentiment labels) and it "forgets" how to hold an open-ended conversation, defaulting to label-shaped completions even on prompts that have nothing to do with the fine-tuning task.

How much forgetting occurs is driven less by raw step count than by how far the fine-tuning distribution sits from the pretraining/instruction mixture. A fine-tune on a stylistic variant of chat — still broadly "in-distribution" for an instruction-tuned model — barely forgets even after many steps. A fine-tune on a narrow, structurally different task (pure classification, pure code completion, a rigid output schema) can measurably degrade general chat ability in a few hundred steps at an ordinary learning rate. Domain distance, not just training duration, is the load-bearing variable.

## In practice

- **Always eval base capabilities before and after.** Run a subset of general-knowledge probes (a slice of [[Breakdown - MMLU]]-style questions), open-ended chat quality, and refusal behavior on the exact same prompts pre- and post-fine-tune. This regression check is the core of the ship gate in [[Playbook - Evaluating a Fine-Tune]]: a fine-tune with positive on-task gain and negative net (task gain minus capability regression) should not ship.
- **PEFT forgets less by construction.** Biderman et al. 2024 ("LoRA Learns Less and Forgets Less") show that because [[Deep Dive - LoRA]] freezes the base and routes the update through a small, capacity-limited channel, the resulting parameters stay measurably closer to the pretrained solution than full fine-tuning at matched on-task performance — LoRA acts as an implicit regularizer against forgetting. This is the same underlying constraint discussed in [[Concept - Why LoRA Underperforms Full Fine-Tuning]]: the low capacity that caps how much LoRA can *learn* is exactly what limits how much it can *forget*.
- **Standard mitigations, roughly in order of how often teams reach for them:** lower learning rate and fewer epochs (1–3, not the "just run it for 10" instinct from small-model classical ML); replay/rehearsal — mix 5–30% general instruction data into the fine-tuning set so gradients keep seeing the original distribution, drawing from the same [[Concept - Data Mixtures]] logic used in pretraining; restrict to PEFT instead of full fine-tuning; add a KL penalty pulling the fine-tuned policy back toward the base model, the same [[Concept - KL Divergence]] machinery [[Deep Dive - RLHF End to End]] uses to bound policy drift during RL. Elastic-weight-consolidation-style per-parameter penalty methods exist in the broader continual-learning literature but see little use in LLM practice, because tracking per-parameter importance at LLM scale is expensive and PEFT already buys most of the same protection more cheaply.
- **Continued pretraining is the sharpest version of this problem.** Naively resuming next-token training on a narrow domain corpus at the original peak learning rate wrecks general ability quickly. Ibrahim et al. 2024 ("Simple and Scalable Strategies to Continually Pre-train LLMs") show that re-warming and re-decaying the learning-rate schedule, combined with a replay fraction of the original pretraining data mixture, recovers most of the lost general capability — the replay ratio is the single most load-bearing knob in that recovery, more than the exact LR schedule shape.

## Failure modes

- **Symptom — rising confidence, narrowing output on out-of-domain prompts.** Lower entropy and a shrinking effective vocabulary or format on prompts unrelated to the fine-tuning task is an early warning sign of forgetting, visible before it shows up as a benchmark-score drop. Check this specifically on prompts that look nothing like the training data.
- **Symptom — format/mode collapse.** Over-training on one narrow output format (a fixed JSON schema, a rigid response template) can collapse generation diversity even on prompts that don't call for that format at all; related to the broader generalization phenomena in [[Concept - Double Descent]] around how narrow training objectives reshape a model's output distribution.
- **Detection — evaluate every checkpoint, not just the final one.** Forgetting is often non-monotonic across epochs; the regression suite from [[Playbook - Evaluating a Fine-Tune]] run at epoch 1, 2, and 3 frequently shows checkpoint 1 beating checkpoint 3 on net value even though checkpoint 3 has the best training loss.
- **Silent failure mode:** teams that track only the on-task metric never observe forgetting until a user reports the model "got dumber" in production. The fix here is procedural, not algorithmic — always run the before/after base-capability comparison as a release gate, the same discipline covered in [[Concept - Supervised Fine-Tuning (SFT)]] workflows.

## The non-obvious

"Use a low learning rate and few epochs" is necessary advice but not sufficient — teams that tune only those two knobs and skip replay data are solving half the problem. Domain distance dominates step count: two fine-tunes with identical loss curves and identical step counts can forget at completely different rates depending on how far the fine-tuning distribution sits from the base model's training mixture. This is why the replay-data composition (what fraction of general instruction data gets mixed back in, and how representative it is of the original distribution) deserves as much engineering attention as the optimizer hyperparameters — it's frequently the difference between a fine-tune that ships and one that quietly regresses production quality.

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
