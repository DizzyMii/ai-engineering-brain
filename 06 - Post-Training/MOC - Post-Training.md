---
tags: [moc, domain/post-training, level/surface]
aliases: []
summary: "Map of Post-Training: SFT, RLHF, DPO/GRPO, reward hacking, and the pipeline that turns a base model into a deployed assistant."
---

# MOC - Post-Training

This domain covers everything that happens after pretraining produces a raw next-token predictor: the staged pipeline — SFT, then preference optimization, then optional RLVR, then distillation or merging — that turns it into a model people can actually talk to, ship, and trust. It matters because post-training is where most of a frontier lab's differentiation now lives; pretraining recipes have largely converged, but how a lab aligns, rewards, and shapes a model's behavior is where the DeepSeek-R1, Tulu 3, and GPT-4o-sycophancy stories all play out. The notes here span the full toolchain: SFT and loss masking, RLHF's four-model machinery and its instabilities, the DPO family that replaced RLHF for most shops, and GRPO/RLVR — the technique behind 2025-2026's reasoning-training paradigm. Every method here fails in a specific, documented way — reward hacking, entropy collapse, sycophancy, length bias — and knowing the failure mode is as load-bearing as knowing the algorithm. The question this domain answers: *given a pretrained base model and a target behavior, which post-training recipe gets you there, and what will it break if you're not watching?*

## Start here

- **Surface** → [[Concept - The Post-Training Pipeline]] — the staged map (SFT → preference optimization → optional RLVR → distillation/merging) everything else in this domain sits inside.
- **Core** → [[Concept - Direct Preference Optimization (DPO)]] — reparameterizes RLHF so the policy is its own reward model; the default 2026 second stage after SFT.
- **Advanced** → [[Deep Dive - RLHF End to End]] — the four-resident-model SFT/RM/PPO pipeline behind InstructGPT and ChatGPT, KL-regularized reward and all.
- **Frontier** → [[Concept - Reasoning Training and Long Chain-of-Thought]] — RL on verifiable rewards turned "think longer" into its own scaling axis, the paradigm behind o1 and DeepSeek-R1.
- **Unicorn** → [[Lore - Reward Hacking Hall of Fame]] — the boat-spinning-in-a-lagoon gallery that makes Goodhart's law in RL visceral instead of theoretical.

## The pipeline and SFT

- [[Concept - The Post-Training Pipeline]] — SFT, preference optimization, optional RLVR, then distillation/merging: the staged process that turns a raw predictor into a deployed assistant.
- [[Concept - Supervised Fine-Tuning (SFT)]] — behavior-cloning a base model on curated (prompt, response) pairs via next-token cross-entropy computed only on completions.
- [[Concept - Loss Masking and Sequence Packing]] — the masking and packing mechanics that make SFT both correct (loss only on completions) and efficient (many examples per sequence, no cross-contamination).
- [[Snippet - Loss Masking a Chat Dataset]] — tokenizes a multi-turn chat example and builds a label mask so cross-entropy loss lands only on assistant tokens and EOS.
- [[Gotchas - Chat Template Bugs]] — the silent, no-error-thrown bugs in template application — double BOS, template drift — that quietly degrade a shipped model.

## Preference optimization: DPO and its family

- [[Concept - Direct Preference Optimization (DPO)]] — reparameterizes RLHF so the optimal policy is its own reward model, collapsing the RM-and-PPO loop into one pairwise loss.
- [[Concept - The DPO Variant Family (IPO KTO ORPO SimPO)]] — what each post-DPO offline algorithm fixes, and the reference-model-memory tradeoffs each one makes.
- [[Snippet - DPO Loss Implementation]] — PyTorch DPO loss from policy and reference log-probs: masked log-prob gather, beta log-ratio margin, reward-accuracy metric.
- [[Concept - Length Bias in Preference Optimization]] — reward models and DPO-tuned policies reward length as a proxy for quality — the canonical reward hack and its debiasing arms race.
- [[Checklist - Preference Data Quality]] — pre-flight checks for a preference dataset before launching alignment training: contamination, length bias, provenance, templates.
- [[Decision - Choosing a Preference Optimization Algorithm]] — which algorithm to run after SFT given data shape and compute budget; the 2026 default is SFT then DPO.
- [[Reference - Post-Training Methods Comparison]] — lookup matrix across SFT, RLHF-PPO, the DPO family, GRPO, and rejection sampling: data type, resident models, cost, stability, defaults.

## RLHF core: reward models, PPO, KL control

