---
tags: [concept, domain/inference-serving, level/unicorn]
aliases: [token_healing, tokenizer boundary healing, prompt boundary healing]
summary: "Fixing prompts that end mid-token: back up and re-constrain so the model re-chooses the natural BPE merge at the boundary."
---
> **One-paragraph hook:** A prompt that ends with `http` seems harmless, but you have just forced the model to continue from the token `http` — and in its training data the natural unit was almost always the single merged token `https` or `http://`, so it essentially never saw "the token `http`, followed by a token starting with `s`." You've pushed the model onto a low-probability path at the exact moment precision matters, and the completion quietly degrades. Token healing is the rarely-documented fix: back up over the trailing token(s) and re-constrain generation so the model re-chooses the *natural* merge. It's a silent quality bug that evals almost never target, which is exactly why it's tribal knowledge.

## The mechanism

Byte-Pair Encoding (see [[Concept - Byte-Pair Encoding]]) is *greedy and deterministic*: given a training document, the tokenizer merges characters into the longest available tokens in a fixed order, so a URL in the corpus was almost always encoded as, say, `["https", "://", "example", ".com"]` — never as `["http", "s", ":", "/", "/", …]`. The model's next-token distribution is therefore conditioned on *whole tokens as they appear under greedy tokenization of training text.*

Now an inference-time prompt arrives as a plain string and is tokenized **independently**. If a user's prompt ends in `http`, the tokenizer emits the token `http`, and the model is asked: given the token `http`, what comes next? But it has almost no training mass for "a token starting with `s` immediately after a standalone `http` token," because greedy tokenization would have swallowed that `s` into `https` in the first place. The distribution the model was trained on and the boundary the prompt imposed **disagree** — inference-time tokenization ≠ training-time tokenization. The result is a completion drawn from a distorted, unfamiliar conditional.

The damage concentrates wherever BPE greedily merges long units: **URLs, file paths, code identifiers, hex/numbers, and template punctuation**. It bites hardest exactly where you most want deterministic correctness.

**The fix — token healing.** Trim the last one (or few) tokens of the prompt, then constrain generation so the regenerated tokens must *start with the removed prefix string*, letting the model re-select the natural merge:

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

Mechanically this is *prefix-constrained decoding*: build a trie (or FSM) over the vocabulary's token strings, and at the boundary allow only tokens whose string is consistent with the removed characters. The model then re-chooses `https` as a single high-probability token instead of being stuck continuing `http`. Because the constraint only forces the removed characters and lets the model pick *which* token realizes them, healing corrects the boundary without overriding the model's intent.

## In practice

- **Microsoft `guidance`** popularized token healing; it heals the prompt boundary automatically so that constrained/templated generation doesn't get corrupted by a trailing partial token.
- **HuggingFace `transformers`** exposes a `token_healing` generation flag implementing the trim-and-reconstrain approach.
- **llama.cpp and grammar-based stacks** must solve the adjacent version of this: aligning a character-level grammar to token boundaries.
- It composes directly with [[Concept - Constrained Decoding]] — in fact constrained decoding *makes the problem worse* if you don't heal, because a grammar defined over characters will happily force the model onto the misaligned token boundary and then demand it continue from an unnatural split. Any correct prefix-constrained or FSM-based generator needs boundary healing as a prerequisite, not an add-on.

## Failure modes

- **Silent completion degradation.** No error, no crash — just subtly worse URLs, malformed identifiers, or off-by-one code. Because output *looks* plausible, it survives smoke tests; detection means specifically diffing healed vs. unhealed completions on structured/technical prompts.
- **Over-trimming.** Healing back too many tokens (or across a semantically meaningful boundary) lets the model *rewrite* prompt content you intended to fix, e.g. changing a user-supplied path.
- **Interaction with streaming.** Healing changes which token the boundary emits, which can interact with [[Concept - Streaming Detokenization]] buffering — a healed token may replace already-considered bytes, so a naive incremental detokenizer can double- or drop-emit at the seam.
- **Grammar dead-ends.** Under constrained decoding, an unhealed boundary can put the FSM in a state where no vocabulary token both satisfies the grammar *and* matches the truncated prefix — generation stalls.

## The non-obvious

The counterintuitive part is that **the tokenizer, not the model, is the source of the bug** — and it's caused by the *mismatch between two tokenizations of overlapping text*, not by anything the model got wrong. Most people reach for prompt engineering or sampling changes when a completion looks off at a boundary; the actual fix lives one layer down, in how the prompt was segmented. This is the same class of failure as a [[Lore - Glitch Tokens]] pathology (under-trained tokens the model handles badly) but from the opposite direction: glitch tokens are pieces of the vocabulary the model rarely *saw*; healing repairs a boundary the model would never have *produced*. Both stem from the fact that the discrete tokenization layer is a lossy, path-dependent interface stapled onto a continuous model.

The reason almost nobody documents this: it produces no crash, no obvious wrong answer, and no eval signal — standard benchmarks pre-tokenize cleanly and never end a prompt mid-merge, so the bug is invisible unless you're doing prefix completion, structured output, or agentic tool-argument continuation ([[Concept - Tool Use and Function Calling]]), where prompts genuinely end at arbitrary character boundaries. It's a real, measurable quality lever hiding in a place instrumentation doesn't look.

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
