---
tags: [concept, domain/prompting-context, level/surface]
aliases: [prompting, prompt design]
summary: "A prompt is prior tokens shifting P(next token | context) at inference time — no weights change; conditioning, not configuration."
---
> **One-paragraph hook:** Every "prompt engineering trick" reduces to one fact: an LLM computes a conditional probability distribution over the next token given everything before it, and a prompt is just more tokens in that "everything before it." There is no parser, no config file, no hidden API being invoked by clever phrasing — you are steering a learned function by choosing its input. That framing is the difference between an engineer who can reason about why a prompt broke and one who is pattern-matching on folklore.

## The mechanism

A decoder-only LLM (see the [[Deep Dive - The Transformer]]) is trained to model $P(x_{t} \mid x_{<t})$ — the probability of the next token given all prior tokens — and generates by repeatedly sampling from that distribution (via [[Concept - Softmax]] over the output logits) and appending the result to the context. A prompt is nothing more than a choice of $x_{<t}$: the fixed prefix you supply before generation starts. Changing the prompt changes the conditioning event, which changes the whole distribution the model samples from. Critically, **no parameters move**. This is what separates prompting from [[Concept - Supervised Fine-Tuning (SFT)]] or RLHF — those permanently reshape the function $P_\theta$; prompting only ever selects a different input to the same frozen $\theta$. That's why prompting is reversible, why it costs zero training compute, and why its effect vanishes the instant the tokens leave the context window.

A prompt has anatomy, and each part is a distinct lever on the output distribution rather than an undifferentiated blob of text:
- **Role/system framing** — sets persona and priority (see [[Concept - System Prompts]]).
- **Task instruction** — the literal ask.
- **Supplied context/inputs** — the data the task operates over.
- **Few-shot exemplars** — demonstrations that condition format and, weakly, content (see [[Concept - In-Context Learning]]).
- **Output-format cue** — a schema, a delimiter, a "respond in JSON" — that narrows the distribution over token sequences to a parseable shape.

Why does any of this work at all, rather than the model just free-associating? Pretraining corpora are saturated with instruction-shaped and QA-shaped text (documentation, forums, textbooks), so the base distribution already has *some* mass on "answer the question that follows." Supervised fine-tuning and RLHF then sharpen $P(\text{good response} \mid \text{instruction})$ specifically — they are the reason "answer this" reliably produces an answer instead of a continuation of the question. Prompting therefore isn't hitting a hardcoded interpreter; it's exploiting a *learned behavior* that post-training installed. This matters practically: a prompt that works beautifully on an instruction-tuned model can fail entirely on the base checkpoint it was distilled from, because the base model was never trained to privilege that behavior.

## In practice

Be honest about what's real mechanism versus perishable folklore. Real, mechanism-backed levers: explicit structure and delimiters, worked examples, task decomposition, and asking for intermediate reasoning (see [[Concept - Chain-of-Thought and Why It Works]]) — these change the actual token distribution in principled, reproducible ways. Folklore-tier levers: "you are a world-class expert," tipping the model $200, or threatening it — these have anecdotal, model-version-dependent evidence at best (see `Lore - Let's Think Step by Step` for the fuller taxonomy of what's proven versus vibes). Treat the two categories differently: build production systems on the former, and if you use the latter, measure it per model version rather than assuming it transfers.

Prompting sits at the cheap end of an escalation ladder. Compared to [[Decision - Fine-Tuning vs RAG vs Prompting]], prompting requires zero training infrastructure and is instantly reversible, but it pays a *recurring* per-call token cost forever (the instructions re-run on every request) and it cannot teach genuinely new knowledge or reliably override behavior baked in by post-training. When a prompt has to get long and elaborate to force a behavior, that is itself a signal you may be fighting the model's priors rather than steering them — a decision point for moving up the ladder.

## Failure modes

- **Contradictory instructions.** Two rules in the same prompt that can't both be satisfied ("be concise" + "explain your full reasoning in detail") resolve unpredictably — the model picks one based on training-data frequency, not your intent. Detection: contradictions surface as inconsistent outputs across near-identical inputs; fix by explicitly prioritizing.
- **Over-specification.** Piling on caveats and edge cases dilutes the signal for the actually-important instruction and consumes context budget for marginal gain (see [[Concept - Context Engineering]]). More instructions is not more control.
- **Literal-wording satisficing.** Models optimize the prompt you *wrote*, not the one you *meant* — ambiguous pronouns, underspecified formats, and unstated assumptions get resolved in whatever way is most probable under training, which is often not what you wanted.
- **Assuming determinism.** The same prompt does not guarantee the same output. Even at temperature 0 with a fixed seed, provider-side nondeterminism (dynamic batch composition, MoE expert routing that depends on what else is in the batch — see [[Concept - Sampling and Decoding Parameters]]) leaks through in production serving. Never build a test suite that asserts exact-string equality against a live API.

## The non-obvious

The most consequential mistake staff engineers make isn't in the prompt text — it's treating prompting as a black art instead of an empirical science with a frozen, testable function underneath. Because $P_\theta$ is fixed, a prompt's effect is in principle fully reproducible given the same decoding settings, which means prompt behavior should be regression-tested exactly like code, not hand-tuned by vibes and shipped. Teams that skip this discover the hard way that "prompt engineering" silently regressed the moment a provider swapped the underlying model checkpoint — the prompt didn't change, but $P_\theta$ did.

## Connections
- [[Deep Dive - The Transformer]] — the architecture computing $P(x_t \mid x_{<t})$ that every prompting effect rides on.
- [[Concept - Softmax]] — the function turning logits into the probability distribution a prompt is steering.
- [[Concept - Supervised Fine-Tuning (SFT)]] — the training stage that installs the instruction-following behavior prompting exploits.
- [[Decision - Fine-Tuning vs RAG vs Prompting]] — where prompting sits on the cost/permanence ladder relative to the alternatives.
- [[Concept - Sampling and Decoding Parameters]] — why "same prompt" doesn't guarantee "same output" in production.
- [[Concept - Chain-of-Thought and Why It Works]] — the flagship example of a mechanism-backed (not folklore) prompting technique.
- [[Concept - Context Engineering]] — the discipline this note zooms into for curating everything else sharing the context window.
- [[Concept - System Prompts]] — the specific, privileged-by-training-not-architecture prompt segment that carries persona and rules.
- [[Concept - In-Context Learning]] — the mechanism behind the few-shot-exemplar lever in a prompt's anatomy.

## Sources
- Brown et al. (2020) — "Language Models are Few-Shot Learners" (GPT-3). Established that scale alone makes prompting, not just fine-tuning, a viable interface to a model.
- Wei et al. (2022) — "Finetuned Language Models Are Zero-Shot Learners" (instruction tuning). The post-training mechanism that makes "answer this" reliably work.
- Wallace et al. (2024) — "The Instruction Hierarchy." Formalizes why some prompt segments are trained to outrank others, relevant to why role framing has any authority at all.
