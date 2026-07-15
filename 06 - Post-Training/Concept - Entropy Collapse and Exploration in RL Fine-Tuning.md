---
tags: [concept, domain/post-training, level/frontier]
aliases: [entropy collapse, exploration collapse, policy entropy in RL]
summary: "On-policy RL fine-tuning bleeds policy entropy, kills exploration, and caps gains; managing the entropy budget is the core RL-tuning skill."
---

# Concept - Entropy Collapse and Exploration in RL Fine-Tuning

> **One-paragraph hook:** Run [[Concept - PPO for Language Models]] or [[Concept - GRPO and RL with Verifiable Rewards|GRPO]] on a reasoning task and watch two curves. Reward climbs, then flattens. Policy entropy drops like a stone in the first few hundred steps and then sits near zero. Those two curves are the same event: the model bought reward with entropy, ran out of entropy, and stopped improving. Once the policy is near-deterministic it cannot explore, so it cannot discover the harder solutions that would have pushed reward higher — and its pass@k collapses even as pass@1 ticks up. Entropy collapse is the single most common reason an RL fine-tune plateaus below its potential, and keeping the entropy budget alive is the skill that separates a working RL run from a dead one.

## The mechanism

Policy entropy at a token is $H(\pi_\theta(\cdot\mid s)) = -\sum_a \pi_\theta(a\mid s)\log \pi_\theta(a\mid s)$ — high when the model is uncertain over next tokens, near zero when one token dominates. Exploration in on-policy RL *is* this entropy: the only way the trainer ever sees an alternative solution is if sampling puts non-trivial mass on the tokens that lead there.

On-policy policy gradients are **multiplicative and self-reinforcing**. A token with positive advantage gets its log-prob pushed up; because the update is proportional to the current probability, tokens that are *already* probable and *also* advantaged get the largest absolute boost. This is a rich-get-richer dynamic: the modal trajectory is reinforced, its probability rises, and the entropy of the distribution falls. Cui et al. (2025), *"The Entropy Mechanism of Reinforcement Learning for Reasoning Language Models,"* made this precise — the per-step change in policy entropy is governed by the **covariance between a token's log-probability and its advantage**:

$$\Delta H \;\propto\; -\,\mathrm{Cov}_{a\sim\pi}\big(\log\pi_\theta(a\mid s),\; A(s,a)\big)$$

When high-probability tokens carry high advantage (the normal case as training succeeds), the covariance is positive and entropy *decreases* every step. The collapse is not a bug in a hyperparameter; it is the default trajectory of a working optimizer.

Cui et al. also reported a striking empirical regularity: across runs, downstream reward $R$ and policy entropy $H$ trace a near-deterministic curve of the form

$$R \approx -a\,e^{H} + b$$

so reward is "bought" with entropy at a predictable exchange rate, and once $H \to 0$ the reward saturates at $b$. You can often *predict a run's final reward from its entropy trajectory in the first few hundred steps* — which also means a run whose entropy has already collapsed has already told you its ceiling. This is why [[Concept - Entropy and Cross-Entropy]] is the load-bearing prerequisite: entropy here is not a diagnostic afterthought, it is the resource being spent.

```
   entropy H                          reward R
 hi |\                              hi |        ______ (plateau at b)
    | \                                |    ___/
    |  \___                            |  _/
    |      \____                       | /
 lo |___________\_____ steps       lo |/________________ steps
     collapse ~200-600 steps            saturates when H->0
```

## In practice

Entropy collapse is why **pass@1 can rise while pass@k falls**. The RL policy concentrates onto one high-reward mode; single-sample accuracy improves, but the diversity that best-of-N, majority vote, and search depend on is gone. A model tuned to a hard pass@1 optimum is often a *worse* generator to sample from at k=64 — directly hurting the test-time-compute methods discussed in [[Concept - Reasoning Training and Long Chain-of-Thought]], which rely on sampling many diverse rollouts. It is also the same distribution-narrowing that shows up in [[Concept - Spurious Rewards and RLVR Failure Modes]]: elicitation sharpens a mode and discards the tail.

The stabilization toolkit, roughly in order of how well it holds up at scale:

- **DAPO's clip-higher** (Yu et al. 2025, *DAPO*). Standard PPO clips the importance ratio symmetrically to $[1-\varepsilon,\,1+\varepsilon]$ with $\varepsilon\approx0.2$. The upper clip caps how much a *low-probability* token can be up-weighted — which is exactly the exploration you want to preserve. Clip-higher **decouples** the bounds, raising $\varepsilon_{\text{high}}$ (to ~0.28) while keeping $\varepsilon_{\text{low}}$ tight, so promising rare tokens aren't throttled. This is the most reliable single knob.
- **Dynamic sampling** (also DAPO). Drop prompts whose GRPO group is all-correct or all-wrong — those give zero advantage and zero gradient but still let the surviving prompts over-sharpen. Filtering keeps the gradient informative and slows collapse.
- **Covariance-targeted clipping** (Cui et al. 2025). **Clip-Cov** and **KL-Cov** directly restrain the highest-covariance tokens — the ones the theory identifies as the entropy sink — instead of clipping by ratio magnitude. More surgical than clip-higher, less battle-tested.
- **KL-to-reference anchor.** A [[Concept - KL Control in RLHF]] penalty toward the SFT policy indirectly limits how far entropy can fall, because the reference still has spread. It slows collapse but does not target it.
- **Entropy bonus.** Add $+\beta_H H(\pi)$ to the objective. Classic in deep RL, but **unstable at LLM scale** — too small does nothing, slightly too large blows entropy up into gibberish, and the safe band is narrow and run-dependent. Most modern LLM-RL recipes prefer clip-higher over an entropy bonus.

