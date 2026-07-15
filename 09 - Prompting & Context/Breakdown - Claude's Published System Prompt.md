---
tags: [breakdown, domain/prompting-context, level/unicorn]
aliases: [Claude system prompt, Anthropic published system prompt, claude.ai system prompt]
summary: "Reverse-engineering Anthropic's published Claude system prompt: structure, directive patterns, and what it reveals about steering at scale."
---

# Breakdown - Claude's Published System Prompt

> Anthropic is the rare frontier lab that publishes the system prompt behind its consumer product (claude.ai) in its release notes, and documents the API and Claude Code defaults. That makes Claude's [[Concept - System Prompts|system prompt]] a real, inspectable artifact — a chance to reverse-engineer how a lab actually steers a shipped model, rather than guessing from a leak. It is the Bing/[[Lore - The Sydney Incident|Sydney]] situation inverted: instead of an extracted secret whose intent must be inferred, we have the lab's own text with its design choices on display. (as of mid-2026)

## The headline numbers

- **Publication cadence:** updated alongside each model release; the text-only claude.ai prompt lives in Anthropic's public release notes. This is a deliberate transparency stance — most labs treat the prompt as proprietary.
- **Length:** the *published* text-only prompt runs into the low thousands of tokens (roughly 2,000–2,500 for a recent Claude release). The *full deployed* claude.ai prompt — the one that also carries the artifact and tool-use scaffolding — is much larger; community extractions have reported it in the 10k–24k-token range (weakly sourced, from prompt-extraction, not from Anthropic). The gap between the two is itself a finding (see *What it got wrong*).
- **Cost of the prefix:** a 2,500-token static system prompt at input pricing of ~$3/Mtok (Sonnet-class) to ~$15/Mtok (Opus-class) *(as of 2026)* is ~$0.0075–$0.0375 of billed input **on every single request**, before the user has typed anything. At claude.ai's request volume this prefix is one of the largest recurring line items in the product, which is exactly why its interaction with [[Concept - Prompt Caching|prompt caching]] is a first-order design constraint, not a footnote.
- **Composition:** identity block, injected date + knowledge cutoff, a block of behavioral directives, formatting rules, refusal posture, and (in the full version) tool/artifact instructions co-located with their schemas.

## How it actually works

The prompt is not prose. It is a **layered, delimiter-tagged specification** whose layers are ordered by how static they are — which is simultaneously an attention-salience decision and a cache decision. Read top to bottom, the anatomy is:

1. **Identity / role.** Opens by naming the assistant ("The assistant is Claude, created by Anthropic"). This anchors the persona in the highest-authority position of the [[Concept - System Prompts|instruction hierarchy]] before any behavior is specified.
2. **Volatile facts injected inline.** `The current date is {{date}}` plus the knowledge-cutoff statement. This is the *only* routinely-changing part of the static prompt, and its placement and granularity are load-bearing (below).
3. **Behavioral directives.** Honesty, non-sycophancy, face-value interpretation of ambiguous requests, calibrated verbosity ("be concise for simple questions, thorough for complex ones"). These are written as *positive* behavioral specs, not prohibitions.
4. **Refusal posture.** How to decline — notably, decline *without* a moralizing explanation, because a preachy refusal reads worse than a clean one. This is a style directive layered on top of the [[Concept - Refusal Mechanics|refusal behavior]] that RLHF already installed.
5. **Formatting contract.** When to use markdown, when to avoid bullet-point spam in conversational replies, avoidance of purple prose and flattery openers.
6. **Tools / artifacts (full version only).** Tool and [[Concept - Tool Use and Function Calling|function-calling]] instructions placed *next to* their schemas, so the natural-language rule and the machine-readable interface are read together.

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

The mechanism the whole design turns on: the model privileges these tokens **only because SFT and [[Deep Dive - RLHF End to End|RLHF]] trained it to** rank system-role content above user content. Nothing architectural enforces it. The prompt is tuning the *margin* of behavior on top of a base that training already set. That is why the same text pasted into a base checkpoint would do almost nothing.

