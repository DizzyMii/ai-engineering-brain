---
tags: [deep-dive, domain/post-training, level/advanced]
aliases: [RLHF, Reinforcement Learning from Human Feedback]
summary: "The SFT, reward-model, PPO pipeline behind InstructGPT and ChatGPT: four resident models, a KL-regularized reward, and real instability."
---

> **One-paragraph hook:** RLHF is the three-stage pipeline that turned raw pretrained-model rambling into ChatGPT-shaped assistants: clone demonstrations with supervised learning, fit a scalar reward model on human comparisons, then run reinforcement learning against that reward while a KL penalty keeps the policy from wandering off into gibberish that fools the reward model. It is the most expensive and least stable stage of post-training — four models resident in GPU memory, an on-policy RL loop against a non-stationary learned objective — which is exactly why DPO and GRPO exist as surgical removals of specific pieces of it. You cannot reason about what those successors trade away without first tracing the full loop.

## The mechanism

Stage 1 is [[Concept - Supervised Fine-Tuning (SFT)]]: behavior-clone a pretrained base model on curated (prompt, response) demonstrations to get a policy $\pi_{SFT}$ that at least follows instructions in the right format. Stage 2 trains a [[Concept - Reward Models|reward model]] $r_\phi(x,y)$ by fitting a Bradley-Terry model to pairwise human comparisons: $P(y_w \succ y_l) = \sigma(r_\phi(x,y_w) - r_\phi(x,y_l))$, minimizing $-\log\sigma(r_w - r_l)$ over chosen/rejected pairs. Stage 3 runs [[Concept - PPO for Language Models|PPO]] to maximize

$$\mathbb{E}_{x \sim D,\, y \sim \pi_\theta}\big[\, r_\phi(x,y) \,\big] - \beta \cdot \text{KL}\big(\pi_\theta(\cdot|x) \,\|\, \pi_{ref}(\cdot|x)\big)$$

where $\pi_{ref}$ is a frozen copy of $\pi_{SFT}$. The [[Concept - KL Divergence]] term is not a regularizer bolted on as an afterthought — without it, PPO discovers that the fastest way to raise $r_\phi$ is to leave the distribution the reward model was trained on, where $r_\phi$'s scores stop meaning anything. Scheduling and estimating this term correctly is important enough to be its own note: [[Concept - KL Control in RLHF]].

In implementation the KL term is folded directly into the per-token reward rather than applied as a separate loss: $r_t = -\beta \log(\pi_\theta(y_t|\cdot)/\pi_{ref}(y_t|\cdot))$ for every non-terminal token, plus the reward model's scalar $r_\phi(x,y)$ added at the final (EOS) token. This gives PPO a dense, per-token reward signal instead of one scalar at the end of a possibly-800-token sequence, which matters for [[Concept - PPO for Language Models|Generalized Advantage Estimation]] to have anything to work with along the way.

## Architecture / walkthrough

```mermaid
flowchart TB
    subgraph S1["Stage 1 — SFT"]
        Base["Pretrained base model"] --> SFTtrain["Behavior-clone on demonstrations"]
        SFTtrain --> PiSFT["pi_SFT"]
    end

    subgraph S2["Stage 2 — Reward Model"]
        PiSFT -->|init from| RMinit["RM backbone"]
        Prefs["Pairwise preference data\n(chosen, rejected)"] --> BTloss["Bradley-Terry loss"]
        RMinit --> BTloss
        BTloss --> RM["Reward model r_phi(x,y)"]
    end

    subgraph S3["Stage 3 — PPO RL loop"]
        PiSFT -->|trainable copy| Policy["Policy pi_theta"]
        PiSFT -.frozen copy.-> Ref["Reference pi_ref"]
        Policy --> Rollout["Sample y ~ pi_theta(x)"]
        Rollout --> RM
        Rollout --> Ref
        RM -->|scalar at EOS| RewardAssemble["Per-token reward:\n-beta*KL(policy||ref) + RM at EOS"]
        Ref --> RewardAssemble
        RewardAssemble --> GAE["Value head + GAE advantages"]
        GAE --> PPOUpdate["Clipped PPO update"]
        PPOUpdate --> Policy
        PPOUpdate -->|repeat rollouts| Rollout
    end
```

