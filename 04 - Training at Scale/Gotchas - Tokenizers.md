---
tags: [gotchas, domain/training-at-scale, level/unicorn]
aliases: [tokenizer gotchas, tokenizer pitfalls]
summary: "Tokenizer pitfalls that silently corrupt training and eval: add-token traps, normalization drift, double-BOS, digits, glitch tokens."
---

# Gotchas - Tokenizers

The tokenizer gets frozen before pretraining and sits between text and tensors. When it fails, it fails badly and *silently*: the run keeps producing numbers, just wrong ones. Ordered by how much pain each causes before anyone notices.

## 1. Adding tokens after pretraining without resizing and initializing the embeddings

**Symptom:** append a special token (a new chat role, a tool-call sentinel) and the model immediately emits garbage logits for it, or you hit an index-out-of-range on the embedding lookup or a shape mismatch on `lm_head`.

**Cause:** the vocabulary grew, but the input embedding matrix and the output projection (`vocab × hidden` each) didn't. Resized or not, the new rows are random and unseen, so they land somewhere arbitrary in the [[Concept - Byte-Pair Encoding|token]] representation space and produce nonsense. Reserving slots up front (see [[Concept - Tokenizer Training]]) avoids this.

**Fix:** call `resize_token_embeddings(len(tokenizer))` (or your framework's equivalent) **and** initialize the new rows sensibly. The mean of the existing embeddings is a strong default. Then *train* on data that uses the token. With tied input/output embeddings, resize both. Better: reserve unused sentinel IDs at tokenizer-training time so the matrix is already sized.

**Detection:** assert `model.get_input_embeddings().weight.shape[0] == len(tokenizer)` in the load path. Watch for a loss spike confined to sequences that contain the new token.

## 2. Train/inference normalization drift and the double-BOS bug

**Symptom:** a model that evaluated well degrades in production for no architectural reason. Outputs get subtly worse, or a benchmark drops several points after a "no-op" serving change.

**Cause:** serving-time normalization or pre-tokenization no longer matches training. Usual suspects: a different Unicode normalization (NFKC vs none), a flipped `add_prefix_space`, or whitespace handling that splits the same string into different tokens than training saw.

The notorious case is **double-BOS**. The chat template prepends `<s>`/BOS, the tokenizer also has `add_bos_token=True`, and every prompt starts with two BOS tokens. The model rarely saw that, and it poisons the first-token context without any error. It bit Llama-2 chat integrations widely.

**Fix:** pin one canonical normalizer and pre-tokenizer, and use the *same* `tokenizer.json` for training and serving. Give BOS exactly one owner (template or tokenizer, never both) and assert `tokenizer.encode(prompt)[0:2] != [bos_id, bos_id]`.

**Detection:** run a corpus sample through both the training and serving tokenizers and alert on any token-ID diff. Log the first few token IDs of production prompts and grep for `[bos, bos]`.

## 3. Digit tokenization and arithmetic

**Symptom:** the model is fluent but shaky at multi-digit arithmetic, and the errors cluster at particular magnitudes or digit counts.

**Cause:** digit segmentation is a tokenizer decision with capability consequences. Llama splits digits into **single tokens**. GPT-4 (`cl100k`) groups runs of **up to three** digits, so "1234" becomes `123|4` and the model has to line up place value across irregular chunks. Left-to-right vs right-to-left grouping adds more artifacts. It's set at training time; you can't patch it at inference.

**Fix:** for a math-sensitive model, split digits individually when training the tokenizer (a `Split` rule on `[0-9]`). You pay slightly longer sequences and get cleaner place-value structure.

**Detection:** probe arithmetic accuracy bucketed by digit count. Check how numbers actually tokenize before blaming the model.

## 4. Undertrained / glitch tokens

**Symptom:** one rare token triggers bizarre, off-distribution behavior. The model misspells it, refuses, hallucinates or loops, even though it's a legal vocabulary entry.

**Cause:** the token is in the vocab (it survived merge training on the tokenizer's sample) but is **nearly absent from the pretraining corpus**, so its embedding barely moves from random init. The canonical examples are scraped-artifact strings like `" SolidGoldMagikarp"` and Reddit usernames (Rumbelow & Watkins 2023). The tokenizer's training data included a forum dump the LM was never trained on, so at inference the token is a near-random vector the model can't interpret.

**Fix:** a shipped model usually stays broken. Fix it at the next tokenizer-training pass: train the tokenizer on the *same* distribution as the LM, or prune candidate tokens below a frequency floor in the actual training set.

**Detection:** histogram the L2 norms of the embedding rows. Undertrained tokens cluster at unusually small or default-magnitude norms; cross-check against token frequency in the training corpus. [[Snippet - Finding Under-Trained Tokens]] automates this sweep, and [[Lore - Glitch Tokens]] catalogues the phenomenology.

## 5. Encoding non-invertibility and boundary edge cases

**Symptom:** `decode(encode(x)) != x` for some inputs. Truncating a sequence corrupts the last "character". Text with trailing whitespace tokenizes oddly.

**Cause:** byte-level BPE guarantees *every* byte string can be encoded, but naive normalization or lossy pre-tokenization can still break the round-trip. A truncation that lands in the middle of a multibyte UTF-8 sequence splits a code point across the boundary. Trailing-space merges attach a space to the next token and change generation. This long tail mostly shows up on adversarial or multilingual inputs.

**Fix:** keep the tokenizer byte-level and lossless (byte fallback, no destructive normalization), truncate on token boundaries, and mind UTF-8 boundaries when streaming or detokenizing. Test the round-trip on non-ASCII and invalid-UTF-8 fixtures.

**Detection:** a CI guard, `assert tokenizer.decode(tokenizer.encode(s)) == s`, run over a corpus with emoji, CJK and deliberately malformed bytes.

## 6. Changing the tokenizer silently invalidates prior comparisons

**Symptom:** two model versions look comparable on the same benchmark, but one switched tokenizers, so the loss/perplexity numbers aren't on the same scale and the comparison means nothing.

**Cause:** cross-entropy and perplexity are *per-token*. Different fertility changes tokens per document, so nominal loss can't be compared across tokenizers and any cached tokenized eval set goes stale.

**Fix:** the tokenizer is part of the experiment's identity. Version it with the model, re-tokenize eval sets when it changes, and compare on bits-per-byte (tokenizer-invariant) instead of per-token loss when tokenizers differ. Guarding against re-tokenized eval leakage overlaps with [[Concept - Benchmark Contamination]].

**Detection:** log a tokenizer hash with every eval result. Refuse to plot two runs on one loss axis if the hashes differ.

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
