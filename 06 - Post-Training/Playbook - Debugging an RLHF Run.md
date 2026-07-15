---
tags: [playbook, domain/post-training, level/advanced]
aliases: [debugging RLHF, RLHF troubleshooting, diagnosing a broken RL fine-tune]
summary: "Ordered procedure and symptom-to-fix branch table for diagnosing a misbehaving RLHF/PPO/GRPO run from launch to convergence."
---

> **Goal:** get a stalled, diverging, or silently-degrading RLHF/GRPO run back to healthy — reward improving, KL bounded, capabilities intact.
> **When to run this:** the moment any of {reward curve, KL curve, eval win-rate, output samples} looks wrong, or before you trust a "reward went up" claim.
> **Prerequisites:** a working [[Deep Dive - RLHF End to End]] or [[Concept - GRPO and RL with Verifiable Rewards]] pipeline already launched, with logging infrastructure ([[Concept - LLM Observability and Tracing]]) wired to at least reward, KL, entropy, and length per step.

RLHF and its on-policy successors fail quietly. A crashed training job is easy — the process dies and you get a stack trace. A *hacked* run does the opposite: the loss curves look great, the reward climbs, and the model is worse. This playbook is the ordered check sequence that catches both, plus a branch table for when you already have a symptom in hand.

## Steps

1. **Pre-launch sanity check on the reward signal itself.** Before spending GPU-hours, run the reward model or verifier over a small fixed set of hand-labeled good and bad completions. *Expected:* good completions score reliably higher than bad ones, with a believable spread (not all scores within noise of each other). *Deviation:* if the RM can't separate obviously-good from obviously-bad text, or a rule-based verifier passes broken code, stop — you're about to optimize against garbage and every downstream symptom will be a red herring.

