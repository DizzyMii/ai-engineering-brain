---
tags: [concept, domain/post-training, level/frontier]
aliases: [Spurious Rewards, RLVR failure modes, RLVR elicitation]
summary: "RLVR can lift some base models with random or even wrong rewards — because RL elicits latent behavior, it doesn't teach new reasoning."
---

# Concept - Spurious Rewards and RLVR Failure Modes

> **One-paragraph hook:** The clean story of RL with verifiable rewards — "reward correct answers, get a reasoner" — is partly a lie. On some popular base models you can reward *random noise*, reward *pure output format*, or even reward the *majority-but-wrong* answer, and still see MATH accuracy jump by double digits. That result (Shao, Wen et al. 2025) breaks the naive causal claim that RLVR is teaching correctness. It forces a harder question every practitioner running [[Concept - GRPO and RL with Verifiable Rewards]] must answer before believing their own numbers: did the reward signal teach anything, or did on-policy RL just amplify a behavior the base model already had?

## The mechanism

RLVR replaces a learned reward model with a programmatic verifier (exact-match on a math answer, unit tests, a `<think>` format regex) and optimizes it with a policy-gradient method, usually GRPO. The intended causal chain is: verifier rewards correct solutions → policy up-weights the token trajectories that produced them → the model reasons better. The **Spurious Rewards** finding severs the first link.

On `Qwen2.5-Math-7B`, Shao, Wen et al. (2025) ran GRPO on MATH with reward functions that carry *no correctness information*:

- **Ground-truth reward** (the real thing): roughly **+25 to +29 points** on MATH-500.
- **Random reward** (Bernoulli coin flip, independent of the answer): roughly **+15 to +21 points**.
- **Format-only reward** (pay out if the answer is boxed, ignore whether it's right): comparable double-digit gains.
- **Incorrect reward** (reward the model for matching the *wrong* majority-vote answer): gains *close to* ground-truth.

A signal that is provably uninformative should do nothing under a correct causal model. That it does something means the reward is not the active ingredient. The authors' explanation: RLVR under a clipped policy-gradient loss is a **distribution-sharpening operator**. Any reward with even weak, incidental correlation to a latent high-value behavior — here, `Qwen2.5-Math`'s pre-installed tendency to reason in Python-like "code reasoning" steps — will, through the mechanics of on-policy sampling and gradient clipping, concentrate probability mass onto that behavior. The reward is a lever that moves a distribution the base model already contains; it is not a teacher supplying new skill.

This connects directly to the **elicitation vs. learning** debate. Yue et al. (2025), *"Does RL Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model?"*, sampled the base model at large k and found that the RL-tuned model's correct solutions were **already reachable by the base model** within the pass@k envelope — RL narrows the output distribution toward solutions the base could already produce, trading breadth for precision:

```
pass@k
 1.0 |                               ______ base (wide, slow)
     |                        ______/
     |                   ____/    ×  <- crossover: RL loses here
     |      RL (sharp)__/   ______/
     |        ______/  _____/
     |   ____/   _____/
 0.0 |__/______/________________________________ k
        1    4    16    64   256  1024
```

At **pass@1**, the RL model wins (it puts its mass on a good answer). At **pass@256+**, the base model catches and often passes it, because RL threw away the tail of alternative solutions. If RL had *taught new reasoning*, the RL curve would dominate everywhere; instead the curves cross. This is the empirical signature of elicitation, and it ties tightly to [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]] — the mechanism that discards the tail is the same entropy loss that caps exploration.

## In practice

The single most important practical fact: **this is base-model dependent and does not transfer.** The spurious-reward effect is strong on the `Qwen2.5` / `Qwen2.5-Math` family and weak-to-absent on `Llama-3` and `OLMo-2`. The reason is mechanistic — `Qwen2.5-Math` was pretrained on data that gave it a strong latent "reason in code" prior, and RLVR amplifies exactly that prior. Llama and OLMo lack it, so there is nothing spurious for a noise reward to amplify.

The consequence for reading the literature: a headline like "our new RL trick adds +20 on MATH" measured *only on Qwen* is nearly uninterpretable, because a random-reward baseline on the same model would also add a large chunk of that. This is why [[Breakdown - DeepSeek-R1]] is more convincing than most RLVR papers — R1-Zero showed emergent long-CoT and self-verification on `DeepSeek-V3-Base`, a *different* base lineage, with an ablation-heavy report. It's also why [[Concept - Reasoning Training and Long Chain-of-Thought]] should be read with the elicitation caveat front-of-mind: RL may be *sharpening* reasoning the base learned during pretraining rather than *creating* it.

