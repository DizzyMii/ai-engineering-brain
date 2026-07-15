---
tags: [concept, domain/post-training, level/advanced]
aliases: [GRPO, RLVR, Group Relative Policy Optimization, RL with Verifiable Rewards, verifiable rewards]
summary: "PPO without a value model: group-normalized rewards replace the critic, and programmatic verifiers replace the learned RM."
---

# Concept - GRPO and RL with Verifiable Rewards
> **One-paragraph hook:** GRPO drops the value network that makes [[Concept - PPO for Language Models]] expensive and unstable, replacing it with a dumb-simple statistic — the mean and standard deviation of rewards inside a sampled group — and pairs naturally with programmatic verifiers (RLVR) instead of a learned [[Concept - Reward Models|reward model]] for domains where you can just check the answer. It is the algorithm behind DeepSeek-R1's reasoning breakthrough and the default choice (as of 2026) whenever a task has a checkable ground truth: the mechanism that turns [[Concept - Chain-of-Thought and Why It Works|chain-of-thought]] from an inference-time prompting trick into a trained capability.

## The mechanism

For a prompt $q$, sample a group of $G$ completions $o_1, \ldots, o_G$ from the current policy $\pi_\theta$. Score each with a reward function $r_i$ — a learned RM, or in RLVR a verifier (exact-match on a math answer, a unit-test pass/fail, a regex on required format). Compute the group-relative advantage:

$$A_i = \frac{r_i - \text{mean}(r_1, \ldots, r_G)}{\text{std}(r_1, \ldots, r_G) + \epsilon}$$

and broadcast this single scalar to every token in completion $o_i$. There is no value network, no GAE, no separate critic forward pass — the group mean *is* the baseline. The update is PPO's clipped surrogate applied token-wise with the group-relative advantage in place of the GAE advantage:

$$J(\theta) = \mathbb{E}\left[\frac{1}{G}\sum_{i=1}^{G}\frac{1}{|o_i|}\sum_{t=1}^{|o_i|} \min\big(\rho_{i,t} A_i,\ \text{clip}(\rho_{i,t}, 1-\epsilon, 1+\epsilon)\, A_i\big)\right] - \beta\, D_{KL}[\pi_\theta \Vert \pi_{ref}]$$

where $\rho_{i,t} = \pi_\theta(o_{i,t} \mid q, o_{i,<t}) / \pi_{\theta_{old}}(o_{i,t} \mid q, o_{i,<t})$. The [[Concept - KL Control in RLHF]] term typically uses the k3 estimator ($\pi_{ref}/\pi_\theta - \log(\pi_{ref}/\pi_\theta) - 1$, unbiased and always $\ge 0$) at a small $\beta$ — some GRPO variants set it to zero once the base model is already RLHF-aligned and drift is less of a concern.

Removing the critic isn't free: PPO's value network gives *per-token* credit assignment (which specific token in a trace caused eventual success or failure), while GRPO's group-relative advantage gives the *same* scalar to every token in a completion. GRPO is closer to REINFORCE with a clever Monte-Carlo control variate than to true actor-critic RL — the baseline it uses is a group statistic estimated from samples, not a learned value function.

**RLVR** (RL with Verifiable Rewards) is the reward-design half of the picture: instead of a Bradley-Terry reward model fit on human comparisons, use a programmatic checker. Correctness for a math problem is exact-match on the final boxed answer; correctness for code is unit tests passing; format compliance is a regex on required tags (e.g., `<think>...</think>`). This sidesteps [[Concept - Reward Hacking]] against a *learned* proxy — there's no RM to overfit — but format- and verifier-gaming remain (see Failure modes), and it does not by itself guarantee the reward is actually teaching new reasoning rather than just amplifying what the base model already has (see [[Concept - Spurious Rewards and RLVR Failure Modes]]).

## In practice

GRPO was introduced by Shao et al. 2024 (DeepSeekMath) to make RL affordable for math reasoning: dropping the value model roughly halves the resident-model memory of the full [[Deep Dive - RLHF End to End|RLHF pipeline]] (policy + reference + reward vs. policy + reference + reward + critic). Group size $G$ is typically 8–64 — small enough to bound generation cost per prompt, large enough that the group mean/std aren't dominated by sampling noise, the same small-sample estimation concern [[Concept - Statistical Rigor in Model Evaluation|pass@k evaluation]] runs into. Compute remains generation-bound: $G$ rollouts per prompt dominate wall-clock, the same bottleneck full RLHF has.

DeepSeek-R1-Zero (DeepSeek-AI, 2025) is the demonstration case: pure GRPO on a base model with only an accuracy reward and a format reward produced emergent [[Concept - Reasoning Training and Long Chain-of-Thought|long chain-of-thought reasoning]] and self-verification behavior with zero SFT warm-start — see [[Breakdown - DeepSeek-R1]]. Reward design in practice combines an accuracy term with a lighter format term; over-weighting the format reward invites the model to satisfy the regex without doing the reasoning, so length and repetition penalties get added as guardrails on top.

