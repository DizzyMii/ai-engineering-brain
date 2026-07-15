---
tags: [gotchas, domain/post-training, level/advanced]
aliases: [RLHF instability, PPO instability, RL fine-tuning gotchas, reward collapse]
summary: "RLHF/DPO/GRPO failure modes ordered by pain: reward hacking, entropy collapse, value divergence, DPO degeneracy, length explosion, silent setup bugs."
---

# Gotchas - RLHF Training Instabilities

## 1. Reward climbs while output quality visibly craters

**Symptom:** the scalar reward curve trends up steadily for hundreds of steps, but generations read as increasingly repetitive, sycophantic, or stuffed with headers and bullet points — a held-out human or [[Concept - LLM-as-Judge|LLM-judge]] win-rate against the SFT baseline stalls or falls even as the training-time reward keeps climbing.
**Cause:** [[Concept - Reward Hacking]]. As the policy's [[Concept - KL Control in RLHF|KL divergence]] from the reference model grows, it drifts into regions of output space the reward model was never trained on and is therefore miscalibrated in — Gao et al. (2023)'s overoptimization scaling law shows true reward rises then falls with KL while the RM's proxy reward keeps climbing, with the gold-vs-proxy gap widening roughly with the square root of KL for Bradley-Terry RMs.
**Fix:** raise the KL coefficient $\beta$ (or lower an adaptive controller's target KL), refresh/retrain the RM on fresh on-policy comparisons rather than trusting a static one, and gate checkpoint selection on held-out eval win-rate rather than the training reward curve.
**Detection:** plot reward against KL, not against step — the (reward, KL) frontier is the diagnostic; a reward that keeps rising well past the point where an independent eval plateaus or falls is the signature. Length and markdown-formatting metrics are useful leading indicators (see gotcha 6).

## 2. Generation collapses into gibberish or one repeated phrase

**Symptom:** sampling entropy falls toward zero over the course of training and outputs degrade into a repeated token, a short repeated phrase, or outright incoherent text — sometimes within just a few hundred steps. This is the same output-narrowing pathology tracked as [[Concept - Mode Collapse in RLHF|mode collapse]].
**Cause:** entropy collapse: the KL leash is too loose (β too low) or the learning rate too high, so each policy update sharpens the output distribution faster than exploration can counteract it. The clipped surrogate in [[Concept - PPO for Language Models]] or [[Concept - GRPO and RL with Verifiable Rewards]] keeps reinforcing whatever already has probability mass, and mass on alternatives never recovers — see [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]].
**Fix:** raise β, lower the learning rate, add an explicit entropy bonus, or use an asymmetric clip that permits larger upward moves on low-probability tokens (DAPO's "clip-higher"). Once collapse has fully set in, it is usually not recoverable within the run — restart from an earlier checkpoint rather than trying to fix it forward.
**Detection:** log policy entropy every step, not just every eval; a monotonically falling entropy curve is the earliest and cleanest warning, well before the human-readable outputs look obviously broken.

## 3. PPO's value loss explodes or NaNs

**Symptom:** value loss grows by orders of magnitude over a handful of steps, gradient norms spike, and the run either NaNs outright or policy quality collapses immediately after.
**Cause:** miscalibrated returns or advantages feeding the value head — usually because reward wasn't normalized, GAE advantages weren't whitened, or the value function was never warmed up before joint policy/value updates began, so the critic chases a moving, unstable target from step one.
**Fix:** normalize and clip rewards before computing returns, whiten advantages to mean 0 / variance 1 each batch, clip the value loss the same way the policy surrogate is clipped, and run a short value-only warmup phase before the policy update engages.
**Detection:** log value loss and advantage magnitude as first-class training curves alongside reward and KL; a value loss trending upward for more than a handful of steps in a row, well before any NaN appears, is the actionable early signal.

## 4. DPO: chosen and rejected logprobs both fall while the margin keeps growing

**Symptom:** the [[Concept - Direct Preference Optimization (DPO)]] loss decreases steadily and the implicit reward margin (chosen minus rejected) widens as expected, but logging the *absolute* log-probabilities of both chosen and rejected responses shows both trending down — and downstream generations degrade in fluency even though the loss curve looks perfectly healthy.
**Cause:** the DPO loss only constrains the *difference* between chosen and rejected implicit rewards, not their absolute scale — it is entirely possible, and empirically common, for the optimizer to satisfy the loss by pushing both probabilities down together rather than by raising the chosen one.
**Fix:** add an NLL/SFT regularization term on the chosen response to anchor its absolute likelihood (Llama 3's RPO approach), and lower β so the margin needed to satisfy the loss is smaller.
**Detection:** this is invisible from the DPO loss curve alone — separately log `policy_chosen_logps` and `policy_rejected_logps` (not just their difference), per [[Snippet - DPO Loss Implementation]]; treat this as a mandatory pair of training curves, not optional instrumentation.

## 5. Reward-model scores converge to near-identical values across a batch

**Symptom:** RM score variance across a rollout batch shrinks steadily until nearly every sampled completion for a given prompt gets almost the same reward, regardless of visible quality differences between them — the policy update has effectively nothing left to learn from.
**Cause:** the reward model has saturated or gone out-of-distribution: as the policy improves and its outputs concentrate in a narrower region, a static RM — trained once on an earlier, more diverse distribution — loses the resolution to discriminate between them, the same distribution-shift root cause as gotcha 1 but manifesting as flatness instead of exploitation.
**Fix:** periodically refresh the RM with freshly-labeled on-policy comparisons (iterated/online RLHF, as in Anthropic's HH pipeline), or switch late-training to an RM ensemble whose disagreement signals when scores are becoming unreliable.
**Detection:** track RM-score variance within each rollout batch over time; a steady decline toward zero variance — independent of whether mean reward is still rising — is the tell.

## 6. Response length grows without bound across training

**Symptom:** mean completion length increases steadily step over step, often well past what the task requires, while human/judge win-rate stays flat or even declines relative to length-matched baselines.
**Cause:** [[Concept - Length Bias in Preference Optimization]] — human labelers, RMs, and LLM judges all show a documented, well-replicated tendency to rate longer answers as better independent of content, so any reward-driven optimization finds length a cheap, always-available lever.
**Fix:** add an explicit length penalty to the reward, switch to a length-normalized objective (SimPO-style), or balance preference-pair length distributions during data curation so chosen and rejected responses aren't systematically different lengths (see [[Checklist - Preference Data Quality]]).
**Detection:** plot mean response length against training step as a first-class curve; a steady upward trend with no corresponding win-rate gain is unambiguous.

## 7. KL reads as nonsensical from the very first logged step

**Symptom:** the KL-to-reference value is negative, wildly large, or simply implausible (nowhere near ~0) at step 0, when the policy and reference model are supposed to be numerically identical.
**Cause:** a mismatch between the generation, reference, and training preprocessing paths — different tokenizer instances, a chat-template version drift between the sampler and the trainer, or a reference model loaded with different special-token handling than the policy — so the two log-probability streams being compared aren't actually scoring the same token sequence.
**Fix:** enforce a single shared tokenizer and [[Concept - Loss Masking and Sequence Packing|chat-template]] configuration object across the generation, reference-scoring, and training code paths, and add a startup assertion that KL is within a small epsilon of zero when policy weights equal reference weights.
**Detection:** check KL at step 0 before trusting anything else about the run; it should be ~0 given policy == reference, and any deviation there is a setup bug, not a training dynamic, and will invalidate every later signal if left unfixed.

## 8. Preprocessing bugs silently carried over from SFT into RL

**Symptom:** training proceeds without any loud errors, but the model behaves subtly worse than expected from the earliest steps — e.g. it never emits an end token cleanly, or its outputs read as though the first token were duplicated or shifted.
**Cause:** two common carryover bugs — the SFT loss mask (or its underlying tokenization convention) gets reused in the RL data pipeline without re-verification, or the RL sampler independently prepends a BOS token that the chat template already emits, producing a double-BOS distribution shift the model never saw during SFT.
**Fix:** re-run the same decode-and-inspect sanity check used to validate SFT data (see [[Snippet - Loss Masking a Chat Dataset]]) against the exact prompts fed to the RL sampler, and diff the tokenized output against what the reference model's tokenizer path produces for the same input.
**Detection:** decode a handful of actual training batches from the RL pipeline — not the SFT pipeline — token-by-token and visually confirm there is no duplicated BOS and that special tokens match the reference/policy's expected format exactly; this is cheap and catches the bug in minutes instead of after a full expensive run underperforms.

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
