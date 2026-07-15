---
tags: [gotchas, domain/training-at-scale, level/unicorn]
aliases: [tokenizer gotchas, tokenizer pitfalls]
summary: "Tokenizer pitfalls that silently corrupt training and eval: add-token traps, normalization drift, double-BOS, digits, glitch tokens."
---

# Gotchas - Tokenizers

The tokenizer is frozen before pretraining and sits at the boundary between text and tensors, which makes its failures both catastrophic and *silent* — the run keeps producing numbers, they are just the wrong numbers. Ordered by how much pain each one causes before you notice.

## 1. Adding tokens after pretraining without resizing and initializing the embeddings

**Symptom:** immediately after appending a special token (a new chat role, a tool-call sentinel) the model emits garbage logits for it, or you get an index-out-of-range on the embedding lookup / a shape mismatch on `lm_head`.

**Cause:** the vocabulary grew but the input embedding matrix and the output projection (`vocab × hidden` each) did not. If you did resize, the new rows are random and the model has never seen them, so their embeddings sit in an arbitrary region of the [[Concept - Byte-Pair Encoding|token]] representation space and produce nonsense. Reserve slots up front (see [[Concept - Tokenizer Training]]) precisely to avoid this.

**Fix:** call `resize_token_embeddings(len(tokenizer))` (or the framework equivalent) **and** initialize the new rows sensibly — the mean of existing embeddings is a strong default — then *train* on data that uses the token. If input/output embeddings are tied, resize both. Best of all: reserve unused sentinel IDs at tokenizer-training time so the matrix is already sized.

**Detection:** assert `model.get_input_embeddings().weight.shape[0] == len(tokenizer)` in your load path; watch for a spike in loss localized to sequences containing the new token.

## 2. Train/inference normalization drift and the double-BOS bug

**Symptom:** a model that evaluated well degrades in production for no architectural reason; outputs are subtly worse or a benchmark drops several points after a "no-op" serving change.

**Cause:** the normalization/pre-tokenization at serving time no longer matches training. Common culprits: a different Unicode normalization (NFKC vs none), a flipped `add_prefix_space`, or whitespace handling that re-segments the same string into different tokens than training saw. The notorious special case is **double-BOS**: a chat template prepends `<s>`/BOS *and* the tokenizer is configured with `add_bos_token=True`, so every prompt starts with two BOS tokens — a distribution the model rarely saw, which quietly poisons the first-token context. This bit Llama-2 chat integrations widely.

**Fix:** pin one canonical normalizer and pre-tokenizer and use the *same* `tokenizer.json` for training and serving. Decide exactly one owner of BOS (the template or the tokenizer, never both) and assert `tokenizer.encode(prompt)[0:2] != [bos_id, bos_id]`.

**Detection:** round-trip a corpus sample through both the training and serving tokenizers and diff the token IDs; alert on any nonzero diff. Log the first few token IDs of production prompts and grep for `[bos, bos]`.

## 3. Digit tokenization and arithmetic

**Symptom:** the model is fluent but unreliable at multi-digit arithmetic, and errors cluster at specific magnitudes or digit counts.

**Cause:** how digits are segmented is a tokenizer decision with downstream capability consequences. Llama splits digits into **single tokens**; GPT-4 (`cl100k`) groups runs of **up to three** digits, so "1234" tokenizes as `123|4` — the model must align place value across an irregular chunking, and left-to-right vs right-to-left grouping creates further artifacts. This is a training-time choice; you cannot patch it at inference.

**Fix:** for a math-sensitive model, split digits individually at tokenizer-training time (a `Split` rule on `[0-9]`), which trades slightly longer sequences for cleaner place-value structure.

**Detection:** probe arithmetic accuracy bucketed by digit count; inspect how numbers actually tokenize before blaming the model.

## 4. Undertrained / glitch tokens

**Symptom:** a specific rare token produces bizarre, off-distribution behavior — the model spells it wrong, refuses, hallucinates, or loops — even though it is a legal vocabulary entry.