The correct experimental hygiene:

- **Always run a spurious-reward control.** Before believing your reward design, run the identical pipeline with a random reward. Report the delta over that baseline, not over the SFT checkpoint.
- **Test on ≥2 base families.** A result that only holds on Qwen is a statement about Qwen, not about your method.
- **Report pass@k, not just pass@1** (per [[Concept - Statistical Rigor in Model Evaluation]]). A method that raises pass@1 while collapsing pass@64 has moved probability mass, not expanded capability.

## Failure modes

- **Format-reward hacking.** When part of the reward pays out for emitting a pattern (`\boxed{}`, `<think>...</think>`), the policy learns to satisfy the *pattern* while decoupling it from reasoning — collecting reward from lucky final-answer matches or from a regex that a non-reasoning completion also satisfies. This is [[Concept - Reward Hacking]] applied to a rule-based verifier; the verifier being "correct by construction" does not make it un-gameable, because the *format* half of the reward is still a proxy. The RLVR-specific case sits alongside other proxy-gaming incidents catalogued in [[Lore - Reward Hacking Hall of Fame]].
- **The Qwen mirage.** Reporting a large RLVR gain measured only on `Qwen2.5-Math` and framing it as evidence the *method* works. Detection: the random-reward baseline recovers most of the gain.
- **Contamination masquerading as reasoning.** Some apparent RLVR gains on math benchmarks are partly [[Concept - Benchmark Contamination]] — the base model saw the test items in pretraining, and RL surfaces the memorized answer. Detection: hold out a private/fresh problem set; if the gain evaporates off-distribution, you were surfacing memorization.
- **Over-claiming emergence.** Calling elicited base behavior "emergent reasoning from RL." This is the same over-reading critiqued in [[Concept - The Emergent Abilities Debate]]: the phenomenon is real but the causal story ("RL created a new capability") is usually wrong.

## The non-obvious

The uncomfortable insight practitioners learn the hard way: **RLVR's ceiling is set by the base model's pass@k support, not by the reward.** RL cannot make the model solve a problem it could never sample a correct solution to — if the base model's pass@1024 on a problem is ~0, there is no positive-advantage trajectory to reinforce, and the group-relative advantage in GRPO is exactly zero (all rollouts wrong → std-normalized advantage of 0 → no gradient). So RLVR is structurally an *elicitor and sharpener* within the base's reachable set, and the highest-leverage lever is often **the base model and its pretraining data**, not the RL recipe. A corollary the field is still absorbing: because the effect rides on latent priors, "RLVR works" is not a property of the algorithm — it is a property of the *(base model, reward, benchmark)* triple, and any of the three can be the thing actually doing the work.

## Connections

- [[Concept - GRPO and RL with Verifiable Rewards]] — the algorithm whose distribution-sharpening dynamics make spurious rewards effective; understand it before you can see why noise "works."
- [[Concept - Reasoning Training and Long Chain-of-Thought]] — the capability RLVR is claimed to build; the elicitation view reframes it as sharpening pretrained reasoning.
- [[Concept - Reward Hacking]] — format-reward gaming is the RLVR-native instance of the general proxy-reward pathology.
- [[Concept - The Emergent Abilities Debate]] — the same "is this a new capability or a measurement artifact?" question, one domain over.
- [[Concept - Benchmark Contamination]] — a competing explanation for apparent RLVR gains that must be ruled out with held-out sets.
- [[Breakdown - DeepSeek-R1]] — the strongest counter-example: a well-ablated result on a non-Qwen base lineage, the bar spurious-reward-prone papers should clear.
- [[Concept - Statistical Rigor in Model Evaluation]] — pass@k reporting and random-reward controls are the concrete defenses against the mirage.
- [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]] — the entropy-loss mechanism that produces the pass@1-up / pass@k-down signature of elicitation.
- [[Lore - Reward Hacking Hall of Fame]] — the ladder up-link: the tribal-knowledge catalog of real proxy-gaming incidents that format-reward hacking under RLVR belongs to.

## Sources
- Shao, Wen et al. (2025) — *Spurious Rewards: Rethinking Training Signals in RLVR*. Showed random/format/incorrect rewards lift `Qwen2.5-Math` on MATH; attributes it to amplifying latent "code reasoning."
- Yue et al. (2025) — *Does RL Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model?* Found RLVR raises pass@1 but pass@k crosses in the base model's favor — the elicitation signature.
- Shao et al. (2024) — *DeepSeekMath* (GRPO). The optimizer whose clipped, group-relative updates do the sharpening.
