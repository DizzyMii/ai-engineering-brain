---
tags: [moc, domain/prompting-context, level/surface]
aliases: []
summary: "Map of prompt engineering, context management, caching, formatting, and reliability techniques for working with LLMs."
---

# MOC - Prompting & Context

This domain covers what goes into a model's context window and how that changes what comes out: prompt construction, in-context learning, chain-of-thought, context engineering for long-running agent loops, caching that cuts cost and latency, and the formatting and tokenization details that silently break reliability. For most practitioners the prompt and its context are the only input they ever touch. The weights are fixed, so the window is all you've got. Cosmetic-looking choices (whitespace, delimiter, example order, token boundaries) can move benchmark scores by double digits, and context that grows past a model's effective working range hurts quality well before the stated token limit.

The notes go from the basics of writing a good prompt, through why long contexts rot, to managing context across hundred-turn agent runs, and finish with real production system prompts and the incidents that shaped how the industry thinks about them.

## Start here

- **Surface:** [[Concept - Prompt Engineering]]: what prompting is and why it's the main lever on LLM behavior.
- **Core:** [[Concept - Context Engineering]]: curating everything that fills the window, beyond what you type first.
- **Advanced:** [[Concept - Context Rot]]: why quality decays as context grows, and why "it fits" isn't "it works."
- **Frontier:** [[Concept - Prompting Reasoning Models]]: how reasoning-tuned models break the prompting conventions built for base chat models.
- **Unicorn:** [[Breakdown - Claude's Published System Prompt]]: a real production system prompt, taken apart line by line.

## Prompting fundamentals

- [[Concept - Prompt Engineering]]: shaping inputs to steer model outputs reliably. Start here for the rest of the domain.
- [[Concept - System Prompts]]: the privileged instruction channel that sets persona, constraints and tools before the user types anything.
- [[Concept - In-Context Learning]]: how transformers pick up a task from examples in the prompt, with no gradient update.
- [[Reference - Prompting Techniques Catalog]]: a lookup table of named prompting techniques and when each is worth using.

## Chain-of-thought and reasoning

- [[Concept - Chain-of-Thought and Why It Works]]: why letting a model "think out loud" before answering improves multi-step accuracy.
- [[Decision - When to Use Chain-of-Thought]]: a decision flow for when explicit reasoning helps and when it just burns tokens.
- [[Concept - Prompting Reasoning Models]]: why reasoning-tuned models need different prompting conventions from base chat models.
- [[Concept - Few-Shot Example Selection and Ordering]]: which examples you pick, and their order, measurably changes accuracy.
- [[Lore - Let's Think Step by Step]]: how one phrase accidentally became a reproducible accuracy hack.

## Context engineering and management

- [[Concept - Context Engineering]]: curating what fills the context window over an agent's whole lifetime, beyond the initial prompt.
- [[Concept - Context Rot]]: why quality degrades as context grows, even well inside the stated window.
- [[Concept - Context Compaction]]: summarizing or pruning long-running agent context so it stays under budget and useful.
- [[Gotchas - Long-Context and Context Windows]]: recurring pitfalls (lost-in-the-middle, needle-in-haystack failures) that catch engineers off guard.

## Prompt caching and cost

- [[Concept - Prompt Caching]]: providers cache the KV state of a repeated prefix to cut latency and cost on long, stable system prompts.
- [[Reference - Prompt Caching Across Providers]]: cache TTLs, pricing and minimum prefix lengths compared across the major API providers.

## Formatting, tokenization, and templates

- [[Concept - Chat Templates and Special Tokens]]: the token scaffolding every chat model is trained on, and why mismatches silently break it.
- [[Concept - Prompt Formatting and Sensitivity]]: why cosmetic changes to whitespace, delimiters or ordering can swing outputs.
- [[Gotchas - Prompt Formatting and Tokenization]]: formatting mistakes that degrade output without any error.
- [[Snippet - Prefilling the Assistant Turn]]: runnable code that seeds the start of the response to force format or persona compliance.

## Reliability, evaluation, and structured output

- [[Playbook - Reliable Structured Output]]: an end-to-end procedure for getting valid, schema-conformant output from an LLM every time.
- [[Concept - Prompt Evaluation and Versioning]]: treating prompts like code, tested, versioned and regression-checked as the models underneath change.

## Case studies and war stories

- [[Breakdown - Claude's Published System Prompt]]: a walkthrough of a real production system prompt and what its structure shows.
- [[Lore - The Sydney Incident]]: the Bing/Sydney meltdown and what it taught the industry about persona control and system prompt leakage.

## Adjacent domains

- [[MOC - Agents]]: context engineering and tool-use prompting carry straight into the agent loop.
- [[MOC - Inference & Serving]]: prompt caching uses the same KV cache mechanics that drive serving cost and latency.
- [[MOC - Safety & Interpretability]]: system prompt design and formatting are the first line of defense against prompt injection and jailbreaks.
