---
tags: [concept, domain/post-training, level/advanced]
aliases: [KL penalty, KL regularization, adaptive KL controller, KL coefficient]
summary: "Why beta times KL-to-reference is RLHF's master dial: the reward-KL frontier, adaptive schedules, and the k1/k2/k3 estimators."
---

> **One-paragraph hook:** Every preference-optimization method ([[Deep Dive - RLHF End to End|PPO-based RLHF]], [[Concept - Direct Preference Optimization (DPO)|DPO]], [[Concept - GRPO and RL with Verifiable Rewards|GRPO]]) is secretly tuning the same dial: how far the trained policy may drift from the reference model it started as. That dial is the KL penalty, and getting it wrong in either direction is the single most common way these methods fail. Too loose and the policy hacks the reward into gibberish. Too tight and nothing improves. Almost every RLHF postmortem traces back to this one number.

## The mechanism

The RL objective in [[Concept - PPO for Language Models]] is $\mathbb{E}[r(x,y)] - \beta \cdot \text{KL}(\pi_\theta \| \pi_{ref})$: reward from the RM minus a [[Concept - KL Divergence]] term scaled by $\beta$. $\beta$ is more than a minor regularization coefficient. It directly trades reward against faithfulness to the reference distribution, and the (reward, KL) curve over training is *the* diagnostic for overoptimization. Gao et al. (2023) show true reward rises with KL up to a point and then falls, while the gap between the proxy reward model's score and a gold/held-out reward grows roughly with $\sqrt{\text{KL}}$ for Bradley-Terry reward models. You only see that turnover if you plot reward against KL instead of against training step.

The right KL strength isn't known in advance and it drifts during training. Ziegler et al. (2019) handled this with the adaptive KL controller: measure realized KL each step and adjust $\beta$ proportionally to close the gap to a target (InstructGPT-era runs commonly targeted around 6 nats). KL above target, raise $\beta$; below target, lower it. Picking $\beta$ stops being a one-shot hyperparameter guess and becomes a closed-loop control problem, which holds up far better across different prompts, reward-model scales and training durations.

There are three common ways to estimate KL from samples, all built on the log-ratio $\log(\pi_\theta/\pi_{ref})$ (Schulman, "Approximating KL Divergence"):

$$k_1 = \log\frac{\pi_\theta}{\pi_{ref}}, \qquad k_2 = \tfrac{1}{2}\Big(\log\frac{\pi_\theta}{\pi_{ref}}\Big)^2, \qquad k_3 = \frac{\pi_{ref}}{\pi_\theta} - \log\frac{\pi_{ref}}{\pi_\theta} - 1$$

$k_1$ is unbiased in expectation but high-variance, and any individual sample can come out negative. $k_3$ is also unbiased, always $\ge 0$ pointwise (so one bad sample can't produce a nonsensical negative "divergence"), and lower-variance. Most modern RLHF and RL-with-verifiable-reward implementations default to $k_3$ over the naive log-ratio for that reason. The resulting penalty can be folded into the per-token RL reward (the standard PPO reward-shaping form) or added to the policy gradient as a separate auxiliary loss. Both show up in production code, and once advantage normalization is involved they aren't strictly equivalent.

## In practice

The dial isn't unique to PPO-based RLHF. [[Concept - Direct Preference Optimization (DPO)]]'s $\beta$ *is* the same KL-strength knob, baked into a closed-form loss instead of tuned online by an adaptive controller. DPO's typical $\beta \approx 0.1$ and PPO's typical target-KL setpoints answer the same question through different mechanisms. [[Concept - GRPO and RL with Verifiable Rewards]] typically adds a $k_3$ KL-to-reference term with a small coefficient, and some GRPO variants set it to zero when the verifiable-reward signal is trusted enough that drift matters less. That removing it counts as a deliberate, named design choice shows how central the dial is.

Watching KL tells you more than watching reward. This is folklore, weakly sourced but consistent across practitioner reports: reward can look great and climb steadily while KL silently explodes underneath, because the reward model happily gives high scores to off-distribution text it was never trained to judge. The reverse also holds. KL collapsing toward zero mid-run means the policy has stopped moving, and effectively no learning is happening whatever the loss curves suggest.

## Failure modes

**Too little KL control.** Either $\beta$ is too small or an adaptive controller has too permissive a target. The policy drifts into regions where the reward model is uncalibrated, which is [[Concept - Reward Hacking]] in its most direct form. It's also tangled up with [[Concept - Mode Collapse in RLHF]]: once the leash is loose enough, the policy over-concentrates its output distribution on a narrow set of reward-hacking continuations.

**Too much KL control.** The policy stays pinned so close to $\pi_{ref}$ that the RL stage produces negligible improvement. Reward barely moves because the policy is barely allowed to.

**Biased or wrong-sign estimator.** A silent, implementation-specific failure. Use $k_1$ naively and treat negative per-sample estimates as valid penalty values, and you can inject noise or a systematically wrong-signed gradient into training. Nothing crashes or complains; the run just trains worse.

[[Gotchas - RLHF Training Instabilities]] catalogs all three, with detection signals, alongside RLHF's other instability patterns.

## The non-obvious

Calling KL "the regularizer" undersells it. It's what keeps the reward model's judgments meaningful at all, since the RM was only trained on data sampled from something close to $\pi_{ref}$. Off that support, an RM's score is noisy and often actively wrong, in a direction that rewards degenerate text. So "just lower the KL penalty to let the model improve faster" is close to the single most common way practitioners accidentally induce reward hacking. And the fix for a stalled-looking RLHF run is almost never "loosen KL further", even though that's the intuitive first move.

## Connections

- [[Deep Dive - RLHF End to End]] — the full pipeline this dial governs; KL control determines whether Stage 3's RL loop stays anchored to a coherent policy.
- [[Concept - PPO for Language Models]] — the algorithm whose reward-shaping and clipped update this KL term is folded into.
- [[Concept - KL Divergence]] — the general-purpose divergence measure this note's estimators (k1/k2/k3) approximate from samples.
- [[Concept - Direct Preference Optimization (DPO)]] — DPO's $\beta$ is the same KL-strength knob expressed in closed form rather than tuned online.
- [[Concept - Reward Hacking]] — too-loose KL control is the direct mechanism by which reward hacking becomes possible.
- [[Concept - GRPO and RL with Verifiable Rewards]] — uses the same $k_3$ estimator, often at a much smaller or zero coefficient.
- [[Concept - Entropy and Cross-Entropy]] — KL divergence decomposes into a cross-entropy and entropy term; the same information-theoretic family as this note's estimators.
- [[Gotchas - RLHF Training Instabilities]] — where too-low, too-high, and mis-estimated KL each appear as named, detectable symptoms.
- [[Concept - Mode Collapse in RLHF]] — the output-distribution-narrowing failure that loose KL control permits and accelerates.

## Sources

- Ziegler et al. (2019) — "Fine-Tuning Language Models from Human Preferences." Introduces the adaptive KL controller targeting a fixed KL setpoint.
- Gao et al. (2023) — "Scaling Laws for Reward Model Overoptimization." The reward-vs-KL frontier as the diagnostic curve for hacking; the sqrt(KL) gold-proxy gap.
- Schulman, J. — "Approximating KL Divergence." Derives and compares the k1/k2/k3 sample-based KL estimators.
