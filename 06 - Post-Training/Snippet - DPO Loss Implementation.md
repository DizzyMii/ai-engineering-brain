---
tags: [snippet, domain/post-training, level/advanced]
aliases: [DPO loss, DPO training step]
summary: "PyTorch DPO loss from policy and reference log-probs: masked log-prob gather, beta log-ratio margin, and reward-accuracy metric."
---

**What it does:** computes the [[Concept - Direct Preference Optimization (DPO)]] loss for one batch of (chosen, rejected) pairs, given the policy and frozen reference models, and returns the loss plus a reward-accuracy diagnostic.
**Dependencies:** `torch>=2.1` (only). No trainer framework required — this is the loss function, not the training loop.
**Expected output:** for a batch where the policy already agrees with the preference labels more than the reference does, `reward_accuracy` should read above 0.5 and rise over training; a healthy run shows loss decreasing while `reward_accuracy` climbs toward 0.7–0.9+.

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

- **Reuses the SFT completion mask verbatim.** `gather_completion_logps` takes the exact `mask` tensor built for [[Concept - Loss Masking and Sequence Packing]] rather than re-deriving completion spans. Any drift between the mask used to train the reference checkpoint and the mask used here silently corrupts `ref_logratios` — DPO's correctness depends on policy and reference being scored under identical preprocessing.
- **Sum, not mean, over completion tokens.** Summing log-probs is standard DPO and is what makes the loss (implicitly) prefer shorter completions less and longer ones more — this is the length-bias mechanism (see [[Concept - Length Bias in Preference Optimization]]). Switching the `.sum(dim=-1)` in `gather_completion_logps` to a length-normalized mean turns this into SimPO's reward, documented in [[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]]. Expose it as a flag if you need to A/B the two.
- **`chosen_reward`/`rejected_reward` are detached.** They are diagnostics, not part of the loss graph — DPO's implicit reward is a derived quantity (β times the policy/reference log-ratio), and computing it without `.detach()` would silently double-count gradient through the metric path in some autograd setups. `reward_accuracy` is the single most useful training-health number to log: it should climb monotonically even when the raw loss value is noisy.
- **`F.logsigmoid` instead of `torch.log(torch.sigmoid(...))`.** The naive composition underflows to `-inf` for very negative margins; `logsigmoid` is numerically stable across the full range the [[Concept - KL Divergence]]-derived margin can take, especially early in training when `pi_logratios` and `ref_logratios` are close and the argument can swing widely with a high β.

## Connections

- [[Concept - Direct Preference Optimization (DPO)]] — the derivation this loss implements; read it first for why the RM cancels out of the Bradley-Terry loss.
- [[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]] — SimPO's length-normalized variant and IPO's squared-loss variant are one-line changes to this same function.
- [[Concept - Loss Masking and Sequence Packing]] — the completion-mask mechanics this snippet assumes are already correct; a masking bug here corrupts every DPO run silently.
- [[Snippet - Loss Masking a Chat Dataset]] — the upstream snippet that produces the `chosen_mask`/`rejected_mask` tensors consumed here.
- [[Concept - Softmax]] — cross-domain (02) grounding for `F.log_softmax` and why `logsigmoid` needs the same log-space stability treatment.
- [[Concept - KL Divergence]] — cross-domain (01) grounding for the KL-regularized-optimum derivation that makes `beta * log-ratio` an implicit reward in the first place.
- [[Concept - Length Bias in Preference Optimization]] — the failure mode directly caused by the sum-vs-mean choice called out above.