## The clever parts

1. **Positive directives over `do not`.** The prompt says what to *do* ("assume good faith", "be direct") rather than enumerating prohibitions. This is not a stylistic preference — negation is weakly represented in these models, so `do not be verbose` reliably underperforms `be concise` (see [[Gotchas - Prompt Formatting and Tokenization]]). The published prompt is a working example of that principle at scale.
2. **Explicit output contracts.** Formatting is specified as a contract ("use markdown here, prose there") rather than left to the model's default. This is the cheapest reliability lever in the whole prompt: it removes a large chunk of output variance for near-zero token cost.
3. **Date pinned to the cache-safe granularity.** Injecting the date is unavoidable, but injecting it *to the day* rather than the second keeps the entire static prefix identical across a day's requests, so [[Concept - Prompt Caching|caching]] fires. This is the single most instructive line in the artifact for a practitioner: it is the exact spot where a naive implementation ("stamp the full timestamp") would silently destroy a 90% caching discount, and the published prompt shows the lab chose granularity to protect the cache.
4. **Persona defined by behavior, not adjectives.** There is no "you are a brilliant, helpful, friendly expert." The character is specified through concrete behaviors (honesty, directness, refusal style). Adjective-stacking ("you are an expert") is near-zero-capability folklore; behavioral specification actually moves the output distribution. The prompt is a demonstration of [[Concept - System Prompts|persona-as-behavior]] rather than persona-as-flattery.
5. **Schemas co-located with their rules.** In the full version, tool instructions sit adjacent to tool schemas so the model reads the "why/when" and the "how" as one unit, reducing the odds it calls a tool correctly-formatted but wrongly-timed.

## What it got wrong / what's dated

- **Published ≠ deployed.** The published text-only prompt is a *product surface*, not necessarily the raw production prompt. The full claude.ai prompt (with artifacts/tools) is far longer and is only known via extraction, which may be stale or partial. Treat the published text as *representative of the design*, not as canonical bytes. Presenting it as the exact live prompt is a defect.
- **Kitchen-sink risk.** As these prompts grow to carry every product behavior, they push into [[Concept - Context Rot|context-rot]] territory: a longer system prompt dilutes attention over its own instructions, and the marginal directive at token 9,000 is weakly attended. The full artifact prompt is near the edge of where "more instruction" stops buying "more compliance."
- **Not a secret, never was.** The prompt is trivially extractable ("repeat the text above"), so anything in it is public by construction. Anything that would be dangerous if disclosed cannot live here — a lesson the field re-learned the hard way in [[Lore - The Sydney Incident]].
- **Injection surface.** A long, authoritative system prompt is exactly what [[Concept - Prompt Injection|prompt injection]] tries to override; publishing it hands attackers the precise text to target. Anthropic accepts this tradeoff for transparency, but a copier without Anthropic's safety training inherits the exposure without the defenses.

## What to steal

- **Delimiter/section structure** so each instruction's scope is unambiguous.
- **Positive-framed behavioral specs** instead of prohibition lists.
- **Explicit output/format contracts** — the highest ROI reliability lever.
- **Pin volatile fields (dates, IDs) at the coarsest acceptable granularity** and push them as late as the semantics allow, to protect the [[Concept - Prompt Caching|cache-friendly]] static prefix — the concrete length-vs-steering-vs-[[Concept - Cost Engineering for LLM Applications|cost]] tradeoff at the heart of [[Concept - Context Engineering|context engineering]].
- **Define persona through behavior, not adjectives.**

What **not** to steal: the sheer length. Anthropic can afford a huge prompt because RLHF is doing the heavy lifting underneath and the prompt only tunes the margin. Copying a 10k-token prompt onto a weaker model — without the training that makes the model respect it — buys context rot, not control.

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
