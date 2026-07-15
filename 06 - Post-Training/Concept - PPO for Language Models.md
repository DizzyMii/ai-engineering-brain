---
tags: [concept, domain/post-training, level/advanced]
aliases: [PPO, Proximal Policy Optimization]
summary: "How PPO's clipped surrogate, GAE, and a value head map onto autoregressive generation, and why its implementation details are load-bearing."
---

> **One-paragraph hook:** PPO is the reinforcement-learning algorithm at the core of the third stage of [[Deep Dive - RLHF End to End]], adapted from a general-purpose robotics/games algorithm to the peculiar structure of autoregressive text generation: a token-level MDP with a reward that is mostly zero until the very last step. It works, but it is notoriously finicky at LLM scale — not because the math is wrong, but because a long list of unglamorous implementation details (advantage whitening, reward clipping, value-loss clipping) turn out to be the difference between a converging run and a policy that collapses into gibberish in a few hundred steps.

## The mechanism

Cast generation as a Markov Decision Process: the state at step $t$ is the prompt plus every token generated so far, the action is the next token, and the policy $\pi_\theta$ is just the language model's next-token distribution. The reward is (near) zero for every non-terminal token except a per-token [[Concept - KL Control in RLHF|KL penalty]] against a frozen reference, plus the reward model's scalar score added once at the terminal (EOS) token — the reward is deferred and sparse by construction, which is unusual for RL and is exactly what makes credit assignment across a several-hundred-token sequence hard. Discount $\gamma \approx 1$ (there's no reason to discount within one response) and GAE $\lambda \approx 0.95$.

PPO's central trick is the clipped surrogate objective, which bounds how far a single gradient step can move the policy relative to the policy that generated the rollout:

$$L^{CLIP}(\theta) = \mathbb{E}_t\Big[\min\big(\rho_t A_t,\ \text{clip}(\rho_t,\, 1-\epsilon,\, 1+\epsilon)\, A_t\big)\Big]$$

where $\rho_t = \pi_\theta(a_t|s_t) / \pi_{\theta_{old}}(a_t|s_t)$ is the probability ratio between the updated and the rollout-time policy, $A_t$ is the advantage estimate, and $\epsilon \approx 0.2$. The clip caps the reward for exploiting a large positive-advantage ratio and caps the penalty for a large negative-advantage ratio, which in practice prevents any single minibatch update from moving the policy far enough to invalidate the rollouts it was computed from — the "proximal" in Proximal Policy Optimization.

Advantages come from a separate value head $V_\phi(s_t)$ (usually sharing the transformer backbone with the policy, with a separate output head) via Generalized Advantage Estimation:

$$A_t = \sum_{l=0}^{T-t} (\gamma\lambda)^l \, \delta_{t+l}, \qquad \delta_t = r_t + \gamma V_\phi(s_{t+1}) - V_\phi(s_t)$$

The value head is trained with its own (also clipped) regression loss toward the return, and in practice needs a warmup period before its predictions are reliable enough for GAE to produce a useful signal — training the policy against a poorly-initialized value function is a common source of early-run instability.

## In practice

None of the equations above are sufficient on their own to make PPO train stably at billion-parameter scale; a set of "implementation details" that don't appear in the original paper turn out to dominate outcomes. Advantage whitening (normalize $A_t$ to mean 0, variance 1 within each minibatch) and reward normalization/clipping are standard, not optional — Engstrom et al. (2020) and Huang's "The 37 Implementation Details of Proximal Policy Optimization" both show that ablating these tricks degrades PPO as much as or more than changing the core algorithm. Typical runs take 1–4 PPO epochs over each rollout batch, split into minibatches, with either a fixed or [[Concept - KL Control in RLHF|adaptively-scheduled]] KL coefficient and large rollout batches (thousands of prompts) because the reward and advantage estimates from a small batch are too noisy to give a stable gradient. Because generation is autoregressive and dominates wall-clock time, the [[Concept - Sampling and Decoding Parameters]] used for rollout sampling (temperature, top-p) directly shape the exploration/exploitation tradeoff the whole loop depends on. The optimizer is [[Concept - Adam and AdamW]], typically at a substantially lower learning rate than SFT, since PPO updates are meant to be small, incremental policy shifts rather than large corrections.

## Failure modes

Value-model divergence — the value loss spikes or grows unbounded — is usually the first thing to break, since GAE quality is entirely downstream of value predictions; the fix is value-loss clipping (mirroring the policy clip), a value-function warmup phase, and reward normalization so returns stay in a predictable range. Advantage explosion (unwhitened or badly-scaled advantages) produces enormous, destabilizing gradient updates even with the ratio clip in place, because the clip bounds the *ratio*, not the *magnitude* of $A_t$ itself. KL blowup — the policy drifts far enough from the reference that generation degenerates into repeated tokens or outright gibberish — is the RL-specific face of [[Concept - Reward Hacking]]: the policy has found a region where the reward model scores well but which no longer resembles coherent language, and it is inseparable from [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning|entropy collapse]], where the policy's output distribution narrows toward a single high-probability continuation and effectively stops exploring. All of these share a root cause worth naming explicitly: PPO is on-policy learning against a non-stationary, learned reward at a scale where a single bad step is expensive to recover from, so defaults that look like arbitrary "hyperparameters" are really hard-won stabilization tricks. The full symptom-first catalog, with fixes and detection signals, lives in [[Gotchas - RLHF Training Instabilities]].

## The non-obvious

The clip in $L^{CLIP}$ only prevents a single update from *overreacting* to one batch of rollouts — it does nothing to prevent the policy from drifting far from the reference over many small updates, each individually within the clip bound. That's why the ratio clip and the KL penalty are not redundant, even though both nominally limit "how far the policy moves": the clip is a per-step brake, the KL term is the cumulative-drift budget, and teams that rely on the clip alone (assuming it subsumes KL control) reliably discover, dozens of steps in, a policy that has wandered arbitrarily far from $\pi_{ref}$ one small legal step at a time.

## Connections

- [[Deep Dive - RLHF End to End]] — PPO is Stage 3 of the full pipeline; this note is the algorithm-internals depth that pipeline note doesn't cover.
- [[Concept - KL Control in RLHF]] — supplies both the per-token reward penalty PPO optimizes against and the cumulative-drift budget the ratio clip alone can't provide.
- [[Concept - GRPO and RL with Verifiable Rewards]] — the successor that removes PPO's value head entirely, replacing GAE with a group-normalized advantage.
- [[Concept - Reward Hacking]] — KL blowup and reward-model exploitation are PPO's specific instance of this general pathology.
- [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]] — the failure mode where PPO's output distribution narrows and stops exploring, often alongside KL blowup.
- [[Concept - Adam and AdamW]] — the optimizer used for PPO's policy and value updates, at a lower learning rate than SFT.
- [[Gotchas - RLHF Training Instabilities]] — the symptom-first catalog of the failure modes named above, with fixes and detection.
- [[Concept - Sampling and Decoding Parameters]] — the rollout-generation settings that shape exploration and dominate PPO's wall-clock cost.

## Sources

- Schulman et al. (2017) — "Proximal Policy Optimization Algorithms." The clipped surrogate objective this note is built around.
- Engstrom et al. (2020) — "Implementation Matters in Deep Policy Gradients." Shows PPO's implementation-level tricks (whitening, clipping) drive results as much as the core algorithm.
- Huang et al. — "The 37 Implementation Details of Proximal Policy Optimization." Catalogs the non-obvious defaults that make PPO stable in practice.
