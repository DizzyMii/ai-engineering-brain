---
tags: [snippet, domain/post-training, level/advanced]
aliases: [DPO loss, DPO training step]
summary: "PyTorch DPO loss from policy and reference log-probs: masked log-prob gather, beta log-ratio margin, and reward-accuracy metric."
---

**What it does:** computes the [[Concept - Direct Preference Optimization (DPO)]] loss for one batch of (chosen, rejected) pairs from the policy and the frozen reference model. Returns the loss and a reward-accuracy diagnostic.
**Dependencies:** `torch>=2.1`, nothing else. No trainer framework; this is the loss function, and the training loop is yours.
**Expected output:** if the policy already agrees with the preference labels more than the reference does, `reward_accuracy` reads above 0.5 and rises over training. In a healthy run the loss falls while `reward_accuracy` climbs toward 0.7–0.9+.

```python
import torch
import torch.nn.functional as F


def gather_completion_logps(logits: torch.Tensor, labels: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Sum log p(label_t | context) over completion tokens only.

    logits: [B, T, V] model output (policy or reference), already shifted so
            logits[:, t] predicts labels[:, t].
    labels: [B, T] token ids (arbitrary at masked positions).
    mask:   [B, T] 1.0 on completion tokens (assistant turn + EOS), 0.0 elsewhere.
            Reuse the exact mask built for SFT loss masking — see
            [[Snippet - Loss Masking a Chat Dataset]].
    """
    log_probs = F.log_softmax(logits, dim=-1)                    # [B, T, V]
    token_logp = torch.gather(log_probs, dim=2, index=labels.unsqueeze(-1)).squeeze(-1)  # [B, T]
    return (token_logp * mask).sum(dim=-1)                        # [B] — sum, not mean (see note below)


def dpo_loss(
    policy_chosen_logits: torch.Tensor,
    policy_rejected_logits: torch.Tensor,
    ref_chosen_logits: torch.Tensor,
    ref_rejected_logits: torch.Tensor,
    chosen_labels: torch.Tensor,
    rejected_labels: torch.Tensor,
    chosen_mask: torch.Tensor,
    rejected_mask: torch.Tensor,
    beta: float = 0.1,
    label_smoothing: float = 0.0,
):
    policy_chosen_logps = gather_completion_logps(policy_chosen_logits, chosen_labels, chosen_mask)
    policy_rejected_logps = gather_completion_logps(policy_rejected_logits, rejected_labels, rejected_mask)
    with torch.no_grad():
        ref_chosen_logps = gather_completion_logps(ref_chosen_logits, chosen_labels, chosen_mask)
        ref_rejected_logps = gather_completion_logps(ref_rejected_logits, rejected_labels, rejected_mask)

    pi_logratios = policy_chosen_logps - policy_rejected_logps
    ref_logratios = ref_chosen_logps - ref_rejected_logps
    logits = beta * (pi_logratios - ref_logratios)                # the implicit reward margin

    if label_smoothing > 0.0:
        # cDPO: tolerate a fraction `label_smoothing` of flipped/noisy preference labels.
        loss = (
            -F.logsigmoid(logits) * (1 - label_smoothing)
            - F.logsigmoid(-logits) * label_smoothing
        )
    else:
        loss = -F.logsigmoid(logits)

    # Metrics only — detach so they don't participate in backward.
    chosen_reward = (beta * (policy_chosen_logps - ref_chosen_logps)).detach()
    rejected_reward = (beta * (policy_rejected_logps - ref_rejected_logps)).detach()
    reward_accuracy = (chosen_reward > rejected_reward).float().mean()
    reward_margin = (chosen_reward - rejected_reward).mean()

    return loss.mean(), {
        "reward_accuracy": reward_accuracy.item(),
        "reward_margin": reward_margin.item(),
        "chosen_reward_mean": chosen_reward.mean().item(),
        "rejected_reward_mean": rejected_reward.mean().item(),
    }
```

## Why it's written this way

- **It reuses the SFT completion mask as-is.** `gather_completion_logps` takes the same `mask` tensor built for [[Concept - Loss Masking and Sequence Packing]] instead of re-deriving completion spans. If the mask used to train the reference checkpoint drifts from the one used here, `ref_logratios` is silently wrong. DPO only works when policy and reference are scored under identical preprocessing.
- **Sum over completion tokens, not mean.** Summing log-probs is standard DPO. It's also why the loss implicitly prefers shorter completions less and longer ones more, which is the length-bias mechanism in [[Concept - Length Bias in Preference Optimization]]. Change the `.sum(dim=-1)` in `gather_completion_logps` to a length-normalized mean and you get SimPO's reward ([[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]]). Make it a flag if you need to A/B the two.
- **`chosen_reward` and `rejected_reward` are detached.** They're diagnostics and stay out of the loss graph. DPO's implicit reward is derived (β times the policy/reference log-ratio), and without `.detach()` some autograd setups would silently double-count gradient through the metric path. Of everything you can log, `reward_accuracy` tells you the most about training health: it should climb monotonically even when the raw loss is noisy.
- **`F.logsigmoid` instead of `torch.log(torch.sigmoid(...))`.** The naive version underflows to `-inf` for very negative margins. `logsigmoid` stays stable across the whole range the [[Concept - KL Divergence]]-derived margin can take. That matters most early in training, when `pi_logratios` and `ref_logratios` are close and a high β can make the argument swing widely.

## Connections

- [[Concept - Direct Preference Optimization (DPO)]] — the derivation this loss implements; read it first for why the RM cancels out of the Bradley-Terry loss.
- [[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]] — SimPO's length-normalized variant and IPO's squared-loss variant are one-line changes to this same function.
- [[Concept - Loss Masking and Sequence Packing]] — the completion-mask mechanics this snippet assumes are already correct; a masking bug here corrupts every DPO run silently.
- [[Snippet - Loss Masking a Chat Dataset]] — the upstream snippet that produces the `chosen_mask`/`rejected_mask` tensors consumed here.
- [[Concept - Softmax]] — cross-domain (02) grounding for `F.log_softmax` and why `logsigmoid` needs the same log-space stability treatment.
- [[Concept - KL Divergence]] — cross-domain (01) grounding for the KL-regularized-optimum derivation that makes `beta * log-ratio` an implicit reward in the first place.
- [[Concept - Length Bias in Preference Optimization]] — the failure mode directly caused by the sum-vs-mean choice called out above.