**Cause:** the token exists in the vocab (it survived merge training on the tokenizer's sample) but is **nearly absent from the pretraining corpus**, so its embedding stays close to its random initialization. The canonical examples are scraped-artifact strings like `" SolidGoldMagikarp"` and Reddit usernames (Rumbelow & Watkins 2023): the tokenizer was trained on data that included a forum dump the LM was then not trained on. The embedding never moved, so at inference it is a near-random vector the model cannot interpret.

**Fix:** you generally cannot fix a shipped model; the remedy is at the next tokenizer-training pass — train the tokenizer on the *same* distribution as the LM, or prune candidate tokens that fall below a frequency floor in the actual training set.

**Detection:** histogram the L2 norm of the embedding rows — undertrained tokens cluster at anomalously small or default-magnitude norms — and cross-reference token frequency in the training corpus. [[Snippet - Finding Under-Trained Tokens]] automates exactly this sweep; the phenomenology is catalogued in [[Lore - Glitch Tokens]].

## 5. Encoding non-invertibility and boundary edge cases

**Symptom:** `decode(encode(x)) != x` for some inputs; truncating a sequence corrupts the last "character"; text with trailing whitespace tokenizes surprisingly.

**Cause:** byte-level BPE guarantees *every* byte string is encodable, but naive normalization or lossy pre-tokenization can break the round-trip; a truncation that lands mid-multibyte-UTF-8 splits a code point across the boundary; trailing-space merges attach a space to the next token in a way that changes generation. These are the low-frequency long tail that only shows up on adversarial or multilingual inputs.

**Fix:** keep the tokenizer byte-level and lossless (byte fallback, no destructive normalization); truncate on token boundaries and be aware of the UTF-8 boundary when streaming/detokenizing; test the round-trip on non-ASCII and invalid-UTF-8 fixtures.

**Detection:** a CI guard: `assert tokenizer.decode(tokenizer.encode(s)) == s` over a corpus that includes emoji, CJK, and deliberately malformed bytes.

## 6. Changing the tokenizer silently invalidates prior comparisons

**Symptom:** two model versions look comparable on the same benchmark, but one quietly used a new tokenizer, so the loss/perplexity numbers are not on the same scale and the comparison is meaningless.

**Cause:** cross-entropy and perplexity are *per-token*; a tokenizer with different fertility changes the number of tokens per document, so nominal loss numbers between tokenizers are incomparable, and any cached tokenized eval set is now stale.

**Fix:** treat the tokenizer as part of the experiment's identity. Version it with the model, re-tokenize eval sets on change, and compare on bits-per-byte (tokenizer-invariant) rather than per-token loss when the tokenizer differs. Guarding against re-tokenized eval leakage overlaps with [[Concept - Benchmark Contamination]].

**Detection:** log a tokenizer hash alongside every eval result; refuse to plot two runs on one loss axis if the hashes differ.

## Connections

- [[Concept - Tokenizer Training]] — most of these gotchas are the failure side of decisions (vocab, normalization, reserved slots) made when the tokenizer is trained.
- [[Concept - Byte-Pair Encoding]] — byte-level BPE is what guarantees encodability yet still admits the round-trip and merge-boundary edge cases in #5.
- [[Lore - Glitch Tokens]] — the phenomenology and the `SolidGoldMagikarp` origin story behind gotcha #4.
- [[Snippet - Finding Under-Trained Tokens]] — the embedding-norm sweep that detects undertrained tokens before they ship.
- [[Concept - Pretraining Objectives]] — packing, BOS/EOS handling, and sentinel reservation are shared seams between objectives and the tokenizer.
- [[Concept - Benchmark Contamination]] — a tokenizer change re-tokenizes eval sets and can invalidate contamination checks and comparisons alike.
- [[Snippet - Training a BPE Tokenizer]] — shows the reserved-token and digit-split choices whose omission causes gotchas #1 and #3.

## Sources

- Rumbelow & Watkins (2023) — *SolidGoldMagikarp (plus, prompt generation).* The report that named glitch tokens and traced them to tokenizer/LM training-data mismatch.
- Radford et al. (2019) — *Language Models are Unsupervised Multitask Learners (GPT-2).* Introduced byte-level BPE and the `Ġ` leading-space marker underlying the whitespace edge cases.
- Sennrich et al. (2016) — *Neural Machine Translation of Rare Words with Subword Units.* The original BPE whose merge determinism drives the encoding behavior.
- Kudo (2018) — *Subword Regularization / SentencePiece.* Normalization and reversible tokenization design that gotcha #2 and #5 depend on.