Four distinct models are resident simultaneously in Stage 3: the trainable policy, the frozen reference (for the KL term), the frozen reward model (to score rollouts), and a trained value/critic head (to compute advantages) — roughly 4x the memory of a single model of that size, which is the single biggest reason RLHF is expensive relative to SFT or DPO (see [[Reference - Memory Math for Transformers]] for the per-parameter accounting, and [[Concept - Data Parallelism and ZeRO]] for how that memory gets sharded across a training cluster). The loop itself is: sample rollouts from the current policy (this generation step dominates wall-clock time, since it is autoregressive decoding one token at a time — see [[Concept - Sampling and Decoding Parameters]] for the knobs that control it), score each rollout with the reward model, assemble the per-token reward above, compute GAE advantages, take 1–4 PPO epochs over the batch, and repeat. Because generation is the bottleneck, production RLHF stacks disaggregate a fast inference engine like [[Breakdown - vLLM]] from the training process rather than generating with the training framework's own forward pass — colocated setups pay for an idle sampler during backward passes and an idle trainer during generation.

## In practice

InstructGPT (Ouyang et al. 2022) is the reference implementation: a 1.3B-parameter RLHF'd model was preferred by human labelers over the 175B GPT-3 base model in head-to-head comparisons — the headline result that made RLHF the default post-training recipe industry-wide. Its reward model was itself 6B parameters, larger than some of the policies it scored, because reward modeling from limited comparison data benefits from capacity the way any small-data supervised task does. Labelers ranked 4–9 completions per prompt, which expands combinatorially into $\binom{k}{2}$ pairwise comparisons for training the RM. The lineage runs through Christiano et al. (2017) — "Deep reinforcement learning from human preferences," which established the reward-model-from-comparisons framing outside of language — and Stiennon et al. (2020), which applied the same recipe to summarization and is the direct ancestor of the InstructGPT pipeline. Anthropic's HH-RLHF (Bai et al. 2022) extended the target from pure helpfulness to helpfulness-plus-harmlessness and introduced "online iterated RLHF": periodically retrain the reward model on fresh on-policy comparisons rather than training it once and freezing it, which slows the rate at which the policy can drift into regions the RM was never trained to score.

Open infrastructure for running this loop includes TRL, TRLX, OpenRLHF, veRL, and NeMo-Aligner — all of them structured around the same four-model resident-memory problem and the generate/score/update loop above, differing mainly in how aggressively they disaggregate or colocate the sampler and trainer, and how they shard the value and reward models across GPUs.

## Failure modes

The dominant failure mode is [[Concept - Reward Hacking]]: reward climbs steadily while a held-out human or LLM-judge win rate stalls or falls, because the policy has found regions of output space where $r_\phi$ is miscalibrated rather than regions of genuinely better output. This is a distribution-shift phenomenon by construction — the reward model was fit on a static dataset, and PPO's whole job is to search for high-reward regions, which inevitably includes regions outside that dataset's support. A second class of failure is outright training instability: value-function divergence, advantage explosion, or KL blowup that collapses the policy into gibberish or a single repeated phrase (entropy collapse). Because these two families of failure (silent reward hacking vs. loud instability) have different symptoms, different root causes, and different fixes, they are cataloged separately and symptom-first in [[Gotchas - RLHF Training Instabilities]], with the accompanying diagnostic procedure in [[Playbook - Debugging an RLHF Run]].

## The non-obvious

The three stages are not equally load-bearing for capability — SFT sets the ceiling on format and the reference distribution everything else is anchored to, and RL mostly reallocates probability mass the SFT policy already assigns non-trivial likelihood to, rather than teaching genuinely new behavior. This is precisely why DPO, GRPO, and rejection sampling — none of which run true on-policy RL against a learned scalar reward — can recover most of RLHF's practical benefit at a fraction of the cost: the hard, expensive part (a live rollout loop against a non-stationary reward with four models in memory) buys real but marginal gains over simpler alternatives for most chat-alignment use cases, and only clearly earns its cost when the target behavior requires the policy to be pulled into regions its SFT and preference data never sampled from in the first place.

