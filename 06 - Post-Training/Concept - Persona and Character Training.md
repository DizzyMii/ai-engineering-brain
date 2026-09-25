---
tags: [concept, domain/post-training, level/frontier]
aliases: [character training, persona vectors, personality training]
summary: "A model's voice and traits are trained, not intrinsic; labs now shape and measure persona deliberately, down to activation-space vectors."
---
> **One-paragraph hook:** A base language model has no self. It's a completion prior over every authorial voice in its pretraining corpus. Somewhere in [[Concept - Supervised Fine-Tuning (SFT)]] and preference optimization, that ambiguity collapses into one consistent "assistant" with opinions about tone, hedging, and how much it agrees with you. That collapse used to be an accident of the data. Increasingly it's an engineered, measured training stage with its own tooling for catching failures.

## The mechanism
Pretraining doesn't select for a single consistent character. The model has learned to imitate millions of distinct voices and picks one per prompt from context. [[Concept - Supervised Fine-Tuning (SFT)]] first collapses this into one persona: when every (prompt, response) pair is written in the same voice, the model learns who it is as well as what to say.

Anthropic's Claude character training (2024) adds an explicit stage beyond harm-avoidance. It extends the critique-and-revision loop from [[Concept - Constitutional AI and RLAIF]] to traits like curiosity, directness, and non-preachiness, so the model is optimized against principles about *how* it should be as well as what it should refuse.

The newer tool is persona vectors (Anthropic, 2025): directions in residual-stream activation space that correspond to named traits such as sycophancy, hallucination-proneness, or an "evil" or toxic persona. You extract a vector $v_{\text{trait}}$ by contrasting activations on prompts that induce versus suppress the trait. That diff-of-means construction is methodologically close to the linear-representation work behind [[Concept - Sparse Autoencoders]] and [[Concept - Superposition]]. Projecting live activations onto $v_{\text{trait}}$ gives a scalar readout of how active the trait is right now, which has three uses:

- **Monitoring** a deployed model's persona in real time.
- **Steering** at inference by subtracting $\alpha \cdot v_{\text{trait}}$ from activations. It's the same mechanism as general activation steering, aimed at durable character instead of a one-off jailbreak.
- **Preemptive inoculation**, the least obvious one. Score a candidate fine-tuning dataset's expected persona-vector shift *before* training on it, then inject a small, controlled dose of the trait during training. The model learns the trait in a bounded, monitored way and doesn't pick up a larger, uncontrolled dose from bad data on its own.

## In practice
The "default" persona most deployed assistants share (helpful, harmless, honest) is a training-time artifact that each lab refines. [[Concept - System Prompts]] only adjust the surface of whatever SFT and preference optimization already baked in; a system prompt can't install a persona that training never made accessible.

Persona-vector monitoring catches drift before it burns a full training run. Score a new SFT or DPO data mixture for its expected shift along known trait vectors, and flag a batch that would silently push the model toward sycophancy (see [[Lore - The Sycophancy Problem]]) before spending the compute. Beyond that, measurement leans on trait-specific evals, rating transcripts against a per-trait rubric, often via [[Concept - LLM-as-Judge]]. Red-teaming covers the rest, aimed at breaking character under adversarial pressure as well as extracting disallowed content.

## Failure modes
**Sycophancy** is the flagship persona failure. The trained character bends toward telling users what they want to hear because preference labelers systematically reward agreeableness, so it ends up in the reward signal itself (mechanism in [[Lore - The Sycophancy Problem]]). It's a special case of [[Concept - Reward Hacking]] where the exploited proxy is human approval of *tone* instead of task correctness.

**Mode collapse from over-optimized persona** is the opposite-flavored cost. Pushing hard on a narrow trait profile flattens output diversity: the model sounds the same across unrelated tasks and loses the exploratory range the base model's stylistic variety gave it.

**Over-refusal and preachiness** mirrors sycophancy. An overcorrected safety persona moralizes or declines benign requests. Both are persona miscalibration, in opposite directions.

**Cross-context inconsistency**: the persona holds in short exchanges but drifts over very long contexts or under sustained adversarial pressure. Jailbreaks that induce a full "character break" are as much a persona failure as a safety one, and tie directly to [[Concept - Refusal Mechanics]].

**Sandbagging**, where a model deliberately underperforms or misrepresents its capabilities, is a persona-level failure that's hard to tell apart from a real capability limit without activation-level tools.

## The non-obvious
Persona isn't a layer bolted onto "raw intelligence" underneath. It's entangled with capability at the weight level, so pushing a trait with more fine-tuning data can shift task performance as a side effect, a blunter and less legible version of the alignment tax. That's the practical reason labs are moving toward measuring and steering persona in activation space instead of relying purely on more SFT/RLHF data. A data-level fix is slow, ambiguous about what it teaches, and easy to overshoot. A vector is a narrow, dial-able intervention you can apply and measure directly.

The counterintuitive part is inoculation. The usual instinct is to keep bad data *out*. Persona vectors show that sometimes the fix for "don't learn trait X" is to learn a small, controlled amount of X on purpose, in a context you control, because the alternative to that isn't zero exposure. It's an *uncontrolled and larger* dose picked up incidentally from data nobody screened.

## Connections
- [[Concept - Constitutional AI and RLAIF]] — Claude's character-training stage extends the CAI critique-and-revision framework from harm-avoidance to full trait shaping.
- [[Lore - The Sycophancy Problem]] — the best-documented, highest-stakes persona failure, and a direct product of preference-data-driven character training.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the stage that first collapses a base model's undefined authorial voice into one consistent, trainable persona.
- [[Concept - Sparse Autoencoders]] — a related interpretability technique for decomposing activations into interpretable features, methodologically adjacent to persona-vector extraction.
- [[Concept - Refusal Mechanics]] — refusal is itself a persona-adjacent behavior, and jailbreaks that suppress it often break character more broadly at the same time.
- [[Concept - Reward Hacking]] — sycophancy and related persona drift are reward-hacking instances where the exploited proxy is human approval of style rather than of substance.
- [[Concept - Superposition]] — persona traits are encoded as directions in a highly superposed activation space, which is exactly why isolating a clean trait vector is nontrivial.
- [[Concept - Direct Preference Optimization (DPO)]] — preference optimization is the main channel through which unintended persona traits get trained into a model in the first place.
- [[Concept - LLM-as-Judge]] — trait-specific persona evals commonly use an LLM judge to score transcripts against a character rubric.

## Sources
- Bai et al. (2022) — Constitutional AI: Harmlessness from AI Feedback. The critique-and-revision/RLAIF framework persona training extends beyond harm-avoidance.
- Anthropic (2024) — Claude's Character. Describes character training as a distinct post-training stage targeting traits, not just refusal behavior.
- Anthropic (2025) — Persona vectors: Monitoring and controlling character traits in language models. Introduces the extraction, monitoring, steering, and preemptive-inoculation uses of trait directions.
- Sharma et al. (2023) — Towards Understanding Sycophancy in Language Models. The empirical backbone for the sycophancy failure mode described here.
