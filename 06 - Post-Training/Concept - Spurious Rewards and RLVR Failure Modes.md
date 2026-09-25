---
tags: [concept, domain/post-training, level/frontier]
aliases: [Spurious Rewards, RLVR failure modes, RLVR elicitation]
summary: "RLVR can lift some base models with random or even wrong rewards — because RL elicits latent behavior, it doesn't teach new reasoning."
---

# Concept - Spurious Rewards and RLVR Failure Modes

> **One-paragraph hook:** The clean story of RL with verifiable rewards, "reward correct answers, get a reasoner," is partly a lie. On some popular base models you can reward *random noise*, reward *pure output format*, or even reward the *majority-but-wrong* answer, and MATH accuracy still jumps by double digits. That result (Shao, Wen et al. 2025) breaks the naive causal claim that RLVR teaches correctness. Anyone running [[Concept - GRPO and RL with Verifiable Rewards]] has to answer a harder question before believing their own numbers: did the reward signal teach anything, or did on-policy RL just amplify a behavior the base model already had?

## The mechanism

RLVR swaps the learned reward model for a programmatic verifier (exact-match on a math answer, unit tests, a `<think>` format regex) and optimizes against it with a policy-gradient method, usually GRPO. The intended causal chain: verifier rewards correct solutions → policy up-weights the token trajectories that produced them → the model reasons better. The **Spurious Rewards** finding cuts the first link.

On `Qwen2.5-Math-7B`, Shao, Wen et al. (2025) ran GRPO on MATH with reward functions that carry *no correctness information*:

- **Ground-truth reward** (the real thing): roughly **+25 to +29 points** on MATH-500.
- **Random reward** (Bernoulli coin flip, independent of the answer): roughly **+15 to +21 points**.
- **Format-only reward** (pay out if the answer is boxed, ignore whether it's right): comparable double-digit gains.
- **Incorrect reward** (reward the model for matching the *wrong* majority-vote answer): gains *close to* ground-truth.

Under a correct causal model, a provably uninformative signal should do nothing. Since it does something, the reward isn't the active ingredient. The authors' explanation is that RLVR under a clipped policy-gradient loss acts as a **distribution-sharpening operator**. Take any reward with even weak, incidental correlation to a latent high-value behavior. Here that behavior is `Qwen2.5-Math`'s pre-installed habit of reasoning in Python-like "code reasoning" steps. On-policy sampling plus gradient clipping will concentrate probability mass onto it. The reward moves a distribution the base model already contains. It doesn't supply new skill.

That ties into the **elicitation vs. learning** debate. Yue et al. (2025), *"Does RL Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model?"*, sampled the base model at large k. The RL-tuned model's correct solutions were **already reachable by the base model** within the pass@k envelope. RL narrows the output distribution toward solutions the base could already produce, trading breadth for precision:

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

At **pass@1** the RL model wins, because it puts its mass on a good answer. At **pass@256+** the base model catches up and often passes it, since RL threw away the tail of alternative solutions. If RL had *taught new reasoning*, its curve would dominate everywhere. The curves cross instead, and that crossing is the empirical signature of elicitation. It's closely tied to [[Concept - Entropy Collapse and Exploration in RL Fine-Tuning]]: the entropy loss that discards the tail is the same one that caps exploration.

## In practice

The most important practical fact: **this is base-model dependent and does not transfer.** The spurious-reward effect is strong on the `Qwen2.5` / `Qwen2.5-Math` family and weak-to-absent on `Llama-3` and `OLMo-2`. The reason is mechanistic. `Qwen2.5-Math` was pretrained on data that gave it a strong latent "reason in code" prior, and RLVR amplifies that prior. Llama and OLMo don't have it, so a noise reward has nothing spurious to amplify.

For reading the literature, this means a headline like "our new RL trick adds +20 on MATH" measured *only on Qwen* is nearly uninterpretable. A random-reward baseline on the same model would also add a large chunk of that. It's why [[Breakdown - DeepSeek-R1]] is more convincing than most RLVR papers: R1-Zero showed emergent long-CoT and self-verification on `DeepSeek-V3-Base`, a *different* base lineage, in an ablation-heavy report. It's also why [[Concept - Reasoning Training and Long Chain-of-Thought]] should be read with the elicitation caveat in mind. RL may be *sharpening* reasoning the base picked up in pretraining, not *creating* it.

Experimental hygiene:

- **Always run a spurious-reward control.** Before trusting your reward design, run the identical pipeline with a random reward. Report the delta over that baseline, not over the SFT checkpoint.
- **Test on ≥2 base families.** A result that only holds on Qwen is a statement about Qwen, not about your method.
- **Report pass@k, not just pass@1** (per [[Concept - Statistical Rigor in Model Evaluation]]). If pass@1 goes up while pass@64 collapses, you've moved probability mass without expanding capability.

## Failure modes

- **Format-reward hacking.** When part of the reward pays for emitting a pattern (`\boxed{}`, `<think>...</think>`), the policy learns to satisfy the *pattern* while decoupling it from reasoning. It collects reward from lucky final-answer matches or from a regex that a non-reasoning completion also satisfies. That's [[Concept - Reward Hacking]] against a rule-based verifier. A verifier that's "correct by construction" can still be gamed, because the *format* half of the reward is still a proxy. This RLVR case sits alongside the other proxy-gaming incidents in [[Lore - Reward Hacking Hall of Fame]].
- **The Qwen mirage.** Reporting a large RLVR gain measured only on `Qwen2.5-Math` as evidence that the *method* works. Detection: the random-reward baseline recovers most of the gain.
- **Contamination masquerading as reasoning.** Some apparent RLVR gains on math benchmarks are partly [[Concept - Benchmark Contamination]]. The base model saw the test items in pretraining, and RL surfaces the memorized answer. Detection: hold out a private/fresh problem set. If the gain evaporates off-distribution, you were surfacing memorization.
- **Over-claiming emergence.** Calling elicited base behavior "emergent reasoning from RL." It's the same over-reading critiqued in [[Concept - The Emergent Abilities Debate]]: the phenomenon is real, but the causal story ("RL created a new capability") is usually wrong.

## The non-obvious

The lesson practitioners learn the hard way is that **RLVR's ceiling is set by the base model's pass@k support, not by the reward.** RL can't make the model solve a problem it could never sample a correct solution to. If the base model's pass@1024 on a problem is ~0, there's no positive-advantage trajectory to reinforce, and GRPO's group-relative advantage is zero (all rollouts wrong → std-normalized advantage of 0 → no gradient). So RLVR is an *elicitor and sharpener* within the base's reachable set, and the biggest lever is often **the base model and its pretraining data**, not the RL recipe. A corollary the field is still absorbing: since the effect rides on latent priors, "RLVR works" describes the *(base model, reward, benchmark)* triple, not the algorithm, and any of the three can be what's actually doing the work.

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
