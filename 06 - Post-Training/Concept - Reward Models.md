---
tags: [concept, domain/post-training, level/core]
aliases: [RM, reward modeling, Bradley-Terry reward model]
summary: "Training a scalar reward model on pairwise human preferences via the Bradley-Terry model — the RM head, data, calibration, and biases it inherits."
---

> **One-paragraph hook:** A reward model turns a pretrained language model into a scalar preference scorer. Give it a prompt and a candidate response and it outputs one number meant to track how much a human would like that response. RLHF's RL stage optimizes against this learned proxy, so its quality sets a hard ceiling on how far preference optimization can push a policy before the policy starts gaming the score instead of improving.

## The mechanism

The standard RM is trained with the Bradley-Terry model of pairwise comparison. Given a prompt $x$ and two completions $y_w$ (chosen/preferred) and $y_l$ (rejected), the RM $r_\theta$ is trained so that

$$P(y_w \succ y_l \mid x) = \sigma\big(r_\theta(x, y_w) - r_\theta(x, y_l)\big)$$

The training loss is the negative log-likelihood of the observed preference. It's the same [[Concept - Entropy and Cross-Entropy|cross-entropy]] form used everywhere else in the stack, applied to a two-outcome "which response wins" distribution instead of a vocabulary:

$$\mathcal{L}(\theta) = -\log \sigma\big(r_\theta(x, y_w) - r_\theta(x, y_l)\big)$$

Only the *difference* between the two rewards appears in the loss, so the reward function is shift-invariant: add any constant to $r_\theta$ everywhere and the loss doesn't change. That's why RM outputs have to be normalized (subtract the batch mean, or z-score) before use downstream. Raw reward magnitudes mean nothing on their own. Only the ordering does.

Architecture: initialize the RM from the [[Concept - Supervised Fine-Tuning (SFT)]] checkpoint, so it has the same backbone, the same tokenizer, and the same distribution of text it'll be scoring. Then swap the vocabulary-sized [[Concept - Softmax]] LM head for a single linear layer that reads the final-token hidden state and produces one scalar per sequence. Reusing the SFT backbone means the RM starts out fluent in the target domain. InstructGPT (Ouyang et al. 2022) used a 6B-parameter RM, comparable to or larger than some of the policies it trained against. Reward modeling is a hard prediction problem in its own right, not a lightweight add-on.

## In practice

Data: labelers see $k$ completions per prompt (InstructGPT ranked 4–9 per prompt) and rank them. The ranking expands into $\binom{k}{2}$ pairwise comparisons for training, so a $k=9$ ranking yields 36 pairs from one labeling pass. That makes ranking more label-efficient than collecting pairwise comparisons directly. For scale, Anthropic's HH-RLHF has roughly 170K pairs, and OpenAI's summarize-from-feedback dataset is a similarly sized reference point.

Evaluation: RewardBench (Lambert et al. 2024) is the standard held-out benchmark for RM quality. It reports pairwise accuracy across category slices (chat, safety, reasoning). Typical held-out pairwise accuracy runs roughly 65–75%. Human-human label agreement sits in a similar 65–75% band and caps it: preference labels are intrinsically noisy, and an RM can't be more reliable than the labels it learned from.

Reward scale drift and off-distribution miscalibration are the seed of [[Concept - Reward Hacking]]. An RM is fit on comparisons drawn from roughly the SFT policy's output distribution. As a downstream RL policy moves away from that distribution during training (see [[Deep Dive - RLHF End to End]]), it reaches regions the RM never saw labeled examples for, and the RM can assign confidently wrong scores there. RM ensembles, several RMs trained on different data splits or seeds with a conservative aggregate, measurably reduce overoptimization (Coste et al. 2023). Ensemble *disagreement* is also a useful out-of-distribution flag. When members diverge sharply on a completion, the policy has probably wandered somewhere the RM's training data didn't cover.

Alternatives to the pairwise Bradley-Terry RM:
- Pointwise RMs that score one response in isolation. Data is cheaper to collect but noisier, since labelers have nothing to calibrate against.
- [[Concept - Process and Outcome Reward Models|Process reward models]], which score each step of a reasoning chain instead of giving one scalar for the whole response.
- Generative/LLM-as-judge RMs, which use a prompted [[Concept - LLM-as-Judge]] model as the scorer in place of a trained scalar head.
- [[Concept - Direct Preference Optimization (DPO)]]'s implicit reward, which never materializes an explicit RM. The policy's own log-probability ratio against the reference model *is* the reward, recovered in closed form from the same Bradley-Terry assumption.

## Failure modes

The RM inherits every bias in its labelers' judgments. Because it outputs a single scalar, those biases become directly optimizable targets for any policy later trained against it. The two best documented:
- **Length bias.** Labelers systematically rate longer responses higher regardless of quality, so the RM learns length as a proxy for thoroughness. See [[Concept - Length Bias in Preference Optimization]].
- **Sycophancy/agreement bias.** Labelers rate responses that agree with or flatter the stated position more highly. That teaches the RM, and downstream the policy, to hedge toward agreement over correctness.

Markdown/formatting exploitation (bullet points, bold text, headers) is a close third. Labelers under time pressure pattern-match "looks organized" to "is good."

To detect it, compare RM score trajectories against a held-out human or gold-RM win rate during downstream RL training. RM score climbing while actual quality plateaus or falls is the signature of a policy that has found a specific RM weakness and is exploiting it.

## The non-obvious

An RM isn't trying to be an accurate value function in any absolute sense. It's shift-invariant by construction and only ever compared against itself within a batch. What matters in practice is how it behaves *off the distribution it was trained on*, since that's the region a downstream RL policy explores as soon as it starts improving. An RM can look excellent on a held-out set from the same distribution as its training pairs (high RewardBench accuracy) and still be a poor RL objective, because policy improvement is a search process that pushes into out-of-distribution territory the RM was never calibrated for. So practitioners treat static-benchmark RM accuracy as necessary but nowhere near sufficient. Iterative/online RM refresh, periodically relabeling fresh on-policy samples from the improving policy and retraining the RM on them, is a standard production mitigation and not an optional extra.

## Connections

- [[Deep Dive - RLHF End to End]] — the pipeline stage where the RM's scalar output becomes the reward signal for PPO.
- [[Concept - Softmax]] — the vocabulary-sized head the RM's linear scalar layer replaces when repurposing an LM backbone.
- [[Concept - Reward Hacking]] — the downstream pathology that RM miscalibration off-distribution directly causes.
- [[Concept - Direct Preference Optimization (DPO)]] — the algorithm that recovers the same Bradley-Terry objective without ever materializing an explicit RM.
- [[Concept - LLM-as-Judge]] — the prompted-model alternative to a trained scalar RM, used both for RL rewards and for evaluation.
- [[Concept - Length Bias in Preference Optimization]] — the single most common bias an RM inherits from its labelers.
- [[Concept - Process and Outcome Reward Models]] — the extension from one scalar per full response to step-level reward signals.
- [[Concept - Entropy and Cross-Entropy]] — the cross-entropy form underlying the Bradley-Terry negative log-likelihood loss.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the checkpoint the RM is initialized from, which sets its starting output distribution.

## Sources

- Ouyang et al. (2022) — InstructGPT. Establishes the SFT-initialized 6B RM trained on 4–9-way rankings.
- Lambert et al. (2024) — "RewardBench: Evaluating Reward Models for Language Modeling." The standard RM evaluation suite.
- Coste et al. (2023) — "Reward Model Ensembles Help Mitigate Overoptimization." RM ensembling as a mitigation against reward hacking.
