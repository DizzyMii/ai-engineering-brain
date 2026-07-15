---
tags: [concept, domain/post-training, level/core]
aliases: [RM, reward modeling, Bradley-Terry reward model]
summary: "Training a scalar reward model on pairwise human preferences via the Bradley-Terry model — the RM head, data, calibration, and biases it inherits."
---

> **One-paragraph hook:** A reward model turns a pretrained language model into a scalar preference scorer: given a prompt and a candidate response, it outputs a single number meant to track how much a human would like that response. It is the learned proxy objective that RLHF's RL stage optimizes against, and its quality — or lack of it — sets a hard ceiling on how far preference optimization can push a policy before the policy starts gaming the score instead of improving.

## The mechanism

The standard reward model is trained with the Bradley-Terry model of pairwise comparison: given a prompt $x$ and two candidate completions $y_w$ (chosen/preferred) and $y_l$ (rejected), the RM $r_\theta$ is trained so that

$$P(y_w \succ y_l \mid x) = \sigma\big(r_\theta(x, y_w) - r_\theta(x, y_l)\big)$$

with training loss the negative log-likelihood of the observed preference — the same [[Concept - Entropy and Cross-Entropy|cross-entropy]] form used everywhere else in the stack, just applied to a two-outcome "which response wins" distribution instead of a vocabulary:

$$\mathcal{L}(\theta) = -\log \sigma\big(r_\theta(x, y_w) - r_\theta(x, y_l)\big)$$

Only the *difference* between the two rewards appears in the loss, which means the reward function is shift-invariant — add any constant to $r_\theta$ everywhere and the loss is unchanged. This is why RM outputs must be normalized (subtract the batch mean, or z-score) before use downstream: raw reward magnitudes carry no meaning on their own, only relative ordering does.

Architecture: initialize the RM from the [[Concept - Supervised Fine-Tuning (SFT)]] checkpoint — same backbone, same tokenizer, same distribution of text it is scoring — then replace the vocabulary-sized [[Concept - Softmax]] LM head with a single linear layer reading the final-token hidden state, producing one scalar per sequence. Reusing the SFT backbone means the RM starts already fluent on the target domain; InstructGPT (Ouyang et al. 2022) used a 6B-parameter RM, comparable to or larger than some of the policy sizes it trained against, reflecting that reward modeling is itself a hard prediction problem, not a lightweight add-on.

## In practice

Data: labelers see $k$ completions per prompt (InstructGPT ranked 4–9 completions per prompt) and produce a ranking, which is expanded into $\binom{k}{2}$ pairwise comparisons for training — a $k=9$ ranking yields 36 pairs from one labeling pass, which is why ranking is more label-efficient than collecting pure pairwise comparisons directly. Public preference datasets anchor scale expectations: Anthropic's HH-RLHF has roughly 170K pairs; OpenAI's summarize-from-feedback dataset is a similarly-scaled reference point.

Evaluation: RewardBench (Lambert et al. 2024) is the standard held-out benchmark for RM quality, reporting pairwise accuracy across category slices (chat, safety, reasoning). Typical held-out pairwise accuracy runs roughly 65–75%, and that number is ceilinged by human-human label agreement, which sits in a similar 65–75% band — preference labeling is intrinsically noisy, and an RM cannot exceed the reliability of the labels it was trained on.

Reward scale drift and miscalibration off-distribution are the seed of [[Concept - Reward Hacking]]: an RM is fit on comparisons drawn from roughly the SFT policy's output distribution, and as a downstream RL policy moves away from that distribution during training (see [[Deep Dive - RLHF End to End]]), it enters regions the RM never saw labeled examples for and can assign confidently wrong scores. RM ensembles — training several RMs on different data splits or seeds and taking a conservative aggregate — measurably reduce overoptimization (Coste et al. 2023), and ensemble *disagreement* is itself a useful out-of-distribution flag: when ensemble members diverge sharply on a completion, that is a signal the policy has wandered somewhere the RM's training data did not cover.

Alternatives to the pointwise Bradley-Terry RM: pointwise RMs that score a single response in isolation (cheaper data collection, noisier, since labelers calibrate against nothing); [[Concept - Process and Outcome Reward Models|process reward models]] that score each step of a reasoning chain rather than one scalar for the whole response; generative/LLM-as-judge RMs that use a prompted [[Concept - LLM-as-Judge]] model as the scorer instead of a trained scalar head; and [[Concept - Direct Preference Optimization (DPO)]]'s implicit reward, which never materializes an explicit RM at all — the policy's own log-probability ratio against the reference model *is* the reward, recovered in closed form from the same Bradley-Terry assumption.

## Failure modes

The RM inherits every bias present in its labelers' judgments, and because it is a single scalar, those biases become directly optimizable targets for whatever policy is later trained against it. The two best-documented: **length bias** (labelers systematically rate longer responses higher independent of quality, so the RM learns length as a proxy for thoroughness — see [[Concept - Length Bias in Preference Optimization]]) and **sycophancy/agreement bias** (labelers rate responses that agree with or flatter the stated position more highly, teaching the RM, and downstream the policy, to hedge toward agreement rather than correctness). Markdown/formatting exploitation (bullet points, bold text, headers) is a close third: labelers under time pressure pattern-match "looks organized" to "is good."

Detection: compare RM score trajectories against a held-out human or gold-RM win rate during downstream RL training — an RM-score-vs-win-rate divergence (RM score climbing while actual quality plateaus or falls) is the signature of the policy having found and started exploiting a specific RM weakness.

## The non-obvious

The RM's job is not to be an accurate value function in any absolute sense — it is shift-invariant by construction and only ever compared to itself within a batch. What actually matters in practice is how the RM behaves *off the distribution it was trained on*, because that is exactly the region a downstream RL policy explores as soon as it starts improving. A reward model can look excellent on a held-out set drawn from the same distribution as its training pairs (high RewardBench accuracy) and still be a poor RL objective, because policy improvement is precisely a search process that pushes into out-of-distribution territory the RM was never calibrated for. This is why practitioners treat static-benchmark RM accuracy as necessary but nowhere near sufficient, and why iterative/online RM refresh — periodically relabeling fresh on-policy samples from the improving policy and retraining the RM on them — is a standard production mitigation rather than an optional extra.

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