**Rollout temperature is an exploration lever too.** The samples the trainer learns from are drawn at some temperature (see [[Concept - Sampling and Decoding Parameters]]); too low a rollout temperature starves the trainer of diversity and accelerates collapse, so RLVR runs typically sample rollouts at T≈0.7–1.0 even when the deployed model will decode greedily.

## Failure modes

- **Silent plateau.** Reward flat for thousands of steps, no error. Cause: entropy already collapsed; there's nothing left to explore. Detection: overlay entropy — if it hit ~0 before the plateau, that's your answer. Fix: raise $\varepsilon_{\text{high}}$, add dynamic sampling, restart from an earlier checkpoint with more entropy.
- **pass@1 up, pass@k down.** The model got "better" on the leaderboard metric and worse as a sampler. Detection: always track the pass@k / pass@1 gap, not pass@1 alone. This is the catastrophe that looks like success.
- **Collapse to a single phrase / mode collapse.** Entropy driven to ~0 by too-high LR or too-aggressive updates; the policy emits one templated response. Overlaps with [[Gotchas - RLHF Training Instabilities]]. Detection: falling generation entropy plus rising repetition; Fix: lower LR, clip-higher, KL anchor.
- **Entropy *explosion*** (the opposite tail). Too large an entropy bonus or KL that's mis-signed sends entropy up and the policy toward gibberish. Detection: entropy rising and reward falling together.

## The non-obvious

The hard-won insight: **the entropy that RL destroys is the exact resource RL needs to keep improving, so the objective is fundamentally self-limiting and there is no "set it and forget it" setting.** You are managing a budget, not tuning a constant — too much entropy and the policy never converges; too little and it collapses before it explores the hard cases. The corollary that trips up teams migrating from classic deep RL: the entropy bonus that "just works" in Atari is treacherous on LLMs, because a language policy's action space is ~$10^5$ tokens and the entropy-bonus gradient interacts with the pretrained prior in ways that make the safe coefficient tiny and unstable. The reliable lever turned out not to be *rewarding* entropy but *refusing to punish rare good tokens* — which is why clip-higher, a change to the clip bound rather than the loss, quietly became the field's default fix in 2025.

Entropy collapse has a sibling pathology one rung deeper into tribal knowledge: [[Concept - Length Bias in Preference Optimization]] is the same self-reinforcing, rich-get-richer optimizer dynamic playing out through a reward proxy instead of raw token probability — one narrows the whole output distribution, the other narrows toward a single spurious feature.

## Connections

- [[Concept - PPO for Language Models]] — the clipped-surrogate mechanics whose upper clip is precisely the exploration-throttling knob clip-higher relaxes.
- [[Concept - GRPO and RL with Verifiable Rewards]] — the on-policy algorithm where entropy collapse is most acute; dynamic sampling and clip-higher were designed for it.
- [[Concept - KL Control in RLHF]] — the reference anchor that indirectly bounds entropy loss; a sibling control on the same distribution-drift axis.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — test-time scaling depends on rollout diversity, which entropy collapse destroys.
- [[Concept - Entropy and Cross-Entropy]] — the definition and intuition for the quantity being spent; the down-link prerequisite.
- [[Concept - Sampling and Decoding Parameters]] — rollout temperature is an exploration lever; too-low T accelerates collapse.
- [[Gotchas - RLHF Training Instabilities]] — mode collapse and gibberish are the acute failure faces of the same entropy dynamics.
- [[Concept - Spurious Rewards and RLVR Failure Modes]] — the pass@1-up/pass@k-down signature is the shared fingerprint of entropy-driven distribution narrowing.
- [[Concept - Length Bias in Preference Optimization]] — the ladder up-link: the sibling collapse pathology in preference optimization, narrowing toward a proxy feature the way entropy collapse narrows the whole distribution.

## Sources
- Cui et al. (2025) — *The Entropy Mechanism of Reinforcement Learning for Reasoning Language Models*. Derived the $\Delta H \propto -\mathrm{Cov}(\log\pi, A)$ law and the $R \approx -a e^{H}+b$ curve; proposed Clip-Cov / KL-Cov.
- Yu et al. (2025) — *DAPO: An Open-Source LLM RL System at Scale*. Introduced clip-higher and dynamic sampling as practical anti-collapse measures.
- Schulman et al. (2017) — *Proximal Policy Optimization*. The clipped surrogate whose symmetric bound clip-higher decouples.
