---
tags: [gotchas, domain/esoterica, level/core]
aliases: [Tokenization Bugs, Tokenizer Footguns]
summary: "Aggregated failure modes that trace back to tokenization, ordered by how often they bite — boundary merges, double-BOS, digit inconsistency, glitch tokens."
---

Every failure below is real, silent, and comes from the tokenizer, not the model. Ordered by how often they bite in practice.

## 1. Leading-space and word-boundary merges

**Symptom:** "My prompt works with a trailing space but not without." Few-shot examples that are correct in the docstring degrade in production; a prefilled assistant turn produces off-by-one wrong tokens; the same text pasted two ways gives different outputs.

**Cause:** In [[Concept - Byte-Pair Encoding]] tokenizers (GPT-2 lineage, Llama SentencePiece with its `▁` meta-space), the word-boundary space is *part of the token*. ` dog` and `dog` are different ids. End a prompt mid-word, or hand-concatenate strings across a boundary the model never saw in training, and it gets a different token sequence from the one you meant. The distribution shifts and behavior changes with no error.

**Fix:** Don't hand-build the token stream across boundaries. Render prompts through the model's own chat template and let the tokenizer place boundaries; respect `add_prefix_space` semantics; when prefilling, stop on a boundary the model expects.

**Detection:** Tokenize both variants and diff the id lists. Check whether your prompt's last token is a partial word or an unexpected bare-vs-spaced form.

## 2. The trailing-whitespace trap

**Symptom:** The first generated token is garbled or oddly lowercased, or the model "stutters," but only when the prompt ends in a space or newline.

**Cause:** Most content tokens are *space-prefixed* (` the`, ` and`). If the prompt ends with a literal space, the model has to emit a token that does **not** start with a space to continue the word, a low-probability, off-distribution move it was rarely trained on. You've split the natural token and put the model on the seam.

**Fix:** Strip trailing whitespace and let the model produce the space-prefixed token itself. [[Concept - Token Healing]] generalizes this: back up over the last few characters and re-tokenize so generation resumes on a natural boundary.

**Detection:** Assert `not prompt.endswith((" ", "\n", "\t"))` before sending, and watch for odd first tokens on prompts ending in whitespace.

## 3. Double-BOS and template mismatch

**Symptom:** Quality drops, system prompts get ignored, or few-shot performance degrades after switching serving stacks, on input that looks identical when printed.

**Cause:** The tokenizer adds a BOS (`add_special_tokens=True`) *and* the chat template prepends one, so you get two. Many models handle that poorly because the [[Concept - Attention Sinks]] mechanism expects one stable anchor at position 0, and a second BOS competes with it. The mirror bug, dropping BOS entirely because the template was supposed to add it, also weakens the sink and shifts behavior.

**Fix:** Decide once where special tokens come from. If the chat template adds BOS, tokenize with `add_special_tokens=False`, and confirm the exact special-token sequence by decoding a fully rendered chat. Get the [[Concept - Chat Templates and Special Tokens]] contract right and freeze it.

**Detection:** Run `tokenizer.decode(input_ids)` on a real rendered request and eyeball the specials. Count BOS ids; there must be exactly one.

## 4. Digit inconsistency and broken arithmetic

**Symptom:** Arithmetic goes wrong on long numbers, the model claims `9.11 > 9.9`, and number handling differs between prompts that "should" be the same.

**Cause:** BPE merges multi-digit substrings by corpus frequency, so `2017` may be one token and `2018` be `201`+`8`. Digit tokens end up non-compositional, carry/borrow structure is invisible to the model, and the same number can tokenize differently in different contexts. The `9.11 > 9.9` error is this plus training data (version strings, dates, chapter numbers) where `9.11` really does come after `9.9`.

**Fix:** Prefer tokenizers that split digits individually or group them in fixed 3-digit chunks (PaLM/Llama-style). [[Concept - Numeracy and Digit Tokenization]] has the full story and the value-aware embedding fixes. For arithmetic-, code- or finance-heavy workloads, test off-distribution digit *lengths* as well as short numbers.

