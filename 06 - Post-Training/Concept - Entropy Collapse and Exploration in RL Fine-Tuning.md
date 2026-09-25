---
tags: [concept, domain/post-training, level/frontier]
aliases: [entropy collapse, exploration collapse, policy entropy in RL]
summary: "On-policy RL fine-tuning bleeds policy entropy, kills exploration, and caps gains; managing the entropy budget is the core RL-tuning skill."
---

# Concept - Entropy Collapse and Exploration in RL Fine-Tuning

> **One-paragraph hook:** Run [[Concept - PPO for Language Models]] or [[Concept - GRPO and RL with Verifiable Rewards|GRPO]] on a reasoning task and watch two curves. Reward climbs, then flattens. Policy entropy drops like a stone in the first few hundred steps and then sits near zero. Those two curves are one event: the model bought reward with entropy, ran out, and stopped improving. A near-deterministic policy can't explore, so it can't find the harder solutions that would have pushed reward higher, and its pass@k collapses even as pass@1 ticks up. Entropy collapse is the single most common reason an RL fine-tune plateaus below its potential. Keeping the entropy budget alive is the skill that separates a working RL run from a dead one.

## The mechanism

Policy entropy at a token is $H(\pi_\theta(\cdot\mid s)) = -\sum_a \pi_\theta(a\mid s)\log \pi_\theta(a\mid s)$. It's high when the model is uncertain over next tokens and near zero when one token dominates. In on-policy RL, exploration *is* this entropy: the trainer only ever sees an alternative solution if sampling puts non-trivial mass on the tokens that lead there.

On-policy policy gradients are multiplicative and self-reinforcing. A token with positive advantage gets its log-prob pushed up, and since the update scales with the current probability, tokens that are *already* probable and *also* advantaged get the largest absolute boost. Rich get richer: the modal trajectory is reinforced, its probability rises, entropy falls. Cui et al. (2025), *"The Entropy Mechanism of Reinforcement Learning for Reasoning Language Models,"* formalized this. The per-step change in policy entropy is governed by the **covariance between a token's log-probability and its advantage**:

$$\Delta H \;\propto\; -\,\mathrm{Cov}_{a\sim\pi}\big(\log\pi_\theta(a\mid s),\; A(s,a)\big)$$

When high-probability tokens carry high advantage (the normal case once training is succeeding), the covariance is positive and entropy *decreases* every step. So collapse isn't a hyperparameter bug. It's the default trajectory of an optimizer that's working.

Cui et al. also reported a striking empirical regularity. Across runs, downstream reward $R$ and policy entropy $H$ trace a near-deterministic curve of the form

$$R \approx -a\,e^{H} + b$$

Reward is "bought" with entropy at a predictable exchange rate, and once $H \to 0$ it saturates at $b$. You can often *predict a run's final reward from its entropy trajectory in the first few hundred steps*, which means a run whose entropy has already collapsed has already told you its ceiling. That makes [[Concept - Entropy and Cross-Entropy]] the prerequisite that matters here: entropy is the resource being spent, and treating it as a diagnostic afterthought misses that.

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

Entropy collapse is how **pass@1 can rise while pass@k falls**. The RL policy concentrates on one high-reward mode. Single-sample accuracy improves, but the diversity that best-of-N, majority vote and search depend on is gone. A model tuned to a hard pass@1 optimum is often a *worse* generator to sample from at k=64. That directly hurts the test-time-compute methods in [[Concept - Reasoning Training and Long Chain-of-Thought]], which rely on sampling many diverse rollouts. It's also the same distribution-narrowing seen in [[Concept - Spurious Rewards and RLVR Failure Modes]]: elicitation sharpens a mode and discards the tail.

The stabilization toolkit, roughly ordered by how well each holds up at scale:

- **DAPO's clip-higher** (Yu et al. 2025, *DAPO*). Standard PPO clips the importance ratio symmetrically to $[1-\varepsilon,\,1+\varepsilon]$ with $\varepsilon\approx0.2$. The upper clip caps how much a *low-probability* token can be up-weighted, and that's the exploration you want to keep. Clip-higher decouples the bounds: raise $\varepsilon_{\text{high}}$ (to ~0.28), keep $\varepsilon_{\text{low}}$ tight, and promising rare tokens stop getting throttled. It's the most reliable single knob.
- **Dynamic sampling** (also DAPO). Drop prompts whose GRPO group is all-correct or all-wrong. Those give zero advantage and zero gradient, yet they still let the surviving prompts over-sharpen. Filtering keeps the gradient informative and slows collapse.
- **Covariance-targeted clipping** (Cui et al. 2025). Clip-Cov and KL-Cov restrain the highest-covariance tokens directly (the ones the theory flags as the entropy sink) instead of clipping by ratio magnitude. More surgical than clip-higher, less battle-tested.
- **KL-to-reference anchor.** A [[Concept - KL Control in RLHF]] penalty toward the SFT policy indirectly limits how far entropy can fall, because the reference still has spread. It slows collapse but doesn't target it.
- **Entropy bonus.** Add $+\beta_H H(\pi)$ to the objective. Classic in deep RL, but **unstable at LLM scale**: too small does nothing, slightly too large blows entropy up into gibberish, and the safe band is narrow and run-dependent. Most modern LLM-RL recipes prefer clip-higher.

Rollout temperature is an exploration lever too. The trainer learns from samples drawn at some temperature (see [[Concept - Sampling and Decoding Parameters]]). Too low a rollout temperature starves it of diversity and speeds up collapse, so RLVR runs typically sample rollouts at T≈0.7–1.0 even when the deployed model will decode greedily.

## Failure modes

- **Silent plateau.** Reward flat for thousands of steps, no error. Cause: entropy already collapsed, so there's nothing left to explore. Detection: overlay entropy. If it hit ~0 before the plateau, that's your answer. Fix: raise $\varepsilon_{\text{high}}$, add dynamic sampling, restart from an earlier checkpoint with more entropy.
- **pass@1 up, pass@k down.** The model got "better" on the leaderboard metric and worse as a sampler. Detection: always track the pass@k / pass@1 gap, never pass@1 alone. This is the catastrophe that looks like success.
- **Collapse to a single phrase / mode collapse.** Too-high LR or too-aggressive updates drive entropy to ~0 and the policy emits one templated response. Overlaps with [[Gotchas - RLHF Training Instabilities]]. Detection: falling generation entropy plus rising repetition. Fix: lower LR, clip-higher, KL anchor.
- **Entropy *explosion*** (the opposite tail). An oversized entropy bonus or a mis-signed KL sends entropy up and the policy toward gibberish. Detection: entropy rising while reward falls.

## The non-obvious

**The entropy RL destroys is the same resource RL needs to keep improving, so the objective limits itself and no setting is "set it and forget it".** You're managing a budget. Too much entropy and the policy never converges; too little and it collapses before it explores the hard cases. The part that trips up teams coming from classic deep RL: the entropy bonus that "just works" in Atari is treacherous on LLMs. A language policy's action space is ~$10^5$ tokens, and the entropy-bonus gradient interacts with the pretrained prior in ways that make the safe coefficient tiny and unstable. The reliable lever turned out to be refusing to punish rare good tokens, not *rewarding* entropy. Clip-higher, a change to the clip bound and not the loss, became the field's default fix in 2025.

Entropy collapse has a sibling pathology one rung deeper into tribal knowledge. [[Concept - Length Bias in Preference Optimization]] is the same self-reinforcing, rich-get-richer optimizer dynamic playing out through a reward proxy instead of raw token probability. One narrows the whole output distribution; the other narrows toward a single spurious feature.

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