2. **Verify KL starts at zero.** At step 0, the policy and the frozen reference are the same checkpoint, so [[Concept - KL Control in RLHF]] measured between them must read ~0 (use the k3 estimator — it's unbiased and non-negative, unlike naive k1). *Expected:* KL ≈ 0 ± noise floor. *Deviation:* nonzero KL at step 0 means policy and reference are already different weights, different tokenizers, or different [[Concept - Chat Templates and Special Tokens]] rendering — fix this before anything else, because every KL number downstream is now meaningless.

3. **Confirm generation config parity.** Check that the chat template, special tokens, `add_generation_prompt`, max length, and stop tokens used by the rollout sampler exactly match what training and the reference model expect. *Expected:* decoding a rollout prompt by hand reproduces byte-for-byte what SFT training saw. *Deviation:* any drift here (a stray double-BOS, a missing generation-prompt header) silently poisons every rollout — see [[Gotchas - Chat Template Bugs]].

4. **Instrument the full metric set before trusting anything.** Log, every N steps: reward mean/std, KL (k3), policy entropy, mean response length, value loss (PPO only), gradient norm, fraction of PPO-clipped tokens, and win-rate against the frozen SFT model on a held-out eval set judged by humans or a strong LLM judge. Reward alone is not a health signal — it's exactly the metric [[Concept - Reward Hacking]] teaches you to distrust in isolation.

5. **Run the ordered diagnostic pass** (Step 1–5 below) any time a curve looks off, in this priority order — later checks assume earlier ones passed:
   - **KL check:** is KL climbing monotonically past your target band while reward keeps rising? → overoptimization (Gao et al. 2023's reward-vs-KL curve: true quality peaks then falls as KL grows). Tighten β / lower target KL, or stop training at the KL band where held-out eval still tracks proxy reward.
   - **Entropy check:** is policy entropy collapsing toward 0? → the model is going near-deterministic and losing exploration ([[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]]). Lower the learning rate, raise the KL anchor, or apply DAPO's clip-higher.
   - **Reward-distribution check:** are rewards flattening to nearly-equal values across a batch? → the RM (or verifier) has gone out-of-distribution as the policy has moved, or a GRPO group is all-correct/all-wrong (zero-variance advantage). Refresh the RM on-policy, or add dynamic sampling to drop degenerate groups.
   - **Length check:** is mean response length growing while win-rate is flat? → classic length hacking. Add an explicit length penalty or switch to a length-normalized objective (SimPO-style).
   - **Coherence check:** is output gibberish or repetitive? → check tokenizer/template parity again (step 3), verify the reference model loaded correctly, and check for an LR that's too high relative to batch size.

## Verification

The run is healthy when, together: held-out win-rate (human or LLM-judge) against the SFT baseline is up and holding, KL sits inside the intended target band rather than climbing unboundedly, policy entropy has stabilized rather than collapsed, and general-capability evals (MMLU-style, or whatever regression suite you have) have not dropped — this last check is the alignment-tax guard from [[Concept - The Post-Training Pipeline]]. A reward curve going up with none of the other checks passing is not verification, it's the setup for a reward-hacking postmortem.

## When it goes wrong

| Symptom | Likely cause | Jump to fix |
|---|---|---|
| Reward rises, outputs get worse/repetitive | Reward hacking as KL drifts off-distribution | Raise β, refresh RM on-policy, gate stopping criterion on human/LLM eval, not proxy reward |
| Output collapses to gibberish or one repeated phrase | Entropy collapse (KL too low or LR too high) | Raise β, lower LR, add entropy bonus or clip-higher (DAPO) |
| DPO: both chosen and rejected logprobs fall while margin grows | The DPO loss only constrains the *difference*, not absolute likelihood | Add an NLL/SFT regularizer on the chosen response (Llama-3's RPO), lower β |
| PPO value loss explodes | Miscalibrated returns/advantages | Value clipping, value-head warmup, reward normalization |
| All rewards converge to nearly equal | RM saturated/OOD, or GRPO group has zero variance | Refresh RM on fresh on-policy comparisons; add dynamic sampling to drop degenerate groups |
| Response length grows unboundedly, win-rate flat | Length bias in the reward signal | Explicit length penalty, or move to SimPO-style length-normalized reward |
| KL values are nonsensical (negative, huge, or NaN) | Reference/policy tokenizer or chat-template mismatch | Enforce identical preprocessing across generation, reference, and training paths |
| Model never stops generating, runs to max_new_tokens | EOS/eot missing or masked out during SFT stage that produced the checkpoint | Verify EOS is unmasked in the upstream SFT loss (see [[Concept - Loss Masking and Sequence Packing]]) |

## Connections

- [[Gotchas - RLHF Training Instabilities]] — the aggregated symptom catalog this playbook's branch table is drawn from; read it for deeper mechanism on each failure.
- [[Concept - KL Control in RLHF]] — KL is the single most load-bearing diagnostic in every step of this procedure.
- [[Concept - PPO for Language Models]] — the value-loss and clipping internals referenced in the PPO-specific branch rows.
- [[Concept - Reward Hacking]] — the general mechanism (Goodhart's law on a learned or verifiable proxy) that steps 5 and the branch table are built to detect.
- [[Concept - LLM Observability and Tracing]] — the cross-domain (16) infrastructure this playbook assumes is already wired up for step 4's logging.
- [[Concept - GRPO and RL with Verifiable Rewards]] — the group-relative-advantage variant of this loop, where "value loss explodes" doesn't apply but "zero-variance group" does.
- [[Concept - Statistical Rigor in Model Evaluation]] — cross-domain (13) grounding for why a single win-rate number in the verification step needs a confidence interval, not a point estimate.

## Sources

- Gao, Schulman, Hilton (2023) — Scaling Laws for Reward Model Overoptimization. The reward-vs-KL curve this playbook's KL check is built around.
- Ziegler et al. (2019) — Fine-Tuning Language Models from Human Preferences. Source of the adaptive KL controller referenced in step 5.
- Yu et al. (2025) — DAPO: An Open-Source LLM Reinforcement Learning System at Scale. Source of clip-higher and dynamic sampling as entropy-collapse and zero-variance-group fixes.
