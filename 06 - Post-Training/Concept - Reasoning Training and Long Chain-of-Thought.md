---
tags: [concept, domain/post-training, level/frontier]
aliases: [long CoT, o1-style reasoning, R1-style reasoning, reasoning RL, test-time compute scaling]
summary: "RL on verifiable rewards turns models into extended-thinking reasoners; a paradigm that made think-tokens a scaling axis of their own."
---
> **One-paragraph hook:** Somewhere between 2024 and 2025 the field discovered that reinforcement learning against verifiable rewards — not more parameters, not more pretraining tokens — could make a model spontaneously start thinking for thousands of tokens before answering, checking its own work, backtracking, and trying a different approach mid-reasoning. OpenAI's o1 and DeepSeek-R1 turned this into the new default recipe for hard reasoning tasks, and it opened a second scaling axis orthogonal to the pretraining [[Concept - Scaling Laws]]: how long the model is allowed to think.

## The mechanism
Ordinary SFT/DPO-trained models produce chain-of-thought because they were shown demonstrations that reason step by step ([[Concept - Chain-of-Thought and Why It Works]]) — the length and style of the reasoning is whatever the demonstrator wrote. Reasoning training instead uses on-policy RL against a **verifiable** reward — [[Concept - GRPO and RL with Verifiable Rewards]] is the workhorse algorithm — on math, code, and other domains with a checkable answer, and lets the model discover its own reasoning length and style under optimization pressure.

Concretely: a response is structured as `<think> ... </think> <answer> ... </answer>`, and the reward is

$$R = R_{\text{accuracy}}(\text{answer}, \text{ground truth}) + R_{\text{format}}(\text{structural compliance})$$

with no explicit term rewarding length. What happens next is emergent, not engineered: longer internal deliberation correlates with getting hard problems right, so gradient ascent under GRPO/PPO pushes probability mass toward longer, more thorough traces over the course of training — average response length grows as a *side effect* of optimizing for correctness, not because anyone put length in the reward.

```mermaid
flowchart LR
    P[Prompt] --> S[Sample long CoT<br/>think tokens + answer]
    S --> V{Verifier<br/>exact match / unit tests}
    V -->|reward| G[GRPO group-relative<br/>advantage]
    G --> U[Policy update]
    U --> S
```

Alongside length growth, DeepSeek-R1-Zero (pure RL, no SFT, directly on a base model — see [[Breakdown - DeepSeek-R1]]) exhibited emergent **self-verification** ("let me check this") and **backtracking** ("wait, that's wrong, let me reconsider") — behaviors nobody wrote a reward term for, elicited purely because they raise the odds of landing on the verifiably correct final answer.

