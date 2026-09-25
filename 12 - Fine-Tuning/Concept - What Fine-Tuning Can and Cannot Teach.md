---
tags: [concept, domain/fine-tuning, level/surface]
aliases: []
summary: "Fine-tuning reliably reshapes behavior, format, and style; it is a slow, unreliable way to inject new facts — that's RAG's job."
---

# Concept - What Fine-Tuning Can and Cannot Teach

> **One-paragraph hook:** the most expensive mistake in applied fine-tuning is using it to "teach the model our documentation." Fine-tuning trains $p(y \mid x)$, the conditional distribution over outputs given inputs, and it's excellent at reshaping *how* the model answers: format, tone, refusal behavior, a fixed classification scheme. It's a poor, unreliable way to change *what the model knows*. Mixing up those two axes wastes more fine-tuning budget than any hyperparameter mistake.

## The mechanism

Each fine-tuning example is a gradient step nudging the output distribution toward the target completion for that input. Say the target behavior is a *shape* the model already has latent capacity for: respond in JSON, adopt this persona, refuse this category of request, always classify into these five labels. A few hundred to a few thousand examples will reliably carve that shape into the output distribution. The knowledge and reasoning needed to produce it were already in the pretrained base; fine-tuning only has to make it the *default* behavior out of many possible ones.

Injecting new facts is a different problem. Pretraining built the model's factual associations from trillions of tokens of repeated, varied co-occurrence between an entity and its attributes. That repetition and variety is what lets a fact generalize: recalled under a different phrasing, combined with other facts. A handful of fine-tuning examples like "Q: What is X's revenue? A: $42M" sends a strong signal to imitate the *format* of a confident, specific answer, and a weak, shallow signal to bind the entity to the number in a way that generalizes. The result is a specific, well-documented failure pattern: the model sounds right and invents the numbers.

Gekhman et al. 2024 ("Does Fine-Tuning LLMs on New Knowledge Encourage Hallucination?") measured this directly. During SFT, examples with facts the base model doesn't already know are fit much more slowly than examples restating what it knows. More important, as the model is pushed to fit the unknown-fact examples, its hallucination rate rises on *unrelated* facts elsewhere. Teaching new knowledge via SFT doesn't only fail to stick reliably; it can actively degrade general factuality.

The capacity argument backs this up. A rank-16 [[Deep Dive - LoRA]] adapter on a 7B model adds on the order of a few tens of millions of parameters. That's nowhere near enough to store a corpus of facts, even before asking whether gradient descent would spend that capacity on storage or on format-matching. Even full fine-tuning, with every parameter trainable, needs many repeated exposures to overwrite a strong pretrained prior, and one pass over a handful of documents isn't that.

## In practice

Rule of thumb: fine-tune for stable behavior and skills, retrieve for facts (especially facts that change), and prompt for quick, cheap behavior shifts that don't justify a training run at all. The full decision tree is in [[Decision - Fine-Tuning vs RAG vs Prompting]].

There is a real knowledge-injection path. It's continued pretraining, sometimes called domain-adaptive pretraining or DAPT (Gururangan et al. 2020, "Don't Stop Pretraining: Adapt Language Models to Domains and Tasks"), not SFT. DAPT runs many epochs of ordinary next-token prediction over a large domain corpus. It uses the same objective and scale of repetition as the original pretraining, so it *can* move facts into the weights. Operationally, though, it behaves like pretraining in every way that matters, not like an instruction fine-tune. The learning rate has to be re-warmed and re-decayed instead of starting from a small constant (Ibrahim et al. 2024, "Simple and Scalable Strategies to Continually Pre-train Large Language Models"). It needs a replay slice of the original pretraining [[Concept - Data Mixtures|data mixture]] mixed back in to limit forgetting of general ability. And it needs orders of magnitude more tokens than an instruction fine-tune: millions to billions of tokens of domain text, where an instruction fine-tune uses a few thousand curated examples.

## Failure modes

The named anti-pattern, "fine-tune on our docs so the model knows our product," is the most common wasted fine-tuning project. Check for it before any training run: hold out a set of facts present *only* in the target documents and check whether the base model, given the same information in-context, already answers correctly. If it does with retrieval, the gap isn't knowledge, and a much cheaper RAG pipeline solves it (see [[Deep Dive - RAG Architectures]]).

A related trap is confusing [[Concept - Knowledge Distillation]] with knowledge injection. Distillation transfers a *teacher model's output distribution* onto a student. At heart that's still a behavior/format transfer, and it can't ground facts that neither model reliably knows.

Fine-tuning can also teach a reasoning *format*, such as the structure of a [[Concept - Chain-of-Thought and Why It Works|chain-of-thought]] trace, without teaching correct reasoning *content* when the facts or skills the reasoning depends on aren't in the base model. The output looks like careful reasoning and is still wrong. That's more dangerous than an obviously wrong answer, since review is less likely to catch it.

Last, aggressive fine-tuning aimed at injecting new material carries real [[Concept - Catastrophic Forgetting|catastrophic forgetting]] risk. Pushing the model hard toward unfamiliar content pulls it away from the broad pretrained solution. Besides failing to teach the intended facts, it can degrade general instruction-following.

## The non-obvious

The hallucination-increase finding is the sharpest lesson for practitioners. A fine-tune that "works" on your eval set, meaning the model now answers your target questions, can at the same time make it *worse* at general knowledge questions it used to get right, because fitting unfamiliar facts perturbs shared representations used elsewhere. A net-positive fine-tune on the target task can be a net-negative model. So any knowledge-adjacent fine-tune needs a general-capability regression check before shipping, on top of the task-metric check.

## Connections
- [[Decision - Fine-Tuning vs RAG vs Prompting]] — the full decision framework this concept feeds; start there once you know whether the gap is knowledge or behavior.
- [[Deep Dive - RAG Architectures]] — the mechanism that actually solves the knowledge-injection problem fine-tuning can't.
- [[Deep Dive - LoRA]] — the capacity argument above depends on how few parameters a typical adapter actually adds.
- [[Concept - Catastrophic Forgetting]] — the risk that knowledge-injection attempts run into when they push too hard against the pretrained prior.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the specific objective whose behavior-not-knowledge character this note explains.
- [[Concept - Knowledge Distillation]] — a related technique that also transfers behavior/distribution rather than grounded facts.
- [[Concept - Data Mixtures]] — the replay-ratio mechanism that makes continued pretraining survivable without wrecking general ability.
- [[Concept - Chain-of-Thought and Why It Works]] — an example of a *format* fine-tuning teaches reliably, distinct from the *content* it doesn't guarantee.
- [[Concept - Why LoRA Underperforms Full Fine-Tuning]] — the companion mechanistic note on why PEFT specifically struggles even harder on large knowledge/domain shifts.

## Sources
- Gekhman et al. 2024 — "Does Fine-Tuning LLMs on New Knowledge Encourage Hallucination?" The core empirical result: unknown facts are learned slowly and their introduction raises hallucination on unrelated facts.
- Gururangan et al. 2020 — "Don't Stop Pretraining: Adapt Language Models to Domains and Tasks." Establishes domain-adaptive continued pretraining (DAPT) as the real knowledge-injection path.
- Ibrahim et al. 2024 — "Simple and Scalable Strategies to Continually Pre-train Large Language Models." LR re-warming and replay strategy for continued pretraining without catastrophic forgetting.
