---
tags: [concept, domain/post-training, level/core]
aliases: [label masking, packing, block-diagonal attention masking, document masking]
summary: "The masking and packing mechanics that make SFT correct (loss only on completions) and efficient (many examples per sequence without cross-contamination)."
---

> **One-paragraph hook:** Two unglamorous mechanics decide whether an SFT run is correct and whether it's fast. Loss masking makes gradient flow only from the tokens the model is responsible for generating (the assistant's turn), not from the prompt it was handed. Sequence packing removes the padding waste you get from batching variable-length conversations. Get either wrong and the bug is silent: the loss curve looks fine and the model learns the wrong thing.

## The mechanism

**Loss masking.** By default, [[Concept - The Training Loop]] used for supervised fine-tuning ([[Concept - Supervised Fine-Tuning (SFT)]]) computes cross-entropy on every token in a training sequence, same as pretraining. For chat data that's wrong. Loss belongs only on the tokens the model produces at inference time, the assistant's response. The system prompt, the user's turn, role headers and padding shouldn't carry any. The standard mechanism sets `labels[i] = -100` (PyTorch's `ignore_index`) for every token that shouldn't carry loss and leaves the raw token id in `labels[i]` only where gradient should flow:

$$\mathcal{L} = -\frac{1}{|C|}\sum_{i \in C} \log p_\theta(x_i \mid x_{<i})$$

where $C$ is the set of completion-token positions. Training on prompt tokens as well spends model capacity predicting text the model didn't generate. "Train on inputs" is a real if disputed folklore tradeoff for very short prompts, but prompt-masked is the safe default.

Multi-turn conversations make it harder. Every assistant turn has to be unmasked and every user turn masked, not only the final assistant turn. A common implementation bug supervises only the last assistant turn, throwing away most of the training signal in a long conversation. Another leaks user-turn tokens into the loss because a re-tokenization pass shifted a span boundary. The terminal token (EOS/eot, defined by whichever [[Concept - Chat Templates and Special Tokens]] the model uses) must be present and unmasked. Drop it from the labels and the model never learns a stopping distribution; at inference it runs to `max_new_tokens` on every generation.

**Sequence packing.** Padding variable-length conversations to a fixed batch length can waste more than 50% of tokens on `<pad>` when length variance is high, since every sequence in a batch pads out to the longest member. Packing concatenates several short examples into one training sequence up to the context length, which gets rid of nearly all padding. That's a large, close-to-free throughput win. The catch is cross-contamination. Naive concatenation lets the [[Concept - Attention Mechanism]] flow across example boundaries inside a packed sequence, so a later example's tokens see an earlier, unrelated example's context as if it were the same conversation. The fix is a block-diagonal ("document") attention mask:

```
        tok1 tok2 tok3 | tok4 tok5 | tok6 tok7 tok8
tok1     x    .    .   |  0    0   |  0    0    0
tok2     x    x    .   |  0    0   |  0    0    0
tok3     x    x    x   |  0    0   |  0    0    0
------------------------------------------------
tok4     0    0    0   |  x    .   |  0    0    0
tok5     0    0    0   |  x    x   |  0    0    0
------------------------------------------------
tok6     0    0    0   |  0    0   |  x    .    .
tok7     0    0    0   |  0    0   |  x    x    .
tok8     0    0    0   |  0    0   |  x    x    x
```

(`x`/`.` = causal-visible within the same block, `0` = masked out. Each example attends only within its own block, never across.) [[Deep Dive - FlashAttention]]'s varlen kernels implement this efficiently; materializing the full $N \times N$ mask would defeat the throughput point of packing. Without a document mask, quality degrades subtly. The model isn't obviously broken. It conditions on context it should never have seen, and that's why this bug survives in codebases longer than more visible ones.

Position IDs also have to reset per packed example. If positions keep counting across the whole packed sequence, [[Concept - Rotary Position Embeddings (RoPE)]] (or any position-dependent mechanism) gives each later example positions as if it continued the previous one, which distorts the relative-position information the model was trained to rely on.

## In practice

Packing strategy matters. Greedy concatenation appends examples in dataset order until the sequence fills and splits whichever one overflows. It's simple but truncates arbitrarily. Bin-packing approaches (best-fit-decreasing, sometimes called "neat packing") sort and group examples to minimize truncation, at the cost of bookkeeping and strict streaming order. Training frameworks expose packing as a flag but differ on whether they apply document masking by default. Check it explicitly: packing without a document mask can ship a worse model than no packing at all. A runnable reference implementation of the masking half is in [[Snippet - Loss Masking a Chat Dataset]].

## Failure modes

- **All-masked batch.** A template or tokenization change makes an entire batch's labels all `-100`; loss reports as `nan` or the run trains on zero signal. Detection: assert `(labels != -100).sum() > 0` on every batch.
- **Missing EOS in labels.** The model never learns to stop. The symptom only appears at inference as runaway generation, never during training. Detection: decode a few examples and check that the last unmasked token is the terminal token. It's one of the entries in [[Gotchas - Chat Template Bugs]], since a wrong or stale template is usually the root cause.
- **Cross-contamination from unmasked packing.** No crash, no obvious metric shift, just a quality regression against an unpacked baseline that's easy to blame on something else. Detection: ablate packing on a small run and compare eval, or check directly that the attention mask is block-diagonal and not full causal.
- **Position ID leakage.** Hurts quality specifically on later examples within long packs, since RoPE angles are wrong past the first sub-sequence. Detection: log position-id ranges per packed sequence and confirm they reset at each boundary.

## The non-obvious

Packing and masking bugs are the single most common way an SFT run "works" (normal loss curve, no crash) while producing a materially worse model than intended. Both failure classes are silent, so teams that skip a decode-and-inspect check routinely ship them to production and only find out when comparing eval numbers against a differently-implemented baseline. The check is cheap: before any large SFT run, print one packed, masked batch, decode it, and confirm by eye which tokens carry loss and which attend to which, and that the loss mask and attention block boundaries match what you intended.

## Connections

- [[Concept - Supervised Fine-Tuning (SFT)]] — the training stage these mechanics make correct and efficient.
- [[Concept - Chat Templates and Special Tokens]] — defines the role boundaries and terminal tokens that loss masking has to get right.
- [[Deep Dive - FlashAttention]] — the kernel family (via varlen/document masking) that makes packing's block-diagonal attention cheap instead of a full quadratic mask.
- [[Concept - Attention Mechanism]] — the mechanism cross-contamination silently corrupts when packing lacks a document mask.
- [[Concept - Rotary Position Embeddings (RoPE)]] — the positional scheme that breaks if position IDs aren't reset per packed example.
- [[Snippet - Loss Masking a Chat Dataset]] — runnable code implementing exactly the masking mechanics described here.
- [[Concept - The Training Loop]] — the general training loop these chat-specific label and batching mechanics plug into.
- [[Gotchas - Chat Template Bugs]] — the sibling bug catalog for the template-level mismatches that masking bugs frequently trace back to.

## Sources

- Krell et al. (2021) — "Efficient Sequence Packing without Cross-contamination." Establishes the block-diagonal masking fix for packed sequences.
- Dao et al. (2022/2023) — FlashAttention / FlashAttention-2. The varlen kernel family used to implement packed attention efficiently.
