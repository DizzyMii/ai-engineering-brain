---
tags: [concept, domain/training-at-scale, level/surface]
aliases: [BPE, byte-level BPE]
summary: "The greedy merge algorithm that turns raw bytes into subword tokens, silently shaping every downstream model capability."
---

# Concept - Byte-Pair Encoding

> **One-paragraph hook:** Every LLM's context window, arithmetic ability and multilingual fluency depend on a decision made once, before pretraining starts: how to chop text into tokens. Nearly every frontier model makes that decision with Byte-Pair Encoding (BPE), and BPE is dumber than people expect. It's a greedy, frequency-driven merge procedure with no notion of "optimal" segmentation, and it stays frozen for the model's entire lifetime.

## The mechanism

BPE training starts from the smallest possible alphabet (individual bytes or characters) and grows a vocabulary by repeatedly merging the most frequent adjacent pair of symbols into a new symbol:

```text
vocab = {256 byte values}
merges = []
while len(vocab) < target_vocab_size:
    pair_counts = count_adjacent_symbol_pairs(corpus)
    best_pair = argmax(pair_counts)          # most frequent adjacent pair
    new_symbol = merge(best_pair)
    vocab.add(new_symbol)
    merges.append(best_pair)                  # record the ORDER of merges
    corpus = replace_all(corpus, best_pair, new_symbol)
```

The final vocabulary is the base alphabet plus N learned merges (vocab size = base + N). The training run records the *order* of the merges as well as which ones happened. Encoding replays that ordering (the "merge rank"): to tokenize new text, apply the recorded merges greedily in rank order until none apply. No search, just a lookup-table walk, so inference-time encoding is fast and deterministic.

**Byte-level BPE** (GPT-2 and nearly every model since) uses the 256 raw byte values as the base alphabet instead of Unicode characters. That makes it robust: every possible byte string, whether any language, any emoji or a malformed encoding, is representable, so there's never an `<UNK>` token. The algorithm itself predates NLP. Gage (1994) invented it as a text compression trick; Sennrich et al. (2016) adapted it as a subword segmentation method for neural machine translation, and Radford et al. (2019, GPT-2) made the byte-level variant standard, with a vocabulary of 50257.

**Pre-tokenization** runs before merging. A regex splits text on whitespace and punctuation boundaries so merges never cross word boundaries; you'll never see "the cat" merged into one token. GPT-2's pre-tokenizer marks a leading space with a special glyph (commonly rendered "Ġ") instead of a literal space, so `" the"` and `"the"` are distinct strings that tokenize differently.

## In practice

Production vocab sizes run from 32k (Llama-2) to 128k (GPT-4, Llama-3) up to 256k (Gemma); [[Concept - Tokenizer Training]] covers the tradeoffs behind that choice. BPE gets roughly 3.5-4 characters per token on English. Code and non-English languages compress noticeably worse, because whatever corpus trained the tokenizer dominates the merge statistics. Vocab size also couples directly to model size: the embedding and unembedding matrices cost `vocab_size × hidden_dim` parameters each (often tied), so doubling the vocab to shorten sequences isn't free. See [[Concept - Pretraining Objectives]] for how this interacts with the causal-LM loss over the vocabulary. [[Snippet - Training a BPE Tokenizer]] trains one end-to-end with the `tokenizers` library, including reserving special and FIM sentinel tokens up front.

## Failure modes

- **Arithmetic errors from digit merges.** Splitting digits individually versus merging them into multi-digit chunks changes how a model sees numbers. Inconsistent digit tokenization is a well-documented contributor to poor multi-digit arithmetic.
- **Multilingual under-segmentation (high fertility).** A tokenizer trained mostly on English produces far more tokens per word for other languages. That 2-4x "token tax" inflates cost and effectively shrinks the usable context window for non-English users.
- **Imperfect round-trip invertibility.** If naive Unicode normalization is applied inconsistently between training and serving, some byte sequences won't decode back to their exact original string.
- **Whitespace-sensitive merges.** Pre-tokenization treats the leading-space and no-space forms of a word as different strings, so code and heavily indented text can tokenize unpredictably.

## The non-obvious

BPE's merge criterion is frequency-greedy, not likelihood-optimal. Each step merges whatever pair is most common right now, with no lookahead and no attempt to minimize expected token count or maximize corpus likelihood. The unigram language-model approach in SentencePiece (see [[Concept - Tokenizer Training]]) optimizes a different target: it prunes a candidate vocabulary via EM to maximize likelihood directly, and it supports probabilistic subword regularization. BPE is simpler and faster to train. Nothing guarantees its greedy merges are the best segmentation for language modeling; it just works well enough that essentially every large model uses it anyway.

The practical lesson: the tokenizer is trained once, frozen before the first pretraining token, and then governs everything downstream without anyone looking at it. That covers effective context length in "concepts" as opposed to tokens, arithmetic, multilingual fairness, even loss magnitude (a worse tokenizer inflates cross-entropy loss for reasons unrelated to the model's intelligence). When a model does something weird, inspect the tokenizer before the weights.

## Connections
- [[Concept - Tokenizer Training]] — the vocab-size and unigram-vs-BPE decisions that sit one level above this algorithm.
- [[Gotchas - Tokenizers]] — the catalog of inference-time tokenizer footguns this note's failure modes feed into.
- [[Concept - Entropy and Cross-Entropy]] — the loss BPE's segmentation choice directly inflates or deflates.
- [[Lore - Glitch Tokens]] — the war story of what happens when rare merged tokens are undertrained.
- [[Concept - Pretraining Objectives]] — the causal-LM loss computed over exactly the vocabulary BPE defines.
- [[Snippet - Training a BPE Tokenizer]] — the runnable training procedure for this exact algorithm.
- [[Concept - Chat Templates and Special Tokens]] — special/sentinel tokens must be reserved in the BPE vocab before training, not added after.
- [[Gotchas - Tokenizer Pathologies]] — broader pathologies (digit splitting, fertility, degenerate tokens) that stem from BPE's greedy training.

## Sources
- Gage (1994) — "A New Algorithm for Data Compression" — the original byte-pair-encoding compression technique.
- Sennrich et al. (2016) — "Neural Machine Translation of Rare Words with Subword Units" — adapted BPE as a subword segmentation method for NLP.
- Radford et al. (2019) — "Language Models are Unsupervised Multitask Learners" (GPT-2) — established byte-level BPE with a 50257-token vocabulary as the modern standard.
