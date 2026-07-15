---
tags: [concept, domain/training-at-scale, level/surface]
aliases: [BPE, byte-level BPE]
summary: "The greedy merge algorithm that turns raw bytes into subword tokens, silently shaping every downstream model capability."
---

# Concept - Byte-Pair Encoding

> **One-paragraph hook:** Every LLM's context window, arithmetic ability, and multilingual fluency is downstream of a decision made once, before pretraining even starts: how to chop text into tokens. Byte-Pair Encoding (BPE) is the algorithm nearly every frontier model uses to make that decision, and it is dumber than people expect — a greedy, frequency-driven merge procedure with no notion of "optimal" segmentation, frozen for the model's entire lifetime.

## The mechanism

BPE training starts from the smallest possible alphabet — individual bytes or characters — and builds up a vocabulary by repeatedly merging the most frequent adjacent pair of symbols into a new symbol:

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

The final vocabulary is the base alphabet plus N learned merges (vocab size = base + N). Crucially, what gets recorded isn't just *which* merges happened but *what order* — that ordering (the "merge rank") is what encoding replays: to tokenize new text, you apply the recorded merges greedily in rank order until no more apply. This is why BPE is fast and deterministic at inference — no search, just a lookup table walk.

**Byte-level BPE** (used by GPT-2 and nearly every model since) operates over the 256 raw byte values as the base alphabet rather than Unicode characters. This is the guarantee that makes it robust: every possible byte string — any language, any emoji, any malformed encoding — is representable, so there is never an `<UNK>` token. The original algorithm predates NLP entirely (Gage 1994, a text compression trick); Sennrich et al. (2016) adapted it for neural machine translation as a subword segmentation method, and Radford et al. (2019, GPT-2) made the byte-level variant standard, with a vocabulary of 50257.

**Pre-tokenization** happens before merging: a regex splits text on whitespace/punctuation boundaries so that merges never cross word boundaries (you'll never see a merge spanning "the cat" into one token). GPT-2's pre-tokenizer marks a leading space with a special glyph (commonly rendered as "Ġ") rather than a literal space character, so `" the"` and `"the"` become distinguishable, differently-tokenized strings.

## In practice

Typical production vocab sizes range from 32k (Llama-2) to 128k (GPT-4, Llama-3) up to 256k (Gemma) — see [[Concept - Tokenizer Training]] for the tradeoff calculus behind that choice. On English text, BPE achieves roughly 3.5-4 characters per token; code and non-English languages compress noticeably worse because the merge statistics are dominated by whatever corpus trained the tokenizer. The vocabulary size directly couples to model size: the embedding and unembedding matrices cost `vocab_size × hidden_dim` parameters each (often tied), so doubling the vocab to shorten sequences is not free — see [[Concept - Pretraining Objectives]] for how this interacts with the causal-LM loss over the vocabulary. [[Snippet - Training a BPE Tokenizer]] walks through training one end-to-end with the `tokenizers` library, including reserving special and FIM sentinel tokens up front.

## Failure modes

- **Arithmetic errors from digit merges**: whether digits are split individually or merged into multi-digit chunks changes how a model sees numbers; inconsistent digit tokenization is a well-documented contributor to poor multi-digit arithmetic.
- **Multilingual under-segmentation (high fertility)**: a tokenizer trained mostly on English text produces far more tokens per word for other languages — a 2-4x "token tax" that inflates cost and effectively shrinks the usable context window for non-English users.
- **Imperfect round-trip invertibility**: naive Unicode normalization applied inconsistently between training and serving can make some byte sequences fail to decode back to their exact original string.
- **Whitespace-sensitive merges**: because pre-tokenization treats leading-space and no-space variants of a word as different strings, code and heavily-indented text can tokenize unpredictably.

## The non-obvious

BPE's merge criterion is **frequency-greedy, not likelihood-optimal** — at each step it merges whatever pair is most common right now, with no lookahead and no attempt to minimize the expected token count or maximize corpus likelihood. This is a genuinely different optimization target from the unigram language-model approach used by SentencePiece (see [[Concept - Tokenizer Training]]), which prunes a candidate vocabulary via EM to directly maximize likelihood and can do probabilistic subword regularization. BPE is simpler and faster to train but there is no guarantee its greedy merges are the best possible segmentation for language modeling — it just happens to work well enough that essentially every large model uses it anyway.

The deeper practitioner lesson: the tokenizer is trained once, frozen before a single pretraining token is seen, and then silently governs everything downstream — effective context length in "concepts" rather than tokens, arithmetic capability, multilingual fairness, and even loss magnitude (a worse tokenizer inflates cross-entropy loss for reasons that have nothing to do with the model's intelligence). Debugging a "weird" model behavior by inspecting the tokenizer first, before the weights, is a habit worth having.

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
