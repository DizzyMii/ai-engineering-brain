---
tags: [moc, domain/prompting-context, level/surface]
aliases: []
summary: "Map of prompt engineering, context management, caching, formatting, and reliability techniques for working with LLMs."
---

# MOC - Prompting & Context

This domain owns everything about shaping what goes into a model's context window and how that shaping changes what comes out: prompt construction, in-context learning, chain-of-thought reasoning, context engineering for long-running agentic loops, caching strategies that cut cost and latency, and the formatting and tokenization details that silently break reliability. It matters because the prompt and its surrounding context are the only input surface most practitioners ever touch — the weights are fixed, so what you put in the window is the whole lever. Small, cosmetic-looking choices (whitespace, delimiter, example order, token boundaries) can swing benchmark scores by double digits, and context that grows past a model's effective working range degrades quality well before it hits the stated token limit. The notes here run from the surface mechanics of writing a good prompt through the internals of why long contexts rot, to the frontier problem of managing context across hundred-turn agent runs, and end in unicorn-tier arcana: real production system prompts and the famous incidents that shaped how the industry thinks about them.

## Start here

- **Surface:** [[Concept - Prompt Engineering]] — what prompting is and why it's the primary lever on LLM behavior.
- **Core:** [[Concept - Context Engineering]] — the practitioner's job of curating what fills the window, not just what you type first.
- **Advanced:** [[Concept - Context Rot]] — the mechanism behind quality decay as context grows, and why "it fits" isn't "it works."
- **Frontier:** [[Concept - Prompting Reasoning Models]] — how reasoning-tuned models break the prompting conventions built for base chat models.
- **Unicorn:** [[Breakdown - Claude's Published System Prompt]] — a real production system prompt, reverse-engineered line by line.

## Prompting fundamentals

- [[Concept - Prompt Engineering]] — the discipline of shaping inputs to reliably steer model outputs; the entry point for the rest of this domain.
- [[Concept - System Prompts]] — the privileged instruction channel that sets persona, constraints, and tools before the user types a word.
- [[Concept - In-Context Learning]] — how transformers pick up a task from examples in the prompt alone, with no gradient update.
- [[Reference - Prompting Techniques Catalog]] — a lookup table of named prompting techniques and when each one actually earns its keep.

## Chain-of-thought and reasoning

- [[Concept - Chain-of-Thought and Why It Works]] — the mechanism behind letting a model "think out loud" before answering, and why it improves multi-step accuracy.
- [[Decision - When to Use Chain-of-Thought]] — a decision flow for when explicit reasoning traces help versus when they just burn tokens.
- [[Concept - Prompting Reasoning Models]] — why reasoning-tuned models need prompting conventions different from base chat models.
- [[Concept - Few-Shot Example Selection and Ordering]] — how which examples you pick and the order you place them in measurably changes accuracy.
- [[Lore - Let's Think Step by Step]] — the origin story of the phrase that accidentally became a reproducible accuracy hack.

## Context engineering and management

- [[Concept - Context Engineering]] — the practice of curating what fills the context window over an agent's lifetime, not just the initial prompt.
- [[Concept - Context Rot]] — why model quality degrades as context length grows, even well within the stated window limit.
- [[Concept - Context Compaction]] — techniques for summarizing or pruning long-running agent context so it stays under budget and useful.
- [[Gotchas - Long-Context and Context Windows]] — the recurring pitfalls (lost-in-the-middle, needle-in-haystack failures) that catch engineers off guard.

## Prompt caching and cost

- [[Concept - Prompt Caching]] — how providers cache the KV state of a repeated prefix to cut latency and cost on long, stable system prompts.
- [[Reference - Prompt Caching Across Providers]] — a comparison table of cache TTLs, pricing, and minimum prefix lengths across major API providers.

## Formatting, tokenization, and templates

- [[Concept - Chat Templates and Special Tokens]] — the exact token scaffolding every chat model is trained on, and why mismatches silently break it.
- [[Concept - Prompt Formatting and Sensitivity]] — why cosmetic changes to whitespace, delimiters, or ordering can swing model outputs.
- [[Gotchas - Prompt Formatting and Tokenization]] — a running list of formatting mistakes that quietly degrade output quality.
- [[Snippet - Prefilling the Assistant Turn]] — runnable code for seeding the start of a model's response to force format or persona compliance.

## Reliability, evaluation, and structured output

- [[Playbook - Reliable Structured Output]] — an end-to-end procedure for getting valid, schema-conformant output out of an LLM every time.
- [[Concept - Prompt Evaluation and Versioning]] — how to treat prompts like code: tested, versioned, and regression-checked as models change underneath them.

## Case studies and war stories

- [[Breakdown - Claude's Published System Prompt]] — a reverse-engineered walkthrough of a real production system prompt and what its structure reveals.
- [[Lore - The Sydney Incident]] — the Bing/Sydney meltdown, and what it taught the industry about persona control and system prompt leakage.

## Adjacent domains

- [[MOC - Agents]] — context engineering and tool-use prompting extend directly into the agent loop.
- [[MOC - Inference & Serving]] — prompt caching rides on the same KV cache mechanics that drive serving cost and latency.
- [[MOC - Safety & Interpretability]] — system prompt design and formatting choices are the first line of defense against prompt injection and jailbreaks.
