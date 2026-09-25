---
tags: [gotchas, domain/post-training, level/advanced]
aliases: [RLHF instability, PPO instability, RL fine-tuning gotchas, reward collapse]
summary: "RLHF/DPO/GRPO failure modes ordered by pain: reward hacking, entropy collapse, value divergence, DPO degeneracy, length explosion, silent setup bugs."
---

# Gotchas - RLHF Training Instabilities

## 1. Reward climbs while output quality visibly craters

**Symptom:** the scalar reward trends up steadily for hundreds of steps, but generations get more repetitive, more sycophantic, more stuffed with headers and bullet points. A held-out human or [[Concept - LLM-as-Judge|LLM-judge]] win-rate against the SFT baseline stalls or falls while the training-time reward keeps climbing.
**Cause:** [[Concept - Reward Hacking]]. As the policy's [[Concept - KL Control in RLHF|KL divergence]] from the reference model grows, it drifts into regions of output space the reward model never trained on and is miscalibrated in. Gao et al. (2023)'s overoptimization scaling law shows true reward rising then falling with KL while the RM's proxy reward keeps going up; for Bradley-Terry RMs the gold-vs-proxy gap widens roughly with the square root of KL.
**Fix:** raise the KL coefficient $\beta$ (or lower an adaptive controller's target KL), refresh or retrain the RM on fresh on-policy comparisons instead of trusting a static one, and pick checkpoints by held-out eval win-rate, not the training reward curve.
**Detection:** plot reward against KL, not against step. The (reward, KL) frontier is the diagnostic, and the signature is reward that keeps rising well past the point where an independent eval plateaus or falls. Length and markdown-formatting metrics make useful leading indicators (see gotcha 6).

## 2. Generation collapses into gibberish or one repeated phrase

**Symptom:** sampling entropy falls toward zero over training and outputs degrade into a repeated token, a short repeated phrase, or incoherent text, sometimes within a few hundred steps. It's the same output-narrowing pathology tracked as [[Concept - Mode Collapse in RLHF|mode collapse]].
**Cause:** entropy collapse. The KL leash is too loose (β too low) or the learning rate too high, so each update sharpens the output distribution faster than exploration can push back. The clipped surrogate in [[Concept - PPO for Language Models]] or [[Concept - GRPO and RL with Verifiable Rewards]] keeps reinforcing whatever already has probability mass, and mass on the alternatives never comes back. See [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]].
**Fix:** raise β, lower the learning rate, add an explicit entropy bonus, or use an asymmetric clip that allows larger upward moves on low-probability tokens (DAPO's "clip-higher"). Once collapse has fully set in it's usually not recoverable within the run. Restart from an earlier checkpoint instead of trying to fix it forward.
**Detection:** log policy entropy every step, not only at evals. A monotonically falling entropy curve is the earliest and cleanest warning, well before outputs look obviously broken to a human reader.

## 3. PPO's value loss explodes or NaNs

**Symptom:** value loss grows by orders of magnitude over a handful of steps, gradient norms spike, and the run either NaNs or policy quality collapses right after.
**Cause:** miscalibrated returns or advantages feeding the value head. Usually reward wasn't normalized, GAE advantages weren't whitened, or the value function was never warmed up before joint policy/value updates started, so the critic chases a moving, unstable target from step one.
**Fix:** normalize and clip rewards before computing returns, whiten advantages to mean 0 / variance 1 each batch, clip the value loss the same way the policy surrogate is clipped, and run a short value-only warmup before the policy update kicks in.
**Detection:** log value loss and advantage magnitude as primary training curves next to reward and KL. Value loss trending up for more than a handful of consecutive steps, well before any NaN, is the early signal you can act on.

## 4. DPO: chosen and rejected logprobs both fall while the margin keeps growing

**Symptom:** the [[Concept - Direct Preference Optimization (DPO)]] loss drops steadily and the implicit reward margin (chosen minus rejected) widens as expected. But the *absolute* log-probabilities of chosen and rejected responses both trend down, and generations lose fluency even though the loss curve looks perfectly healthy.
**Cause:** the DPO loss constrains only the *difference* between chosen and rejected implicit rewards, not their absolute scale. It's entirely possible, and empirically common, for the optimizer to satisfy the loss by pushing both probabilities down together instead of raising the chosen one.
**Fix:** add an NLL/SFT regularization term on the chosen response to anchor its absolute likelihood (Llama 3's RPO approach), and lower β so the margin needed to satisfy the loss is smaller.
**Detection:** you can't see this from the DPO loss curve. Log `policy_chosen_logps` and `policy_rejected_logps` as separate curves alongside their difference, per [[Snippet - DPO Loss Implementation]]. Treat that pair of curves as mandatory.

## 5. Reward-model scores converge to near-identical values across a batch

**Symptom:** RM score variance across a rollout batch shrinks until nearly every sampled completion for a prompt gets almost the same reward, whatever the visible quality differences. The policy update has effectively nothing left to learn from.
**Cause:** the reward model has saturated or gone out-of-distribution. As the policy improves and its outputs concentrate in a narrower region, a static RM (trained once on an earlier, more diverse distribution) loses the resolution to tell them apart. Same distribution-shift root cause as gotcha 1, showing up as flatness instead of exploitation.
**Fix:** periodically refresh the RM with freshly labeled on-policy comparisons (iterated/online RLHF, as in Anthropic's HH pipeline), or switch late in training to an RM ensemble whose disagreement tells you when scores are becoming unreliable.
**Detection:** track RM-score variance within each rollout batch over time. A steady decline toward zero variance is the tell, whether or not mean reward is still rising.

## 6. Response length grows without bound across training

**Symptom:** mean completion length climbs step over step, often well past what the task needs, while human/judge win-rate stays flat or even drops against length-matched baselines.
**Cause:** [[Concept - Length Bias in Preference Optimization]]. Human labelers, RMs, and LLM judges all show a documented, well-replicated tendency to rate longer answers higher regardless of content, so any reward-driven optimization finds length a cheap lever that's always available.
**Fix:** add an explicit length penalty to the reward, switch to a length-normalized objective (SimPO-style), or balance preference-pair lengths during data curation so chosen and rejected responses aren't systematically different lengths (see [[Checklist - Preference Data Quality]]).
**Detection:** plot mean response length against training step as its own curve. A steady upward trend with no matching win-rate gain is unambiguous.

## 7. KL reads as nonsensical from the very first logged step

**Symptom:** at step 0, when policy and reference should be numerically identical, the KL-to-reference is negative, wildly large, or otherwise implausible (nowhere near ~0).
**Cause:** the generation, reference, and training preprocessing paths don't match: different tokenizer instances, chat-template version drift between sampler and trainer, or a reference model loaded with different special-token handling than the policy. The two log-probability streams aren't scoring the same token sequence.
**Fix:** share one tokenizer and [[Concept - Loss Masking and Sequence Packing|chat-template]] configuration object across the generation, reference-scoring, and training code paths. Add a startup assertion that KL is within a small epsilon of zero when policy weights equal reference weights.
**Detection:** check KL at step 0 before trusting anything else about the run. With policy == reference it should be ~0. Any deviation there is a setup bug, not training dynamics, and left unfixed it invalidates every later signal.

## 8. Preprocessing bugs silently carried over from SFT into RL

**Symptom:** no loud errors, but the model behaves subtly worse than expected from the earliest steps. It never emits an end token cleanly, say, or its outputs read as if the first token were duplicated or shifted.
**Cause:** two common carryover bugs. Either the SFT loss mask (or the tokenization convention under it) is reused in the RL data pipeline without re-verification, or the RL sampler prepends its own BOS token on top of the one the chat template already emits, a double-BOS distribution shift the model never saw during SFT.
**Fix:** run the same decode-and-inspect sanity check used to validate SFT data (see [[Snippet - Loss Masking a Chat Dataset]]) on the exact prompts fed to the RL sampler, and diff the tokenized output against what the reference model's tokenizer path produces for the same input.
**Detection:** decode a handful of real training batches from the RL pipeline (not the SFT pipeline) token by token. Confirm there's no duplicated BOS and that special tokens match the reference/policy's expected format exactly. It's cheap, and it catches the bug in minutes instead of after a full expensive run underperforms.

## Connections
- [[Deep Dive - RLHF End to End]] — the instabilities catalogued here are what actually shows up running the full pipeline this note describes end to end.
- [[Concept - KL Control in RLHF]] — the shared lever behind gotchas 1, 2, and 7.
- [[Concept - PPO for Language Models]] — gotchas 2 and 3 are PPO-specific manifestations of its known implementation sensitivity.
- [[Concept - GRPO and RL with Verifiable Rewards]] — the value-model-free alternative where gotcha 2's entropy collapse is especially acute.
- [[Concept - Reward Hacking]] — the mechanism underlying gotcha 1 and, in milder form, gotcha 6.
- [[Concept - Length Bias in Preference Optimization]] — the dedicated deep-dive on gotcha 6's root cause.
- [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]] — the dedicated deep-dive on gotcha 2's root cause.
- [[Playbook - Debugging an RLHF Run]] — the step-by-step procedure for working through these symptoms in order on an actual run.
- [[Concept - Direct Preference Optimization (DPO)]] — gotcha 4 is DPO-specific and doesn't appear in PPO/GRPO runs.
- [[Concept - Training Stability and Loss Spikes]] — cross-domain: the pretraining-side analog of instability monitoring; the same instrumentation habits (log everything, distrust a single curve) transfer directly.
- [[Gotchas - Numerical Stability]] — cross-domain: gotcha 3's NaN/explosion failure mode is a specific instance of the general numerical-stability pitfalls catalogued there.

## Sources
- Ziegler et al. (2019) — Fine-Tuning Language Models from Human Preferences. The adaptive KL controller referenced in gotchas 1 and 7.
- Gao et al. (2023) — Scaling Laws for Reward Model Overoptimization. The (reward, KL) frontier behind gotcha 1.
- Yu et al. (2025) — DAPO: An Open-Source LLM Reinforcement Learning System at Scale. The clip-higher fix referenced in gotcha 2.
- Touvron et al. (2024) — The Llama 3 Herd of Models. RPO/DPO regularization detail referenced in gotcha 4.
- Bai et al. (2022) — Anthropic HH: Training a Helpful and Harmless Assistant. Iterated/online RLHF referenced in gotcha 5's fix.
