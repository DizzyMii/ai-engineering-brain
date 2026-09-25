---
tags: [lore, domain/prompting-context, level/unicorn]
aliases: [zero-shot CoT, magic prompt phrases, take a deep breath, let's think step by step]
summary: "Folklore and real research behind magic trigger phrases: zero-shot CoT, machine-discovered incantations, and the tipping/threats zoo."
---

# Lore - Let's Think Step by Step

> One sentence appended to a prompt roughly doubled GPT-3's math accuracy. That result was real, reproducible and peer-reviewed, and it started a genre of "magic phrase" folklore that is mostly perishable and weakly sourced. This note separates the two.

## What happened

**The real discovery (2022).** Kojima et al. 2022, *Large Language Models are Zero-Shot Reasoners*, appended **"Let's think step by step"** to a question with *no* worked examples. GPT-3 (`text-davinci-002`) switched from answering directly to producing [[Concept - Chain-of-Thought and Why It Works|chain-of-thought]] reasoning, and accuracy jumped. On GSM8K, zero-shot accuracy went from **10.4% → 40.7%**. MultiArith was starker: **17.7% → 78.7%**. The surprise was that it was *zero-shot*. Wei et al. 2022 had already shown that few-shot exemplars *containing* reasoning helped; Kojima showed one trigger phrase with no exemplars got the same behavior. The phrase didn't teach the model to reason. It selected a region of behavior the model had already learned.

**Machines out-prompted the humans (2022–2023).** If a hand-picked phrase works, an optimizer can find a better one. Two results showed it:

- **APE** (Zhou et al. 2022, *Large Language Models Are Human-Level Prompt Engineers*) had an LLM *generate and score* candidate instructions. It found **"Let's work this out in a step by step way to be sure we have the right answer,"** which beat the human-written "Let's think step by step."
- **OPRO** (Yang et al. 2023, *Large Language Models as Optimizers*) treated prompt writing as an optimization loop and turned up **"Take a deep breath and work on this problem step by step"** as a top instruction for PaLM 2-L, reaching ~80% on GSM8K. "Take a deep breath" became the standard example of how strange and un-human the best machine-found prompts can look.

**The folklore zoo (2023–).** Next to the peer-reviewed work, a menagerie of informal incantations spread:

| Incantation | Claimed effect | Provenance |
|---|---|---|
| "I'll tip you $200" | longer / better answers | viral tweet experiment (late 2023), never peer-reviewed |
| "My job depends on this" / threats | more effort | anecdotal, model- and version-specific |
| "This is very important to my career" | accuracy/effort lift | Li et al. 2023, *EmotionPrompt*: real paper, contested generalization |
| Role priming ("you are an expert…") | capability boost | near-zero capability effect; real style/register shift only |

EmotionPrompt (Li et al. 2023, *Large Language Models Understand and Can Be Enhanced by Emotional Stimuli*) is the most rigorous of these. It reported average improvements across a battery of tasks, but the effect is small, uneven across models, and doesn't hold up on stronger instruction-tuned models. The tipping and threat lore has no controlled sourcing at all.

## The lesson

**None of these are magic. They select a region of the distribution.** Each phrase pushes the model toward the high-effort, reasoning-shaped part of its pretraining and post-training distribution. "Let's think step by step" co-occurs in training data with careful worked solutions, so conditioning on it raises $P(\text{worked-solution continuation})$. The effect belongs to the model's data, not the words. That's why (a) an optimizer can find stranger, better phrases and (b) the same phrase transfers poorly between models. It's the [[Concept - Prompt Engineering|prompt-as-conditioning]] view in its purest form: no weights change, you only move the conditional distribution.

**The effect is perishable, and much of it has expired.** On instruction-tuned models the gains shrank because the reasoning behavior became easier to get by default. On [[Concept - Prompting Reasoning Models|RL-trained reasoning models]] (o-series, DeepSeek-R1, extended-thinking Claude) the phrase is *redundant or harmful*. Those models were trained via [[Concept - GRPO and RL with Verifiable Rewards|RL with verifiable rewards]] to produce long internal chains before answering, so "think step by step" adds noise to a process that's already running. A trick that doubled accuracy in 2022 can be a no-op or a small regression in 2026. The [[Concept - The Emergent Abilities Debate|capability]] moved from the prompt into the weights.

**What to take away is a process.** Prompt tricks are empirical and change over time, so the only defensible stance is to **measure instead of cargo-culting**. Keep a labeled eval set, treat any incantation as a hypothesis, and re-test it on every model upgrade, because today's winning phrase is tomorrow's dead weight (see [[Concept - Prompt Evaluation and Versioning]]). [[Reference - Prompting Techniques Catalog]] lists what to try. This note is the warning label on it.

## Evidence status

- **Peer-reviewed and reproduced:** Kojima et al. 2022 (zero-shot CoT), Wei et al. 2022 (few-shot CoT), APE (Zhou et al. 2022), OPRO (Yang et al. 2023). The core numbers here come from those papers.
- **Real paper, contested generalization:** EmotionPrompt (Li et al. 2023). A real study, but the effect is small and doesn't reliably carry over to frontier instruction-tuned models.
- **Weakly sourced folklore:** the "$200 tip", threats, and job-dependency lines. Anecdotal, viral in origin, version-specific; don't rely on them. They're labeled folklore because that honesty is the point of the note.

## Connections

- [[Concept - Chain-of-Thought and Why It Works]] — the mechanism the phrase triggers; this note is the folklore, that note is the physics.
- [[Concept - Prompting Reasoning Models]] — explains why the phrase expired on o-series/R1: the reasoning is now trained in, so eliciting it by prompt is redundant.
- [[Concept - Prompt Engineering]] — the conditioning view that reframes "magic words" as distribution selection, not incantation.
- [[Concept - Prompt Evaluation and Versioning]] — the antidote to cargo-culting: version and re-test every phrase against a holdout on each model change.
- [[Reference - Prompting Techniques Catalog]] — the catalog these phrases belong to; this note is its skeptical companion marking which entries are folklore.
- [[Concept - The Emergent Abilities Debate]] — zero-shot CoT was an emergent-behavior data point; the capability later migrated from prompt to weights.
- [[Concept - GRPO and RL with Verifiable Rewards]] — the RL training that internalized long reasoning and thereby retired the trigger phrase.

## Sources

- Kojima et al. (2022) — *Large Language Models are Zero-Shot Reasoners.* The origin of "Let's think step by step"; GSM8K 10.4%→40.7%, MultiArith 17.7%→78.7% on `text-davinci-002`.
- Wei et al. (2022) — *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.* The few-shot precursor that zero-shot CoT distilled to one phrase.
- Zhou et al. (2022) — *Large Language Models Are Human-Level Prompt Engineers (APE).* Machine-discovered a better phrase than the human one.
- Yang et al. (2023) — *Large Language Models as Optimizers (OPRO).* Surfaced "Take a deep breath and work on this problem step by step."
- Li et al. (2023) — *Large Language Models Understand and Can Be Enhanced by Emotional Stimuli (EmotionPrompt).* The most rigorous of the emotional-stimulus results; effect real but small and non-robust.