## Failure modes

Zero-variance groups are the sharpest edge case: if every sample in a group is correct (or every sample is wrong), $\text{std} = 0$ and every advantage in the group collapses to zero — no gradient, wasted generation. This motivates dynamic sampling / difficulty filtering, formalized by DAPO (Yu et al. 2025), which resamples prompts until a group has a non-trivial pass rate rather than wasting rollouts on degenerate groups.

Dividing by the group standard deviation also introduces a bias most practitioners miss: it *up-weights* low-variance (near-all-easy or near-all-hard) groups relative to their true reward spread, and separately biases toward longer completions when reward correlates with length. Dr.GRPO (Liu et al. 2025) removes both the std-normalization and a hidden length-normalization term in the original loss and shows the corrected objective trains more stably at equal compute.

RLVR narrows the reward-hacking surface but does not close it — see [[Concept - Spurious Rewards and RLVR Failure Modes]] for the sharpest version of this: on some base models (notably `Qwen2.5-Math`), even a *random* or *provably wrong* reward produces large accuracy gains, because GRPO's clipped update sharpens whatever latent behavior the base model already leans toward, reward-correlated or not.

Entropy collapse over long RL runs is the other headline failure — see [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]] and [[Gotchas - RLHF Training Instabilities]]. The clipped surrogate keeps reinforcing whatever already has probability mass, sampling entropy falls monotonically, and the model narrows onto a small set of stereotyped solution templates, losing the exploration needed to solve harder problems later in training; DAPO's "clip-higher" (an asymmetric clip that permits larger upward probability moves on low-probability tokens) is a direct countermeasure.

## The non-obvious

GRPO's group-relative advantage trades a real bias-variance problem for implementation simplicity: because the same normalized advantage is broadcast to every token in a completion, GRPO cannot tell you *which step* in a long chain-of-thought was the one that mattered — a correct final answer reached via a lucky guess after three wrong turns gets exactly the same per-token credit as a clean derivation. This is fine when correctness dominates and traces are short-ish, and it degrades as chains lengthen and reasoning *quality*, not just the final answer, starts to matter — which is exactly the direction reasoning-model training has pushed since R1, and exactly why [[Concept - Process and Outcome Reward Models|dense, step-level reward]] keeps resurfacing as the "real" fix that RLVR's simplicity was deferring.

## Connections
- [[Snippet - GRPO Advantage Computation]] — the runnable implementation of the group-relative advantage and clipped, k3-KL-penalized loss derived above.
- [[Deep Dive - RLHF End to End]] — GRPO is the value-model-free descendant of the PPO stage in the canonical RLHF pipeline.
- [[Concept - PPO for Language Models]] — GRPO reuses PPO's clipped surrogate; the only structural change is where the advantage comes from.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — GRPO/RLVR is the training algorithm that produces long-CoT reasoning models in practice.
- [[Breakdown - DeepSeek-R1]] — the flagship system that proved GRPO+RLVR alone (R1-Zero) elicits emergent reasoning with no SFT warm-start.
- [[Concept - Reward Hacking]] — RLVR narrows but does not eliminate reward hacking; verifiers get gamed too.
- [[Concept - Spurious Rewards and RLVR Failure Modes]] — the deeper catalog of ways verifiable rewards still mislead, including reward-free gains.
- [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]] — the dominant training-time pathology of long GRPO runs.
- [[Concept - KL Control in RLHF]] — the KL coefficient in the GRPO objective is the same dial as in PPO, often just set closer to zero.
- [[Concept - Chain-of-Thought and Why It Works]] — cross-domain: GRPO/RLVR is the mechanism that turns CoT from a prompting trick into a trained capability.
- [[Concept - Statistical Rigor in Model Evaluation]] — cross-domain: group-size and pass-rate statistics in GRPO face the same small-sample estimation problem pass@k evaluation does.
- [[Gotchas - RLHF Training Instabilities]] — the operational symptom catalog for the failure modes described here, from the debugging side.

## Sources
- Shao et al. (2024) — DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models. Introduces GRPO and the group-relative advantage.
- DeepSeek-AI (2025) — DeepSeek-R1. Applies GRPO/RLVR at scale to produce R1-Zero's emergent long-CoT reasoning.
- Liu et al. (2025) — Understanding R1-Zero-Like Training (Dr.GRPO). Identifies and fixes length and std-normalization bias in the original GRPO loss.
- Yu et al. (2025) — DAPO: An Open-Source LLM Reinforcement Learning System at Scale. Clip-higher and dynamic sampling to fight entropy collapse and zero-gradient groups.
