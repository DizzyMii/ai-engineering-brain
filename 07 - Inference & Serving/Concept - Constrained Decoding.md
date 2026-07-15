---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [guided decoding, grammar-constrained decoding, structured generation]
summary: "Masking invalid tokens' logits each decode step so generation is forced to conform to a JSON schema, regex, or CFG — a guarantee, not a hope."
---

> **One-paragraph hook:** Ask a model to "return valid JSON" and you get valid JSON most of the time — which is useless the moment you're parsing millions of tool calls. Constrained decoding turns "please" into "must" by intersecting the model's vocabulary with the set of tokens that keep the output grammatically legal at every single decode step, before the model ever samples. The model still picks *which* legal token to emit by its own probabilities; it simply cannot emit an illegal one. It's the mechanism behind reliable JSON mode, function-calling schemas, and regex-constrained extraction across [[Concept - Sampling and Decoding Parameters|every serving stack]] that offers a "structured output" API.

## The mechanism

At each decode step the sampler normally computes a full probability distribution over the vocabulary and draws from it (see [[Concept - Sampling and Decoding Parameters]]). Constrained decoding inserts one step before that: given the grammar's current state, compute the set of tokens that keep the eventual string valid, and set every other token's logit to `-inf`:

```
for each decode step:
    logits = model.forward(context)          # unconstrained distribution
    state  = grammar.current_state()          # position in the FSM/PDA
    mask   = grammar.allowed_tokens(state)    # precomputed per state
    logits[~mask] = -inf
    token  = sample(logits)                   # normal sampler runs on the survivors
    state  = grammar.transition(state, token)
```

The `-inf` masking (not zeroing probabilities) matters for the same numerical reason it matters in [[Snippet - Sampling from Logits]]: it removes the token from consideration *before* softmax renormalizes, so no probability mass leaks to an illegal token via floating-point residue.

The hard engineering problem is making `grammar.allowed_tokens(state)` cheap. Outlines (Willard & Louf, 2023) solves this for regexes and JSON Schema by compiling the grammar into a **finite-state machine over the model's vocabulary** ahead of time: instead of re-parsing partial output every step, you precompute, for every FSM state, the full bitmask of tokens allowed from that state. Runtime cost collapses to an O(1) mask lookup per step — the compilation cost is paid once per unique schema, not once per request.

Regular languages aren't expressive enough for everything that matters, though — balanced braces and arbitrary-depth JSON nesting are context-free, not regular, so a pure FSM either over- or under-constrains them. Grammars for that need a **pushdown automaton / context-free grammar**, which is what XGrammar and llama.cpp's GBNF format implement: a stack tracks nesting depth alongside the FSM state. These systems also add **jump-forward decoding**: when the grammar makes the next several characters mandatory regardless of model choice (the `": "` between a JSON key and its value, a closing `}`), the engine emits them directly and skips the model call entirely — free tokens, no forward pass.

The remaining wrinkle is the **token-alignment problem**. Grammars are defined over characters; models emit tokens from a [[Concept - Byte-Pair Encoding|BPE]] vocabulary where a single token can span multiple characters or straddle a grammar boundary (e.g., a token that is `"} ` all at once). The grammar compiler has to project character-level FSM transitions onto the token vocabulary, deciding for every token whether *every character it would emit* stays legal. Get this projection wrong at a prompt boundary and you get exactly the class of bug [[Concept - Token Healing]] exists to fix — the tokenizer's greedy merge choice at the boundary doesn't match what the grammar expects next.

## In practice

vLLM's guided-decoding layer exposes three interchangeable backends — Outlines, lm-format-enforcer, and XGrammar — behind one API, because grammar compilation strategy is a swappable implementation detail once the mask-per-step contract is fixed. [[Breakdown - SGLang and RadixAttention|SGLang]] ships a compressed-FSM implementation with jump-forward decoding built in, which is one reason it's a strong default for structured-output-heavy [[Playbook - Reliable Structured Output|agent and extraction workloads]] where most of the output (JSON punctuation, fixed keys) is grammar-forced anyway.

