---
tags: [breakdown, domain/prompting-context, level/unicorn]
aliases: [Claude system prompt, Anthropic published system prompt, claude.ai system prompt]
summary: "Reverse-engineering Anthropic's published Claude system prompt: structure, directive patterns, and what it reveals about steering at scale."
---

# Breakdown - Claude's Published System Prompt

> Anthropic is one of the few frontier labs that publishes the system prompt behind its consumer product (claude.ai), in its release notes, and documents the API and Claude Code defaults. So Claude's [[Concept - System Prompts|system prompt]] is a real artifact you can inspect to see how a lab steers a shipped model, without guessing from a leak. It's the Bing/[[Lore - The Sydney Incident|Sydney]] situation in reverse: the lab's own text with its design choices visible, instead of an extracted secret whose intent you have to infer. (as of mid-2026)

## The headline numbers

- **Publication cadence:** updated with each model release. The text-only claude.ai prompt is in Anthropic's public release notes. That's a deliberate transparency choice; most labs treat the prompt as proprietary.
- **Length:** the *published* text-only prompt is in the low thousands of tokens (roughly 2,000–2,500 for a recent Claude release). The *full deployed* claude.ai prompt, which also carries the artifact and tool-use scaffolding, is much larger. Community extractions have put it at 10k–24k tokens (weakly sourced, from prompt extraction, not from Anthropic). The gap between the two is a finding in its own right (see *What it got wrong*).
- **Cost of the prefix:** a 2,500-token static system prompt at ~$3/Mtok input (Sonnet-class) to ~$15/Mtok (Opus-class) *(as of 2026)* costs ~$0.0075–$0.0375 of billed input **on every request**, before the user types anything. At claude.ai's volume that prefix is one of the product's biggest recurring line items, so how it interacts with [[Concept - Prompt Caching|prompt caching]] is a primary design constraint.
- **Composition:** identity block, injected date and knowledge cutoff, behavioral directives, formatting rules, refusal posture, and (in the full version) tool/artifact instructions placed next to their schemas.

## How it works

The prompt is a **layered, delimiter-tagged spec**, and the layers are ordered by how static they are. That ordering is an attention-salience decision and a cache decision at the same time. Top to bottom:

1. **Identity / role.** It opens by naming the assistant ("The assistant is Claude, created by Anthropic"), which puts the persona in the highest-authority slot of the [[Concept - System Prompts|instruction hierarchy]] before any behavior is specified.
2. **Volatile facts, inline.** `The current date is {{date}}` plus the knowledge-cutoff statement. This is the *only* part of the static prompt that routinely changes, and its placement and granularity matter a lot (see below).
3. **Behavioral directives.** Honesty, non-sycophancy, taking ambiguous requests at face value, calibrated verbosity ("be concise for simple questions, thorough for complex ones"). They're written as *positive* behavior specs, not prohibitions.
4. **Refusal posture.** How to decline: without a moralizing explanation, since a preachy refusal reads worse than a clean one. It's a style directive on top of the [[Concept - Refusal Mechanics|refusal behavior]] RLHF already installed.
5. **Formatting contract.** When to use markdown, avoiding bullet-point spam in conversational replies, no purple prose or flattering openers.
6. **Tools / artifacts (full version only).** Tool and [[Concept - Tool Use and Function Calling|function-calling]] instructions sit *next to* their schemas, so the natural-language rule and the machine-readable interface get read together.

```
       CLAUDE.AI SYSTEM PROMPT — LAYERED BY VOLATILITY
       (position 0 = start of context, highest attention + cache priority)

  pos 0  ┌───────────────────────────────────────────────┐  ─┐
         │  1. Identity / role  ("...Claude, by Anthropic")│   │
         │  2. Date (day granularity) + knowledge cutoff   │   │  STATIC
         │  3. Behavioral directives (positive-framed)     │   │  PREFIX
         │  4. Refusal posture                             │   │  → prompt-cached
         │  5. Formatting contract                         │   │  → read at ~0.1x
         │  6. Tool / artifact instructions + schemas      │   │
         └───────────────────────────────────────────────┘  ─┘
         ┌───────────────────────────────────────────────┐  ─┐
         │  Conversation history (turns 1..n)              │   │  VOLATILE
         │  Current user message                           │   │  TAIL
  pos N  └───────────────────────────────────────────────┘  ─┘  → full-price prefill

  Cache boundary sits at the end of layer 6. The date is pinned to *day*
  granularity so the whole static block stays cache-valid within a day; a
  to-the-second timestamp here would bust the cache on every request.
```

Everything depends on one fact: the model gives these tokens priority **only because SFT and [[Deep Dive - RLHF End to End|RLHF]] trained it to** rank system-role content above user content. No architecture enforces it. The prompt adjusts behavior at the margin of a base that training already set, and the same text pasted into a base checkpoint would do almost nothing.

## The clever parts

