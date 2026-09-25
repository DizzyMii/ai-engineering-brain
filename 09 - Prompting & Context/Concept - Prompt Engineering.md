---
tags: [concept, domain/prompting-context, level/surface]
aliases: [prompting, prompt design]
summary: "A prompt is prior tokens shifting P(next token | context) at inference time — no weights change; conditioning, not configuration."
---
> **One-paragraph hook:** Every "prompt engineering trick" comes down to one fact. An LLM computes a probability distribution over the next token given everything before it, and a prompt is more tokens in that "everything before it." There's no parser, no config file, no hidden API that clever phrasing invokes. You steer a learned function by choosing its input. Engineers who think this way can reason about why a prompt broke; the rest are pattern-matching on folklore.

## The mechanism

A decoder-only LLM (see the [[Deep Dive - The Transformer]]) is trained to model $P(x_{t} \mid x_{<t})$, the probability of the next token given all the previous ones. It generates by sampling from that distribution (via [[Concept - Softmax]] over the output logits) and appending the result to the context, over and over. A prompt is a choice of $x_{<t}$: the fixed prefix you supply before generation starts. Change the prompt and you change the conditioning event, and with it the whole distribution the model samples from. **No parameters move.** That's the difference from [[Concept - Supervised Fine-Tuning (SFT)]] or RLHF, which permanently reshape $P_\theta$. Prompting only picks a different input to the same frozen $\theta$, so it's reversible, costs zero training compute, and stops having any effect the moment the tokens leave the context window.

A prompt has parts, and each one pulls a different lever on the output distribution:
- **Role/system framing** sets persona and priority (see [[Concept - System Prompts]]).
- **Task instruction** is the literal ask.
- **Supplied context/inputs** are the data the task works on.
- **Few-shot exemplars** condition format and, weakly, content (see [[Concept - In-Context Learning]]).
- **Output-format cue** (a schema, a delimiter, "respond in JSON") narrows the distribution to a parseable shape.

Why does any of this work instead of the model free-associating? Pretraining corpora are full of instruction-shaped and QA-shaped text (documentation, forums, textbooks), so the base distribution already puts *some* mass on "answer the question that follows." Supervised fine-tuning and RLHF then sharpen $P(\text{good response} \mid \text{instruction})$ specifically. They're why "answer this" reliably gets an answer and not a continuation of the question. So prompting exploits a *learned behavior* that post-training installed; there's no hardcoded interpreter. In practice, a prompt that works beautifully on an instruction-tuned model can fail completely on the base checkpoint it came from, because the base model was never trained to favor that behavior.

## In practice

Be honest about which levers have a mechanism and which are perishable folklore. Mechanism-backed: explicit structure and delimiters, worked examples, task decomposition, and asking for intermediate reasoning (see [[Concept - Chain-of-Thought and Why It Works]]). These shift the token distribution in principled, reproducible ways. Folklore: "you are a world-class expert", tipping the model $200, threatening it. The evidence for these is anecdotal and model-version-dependent at best (`Lore - Let's Think Step by Step` sorts what's proven from what's vibes). Build production systems on the first group. If you use the second, measure it per model version; don't assume it transfers.

Prompting is the cheap bottom rung of an escalation ladder. Compared with the options in [[Decision - Fine-Tuning vs RAG vs Prompting]], it needs no training infrastructure and is instantly reversible. But it costs tokens on every call forever (the instructions run again on every request), it can't teach new knowledge, and it can't reliably override behavior post-training baked in. When a prompt has to grow long and elaborate to force a behavior, that's a sign you may be fighting the model's priors, and a cue to consider moving up the ladder.

## Failure modes

- **Contradictory instructions.** Two rules that can't both hold ("be concise" + "explain your full reasoning in detail") resolve unpredictably. The model picks one based on training-data frequency, not your intent. Detection: contradictions show up as inconsistent outputs across near-identical inputs. Fix by stating the priority.
- **Over-specification.** Piling on caveats and edge cases dilutes the instruction that matters and eats context budget for little gain (see [[Concept - Context Engineering]]). More instructions don't buy more control.
- **Literal-wording satisficing.** Models optimize the prompt you *wrote*, not the one you *meant*. Ambiguous pronouns, underspecified formats and unstated assumptions get resolved however training makes most probable, which often isn't what you wanted.
- **Assuming determinism.** The same prompt doesn't guarantee the same output. Even at temperature 0 with a fixed seed, provider-side nondeterminism (dynamic batch composition, MoE expert routing that depends on what else is in the batch; see [[Concept - Sampling and Decoding Parameters]]) leaks through in production serving. Never write a test suite that asserts exact-string equality against a live API.

## The non-obvious

The costliest mistake staff engineers make is outside the prompt text: treating prompting as a black art when it's an empirical science with a frozen, testable function underneath. Since $P_\theta$ is fixed, a prompt's effect is in principle fully reproducible under the same decoding settings. So prompt behavior should be regression-tested like code, not hand-tuned by feel and shipped. Teams that skip this learn the hard way when a provider swaps the model checkpoint and their prompts silently regress. The prompt didn't change. $P_\theta$ did.

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