**Detection:** Tokenize a sweep of integers and decimals and look for inconsistent splits of the same digit strings. Evaluate on long-digit arithmetic; single-digit spot checks prove little.

## 5. Multilingual and code over-fragmentation

**Symptom:** Non-English text and source code cost noticeably more tokens, latency goes up, the context window fills faster than expected, and per-token pricing is quietly higher for some languages.

**Cause:** A tokenizer trained mostly on English shreds other scripts and code into many short pieces or raw bytes. Tokens-per-word varies 2–5× across languages for the same content, which changes both the effective context budget and the cost of a request without anyone noticing.

**Fix:** Pick or train a tokenizer that covers your target languages and code. Budget context in *tokens*, not words, and include the per-language cost multiplier in pricing. Token count also drives cache economics: prefixes reused through [[Concept - Prompt Caching]] only pay off relative to how many tokens they are.

**Detection:** Measure tokens-per-word (or per character) on representative samples of each target language and your code. A >3–4× ratio against English flags a quality-and-cost problem, and those are also the ranges where under-trained tokens cluster.

## 6. Glitch and unreachable tokens

**Symptom:** Garbage, hallucination, refusal or persona breaks when a rare string appears in the input; some vocabulary that's just dead weight.

**Cause:** *Under-trained* tokens (the SolidGoldMagikarp class) have near-random embeddings because the corpus never exercised them, so the model reads a meaningless vector and does something undefined. *Unreachable* tokens are in the vocabulary but the tokenizer never produces them from any normal string: wasted capacity and occasionally an exploit surface. The backstory is in [[Lore - Glitch Tokens]].

**Fix:** Audit a new tokenizer or open-weights model before trusting it, and remap or filter known glitch tokens out of any user-controllable input path. Use [[Checklist - Auditing a Tokenizer for Glitch Tokens]] as a gate.

**Detection:** Screen the whole vocab by embedding norm / max predicted probability, then run a behavioral repeat probe on the worst offenders, following the checklist above.

## Symptom → cause quick table

| What you see | Underlying tokenizer cause | Section |
|---|---|---|
| Model can't spell a word / "count the r's" fails | BPE hides the character composition of tokens | 4 |
| Off-by-one formatting; trailing-space sensitivity | Word-boundary / leading-space token merges | 1, 2 |
| Quality drop after a serving-stack change | Double-BOS or missing-BOS template mismatch | 3 |
| Arithmetic wrong on long numbers; `9.11 > 9.9` | Non-compositional multi-digit merges | 4 |
| Foreign-language text truncated / expensive | Over-fragmentation eating the context budget | 5 |
| Garbage or evasion on a rare string | Under-trained / glitch token | 6 |

## Connections
- [[Concept - Byte-Pair Encoding]] — the merge algorithm whose boundary and digit behavior causes gotchas 1, 2, and 4.
- [[Lore - Glitch Tokens]] — the backstory and mechanism behind gotcha 6's under-trained tokens.
- [[Concept - Numeracy and Digit Tokenization]] — the deep treatment of the digit-inconsistency failure and its fixes.
- [[Concept - Attention Sinks]] — why exactly one BOS matters; the sink expects a single position-0 anchor.
- [[Concept - Chat Templates and Special Tokens]] — the special-token contract you must freeze to avoid double-BOS.
- [[Concept - Token Healing]] — the general fix for boundary/whitespace splits at generation time.
- [[Concept - Prompt Caching]] — token count (inflated by fragmentation) drives both cost and cache payoff.
- [[Checklist - Auditing a Tokenizer for Glitch Tokens]] — the pre-flight gate that catches gotchas 4–6 before production.

## Sources
- Rumbelow & Watkins (2023, LessWrong) — *SolidGoldMagikarp*. Documented the glitch-token behavior class.
- Land & Bartolo (2024) — *Fishing for Magikarp*. Automated detection of under-trained and unreachable tokens across open models.
- Community/practitioner folklore — the trailing-space, double-BOS, and boundary-merge footguns are widely reproduced and documented in tokenizer library issue trackers (Hugging Face `tokenizers`, `transformers`).