Two training regimes matter: **zero** (R1-Zero: pure RL straight from a base model, proving the emergent reasoning is RL-driven rather than imitated) and **cold-start** (R1: a small SFT stage on curated long-CoT examples before RL, added specifically to fix R1-Zero's poor readability and language-mixing). At inference, some systems hide the thinking tokens from the user (OpenAI o1 shows only a summary), others show the full trace (DeepSeek-R1).

## In practice
Reward design in practice keeps accuracy dominant and format light — a small reward for emitting well-formed `<think>`/`<answer>` tags so outputs stay parseable, without letting format dominate (over-weighting it invites models to emit the wrapper without doing real reasoning). Verifiable domains are the hard requirement: exact-match or normalized numeric answers for math, passing unit tests for code, checkable proof steps for formal reasoning. No verifiable signal, no RLVR-style reasoning training as currently practiced — this is why reasoning-RL gains concentrate so heavily in math and code.

Test-time scaling is the other half of the story: pass@1 improves as a function of how much CoT the model is allowed to generate, or how many samples are aggregated (majority vote, best-of-N) — a scaling axis roughly orthogonal to parameters × pretraining tokens. Budget forcing (Muennighoff et al. 2025, "s1: Simple test-time scaling") is the cheapest version of this lever: when the model tries to stop thinking early, forcibly inject a token like "Wait" to extend the trace — no additional training, often a direct accuracy bump. Once a reasoning model exists, its long traces are also the cheapest path to a smaller one: SFT-distilling the traces into a dense model ([[Concept - Knowledge Distillation]]) frequently transfers more reasoning capability than running the same RL recipe on the small model directly.

## Failure modes
**Overthinking** is the length-bias analogue for reasoning models: a model burns thousands of think-tokens on a trivial prompt for no accuracy gain, driving up latency and cost with nothing to show for it. **Language mixing and unreadable CoT** shows up in pure-RL regimes (R1-Zero) because nothing in an outcome-only reward constrains the reasoning to stay in one language or read naturally to a human — fixed only by adding an explicit language-consistency reward or a cold-start SFT stage. The **generalization ceiling** is real: gains concentrate in verifiable domains, and transfer to open-ended, non-verifiable tasks (writing, general dialogue, judgment calls) is weak or absent, a pattern explored further in [[Concept - Spurious Rewards and RLVR Failure Modes]]. That work also surfaces the deeper, contested question: does long-CoT RL teach genuinely new reasoning strategies, or mainly resample and sharpen strategies already latent in the pretrained base? Yue et al. 2025 found pass@k can be flat or even worse after RL even as pass@1 rises — evidence for elicitation over creation, and a live fault line connected to [[Concept - The Emergent Abilities Debate]].

## The non-obvious
The most counterintuitive practitioner finding is that nobody explicitly rewards length, yet response length is the single most-watched leading indicator that reasoning RL is "working" — teams track the length-vs-training-step curve the way they'd track a loss curve, even though length was never the target and a rising length can equally be an overthinking or hacking symptom rather than genuine progress; it has to be read jointly with accuracy, never alone. A second, sharper insight comes from budget forcing: RL apparently doesn't install a fixed policy for "how long to think" so much as a willingness to keep going once started — you can externally coerce more of that willingness after training with a single injected "Wait" token, at zero training cost, which says the length the model settled on during RL was never a hard ceiling to begin with.

## Connections
- [[Concept - GRPO and RL with Verifiable Rewards]] — the core RL algorithm that makes reasoning training tractable at scale, via its group-relative, value-model-free advantage.
- [[Breakdown - DeepSeek-R1]] — the canonical worked example of this entire paradigm, including the zero-vs-cold-start distinction.
- [[Concept - Chain-of-Thought and Why It Works]] — long-CoT reasoning training is what happens when you optimize the length and content of chain-of-thought with RL instead of just prompting or demonstrating it.
- [[Concept - Spurious Rewards and RLVR Failure Modes]] — the evidence base for the elicitation-vs-new-capability debate and for RLVR's generalization limits.
- [[Concept - Process and Outcome Reward Models]] — the reward-granularity question (score the whole trace or every step) that reasoning training has to answer.
- [[Concept - Scaling Laws]] — test-time think-token scaling is a second axis alongside parameter/data scaling, with its own diminishing-returns curve.
- [[Concept - The Emergent Abilities Debate]] — the elicitation-vs-creation question for reasoning RL is a specific instance of the broader debate over what counts as an emergent capability.
- [[Concept - Sampling and Decoding Parameters]] — think-token budgets, temperature, and majority-vote aggregation are all decoding-time knobs on top of a reasoning-trained model.
- [[Concept - Knowledge Distillation]] — the cheapest way to get a small reasoning model is usually SFT-distilling a large reasoning model's traces, not RL-training the small model directly.
- [[Lore - Let's Think Step by Step]] — the zero-shot CoT lineage this paradigm ultimately descends from, now with RL choosing the reasoning instead of a human writing it into a prompt.

## Sources
- OpenAI (2024) — o1 system card. Introduces RL-trained, largely hidden long-CoT reasoning at inference time.
- DeepSeek-AI (2025) — DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning. Open recipe reproducing o1-style reasoning via GRPO/RLVR, including the R1-Zero pure-RL result.
- Muennighoff et al. (2025) — s1: Simple test-time scaling. Budget forcing via forced continuation tokens.
- Kojima et al. (2022) — Large Language Models are Zero-Shot Reasoners. The "let's think step by step" lineage this paradigm builds on and ultimately automates via RL.
