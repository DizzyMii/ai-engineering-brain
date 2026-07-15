---
tags: [concept, domain/post-training, level/core]
aliases: [RFT, RAFT, rejection sampling fine-tuning, expert iteration]
summary: "Sample N candidates, keep the best by reward or verifier, SFT on the winners, and repeat — RL-flavored post-training without RL."
---

# Concept - Rejection Sampling and Expert Iteration
> **One-paragraph hook:** Before reaching for PPO or GRPO, the cheapest way to turn a reward signal into weight updates is to sample many completions, keep the good ones, and fine-tune on them — no value function, no policy gradient, no on-the-fly RL infrastructure, just [[Concept - Supervised Fine-Tuning (SFT)]] run in a loop. It's unglamorous, and it's exactly what Llama 3 used for most of its post-training rounds.

## The mechanism

Rejection sampling fine-tuning (RFT / RAFT, Dong et al. 2023): for each prompt $x$ in a batch, sample $k$ completions $\{y_1, \dots, y_k\}$ from the current policy, score each with a [[Concept - Reward Models]] or a programmatic verifier, keep the top-1 (or every completion above a reward threshold), then run standard SFT cross-entropy using the filtered (prompt, winning-completion) pairs as demonstrations. Repeat the whole cycle with the newly fine-tuned model as the new sampler.

This is a hard-max approximation to policy improvement: formally it's reward-weighted regression with a one-hot weight — the argmax sample gets weight 1, everything else gets weight 0 — rather than the soft, gradient-based credit assignment [[Concept - PPO for Language Models]] performs via an advantage estimate. It's the "poor man's RLHF": stable because the update step is just supervised learning, embarrassingly parallel because sampling $k$ completions per prompt needs no synchronization across workers, and immune to the value-function divergence that plagues PPO, because there is no value function.

STaR (Zelikman et al. 2022, "Self-Taught Reasoner") is the reasoning-specific ancestor: sample chain-of-thought rationales, keep the ones reaching the correct final answer, and — the distinctive move — for prompts where every sample fails, generate a "rationalization" by handing the model the correct answer and asking it to work backward to a plausible rationale, then SFT on both the genuine and rationalized traces. STaR itself descends from expert iteration (Anthony, Tian, and Barber 2017, originally used for AlphaZero-style self-play): a policy generates data, an "expert" — search, a verifier, or a reward-filtered subset — improves on that data, and the policy is retrained toward the expert's output, repeated indefinitely.

## In practice

Llama 2 (Touvron et al. 2023) ran rejection sampling ahead of PPO in its post-training stack. Llama 3 (2024) went further: post-training ran roughly six rounds of rejection sampling combined with [[Concept - Direct Preference Optimization (DPO)]] and no PPO at all — each round's rejection-sampled winners became that round's SFT data, and the resulting model then went through DPO on preference pairs before the next round's sampling began.

Best-of-N with a verifier at inference time is a test-time-compute technique in its own right, governed by [[Concept - Sampling and Decoding Parameters]]; RFT is precisely the move of distilling that best-of-N behavior back into the model's weights, so the sampling cost is paid once during training instead of on every inference request.

Knobs: $k$ typically 8–128 samples per prompt; sampling temperature is set higher than deployment temperature to get diversity across the $k$ draws; near-duplicate samples are deduped before filtering; the reward/verifier threshold controls how selective the kept set is. Higher $k$ raises the ceiling of what the filtered set can contain but with diminishing returns — the marginal probability of drawing a much-better sample shrinks — and rising reward-hacking risk, since a large enough $k$ will eventually surface whatever hole exists in the reward function (see [[Concept - Reward Hacking]]).

## Failure modes

- **Collapse onto easy prompts.** Prompts the model already solves most of the time contribute strong, clean SFT signal every round; prompts near the model's capability frontier contribute noisy or absent signal, so training-data composition drifts toward what the model can already do rather than toward its weaknesses.
- **Amplification of reward/verifier bias.** Because the "keep" step is a hard filter on the reward, whatever the reward over-rates — commonly length — gets over-represented in the resulting SFT set, and the SFT step then further entrenches it: compounding, not merely inheriting, the reward model's bias.
- **Nothing to learn on hard prompts.** If pass@k is ~0 for a prompt (none of the $k$ samples solve it — common on genuinely hard math or code problems in [[Concept - Reasoning Training and Long Chain-of-Thought]] settings), there is no winning sample to keep, and that prompt silently drops out of training entirely. The method cannot bootstrap a capability it cannot already occasionally produce, unlike STaR's rationalization trick, which papers over exactly this gap for reasoning specifically.

## The non-obvious

Because rejection sampling only ever trains on samples the current policy already generates, its ceiling is set by the model's pass@k at generation time, not by anything the reward model knows. This is the mirror image of reward hacking a learned critic: instead of exploiting the reward's blind spots, the model simply never encounters the good behavior to imitate. In practice this produces a characteristic curve — fast early gains from the low-hanging pass@k improvements, then a hard flattening — at which point teams either raise $k$ (expensive, diminishing returns) or switch to an on-policy method like [[Concept - GRPO and RL with Verifiable Rewards]] that can shape behavior via gradient credit assignment on partial correctness, rather than requiring a complete success to learn from at all.

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