## Evolution

[[Concept - Direct Preference Optimization (DPO)]] (2023) collapsed stages 2 and 3 into a single closed-form loss, removing the reward model and the RL loop entirely by proving the KL-regularized optimum has an implicit reward expressible in terms of the policy itself. [[Concept - GRPO and RL with Verifiable Rewards|GRPO]] (Shao et al. 2024, DeepSeekMath) kept the RL loop but removed the value/critic model, replacing GAE with a group-normalized advantage computed from multiple samples per prompt — roughly halving PPO's memory footprint. RLVR removed the learned reward model itself wherever a programmatic verifier (unit tests, exact-match math answers) can substitute for human preference labels, closing the loop that [[Concept - Constitutional AI and RLAIF]] had already partly opened by substituting AI-generated preference labels for human ones. That RLVR line continues directly into [[Concept - Reasoning Training and Long Chain-of-Thought]], where DeepSeek-R1 showed pure RL against verifiable rewards — no SFT warm-start required — can produce emergent long chain-of-thought reasoning. RLHF's enduring lesson survives across all of these descendants: preferences carry information demonstrations cannot express. Its enduring pain — instability, cost, and reward hacking — is exactly what each successor is a targeted attempt to cut away.

## Connections

- [[Concept - Supervised Fine-Tuning (SFT)]] — Stage 1; the policy initialization and frozen reference that every later stage is anchored to.
- [[Concept - Reward Models]] — Stage 2; the Bradley-Terry objective that turns human comparisons into the scalar signal PPO optimizes.
- [[Concept - PPO for Language Models]] — Stage 3's algorithm; the token-level MDP, clipped surrogate, and value head that make the RL loop work.
- [[Concept - KL Control in RLHF]] — governs the single most important dial in the objective; too low and the policy hacks, too high and nothing improves.
- [[Concept - Reward Hacking]] — the central pathology RLHF is vulnerable to precisely because it optimizes a learned proxy under distribution shift.
- [[Reference - Memory Math for Transformers]] — the per-parameter accounting behind why four resident models costs roughly 4x a single model's memory.
- [[Breakdown - vLLM]] — the fast sampler production RLHF stacks disaggregate from the trainer to avoid generation-bound idle time.
- [[Concept - Direct Preference Optimization (DPO)]] — the direct successor that collapses stages 2 and 3 into one offline loss.
- [[Concept - KL Divergence]] — the general-purpose divergence measure the KL-regularized objective is built from.
- [[Concept - Data Parallelism and ZeRO]] — how the four-model memory footprint gets sharded across a training cluster in practice.
- [[Concept - GRPO and RL with Verifiable Rewards]] — the successor that keeps the RL loop but removes the value model.
- [[Concept - Constitutional AI and RLAIF]] — replaces human preference labels with AI-generated ones inside the same three-stage skeleton.
- [[Concept - Sampling and Decoding Parameters]] — governs the rollout-generation step that dominates RLHF's wall-clock cost.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — where the RLVR line this pipeline evolved into produces emergent reasoning behavior.
- [[Gotchas - RLHF Training Instabilities]] — the symptom-first catalog of the reward-hacking and instability failures this pipeline is prone to.
- [[Playbook - Debugging an RLHF Run]] — the step-by-step procedure for diagnosing which of this pipeline's three stages is misbehaving.

## Sources

- Ouyang et al. (2022) — "Training language models to follow instructions with human feedback" (InstructGPT). The reference three-stage RLHF pipeline; the 1.3B-beats-175B result.
- Christiano et al. (2017) — "Deep reinforcement learning from human preferences." Establishes learning a reward model from pairwise comparisons.
- Stiennon et al. (2020) — "Learning to summarize from human feedback." Direct ancestor of the InstructGPT pipeline, applied to summarization.
- Bai et al. (2022) — "Training a Helpful and Harmless Assistant with RLHF" (Anthropic HH). Adds harmlessness and online iterated RLHF.
