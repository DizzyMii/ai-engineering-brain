---
tags: [snippet, domain/post-training, level/advanced]
aliases: [GRPO advantage, group-relative advantage, group-normalized advantage]
summary: "Group-relative advantage computation for GRPO from grouped rewards, plus the token-level clipped loss with a k3 KL term."
---

**What it does:** turns a `[num_prompts, G]` grid of sampled rewards into per-token advantages for [[Concept - GRPO and RL with Verifiable Rewards]], then applies a PPO-style clipped loss with a k3 KL-to-reference penalty — the update rule behind DeepSeek-R1's RL stage.
**Dependencies:** `torch>=2.1` only.
**Expected output:** for a group with mixed correct/incorrect completions, correct completions get positive advantage and incorrect ones negative, all completions of the *same* prompt sharing the group's mean/std; groups that are all-correct or all-wrong produce advantage ≈ 0 for every token in that group.

```python
import torch


def group_relative_advantage(rewards: torch.Tensor, eps: float = 1e-4, normalize_std: bool = True) -> torch.Tensor:
    """
    rewards: [num_prompts, G] — G sampled completions per prompt, one scalar reward each
              (verifier accuracy, format reward, or RM score).
    Returns: [num_prompts, G] advantage, one scalar per completion — no value/critic model needed.
    """
    group_mean = rewards.mean(dim=1, keepdim=True)
    if normalize_std:
        group_std = rewards.std(dim=1, keepdim=True)
        advantage = (rewards - group_mean) / (group_std + eps)
    else:
        # Dr.GRPO (Liu et al. 2025): drop std-normalization — dividing by std
        # over-weights low-variance (near-all-correct or near-all-wrong) groups.
        advantage = rewards - group_mean
    return advantage


def broadcast_advantage_to_tokens(advantage: torch.Tensor, completion_mask: torch.Tensor) -> torch.Tensor:
    """
    advantage:        [num_prompts, G] sequence-level scalar from group_relative_advantage.
    completion_mask:  [num_prompts, G, T] 1.0 on completion tokens, 0.0 elsewhere.
    Returns:          [num_prompts, G, T] the same scalar copied to every completion token —
                       GRPO has no per-token credit assignment, unlike PPO's GAE.
    """
    return advantage.unsqueeze(-1) * completion_mask


def grpo_token_loss(
    logp_new: torch.Tensor,       # [num_prompts, G, T] current policy log-probs of taken tokens
    logp_old: torch.Tensor,       # [num_prompts, G, T] log-probs at rollout time (sampling policy)
    logp_ref: torch.Tensor,       # [num_prompts, G, T] frozen reference log-probs
    advantage_tok: torch.Tensor,  # [num_prompts, G, T] from broadcast_advantage_to_tokens
    completion_mask: torch.Tensor,
    clip_eps: float = 0.2,
    kl_beta: float = 0.001,
):
    ratio = torch.exp(logp_new - logp_old)
    unclipped = ratio * advantage_tok
    clipped = torch.clamp(ratio, 1 - clip_eps, 1 + clip_eps) * advantage_tok
    policy_loss_tok = -torch.min(unclipped, clipped)

    # k3 estimator (Schulman): unbiased, low-variance, always >= 0 — unlike naive
    # log(pi/pi_ref), which can go negative and blow up variance.
    log_ratio_ref = logp_ref - logp_new
    kl_tok = torch.exp(log_ratio_ref) - log_ratio_ref - 1

    per_token_loss = policy_loss_tok + kl_beta * kl_tok
    # Average over unmasked (completion) tokens only, then over the batch.
    denom = completion_mask.sum(dim=-1).clamp(min=1)
    per_sequence_loss = (per_token_loss * completion_mask).sum(dim=-1) / denom
    return per_sequence_loss.mean()
```

## Why it's written this way

- **The group mean replaces a value network entirely.** `group_relative_advantage` never touches a critic — normalizing each reward against the mean (and optionally std) of its own group of `G` samples for the *same prompt* is what removes PPO's value model and its ~2x memory/compute overhead. This is GRPO's central trick (Shao et al. 2024): a low-variance baseline for free, at the cost of needing `G` rollouts per prompt instead of one.
- **Advantage is broadcast, not computed per-token.** `broadcast_advantage_to_tokens` copies one scalar to every completion token because GRPO — unlike [[Concept - PPO for Language Models]]'s GAE — has no per-token value estimate to differentiate credit within a sequence; every token of a good completion is reinforced equally.
- **The `eps` and `normalize_std` guards exist because of a real degenerate case.** When every sample in a group gets the same reward (all-correct on an easy prompt, or all-wrong on an unsolvable one), `group_std` is 0 and the advantage would be `0/0` without `eps`; the `normalize_std=False` path documents the Dr.GRPO finding that std-normalization itself introduces a length/difficulty bias by over-weighting low-variance groups — motivating dynamic sampling (drop degenerate groups) as the more principled fix, per [[Concept - Spurious Rewards and RLVR Failure Modes]] and the entropy-collapse literature.
- **The k3 KL estimator, not k1.** `kl_tok` uses `exp(log_ratio) - log_ratio - 1` rather than the naive `-log_ratio`, because k1 can be negative and high-variance while k3 is always ≥ 0 and unbiased — the same estimator choice documented in [[Concept - KL Divergence]] and used throughout RLHF. A negative KL penalty silently rewards drifting from the reference, which is exactly the failure mode a KL term exists to prevent.

## Connections

- [[Concept - GRPO and RL with Verifiable Rewards]] — the algorithm this snippet implements; read it for why group-relative advantages work as well as they do on verifiable-reward domains.
- [[Concept - PPO for Language Models]] — the clipped-surrogate loss and ratio computation here are lifted directly from PPO; GRPO's only structural change is the advantage source.
- [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]] — the `clip_eps` and `kl_beta` knobs in `grpo_token_loss` are exactly the levers that literature uses to fight entropy collapse (clip-higher, KL anchoring).
- [[Concept - Spurious Rewards and RLVR Failure Modes]] — the zero-variance-group degenerate case this snippet guards against is a special case of the broader finding that RLVR gains can be a mirage of base-model priors rather than the reward signal.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — this exact update rule, applied to math/code verifiers, is the mechanism behind DeepSeek-R1's emergent long chain-of-thought.
- [[Concept - Softmax]] — cross-domain (02) grounding for the `log_softmax`/log-prob machinery that produces `logp_new`, `logp_old`, and `logp_ref` upstream of this snippet.
- [[Concept - KL Divergence]] — cross-domain (01) grounding for why the k3 estimator is unbiased and why that property matters for a term added directly into a policy-gradient loss.
