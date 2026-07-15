---
tags: [concept, domain/post-training, level/advanced]
aliases: [KL penalty, KL regularization, adaptive KL controller, KL coefficient]
summary: "Why beta times KL-to-reference is RLHF's master dial: the reward-KL frontier, adaptive schedules, and the k1/k2/k3 estimators."
---

> **One-paragraph hook:** Every preference-optimization method — [[Deep Dive - RLHF End to End|PPO-based RLHF]], [[Concept - Direct Preference Optimization (DPO)|DPO]], [[Concept - GRPO and RL with Verifiable Rewards|GRPO]] — is secretly tuning the same single dial: how far the trained policy is allowed to drift from the reference model it started as. That dial is the KL penalty, and getting it wrong in either direction is the single most common way these methods fail. Too loose and the policy hacks the reward into gibberish; too tight and nothing improves. Almost every RLHF postmortem traces back to this one number.

## The mechanism

The RL objective in [[Concept - PPO for Language Models]] is $\mathbb{E}[r(x,y)] - \beta \cdot \text{KL}(\pi_\theta \| \pi_{ref})$: reward from the RM minus a [[Concept - KL Divergence]] term scaled by $\beta$. $\beta$ is not a minor regularization coefficient — it directly trades reward against faithfulness to the reference distribution, and the resulting (reward, KL) curve as training progresses is *the* diagnostic for overoptimization: Gao et al. (2023) show true reward rises with KL up to a point and then falls, while the gap between the proxy reward model's score and a gold/held-out reward grows roughly with $\sqrt{\text{KL}}$ for Bradley-Terry reward models. Plotting reward against KL, rather than reward against training step, is what makes this turnover visible.

Because the optimal KL strength isn't known in advance and drifts as training progresses, Ziegler et al. (2019) introduced the adaptive KL controller: measure the realized KL each step, and adjust $\beta$ proportionally to close the gap against a target (InstructGPT-era runs commonly targeted around 6 nats) — raise $\beta$ when KL runs above target, lower it when KL runs below target. This turns "pick the right $\beta$" from a one-shot hyperparameter guess into a closed-loop control problem, which is far more robust across different prompts, reward-model scales, and training durations.

Estimating KL itself from samples has three common forms, all derived from the log-ratio $\log(\pi_\theta/\pi_{ref})$ (Schulman, "Approximating KL Divergence"):

$$k_1 = \log\frac{\pi_\theta}{\pi_{ref}}, \qquad k_2 = \tfrac{1}{2}\Big(\log\frac{\pi_\theta}{\pi_{ref}}\Big)^2, \qquad k_3 = \frac{\pi_{ref}}{\pi_\theta} - \log\frac{\pi_{ref}}{\pi_\theta} - 1$$

$k_1$ is an unbiased estimator of KL in expectation but can be negative on any individual sample and is high-variance; $k_3$ is also unbiased, is always $\ge 0$ pointwise (so a single bad sample can't produce a nonsensical negative "divergence"), and has lower variance — which is why most modern RLHF and RL-with-verifiable-reward implementations default to $k_3$ rather than the naive log-ratio. The penalty computed this way can be folded directly into the per-token RL reward (as in the standard PPO reward-shaping form) or applied as a separate auxiliary loss term added to the policy gradient; both appear in production code, and they are not exactly equivalent once combined with advantage normalization.

## In practice

$\beta$ is not unique to PPO-based RLHF — [[Concept - Direct Preference Optimization (DPO)]]'s $\beta$ *is* the same KL-strength knob, just baked into a closed-form loss instead of tuned online via an adaptive controller, which is why DPO's typical $\beta \approx 0.1$ and PPO's typical target-KL setpoints are answering the same underlying question through different mechanisms. [[Concept - GRPO and RL with Verifiable Rewards]] typically adds a $k_3$ KL-to-reference term with a small coefficient, and some GRPO variants set it to zero entirely when the verifiable-reward signal is trusted enough that drift is less of a concern — a sign of how central this dial is that removing it is a deliberate, named design choice rather than an oversight. In practice, watching KL is more informative than watching reward: folklore, weakly sourced but consistent across practitioner reports — reward can look great and be climbing steadily while KL silently explodes underneath it, because the reward model happily assigns high scores to off-distribution text it was never trained to judge. Conversely, KL collapsing toward zero mid-run is a sign the policy has stopped moving at all — effectively no learning is happening, whatever the loss curves suggest.

## Failure modes

Too-low effective KL control (either $\beta$ set too small, or an adaptive controller with too permissive a target) lets the policy drift into distribution regions where the reward model is uncalibrated, which is [[Concept - Reward Hacking]] in its most direct form — this is also entangled with [[Concept - Mode Collapse in RLHF]], where the policy over-concentrates its output distribution on a narrow set of reward-hacking continuations once the KL leash is loose enough to permit it. Too-high KL control keeps the policy pinned so close to $\pi_{ref}$ that the RL stage produces negligible improvement — reward barely moves because the policy is barely allowed to move. A biased or wrong-sign KL estimator is a silent failure specific to implementation: using $k_1$ naively and treating negative per-sample estimates as if they were valid penalty values can inject noise or a systematically wrong-signed gradient into training without any visible error, since nothing in the training loop crashes or complains — it just quietly trains worse. All three failure modes, plus their detection signals, are cataloged alongside the rest of RLHF's instability patterns in [[Gotchas - RLHF Training Instabilities]].

## The non-obvious

Treating KL as "the regularizer" undersells what it actually does: it is the mechanism that keeps the reward model's judgments meaningful in the first place, because the RM was only ever trained on data sampled from something close to $\pi_{ref}$. A reward model's score off that support isn't just noisy, it's often actively wrong in a direction that rewards degenerate text — which is why "just lower the KL penalty to let the model improve faster" is close to the single most common way practitioners accidentally induce reward hacking, and why the fix for a stalled-looking RLHF run is almost never "loosen KL further" even though that's the intuitive first move.

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