- [[Concept - Reward Models]] — a scalar RM trained on pairwise human preferences via the Bradley-Terry model, and the calibration biases it inherits from that data.
- [[Concept - PPO for Language Models]] — how the clipped surrogate, GAE, and a value head map onto autoregressive generation, and why its implementation details are load-bearing.
- [[Concept - KL Control in RLHF]] — why beta times KL-to-reference is RLHF's master dial: the reward-KL frontier, adaptive schedules, the k1/k2/k3 estimators.
- [[Deep Dive - RLHF End to End]] — the SFT/RM/PPO pipeline behind InstructGPT and ChatGPT: four resident models, a KL-regularized reward, and real training instability.
- [[Gotchas - RLHF Training Instabilities]] — RLHF/DPO/GRPO failure modes ordered by pain: reward hacking, entropy collapse, value divergence, DPO degeneracy, length explosion, silent setup bugs.
- [[Playbook - Debugging an RLHF Run]] — ordered procedure and symptom-to-fix branch table for diagnosing a misbehaving RLHF/PPO/GRPO run from launch to convergence.
- [[Concept - Reward Hacking]] — the policy exploits flaws in a reward model or verifier to gain reward without the intended behavior: RL's version of Goodhart's law.

## RL with verifiable rewards and reasoning training

- [[Concept - GRPO and RL with Verifiable Rewards]] — PPO without a value model: group-normalized rewards replace the critic, programmatic verifiers replace the learned RM.
- [[Snippet - GRPO Advantage Computation]] — group-relative advantage computation from grouped rewards, plus the token-level clipped loss with a k3 KL term.
- [[Concept - Rejection Sampling and Expert Iteration]] — sample N candidates, keep the best by reward or verifier, SFT on the winners, repeat: RL-flavored post-training without RL.
- [[Concept - Process and Outcome Reward Models]] — scoring a whole answer (ORM) versus scoring every reasoning step (PRM), and why RLVR at scale mostly displaced PRMs anyway.
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — RL on verifiable rewards turns models into extended-thinking reasoners, making think-tokens a scaling axis of their own.
- [[Concept - Spurious Rewards and RLVR Failure Modes]] — RLVR can lift some base models even with random or wrong rewards, because RL elicits latent behavior rather than teaching new reasoning.
- [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]] — on-policy RL fine-tuning bleeds policy entropy and kills exploration; managing the entropy budget is the core RL-tuning skill.
- [[Breakdown - DeepSeek-R1]] — DeepSeek-AI's Jan 2025 open reasoning model that matched o1 on math/code using GRPO-only RL, proof that RL alone can drive reasoning gains.

## Alignment, persona, and model composition

- [[Concept - Constitutional AI and RLAIF]] — replacing human harm labels with a written constitution: self-critique-and-revise for SFT data, then AI preference labels for RL.
- [[Concept - Persona and Character Training]] — a model's voice and traits are trained, not intrinsic; labs now shape and measure persona deliberately, down to activation-space vectors.
- [[Concept - Knowledge Distillation]] — transferring capability from a teacher model to a smaller or cheaper student via soft targets or teacher-generated training data.
- [[Concept - Model Merging]] — combining fine-tuned checkpoints by arithmetic on their weights: free at inference, no retraining, as long as they share a base.

## Case studies and folklore

- [[Breakdown - Tulu 3]] — AllenAI's fully-open post-training recipe: SFT, then length-normalized DPO, then RLVR, on Llama-3.1 bases at 8B/70B/405B.
- [[Lore - The Sycophancy Problem]] — RLHF teaches models to tell users what they want to hear; the mechanism lives in the preference data, and GPT-4o shipped it to production in April 2025.
- [[Lore - Reward Hacking Hall of Fame]] — a curated gallery of documented reward-hacking and specification-gaming incidents, from a boat spinning in a lagoon to RL agents editing their own unit tests.

## Adjacent domains

- [[MOC - Fine-Tuning]] — where parameter-efficient methods (LoRA, adapters) intersect with the SFT and preference-optimization stages this domain defines.
- [[MOC - Training at Scale]] — the distributed-training infrastructure (FSDP, ZeRO, multi-node schedulers) that every RLHF/GRPO run in this domain runs on top of.
- [[MOC - Evaluation]] — the benchmarks and eval harnesses that RLVR verifiers depend on and that reward-hacking policies learn to game.
- [[MOC - Safety & Interpretability]] — where reward hacking and sycophancy, treated here as training-mechanism problems, become alignment and interpretability problems.
