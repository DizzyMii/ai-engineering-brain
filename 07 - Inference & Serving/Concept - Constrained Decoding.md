---
tags: [concept, domain/inference-serving, level/advanced]
aliases: [guided decoding, grammar-constrained decoding, structured generation]
summary: "Masking invalid tokens' logits each decode step so generation is forced to conform to a JSON schema, regex, or CFG — a guarantee, not a hope."
---

> **One-paragraph hook:** Ask a model to "return valid JSON" and you get valid JSON most of the time, which is useless once you're parsing millions of tool calls. Constrained decoding turns "please" into "must": at every decode step, before sampling, it intersects the vocabulary with the set of tokens that keep the output grammatically legal. The model still picks *which* legal token to emit by its own probabilities. It just can't emit an illegal one. This is the mechanism behind reliable JSON mode, function-calling schemas, and regex-constrained extraction across [[Concept - Sampling and Decoding Parameters|every serving stack]] that offers a "structured output" API.

## The mechanism

Normally the sampler computes a full distribution over the vocabulary each step and draws from it (see [[Concept - Sampling and Decoding Parameters]]). Constrained decoding adds one step before that. Given the grammar's current state, compute the tokens that keep the eventual string valid, and set every other token's logit to `-inf`:

```
for each decode step:
    logits = model.forward(context)          # unconstrained distribution
    state  = grammar.current_state()          # position in the FSM/PDA
    mask   = grammar.allowed_tokens(state)    # precomputed per state
    logits[~mask] = -inf
    token  = sample(logits)                   # normal sampler runs on the survivors
    state  = grammar.transition(state, token)
```

Masking with `-inf` instead of zeroing probabilities matters for the same numerical reason as in [[Snippet - Sampling from Logits]]. The token is gone *before* softmax renormalizes, so no probability mass leaks to an illegal token through floating-point residue.

The hard part is making `grammar.allowed_tokens(state)` cheap. Outlines (Willard & Louf, 2023) handles regexes and JSON Schema by compiling the grammar ahead of time into a **finite-state machine over the model's vocabulary**. Instead of re-parsing partial output every step, it precomputes the full bitmask of allowed tokens for every FSM state. Runtime cost drops to an O(1) mask lookup per step, and compilation is paid once per unique schema, not once per request.

Regular languages can't express everything you need. Balanced braces and arbitrary-depth JSON nesting are context-free, so a pure FSM either over- or under-constrains them. Those grammars need a **pushdown automaton / context-free grammar**, which XGrammar and llama.cpp's GBNF format implement with a stack that tracks nesting depth alongside the FSM state. These systems also do **jump-forward decoding**. When the grammar makes the next few characters mandatory whatever the model picks (the `": "` between a JSON key and its value, a closing `}`), the engine emits them directly and skips the model call. Those tokens are free, with no forward pass.

Then there's the **token-alignment problem**. Grammars are defined over characters, but models emit tokens from a [[Concept - Byte-Pair Encoding|BPE]] vocabulary where one token can span several characters or straddle a grammar boundary (a token that is `"} ` all at once, say). The compiler has to project character-level FSM transitions onto the token vocabulary and decide, for every token, whether *every character it would emit* stays legal. Get the projection wrong at a prompt boundary and you get the class of bug [[Concept - Token Healing]] exists to fix: the tokenizer's greedy merge at the boundary doesn't match what the grammar expects next.

## In practice

vLLM's guided-decoding layer puts three interchangeable backends (Outlines, lm-format-enforcer, and XGrammar) behind one API. Once the mask-per-step contract is fixed, grammar compilation strategy is a swappable implementation detail. [[Breakdown - SGLang and RadixAttention|SGLang]] ships a compressed-FSM implementation with jump-forward decoding built in. That's one reason it's a strong default for structured-output-heavy [[Playbook - Reliable Structured Output|agent and extraction workloads]], where most of the output (JSON punctuation, fixed keys) is grammar-forced anyway.

Compiled grammars can be cached per schema. A fixed tool-calling schema hit thousands of times per second should compile once and reuse its FSM/mask table across every request. Recompilation cost scales with schema complexity, and for large or deeply nested JSON schemas it can dominate latency if you recompile per call.

Typical uses: [[Concept - Tool Use and Function Calling|forcing a tool call's arguments]] to match their JSON schema exactly, or forcing an extraction pipeline's output to match a fixed regex (dates, IDs, enums) so downstream code never has to defensively parse free text.

## Failure modes

- **Dead states.** If some reachable state admits zero valid next tokens (a schema bug, an off-by-one in the compiled FSM, a vocabulary that can't spell a required literal), generation stalls. Every logit is `-inf` and there's nothing to sample. Unit-test the compiled grammar against known-valid and known-boundary strings before deploying; eyeballing the schema isn't enough.
- **Quality collapse from over-constraining.** Forcing JSON from the first token leaves the model no room to "think" before committing to an answer. The SGLang/structured-output literature documents measurable accuracy drops (particularly on math and multi-step tool selection) when the grammar starts immediately, compared with allowing free-text reasoning first and constraining only the final answer. This is the most common practitioner mistake with the technique.
- **Whitespace loops.** An overly rigid schema, e.g. one that fights the model's habit of emitting a space after a colon, can trap generation in a narrow allowed set that it keeps sampling from without progress, burning tokens on a technically valid but useless stall.
- **Alignment breaks at the prompt boundary.** Character-vs-token misalignment right where user content ends and constrained generation begins is the most common source of malformed first tokens. It's a tokenizer-boundary bug that looks identical to a grammar bug from outside.

## The non-obvious

The instinct is to constrain the *entire* output for maximum reliability. The correction, learned the hard way and now well documented, is to constrain only what must be structurally exact and let the model reason in unconstrained text first. A tool-call agent that reasons in free text ("I need to call `search` with query X because...") and only turns on the grammar mask for the final JSON blob measurably beats one that's JSON-constrained from token zero. The grammar guarantees the *output format*. It doesn't give the model room to compute the *content* that goes into it.

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