Compiled grammars are cacheable per schema: a fixed tool-calling schema hit thousands of times per second should compile once and reuse the FSM/mask table across every request, not recompile per call — recompilation cost scales with schema complexity and can dominate latency for large or deeply nested JSON schemas if done naively.

Typical use is [[Concept - Tool Use and Function Calling|forcing a tool call's arguments]] to match its JSON schema exactly, or forcing an extraction pipeline's output to match a fixed regex (dates, IDs, enums) so downstream code never has to defensively parse free text.

## Failure modes

- **Dead states.** If the grammar admits zero valid next tokens from some reachable state — a schema bug, an off-by-one in the compiled FSM, or a tokenizer whose vocabulary can't spell a required literal — generation stalls: every logit is `-inf` and sampling has nothing to draw from. Detect by unit-testing the compiled grammar against known-valid and known-boundary strings before deploying it, not just eyeballing the schema.
- **Quality collapse from over-constraining.** Forcing JSON structure from the very first token denies the model any room to "think" before committing to an answer — the SGLang/structured-output literature documents measurable accuracy drops (particularly on math and multi-step tool selection) when the grammar starts immediately versus when free-text reasoning is allowed first and only the final answer is constrained. This is the most common practitioner mistake with the technique.
- **Whitespace loops.** An overly rigid schema (e.g., one that fights the model's natural tendency to emit a space after a colon) can trap generation in a narrow allowed set that the model keeps sampling from without making forward progress, burning tokens on a technically-valid but useless stall.
- **Alignment breaks at the prompt boundary.** Character-vs-token misalignment right where user content ends and constrained generation begins is the single most common source of malformed first tokens; it's a tokenizer-boundary bug, not a grammar bug, and looks identical to one from the outside.

## The non-obvious

The instinct is to constrain the *entire* output for maximum reliability. The practitioner correction, learned the hard way and now well-documented: constrain only the parts that must be structurally exact, and let the model reason in free, unconstrained text first. A tool-call agent that free-text-reasons ("I need to call `search` with query X because...") and only switches on the grammar mask for the final JSON blob measurably outperforms one that is JSON-constrained from token zero — the grammar is a correctness guarantee on the *output format*, not a substitute for giving the model room to compute the *content* that goes into it.

## Connections
- [[Concept - Sampling and Decoding Parameters]] — constrained decoding is a mask applied before the normal temperature/top-p pipeline runs; it restricts the candidate set, it doesn't replace the sampler.
- [[Concept - Token Healing]] — fixes the tokenizer-boundary half of the same alignment problem that grammar compilation has to solve on the grammar side.
- [[Concept - Byte-Pair Encoding]] — the vocabulary the grammar's FSM/PDA has to be projected onto; token-vs-character mismatch is the source of the hardest bugs here.
- [[Concept - Streaming Detokenization]] — constrained output still has to be correctly detokenized incrementally; a forced JSON token stream hits the same partial-UTF-8 and stop-string issues as any other stream.
- [[Concept - Tool Use and Function Calling]] — the dominant production use case: forcing tool-call arguments to match a schema exactly instead of hoping.
- [[Playbook - Reliable Structured Output]] — the operational playbook for deploying this reliably, including the reason-then-constrain pattern in the non-obvious section above.
- [[Snippet - Sampling from Logits]] — the underlying `-inf`-masking numerical technique that grammar masks reuse.
- [[Breakdown - SGLang and RadixAttention]] — a serving engine whose compressed-FSM and jump-forward implementation is a reference design for this technique in production.

## Sources
- Willard & Louf (2023) — *Efficient Guided Generation for Large Language Models* (Outlines). Introduces compiling regex/JSON-schema grammars into a finite-state machine over the vocabulary with precomputed per-state token masks.
