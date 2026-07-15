---
tags: [concept, domain/post-training, level/frontier]
aliases: [PRM, ORM, process reward model, outcome reward model, process supervision]
summary: "Scoring a whole answer (ORM) versus scoring every reasoning step (PRM), and why RLVR at scale mostly displaced PRMs anyway."
---
> **One-paragraph hook:** Once models started producing long chains of reasoning, a natural question became where to attach the reward — only to the final answer, or to every intermediate step? Process reward models promised denser signal and better credit assignment for long chain-of-thought; by 2025 the field's flagship reasoning system tried them, found them unstable and hackable at scale, and shipped without them. Understanding why is the fastest way to understand what [[Concept - GRPO and RL with Verifiable Rewards]] actually buys you.

## The mechanism
An **outcome reward model (ORM)** assigns one scalar to a completed trajectory: correct/incorrect against a verifier, or a learned score trained the same way as a standard [[Concept - Reward Models]] — Bradley-Terry over pairwise comparisons, just applied to the whole answer.

A **process reward model (PRM)** decomposes a chain-of-thought $y = (s_1, \dots, s_n)$ into steps and assigns a reward $r_i = \text{PRM}(x, s_1, \dots, s_i)$ to each one. Lightman et al. 2023 ("Let's Verify Step by Step," OpenAI) trained a PRM on PRM800K, ~800K human step-level labels (positive/neutral/negative), with a per-step binary cross-entropy loss:

$$\mathcal{L} = -\sum_i \big[\, y_i \log p_i + (1-y_i)\log(1-p_i) \,\big], \quad p_i = \text{PRM}(x, s_1{:}i)$$

Human labeling doesn't scale, so Wang et al. 2023 (Math-Shepherd) automated it: from step $s_i$, run $k$ Monte Carlo rollouts to a final answer; label the step's soft target as the fraction of rollouts that reach the correct answer (or threshold it into a hard 0/1 label). A step is "good" if it's still on a path that plausibly resolves correctly, whether or not a human ever reads it.

Both PRMs and ORMs are consumed the same two ways: as a **verifier** at inference time — score $N$ sampled solutions (min-over-steps, product-over-steps, or last-step score) and pick the best, or guide a tree/MCTS-style search that prunes bad branches early — or as a **reward signal during RL**, where a PRM's per-step reward is meant to ease credit assignment relative to a single terminal reward.

## In practice
Lightman et al.'s headline result: a PRM-based verifier beats both an ORM-based verifier and majority voting on MATH at the same sample budget — the empirical case for "process supervision beats outcome supervision," at least for verification. Math-Shepherd showed the same qualitative win without human labels, using MC-estimated soft labels for both reranking and as an RL reward signal.

The practical use case that survived best is inference-time reranking (best-of-N with a PRM), not training-time RL reward. That distinction matters: as a one-shot scorer over $N$ already-sampled completions, a PRM is hard to game because there's no gradient pressure adapting the policy against it. As a live RL reward, it becomes exactly the kind of proxy that [[Concept - Reward Hacking]] describes — a differentiable target under sustained optimization pressure.

## Failure modes
PRMs inherit every failure mode of ordinary reward models and add a bigger attack surface: instead of one place to hack (the final answer), there are $n$ places per trajectory. **PRM reward hacking** looks like plausible-but-wrong steps scored high — fluent, confident-sounding intermediate reasoning that a step-level scorer rates well regardless of correctness. **MC label noise** is real at low $k$: Math-Shepherd's soft labels have high variance when few rollouts are used, and the PRM ends up fitting noise. **Distribution shift** compounds over an RL run: a PRM trained on one policy's outputs starts misjudging a policy that has moved away from that distribution, the same overoptimization dynamic that afflicts any [[Concept - Reward Models]] under a drifting policy. DeepSeek's own report ([[Breakdown - DeepSeek-R1]]) is the most concrete data point here: they explicitly tried PRM-guided training and MCTS-style search and dropped both, citing instability and hackability at the scale of their RL runs.

## The non-obvious
The "denser signal helps" intuition partially breaks down once you have a strong outcome-only RLVR signal. [[Concept - GRPO and RL with Verifiable Rewards]]'s group-relative baseline already provides workable credit assignment without a value network or a per-step critic, so the marginal benefit of process supervision shrinks exactly as its cost (a new, gameable reward surface) grows. The folklore that has accumulated since: PRMs are a solid *verifier* — a passive judge over already-generated candidates — but a fragile *trainer* — an active target that gradient descent will find cracks in over enough RL steps. Treat "should I add a PRM" and "should I add a PRM as an RL reward" as two different, differently-risky questions.

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
