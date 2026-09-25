---
tags: [concept, domain/post-training, level/core]
aliases: [RFT, RAFT, rejection sampling fine-tuning, expert iteration]
summary: "Sample N candidates, keep the best by reward or verifier, SFT on the winners, and repeat — RL-flavored post-training without RL."
---

# Concept - Rejection Sampling and Expert Iteration
> **One-paragraph hook:** Before reaching for PPO or GRPO, the cheapest way to turn a reward signal into weight updates is to sample many completions, keep the good ones, and fine-tune on them. No value function, no policy gradient, no on-the-fly RL infrastructure: it's [[Concept - Supervised Fine-Tuning (SFT)]] run in a loop. Unglamorous, and it's what Llama 3 used for most of its post-training rounds.

## The mechanism

Rejection sampling fine-tuning (RFT / RAFT, Dong et al. 2023) works like this. For each prompt $x$ in a batch, sample $k$ completions $\{y_1, \dots, y_k\}$ from the current policy. Score each with a [[Concept - Reward Models]] or a programmatic verifier. Keep the top-1, or every completion above a reward threshold. Then run standard SFT cross-entropy with the filtered (prompt, winning-completion) pairs as demonstrations. Repeat the cycle with the newly fine-tuned model as the sampler.

Formally it's a hard-max approximation to policy improvement: reward-weighted regression with a one-hot weight, where the argmax sample gets weight 1 and everything else gets 0. [[Concept - PPO for Language Models]] instead does soft, gradient-based credit assignment through an advantage estimate. Call it the "poor man's RLHF". The update step is just supervised learning, so it's stable. Sampling $k$ completions per prompt needs no synchronization across workers, so it's embarrassingly parallel. And with no value function, there's no value-function divergence of the kind that plagues PPO.

STaR (Zelikman et al. 2022, "Self-Taught Reasoner") is the reasoning-specific ancestor. It samples chain-of-thought rationales and keeps the ones that reach the correct final answer. Its distinctive move is for prompts where every sample fails: hand the model the correct answer, ask it to work backward to a plausible "rationalization", then SFT on both the genuine and rationalized traces. STaR in turn descends from expert iteration (Anthony, Tian, and Barber 2017, originally for AlphaZero-style self-play). A policy generates data, an "expert" (search, a verifier, or a reward-filtered subset) improves on it, the policy is retrained toward the expert's output, and the loop repeats indefinitely.

## In practice

Llama 2 (Touvron et al. 2023) ran rejection sampling ahead of PPO. Llama 3 (2024) dropped PPO entirely: post-training was roughly six rounds of rejection sampling combined with [[Concept - Direct Preference Optimization (DPO)]]. Each round's rejection-sampled winners became that round's SFT data, and the resulting model went through DPO on preference pairs before the next round's sampling began.

Best-of-N with a verifier at inference time is a test-time-compute technique on its own, governed by [[Concept - Sampling and Decoding Parameters]]. RFT distills that best-of-N behavior back into the weights, so you pay the sampling cost once in training instead of on every inference request.

Knobs: $k$ is typically 8–128 samples per prompt. Sampling temperature goes above deployment temperature to get diversity across the $k$ draws. Near-duplicates are deduped before filtering, and the reward/verifier threshold sets how selective the kept set is. Higher $k$ raises the ceiling of what the filtered set can contain, with diminishing returns (the marginal chance of drawing a much-better sample shrinks) and growing reward-hacking risk: a large enough $k$ will eventually surface whatever hole the reward function has (see [[Concept - Reward Hacking]]).

## Failure modes

- **Collapse onto easy prompts.** Prompts the model already solves most of the time give strong, clean SFT signal every round. Prompts near the capability frontier give noisy or no signal. So the training mix drifts toward what the model can already do and away from its weaknesses.
- **Amplification of reward/verifier bias.** The "keep" step is a hard filter on reward, so whatever the reward over-rates (commonly length) gets over-represented in the SFT set. The SFT step then entrenches it further. The bias compounds instead of merely being inherited.
- **Nothing to learn on hard prompts.** If pass@k is ~0 for a prompt, none of the $k$ samples solve it. That's common on hard math or code problems in [[Concept - Reasoning Training and Long Chain-of-Thought]] settings. There's no winner to keep, and the prompt silently drops out of training. The method can't bootstrap a capability it can't already occasionally produce. STaR's rationalization trick papers over this gap, but only for reasoning.

## The non-obvious

Rejection sampling only trains on samples the current policy already generates. Its ceiling is the model's pass@k at generation time, not anything the reward model knows. That's the mirror image of reward hacking a learned critic: the model doesn't exploit the reward's blind spots, it just never sees the good behavior it would need to imitate. The result is a characteristic curve, with fast early gains from the easy pass@k improvements and then a hard flattening. At that point teams either raise $k$ (expensive, diminishing returns) or switch to an on-policy method like [[Concept - GRPO and RL with Verifiable Rewards]], which can shape behavior through gradient credit assignment on partial correctness and doesn't need a complete success to learn from.

## Connections

- [[Concept - Supervised Fine-Tuning (SFT)]] — the actual training step every rejection-sampling round performs; RFT is a data-generation loop wrapped around ordinary SFT.
- [[Concept - Reward Models]] — the scoring function that filters which of the $k$ samples get kept, and the source of the bias-amplification failure mode.
- [[Concept - Direct Preference Optimization (DPO)]] — Llama 3 alternates rejection-sampling rounds with DPO rounds instead of using PPO; they are complementary stages in the same pipeline.
- [[Breakdown - Tulu 3]] — a fully open, documented recipe that, like Llama 3, uses rejection-sampling-style data generation ahead of preference optimization and RLVR.
- [[Concept - Sampling and Decoding Parameters]] — controls $k$, temperature, and diversity of the candidate pool that rejection sampling filters.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — STaR-style rejection sampling on chain-of-thought traces is a primary route to bootstrapped reasoning capability.
- [[Concept - GRPO and RL with Verifiable Rewards]] — the on-policy, gradient-based alternative that scales better than rejection sampling once pass@k is near zero.
- [[Concept - Chain-of-Thought and Why It Works]] — STaR's rationalization mechanism depends on chain-of-thought traces being the object filtered and imitated.
- [[Concept - PPO for Language Models]] — the soft, gradient-based credit-assignment alternative to RFT's hard-max, one-hot weighting.
- [[Concept - Reward Hacking]] — a large enough $k$ will eventually surface whatever hole exists in the reward or verifier, the same overoptimization risk RL methods face.

## Sources

- Dong et al. (2023) — RAFT: Reward rAnked FineTuning for Generative Foundation Model Alignment. The RFT/RAFT formulation.
- Zelikman et al. (2022) — STaR: Bootstrapping Reasoning With Reasoning. The rationalization-augmented rejection sampling loop for chain-of-thought.
- Anthony, Tian, and Barber (2017) — Thinking Fast and Slow with Deep Learning and Tree Search. Expert iteration, the general ancestor pattern.
