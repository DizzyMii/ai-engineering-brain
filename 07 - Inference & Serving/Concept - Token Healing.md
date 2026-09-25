---
tags: [concept, domain/inference-serving, level/unicorn]
aliases: [token_healing, tokenizer boundary healing, prompt boundary healing]
summary: "Fixing prompts that end mid-token: back up and re-constrain so the model re-chooses the natural BPE merge at the boundary."
---
> **One-paragraph hook:** A prompt that ends in `http` looks harmless. It forces the model to continue from the token `http`, though, and in training data the natural unit was almost always the merged token `https` or `http://`. The model essentially never saw "the token `http`, then a token starting with `s`." You've put it on a low-probability path right where precision matters, and the completion degrades without any visible error. Token healing is the rarely documented fix: back up over the trailing token(s) and constrain generation so the model re-chooses the *natural* merge. It's a silent quality bug that evals almost never target, so it stays tribal knowledge.

## The mechanism

[[Concept - Byte-Pair Encoding]] is *greedy and deterministic*. On a training document it merges characters into the longest available tokens in a fixed order, so a URL in the corpus was almost always encoded as, say, `["https", "://", "example", ".com"]`, never as `["http", "s", ":", "/", "/", …]`. The model's next-token distribution is conditioned on *whole tokens as they come out of greedy tokenization of training text.*

At inference the prompt arrives as a plain string and gets tokenized **on its own**. If it ends in `http`, the tokenizer emits the token `http`, and the model is asked what follows it. It has almost no training mass for a token starting with `s` right after a standalone `http`, because greedy tokenization would have swallowed that `s` into `https`. The training distribution and the prompt's boundary **disagree**: inference-time tokenization ≠ training-time tokenization. The completion is drawn from a distorted, unfamiliar conditional.

The damage concentrates where BPE greedily merges long units: **URLs, file paths, code identifiers, hex/numbers, and template punctuation**. Those are the places you most want deterministic correctness.

The fix: trim the last one (or few) tokens of the prompt, then constrain generation so the regenerated tokens must *start with the removed prefix string*. The model gets to re-select the natural merge:

```
prompt string: "...visit http"
1. tokenize -> [..., "http"]
2. pop trailing token(s) whose decoded text could be the PREFIX of a longer vocab token
   -> removed = "http"
3. constrain: first generated token(s) must reproduce "http" as a prefix
   (walk a trie / FSM over the vocabulary's token strings)
4. model now freely chooses the natural continuation:
   "https" (one token) or "http://" (one token) — the merges it was trained on
```

Mechanically it's *prefix-constrained decoding*. Build a trie (or FSM) over the vocabulary's token strings and, at the boundary, allow only tokens whose string is consistent with the removed characters. The model re-chooses `https` as one high-probability token instead of being stuck continuing `http`. The constraint forces only the removed characters and leaves the model to pick *which* token realizes them, so healing fixes the boundary without overriding the model's intent.

## In practice

- **Microsoft `guidance`** popularized token healing. It heals the prompt boundary automatically so constrained or templated generation isn't corrupted by a trailing partial token.
- **HuggingFace `transformers`** has a `token_healing` generation flag that implements trim-and-reconstrain.
- **llama.cpp and grammar-based stacks** have to solve the neighboring version: aligning a character-level grammar to token boundaries.
- It composes directly with [[Concept - Constrained Decoding]]. Without healing, constrained decoding *makes the problem worse*: a grammar defined over characters will push the model onto the misaligned boundary and then demand it continue from an unnatural split. A correct prefix-constrained or FSM-based generator needs boundary healing as a prerequisite.

## Failure modes

- **Silent completion degradation.** No error and no crash, just subtly worse URLs, malformed identifiers, or off-by-one code. The output *looks* plausible, so it survives smoke tests. To catch it you have to diff healed against unhealed completions on structured or technical prompts.
- **Over-trimming.** Healing back too many tokens, or across a meaningful boundary, lets the model *rewrite* prompt content you meant to keep fixed, such as a user-supplied path.
- **Interaction with streaming.** Healing changes which token the boundary emits, which can collide with [[Concept - Streaming Detokenization]] buffering. A healed token may replace bytes already considered, and a naive incremental detokenizer double-emits or drops at the seam.
- **Grammar dead-ends.** Under constrained decoding, an unhealed boundary can leave the FSM in a state where no vocabulary token both satisfies the grammar *and* matches the truncated prefix. Generation stalls.

## The non-obvious

**The bug comes from the tokenizer, not the model.** It's caused by a *mismatch between two tokenizations of overlapping text*, and the model did nothing wrong. When a completion looks off at a boundary, most people try prompt engineering or sampling changes, but the fix sits one layer down, in how the prompt was segmented. It's in the same class as the [[Lore - Glitch Tokens]] pathology (under-trained tokens the model handles badly), coming from the other side. Glitch tokens are vocabulary pieces the model rarely *saw*; healing repairs a boundary the model would never have *produced*. Both come from a discrete, lossy, path-dependent tokenization layer stapled onto a continuous model.

Almost nobody documents it because it gives no crash, no obvious wrong answer and no eval signal. Standard benchmarks pre-tokenize cleanly and never end a prompt mid-merge. You only see the bug in prefix completion, structured output, or agentic tool-argument continuation ([[Concept - Tool Use and Function Calling]]), where prompts really do end at arbitrary character boundaries. It's a real, measurable quality lever in a place instrumentation doesn't look.

## Connections
- [[Concept - Byte-Pair Encoding]] — the greedy, path-dependent merging that makes prompt-time and train-time tokenizations disagree; the root cause.
- [[Concept - Constrained Decoding]] — the technique healing composes with (and rescues), since grammars are defined over characters but the model emits tokens.
- [[Concept - Sampling and Decoding Parameters]] — the step healing runs *before*; it fixes the boundary that the sampler then operates on.
- [[Concept - Streaming Detokenization]] — the byte-buffering layer that healing's boundary rewrite can perturb if the incremental decoder is naive.
- [[Lore - Glitch Tokens]] — the sibling tokenizer pathology (under-trained tokens); same discrete-interface fragility, opposite mechanism.
- [[Gotchas - Tokenizer Pathologies]] — the broader catalog of ways the tokenization layer silently corrupts behavior, of which boundary misalignment is one.
- [[Concept - The Inference Request Lifecycle]] — locates healing in the tokenize→prefill→decode path, right at the prompt-encoding stage.
- [[Playbook - Reliable Structured Output]] — the operational procedure where healing matters, since structured/prefix-constrained generation depends on correct boundary alignment.
- [[Concept - Tool Use and Function Calling]] — a common real source of mid-token prompt boundaries (continuing a partially-emitted tool argument).

## Sources
- Microsoft `guidance` library — introduced and popularized automatic token healing for prompt boundaries in constrained/templated generation.
- HuggingFace `transformers` — `token_healing` generation option implementing trim-and-reconstrain.
- The mechanism follows directly from the greedy-BPE tokenization property (Sennrich et al. 2016 for BPE; the healing framing is engineering folklore, not a single canonical paper).
