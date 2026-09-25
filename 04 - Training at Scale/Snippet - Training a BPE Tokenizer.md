---
tags: [snippet, domain/training-at-scale, level/core]
aliases: []
summary: "Runnable HuggingFace tokenizers code that trains a byte-level BPE tokenizer with reserved special/FIM tokens and checks round-trip + fertility."
---

# Snippet - Training a BPE Tokenizer

**What it does:** trains a byte-level [[Concept - Byte-Pair Encoding]] tokenizer with a `ByteLevel` pre-tokenizer, single-digit splitting, and reserved special and fill-in-the-middle sentinel tokens (the reservation matters; see [[Concept - Chat Templates and Special Tokens]]). It then checks the encode/decode round-trip and measures fertility on a held-out sample.

**Dependencies:** `tokenizers>=0.15` (`pip install tokenizers`), Python 3.9+.

**Expected output** (this toy corpus, `vocab_size=3000`):
```
Vocab size: 3000
The 2024 model uses 128 experts. -> ['The', 'Ġ2', '0', '2', '4', 'Ġmodel', 'Ġuses', ...]
Round-trip OK: True
Fertility (tokens/word): 1.8
```
`Ġ` marks a token that starts with a space (the GPT-2/byte-level convention). Exact merges depend on corpus statistics. On a real multi-GB corpus at 32k+ vocab, English fertility settles closer to 1.2-1.4 tokens/word (see [[Concept - Tokenizer Training]]). This toy corpus is far too small and repetitive to reach that, and that's the lesson: never trust a fertility number measured on the tokenizer's own training sample.

```python
"""
Trains a byte-level BPE tokenizer (GPT-2/Llama style) with reserved special
and FIM sentinel tokens, individual-digit splitting, and verifies the
encode/decode round-trip plus fertility on held-out text.
"""

from tokenizers import Tokenizer, pre_tokenizers, decoders, Regex
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import ByteLevel, Split
from tokenizers.decoders import ByteLevel as ByteLevelDecoder

# ---- 1. Reserve special + FIM sentinel tokens BEFORE training ----
# Adding tokens after pretraining forces an embedding-matrix resize and
# leaves the new rows untrained — reserve every slot you will ever need now.
SPECIAL_TOKENS = [
    "<bos>", "<eos>", "<pad>",
    "<fim_prefix>", "<fim_middle>", "<fim_suffix>",  # Bavarian et al. 2022
]

# ---- 2. Build the tokenizer skeleton ----
tokenizer = Tokenizer(BPE(unk_token=None))  # byte-level BPE needs no UNK token

# Isolate digits into single characters (Llama-style: "2024" -> "2","0","2","4")
# BEFORE the ByteLevel split runs. Order matters: Sequence applies left to right.
tokenizer.pre_tokenizer = pre_tokenizers.Sequence([
    Split(Regex(r"\d"), behavior="isolated"),
    ByteLevel(add_prefix_space=True, use_regex=True),
])
tokenizer.decoder = ByteLevelDecoder()

# GPT-2's alternative pre-tokenization regex, for comparison. GPT-2/GPT-4
# group up to 1-3 digits per token instead of isolating each digit; the
# choice measurably changes arithmetic behavior downstream.
GPT2_PATTERN = (
    r"'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+"
    r"| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"
)

# ---- 3. Train ----
trainer = BpeTrainer(
    vocab_size=3000,               # toy value; production runs use 32k-256k
    min_frequency=2,
    special_tokens=SPECIAL_TOKENS,
    initial_alphabet=ByteLevel.alphabet(),  # all 256 bytes present -> no OOV, ever
)

corpus = [
    "The 2024 model uses 128 experts and a 4096-token context window.",
    "def forward(self, x): return self.linear(x) + self.bias",
    "Byte-pair encoding merges the most frequent adjacent pair first.",
    # In production this is a representative multi-GB sample of the actual
    # pretraining mixture, not the full corpus — merge-frequency statistics
    # converge well before you've consumed every token, and training on
    # everything is wasted I/O for no better merges.
] * 200  # repeated so the toy corpus has non-trivial merge frequencies

tokenizer.train_from_iterator(corpus, trainer=trainer)
print(f"Vocab size: {tokenizer.get_vocab_size()}")

# ---- 4. Round-trip check ----
sample = "The 2024 model uses 128 experts."
encoding = tokenizer.encode(sample)
decoded = tokenizer.decode(encoding.ids)
print(sample, "->", encoding.tokens)
print("Round-trip OK:", decoded.strip() == sample)

# ---- 5. Fertility on a held-out sample ----
held_out = "A held-out sentence with 2025 in it and several unseen words."
enc = tokenizer.encode(held_out)
fertility = len(enc.ids) / len(held_out.split())
print(f"Fertility (tokens/word): {fertility:.2f}")

# ---- 6. Persist and reload ----
tokenizer.save("tokenizer.json")
reloaded = Tokenizer.from_file("tokenizer.json")
assert reloaded.encode(sample).ids == encoding.ids
```

## Why it's written this way
- `unk_token=None` with a `ByteLevel` pre-tokenizer means any input string encodes with zero UNK tokens. That guarantee is why byte-level BPE displaced word-level and character-level BPE for LLM pretraining.
- Special and FIM sentinel tokens go into `SPECIAL_TOKENS` before `train_from_iterator` runs. Appending vocabulary after pretraining forces a resize of the embedding and unembedding matrices, and the new rows start random and untrained. Teams that bolt on chat-template tokens post hoc commonly get degenerate generation from this.
- `add_prefix_space=True` has to match between this training config and every `encode()` call at inference. A mismatch silently shifts which byte sequences map to which merges, so serving-time tokenization differs systematically from what the model saw in training.
- The digit `Split` runs before `ByteLevel` in the `Sequence`. Pre-tokenizer order decides whether digits merge into multi-digit tokens or stay isolated, and that choice measurably affects arithmetic reliability. So it's set explicitly instead of being left to BPE's frequency-driven merges.
- The corpus is a small repeated sample, not the full pretraining set. Merge-frequency statistics converge on a representative sample. The code comment flags this because it's the most common mistake newcomers make with tokenizer training: burning days tokenizing terabytes for a vocabulary that would have converged on gigabytes.

## Connections
- [[Concept - Byte-Pair Encoding]] — the merge algorithm this snippet trains; read it first to understand what `BpeTrainer` is actually computing.
- [[Concept - Tokenizer Training]] — the vocab-size, fertility, and normalization decisions this snippet's parameters encode.
- [[Gotchas - Tokenizers]] — the inference-time failure modes (glitch tokens, digit mishandling) that trace back to choices made in this training script.
- [[Concept - Pretraining Objectives]] — fill-in-the-middle training (the reason FIM sentinels are reserved here) is a pretraining-objective choice, not a tokenizer one.
- [[Lore - Glitch Tokens]] — what happens downstream when a reserved or rare token, like the ones this snippet's `initial_alphabet` guarantees exist, never accumulates enough gradient signal during pretraining.
- [[Concept - Chat Templates and Special Tokens]] — the special-token reservation pattern this snippet follows generalizes to every chat-template and role token added at the post-training stage.
