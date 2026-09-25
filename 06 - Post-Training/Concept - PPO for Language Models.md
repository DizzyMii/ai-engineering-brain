---
tags: [concept, domain/post-training, level/advanced]
aliases: [PPO, Proximal Policy Optimization]
summary: "How PPO's clipped surrogate, GAE, and a value head map onto autoregressive generation, and why its implementation details are load-bearing."
---

> **One-paragraph hook:** PPO is the RL algorithm inside the third stage of [[Deep Dive - RLHF End to End]]. It was built for robotics and games, then adapted to the odd shape of autoregressive text generation: a token-level MDP whose reward is mostly zero until the last step. It works, but it's notoriously finicky at LLM scale. The math is fine. The trouble is a long list of unglamorous implementation details (advantage whitening, reward clipping, value-loss clipping) that decide whether a run converges or collapses into gibberish within a few hundred steps.

## The mechanism

Treat generation as a Markov Decision Process. The state at step $t$ is the prompt plus every token generated so far, the action is the next token, and the policy $\pi_\theta$ is the language model's next-token distribution. Every non-terminal token gets (near) zero reward apart from a per-token [[Concept - KL Control in RLHF|KL penalty]] against a frozen reference; the reward model's scalar score is added once, at the terminal (EOS) token. So the reward is deferred and sparse by construction. That's unusual for RL, and it's what makes credit assignment across a several-hundred-token sequence hard. Discount $\gamma \approx 1$ (nothing justifies discounting inside one response) and GAE $\lambda \approx 0.95$.

PPO's central trick is the clipped surrogate objective, which bounds how far one gradient step can move the policy away from the policy that generated the rollout:

$$L^{CLIP}(\theta) = \mathbb{E}_t\Big[\min\big(\rho_t A_t,\ \text{clip}(\rho_t,\, 1-\epsilon,\, 1+\epsilon)\, A_t\big)\Big]$$

Here $\rho_t = \pi_\theta(a_t|s_t) / \pi_{\theta_{old}}(a_t|s_t)$ is the probability ratio between the updated and rollout-time policy, $A_t$ is the advantage estimate, and $\epsilon \approx 0.2$. The clip caps the gain from pushing a large ratio on a positive advantage and caps the penalty on a negative one. In practice that stops any single minibatch update from moving the policy far enough to invalidate the rollouts it was computed from. That's the "proximal" in the name.

Advantages come from a separate value head $V_\phi(s_t)$, usually sharing the transformer backbone with the policy but with its own output head, via Generalized Advantage Estimation:

$$A_t = \sum_{l=0}^{T-t} (\gamma\lambda)^l \, \delta_{t+l}, \qquad \delta_t = r_t + \gamma V_\phi(s_{t+1}) - V_\phi(s_t)$$

The value head trains on its own (also clipped) regression loss toward the return. In practice it needs a warmup period before its predictions are good enough for GAE to give a useful signal. Training the policy against a badly initialized value function is a common source of early-run instability.

## In practice

The equations alone won't make PPO train stably at billion-parameter scale. A set of "implementation details" missing from the original paper dominate outcomes. Advantage whitening (normalize $A_t$ to mean 0, variance 1 within each minibatch) and reward normalization/clipping are standard, not optional: Engstrom et al. (2020) and Huang's "The 37 Implementation Details of Proximal Policy Optimization" both show that ablating these tricks hurts PPO as much as or more than changing the core algorithm.

Typical runs do 1–4 PPO epochs over each rollout batch, split into minibatches. The KL coefficient is fixed or [[Concept - KL Control in RLHF|adaptively-scheduled]], and rollout batches are large (thousands of prompts) because small-batch reward and advantage estimates are too noisy for a stable gradient. Generation is autoregressive and dominates wall-clock time, and the [[Concept - Sampling and Decoding Parameters]] used for rollouts (temperature, top-p) directly set the exploration/exploitation tradeoff the loop depends on. The optimizer is [[Concept - Adam and AdamW]], typically at a much lower learning rate than SFT, since PPO updates are meant to be small incremental policy shifts.

## Failure modes

Value-model divergence, where the value loss spikes or grows without bound, is usually the first thing to break, because GAE quality depends entirely on value predictions. Fixes: value-loss clipping (mirroring the policy clip), a value-function warmup phase, and reward normalization so returns stay in a predictable range.

Advantage explosion (unwhitened or badly scaled advantages) produces huge, destabilizing updates even with the ratio clip on. The clip bounds the *ratio*, not the *magnitude* of $A_t$.

KL blowup is when the policy drifts far enough from the reference that generation degenerates into repeated tokens or gibberish. It's the RL-specific form of [[Concept - Reward Hacking]]: the policy has found a region the reward model scores well that no longer looks like coherent language. It comes tangled with [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning|entropy collapse]], where the output distribution narrows toward one high-probability continuation and effectively stops exploring.

These share a root cause. PPO is on-policy learning against a non-stationary, learned reward, at a scale where one bad step is expensive to recover from. Defaults that look like arbitrary "hyperparameters" are hard-won stabilization tricks. The full symptom-first catalog, with fixes and detection signals, is in [[Gotchas - RLHF Training Instabilities]].

## The non-obvious

The clip in $L^{CLIP}$ only keeps a single update from *overreacting* to one batch of rollouts. It does nothing about the policy drifting far from the reference over many small updates, each inside the clip bound. So the ratio clip and the KL penalty aren't redundant, even though both nominally limit how far the policy moves. The clip is a per-step brake; the KL term is the cumulative-drift budget. Teams that rely on the clip alone, assuming it covers KL control, reliably find a policy dozens of steps in that has wandered arbitrarily far from $\pi_{ref}$ one small legal step at a time.

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
