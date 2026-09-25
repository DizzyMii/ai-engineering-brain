---
tags: [concept, domain/esoterica, level/advanced]
aliases: [A is B B is A problem, directional fact storage]
summary: "LLMs trained on 'A is B' fail to infer 'B is A' — directional fact storage in weights and its knowledge-editing consequences."
---
> **One-paragraph hook:** Fine-tune a model on "Uriah Hawthorne is the composer of Abyssal Melodies," then ask "Who composed Abyssal Melodies?" You get chance-level accuracy, nowhere near the near-100% you'd expect for a fact it was just trained on. LLMs store facts directionally, keyed on the order they appeared in training. You can't paraphrase your way out of it. It comes from autoregressive training itself, it shows up at GPT-4 scale, and it matters for knowledge editing, synthetic data design, and why parametric memory alone isn't enough.

## The mechanism
Berglund et al. 2023 ("The Reversal Curse: LLMs trained on 'A is B' fail to learn 'B is A'") used [[Concept - Supervised Fine-Tuning (SFT)]] on synthetic facts of the form "A is B": fictional people and fictional occupations, novel on purpose so the reverse fact couldn't have leaked in from pretraining. Then they tested the reverse, "Who is B?" Accuracy and log-probability for the *correct* reverse answer were statistically no better than for a random name. The model hadn't formed a weak reverse association; it had formed none.

The cause is how [[Concept - Backpropagation]] updates weights under next-token prediction. Training on "A is B" only computes and backpropagates the gradient for $P(B \mid \text{context ending in A})$. The loss never constructs $P(A \mid \text{context ending in B})$, so gradient descent never sees it. If the MLP layers store facts as something like directional key→value lookups (key "A", value "B"), the training that would write the reverse key ("B" → "A") never runs. The asymmetry is built into what autoregressive pretraining optimizes, so more data doesn't remove it.

Keep this separate from [[Concept - Induction Heads]], the in-context copying circuitry that lets a model use a fact *within* one context whichever direction it's presented in. The curse is about what pretraining gradients write into the weights, not what the model can do in-context at inference.

Within the range Berglund et al. studied, neither scale nor paraphrase augmentation fixes it. Bigger models don't form the reverse association, and rephrasing "A is B" a dozen ways during training still only trains the forward direction.

## In practice
The effect holds at frontier scale on real, naturally occurring facts, beyond synthetic fine-tuning setups. GPT-4 answers "Who is Tom Cruise's mother?" correctly around 79% of the time, but "Who is Mary Lee Pfeiffer's son?" (same fact, reversed) only about 33% of the time. The gap is smallest for pairs where both directions co-occur densely in pretraining data (celebrities discussed both ways all the time) and largest for facts almost always stated in one canonical direction.

## Failure modes
The biggest downstream failure is in **knowledge editing**. Patch a new or corrected fact into a model in one direction and the edit doesn't reach the reverse query. You have to edit both directions explicitly, which doubles the surface of every factual update and makes "the model now knows X" a claim that only holds in one direction. It's a close cousin of [[Concept - Catastrophic Forgetting]]: in both, updating a model's knowledge is brittle and narrowly scoped.

It's also a concrete argument for why [[Deep Dive - RAG Architectures]] stays necessary as context windows and parametric capacity grow. Retrieval puts the fact in front of the model in whatever direction the query needs at inference, so asymmetric storage stops mattering and you don't have to hope both directions were memorized. Directional storage is one of several unresolved threads under hallucination as an open problem in [[Reference - Open Problems in LLM Engineering]].

## The non-obvious
The reversal curse is a special case of a broader, more unsettling pattern: models store what they were trained to *predict*, not the logical closure of what they were trained on. Allen-Zhu & Li's "Physics of Language Models" work on knowledge extraction makes the same point from another side. Whether a fact is *stored* in the weights (probeable, present somewhere among the overlapping feature directions of [[Concept - Superposition]]) is a different question from whether it's *extractable* by ordinary generation through the forward-prediction pathway the model uses at inference. The reversal curse says that gap can be total. For a truly one-directional fact, the reverse isn't stored but hard to reach; the forward-only gradient never wrote it at all.

The lesson for anyone building [[Concept - Synthetic Training Data]]: state every fact you care about in both directions explicitly. "The model will infer the symmetric case" is false, not merely weak.

## Connections
- [[Concept - Induction Heads]] — the in-context copying mechanism that lets a model use a fact within a single context regardless of direction, in contrast to the directional way facts are baked into weights during training.
- [[Deep Dive - RAG Architectures]] — retrieval sidesteps directional parametric storage by re-presenting facts at query time in whatever direction is needed.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the training stage where this pathology is easiest to reproduce and where practitioners most often get bitten by it when writing synthetic fact data.
- [[Concept - Backpropagation]] — the mechanism (gradients only flow for the direction actually predicted) that makes the curse structural rather than a data-quantity problem.
- [[Concept - Synthetic Training Data]] — the practical lever: state facts bidirectionally in generated training data, because the model will not infer the reverse on its own.
- [[Reference - Open Problems in LLM Engineering]] — hallucination and knowledge-storage brittleness are open problems this note's directional-storage finding directly informs.
- [[Concept - Superposition]] — the representational substrate of overlapping feature directions that directional key-value lookups live inside.
- [[Concept - Catastrophic Forgetting]] — knowledge editing's failure to propagate across direction is a close cousin of the broader problem that updating a model's knowledge is brittle and narrowly scoped.

## Sources
- Berglund et al. (2023) — The Reversal Curse: LLMs Trained on "A is B" Fail to Learn "B is A". The core synthetic-fact experiment and the GPT-4 Tom Cruise measurement.
- Allen-Zhu & Li (2023–2024) — Physics of Language Models (knowledge storage and extraction series). The storage-vs-extractability framing this note contrasts the curse against.
