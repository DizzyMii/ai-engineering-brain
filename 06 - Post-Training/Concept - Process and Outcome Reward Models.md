---
tags: [concept, domain/post-training, level/frontier]
aliases: [PRM, ORM, process reward model, outcome reward model, process supervision]
summary: "Scoring a whole answer (ORM) versus scoring every reasoning step (PRM), and why RLVR at scale mostly displaced PRMs anyway."
---
> **One-paragraph hook:** With long chains of reasoning came the question of where to attach the reward: the final answer only, or every step? Process reward models promised denser signal and better credit assignment for long chain-of-thought. By 2025 the field's flagship reasoning system had tried them, found them unstable and hackable at scale, and shipped without them. Knowing why is the fastest route to understanding what [[Concept - GRPO and RL with Verifiable Rewards]] actually buys you.

## The mechanism
An **outcome reward model (ORM)** gives one scalar to a completed trajectory. Either correct/incorrect against a verifier, or a learned score trained like a standard [[Concept - Reward Models]]: Bradley-Terry over pairwise comparisons, applied to the whole answer.

A **process reward model (PRM)** splits a chain-of-thought $y = (s_1, \dots, s_n)$ into steps and assigns each a reward $r_i = \text{PRM}(x, s_1, \dots, s_i)$. Lightman et al. 2023 ("Let's Verify Step by Step," OpenAI) trained a PRM on PRM800K, ~800K human step-level labels (positive/neutral/negative), with a per-step binary cross-entropy loss:

$$\mathcal{L} = -\sum_i \big[\, y_i \log p_i + (1-y_i)\log(1-p_i) \,\big], \quad p_i = \text{PRM}(x, s_1{:}i)$$

Human labeling doesn't scale, so Wang et al. 2023 (Math-Shepherd) automated it. From step $s_i$, run $k$ Monte Carlo rollouts to a final answer and set the step's soft target to the fraction that reach the correct answer (or threshold that into a hard 0/1 label). A step is "good" if it's still on a path that plausibly resolves correctly, whether or not a human reads it.

Both get used two ways. As a **verifier** at inference time: score $N$ sampled solutions (min-over-steps, product-over-steps, or last-step score) and pick the best, or guide a tree/MCTS-style search that prunes bad branches early. As a **reward signal during RL**, where a PRM's per-step reward is supposed to ease credit assignment compared with a single terminal reward.

## In practice
Lightman et al.'s headline result: at the same sample budget on MATH, a PRM-based verifier beats both an ORM-based verifier and majority voting. That's the empirical case for "process supervision beats outcome supervision," at least for verification. Math-Shepherd got the same qualitative win without human labels, using MC-estimated soft labels for reranking and as an RL reward.

The use that held up best is inference-time reranking (best-of-N with a PRM), not training-time RL reward. As a one-shot scorer over $N$ completions already sampled, a PRM is hard to game, since no gradient pressure is adapting the policy against it. As a live RL reward it becomes the kind of proxy [[Concept - Reward Hacking]] describes: a differentiable target under sustained optimization pressure.

## Failure modes
PRMs inherit every failure mode of ordinary reward models and widen the attack surface: an ORM has one place to hack (the final answer), a PRM has $n$ per trajectory.

- **PRM reward hacking:** plausible-but-wrong steps get high scores. Fluent, confident intermediate reasoning rates well with a step-level scorer regardless of correctness.
- **MC label noise** is real at low $k$. With few rollouts, Math-Shepherd's soft labels have high variance and the PRM ends up fitting noise.
- **Distribution shift** compounds over an RL run. A PRM trained on one policy's outputs starts misjudging a policy that has moved away from that distribution, the same overoptimization dynamic that hits any [[Concept - Reward Models]] under a drifting policy.

The most concrete data point is DeepSeek's own report ([[Breakdown - DeepSeek-R1]]): they tried PRM-guided training and MCTS-style search and dropped both, citing instability and hackability at the scale of their RL runs.

## The non-obvious
The "denser signal helps" intuition partly breaks down once you have a strong outcome-only RLVR signal. [[Concept - GRPO and RL with Verifiable Rewards]]'s group-relative baseline already gives workable credit assignment with no value network or per-step critic. So process supervision's marginal benefit shrinks just as its cost (a new, gameable reward surface) grows. The folklore since then: a PRM is a solid *verifier*, a passive judge over candidates already generated, and a fragile *trainer*, an active target gradient descent will find cracks in over enough RL steps. "Should I add a PRM?" and "should I add a PRM as an RL reward?" are two different questions with different risks.

## Connections
- [[Concept - Reward Models]] — PRM and ORM are both reward-model variants; PRM just scores per-step instead of per-sequence, reusing the same Bradley-Terry machinery underneath the learned variant.
- [[Concept - GRPO and RL with Verifiable Rewards]] — GRPO's outcome-only rule reward is the alternative that displaced PRMs as the training-time signal at scale.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — PRMs were the field's original hoped-for scaffold for long-CoT training before pure outcome RL proved sufficient on its own.
- [[Concept - Chain-of-Thought and Why It Works]] — process reward only makes sense once you've decomposed a CoT into discrete, scoreable steps.
- [[Concept - Reward Hacking]] — PRMs are a special, higher-surface-area case of the general reward-hacking problem.
- [[Breakdown - DeepSeek-R1]] — the most-cited real-world data point of a lab trying PRM-guided training and abandoning it for hacking and instability at scale.
- [[Concept - Speculative Decoding]] — both patterns share a generate-candidates-then-verify-before-committing shape, even though what's being verified (token correctness vs. reasoning-step correctness) differs.
- [[Concept - Statistical Rigor in Model Evaluation]] — comparing PRM-guided against ORM-guided best-of-N requires the same care about sample-size noise as any other eval comparison.
- [[Lore - Reward Hacking Hall of Fame]] — catalogs the RLVR-era verifier-gaming incidents that PRM training is especially prone to.

## Sources
- Lightman et al. (2023) — Let's Verify Step by Step. PRM800K dataset; shows process supervision beats outcome supervision for MATH verification.
- Wang et al. (2023) — Math-Shepherd. Automatic process-label generation via Monte Carlo rollouts, removing the need for human step labels.
- DeepSeek-AI (2025) — DeepSeek-R1 technical report. Reports PRM and MCTS instability/hacking at scale and drops both in favor of rule-based outcome rewards.