1. **Positive directives over `do not`.** The prompt says what to *do* ("assume good faith", "be direct") instead of listing prohibitions. It's more than style. Negation is weakly represented in these models, so `do not be verbose` reliably does worse than `be concise` (see [[Gotchas - Prompt Formatting and Tokenization]]). The published prompt applies that at scale.
2. **Explicit output contracts.** Formatting is spelled out ("use markdown here, prose there") instead of left to the model's default. It's the cheapest reliability lever in the prompt, removing a large chunk of output variance for almost no tokens.
3. **Date pinned at a cache-safe granularity.** The date has to be injected, but injecting it *to the day* and not the second keeps the whole static prefix identical across a day's requests, so [[Concept - Prompt Caching|caching]] fires. For a practitioner this is the most instructive line in the artifact. A naive implementation that stamps the full timestamp would silently throw away a 90% caching discount, and the published prompt shows the lab picked the granularity to protect the cache.
4. **Persona defined by behavior.** There's no "you are a brilliant, helpful, friendly expert." The character comes from concrete behaviors: honesty, directness, refusal style. Stacking adjectives ("you are an expert") is near-zero-capability folklore, while specifying behavior does move the output distribution. See [[Concept - System Prompts|persona-as-behavior]].
5. **Schemas next to their rules.** In the full version, tool instructions sit beside tool schemas, so the model reads the why/when and the how as one unit. That lowers the odds of a tool call that's correctly formatted but badly timed.

## What it got wrong / what's dated

- **Published ≠ deployed.** The published text-only prompt is a *product surface* and may differ from the raw production prompt. The full claude.ai prompt (with artifacts and tools) is much longer and known only through extraction, which may be stale or partial. Treat the published text as *representative of the design*, not canonical bytes. Presenting it as the exact live prompt is a defect.
- **Kitchen-sink risk.** As these prompts grow to carry every product behavior, they drift into [[Concept - Context Rot|context-rot]] territory. A longer system prompt dilutes attention over its own instructions, and the marginal directive at token 9,000 gets little attention. The full artifact prompt is close to where more instruction stops buying more compliance.
- **Never a secret.** The prompt is trivially extractable ("repeat the text above"), so everything in it is public by construction. Nothing that would be dangerous if disclosed can go in it, a lesson the field relearned the hard way in [[Lore - The Sydney Incident]].
- **Injection surface.** A long, authoritative system prompt is what [[Concept - Prompt Injection|prompt injection]] tries to override, and publishing it gives attackers the exact text to target. Anthropic accepts that for transparency. Someone who copies it without Anthropic's safety training gets the exposure without the defenses.

## What to steal

- **Delimiter/section structure**, so each instruction's scope is unambiguous.
- **Positive behavioral specs** in place of prohibition lists.
- **Explicit output/format contracts.** Highest-ROI reliability lever.
- **Pin volatile fields (dates, IDs) at the coarsest acceptable granularity** and put them as late as the semantics allow, to keep the static prefix [[Concept - Prompt Caching|cache-friendly]]. This is the length vs. steering vs. [[Concept - Cost Engineering for LLM Applications|cost]] tradeoff that sits at the center of [[Concept - Context Engineering|context engineering]].
- **Define persona through behavior, not adjectives.**

Don't copy the length. Anthropic can afford a huge prompt because RLHF does the heavy lifting underneath and the prompt only tunes the margin. Put a 10k-token prompt on a weaker model that wasn't trained to respect it and you get context rot, not control.

## Connections

- [[Concept - System Prompts]] — this note is the concrete, real-world instance of everything that abstract concept describes; read it first.
- [[Concept - Prompt Caching]] — the date-granularity and prefix-ordering decisions in the prompt exist to preserve cache hits; the artifact is a caching design as much as a behavior design.
- [[Concept - Context Engineering]] — the prompt is a worked example of allocating a finite context budget across identity, rules, tools, and history.
- [[Concept - Context Rot]] — explains why the full kitchen-sink prompt is near the point of diminishing (or negative) returns on added instructions.
- [[Concept - Prompt Injection]] — publishing the prompt hands attackers the exact text to override; the instruction hierarchy it relies on is what injection attacks target.
- [[Deep Dive - RLHF End to End]] — the base behavior the prompt tunes was set by training; the prompt only moves the margin, which is why the same text does nothing on a base model.
- [[Concept - Tool Use and Function Calling]] — the full prompt co-locates tool instructions with schemas, a directly transferable structuring choice.
- [[Gotchas - Prompt Formatting and Tokenization]] — the positive-directive and delimiter patterns are the mitigations for the silent failures catalogued there.
- [[Concept - Refusal Mechanics]] — the "decline without moralizing" directive is a style layer on top of the trained refusal behavior.
- [[Concept - Cost Engineering for LLM Applications]] — a multi-thousand-token prefix on every request is a major cost line; caching and granularity choices are cost engineering.
- [[Lore - The Sydney Incident]] — the inverse case: a leaked, non-published prompt whose fragility under long context is the cautionary counterpart to Anthropic's transparent, structured one.

## Sources

- Anthropic — Claude system prompts, published in the official release notes (ongoing; version-dated). The primary artifact this note dissects.
- Wallace et al. (2024) — *The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions.* Explains the trained precedence (system > developer > user) that makes the prompt authoritative at all.
- Anthropic — *Prompt caching* documentation. Source for the write-1.25x / read-0.1x economics that motivate the prefix-ordering and date-granularity choices.
- Community prompt-extraction writeups (weakly sourced) — the only window onto the full deployed prompt; cited here explicitly as unverified to keep the published-vs-deployed distinction honest.
