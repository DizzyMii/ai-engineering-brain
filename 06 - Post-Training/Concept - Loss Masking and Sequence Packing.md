---
tags: [concept, domain/post-training, level/core]
aliases: [label masking, packing, block-diagonal attention masking, document masking]
summary: "The masking and packing mechanics that make SFT correct (loss only on completions) and efficient (many examples per sequence without cross-contamination)."
---

> **One-paragraph hook:** Two unglamorous mechanics decide whether an SFT run is correct and whether it is fast. Loss masking ensures gradient only flows from the tokens the model is actually responsible for generating — the assistant's turn — not from the prompt it was handed. Sequence packing eliminates the padding waste that comes from batching variable-length conversations. Get either wrong and the bug is silent: the loss curve still looks fine, and the model just quietly learns the wrong thing.

## The mechanism

**Loss masking.** By default, [[Concept - The Training Loop]] used for supervised fine-tuning ([[Concept - Supervised Fine-Tuning (SFT)]]) computes cross-entropy on every token in a training sequence, exactly like pretraining. For chat data that is wrong: loss should be computed only on the tokens the model is responsible for producing at inference time — the assistant's response — not on the system prompt, the user's turn, role headers, or padding. The standard mechanism sets `labels[i] = -100` (PyTorch's `ignore_index`) for every token that shouldn't carry loss, leaving the raw token id in `labels[i]` only where gradient should flow:

$$\mathcal{L} = -\frac{1}{|C|}\sum_{i \in C} \log p_\theta(x_i \mid x_{<i})$$

where $C$ is the set of completion-token positions. Training on prompt tokens too wastes model capacity predicting text it didn't generate; "train on inputs" is a real if disputed folklore tradeoff for very short prompts, but prompt-masked is the safe default.

Multi-turn conversations complicate this further: every assistant turn must be unmasked and every user turn masked, not just the final assistant turn. A common implementation bug supervises only the last assistant turn — discarding most of the training signal in a long conversation — or leaks user-turn tokens into the loss because a re-tokenization pass shifted a span boundary. The terminal token (EOS/eot, defined by whichever [[Concept - Chat Templates and Special Tokens]] the model uses) must be present and unmasked; if it is dropped from the labels, the model never learns a stopping distribution, and at inference it silently runs to `max_new_tokens` on every generation.

**Sequence packing.** Padding variable-length conversations to a fixed batch length can waste more than 50% of tokens on `<pad>` when length variance is high, since every sequence in a batch pads out to the longest member. Packing concatenates multiple short examples into one training sequence up to the context length, eliminating padding almost entirely — a large, close-to-free throughput win. The catch is cross-contamination: naive concatenation lets the [[Concept - Attention Mechanism]] flow across example boundaries within a packed sequence, so a later example's tokens see an earlier, unrelated example's context as if it were the same conversation. The fix is a block-diagonal ("document") attention mask:

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

(`x`/`.` = causal-visible within the same block, `0` = masked out — each example attends only within its own block, never across.) [[Deep Dive - FlashAttention]]'s varlen kernels implement exactly this efficiently, since materializing the full $N \times N$ mask defeats the throughput point of packing in the first place. Without a document mask, quality degrades subtly rather than catastrophically — the model is not obviously broken, it is just quietly conditioning on context it should never have seen, which is precisely why this bug survives in codebases longer than more visible ones.

Position IDs must also reset per packed example: if positions simply keep counting across the whole packed sequence, [[Concept - Rotary Position Embeddings (RoPE)]] (or any position-dependent mechanism) assigns each later example positions as though it were a continuation of the previous one, distorting the relative-position information the model was trained to rely on.

## In practice

Packing strategy matters. Greedy concatenation — append examples in dataset order until the sequence fills, split whichever one overflows — is simple but truncates arbitrarily. Bin-packing approaches (best-fit-decreasing, sometimes called "neat packing") sort and group examples to minimize truncation, at the cost of bookkeeping and losing strict streaming order. Training frameworks expose packing as a flag but differ on whether document masking is applied by default; this is worth checking explicitly, since packing without a document mask can ship a worse model than no packing at all. A runnable reference implementation of the masking half of this is in [[Snippet - Loss Masking a Chat Dataset]].

## Failure modes

- **All-masked batch.** A template or tokenization change causes an entire batch's labels to be all `-100`; loss reports as `nan` or silently trains on zero signal. Detection: assert `(labels != -100).sum() > 0` on every batch.
- **Missing EOS in labels.** The model never learns to stop; the symptom only shows up at inference as runaway generation, never during training. Detection: decode a few examples and verify the last unmasked token is the terminal token. This is one of the entries in [[Gotchas - Chat Template Bugs]], since a wrong or stale template is usually the root cause.
- **Cross-contamination from unmasked packing.** No crash, no obvious metric shift — just a quality regression versus an unpacked baseline that is easy to misattribute to something else. Detection: ablate packing on a small run and compare eval, or directly verify the attention mask is block-diagonal rather than full causal.
- **Position ID leakage.** Degrades quality specifically on later examples within long packs, since RoPE angles are wrong past the first sub-sequence. Detection: log position-id ranges per packed sequence and confirm they reset at each boundary.

## The non-obvious

Packing and masking bugs are the single most common way an SFT run "works" — the loss curve looks completely normal, nothing crashes — while quietly producing a materially worse model than intended. Because both failure classes fail silently, teams that skip a decode-and-inspect sanity check (print one packed, masked batch and visually confirm the loss mask and attention block boundaries line up with intent) routinely ship these bugs to production and only discover them when comparing eval numbers against a differently-implemented baseline. A cheap, high-value habit: before any large SFT run, manually decode one packed batch and inspect exactly which tokens carry loss and which attend to which.

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
