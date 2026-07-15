---
tags: [concept, domain/fine-tuning, level/surface]
aliases: []
summary: "Fine-tuning reliably reshapes behavior, format, and style; it is a slow, unreliable way to inject new facts — that's RAG's job."
---

# Concept - What Fine-Tuning Can and Cannot Teach

> **One-paragraph hook:** The most expensive mistake in applied fine-tuning is treating it as a way to "teach the model our documentation." Fine-tuning trains $p(y \mid x)$ — the conditional distribution over outputs given inputs — and it is superb at reshaping *how* the model answers: format, tone, refusal behavior, a fixed classification scheme. It is a poor and unreliable way to change *what the model knows*. Confusing these two axes wastes more fine-tuning budget than any hyperparameter mistake.

## The mechanism

Every fine-tuning example is a gradient step that nudges the model's output distribution toward the target completion for that input. When the target behavior is a *shape* the model already has latent capacity for — respond in JSON, adopt this persona, refuse this category of request, always classify into these five labels — a few hundred to a few thousand examples is enough to reliably carve that shape into the output distribution, because the underlying knowledge and reasoning needed to produce it was already present in the pretrained base; fine-tuning just has to make it the *default* behavior instead of one of many possible behaviors.

Injecting new facts is a different problem. A model's factual associations were built by pretraining over trillions of tokens of repeated, varied co-occurrence between an entity and its attributes — that repetition and diversity is what lets a fact generalize (recall it when asked in a different phrasing, combine it with other facts). A handful of fine-tuning examples showing "Q: What is X's revenue? A: $42M" gives the model a strong signal to imitate the *format* of a confident, specific-sounding answer, but a comparatively weak and shallow signal to actually bind the entity to the number in a way that generalizes. The result is a specific, well-documented failure pattern: the model sounds right and invents the numbers.

Gekhman et al. 2024 ("Does Fine-Tuning LLMs on New Knowledge Encourage Hallucination?") measured this directly: examples containing facts the base model doesn't already know are fit much more slowly during SFT than examples that just restate what the model already knows, and — more importantly — as the model is pushed to fit those unknown-fact examples, its hallucination rate rises on *unrelated* facts elsewhere in the model. Teaching new knowledge via SFT doesn't just fail to stick reliably; it can actively degrade general factuality.

The capacity argument reinforces the empirical one. A rank-16 [[Deep Dive - LoRA]] adapter on a 7B model adds on the order of a few tens of millions of parameters — nowhere near enough to store a corpus of facts, even setting aside whether gradient descent would use that capacity for storage versus format-matching. Even full fine-tuning, with every parameter trainable, needs many repeated exposures to overwrite a strong pretrained prior; a single pass over a handful of documents is not that.

## In practice

The practical rule of thumb: fine-tune for stable behavior and skills, retrieve for facts — especially facts that change — and prompt for quick, cheap behavior shifts that don't justify a training run at all (the full decision tree lives in [[Decision - Fine-Tuning vs RAG vs Prompting]]).

There is a real knowledge-injection path, but it isn't SFT — it's continued pretraining, sometimes called domain-adaptive pretraining or DAPT (Gururangan et al. 2020, "Don't Stop Pretraining: Adapt Language Models to Domains and Tasks"). DAPT runs many epochs of ordinary next-token prediction over a large domain corpus, and because it uses the same objective and scale of repetition as the original pretraining, it *can* move facts into the model's weights. But it behaves like pretraining, not like an instruction fine-tune, in every way that matters operationally: it needs the learning rate re-warmed and re-decayed rather than starting from a small constant LR (Ibrahim et al. 2024, "Simple and Scalable Strategies to Continually Pre-train Large Language Models"), it needs a replay slice of the original pretraining [[Concept - Data Mixtures|data mixture]] mixed back in to limit forgetting of general ability, and it needs orders of magnitude more tokens than an instruction fine-tune — millions to billions of tokens of domain text, not a few thousand curated examples.

## Failure modes

The named anti-pattern — "fine-tune on our docs so the model knows our product" — is the single most common wasted fine-tuning project. Detection is straightforward and should happen before any training run: hold out a set of facts *only* present in the target documents and ask whether the base model, given the same information in-context, already answers correctly. If it does with retrieval, the gap isn't knowledge, it's something a much cheaper RAG pipeline solves (see [[Deep Dive - RAG Architectures]]).

A related trap is conflating [[Concept - Knowledge Distillation]] with knowledge injection: distillation transfers a *teacher model's output distribution* onto a student, which is still a behavior/format transfer at heart, not a mechanism for grounding facts that neither model reliably knows.

Fine-tuning can also teach a reasoning *format* — the structure of a [[Concept - Chain-of-Thought and Why It Works|chain-of-thought]] trace, for instance — without teaching correct reasoning *content* if the underlying facts or skills the reasoning depends on aren't already in the base model. The output will look like careful reasoning and still be wrong, which is more dangerous than an obviously wrong answer because it's harder to catch in review.

Finally, aggressive fine-tuning aimed at injecting new material carries real [[Concept - Catastrophic Forgetting|catastrophic forgetting]] risk: pushing the model hard toward unfamiliar content pulls it away from the broad pretrained solution and can degrade general instruction-following as a side effect, not just fail to teach the intended facts.

## The non-obvious

The hallucination-increase finding is the sharpest practitioner lesson here: a fine-tune that "works" on your eval set — the model now answers your target questions — can simultaneously make the model *worse* at general knowledge questions it used to get right, because pushing weights to fit unfamiliar facts perturbs shared representations used elsewhere. A net-positive fine-tune on the target task can be a net-negative model. This is why any knowledge-adjacent fine-tune needs a general-capability regression check, not just a task-metric check, before shipping.

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
